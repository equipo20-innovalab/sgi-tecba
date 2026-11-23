/**
 * @file MapView.jsx
 * @description Visor geográfico urbano 3D para la Ciudad Autónoma de Buenos Aires.
 * Mantiene la estructura original (validación estricta de coordenadas CABA,
 * marcador, popup y flyTo) y incorpora las fuentes públicas del visor oficial
 * Ciudad 3D del GCBA: parcelas catastrales, Código Urbanístico, alturas,
 * mixtura, incidencia/alícuota y volúmenes edificables por SMP.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { obtenerParcelasMapa } from '../services/api';
import {
    GCBA_FUENTES,
    obtenerDatosOficialesParcela,
    urlVisorCiudad3D,
} from '../services/ciudad3d';

// Vite no resuelve el worker interno de MapLibre: lo apuntamos explícitamente
maplibregl.setWorkerUrl(maplibreWorkerUrl);

// Centro por defecto (Obelisco, CABA)
const DEFAULT_CENTER = [-58.3816, -34.6037];
const DEFAULT_ZOOM = 14;

// Límites aproximados de la Ciudad de Buenos Aires (excluye el conurbano y el río abierto)
const CABA_BOUNDS = [
    [-58.545, -34.71], // suroeste [lng, lat]
    [-58.33, -34.52],  // noreste [lng, lat]
];

/** Capas temáticas del Código Urbanístico (permanecen ocultas; sin selector). */
const CAPAS_TEMATICAS = {
    alturas: { id: 'gcba-alturas', titulo: 'Alturas CU' },
    mixtura: { id: 'gcba-mixtura', titulo: 'Mixtura de usos' },
    incidencia: { id: 'gcba-incidencia', titulo: 'Incidencia UVA' },
    alicuota: { id: 'gcba-alicuota', titulo: 'Alícuota Ley 6.062' },
    barrios: { id: 'gcba-barrios', titulo: 'Barrios' },
};

const SIN_PARCELA = '__sin_parcela__';

/**
 * Valida que un par de coordenadas corresponda a un punto válido dentro de CABA.
 * Previene el bug de JavaScript donde Number(null) === 0 desplaza el mapa al agua.
 *
 * @param {number|string|null|undefined} lat - Latitud a evaluar.
 * @param {number|string|null|undefined} lng - Longitud a evaluar.
 * @returns {boolean} True si las coordenadas son números reales dentro de CABA.
 */
function esCoordenadaEnCABA(lat, lng) {
    if (lat === null || lat === undefined || lng === null || lng === undefined) {
        return false;
    }
    if (lat === '' || lng === '') {
        return false;
    }
    const latNum = Number(lat);
    const lngNum = Number(lng);
    if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) {
        return false;
    }
    const [[minLng, minLat], [maxLng, maxLat]] = CABA_BOUNDS;
    return latNum >= minLat && latNum <= maxLat && lngNum >= minLng && lngNum <= maxLng;
}

/**
 * Estilo del visor: satélite USIG (TMS) como base, edificios 3D de contexto de
 * CARTO y capas vectoriales oficiales de USIG/EPOK con los colores publicados
 * en `configBase.json` del visor Ciudad 3D.
 */
