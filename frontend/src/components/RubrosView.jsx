/**
 * @file RubrosView.jsx
 * @description Catálogo de rubros y requisitos, más los rubros más habilitados por comuna.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useMemo, useState } from 'react';
import { obtenerRubros, obtenerRequisitos, obtenerRubrosPorComuna } from '../services/api';

const ETAPAS = {
    previo: { titulo: 'Pasos previos', icono: '📋', color: 'bg-sky-50 border-sky-200 text-sky-900' },
    habilitacion: { titulo: 'Habilitación', icono: '🏛️', color: 'bg-amber-50 border-amber-200 text-amber-900' },
    rubro: { titulo: 'Específico del rubro', icono: '🏷️', color: 'bg-violet-50 border-violet-200 text-violet-900' },
    operativo: { titulo: 'En operación', icono: '⚙️', color: 'bg-emerald-50 border-emerald-200 text-emerald-900' },
    tributario: { titulo: 'Tributario', icono: '🧾', color: 'bg-rose-50 border-rose-200 text-rose-900' },
};

const formateador = new Intl.NumberFormat('es-AR');

function normalizar(texto) {
    return (texto || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');
}

export default function RubrosView() {
    const [rubros, setRubros] = useState([]);
    const [filtro, setFiltro] = useState('');
    const [seleccionado, setSeleccionado] = useState('');
    const [requisitos, setRequisitos] = useState(null);
    const [cargandoRubros, setCargandoRubros] = useState(true);
    const [cargandoRequisitos, setCargandoRequisitos] = useState(true);
    const [error, setError] = useState('');
    const [comuna, setComuna] = useState(1);
    const [topRubros, setTopRubros] = useState([]);
    const [cargandoComuna, setCargandoComuna] = useState(true);

    useEffect(() => {
        const control = new AbortController();

        obtenerRubros({ signal: control.signal })
            .then((lista) => {
                if (control.signal.aborted) return;
                setRubros(lista);
                if (lista.length > 0) {
                    setSeleccionado((actual) => actual || lista[0]);
                }
            })
            .catch((err) => {
                if (err.name !== 'AbortError') setError(err.message);
            })
            .finally(() => {
                if (!control.signal.aborted) setCargandoRubros(false);
            });

        return () => control.abort();
    }, []);

    useEffect(() => {
        if (!seleccionado) return undefined;

        const control = new AbortController();

        obtenerRequisitos(seleccionado, { signal: control.signal })
            .then((datos) => {
                if (!control.signal.aborted) setRequisitos(datos);
            })
            .catch((err) => {
                if (err.name !== 'AbortError') {
                    setError(err.message);
                    setRequisitos(null);
                }
            })
            .finally(() => {
                if (!control.signal.aborted) setCargandoRequisitos(false);
            });

        return () => control.abort();
    }, [seleccionado]);

    useEffect(() => {
        const control = new AbortController();

        obtenerRubrosPorComuna(comuna, { limite: 10, signal: control.signal })
            .then((datos) => {
                if (!control.signal.aborted) setTopRubros(datos);
            })
            .catch((err) => {
                if (err.name !== 'AbortError') setTopRubros([]);
            })
            .finally(() => {
                if (!control.signal.aborted) setCargandoComuna(false);
            });

        return () => control.abort();
    }, [comuna]);

    const rubrosFiltrados = useMemo(() => {
        const busqueda = normalizar(filtro.trim());
        if (!busqueda) return rubros;
        return rubros.filter((rubro) => normalizar(rubro).includes(busqueda));
    }, [rubros, filtro]);

    const grupos = useMemo(() => {
        if (!requisitos?.requisitos) return [];
        const orden = Object.keys(ETAPAS);
        const mapa = new Map();

        requisitos.requisitos.forEach((requisito) => {
            const etapa = requisito.etapa || 'habilitacion';
            if (!mapa.has(etapa)) mapa.set(etapa, []);
            mapa.get(etapa).push(requisito);
        });

        return Array.from(mapa.entries()).sort(
            ([a], [b]) => orden.indexOf(a) - orden.indexOf(b)
        );
    }, [requisitos]);

    const maximoComuna = topRubros.reduce((maximo, item) => Math.max(maximo, item.total), 0);

    const handleSeleccionarRubro = (rubro) => {
        if (rubro === seleccionado) return;
        setSeleccionado(rubro);
        setRequisitos(null);
        setError('');
        setCargandoRequisitos(true);
    };

    const handleCambiarComuna = (numero) => {
        if (numero === comuna) return;
        setComuna(numero);
        setTopRubros([]);
        setCargandoComuna(true);
    };

    return (
        <div className="w-full">
            <header className="mb-8">
                <span className="text-xs font-semibold uppercase tracking-wider text-gcba-secondary">
                    Catálogo de actividades
                </span>
                <h1 className="mt-1 text-3xl sm:text-4xl font-bold text-gcba-dark">Rubros y requisitos</h1>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-slate-600">
                    Consultá qué documentación y trámites pide cada actividad. Los requisitos combinan las
                    reglas generales con las específicas del rubro seleccionado.
                </p>
            </header>

            {error && (
                <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
                    <p className="font-semibold">No se pudo cargar la información.</p>
                    <p className="mt-1">{error}</p>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                <aside className="lg:col-span-4 bg-white rounded-xl shadow-sm border border-slate-200 p-5">
                    <div className="flex items-center justify-between gap-2 mb-3">
                        <h2 className="text-sm font-bold text-gcba-dark">Rubros disponibles</h2>
                        <span className="text-xs text-slate-500 bg-slate-100 border border-slate-200 rounded-full px-2 py-0.5">
                            {formateador.format(rubros.length)}
                        </span>
                    </div>

                    <label htmlFor="filtro-rubros" className="sr-only">Buscar rubro</label>
                    <input
                        id="filtro-rubros"
                        type="search"
                        value={filtro}
                        onChange={(event) => setFiltro(event.target.value)}
                        placeholder="Buscar rubro..."
                        className="w-full mb-4 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-700 placeholder-slate-400 focus:border-gcba-primary focus:outline-none focus:ring-2 focus:ring-gcba-primary/20"
                    />

                    {cargandoRubros ? (
                        <p className="text-sm text-slate-500">Cargando rubros…</p>
                    ) : rubrosFiltrados.length === 0 ? (
                        <p className="text-sm text-slate-500">No hay rubros que coincidan con “{filtro}”.</p>
                    ) : (
                        <ul className="space-y-2 max-h-[28rem] overflow-y-auto pr-1">
                            {rubrosFiltrados.map((rubro) => {
                                const activo = rubro === seleccionado;
                                return (
                                    <li key={rubro}>
                                        <button
                                            type="button"
                                            onClick={() => handleSeleccionarRubro(rubro)}
                                            aria-pressed={activo}
                                            className={`w-full text-left rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                                                activo
                                                    ? 'border-gcba-primary bg-gcba-primary text-white shadow-sm'
                                                    : 'border-slate-200 bg-slate-50 text-slate-700 hover:border-gcba-secondary hover:bg-white'
                                            }`}
                                        >
                                            {rubro}
                                        </button>
                                    </li>
                                );
                            })}
                        </ul>
                    )}

                    {rubros.length <= 2 && !cargandoRubros && (
                        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                            Catálogo piloto: la base actual solo tiene requisitos cargados para{' '}
                            {rubros.length} rubro{rubros.length === 1 ? '' : 's'}. Se irán sumando el resto.
                        </p>
                    )}
                </aside>

                <section className="lg:col-span-8 bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    {!seleccionado ? (
                        <p className="text-sm text-slate-600">Elegí un rubro para ver sus requisitos.</p>
                    ) : (
                        <>
                            <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-100 pb-4 mb-5">
                                <div>
                                    <span className="text-xs font-semibold uppercase tracking-wider text-gcba-secondary">
                                        Requisitos
                                    </span>
                                    <h2 className="text-2xl font-bold text-gcba-dark">{seleccionado}</h2>
                                </div>
                                {requisitos && (
                                    <span className="text-xs text-slate-600 bg-slate-100 border border-slate-200 rounded-full px-3 py-1">
                                        {formateador.format(requisitos.total)} requisitos
                                    </span>
                                )}
                            </div>

                            {cargandoRequisitos ? (
                                <p className="text-sm text-slate-500">Cargando requisitos…</p>
                            ) : grupos.length === 0 ? (
                                <p className="text-sm text-slate-500">No hay requisitos cargados para este rubro.</p>
                            ) : (
                                <div className="space-y-6">
                                    {grupos.map(([etapa, items]) => {
                                        const meta = ETAPAS[etapa] || {
                                            titulo: etapa,
                                            icono: '📌',
                                            color: 'bg-slate-50 border-slate-200 text-slate-900',
                                        };
                                        return (
                                            <section key={etapa}>
                                                <h3 className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-bold ${meta.color}`}>
                                                    <span aria-hidden="true">{meta.icono}</span>
                                                    {meta.titulo}
                                                    <span className="font-medium opacity-70">({items.length})</span>
                                                </h3>

                                                <ol className="mt-3 space-y-3">
                                                    {items.map((requisito) => (
                                                        <li key={requisito.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                                                            <div className="flex flex-wrap items-start justify-between gap-2">
                                                                <h4 className="text-sm font-bold text-slate-900">
                                                                    {requisito.orden}. {requisito.tramite}
                                                                </h4>
                                                                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                                                                    requisito.obligatorio === 'Obligatorio'
                                                                        ? 'border-rose-200 bg-rose-50 text-rose-700'
                                                                        : 'border-slate-200 bg-white text-slate-600'
                                                                }`}>
                                                                    {requisito.obligatorio || 'Informativo'}
                                                                </span>
                                                            </div>

                                                            {requisito.documentacion_requerida && (
                                                                <p className="mt-2 text-sm text-slate-700 whitespace-pre-line">
                                                                    {requisito.documentacion_requerida}
                                                                </p>
                                                            )}

                                                            {requisito.aplica_cuando && (
                                                                <p className="mt-2 text-xs text-slate-600">
                                                                    <strong>Aplica cuando:</strong> {requisito.aplica_cuando}
                                                                </p>
                                                            )}

                                                            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                                                                {requisito.organismo && (
                                                                    <span>Organismo: {requisito.organismo}</span>
                                                                )}
                                                                {requisito.link_oficial && (
                                                                    <a
                                                                        href={requisito.link_oficial}
                                                                        target="_blank"
                                                                        rel="noreferrer"
                                                                        className="font-semibold text-gcba-secondary hover:underline"
                                                                    >
                                                                        Ver trámite oficial ↗
                                                                    </a>
                                                                )}
                                                            </div>
                                                        </li>
                                                    ))}
                                                </ol>
                                            </section>
                                        );
                                    })}
                                </div>
                            )}
                        </>
                    )}
                </section>
            </div>

            <section className="mt-8 bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
                    <div>
                        <span className="text-xs font-semibold uppercase tracking-wider text-gcba-secondary">
                            Panorama territorial
                        </span>
                        <h2 className="text-xl font-bold text-gcba-dark">Rubros más habilitados por comuna</h2>
                        <p className="mt-1 text-sm text-slate-600">
                            Ranking de actividades económicas registradas en el padrón de habilitaciones.
                        </p>
                    </div>

                    <div className="flex items-center gap-2">
                        <label htmlFor="comuna-rubros" className="text-xs font-semibold text-slate-600">
                            Comuna
                        </label>
                        <select
                            id="comuna-rubros"
                            value={comuna}
                            onChange={(event) => handleCambiarComuna(Number(event.target.value))}
                            className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-700 focus:border-gcba-primary focus:outline-none focus:ring-2 focus:ring-gcba-primary/20"
                        >
                            {Array.from({ length: 15 }, (_, indice) => indice + 1).map((numero) => (
                                <option key={numero} value={numero}>Comuna {numero}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {cargandoComuna ? (
                    <p className="text-sm text-slate-500">Cargando ranking…</p>
                ) : topRubros.length === 0 ? (
                    <p className="text-sm text-slate-500">No hay datos de rubros para esta comuna.</p>
                ) : (
                    <ol className="space-y-3">
                        {topRubros.map((item, indice) => (
                            <li key={item.rubro}>
                                <div className="flex items-baseline justify-between gap-3 text-sm">
                                    <span className="text-slate-700">
                                        <span className="inline-block w-6 text-xs font-bold text-slate-400">{indice + 1}.</span>
                                        {item.rubro}
                                    </span>
                                    <span className="font-semibold text-slate-900">{formateador.format(item.total)}</span>
                                </div>
                                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                                    <div
                                        className="h-full rounded-full bg-gcba-secondary"
                                        style={{ width: `${maximoComuna > 0 ? (item.total / maximoComuna) * 100 : 0}%` }}
                                    />
                                </div>
                            </li>
                        ))}
                    </ol>
                )}

                <p className="mt-5 text-xs text-slate-500">
                    Los totales provienen de las habilitaciones cargadas y pueden no representar la totalidad
                    de locales activos de la comuna.
                </p>
            </section>
        </div>
    );
}
