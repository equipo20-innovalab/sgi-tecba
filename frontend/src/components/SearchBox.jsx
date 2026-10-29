/**
 * @file SearchBox.jsx
 * @description Componente de entrada para consultas urbanas con soporte de texto y futura integración de voz.
 * @author Equipo Frontend - SGI TECBA
 */

import { useState } from 'react';

export const SearchBox = ({ onSearch, isLoading = false }) => {
    const [query, setQuery] = useState('');
    const [isListening, setIsListening] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!query.trim() || isLoading) return;
        if (onSearch) {
            onSearch(query);
        }
    };

    const handleVoiceSearch = () => {
        setIsListening(true);
        setTimeout(() => {
            setQuery('Evaluación de local comercial en Av. Corrientes');
            setIsListening(false);
        }, 2000);
    };

    return (
        <div className="w-full max-w-4xl mx-auto py-12 px-4">
            <div className="text-center mb-10 space-y-4">
                <h2 className="text-3xl sm:text-4xl font-bold text-slate-800">
                    Sistema de Gestión Inteligente
                </h2>
                <p className="text-lg text-slate-600">
                    Los trámites que necesitás para realizar tu actividad, en un solo lugar.
                </p>
            </div>

            {/* Contenedor unificado del buscador (Formulario) */}
            <form 
                onSubmit={handleSubmit} 
                className="flex flex-col sm:flex-row items-center bg-white p-2 rounded-2xl shadow-md gap-2"
            >
                {/* Campo de Texto Transparente */}
                <div className="relative flex-1 w-full flex items-center">
                    <span className="pl-4 text-slate-400 text-lg pointer-events-none">
                        🔍
                    </span>
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="¿En qué te podemos ayudar? Ej: Apto cafetería en Palermo, zonificación R2A..."
                        className="w-full bg-transparent border-none py-3 px-4 text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-0 text-base"
                    />
                </div>

                {/* Contenedor de Botones (Voz(futuro) + Buscar) */}
                <div className="flex w-full sm:w-auto gap-2 px-2 pb-2 sm:p-0 sm:pr-2">
                    <button
                        type="button"
                        onClick={handleVoiceSearch}
                        disabled={isListening || isLoading}
                        title="Consulta por voz (Próximamente)"
                        className={`flex-1 sm:flex-none px-4 py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2 transition-all ${
                            isListening
                                ? 'bg-red-50 text-red-600 animate-pulse'
                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                    >       
                            <svg /* cambie el inoco por uno de tailwind */
                            xmlns="http://www.w3.org/2000/svg" 
                              fill="none" 
                              viewBox="0 0 24 24" 
                              strokeWidth={2} 
                              stroke="currentColor" 
                              className="w-4 h-4 text-slate-500" >
                             <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
                            </svg>
                        <span>{isListening ? 'Escuchando...' : 'Voz'}</span>
                    </button>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="flex-1 sm:flex-none bg-gcba-primary hover:bg-blue-900 disabled:cursor-wait disabled:opacity-60 text-white font-medium px-8 py-3 rounded-xl transition-colors text-sm"
                    >
                        {isLoading ? 'Consultando...' : 'Buscar'}
                    </button>
                </div>
            </form>
        </div>
    );
};