const ESTILO_CIUDAD_3D = {
    version: 8,
    glyphs: GCBA_FUENTES.cartoGlyphs,
    sources: {
        'satelite-usig': {
            type: 'raster',
            scheme: 'tms',
            tiles: [GCBA_FUENTES.sateliteTms],
            tileSize: 256,
            // El servicio USIG publica hasta el nivel 18; por encima MapLibre
            // hace overzoom de esas teselas en lugar de pedir z19 (que dan 404).
            maxzoom: 18,
            attribution:
                'Satélite © GCBA · USIG (Fotografías Aéreas 2021 CABA)',
        },
        'satelite-esri': {
            type: 'raster',
            tiles: [GCBA_FUENTES.esriSatelite],
            tileSize: 256,
            maxzoom: 19,
            attribution: 'Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics',
        },
        'carto-edificios': {
            type: 'vector',
            tiles: [GCBA_FUENTES.cartoVectores],
            maxzoom: 15,
            attribution: '© OpenStreetMap contributors © CARTO',
        },
        'gcba-parcelas': {
            type: 'vector',
            tiles: [
                `${GCBA_FUENTES.vectores}parcela/{z}/{x}/{y}.pbf?optimize=true`,
            ],
            minzoom: 10,
            maxzoom: 18,
        },
        'gcba-codigo-urbanistico': {
            type: 'vector',
            tiles: [
                `${GCBA_FUENTES.vectores}codigo_urbanistico/{z}/{x}/{y}.pbf?optimize=true`,
            ],
            minzoom: 10,
            maxzoom: 18,
        },
        'gcba-volumen-edif': {
            type: 'vector',
            tiles: [
                `${GCBA_FUENTES.vectores}volumen_edif/{z}/{x}/{y}.pbf?optimize=true`,
            ],
            minzoom: 10,
            maxzoom: 18,
        },
    },
    layers: [
        { id: 'satelite-usig', type: 'raster', source: 'satelite-usig' },
        {
            id: 'satelite-esri',
            type: 'raster',
            source: 'satelite-esri',
            layout: { visibility: 'none' },
        },

        // Capas temáticas del Código Urbanístico (colores según configBase.json)
        {
            id: CAPAS_TEMATICAS.alturas.id,
            type: 'fill',
            source: 'gcba-codigo-urbanistico',
            'source-layer': 'default',
            minzoom: 13,
            layout: { visibility: 'none' },
            paint: {
                'fill-color': [
                    'match',
                    ['to-string', ['coalesce', ['get', 'uni_edif_1'], '']],
                    '38', '#557e8d',
                    '31.2', '#85adb1',
                    '22.8', '#ea9e82',
                    '17.2', '#f5c294',
                    '14.6', '#c9c2ab',
                    '12', '#f0e6cc',
                    '9', '#f3d30c',
                    '#ffffff',
                ],
                'fill-opacity': 0.5,
            },
        },
        {
            id: CAPAS_TEMATICAS.mixtura.id,
            type: 'fill',
            source: 'gcba-codigo-urbanistico',
            'source-layer': 'default',
            minzoom: 13,
            layout: { visibility: 'none' },
            paint: {
                'fill-color': [
                    'match',
                    ['to-number', ['coalesce', ['get', 'uso_1'], 0]],
                    0, '#ffffff',
                    1, '#eff3ff',
                    2, '#bdd7e7',
                    3, '#6baed6',
                    4, '#3182bd',
                    5, '#08519c',
                    '#f7f7f7',
                ],
                'fill-opacity': 0.6,
            },
        },
        {
            id: CAPAS_TEMATICAS.incidencia.id,
            type: 'fill',
            source: 'gcba-codigo-urbanistico',
            'source-layer': 'default',
            minzoom: 13,
            layout: { visibility: 'none' },
            paint: {
                'fill-color': [
                    'step',
                    ['coalesce', ['to-number', ['get', 'inc_uva_21']], 0],
                    '#969696',
                    300, '#5ea7b1',
                    400, '#91cba9',
                    500, '#bce4aa',
                    600, '#def2b4',
                    700, '#ffffbf',
                    800, '#ffdf9a',
                    900, '#febe74',
                    1000, '#f69053',
                    1500, '#e75437',
                ],
                'fill-opacity': 0.6,
            },
        },
        {
            id: CAPAS_TEMATICAS.alicuota.id,
            type: 'fill',
            source: 'gcba-codigo-urbanistico',
            'source-layer': 'default',
            minzoom: 13,
            layout: { visibility: 'none' },
            paint: {
                'fill-color': [
                    'match',
                    ['to-string', ['coalesce', ['get', 'alicuota'], '']],
                    '0.1', 'rgb(255, 191, 191)',
                    '0.18', 'rgb(214, 144, 144)',
                    '0.27', 'rgb(176, 104, 104)',
                    '0.35', 'rgb(138, 69, 69)',
                    '#ffffff',
                ],
                'fill-opacity': 0.55,
            },
        },
        {
            id: CAPAS_TEMATICAS.barrios.id,
            type: 'fill',
            source: 'gcba-codigo-urbanistico',
            'source-layer': 'default',
            minzoom: 13,
            layout: { visibility: 'none' },
            paint: {
                'fill-color': '#d1bbd0',
                'fill-opacity': ['case', ['has', 'barrio'], 0.35, 0],
            },
        },

        // Límites catastrales oficiales y parcela seleccionada
        {
            id: 'gcba-parcela-contorno',
            type: 'line',
            source: 'gcba-parcelas',
            'source-layer': 'default',
            minzoom: 15,
            paint: {
                'line-color': '#c0bfc1',
                'line-width': ['interpolate', ['linear'], ['zoom'], 16, 0.6, 18, 2, 19, 4],
                'line-opacity': 0.85,
            },
        },
        {
            id: 'parcela-seleccionada',
            type: 'fill',
            source: 'gcba-parcelas',
            'source-layer': 'default',
            filter: ['==', ['get', 'smp'], SIN_PARCELA],
            paint: {
                'fill-color': '#fdd306',
                'fill-opacity': 0.28,
                'fill-outline-color': '#fdd306',
            },
        },

        // Contexto 3D de CARTO + volumen edificable oficial de la parcela
        {
            id: '3d-buildings',
            type: 'fill-extrusion',
            source: 'carto-edificios',
            'source-layer': 'buildings',
            minzoom: 13,
            paint: {
                'fill-extrusion-color': [
                    'interpolate',
                    ['linear'],
                    ['coalesce', ['get', 'height'], 12],
                    0, '#6f767e',
                    12, '#848b93',
                    25, '#9aa1a9',
                    45, '#b1b8c0',
                    80, '#c9d0d7',
                    150, '#e6ebf1',
                ],
                'fill-extrusion-height': ['coalesce', ['get', 'height'], 12],
                'fill-extrusion-base': ['coalesce', ['get', 'min_height'], 0],
                'fill-extrusion-opacity': 0.85,
                'fill-extrusion-vertical-gradient': true,
            },
        },
        {
            id: 'edif_smp',
            type: 'fill-extrusion',
            source: 'gcba-volumen-edif',
            'source-layer': 'default',
            minzoom: 14,
            filter: ['==', ['get', 'smp'], SIN_PARCELA],
            paint: {
                'fill-extrusion-color': '#fdd306',
                'fill-extrusion-height': [
                    'coalesce', ['to-number', ['get', 'altura_fin']], 0,
                ],
                'fill-extrusion-opacity': 0.9,
            },
        },

        // Rotulado (glifos de CARTO, heredado del visor anterior)
        {
            id: 'calles-nombres',
            type: 'symbol',
            source: 'carto-edificios',
            'source-layer': 'roads',
            minzoom: 14,
            filter: ['has', 'name'],
            layout: {
                'symbol-placement': 'line',
                'text-field': ['get', 'name'],
                'text-font': ['Montserrat Medium', 'Open Sans Regular', 'Noto Sans Regular'],
                'text-size': ['interpolate', ['linear'], ['zoom'], 14, 10, 16, 12, 18, 13],
                'symbol-spacing': 250,
                'text-pitch-alignment': 'viewport',
                'text-rotation-alignment': 'viewport',
                'text-keep-upright': true,
            },
            paint: {
                'text-color': '#ffffff',
                'text-halo-color': 'rgba(0, 0, 0, 0.85)',
                'text-halo-width': 1.2,
            },
        },
        {
            id: 'lugares-nombres',
            type: 'symbol',
            source: 'carto-edificios',
            'source-layer': 'places',
            minzoom: 13,
            filter: ['has', 'name'],
            layout: {
                'text-field': ['get', 'name'],
                'text-font': ['Montserrat SemiBold', 'Open Sans Bold', 'Noto Sans Regular'],
                'text-size': ['interpolate', ['linear'], ['zoom'], 13, 11, 16, 14],
                'text-transform': 'uppercase',
                'text-letter-spacing': 0.08,
                'text-max-width': 8,
            },
            paint: {
                'text-color': '#f8fafc',
                'text-halo-color': 'rgba(0, 0, 0, 0.9)',
                'text-halo-width': 1.4,
            },
        },
    ],
};

