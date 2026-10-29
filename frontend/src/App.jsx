/**
 * @file App.jsx
 * @description Componente raíz de la aplicación SGI TECBA. Integra la arquitectura modular de la interfaz
 * y el ruteo por hash entre el inicio, rubros, cobertura y fuentes.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { SearchBox } from './components/SearchBox';
import { ResultPanel } from './components/ResultPanel';
import { HomeCards } from './components/HomeCards';
import RubrosView from './components/RubrosView';
import CoberturaView from './components/CoberturaView';
import FuentesView from './components/FuentesView';
import MapView from './components/MapView';
import { consultarProyecto } from './services/api';

const RUTAS = ['/', '/rubros', '/cobertura', '/fuentes'];

function rutaActual() {
    const hash = window.location.hash.replace(/^#/, '');
    if (!hash) return '/';
    return hash.startsWith('/') ? hash : `/${hash}`;
}

export default function App() {
    const [path, setPath] = useState(() => {
        const inicial = rutaActual();
        return RUTAS.includes(inicial) ? inicial : '/';
    });
    const [searchResult, setSearchResult] = useState(null);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        const handleHashChange = () => {
            const destino = rutaActual();

            // Permite anclas internas (por ejemplo #main) sin cambiar de página.
            if (!RUTAS.includes(destino)) return;

            setPath(destino);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };

        window.addEventListener('hashchange', handleHashChange);
        return () => window.removeEventListener('hashchange', handleHashChange);
    }, []);

    const handleSearch = async (queryText) => {
        setIsLoading(true);
        setError('');
        setSearchResult(null);

        try {
            setSearchResult(await consultarProyecto(queryText));
        } catch (requestError) {
            setError(
                requestError instanceof Error
                    ? requestError.message
                    : 'No se pudo completar la consulta.'
            );
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col bg-slate-100 font-sans text-slate-900">
            <Navbar currentPath={path} />
            <main id="main" className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8">
                {path === '/rubros' && <RubrosView />}
                {path === '/cobertura' && <CoberturaView />}
                {path === '/fuentes' && <FuentesView />}

                {path === '/' && (
                    <>
                        <SearchBox onSearch={handleSearch} isLoading={isLoading} />
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
                                        <MapView location={searchResult?.ubicacion} />
                                    </div>
                                </div>
                            </div>
                            <div className="lg:col-span-5 flex flex-col">
                                <ResultPanel data={searchResult} />
                            </div>
                        </div>

                        <HomeCards />
                    </>
                )}
            </main>
            <Footer />
        </div>
    );
}
