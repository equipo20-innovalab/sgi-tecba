import { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import 'maplibre-gl/dist/maplibre-gl.css';

// Vite no resuelve el worker interno de MapLibre: lo apuntamos explícitamente
maplibregl.setWorkerUrl(maplibreWorkerUrl);

// Límites aproximados de la Ciudad de Buenos Aires (excluye el conurbano)
const CABA_BOUNDS = [
    [-58.545, -34.71], // suroeste [lng, lat]
    [-58.33, -34.52], // noreste [lng, lat]
];

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
                // Gradiente por altura: más bajo = gris oscuro, más alto = casi blanco
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

export default function MapView({ location }) {
    const containerRef = useRef(null);
    const mapRef = useRef(null);
    const markerRef = useRef(null);
    const [mapMessage, setMapMessage] = useState('Cargando mapa satelital…');

    useEffect(() => {
        const map = new maplibregl.Map({
            container: containerRef.current,
            style: ESTILO_SATELITE,
            center: [-58.3816, -34.6037],
            zoom: 14,
            pitch: 45,
            bearing: -15,
            antialias: true,
            minZoom: 12,
            maxBounds: CABA_BOUNDS,
            attributionControl: true,
        });
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        mapRef.current = map;

        map.on('load', async () => {
            try {
                const response = await fetch('/api/v1/mapa/comunas');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const geojson = await response.json();

                map.addSource('comunas', { type: 'geojson', data: geojson });
                map.addLayer(
                    {
                        id: 'comunas-fill',
                        type: 'fill',
                        source: 'comunas',
                        paint: {
                            'fill-color': '#38bdf8',
                            'fill-opacity': 0.06,
                        },
                    },
                    'calles-nombres',
                );
                map.addLayer(
                    {
                        id: 'comunas-line',
                        type: 'line',
                        source: 'comunas',
                        paint: {
                            'line-color': '#7dd3fc',
                            'line-width': 1.5,
                            'line-opacity': 0.7,
                        },
                    },
                    'calles-nombres',
                );

                // Restringir la navegación a la silueta real de CABA
                const bounds = boundsDeGeoJSON(geojson);
                if (bounds) {
                    map.setMaxBounds(bounds);
                }
                setMapMessage('Ciudad de Buenos Aires · satélite + edificios 3D');
            } catch (error) {
                setMapMessage(`No se pudieron cargar los límites de comunas: ${error.message}`);
            }
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

    // Solo mostramos la ubicación consultada (sin capas masivas de parcelas)
    useEffect(() => {
        const map = mapRef.current;
        if (!map) return;

        const lat = Number(location?.lat);
        const lng = Number(location?.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        const aplicarUbicacion = () => {
            markerRef.current?.remove();
            const label = location.direccion_normalizada
                || location.direccion_original
                || location.smp
                || 'Ubicación consultada';
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
        <div className="relative w-full h-[400px] rounded-xl overflow-hidden shadow-lg border border-slate-200">
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
