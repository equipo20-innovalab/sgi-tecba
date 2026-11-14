/**
 * @file ResultPanel.jsx
 * @description Panel de visualización de resultados y viabilidad urbana para la consulta del usuario.
 * Integra los datos territoriales y catastrales en vivo de la API pública USIG (datos_utiles):
 * Comuna, Barrio, Sección, Manzana, Parcela y Clave SMP.
 * @author Equipo Frontend - SGI TECBA
 */

import { useEffect, useState } from 'react';

/**
 * Mapea el identificador técnico de una fuente de datos a una etiqueta legible.
 *
 * @param {string} fuente - Identificador interno de la fuente.
 * @returns {string} Nombre descriptivo de la fuente.
 */
const etiquetaFuente = (fuente) => ({
    archivo: 'Fuente original',
    catastro: 'Catastro',
    callejero: 'Callejero oficial',
    callejero_fuzzy: 'Callejero aproximado',
    seccion_manzana_parcela: 'Sección, manzana y parcela',
    sin_dato: 'Fuente sin dato',
}[fuente] || 'Origen no informado');

/**
 * Formatea un valor arbitrario para su visualización segura en la interfaz.
 *
 * @param {*} value - Valor a formatear.
 * @returns {string} Cadena de texto formateada o indicador de dato no disponible.
 */
const formatValue = (value) => {
    if (value == null || value === '') return 'Dato no disponible';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
};

/**
 * Extrae el nombre de la calle y la altura numérica a partir de una dirección normalizada de USIG.
 * Ejemplo: "CORRIENTES AV. 2500, CABA" -> { calle: "CORRIENTES AV.", altura: 2500 }
 *
 * @param {string} direccion - Dirección a analizar.
 * @returns {{calle: string, altura: number}|null} Objeto con calle y altura, o null.
 */
function extraerCalleYAltura(direccion) {
    if (!direccion) return null;
    const sinCaba = direccion.replace(/,?\s*(CABA|CAPITAL FEDERAL).*$/i, '').trim();
    const match = sinCaba.match(/^(.+?)\s+(\d+)\s*$/);
    if (!match) return null;
    return {
        calle: match[1].trim(),
        altura: parseInt(match[2], 10),
    };
}

/**
 * Componente ResultPanel
 * Renderiza el resumen territorial enriquecido con USIG (datos_utiles), los datos catastrales
 * de Sección-Manzana-Parcela, los requisitos del trámite y las fuentes oficiales.
 *
 * @param {Object} props - Propiedades del componente.
 * @param {Object|null} props.data - Respuesta estructurada del endpoint /api/v1/consulta.
 * @returns {JSX.Element} Panel de resultados de la consulta.
 */
