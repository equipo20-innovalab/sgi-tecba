/**
 * @file SearchBox.jsx
 * @description Componente de entrada para consultas urbanas con soporte de texto y futura integración de voz.
 * @author Equipo Frontend - SGI TECBA
 */

import React, { useState } from 'react';

export const SearchBox = ({ onSearch }) => {
    const [query, setQuery] = useState('');
    const [isListening, setIsListening] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!query.trim()) return;
        // Si pasamos una función por props, la ejecutamos con la consulta
        if (onSearch) {
            onSearch(query);
        }
    };

    const handleVoiceSearch = () => {
        // Simulación de interacción por voz para la estructura del MVP
        setIsListening(true);
        setTimeout(() => {
            setQuery('Evaluación de local comercial en Av. Corrientes');
            setIsListening(false);
        }, 2000);
    };

    return (
        <div className="w-full bg-white rounded-xl shadow-lg border border-slate-200 p-6 mb-6">
            <div className="mb-4">
                <h2 className="text-lg font-bold text-gcba-dark">Consulta Inteligente de Zonificación</h2>
                <p className="text-sm text-slate-600">
                    Ingrese una dirección, distrito o tipo de actividad comercial para verificar su viabilidad en la Ciudad.
                </p>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
                {/* Campo de Texto Principal */}
                <div className="relative flex-1">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-slate-400">
                        🔍
                    </span>
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Ej: Apto cafetería en Palermo, zonificación R2A..."
                        className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gcba-primary focus:bg-white transition-all text-sm"
                    />
                </div>

                {/* Botón de Comandos por Voz (Funcionalidad Futura) */}
                <button
                    type="button"
                    onClick={handleVoiceSearch}
                    title="Consulta por voz (Próximamente)"
                    className={`px-4 py-3 rounded-lg border font-medium text-sm flex items-center justify-center gap-2 transition-all ${isListening
                            ? 'bg-red-50 text-red-600 border-red-300 animate-pulse'
                            : 'bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200'
                        }`}
                >
                    <span>🎙️</span>
                    <span className="hidden sm:inline">{isListening ? 'Escuchando...' : 'Voz'}</span>
                </button>

                {/* Botón de Envío de Consulta */}
                <button
                    type="submit"
                    className="bg-gcba-primary hover:bg-blue-900 text-white font-medium px-6 py-3 rounded-lg transition-colors shadow-sm text-sm flex items-center justify-center"
                >
                    Consultar
                </button>
            </form>
        </div>
    );
};