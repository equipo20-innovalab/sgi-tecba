import React from 'react';
import MapView from './MapView';

export default function ConfirmacionView({ direccionBusqueda, onBack, onVerTramites }) {
  return (
    <div className="w-full max-w-7xl mx-auto px-4 md:px-8 py-4">
      {/* Botón Volver */}
      <button 
        onClick={onBack}
        className="mb-6 bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm"
      >
        ← Volver
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* COLUMNA IZQUIERDA: Ubicación, Mapa y Métricas */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          
          <div className="bg-white rounded-xl p-5 shadow-sm border border-slate-200">
            <h3 className="font-bold text-slate-800 text-base mb-1">Ubicación</h3>
            <p className="text-sm text-slate-600 mb-3">
              {direccionBusqueda ? direccionBusqueda : "Calle Corrientes 2500"}
            </p>
            
            {/* Contenedor del Mapa */}
            <div className="h-48 w-full mb-4">
              <MapView direccion={direccionBusqueda || "Calle Corrientes 2500"} />
            </div>

            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg text-sm font-medium transition-colors">
              Cambiar ubicación
            </button>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Rubro</label>
            <select className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-700 outline-none">
              <option>Cafetería</option>
              <option>Gastronomía general</option>
              <option>Comercio minorista</option>
            </select>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 flex items-start gap-3">
            <span className="text-xl">ℹ️</span>
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tiempo estimado</h4>
              <p className="text-base font-bold text-slate-800">20 a 45 días.</p>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 flex items-start gap-3">
            <span className="text-xl">ℹ️</span>
            <div>
              <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Disponibilidad de turnos</h4>
              <p className="text-base font-bold text-slate-800">A 15 días.</p>
            </div>
          </div>

        </div>

        {/* COLUMNA DERECHA: Requisitos */}
        <div className="lg:col-span-7 bg-white rounded-xl p-8 shadow-sm border border-slate-200">
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Requisitos para la gestión</h2>
          
          <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-6 rounded-r-lg">
            <p className="text-xs font-bold text-amber-800 uppercase">Tu proyecto empieza acá</p>
            <p className="text-sm text-amber-900">
              Antes de abrir las puertas de tu local, vamos a revisar juntos qué necesitás para ponerlo en marcha.
            </p>
          </div>

          <p className="text-sm text-slate-600 mb-6 leading-relaxed">
            Cada local es diferente. Estos son los requisitos que tenés que cumplir según la actividad y la ubicación que nos compartiste. Revisalos con tranquilidad: te vamos a guiar paso a paso para que sepas cómo seguir.
          </p>

          <div className="space-y-4 mb-8">
            <div className="flex items-start gap-3 text-sm text-slate-700">
              <span className="text-blue-600 font-bold">•</span>
              <p>Debe tener una superficie total que no supere los 200 m2.</p>
            </div>
            <div className="flex items-start gap-3 text-sm text-slate-700">
              <span className="text-blue-600 font-bold">•</span>
              <p>No debe comercializar explosivos, inflamables ni productos medicinales sin envasar.</p>
            </div>
            <div className="flex items-start gap-3 text-sm text-slate-700">
              <span className="text-blue-600 font-bold">•</span>
              <p>No debe estar ubicado en galerías, centros comerciales, paseos de compras, mercados o patios gastronómicos, estación de subte, tren, aeropuerto o en otros complejos comerciales.</p>
            </div>
            <div className="flex items-start gap-3 text-sm text-slate-700">
              <span className="text-blue-600 font-bold">•</span>
              <p>No debe estar en áreas especiales por ser históricas, culturales, ambientales, o tener usos específicos establecidos en el Código Urbanístico.</p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-slate-100">
            <button 
              onClick={onVerTramites}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-xl transition-colors text-center shadow-sm"
            >
              Ver trámites
            </button>
            <button 
              onClick={onBack}
              className="flex-1 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium py-3 px-4 rounded-xl transition-colors text-center shadow-sm"
            >
              Realizar otra consulta
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}