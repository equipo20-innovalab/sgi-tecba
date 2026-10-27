/**
 * @file App.jsx
 * @description Componente raíz de la aplicación SGI TECBA. Integra la arquitectura modular de la interfaz.
 * @author Equipo Frontend - SGI TECBA
 */

import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import ConfirmacionView from './components/ConfirmacionView';
import TramitesView from './components/TramitesView';

export default function App() {
  const [busqueda, setBusqueda] = useState('');
  const [pasoActual, setPasoActual] = useState('home'); // 'home' | 'requisitos' | 'tramites'

  const handleSearch = (e) => {
    e.preventDefault();
    setPasoActual('requisitos'); // Al buscar, pasa a la vista de requisitos
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 font-sans text-slate-800">
      {/* 1. Navbar oficial */}
      <Navbar />

      {/* 2. Contenido Principal Dinámico */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-10 flex flex-col items-center">
        {pasoActual === 'home' && (
          /* --- VISTA 1: HOME COMPLETO --- */
          <>
            {/* Título y Subtítulo */}
            <h1 className="text-2xl md:text-3xl font-bold text-slate-800 mb-2 text-center">
              Sistema de Gestión Inteligente
            </h1>
            <p className="text-slate-600 mb-8 text-center text-sm md:text-base">
              Los trámites que necesitas para realizar tu actividad, en un solo lugar.
            </p>

            {/* Buscador Central */}
            <form onSubmit={handleSearch} className="w-full max-w-2xl bg-white p-2 rounded-xl shadow-md flex items-center mb-12">
              <span className="pl-3 text-slate-400">🔍</span>
              <input 
                type="text" 
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="¿En qué te podemos ayudar? Ej: Apto cafetería en Palermo, zonificación..."
                className="w-full px-3 py-2 outline-none text-slate-700 text-sm md:text-base"
              />
              <button 
                type="submit" 
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-lg font-medium transition-colors text-sm md:text-base"
              >
                Buscar
              </button>
            </form>

            {/* Tarjetas Destacadas */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full mb-16">
              <div className="bg-white rounded-xl shadow-md overflow-hidden border border-slate-200 hover:shadow-lg transition-shadow cursor-pointer flex flex-col">
                <div className="h-40 w-full relative bg-slate-200 overflow-hidden">
                  <img src="" alt="" className="w-full h-full object-cover" />
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-slate-800 text-lg mb-1">¿Quéres abrir tu negocio?</h3>
                  <p className="text-slate-500 text-sm">Conocé los pasos.</p>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-md overflow-hidden border border-slate-200 hover:shadow-lg transition-shadow cursor-pointer flex flex-col">
                <div className="h-40 w-full relative bg-slate-200 overflow-hidden">
                  <img src="" alt="" className="w-full h-full object-cover" />
                </div>
                <div className="p-5">
                  <h3 className="font-bold text-slate-800 text-lg mb-1">Gestioná tu habilitación</h3>
                  <p className="text-slate-500 text-sm">Consultá el estado de tus trámites.</p>
                </div>
              </div>
            </div>

            {/* Sección: ¿Cómo funciona? */}
            <section className="w-full mb-16">
              <h2 className="text-xl font-bold text-slate-800 mb-8">¿Cómo funciona?</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="flex flex-col">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm">1</span>
                    <h4 className="font-bold text-slate-800">Contanos que queres hacer</h4>
                  </div>
                  <p className="text-slate-500 text-sm pl-10">Escribí la actividad que quieras realizar.</p>
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm">2</span>
                    <h4 className="font-bold text-slate-800">Indicá dónde</h4>
                  </div>
                  <p className="text-slate-500 text-sm pl-10">Seleccioná una dirección o zona.</p>
                </div>
                <div className="flex flex-col">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-sm">3</span>
                    <h4 className="font-bold text-slate-800">Te mostramos que necesitas</h4>
                  </div>
                  <p className="text-slate-500 text-sm pl-10">Trámites, requisitos, documentación y pasos.</p>
                </div>
              </div>
            </section>

            {/* Sección: Gestiones frecuentes */}
            <section className="w-full mb-8">
              <h2 className="text-xl font-bold text-slate-800 mb-6">Gestiones frecuentes</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col items-center text-center hover:shadow-md transition-shadow cursor-pointer">
                  <span className="text-2xl mb-2">📄</span>
                  <span className="text-sm font-medium text-slate-700">Habilitar un comercio.</span>
                </div>
                <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col items-center text-center hover:shadow-md transition-shadow cursor-pointer">
                  <span className="text-2xl mb-2">🏠</span>
                  <span className="text-sm font-medium text-slate-700">Iniciar una actividad desde casa.</span>
                </div>
                <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col items-center text-center hover:shadow-md transition-shadow cursor-pointer">
                  <span className="text-2xl mb-2">🏗️</span>
                  <span className="text-sm font-medium text-slate-700">Realizar una obra.</span>
                </div>
                <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 flex flex-col items-center text-center hover:shadow-md transition-shadow cursor-pointer">
                  <span className="text-2xl mb-2">⋯</span>
                  <span className="text-sm font-medium text-slate-700">Otras gestiones.</span>
                </div>
              </div>
            </section>
          </>
        )}

        {pasoActual === 'requisitos' && (
          /* --- VISTA 2: REQUISITOS --- */
          <ConfirmacionView 
            direccionBusqueda={busqueda} 
            onBack={() => setPasoActual('home')} 
            onVerTramites={() => setPasoActual('tramites')} 
          />
        )}

        {pasoActual === 'tramites' && (
          /* --- VISTA 3: LOS 4 PASOS DE TRÁMITES --- */
          <TramitesView 
            direccionBusqueda={busqueda} 
            onBackToConfirmacion={() => setPasoActual('requisitos')} 
          />
        )}
      </main>

      {/* 3. Footer */}
      <Footer />
    </div>
  );
}