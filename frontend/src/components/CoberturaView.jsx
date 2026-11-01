/**
 * @file CoberturaView.jsx
 * @description Panel de cobertura y calidad de los datos del padrón de habilitaciones.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useMemo, useState } from 'react';
import { obtenerCobertura, obtenerHabilitacionesPorComuna } from '../services/api';

const ETIQUETAS_CAMPOS = {
    solicitud: 'Número de solicitud',
    tipo_tramite: 'Tipo de trámite',
    tipo_expediente: 'Tipo de expediente',
    subtipo_expediente: 'Subtipo de expediente',
    fecha_habilitacion: 'Fecha de habilitación',
    numero_expediente: 'Número de expediente',
    codigo_rubro: 'Código de rubro',
    descripcion_rubro: 'Descripción del rubro',
    superficie: 'Superficie',
    seccion: 'Sección',
    manzana: 'Manzana',
    parcela: 'Parcela',
    calles: 'Calles',
    comuna: 'Comuna',
    razon_social: 'Razón social',
    partida_matriz: 'Partida matriz',
    origen: 'Origen del registro',
    anio: 'Año',
    smp: 'Clave SMP',
    comuna_fuente: 'Fuente de la comuna',
    smp_fuente: 'Fuente del SMP',
    fecha_fuente: 'Fuente de la fecha',
};

const ETIQUETAS_FUENTES = {
    archivo: 'Archivo original',
    catastro: 'Catastro',
    callejero: 'Callejero oficial',
    callejero_fuzzy: 'Callejero aproximado',
    seccion_manzana_parcela: 'Sección, manzana y parcela',
    sin_dato: 'Sin dato',
};

const formateador = new Intl.NumberFormat('es-AR');
const porcentaje = (valor) => `${(valor * 100).toFixed(1)}%`;

export default function CoberturaView() {
    const [cobertura, setCobertura] = useState(null);
    const [comunas, setComunas] = useState([]);
    const [cargando, setCargando] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const control = new AbortController();

        Promise.all([
            obtenerCobertura({ signal: control.signal }),
            Promise.allSettled(
                Array.from({ length: 15 }, (_, indice) =>
                    obtenerHabilitacionesPorComuna(indice + 1, { signal: control.signal })
                )
            ),
        ])
            .then(([datosCobertura, resultadosComunas]) => {
                if (control.signal.aborted) return;
                setCobertura(datosCobertura);
                const totales = resultadosComunas
                    .filter((resultado) => resultado.status === 'fulfilled')
                    .map((resultado) => resultado.value);
                setComunas(totales);
            })
            .catch((err) => {
                if (err.name !== 'AbortError') setError(err.message);
            })
            .finally(() => {
                if (!control.signal.aborted) setCargando(false);
            });

        return () => control.abort();
    }, []);

    const campos = useMemo(() => {
        if (!cobertura?.campos) return [];
        return Object.entries(cobertura.campos).map(([clave, datos]) => ({ clave, ...datos }));
    }, [cobertura]);

    const camposConExpectativa = campos.filter((campo) => campo.expectativa_minima != null);
    const expectativasCumplidas = camposConExpectativa.filter((campo) => campo.cumple_expectativa);
    const maximoComuna = comunas.reduce((maximo, item) => Math.max(maximo, item.total_habilitaciones), 0);
    const fuentesComuna = cobertura?.campos?.comuna_fuente?.fuentes || {};
    const totalFuentes = Object.values(fuentesComuna).reduce((total, valor) => total + valor, 0);
    const camposTrazabilidadPendientes = ['smp_fuente', 'fecha_fuente']
        .map((clave) => campos.find((campo) => campo.clave === clave))
        .filter(Boolean);

    if (cargando) {
        return (
            <div className="w-full">
                <p className="text-sm text-slate-500">Cargando indicadores de cobertura…</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="w-full">
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">
                    <p className="font-semibold">No se pudieron cargar los indicadores.</p>
                    <p className="mt-1">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full">
            <header className="mb-8">
                <span className="text-xs font-semibold uppercase tracking-wider text-gcba-secondary">
                    Calidad de datos
                </span>
                <h1 className="mt-1 text-3xl sm:text-4xl font-bold text-gcba-dark">Cobertura del padrón</h1>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-slate-600">
                    Porcentaje de registros con dato por campo y comparación con las expectativas mínimas
                    definidas para el padrón de habilitaciones.
                </p>
            </header>

            <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <p className="text-xs font-medium text-slate-500">Registros analizados</p>
                    <p className="mt-1 text-3xl font-bold text-gcba-dark">
                        {formateador.format(cobertura?.total_registros || 0)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Habilitaciones en la base</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <p className="text-xs font-medium text-slate-500">Campos monitoreados</p>
                    <p className="mt-1 text-3xl font-bold text-gcba-dark">{campos.length}</p>
                    <p className="mt-1 text-xs text-slate-500">Columnas con medición de cobertura</p>
                </div>
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
                    <p className="text-xs font-medium text-emerald-800">Expectativas cumplidas</p>
                    <p className="mt-1 text-3xl font-bold text-emerald-900">
                        {expectativasCumplidas.length}
                        <span className="text-base font-semibold text-emerald-700"> / {camposConExpectativa.length}</span>
                    </p>
                    <p className="mt-1 text-xs text-emerald-800">Campos con umbral definido</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                    <p className="text-xs font-medium text-slate-500">Comunas con datos</p>
                    <p className="mt-1 text-3xl font-bold text-gcba-dark">{comunas.length}</p>
                    <p className="mt-1 text-xs text-slate-500">Sobre 15 comunas de CABA</p>
                </div>
            </section>

            {camposTrazabilidadPendientes.length > 0 && (
                <div className="mb-8 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                    <p className="font-semibold">Trazabilidad en proceso</p>
                    <p className="mt-1">
                        {camposTrazabilidadPendientes.map((campo) => ETIQUETAS_CAMPOS[campo.clave] || campo.clave).join(' y ')}{' '}
                        todavía no tienen la fuente registrada en el padrón. No significa que falte el dato:
                        la cobertura se mide sobre el valor, no sobre su origen.
                    </p>
                </div>
            )}

            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
                <section className="xl:col-span-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                    <h2 className="text-lg font-bold text-gcba-dark">Cobertura por campo</h2>
                    <p className="mt-1 mb-5 text-sm text-slate-600">
                        Los campos con expectativa muestran si alcanzan el mínimo acordado.
                    </p>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                                    <th className="py-2 pr-3 font-semibold">Campo</th>
                                    <th className="py-2 pr-3 font-semibold">Cobertura</th>
                                    <th className="py-2 pr-3 font-semibold text-right">Con dato</th>
                                    <th className="py-2 pr-3 font-semibold text-right">Sin dato</th>
                                    <th className="py-2 font-semibold">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {campos.map((campo) => {
                                    const estado = campo.cumple_expectativa == null
                                        ? 'Sin umbral'
                                        : campo.cumple_expectativa
                                            ? 'Cumple'
                                            : 'Debajo';
                                    const colorBarra = campo.cumple_expectativa == null
                                        ? 'bg-gcba-secondary'
                                        : campo.cumple_expectativa
                                            ? 'bg-emerald-500'
                                            : 'bg-rose-500';
                                    return (
                                        <tr key={campo.clave} className="border-b border-slate-100 last:border-0">
                                            <td className="py-2.5 pr-3 text-slate-800">
                                                {ETIQUETAS_CAMPOS[campo.clave] || campo.clave}
                                            </td>
                                            <td className="py-2.5 pr-3">
                                                <div className="flex items-center gap-2">
                                                    <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-100">
                                                        <div
                                                            className={`h-full rounded-full ${colorBarra}`}
                                                            style={{ width: `${Math.max(campo.cobertura * 100, 1)}%` }}
                                                        />
                                                    </div>
                                                    <span className="tabular-nums text-slate-700">
                                                        {porcentaje(campo.cobertura)}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="py-2.5 pr-3 text-right tabular-nums text-slate-600">
                                                {formateador.format(campo.registros_con_dato)}
                                            </td>
                                            <td className="py-2.5 pr-3 text-right tabular-nums text-slate-600">
                                                {formateador.format(campo.registros_sin_dato)}
                                            </td>
                                            <td className="py-2.5">
                                                <span className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold ${
                                                    estado === 'Cumple'
                                                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                                                        : estado === 'Debajo'
                                                            ? 'border-rose-200 bg-rose-50 text-rose-700'
                                                            : 'border-slate-200 bg-slate-50 text-slate-600'
                                                }`}>
                                                    {estado}
                                                </span>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </section>

                <div className="xl:col-span-4 space-y-6">
                    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h2 className="text-lg font-bold text-gcba-dark">Origen de la comuna</h2>
                        <p className="mt-1 mb-4 text-sm text-slate-600">
                            Distribución de la fuente usada para asignar la comuna.
                        </p>
                        {Object.keys(fuentesComuna).length === 0 ? (
                            <p className="text-sm text-slate-500">Sin datos de procedencia.</p>
                        ) : (
                            <ul className="space-y-3">
                                {Object.entries(fuentesComuna)
                                    .sort(([, a], [, b]) => b - a)
                                    .map(([fuente, valor]) => (
                                        <li key={fuente}>
                                            <div className="flex items-baseline justify-between gap-2 text-sm">
                                                <span className="text-slate-700">{ETIQUETAS_FUENTES[fuente] || fuente}</span>
                                                <span className="font-semibold text-slate-900">
                                                    {totalFuentes > 0 ? porcentaje(valor / totalFuentes) : '0%'}
                                                </span>
                                            </div>
                                            <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                                                <div
                                                    className="h-full rounded-full bg-gcba-secondary"
                                                    style={{ width: `${totalFuentes > 0 ? (valor / totalFuentes) * 100 : 0}%` }}
                                                />
                                            </div>
                                        </li>
                                    ))}
                            </ul>
                        )}
                    </section>

                    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
                        <h2 className="text-lg font-bold text-gcba-dark">Habilitaciones por comuna</h2>
                        <p className="mt-1 mb-4 text-sm text-slate-600">Totales registrados en cada comuna.</p>
                        <ul className="space-y-2">
                            {comunas.map((item) => (
                                <li key={item.comuna}>
                                    <div className="flex items-baseline justify-between gap-2 text-sm">
                                        <span className="text-slate-700">Comuna {item.comuna}</span>
                                        <span className="tabular-nums font-semibold text-slate-900">
                                            {formateador.format(item.total_habilitaciones)}
                                        </span>
                                    </div>
                                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                                        <div
                                            className="h-full rounded-full bg-gcba-primary"
                                            style={{ width: `${maximoComuna > 0 ? (item.total_habilitaciones / maximoComuna) * 100 : 0}%` }}
                                        />
                                    </div>
                                </li>
                            ))}
                        </ul>
                    </section>
                </div>
            </div>

            <p className="mt-6 text-xs text-slate-500">
                La cobertura indica presencia de dato, no exactitud ni vigencia. Los umbrales son orientativos
                y no constituyen una validación oficial de la fuente.
            </p>
        </div>
    );
}
