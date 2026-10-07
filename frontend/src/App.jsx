/**
 * @file App.jsx
 * @description Componente raíz de la aplicación SGI TECBA. Integra la arquitectura modular de la interfaz.
 * @author Equipo Frontend - SGI TECBA
 */

import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { SearchBox } from './components/SearchBox';
import { ResultPanel } from './components/ResultPanel';
import MapView from './components/MapView';
import { Footer } from './components/Footer';

export default function App() {
  // Estado para manejar los datos dinámicos de la consulta urbana
  const [searchResult, setSearchResult] = useState(null);

  const handleSearch = (queryText) => {
    // Simulamos la respuesta de la búsqueda (preparado para conectar con FastAPI en la siguiente fase)
    console.log("Procesando consulta urbana para:", queryText);
    setSearchResult({
      address: queryText,
      district: 'R2A (Residencial / Comercial Mixto)',
      landArea: '280 m²',
      maxHeight: '12 metros (Planta baja + 3 pisos)',
      viabilityStatus: 'Apto Comercial',
      activity: 'Comercio minorista y gastronomía sin molestas',
      observaciones: 'Zonificación compatible según parámetros preliminares del Código Urbanístico de la Ciudad.'
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 font-sans text-slate-900">
      {/* 1. Barra de Navegación Institucional */}
      <Navbar />

      {/* 2. Contenedor Principal */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8">
        {/* Módulo de Búsqueda y Consulta */}
        <SearchBox onSearch={handleSearch} />

        {/* Grilla Principal de Trabajo (Mapa + Resultados) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Columna Izquierda: Visor Cartográfico (Leaflet) */}
          <div className="lg:col-span-7 flex flex-col">
            <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-4 h-full flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-gcba-dark flex items-center gap-2">
                  <span>📍</span> Visor Geográfico Urbano
                </h3>
                <span className="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
                  OpenStreetMap / Leaflet
                </span>
              </div>
              <div className="flex-1 min-h-[400px]">
                <MapView />
              </div>
            </div>
          </div>

          {/* Columna Derecha: Panel de Resultados y Viabilidad */}
          <div className="lg:col-span-5 flex flex-col">
            <ResultPanel data={searchResult} />
          </div>
        </div>
      </main>

      {/* 3. Pie de Página Institucional */}
      <Footer />
    </div>
  );
}