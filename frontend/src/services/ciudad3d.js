/**
 * @file ciudad3d.js
 * @description Fuentes públicas del visor oficial Ciudad 3D del Gobierno de la
 * Ciudad de Buenos Aires (USIG / EPOK) y helpers para consultar la ficha
 * urbanística de una parcela por SMP.
 *
 * Estos servicios se consumen directamente desde el navegador: responder con
 * CORS `*` (verificado contra los endpoints públicos). No requieren API key.
 * @author Equipo Frontend - SGI TECBA
 */

/** URLs base del ecosistema Ciudad 3D / USIG / EPOK. */
export const GCBA_FUENTES = {
    visor: 'https://ciudad3d.buenosaires.gob.ar/',
    epokApi: 'https://epok.buenosaires.gob.ar',
    servicioGeo: 'https://ws.usig.buenosaires.gob.ar',
    vectores: 'https://vectortiles.usig.buenosaires.gob.ar/cur3d/',
    sateliteTms:
        'https://servicios.usig.buenosaires.gob.ar/mapcache/tms/1.0.0/fotografias_aereas_2021_caba_3857@GoogleMapsCompatible/{z}/{x}/{y}.png',
    esriSatelite:
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    cartoVectores:
        'https://tiles.basemaps.cartocdn.com/v/20261118-01/vectortiles/carto.streets/v2/{z}/{x}/{y}.mvt',
    cartoGlyphs:
        'https://tiles.basemaps.cartocdn.com/v/20261118-01/fonts/{fontstack}/{range}.pbf',
};

/** Devuelve el enlace profundo al visor oficial para un SMP dado. */
export function urlVisorCiudad3D(smp) {
    if (!smp) return GCBA_FUENTES.visor;
    return `${GCBA_FUENTES.visor}?smp=${encodeURIComponent(smp)}`;
}

async function fetchJson(url, signal) {
    const response = await fetch(url, { signal });
    if (!response.ok) {
        throw new Error(`La fuente oficial respondió ${response.status}`);
    }
    return response.json();
}

/**
 * Consulta en paralelo las fichas urbanísticas publicadas por EPOK para un SMP.
 * Se usan `allSettled` para que si un bloque no tiene datos (o falla) igual se
 * muestre el resto de la información disponible.
 *
 * @param {string} smp - Clave Sección-Manzana-Parcela, ej. `005-075B-000`.
 * @param {{signal?: AbortSignal}} [options] - Señal para cancelar la petición.
 * @returns {Promise<Object|null>} Objeto con las secciones disponibles.
 */
export async function obtenerDatosOficialesParcela(smp, { signal } = {}) {
    const smpLimpio = String(smp ?? '').trim();
    if (!smpLimpio) return null;

    const smpCodificado = encodeURIComponent(smpLimpio);
    const base = GCBA_FUENTES.epokApi;
    const endpoints = [
        ['catastro', `${base}/catastro/parcela/?smp=${smpCodificado}`],
        ['edificabilidad', `${base}/cur3d/seccion_edificabilidad/?smp=${smpCodificado}`],
        ['mixtura', `${base}/cur3d/mixtura_usos/?smp=${smpCodificado}`],
        ['afectaciones', `${base}/cur3d/afectaciones/?smp=${smpCodificado}`],
        ['obras', `${base}/cur3d/obras/?smp=${smpCodificado}`],
        ['inspecciones', `${base}/cur3d/inspecciones/?smp=${smpCodificado}`],
        ['patrimonio', `${base}/cur3d/monumento_historico_nacional/?smp=${smpCodificado}`],
        ['catalogacion', `${base}/cur3d/fichadecatalogacion/?smp=${smpCodificado}`],
        ['estadoParcelario', `${base}/cur3d/constitucion_estado_parcelario/?smp=${smpCodificado}`],
    ];

    const respuestas = await Promise.allSettled(
        endpoints.map(([, url]) => fetchJson(url, signal))
    );

    const datos = { smp: smpLimpio };
    respuestas.forEach((respuesta, indice) => {
        if (respuesta.status === 'fulfilled') {
            datos[endpoints[indice][0]] = respuesta.value;
        }
    });

    // Barrio y Comuna no vienen en `/catastro/parcela/`: el visor oficial los
    // obtiene de USIG a partir del centroide de la parcela.
    const centroide = datos.catastro?.centroide;
    if (Array.isArray(centroide) && centroide.length >= 2) {
        const [lng, lat] = centroide;
        const urlGeo = `${GCBA_FUENTES.servicioGeo}/datos_utiles?x=${encodeURIComponent(
            lng
        )}&y=${encodeURIComponent(lat)}`;
        try {
            datos.geo = await fetchJson(urlGeo, signal);
        } catch {
            // Dato opcional: la ficha se muestra igual si USIG no responde.
        }
    }

    return datos;
}
