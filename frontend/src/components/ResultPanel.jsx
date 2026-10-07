/**
 * @file ResultPanel.jsx
 * @description Panel de visualización de resultados y viabilidad urbana para la consulta del usuario.
 * @author Equipo Frontend - SGI TECBA
 */

import React from 'react';

export const ResultPanel = ({ data }) => {
    // Datos por defecto para estructurar el MVP si aún no hay una consulta activa
    const defaultData = {
        address: 'Av. Corrientes 1234, CABA',
        district: 'R2A (Residencial / Comercial Mixto)',
        landArea: '240 m²',
        maxHeight: '12 metros (Planta baja + 3 pisos)',
        viabilityStatus: 'Apto con Condicionantes',
        activity: 'Gastronomía menor / Cafetería sin elaboración compleja',
        observaciones: 'Requiere verificación de factor de ocupación total (FOT) y ventilación reglamentaria según Código Urbanístico.'
    };

    const result = data || defaultData;

    return (
        <div className="w-full bg-white rounded-xl shadow-lg border border-slate-200 p-6 mb-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-slate-100 pb-4 mb-4 gap-2">
                <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-gcba-secondary">
                        Resultado de Análisis Urbano
                    </span>
                    <h3 className="text-lg font-bold text-gcba-dark">{result.address}</h3>
                </div>
                <span className="bg-amber-100 text-amber-800 text-xs font-medium px-3 py-1 rounded-full border border-amber-200">
                    ● {result.viabilityStatus}
                </span>
            </div>

            {/* Grilla de Métricas Urbanas */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Zonificación</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">{result.district}</p>
                </div>
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Superficie Estimada</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">{result.landArea}</p>
                </div>
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Altura Máxima Permitida</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">{result.maxHeight}</p>
                </div>
            </div>

            {/* Viabilidad Comercial y Observaciones */}
            <div className="bg-blue-50/50 border border-blue-100 rounded-lg p-4">
                <h4 className="text-sm font-bold text-gcba-primary mb-1">
                    Actividad Evaluada: {result.activity}
                </h4>
                <p className="text-xs text-slate-600 leading-relaxed">
                    {result.observaciones}
                </p>
            </div>
        </div>
    );
};