const ETIQUETAS_AFECTACION = {
    riesgo_hidrico: 'Riesgo hídrico',
    lep: 'LEP',
    ensanche: 'Ensanche',
    apertura: 'Apertura de calle',
    ci_digital: 'CI Digital',
};

/** Formatea números de EPOK con el separador de miles de `es-AR`. */
function formatearNumero(valor) {
    if (valor === null || valor === undefined || valor === '') return '';
    const numero = Number(String(valor).replace(',', '.'));
    if (Number.isNaN(numero)) return String(valor);
    return numero.toLocaleString('es-AR', { maximumFractionDigits: 2 });
}

/** Agrega una fila etiqueta/valor al contenido del popup usando texto seguro. */
function agregarFila(contenedor, etiqueta, valor) {
    if (valor === null || valor === undefined || valor === '') return;
    const fila = document.createElement('div');
    fila.className = 'visor-popup__fila';
    const nombre = document.createElement('span');
    nombre.className = 'visor-popup__etiqueta';
    nombre.textContent = etiqueta;
    const dato = document.createElement('span');
    dato.className = 'visor-popup__valor';
    dato.textContent = String(valor);
    fila.append(nombre, dato);
    contenedor.appendChild(fila);
}

/**
 * Construye el contenido del popup combinando la respuesta local del backend
 * con la ficha urbanística oficial de EPOK. Todo se inserta con `textContent`
 * para evitar inyección de HTML con datos externos.
 */
