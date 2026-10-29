/**
 * @file FuentesView.jsx
 * @description Fuentes oficiales, metodología y límites de los datos del SGI TECBA.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useState } from 'react';
import { obtenerHealth } from '../services/api';

const FUENTES = [
    {
        icono: '🏛️',
        titulo: 'Habilitaciones aprobadas',
        detalle: 'Padrón de actividades económicas de la Ciudad, con solicitud, expediente, rubro, ubicación y estado.',
        uso: 'Base principal de la consulta y del ranking de rubros por comuna.',
    },
    {
        icono: '🗺️',
        titulo: 'Fichas EPOK',
        detalle: 'Datos catastrales por parcela: superficie, frente, fondo, pisos y unidades funcionales.',
        uso: 'Contexto territorial de la dirección consultada.',
    },
    {
        icono: '📐',
        titulo: 'Catastro y callejero',
        detalle: 'Normalización de direcciones, sección, manzana y parcela, y asignación de comuna.',
        uso: 'Geolocalización y cruce entre el texto del usuario y la clave SMP.',
    },
    {
        icono: '📚',
        titulo: 'Rubros y requisitos',
        detalle: 'Catálogo de trámites, documentación, organismo y enlace oficial por rubro.',
        uso: 'Checklist de habilitación que se muestra en los resultados.',
    },
    {
        icono: '🧭',
        titulo: 'Código Urbanístico',
        detalle: 'Zonificación y reglas urbanísticas por parcela.',
        uso: 'Previsto para análisis de aptitud; su carga depende de la versión de la base.',
    },
];

const LIMITES = [
    'La cobertura mide si el campo tiene dato, no si el dato es correcto o está vigente.',
    'Los niveles de confianza son indicativos según la fuente y no son probabilidades.',
    'La clave SMP puede faltar o estar incompleta en registros históricos.',
    'El padrón refleja habilitaciones registradas, no la totalidad de locales activos.',
    'El catálogo de requisitos es un piloto y todavía no cubre todos los rubros.',
    'Los resultados no reemplazan la revisión de un profesional ni el trámite oficial.',
];

const formateador = new Intl.NumberFormat('es-AR');

export default function FuentesView() {
    const [salud, setSalud] = useState(null);
    const [errorSalud, setErrorSalud] = useState('');

    useEffect(() => {
        const control = new AbortController();

        obtenerHealth({ signal: control.signal })
            .then((datos) => {
                if (!control.signal.aborted) setSalud(datos);
            })
            .catch((err) => {
                if (err.name !== 'AbortError') setErrorSalud(err.message);
            });

        return () => control.abort();
    }, []);

    const tablas = salud?.tablas || {};
    const indicadores = [
        { etiqueta: 'Habilitaciones', valor: tablas.habilitaciones, nota: 'registros del padrón' },
        { etiqueta: 'Fichas EPOK', valor: tablas.epok_fichas, nota: 'parcelas con datos catastrales' },
        { etiqueta: 'Requisitos', valor: tablas.rubros_requisitos, nota: 'filas del catálogo piloto' },
        { etiqueta: 'Código Urbanístico', valor: tablas.codigo_urbanistico, nota: 'registros cargados' },
    ];

    return (
        <div className="w-full">
            <header className="mb-8">
                <span className="text-xs font-semibold uppercase tracking-wider text-gcba-secondary">
                    Transparencia
                </span>
                <h1 className="mt-1 text-3xl sm:text-4xl font-bold text-gcba-dark">Fuentes y metodología</h1>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-slate-600">
                    De dónde salen los datos, cómo se combinan y qué límites tiene la información que
                    muestra el sistema.
                </p>
            </header>

            <section className="mb-8">
                <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-lg font-bold text-gcba-dark">Datos cargados ahora</h2>
                    <span className="text-xs text-slate-500">Consultado en vivo a la API</span>
                </div>

                {errorSalud ? (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                        No se pudo consultar el estado de la base: {errorSalud}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                        {indicadores.map((indicador) => (
                            <div key={indicador.etiqueta} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                                <p className="text-xs font-medium text-slate-500">{indicador.etiqueta}</p>
                                <p className="mt-1 text-2xl font-bold text-gcba-dark">
                                    {typeof indicador.valor === 'number'
                                        ? formateador.format(indicador.valor)
                                        : '—'}
                                </p>
                                <p className="mt-1 text-xs text-slate-500">{indicador.nota}</p>
                            </div>
                        ))}
                    </div>
                )}

                {salud && tablas.codigo_urbanistico === 0 && (
                    <p className="mt-3 text-xs text-slate-500">
                        El Código Urbanístico figura en 0 porque la versión de la base usada para esta demo
                        es anterior a su integración. El resto de los módulos no depende de esa tabla.
                    </p>
                )}
            </section>

            <section className="mb-8">
                <h2 className="text-lg font-bold text-gcba-dark mb-4">Fuentes de información</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {FUENTES.map((fuente) => (
                        <article key={fuente.titulo} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                            <div className="flex items-start gap-3">
                                <span className="text-2xl" aria-hidden="true">{fuente.icono}</span>
                                <div>
                                    <h3 className="text-sm font-bold text-slate-900">{fuente.titulo}</h3>
                                    <p className="mt-1 text-sm text-slate-600">{fuente.detalle}</p>
                                    <p className="mt-2 text-xs text-slate-500">
                                        <strong className="text-slate-600">Uso en el sistema:</strong> {fuente.uso}
                                    </p>
                                </div>
                            </div>
                        </article>
                    ))}

                    <article className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-5">
                        <h3 className="text-sm font-bold text-slate-900">Datos abiertos de la Ciudad</h3>
                        <p className="mt-1 text-sm text-slate-600">
                            Los conjuntos originales se publican en el portal de datos abiertos de Buenos Aires.
                            El sistema los procesa y los cruza, pero no los modifica en origen.
                        </p>
                        <a
                            href="https://data.buenosaires.gob.ar/"
                            target="_blank"
                            rel="noreferrer"
                            className="mt-3 inline-block text-xs font-semibold text-gcba-secondary hover:underline"
                        >
                            Ir al portal de datos abiertos ↗
                        </a>
                    </article>
                </div>
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start mb-8">
                <section className="lg:col-span-7 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-bold text-gcba-dark">Cómo se arma una respuesta</h2>
                    <ol className="mt-4 space-y-4">
                        {[
                            ['Interpretación', 'Se detecta la actividad y la dirección a partir del texto libre del usuario.'],
                            ['Geolocalización', 'La dirección se normaliza con callejero y catastro para obtener comuna y clave SMP.'],
                            ['Cruce de datos', 'Se buscan habilitaciones, ficha catastral y antecedentes de la parcela.'],
                            ['Requisitos', 'Se combinan las reglas generales con las del rubro detectado.'],
                            ['Cobertura', 'Cada respuesta indica qué campos están completos y con qué confianza.'],
                        ].map(([titulo, detalle], indice) => (
                            <li key={titulo} className="flex gap-3">
                                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gcba-primary text-xs font-bold text-white">
                                    {indice + 1}
                                </span>
                                <div>
                                    <p className="text-sm font-semibold text-slate-900">{titulo}</p>
                                    <p className="text-sm text-slate-600">{detalle}</p>
                                </div>
                            </li>
                        ))}
                    </ol>
                </section>

                <section className="lg:col-span-5 rounded-xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
                    <h2 className="text-lg font-bold text-amber-950">Alcances y límites</h2>
                    <ul className="mt-4 space-y-2.5">
                        {LIMITES.map((limite) => (
                            <li key={limite} className="flex gap-2 text-sm text-amber-950">
                                <span aria-hidden="true" className="mt-0.5">•</span>
                                <span>{limite}</span>
                            </li>
                        ))}
                    </ul>
                </section>
            </div>

            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-bold text-gcba-dark">Versión y reproducibilidad</h2>
                <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Fixture demo</p>
                        <p className="mt-1 font-bold text-slate-900">Versión 1.0.0</p>
                        <p className="mt-1 text-slate-600">Datos sanitizados y versionados en el repositorio, sin LFS.</p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Restauración</p>
                        <p className="mt-1 font-bold text-slate-900">Script verificado</p>
                        <p className="mt-1 text-slate-600">
                            El dump se restaura en PostgreSQL 18 y se validan los conteos por tabla.
                        </p>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Privacidad</p>
                        <p className="mt-1 font-bold text-slate-900">Datos pseudonimizados</p>
                        <p className="mt-1 text-slate-600">
                            La demo reemplaza solicitud, expediente, razón social y partida matriz.
                        </p>
                    </div>
                </div>

                <p className="mt-4 text-xs text-slate-500">
                    Para el detalle técnico, consultá la documentación del repositorio en{' '}
                    <a
                        href="https://github.com/equipo20-innovalab/sgi-tecba"
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold text-gcba-secondary hover:underline"
                    >
                        equipo20-innovalab/sgi-tecba ↗
                    </a>
                    .
                </p>
            </section>
        </div>
    );
}
