/**
 * @file SearchBox.jsx
 * @description Componente de entrada para consultas urbanas con soporte de texto, 
 * botón de limpieza condicional (optimizado para touch y desktop) y atajo de teclado Escape.
 * @author Equipo Frontend - SGI TECBA
 */

import { useState, useRef } from 'react';

export const SearchBox = ({ onSearch, isLoading = false }) => {
    const [query, setQuery] = useState('');
    const [isListening, setIsListening] = useState(false);
    
    // Referencia para controlar el foco del input al limpiar o presionar Escape
    const inputRef = useRef(null);

    /**
     * Maneja el envío del formulario de búsqueda.
     */
    const handleSubmit = (e) => {
        e.preventDefault();
        if (!query.trim() || isLoading) return;
        if (onSearch) {
            onSearch(query);
        }
    };

    /**
     * Limpia el texto de la caja de búsqueda y devuelve el foco al input.
     */
    const handleClear = () => {
        setQuery('');
        inputRef.current?.focus();
    };

    /**
     * Detecta eventos de teclado en el input (ej. tecla Escape para limpiar).
     */
    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            setQuery('');
            inputRef.current?.blur(); // Quita el foco opcionalmente al presionar Escape
        }
    };

    /**
     * Simulación de búsqueda por voz (futura integración).
     */
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
                {/* Campo de Texto Transparente con input, icono de búsqueda y botón de borrado */}
                <div className="relative flex-1 w-full flex items-center">
                    <span className="pl-4 text-slate-400 text-lg pointer-events-none">
                        🔍
                    </span>
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ej: Quiero abrir una cafetería en Corrientes al 2500"
                        className="w-full bg-transparent border-none py-3 pl-4 pr-12 text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-0 text-base"
                    />

                    {/* Botón de limpieza condicional ("X"): Aparece solo si hay texto escrito */}
                    {query.length > 0 && (
                        <button
                            type="button"
                            onClick={handleClear}
                            className="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
                            aria-label="Borrar texto de búsqueda"
                        >
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2}
                                stroke="currentColor"
                                className="w-4 h-4"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    )}
                </div>

                {/* Contenedor de Botones (Voz + Buscar) */}
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
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth={2}
                            stroke="currentColor"
                            className="w-4 h-4 text-slate-500"
                        >
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