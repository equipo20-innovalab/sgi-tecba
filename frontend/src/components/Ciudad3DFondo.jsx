/**
 * @file Ciudad3DFondo.jsx
 * @description Fondo de pantalla con la ciudad 3D de CABA. Reutiliza las
 * teselas vectoriales de CARTO que ya usa el visor para dibujar edificios
 * extruidos sobre un plano claro, sin satélite y sin interacción, de modo que
 * acompañe el contenido sin robarle protagonismo ni capturar clics.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { GCBA_FUENTES } from '../services/ciudad3d';

maplibregl.setWorkerUrl(maplibreWorkerUrl);

/** Centro del microcentro porteño, enmarcado en vista aérea inclinada. */
const CENTRO = [-58.3816, -34.6037];

const ESTILO_FONDO = {
    version: 8,
    glyphs: GCBA_FUENTES.cartoGlyphs,
    sources: {
        'carto-edificios': {
            type: 'vector',
            tiles: [GCBA_FUENTES.cartoVectores],
            maxzoom: 15,
            attribution: '© OpenStreetMap contributors © CARTO',
        },
    },
    layers: [
        {
            id: 'fondo-claro',
            type: 'background',
            paint: { 'background-color': '#d6e4f6' },
        },
        {
            id: 'calles',
            type: 'line',
            source: 'carto-edificios',
            'source-layer': 'roads',
            minzoom: 12,
            paint: {
                'line-color': '#ffffff',
                'line-width': [
                    'interpolate',
                    ['linear'],
                    ['zoom'],
                    12, 0.6,
                    15, 2.2,
                ],
                'line-opacity': 0.65,
            },
        },
        {
            id: 'edificios-3d',
            type: 'fill-extrusion',
            source: 'carto-edificios',
            'source-layer': 'buildings',
            minzoom: 13,
            paint: {
                'fill-extrusion-color': [
                    'interpolate',
                    ['linear'],
                    ['coalesce', ['get', 'height'], 12],
                    0, '#c4c3be',
                    12, '#d2d1cc',
                    25, '#deddd8',
                    45, '#eae9e4',
                    80, '#f4f3ef',
                    150, '#faf9f6',
                ],
                'fill-extrusion-height': ['coalesce', ['get', 'height'], 12],
                'fill-extrusion-base': ['coalesce', ['get', 'min_height'], 0],
                'fill-extrusion-opacity': 0.92,
                'fill-extrusion-vertical-gradient': true,
            },
        },
    ],
};

export const Ciudad3DFondo = () => {
    const contenedorRef = useRef(null);

    useEffect(() => {
        if (!contenedorRef.current) return undefined;

        const mapa = new maplibregl.Map({
            container: contenedorRef.current,
            style: ESTILO_FONDO,
            center: CENTRO,
            zoom: 14.4,
            pitch: 58,
            bearing: -18,
            interactive: false,
            attributionControl: false,
            fadeDuration: 0,
        });



        // Giro muy lento para dar vida al fondo sin distraer la lectura.
        let timer = null;
        mapa.on('load', () => {
            timer = window.setInterval(() => {
                if (document.hidden) return;
                mapa.setBearing(mapa.getBearing() + 0.04);
            }, 100);
        });

        return () => {
            if (timer) window.clearInterval(timer);
            mapa.remove();
        };
    }, []);

    return (
        <div
            ref={contenedorRef}
            aria-hidden="true"
            className="z-0 pointer-events-none"
            style={{
                // MapLibre aplica `.maplibregl-map { position: relative }` que
                // gana a la clase `fixed` de Tailwind según el orden de import.
                // El estilo inline garantiza que el mapa cubra todo el viewport.
                position: 'fixed',
                inset: 0,
                width: '100vw',
                height: '100vh',
                backgroundColor: '#d6e4f6',
            }}
        />
    );
};

export default Ciudad3DFondo;
