import { useState, useEffect } from 'react';
import AsistenteSGI from './AsistenteSGI';

export default function TramitesView({
  direccionBusqueda,
  rubroInicial,
  ubicacion,
  data,
  onBackToConfirmacion,
}) {
  // Asegura que al entrar a la vista la página comience siempre arriba del todo
  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, []);

  const [rubro, setRubro] = useState(rubroInicial || 'Cafetería');
  const direccion = direccionBusqueda || ubicacion?.direccion_normalizada || ubicacion?.direccion_original || 'Calle Corrientes 2500';

  const requisitosBackend = data?.requisitos || [];
  const pasosDefecto = [
    { tramite: 'Comprobar disponibilidad', documentacion_requerida: 'Verificá la zonificación y los códigos urbanísticos permitidos para tu actividad en la parcela.', etapa: 'Etapa inicial' },
    { tramite: 'Tramitar habilitación', documentacion_requerida: 'Iniciá el expediente digital en la plataforma oficial con la documentación respaldatoria.', etapa: 'Etapa de gestión' },
    { tramite: 'Obtener permisos', documentacion_requerida: 'Gestioná los visados especiales de seguridad, salubridad y bomberos correspondientes.', etapa: 'Etapa de permisos' },
    { tramite: 'Validar datos', documentacion_requerida: 'Revisá la consistencia de la superficie, catastro (S-M-P) y planos del local comercial.', etapa: 'Etapa de validación' },
    { tramite: 'Finalizar trámite', documentacion_requerida: 'Obtené la oblea y el certificado definitivo para abrir tus puertas al público.', etapa: 'Etapa final' },
  ];

  const listaPasos = requisitosBackend.length > 0 ? requisitosBackend : pasosDefecto;
  const totalPasos = listaPasos.length;

  const [pasosCompletados, setPasosCompletados] = useState([]);

  const togglePaso = (index) => {
    if (pasosCompletados.includes(index)) {
      setPasosCompletados(pasosCompletados.filter(i => i !== index));
    } else {
      setPasosCompletados([...pasosCompletados, index]);
    }
  };

  const porcentajeProgreso = totalPasos > 0 ? (pasosCompletados.length / totalPasos) * 100 : 0;

  return (
    <div className="w-full max-w-7xl mx-auto px-4 md:px-8 py-4">
      <button 
        onClick={onBackToConfirmacion}
        className="mb-6 bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm"
      >
        ← Volver
      </button>

      <div className="grid grid-cols-1 items-stretch gap-8 lg:grid-cols-12">
        
        {/* COLUMNA IZQUIERDA: 1. Asistente SGI -> 2. Rubro (Sin mapa) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          
          {/* 1. ASISTENTE SGI ARRIBA */}
          <div className="bg-white rounded-xl p-5 shadow-sm border border-slate-200">
            <h3 className="font-bold text-slate-800 text-base mb-1">Asistente SGI</h3>
            <p className="text-sm text-slate-600 mb-4">
              Consultaste en <strong className="text-slate-800">{direccion}</strong>.<br/>
              ¿Qué más te gustaría saber?
            </p>
            <AsistenteSGI
              key={`${rubro}:${direccion}`}
              rubro={rubro}
              direccion={direccion}
              totalPasos={totalPasos}
            />
          </div>

          {/* 2. SECCIÓN DE RUBROS ABAJO */}
          <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Rubro</label>
            <select
              value={rubro}
              onChange={(event) => setRubro(event.target.value)}
              className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-lg text-sm text-slate-700 outline-none"
            >
              {[rubroInicial, 'Cafetería', 'Gastronomía general', 'Comercio minorista']
                .filter((opcion, indice, opciones) => opcion && opciones.indexOf(opcion) === indice)
                .map((opcion) => (
                  <option key={opcion}>{opcion}</option>
                ))}
            </select>
          </div>

        </div>

        {/* COLUMNA DERECHA: Circuito con Banderita Gigante a la Derecha */}
        <div className="lg:col-span-7 bg-white rounded-xl p-8 shadow-sm border border-slate-200">
          <h2 className="text-2xl font-bold text-slate-800 mb-1">Tu camino para abrir el local</h2>
          <p className="text-sm text-slate-500 mb-6">¡Vamos a poner tu proyecto en marcha!</p>

          {/* CIRCUITO CONTINUO CON BANDERITA GIGANTE */}
          <div className="bg-slate-700 text-white border border-slate-800 rounded-2xl p-6 mb-8 shadow-lg">
            <div className="flex justify-between items-center mb-4">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-widest text-yellow-400">Habilitación Inteligente</span>
                <h4 className="text-base font-bold text-white">Circuito de Trámites y Meta</h4>
              </div>
              <span className="text-xs font-bold px-3 py-1 bg-yellow-400/20 text-yellow-300 rounded-full border border-yellow-400/30">
                {pasosCompletados.length} de {totalPasos} completados ({Math.round(porcentajeProgreso)}%)
              </span>
            </div>

            {/* Contenedor SVG dinámico */}
            <div className="w-full overflow-x-auto py-3">
              <svg 
                viewBox={`0 0 ${Math.max(500, totalPasos * 90 + 50)} 145`} 
                className="w-full h-auto min-w-[450px] drop-shadow-md"
              >
                {/* Bloque decorativo inicial */}
                <rect x="25" y="15" width="14" height="35" rx="7" fill="#cbd5e1" opacity="0.4" />

                {/* Renderizado de cada segmento del circuito */}
                {listaPasos.map((_, index) => {
                  const isCompleted = index < pasosCompletados.length;
                  const isLast = index === totalPasos - 1;
                  
                  const segmentWidth = 85;
                  const startX = 30 + index * segmentWidth;
                  const endX = startX + segmentWidth;
                  
                  const startY = index % 2 === 0 ? 85 : 35;
                  const endY = (index + 1) % 2 === 0 ? 85 : 35;

                  const pathD = startY === endY 
                    ? `M ${startX} ${startY} L ${endX} ${endY}`
                    : `M ${startX} ${startY} L ${startX + 35} ${startY} Q ${startX + 42} ${endY}, ${startX + 42} ${endY} L ${endX} ${endY}`;

                  return (
                    <g key={index}>
                      {/* 1. Calle base inactiva */}
                      <path
                        d={pathD}
                        fill="none"
                        stroke="#cbd5e1"
                        strokeWidth="10"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />

                      {/* 2. Calle activa (Amarillo secuencial) */}
                      {isCompleted && (
                        <path
                          d={pathD}
                          fill="none"
                          stroke="#facc15"
                          strokeWidth="10"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      )}

                      {/* Nodo inicial */}
                      {index === 0 && (
                        <g transform={`translate(${startX}, ${startY})`}>
                          <circle r="10" className={isCompleted ? "fill-yellow-400 stroke-emerald-600" : "fill-slate-300 stroke-slate-400"} strokeWidth="2" />
                          <circle r="4.5" className={isCompleted ? "fill-emerald-600" : "fill-slate-500"} />
                        </g>
                      )}

                      {/* Nodo final o Banderita Roja GIGANTE a la Derecha */}
                      <g transform={`translate(${endX}, ${endY})`}>
                        {isLast ? (
                          <g>
                            <circle 
                              r="15" 
                              className={isCompleted ? "fill-yellow-400 stroke-emerald-600 shadow-lg" : "fill-slate-300 stroke-slate-400"} 
                              strokeWidth="3" 
                            />
                            
                            {/* Banderita Roja Vectorial al Doble de Tamaño */}
                            <g transform="translate(30, -35)">
                              <line x1="0" y1="0" x2="0" y2="40" stroke="#ffffff" strokeWidth="4" strokeLinecap="square" />
                              <polygon points="0,0 44,14 0,28" fill="#ef4444" />
                            </g>

                          </g>
                        ) : (
                          // Nodo intermedio estándar
                          <g>
                            <circle 
                              r="10" 
                              className={isCompleted ? "fill-yellow-400 stroke-emerald-600" : "fill-slate-300 stroke-slate-400"} 
                              strokeWidth="2" 
                            />
                            <circle 
                              r="4.5" 
                              className={isCompleted ? "fill-emerald-600" : "fill-slate-500"} 
                            />
                            <text
                              textAnchor="middle"
                              dominantBaseline="central"
                              className="text-[8px] font-extrabold fill-slate-200"
                              dy="-16"
                            >
                              P{index + 1}
                            </text>
                          </g>
                        )}
                      </g>
                    </g>
                  );
                })}
              </svg>
            </div>

            <div className="bg-slate-800/90 border border-slate-600 rounded-xl p-3 text-xs text-slate-300 mt-4 flex items-center gap-2">
              <span>🏁</span>
              <span>¡Completá todos los trámites para encender el circuito por completo y cruzar la bandera roja de meta!</span>
            </div>
          </div>

          {/* LISTADO DE PASOS INTERACTIVOS */}
          <div className="space-y-6">
            {listaPasos.map((req, index) => {
              const estaCompletado = pasosCompletados.includes(index);

              return (
                <div 
                  key={index} 
                  className={`border rounded-xl p-5 transition-all duration-200 ${
                    estaCompletado 
                      ? 'border-emerald-200 bg-emerald-50/40 shadow-sm' 
                      : 'border-slate-100 bg-white hover:border-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-sm text-white ${
                      estaCompletado ? 'bg-emerald-600' : 'bg-slate-700'
                    }`}>
                      {index + 1}
                    </span>
                    <h3 className="font-bold text-slate-800 text-base">{req.tramite || req.titulo}</h3>
                  </div>

                  <p className="text-sm text-slate-600 pl-10 mb-3">
                    {req.documentacion_requerida || req.descripcion || 'Sin descripción detallada para este trámite.'}
                  </p>

                  {req.etapa && (
                    <p className="text-xs text-blue-600 font-semibold pl-10 mb-3">
                      Etapa: {req.etapa} {req.obligatorio ? `· ${req.obligatorio}` : ''}
                    </p>
                  )}

                  <div className="pl-10 flex flex-wrap gap-2 pt-2">
                    <button
                      onClick={() => togglePaso(index)}
                      className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                        estaCompletado
                          ? 'bg-emerald-600 border-emerald-600 text-white hover:bg-emerald-700 shadow-sm'
                          : 'border-slate-300 hover:bg-slate-50 text-slate-700 bg-white'
                      }`}
                    >
                      {estaCompletado ? 'Completado ✓' : 'Marcar como hecho'}
                    </button>

                    {req.link_oficial ? (
                      <a 
                        href={req.link_oficial} 
                        target="_blank" 
                        rel="noreferrer"
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition-colors inline-flex items-center gap-1"
                      >
                        Información oficial ↗
                      </a>
                    ) : (
                      <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition-colors">
                        Iniciar gestión
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

        </div>

      </div>
    </div>
  );
}