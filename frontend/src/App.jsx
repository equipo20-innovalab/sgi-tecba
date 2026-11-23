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

    const [rubroBusqueda, setRubroBusqueda] = useState('');

    const [error, setError] = useState('');

    const [isLoading, setIsLoading] = useState(false);



    useEffect(() => {

        const handleHashChange = () => {

            const destino = rutaActual();

            if (!RUTAS.includes(destino)) return;

            setPath(destino);

            window.scrollTo({ top: 0, behavior: 'smooth' });

        };

        window.addEventListener('hashchange', handleHashChange);

        return () => window.removeEventListener('hashchange', handleHashChange);

    }, []);


    const handleSearch = async ({ rubro, direccion }) => {

        setIsLoading(true);

        setRubroBusqueda(rubro);

        setSearchQuery(direccion);

        setError('');

        setSearchResult(null);



        try {

            setSearchResult(await consultarProyecto({ rubro, direccion }));

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

        <div
            className="min-h-screen flex flex-col bg-slate-100 font-sans text-slate-900"
            style={{
                backgroundImage:
                    'linear-gradient(180deg, rgba(214, 228, 246, 0.35) 0%, rgba(214, 228, 246, 0.45) 50%, rgba(214, 228, 246, 0.62) 100%), url(/ba3d.webp)',
                // En esta imagen los techos están al ~24% de la altura. Se
                // corre el fondo hacia arriba para que el obelisco asome por
                // encima del mapa urbano y quede visible en la zona del título.
                backgroundSize: 'auto 130%',
                backgroundPosition: 'center calc(175px - 42vh)',
                backgroundAttachment: 'fixed',
                backgroundRepeat: 'no-repeat',
            }}
        >

            <Navbar currentPath={path} />

            <main id="main" className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8">

                {path === '/rubros' && <RubrosView />}
                {path === '/cobertura' && <CoberturaView />}
                {path === '/fuentes' && <FuentesView />}
                {path === '/' && (

                    <ConsultaJourney

                        data={searchResult}

                        direccionBusqueda={searchQuery}

                        rubroBusqueda={rubroBusqueda}

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

