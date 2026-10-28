import React from 'react';
import MapView from './MapView';

export default function TramitesView({ direccionBusqueda, onBackToConfirmacion }) {
  return (
    <div className="w-full max-w-7xl mx-auto px-4 md:px-8 py-4">
      <button 
        onClick={onBackToConfirmacion}
        className="mb-6 bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm"
      >
        ← Volver
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* COLUMNA IZQUIERDA: Ubicación y Mapa */}
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

          <div className="bg-white rounded-xl p-5 shadow-sm border border-slate-200 flex flex-col justify-between">
            <p className="text-sm text-slate-600 mb-4">
              Consultaste por <strong className="text-slate-800">Cafetería</strong> en <strong className="text-slate-800">{direccionBusqueda || "Calle Corrientes 2500"}</strong>.<br/>
              ¿Qué más te gustaría saber?
            </p>
            <div className="relative">
              <input 
                type="text" 
                placeholder="Preguntar..." 
                className="w-full bg-slate-50 border border-slate-300 rounded-lg py-2.5 pl-3 pr-10 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button className="absolute right-2 top-2 bg-blue-600 text-white p-1.5 rounded-md text-xs">
                ⬆
              </button>
            </div>
          </div>

        </div>

        {/* COLUMNA DERECHA: Los 4 pasos */}
        <div className="lg:col-span-7 bg-white rounded-xl p-8 shadow-sm border border-slate-200">
          <h2 className="text-2xl font-bold text-slate-800 mb-1">Tu camino para abrir el local</h2>
          <p className="text-sm text-slate-500 mb-6">¡Vamos a poner tu proyecto en marcha!</p>

          <p className="text-sm text-slate-600 mb-6">
            Ya tenés el mapa del camino. Te esperan 4 pasos para organizar las gestiones necesarias para abrir tu local. Avanzá a tu ritmo: acá vas a encontrar qué hacer en cada etapa.
          </p>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 mb-8">
            <div className="flex justify-between text-xs font-bold text-slate-600 mb-2">
              <span>Tu avance</span>
              <span>0 de 4 trámites completados</span>
            </div>
            <div className="w-full bg-slate-200 h-2 rounded-full mb-4 overflow-hidden">
              <div className="bg-blue-600 h-full w-0"></div>
            </div>
            <h4 className="text-sm font-bold text-slate-800 mb-1">¡Empezá tu recorrido!</h4>
            <p className="text-xs text-slate-600 mb-4">Tu primer paso es Comprobar disponibilidad.</p>
            
            <div className="bg-white border border-slate-200 rounded-lg p-3 text-xs text-slate-500">
              <span className="font-bold text-slate-700 block mb-0.5">ℹ️ Sin cuentas: seguimiento local</span>
              Tu avance se guarda solo en este navegador, sin cuenta. Si borrás tus datos o cambiás de dispositivo, no podrás recuperarlo.
            </div>
          </div>

          <div className="space-y-6">
            <div className="border-b border-slate-100 pb-6">
              <div className="flex items-center gap-3 mb-2">
                <span className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm">1</span>
                <h3 className="font-bold text-slate-800 text-base">Comprobar disponibilidad</h3>
              </div>
              <p className="text-sm text-slate-600 pl-10 mb-4">
                En esta descripción del paso se muestran los detalles principales de las acciones que deberá realizar la persona usuaria posteriormente.
              </p>
              <div className="pl-10 flex gap-2">
                <button className="border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Marcar como hecho
                </button>
                <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Iniciar gestión
                </button>
              </div>
            </div>

            <div className="border-b border-slate-100 pb-6">
              <div className="flex items-center gap-3 mb-2">
                <span className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm">2</span>
                <h3 className="font-bold text-slate-800 text-base">Tramitar habilitación</h3>
              </div>
              <p className="text-sm text-slate-600 pl-10 mb-4">
                En esta descripción del paso se muestran los detalles principales de las acciones que deberá realizar la persona usuaria posteriormente.
              </p>
              <div className="pl-10 flex gap-2">
                <button className="border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Marcar como hecho
                </button>
                <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Iniciar gestión
                </button>
              </div>
            </div>

            <div className="border-b border-slate-100 pb-6">
              <div className="flex items-center gap-3 mb-2">
                <span className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm">3</span>
                <h3 className="font-bold text-slate-800 text-base">Obtener permisos</h3>
              </div>
              <p className="text-sm text-slate-600 pl-10 mb-4">
                En esta descripción del paso se muestran los detalles principales de las acciones que deberá realizar la persona usuaria posteriormente.
              </p>
              <div className="pl-10 flex gap-2">
                <button className="border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Marcar como hecho
                </button>
                <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Iniciar gestión
                </button>
              </div>
            </div>

            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm">4</span>
                <h3 className="font-bold text-slate-800 text-base">Validar datos</h3>
              </div>
              <p className="text-sm text-slate-600 pl-10 mb-4">
                En esta descripción del paso se muestran los detalles principales de las acciones que deberá realizar la persona usuaria posteriormente.
              </p>
              <div className="pl-10 flex gap-2">
                <button className="border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Marcar como hecho
                </button>
                <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                  Iniciar gestión
                </button>
              </div>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
}