import { useEffect } from 'react';
import L from 'leaflet';

// Importamos las imágenes de los marcadores para que Vite las gestione correctamente
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

// Corregimos la ruta por defecto de los íconos de Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: markerIcon2x,
    iconUrl: markerIcon,
    shadowUrl: markerShadow,
});

export default function MapView() {
    useEffect(() => {
        // Inicializamos el mapa
        const map = L.map('map').setView([-34.6037, -58.3816], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        L.marker([-34.6037, -58.3816]).addTo(map)
            .bindPopup('Sistema de Gestión Inteligente <br /> SGI - TECBA')
            .openPopup();

        // Limpieza al desmontar
        return () => {
            map.remove();
        };
    }, []);

    return (
        <div className="w-full h-[400px] rounded-xl overflow-hidden shadow-lg border border-slate-200">
            <div id="map" style={{ width: '100%', height: '100%' }} />
        </div>
    );
}