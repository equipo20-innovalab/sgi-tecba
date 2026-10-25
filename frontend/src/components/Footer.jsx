/**
 * @file Footer.jsx
 * @description Componente de pie de página institucional adaptado al diseño de Figma (Obelisco v2) para el SGI TECBA.
 * @author Equipo Frontend - SGI TECBA
 */

import React from 'react';

export const Footer = () => {
    return (
        <footer className="w-full bg-[#031b26] text-slate-300 mt-auto border-t border-slate-800">
            <div className="max-w-7xl mx-auto px-4 sm:px-8 py-10">

                {/* 1. Sección de Teléfonos Útiles */}
                <div className="mb-8 pb-8 border-b border-slate-800">
                    <h4 className="font-bold text-white text-sm mb-3">Teléfonos útiles</h4>
                    <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs mb-3">
                        <a href="tel:102" className="hover:underline text-slate-200"><strong>102</strong> - Niñez y Adolescencia</a>
                        <a href="tel:103" className="hover:underline text-slate-200"><strong>103</strong> - Emergencias</a>
                        <a href="tel:107" className="hover:underline text-slate-200"><strong>107</strong> - SAME</a>
                        <a href="tel:911" className="hover:underline text-slate-200"><strong>911</strong> - Policía</a>
                        <a href="tel:144" className="hover:underline text-slate-200"><strong>144</strong> - Violencia de Género</a>
                        <a href="tel:147" className="hover:underline text-slate-200"><strong>147</strong> - Atención Ciudadana</a>
                    </div>
                    <a href="#telefonos" className="text-xs text-cyan-400 hover:underline font-semibold">
                        Ver todos los teléfonos
                    </a>
                </div>

                {/* 2. Sección de Redes de la Ciudad */}
                <div className="mb-10 pb-8 border-b border-slate-800">
                    <h4 className="font-bold text-white text-sm mb-3">Redes de la Ciudad</h4>
                    <div className="flex flex-wrap gap-x-6 gap-y-3 text-xs items-center">
                        <a href="#facebook" className="hover:text-white transition-colors flex items-center gap-2 text-slate-300">
                            <span>🌐</span> Facebook
                        </a>
                        <a href="#instagram" className="hover:text-white transition-colors flex items-center gap-2 text-slate-300">
                            <span>📸</span> Instagram
                        </a>
                        <a href="#x" className="hover:text-white transition-colors flex items-center gap-2 text-slate-300">
                            <span>✏️</span> X
                        </a>
                        <a href="#youtube" className="hover:text-white transition-colors flex items-center gap-2 text-slate-300">
                            <span>▶️</span> YouTube
                        </a>
                        <a href="#linkedin" className="hover:text-white transition-colors flex items-center gap-2 text-slate-300">
                            <span>💼</span> LinkedIn
                        </a>
                        <a href="#tiktok" className="hover:text-white transition-colors flex items-center gap-2 text-slate-300">
                            <span>🎵</span> TikTok
                        </a>
                        <a href="#pinterest" className="hover:text-white transition-colors flex items-center gap-2 text-slate-300">
                            <span>🖼️</span> Pinterest
                        </a>
                    </div>
                </div>

                {/* 3. Bloque Institucional y Logotipos */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8 pb-8 border-b border-slate-800">
                    <div className="flex items-center gap-6">
                        {/* Logotipo oficial GCBA simulado/adaptado con assets */}
                        <div className="flex items-center space-x-2">
                            <span className="font-bold tracking-tight text-white text-sm">Buenos Aires Ciudad</span>
                        </div>
                    </div>

                    {/* Enlaces legales obligatorios según Figma */}
                    <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
                        <a href="#boletin" className="hover:underline text-slate-300">Boletín Oficial</a>
                        <a href="#terminos" className="hover:underline text-slate-300">Términos y condiciones</a>
                        <a href="#privacidad" className="hover:underline text-slate-300">Política de privacidad</a>
                        <a href="#oficios" className="hover:underline text-slate-300">Oficios judiciales</a>
                        <a href="#transparencia" className="hover:underline text-slate-300">Transparencia</a>
                    </div>
                </div>

                {/* 4. Copyright y Licencia */}
                <div className="text-[11px] text-slate-500 leading-relaxed">
                    <p>Los contenidos de buenosaires.gob.ar están licenciados bajo Creative Commons Reconocimiento 2.5 Argentina License.</p>
                    <p className="mt-1">© 2026 SGI TECBA — Convenio Académico de Transformación Digital Urbana.</p>
                </div>
            </div>
        </footer>
    );
};