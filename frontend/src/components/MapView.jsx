/**
 * @file MapView.jsx
 * @description Visor geográfico urbano 3D para la Ciudad Autónoma de Buenos Aires.
 * Utiliza MapLibre GL con imágenes satelitales de Esri y extrusión de edificios 3D de CARTO.
 * Incluye validación estricta de coordenadas (Bounding Box CABA) para evitar desplazamientos
 * hacia coordenadas nulas (0, 0) o zonas fuera de la jurisdicción terrestre.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import 'maplibre-gl/dist/maplibre-gl.css';

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

// Estilo satelital (Esri World Imagery) + edificios 3D desde los vectores de CARTO
const ESTILO_SATELITE = {
    version: 8,
    glyphs: 'https://tiles.basemaps.cartocdn.com/v/20261001-03/fonts/{fontstack}/{range}.pbf',
    sources: {
        satelite: {
            type: 'raster',
            tiles: [
                'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            ],
            tileSize: 256,
            maxzoom: 19,
            attribution:
                'Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community',
        },
        edificios: {
            type: 'vector',
            tiles: [
                'https://tiles.basemaps.cartocdn.com/v/20261001-03/vectortiles/carto.streets/v2/{z}/{x}/{y}.mvt',
            ],
            maxzoom: 15,
            attribution: '© OpenStreetMap contributors © CARTO',
        },
    },
    layers: [
        { id: 'fondo-satelite', type: 'raster', source: 'satelite' },
        {
            id: '3d-buildings',
            type: 'fill-extrusion',
            source: 'edificios',
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
                'fill-extrusion-opacity': 0.9,
                'fill-extrusion-vertical-gradient': true,
            },
        },
        {
            id: 'calles-nombres',
            type: 'symbol',
            source: 'edificios',
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
            source: 'edificios',
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

/**
 * Calcula la caja delimitadora (Bounding Box) de una colección GeoJSON.
 *
 * @param {Object} geojson - Objeto GeoJSON con las geometrías de comunas.
 * @returns {Array<Array<number>>|null} Coordenadas [[minLng, minLat], [maxLng, maxLat]].
 */
function boundsDeGeoJSON(geojson) {
    let minLng = Infinity;
    let minLat = Infinity;
    let maxLng = -Infinity;
    let maxLat = -Infinity;

    const visitar = (coords) => {
        if (typeof coords[0] === 'number') {
            const [lng, lat] = coords;
            minLng = Math.min(minLng, lng);
            maxLng = Math.max(maxLng, lng);
            minLat = Math.min(minLat, lat);
            maxLat = Math.max(maxLat, lat);
            return;
        }
        coords.forEach(visitar);
    };

    (geojson.features || []).forEach((feature) => visitar(feature.geometry.coordinates));
    if (!Number.isFinite(minLng)) return null;
    return [
        [minLng, minLat],
        [maxLng, maxLat],
    ];
}

/**
 * Componente MapView
 * Renderiza el mapa interactivo 3D y posiciona un marcador en la dirección consultada.
 *
 * @param {Object} props - Propiedades del componente.
 * @param {Object|null} props.location - Objeto ubicación devuelto por el backend ({lat, lng, direccion_normalizada, smp}).
 * @param {string} [props.containerHeightClass='h-full min-h-[400px]'] - Clases de altura Tailwind para el contenedor.
 * @returns {JSX.Element} Contenedor con el visor MapLibre GL.
 */
export default function MapView({ location, containerHeightClass = 'h-full min-h-[400px]' }) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const markerRef = useRef(null);
    const [mapMessage, setMapMessage] = useState('Cargando mapa satelital…');

    useEffect(() => {
        const map = new maplibregl.Map({
            container: containerRef.current,
            style: ESTILO_SATELITE,
            center: DEFAULT_CENTER,
            zoom: DEFAULT_ZOOM,
            pitch: 45,
            bearing: -15,
            antialias: true,
            minZoom: 12,
            maxBounds: CABA_BOUNDS,
            attributionControl: true,
        });
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        mapRef.current = map;

        map.on('load', () => {
            setMapMessage('Ciudad de Buenos Aires · satélite/edificios 3D');
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
            map.remove();
            mapRef.current = null;
        };
    }, []);

    // Actualización de marcador y cámara al recibir una nueva ubicación
    useEffect(() => {
        const map = mapRef.current;
        if (!map) return;

        // Si no hay ubicación o sus coordenadas son nulas/inválidas, limpiamos el pin
        // y mantenemos la vista general de CABA sin volar a [0, 0] (agua).
        if (!esCoordenadaEnCABA(location?.lat, location?.lng)) {
            markerRef.current?.remove();
            markerRef.current = null;
            return;
        }

        const lat = Number(location.lat);
        const lng = Number(location.lng);

        const aplicarUbicacion = () => {
            markerRef.current?.remove();
            const label =
                location.direccion_normalizada ||
                location.direccion_original ||
                location.smp ||
                'Ubicación consultada';

            const popup = new maplibregl.Popup({ maxWidth: '320px' }).setText(label);
            markerRef.current = new maplibregl.Marker()
                .setLngLat([lng, lat])
                .setPopup(popup)
                .addTo(map);
            markerRef.current.togglePopup();
            map.flyTo({ center: [lng, lat], zoom: 16 });
        };

        if (map.isStyleLoaded()) {
            aplicarUbicacion();
        } else {
            map.once('load', aplicarUbicacion);
        }
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