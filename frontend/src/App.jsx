/**
 * @file App.jsx
 * @description Componente raíz de la aplicación SGI TECBA. Integra la arquitectura modular de la interfaz
 * y el ruteo por hash entre el inicio, rubros, cobertura y fuentes.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { ConsultaJourney } from './components/ConsultaJourney';
import RubrosView from './components/RubrosView';
import CoberturaView from './components/CoberturaView';
import FuentesView from './components/FuentesView';
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
    const [searchQuery, setSearchQuery] = useState('');
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
        setSearchQuery(queryText);
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
                    <ConsultaJourney
                        data={searchResult}
                        direccionBusqueda={searchQuery}
                        error={error}
                        isLoading={isLoading}
                        onSearch={handleSearch}
                    />
                )}
            </main>
            <Footer />
        </div>
    );
}
