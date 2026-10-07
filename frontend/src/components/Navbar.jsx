/**
 * @file Navbar.jsx
 * @description Componente de barra de navegación superior con identidad visual del GCBA / SGI TECBA.
 * @author Equipo Frontend - SGI TECBA
 */

import React from 'react';

export const Navbar = () => {
    return (
        <header className="w-full bg-gcba-primary text-white shadow-md sticky top-0 z-50">
            {/* Barra superior de acento institucional */}
            <div className="bg-gcba-dark text-xs py-1 px-4 sm:px-8 flex justify-between items-center border-b border-blue-900/40">
                <span className="font-medium tracking-wide">
                    Gobierno de la Ciudad de Buenos Aires | Convenio Académico TECBA
                </span>
                <span className="hidden sm:inline-block text-gray-300">
                    Sistema de Gestión Inteligente (SGI) — Versión 1.0.0 (MVP)
                </span>
            </div>

            {/* Barra de navegación principal */}
            <div className="max-w-7xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between">
                {/* Logotipo e Identidad */}
                <div className="flex items-center space-x-3">
                    <div className="w-9 h-9 rounded bg-white text-gcba-primary flex items-center justify-center font-bold text-lg shadow-inner">
                        <span>GC</span>
                    </div>
                    <div>
                        <h1 className="font-bold text-base sm:text-lg leading-tight tracking-tight">
                            SGI — TECBA
                        </h1>
                        <p className="text-xs text-blue-200">Gestión Urbana Inteligente</p>
                    </div>
                </div>

                {/* Enlaces de navegación rápidos */}
                <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
                    <a href="#inicio" className="hover:text-blue-200 transition-colors">
                        Inicio
                    </a>
                    <a href="#mapa" className="hover:text-blue-200 transition-colors">
                        Visualizador Geoespacial
                    </a>
                    <span className="bg-emerald-600/30 text-emerald-300 text-xs px-2.5 py-1 rounded-full border border-emerald-500/30">
                        ● Sistema Operativo
                    </span>
                </nav>
            </div>
        </header>
    );
};