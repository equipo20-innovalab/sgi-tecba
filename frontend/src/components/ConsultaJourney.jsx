import { useState } from 'react';
import ConfirmacionView from './ConfirmacionView';
import { HomeCards } from './HomeCards';
import MapView from './MapView';
import { ResultPanel } from './ResultPanel';
import { SearchBox } from './SearchBox';
import TramitesView from './TramitesView';

const VISTAS = {
    RESULTADO: 'resultado',
    CONFIRMACION: 'confirmacion',
    TRAMITES: 'tramites',
};

function AvisoDatosDePrueba() {
    return (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Vista de prueba: los requisitos, plazos y trámites mostrados son contenido fijo
            y todavía no están vinculados a los datos de esta consulta.
        </p>
    );
}

export function ConsultaJourney({
    data,
    direccionBusqueda,
    error,
    isLoading,
    onSearch,
}) {
    const [vista, setVista] = useState(VISTAS.RESULTADO);

    const direccionConfirmacion = data?.ubicacion?.direccion_normalizada
        || data?.ubicacion?.direccion_original
        || direccionBusqueda;
    const handleSearch = (queryText) => {
        setVista(VISTAS.RESULTADO);
        onSearch(queryText);
    };

    return (
        <>
            <SearchBox onSearch={handleSearch} isLoading={isLoading} />

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

            {vista === VISTAS.RESULTADO && (
                <>
                    {error && (
                        <div className="max-w-4xl mx-auto mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
                            <p className="font-semibold">No se pudo consultar el backend.</p>
                            <p className="mt-1">{error}</p>
                            <p className="mt-1">Verificá que la API esté activa y que la base de datos tenga los datos cargados.</p>
                        </div>
                    )}

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                        <div className="lg:col-span-7 flex flex-col">
                            <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-4 h-full flex flex-col">
                                <div className="flex items-center justify-between mb-3">
                                    <h3 className="text-sm font-bold text-gcba-dark flex items-center gap-2">
                                        <span>📍</span> Visor Geográfico Urbano
                                    </h3>
                                    <span className="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
                                        Satélite Esri · MapLibre
                                    </span>
                                </div>
                                <div className="flex-1 min-h-[400px]">
                                    <MapView location={data?.ubicacion} />
                                </div>
                            </div>
                        </div>

                        <div className="lg:col-span-5 flex flex-col">
                            <ResultPanel data={data} />
                            {data && (
                                <button
                                    type="button"
                                    onClick={() => setVista(VISTAS.CONFIRMACION)}
                                    className="w-full rounded-xl bg-gcba-primary px-4 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-900"
                                >
                                    Ver requisitos
                                </button>
                            )}
                        </div>
                    </div>

                    <HomeCards />
                </>
            )}
        </>
    );
}
