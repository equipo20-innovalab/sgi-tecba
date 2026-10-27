import React, { useEffect } from 'react';
import L from 'leaflet';

// Importamos los estilos y marcadores de Leaflet
import 'leaflet/dist/leaflet.css';
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

export default function MapView({ direccion = "Calle Corrientes 2500, Buenos Aires" }) {
    useEffect(() => {
        // Inicializamos el mapa centrado en Buenos Aires por defecto
        const map = L.map('map').setView([-34.6037, -58.3816], 15);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        let marker = null;

        // Función para buscar las coordenadas reales de la dirección usando Nominatim (Gratuito y sin CORS)
        const ubicarDireccion = async () => {
            try {
                // Si la dirección es genérica, usamos el centro por defecto
                const query = direccion ? `${direccion}, Buenos Aires, Argentina` : "Buenos Aires";
                const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
                const data = await response.json();

                if (data && data.length > 0) {
                    const lat = parseFloat(data[0].lat);
                    const lon = parseFloat(data[0].lon);

                    // Movemos el mapa a la nueva ubicación y ponemos el marcador
                    map.setView([lat, lon], 17);
                    if (marker) {
                        marker.setLatLng([lat, lon]);
                    } else {
                        marker = L.marker([lat, lon]).addTo(map)
                            .bindPopup(`<b>Ubicación:</b><br />${direccion}`)
                            .openPopup();
                    }
                } else {
                    // Si no encuentra la dirección exacta, deja un marcador por defecto en CABA
                    marker = L.marker([-34.6037, -58.3816]).addTo(map)
                        .bindPopup(`SGI TECBA <br /> ${direccion}`)
                        .openPopup();
                }
            } catch (error) {
                console.error("Error al buscar la geolocalización de la dirección:", error);
            }
        };

        ubicarDireccion();

        // Limpieza al desmontar el componente
        return () => {
            map.remove();
        };
    }, [direccion]); // Se vuelve a ejecutar cada vez que cambia la dirección ingresada

    return (
        <div className="w-full h-full min-h-[220px] rounded-lg overflow-hidden border border-slate-200 relative z-0">
            <div id="map" style={{ width: '100%', height: '100%' }} />
        </div>
    );
}