function construirContenidoPopup({ location, oficial, local, cargando }) {
    const raiz = document.createElement('div');
    raiz.className = 'visor-popup';

    const titulo = document.createElement('div');
    titulo.className = 'visor-popup__titulo';
    titulo.textContent =
        location?.direccion_normalizada ||
        location?.direccion_original ||
        oficial?.catastro?.direccion ||
        'Ubicación consultada';
    raiz.appendChild(titulo);

    const bajada = document.createElement('div');
    bajada.className = 'visor-popup__bajada';
    bajada.textContent = 'Ficha urbanística · GCBA';
    raiz.appendChild(bajada);

    const smp = location?.smp || oficial?.smp || null;
    agregarFila(raiz, 'SMP', smp);

    if (cargando) {
        const aviso = document.createElement('p');
        aviso.className = 'visor-popup__aviso';
        aviso.textContent = 'Consultando ficha urbanística oficial…';
        raiz.appendChild(aviso);
        return raiz;
    }

    const edificabilidad = oficial?.edificabilidad;
    const catastro = oficial?.catastro;
    const parcelaLocal = smp
        ? (local?.features || []).find((feature) => feature.smp === smp)
        : null;

    // Datos geográficos básicos del visor oficial (USIG), por centroide.
    if (oficial?.geo?.barrio) {
        agregarFila(raiz, 'Barrio', oficial.geo.barrio);
    }
    if (oficial?.geo?.comuna) {
        agregarFila(raiz, 'Comuna', oficial.geo.comuna);
    }

    // Datos catastrales que el visor oficial muestra como "Datos básicos".
    if (catastro) {
        if (catastro.superficie_cubierta) {
            agregarFila(
                raiz,
                'Superficie edificada',
                `${formatearNumero(catastro.superficie_cubierta)} m²`
            );
        }
        agregarFila(raiz, 'Unidades funcionales', formatearNumero(catastro.unidades_funcionales));
        agregarFila(raiz, 'Pisos sobre rasantes', formatearNumero(catastro.pisos_sobre_rasante));
        agregarFila(raiz, 'Pisos bajo rasantes', formatearNumero(catastro.pisos_bajo_rasante));
    }

    // Toda la información disponible se muestra de una vez; el contenedor del
    // popup tiene scroll interno por si una parcela tuviera muchos datos.
    if (edificabilidad) {
        const alturas = Array.isArray(edificabilidad.altura_max)
            ? edificabilidad.altura_max.filter((valor) => Number(valor) > 0)
            : [];
        if (alturas.length) {
            agregarFila(raiz, 'Altura máx. (CU)', `${alturas.join(' / ')} m`);
        }
        if (edificabilidad.plusvalia?.incidencia_uva !== undefined) {
            agregarFila(raiz, 'Incidencia UVA', edificabilidad.plusvalia.incidencia_uva);
        }
        if (edificabilidad.plusvalia?.alicuota !== undefined) {
            agregarFila(raiz, 'Alícuota', edificabilidad.plusvalia.alicuota);
        }
        const distritos = (edificabilidad.distrito_especial || [])
            .map((item) => item.distrito_especifico)
            .filter(Boolean);
        if (distritos.length) agregarFila(raiz, 'Distrito', distritos.join(', '));
        if (edificabilidad.catalogacion?.denominacion) {
            agregarFila(
                raiz,
                'Catalogación',
                `${edificabilidad.catalogacion.denominacion}${
                    edificabilidad.catalogacion.proteccion
                        ? ` · ${edificabilidad.catalogacion.proteccion}`
                        : ''
                }`
            );
        }
        if (edificabilidad.superficie_parcela) {
            agregarFila(
                raiz,
                'Superficie de parcela',
                `${formatearNumero(edificabilidad.superficie_parcela)} m²`
            );
        }
    }

    const usos = oficial?.mixtura?.usos;
    if (Array.isArray(usos) && usos.some((valor) => Number(valor) > 0)) {
        agregarFila(raiz, 'Usos', usos.join(' / '));
    }

    const afectaciones = Object.entries(oficial?.afectaciones || {})
        .filter(([, valor]) => Number(valor) > 0)
        .map(([clave]) => ETIQUETAS_AFECTACION[clave] || clave);
    if (afectaciones.length) {
        agregarFila(raiz, 'Afectaciones', afectaciones.join(', '));
    }

    const obras = oficial?.obras;
    if (obras) {
        const totalObras = [
            ...(obras.obras_iniciadas || []),
            ...(obras.obras_registradas || []),
        ].length;
        if (totalObras) agregarFila(raiz, 'Obras registradas', totalObras);
    }
    const inspecciones = oficial?.inspecciones?.inspecciones;
    if (Array.isArray(inspecciones) && inspecciones.length) {
        agregarFila(raiz, 'Inspecciones', inspecciones.length);
    }
    if (parcelaLocal) {
        agregarFila(raiz, 'Habilitaciones', parcelaLocal.total_habilitaciones);
        if (parcelaLocal.rubros?.length) {
            agregarFila(raiz, 'Rubros', parcelaLocal.rubros.slice(0, 4).join(', '));
        }
    }

    const planos = [
        ['croquis_parcela', 'Croquis de parcela'],
        ['perimetro_manzana', 'Perímetro de manzana'],
        ['plano_indice', 'Plano índice'],
    ];
    planos.forEach(([clave, etiqueta]) => {
        const url = edificabilidad?.link_imagen?.[clave];
        if (!url) return;
        const enlace = document.createElement('a');
        enlace.className = 'visor-popup__enlace visor-popup__enlace--plano';
        enlace.href = url;
        enlace.target = '_blank';
        enlace.rel = 'noreferrer';
        enlace.textContent = `${etiqueta} ↗`;
        raiz.appendChild(enlace);
    });

    const enlaceVisor = document.createElement('a');
    enlaceVisor.className = 'visor-popup__enlace visor-popup__enlace--principal';
    enlaceVisor.href = urlVisorCiudad3D(smp);
    enlaceVisor.target = '_blank';
    enlaceVisor.rel = 'noreferrer';
    enlaceVisor.textContent = 'Ver ficha en Ciudad 3D ↗';
    raiz.appendChild(enlaceVisor);

    return raiz;
}