export const ResultPanel = ({ data }) => {
    const [datosUtiles, setDatosUtiles] = useState(null);

    const ubicacion = data?.ubicacion || {};
    const address =
        ubicacion.direccion_normalizada ||
        ubicacion.direccion_original ||
        'Dirección no identificada';

    // Consulta en vivo a la API pública USIG (datos_utiles) para obtener Barrio, Sección, Manzana y Parcela
    useEffect(() => {
        let cancelado = false;
        const parsed = extraerCalleYAltura(
            ubicacion.direccion_normalizada || ubicacion.direccion_original
        );

        if (!parsed) {
            setDatosUtiles(null);
            return undefined;
        }

        const consultarUsig = async () => {
            // Si la altura termina en 00 (esquina exacta), probamos también +2 para obtener la parcela frentista
            const alturas =
                parsed.altura % 100 === 0
                    ? [parsed.altura, parsed.altura + 2, parsed.altura + 4]
                    : [parsed.altura];

            let mejorDato = null;
            for (const alt of alturas) {
                try {
                    const url = `https://ws.usig.buenosaires.gob.ar/datos_utiles/?calle=${encodeURIComponent(
                        parsed.calle
                    )}&altura=${alt}`;
                    const resp = await fetch(url);
                    if (!resp.ok) continue;
                    const json = await resp.json();
                    if (json && (json.comuna || json.barrio)) {
                        if (!mejorDato) mejorDato = json;
                        if (json.seccion && json.manzana && json.parcela) {
                            mejorDato = json;
                            break;
                        }
                    }
                } catch {
                    // Continuar con el siguiente intento si falla la red
                }
            }

            if (!cancelado) {
                setDatosUtiles(mejorDato);
            }
        };

        consultarUsig();
        return () => {
            cancelado = true;
        };
    }, [ubicacion.direccion_normalizada, ubicacion.direccion_original]);

    if (!data) {
        return (
            <div className="w-full bg-white rounded-xl shadow-lg border border-slate-200 p-6 mb-6">
                <h3 className="text-lg font-bold text-gcba-dark">Resultado de la consulta</h3>
                <p className="mt-2 text-sm text-slate-600">
                    Ingresá una actividad y una dirección para consultar los datos disponibles.
                </p>
            </div>
        );
    }

    const ficha = data.ficha_catastral;
    const parcela = data.habilitaciones_parcela?.[0];
    const contexto = data.contexto_territorial;

    // Desglose de Sección, Manzana y Parcela desde datos_utiles, ficha local o SMP
    const smpBase = ficha?.smp || parcela?.smp || ubicacion.smp;
    const partesSmp = smpBase ? smpBase.split('-') : [];

    const seccion =
        datosUtiles?.seccion ||
        parcela?.seccion ||
        partesSmp[0] ||
        null;
    const manzana =
        datosUtiles?.manzana ||
        parcela?.manzana ||
        partesSmp[1] ||
        null;
    const parcelaNum =
        datosUtiles?.parcela ||
        parcela?.parcela ||
        partesSmp[2] ||
        null;

    const smpCalculado =
        smpBase ||
        (seccion && manzana && parcelaNum
            ? `${String(seccion).padStart(3, '0')}-${String(manzana).padStart(3, '0')}-${String(parcelaNum).padStart(3, '0')}`
            : null);

    const barrio = datosUtiles?.barrio || null;
    const area = ficha?.superficie_total ?? ficha?.superficie_cubierta;

    const confianzaComuna = {
        archivo: 'Alta',
        catastro: 'Alta',
        callejero: 'Media',
        callejero_fuzzy: 'Baja',
    }[parcela?.comuna_fuente] || 'No disponible';

    return (
        <div className="w-full bg-white rounded-xl shadow-lg border border-slate-200 p-6 mb-6">
            {/* Encabezado de la dirección consultada */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-slate-100 pb-4 mb-4 gap-2">
                <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-gcba-secondary">
                        Resultado de consulta
                    </span>
                    <h3 className="text-lg font-bold text-gcba-dark">{address}</h3>
                </div>
                <span className="bg-slate-100 text-slate-700 text-xs font-medium px-3 py-1 rounded-full border border-slate-200">
                    {data.mensaje ? 'Requiere más información' : 'Datos consultados'}
                </span>
            </div>

            {/* Tarjetas de indicadores territoriales y catastrales (USIG Datos Útiles) */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                {/* Tarjeta 1: Comuna y Barrio */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Comuna y Barrio</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">
                        {ubicacion.comuna
                            ? `Comuna ${ubicacion.comuna}${barrio ? ` · ${barrio}` : ''}`
                            : datosUtiles?.comuna
                                ? `${datosUtiles.comuna}${barrio ? ` · ${barrio}` : ''}`
                                : 'No disponible'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                        {parcela?.comuna_fuente
                            ? `${etiquetaFuente(parcela.comuna_fuente)} · Confianza ${confianzaComuna}`
                            : 'API Datos Útiles USIG · GCBA'}
                    </p>
                </div>

                {/* Tarjeta 2: Superficie y Catastro USIG (S-M-P) */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Superficie y Catastro (S-M-P)</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">
                        {area != null
                            ? `${area} m²${smpCalculado ? ` · SMP ${smpCalculado}` : ''}`
                            : seccion && manzana && parcelaNum
                                ? `Sec. ${seccion} · Manz. ${manzana} · Parc. ${parcelaNum}`
                                : 'No disponible'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                        {seccion && manzana && parcelaNum
                            ? `Sección ${seccion} · Manzana ${manzana} · Parcela ${parcelaNum}`
                            : 'Catastro oficial CABA'}
                    </p>
                </div>

                {/* Tarjeta 3: Habilitaciones en la Comuna */}
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Habilitaciones en la comuna</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">
                        {contexto ? contexto.total_habilitaciones.toLocaleString('es-AR') : 'No disponible'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                        Padrón histórico BA Data
                    </p>
                </div>
            </div>

            {/* Actividad comercial identificada y avisos de validación */}
            <p className="text-sm text-slate-700">
                Actividad detectada: <strong>{data.actividad_detectada || 'No identificada'}</strong>
            </p>
            {data.mensaje && (
                <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    {data.mensaje}
                </p>
            )}

            {/* Sección detallada con todos los Datos Útiles de USIG y Ficha Catastral */}
            {(datosUtiles || ficha || parcela || smpCalculado) && (
                <section className="mt-5 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-bold text-slate-800">
                        Información Catastral y Territorial (USIG · GCBA)
                    </h4>
                    <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                        <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-100">
                            <p className="text-[11px] font-medium text-slate-500">Barrio</p>
                            <p className="text-xs font-bold text-slate-800 mt-0.5">
                                {barrio || 'No disponible'}
                            </p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-100">
                            <p className="text-[11px] font-medium text-slate-500">Sección</p>
                            <p className="text-xs font-bold text-slate-800 mt-0.5">
                                {seccion || 'No disponible'}
                            </p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-100">
                            <p className="text-[11px] font-medium text-slate-500">Manzana</p>
                            <p className="text-xs font-bold text-slate-800 mt-0.5">
                                {manzana || 'No disponible'}
                            </p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-100">
                            <p className="text-[11px] font-medium text-slate-500">Parcela</p>
                            <p className="text-xs font-bold text-slate-800 mt-0.5">
                                {parcelaNum || 'No disponible'}
                            </p>
                        </div>
                        <div className="rounded-lg bg-slate-50 p-2.5 border border-slate-100">
                            <p className="text-[11px] font-medium text-slate-500">Código Postal</p>
                            <p className="text-xs font-bold text-slate-800 mt-0.5">
                                {datosUtiles?.codigo_postal_argentino ||
                                    datosUtiles?.codigo_postal ||
                                    'No disponible'}
                            </p>
                        </div>
                    </div>

                    {datosUtiles && (
                        <p className="mt-2.5 text-xs text-slate-500">
                            {[
                                datosUtiles.area_hospitalaria
                                    ? `Área Hospitalaria: ${datosUtiles.area_hospitalaria}`
                                    : null,
                                datosUtiles.comisaria_vecinal
                                    ? `Comisaría Vecinal: ${datosUtiles.comisaria_vecinal}`
                                    : datosUtiles.comisaria
                                        ? `Comisaría: ${datosUtiles.comisaria}`
                                        : null,
                                datosUtiles.distrito_escolar
                                    ? `Distrito Escolar: ${datosUtiles.distrito_escolar}`
                                    : null,
                            ]
                                .filter(Boolean)
                                .join(' · ')}
                        </p>
                    )}
                </section>
            )}

            {/* Historial de Habilitaciones en la Parcela */}
            {data.habilitaciones_parcela?.length > 0 && (
                <section className="mt-5 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-bold text-slate-800">
                        Habilitaciones asociadas a esta parcela ({data.habilitaciones_parcela.length})
                    </h4>
                    <ul className="mt-2 space-y-2 text-sm text-slate-600">
                        {data.habilitaciones_parcela.map((item, index) => (
                            <li
                                key={`${item.smp}-${item.descripcion_rubro}-${item.anio}-${index}`}
                                className="rounded-lg bg-slate-50 p-3"
                            >
                                <p className="font-semibold text-slate-800">
                                    {item.descripcion_rubro || 'Rubro sin descripción'}
                                </p>
                                <p className="mt-1 text-xs text-slate-500">
                                    {[
                                        item.calles || 'Dirección no disponible',
                                        item.anio || 'Año no disponible',
                                        item.superficie != null ? `${item.superficie} m²` : 'Superficie no disponible',
                                    ].join(' · ')}
                                </p>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            {/* Atributos del Código Urbanístico */}
            {data.codigo_urbanistico && (
                <section className="mt-5 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-bold text-slate-800">Código Urbanístico de la parcela</h4>
                    <details className="mt-2 text-sm">
                        <summary className="cursor-pointer font-medium text-blue-700">
                            Ver todos los atributos del Código Urbanístico ({Object.keys(data.codigo_urbanistico).length})
                        </summary>
                        <dl className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {Object.entries(data.codigo_urbanistico).map(([key, value]) => (
                                <div key={key} className="rounded-lg bg-slate-50 p-3">
                                    <dt className="text-xs font-semibold text-slate-500">{key}</dt>
                                    <dd className="break-words text-sm text-slate-700">
                                        {formatValue(value)}
                                    </dd>
                                </div>
                            ))}
                        </dl>
                    </details>
                </section>
            )}

            {/* Checklist de Requisitos y Trámites */}
            {data.requisitos?.length > 0 && (
                <section className="mt-5 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-bold text-slate-800">
                        Requisitos y trámites ({data.requisitos.length})
                    </h4>
                    <ul className="mt-2 space-y-3">
                        {data.requisitos.map((requisito, index) => (
                            <li
                                key={`${requisito.tramite}-${index}`}
                                className="rounded-lg bg-slate-50 p-3 text-sm"
                            >
                                <p className="font-semibold text-slate-800">{requisito.tramite}</p>
                                {requisito.etapa && (
                                    <p className="mt-1 text-xs text-slate-500">
                                        Etapa: {requisito.etapa}
                                        {requisito.obligatorio ? ` · ${requisito.obligatorio}` : ''}
                                    </p>
                                )}
                                <p className="mt-1 text-slate-600">
                                    {requisito.documentacion_requerida}
                                </p>
                                {requisito.link_oficial && (
                                    <a
                                        className="mt-1 inline-block text-blue-700 underline"
                                        href={requisito.link_oficial}
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        Información oficial
                                    </a>
                                )}
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            {/* Competencia o Habilitaciones Cercanas del Mismo Rubro */}
            {data.competencia_cercana?.length > 0 && (
                <section className="mt-5 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-bold text-slate-800">
                        Habilitaciones del mismo rubro ({data.competencia_cercana.length})
                    </h4>
                    <ul className="mt-2 space-y-2 text-sm text-slate-600">
                        {data.competencia_cercana.map((item, index) => (
                            <li key={`${item.descripcion_rubro}-${index}`}>
                                {item.descripcion_rubro || 'Rubro sin descripción'}
                                {item.calles ? ` · ${item.calles}` : ''}
                                {item.anio ? ` · ${item.anio}` : ''}
                            </li>
                        ))}
                    </ul>
                </section>
            )}

            {/* Trazabilidad de Fuentes */}
            {data.fuentes?.length > 0 && (
                <section className="mt-5 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-bold text-slate-800">Fuentes</h4>
                    <ul className="mt-2 space-y-1 text-xs text-slate-600">
                        {data.fuentes.map((fuente) => (
                            <li key={fuente.nombre}>
                                {fuente.url ? (
                                    <a
                                        className="text-blue-700 underline"
                                        href={fuente.url}
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        {fuente.nombre}
                                    </a>
                                ) : (
                                    fuente.nombre
                                )}
                            </li>
                        ))}
                    </ul>
                </section>
            )}
        </div>
    );
};