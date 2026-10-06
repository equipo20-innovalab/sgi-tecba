/**
 * @file Footer.jsx
 * @description Componente de pie de página institucional para el sistema SGI TECBA.
 * @author Equipo Frontend - SGI TECBA
 */

import React from 'react';

export const Footer = () => {
    return (
        <footer className="w-full bg-gcba-dark text-slate-300 mt-auto border-t border-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-8 py-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    {/* Columna de identidad */}
                    <div>
                        <h4 className="font-bold text-white text-sm mb-2">SGI — TECBA</h4>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            Sistema de Gestión Inteligente desarrollado en el marco del convenio académico de desarrollo de software y transformación digital urbana.
                        </p>
                    </div>

                    {/* Columna de enlaces rápidos */}
                    <div>
                        <h5 className="font-semibold text-white text-xs mb-2 uppercase tracking-wider">Enlaces de Interés</h5>
                        <ul className="space-y-1 text-xs">
                            <li>
                                <a href="#inicio" className="hover:text-white transition-colors">Portal Institucional</a>
                            </li>
                            <li>
                                <a href="#mapa" className="hover:text-white transition-colors">Visor Geográfico Urbano</a>
                            </li>
                            <li>
                                <a href="#terminos" className="hover:text-white transition-colors">Términos y Condiciones</a>
                            </li>
                        </ul>
                    </div>

                    {/* Columna de soporte */}
                    <div>
                        <h5 className="font-semibold text-white text-xs mb-2 uppercase tracking-wider">Soporte Técnico</h5>
                        <p className="text-xs text-slate-400 leading-relaxed">
                            Equipo Frontend — SGI TECBA<br />
                            Buenos Aires, Argentina
                        </p>
                    </div>
                </div>

                {/* Línea de copyright y disclaimer */}
                <div className="border-t border-slate-800 pt-4 flex flex-col sm:flex-row justify-between items-center text-xs text-slate-500">
                    <p>© 2026 SGI TECBA. Todos los derechos reservados.</p>
                    <p className="mt-2 sm:mt-0">Basado en estándares y directrices de portales de la Ciudad.</p>
                </div>
            </div>
        </footer>
    );
};