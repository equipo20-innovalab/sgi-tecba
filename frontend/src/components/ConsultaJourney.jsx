/**
 * @file ConsultaJourney.jsx
 * @description Componente contenedor principal para el flujo de consulta interactiva (SGI TECBA).
 * Reestructurado con un layout vertical óptimo: el mapa geográfico urbano se ubica en la
 * parte superior a ancho completo, y los paneles de información detallada, resultados y 
 * botones de acción se despliegan de manera ordenada en la parte inferior.
 * @author Equipo Frontend - SGI TECBA
 */

import { useState } from 'react';
import ConfirmacionView from './ConfirmacionView';
import { HomeCards } from './HomeCards';
import MapView from './MapView';
import { ResultPanel } from './ResultPanel';
import { SearchBox } from './SearchBox';
import TramitesView from './TramitesView';

/**
 * Enumeración de las vistas disponibles dentro del journey de consulta.
 * @readonly
 * @enum {string}
 */
const VISTAS = {
    RESULTADO: 'resultado',
    CONFIRMACION: 'confirmacion',
    TRAMITES: 'tramites',
};

/**
 * Componente auxiliar para mostrar un aviso temporal de datos de prueba.
 * @returns {JSX.Element} Elemento JSX con el banner de advertencia.
 */
function AvisoDatosDePrueba() {
    return (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Vista de prueba: los requisitos, plazos y trámites mostrados son contenido fijo
            y todavía no están vinculados a los datos de esta consulta.
        </p>
    );
}

/**
 * Componente ConsultaJourney
 * Gestiona la navegación interna entre la vista de resultados, confirmación y trámites,
 * organizando visualmente el mapa y los datos bajo una estructura vertical limpia.
 * 
 * @param {Object} props - Propiedades del componente.
 * @param {Object|null} props.data - Datos de la ubicación y resultados devueltos por la API.
 * @param {string} props.direccionBusqueda - Texto de la dirección ingresada en el buscador.
 * @param {string} props.error - Mensaje de error en caso de fallo en la petición HTTP.
 * @param {boolean} props.isLoading - Indicador de estado de carga activo.
 * @param {Function} props.onSearch - Función callback para disparar la consulta al backend.
 * @returns {JSX.Element} Estructura completa del journey de consulta.
 */
export function ConsultaJourney({
    data,
    direccionBusqueda,
    error,
    isLoading,
    onSearch,
}) {
    // Estado local para gestionar la vista activa dentro del flujo del usuario
    const [vista, setVista] = useState(VISTAS.RESULTADO);

    // Obtención de la dirección normalizada o original para las vistas secundarias
    const direccionConfirmacion = data?.ubicacion?.direccion_normalizada
        || data?.ubicacion?.direccion_original
        || direccionBusqueda;

    /**
     * Manejador para reiniciar la vista a resultados al realizar una nueva búsqueda.
     * @param {string} queryText - Texto de búsqueda ingresado.
     */
    const handleSearch = (queryText) => {
        setVista(VISTAS.RESULTADO);
        onSearch(queryText);
    };

    return (
        <>
            {/* Buscador Principal */}
            <SearchBox onSearch={handleSearch} isLoading={isLoading} />

            {/* Vista de Confirmación de Dirección y Datos */}
            {vista === VISTAS.CONFIRMACION && (
                <>
                    <AvisoDatosDePrueba />
                    <ConfirmacionView
                        direccionBusqueda={direccionConfirmacion}
                        ubicacion={data?.ubicacion}
                        onBack={() => setVista(VISTAS.RESULTADO)}
                        onVerTramites={() => setVista(VISTAS.TRAMITES)}
                    />
                </>
            )}

            {/* Vista Detallada de Trámites y Requisitos */}
            {vista === VISTAS.TRAMITES && (
                <>
                    <AvisoDatosDePrueba />
                    <TramitesView
                        direccionBusqueda={direccionConfirmacion}
                        ubicacion={data?.ubicacion}
                        onBackToConfirmacion={() => setVista(VISTAS.CONFIRMACION)}
                    />
                </>
            )}

            {/* Vista Principal de Resultados (Layout Vertical) */}
            {vista === VISTAS.RESULTADO && (
                <>
                    {/* Alerta de Error de Conexión */}
                    {error && (
                        <div className="max-w-4xl mx-auto mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
                            <p className="font-semibold">No se pudo consultar el backend.</p>
                            <p className="mt-1">{error}</p>
                            <p className="mt-1">Verificá que la API esté activa y que la base de datos tenga los datos cargados.</p>
                        </div>
                    )}

                    {/* Layout Vertical Optimizado: Mapa en la parte superior y paneles abajo */}
                    <div className="flex flex-col gap-6 w-full">

                        {/* 1. Visor Geográfico Urbano (Mapa Arriba) */}
                        <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-4 w-full flex flex-col">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-sm font-bold text-gcba-dark flex items-center gap-2">
                                    <span>📍</span> Visor Geográfico Urbano
                                </h3>
                                <span className="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
                                    Satélite Esri · MapLibre
                                </span>
                            </div>
                            <div className="w-full h-[450px]">
                                <MapView location={data?.ubicacion} />
                            </div>
                        </div>

                        {/* 2. Paneles de Información y Requisitos (Abajo) */}
                        <div className="flex flex-col gap-4 w-full">
                            <ResultPanel data={data} />
                            {data && (
                                <button
                                    type="button"
                                    onClick={() => setVista(VISTAS.CONFIRMACION)}
                                    className="w-full rounded-xl bg-gcba-primary px-4 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-900 shadow-md"
                                >
                                    Ver requisitos
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Tarjetas de Home inferiores */}
                    <HomeCards />
                </>
            )}
        </>
    );
}