/** Aplica el filtro de SMP a las capas que resaltan la parcela seleccionada. */
function aplicarFiltroParcela(map, smp) {
    const filtro = ['==', ['get', 'smp'], smp || SIN_PARCELA];
    ['edif_smp', 'parcela-seleccionada'].forEach((id) => {
        if (map.getLayer(id)) map.setFilter(id, filtro);
    });
}

/**
 * Componente MapView
 * Renderiza el visor 3D con capas oficiales y posiciona un marcador en la
 * dirección consultada.
 *
 * @param {Object} props - Propiedades del componente.
 * @param {Object|null} props.location - Ubicación del backend ({lat, lng, direccion_normalizada, smp}).
 * @param {string} [props.containerHeightClass='h-full min-h-[400px]'] - Clases de altura Tailwind.
 * @returns {JSX.Element} Contenedor con el visor MapLibre GL.
 */
export default function MapView({ location, containerHeightClass = 'h-full min-h-[400px]' }) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const markerRef = useRef(null);
    const popupRef = useRef(null);
    const [mapMessage, setMapMessage] = useState('Cargando mapa satelital…');

    useEffect(() => {
        const map = new maplibregl.Map({
            container: containerRef.current,
            style: ESTILO_CIUDAD_3D,
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            pitch: 45,
            bearing: -15,
            antialias: true,
            minZoom: 12,
            maxBounds: CABA_BOUNDS,
            attributionControl: true,
        });
        // Zoom a la izquierda para que no tape la ficha, que va arriba a la derecha.
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left');
        mapRef.current = map;

        map.on('load', () => {
            setMapMessage('Ciudad 3D · GCBA · Sin capa');
        });

        map.on('error', (event) => {
            const mensaje = event?.error?.message || '';
            const status = event?.error?.status;
            if (mensaje.includes('Failed to fetch') || status === 0) {
                setMapMessage('No se pudieron cargar los mapas base. Verificá tu conexión a Internet.');
            }
        });

        return () => {
            markerRef.current?.remove();
            markerRef.current = null;
            popupRef.current = null;
            map.remove();
            mapRef.current = null;
        };
    }, []);

    // Actualización de marcador, filtros, datos y cámara al recibir una nueva ubicación
    useEffect(() => {
        const map = mapRef.current;
        if (!map) return undefined;
        const controlador = new AbortController();

        // Si no hay ubicación o sus coordenadas son nulas/inválidas, limpiamos el pin
        // y mantenemos la vista general de CABA sin volar a [0, 0] (agua).
        if (!esCoordenadaEnCABA(location?.lat, location?.lng)) {
            markerRef.current?.remove();
            markerRef.current = null;
            popupRef.current = null;
            aplicarFiltroParcela(map, null);
            return () => controlador.abort();
        }

        const lat = Number(location.lat);
        const lng = Number(location.lng);
        const smp = location.smp ? String(location.smp).trim() : null;

        const aplicarUbicacion = () => {
            aplicarFiltroParcela(map, smp);

            markerRef.current?.remove();
            const popup = new maplibregl.Popup({
                maxWidth: '300px',
                className: 'visor-popup-ctl',
                closeOnClick: false,
            }).setDOMContent(
                construirContenidoPopup({ location, oficial: null, local: null, cargando: true })
            );
            markerRef.current = new maplibregl.Marker()
                .setLngLat([lng, lat])
                .setPopup(popup)
                .addTo(map);
            popupRef.current = popup;
            markerRef.current.togglePopup();
            map.flyTo({ center: [lng, lat], zoom: 16 });

            const bbox = 0.006;
            const consultas = [];
            if (smp) {
                consultas.push(obtenerDatosOficialesParcela(smp, { signal: controlador.signal }));
            }
            consultas.push(
                obtenerParcelasMapa({
                    oeste: lng - bbox,
                    sur: lat - bbox,
                    este: lng + bbox,
                    norte: lat + bbox,
                    signal: controlador.signal,
                })
            );

            Promise.allSettled(consultas).then((respuestas) => {
                if (controlador.signal.aborted || !popupRef.current) return;
                const oficial = smp && respuestas[0].status === 'fulfilled' ? respuestas[0].value : null;
                const local = respuestas[smp ? 1 : 0].status === 'fulfilled'
                    ? respuestas[smp ? 1 : 0].value
                    : null;
                popupRef.current.setDOMContent(
                    construirContenidoPopup({ location, oficial, local, cargando: false })
                );
            });
        };

        if (map.isStyleLoaded()) {
            aplicarUbicacion();
        } else {
            map.once('load', aplicarUbicacion);
        }

        return () => {
            controlador.abort();
            map.off('load', aplicarUbicacion);
        };
    }, [location]);

    return (
        <div className={`relative w-full ${containerHeightClass} rounded-xl overflow-hidden shadow-lg border border-slate-200`}>
            <div
                ref={containerRef}
                aria-label="Mapa de la Ciudad de Buenos Aires"
                style={{ width: '100%', height: '100%' }}
            />
            <div
                className="absolute bottom-3 left-3 z-[1000] max-w-[90%] rounded-md bg-white/95 px-3 py-2 text-xs text-slate-700 shadow"
                role="status"
                aria-live="polite"
            >
                <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full bg-emerald-600" />
                {mapMessage}
            </div>
        </div>
    );
}
