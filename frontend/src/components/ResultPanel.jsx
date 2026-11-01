/**
 * @file ResultPanel.jsx
 * @description Panel de visualización de resultados y viabilidad urbana para la consulta del usuario.
 * @author Equipo Frontend - SGI TECBA
 */

export const ResultPanel = ({ data }) => {
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

    const ubicacion = data.ubicacion || {};
    const ficha = data.ficha_catastral;
    const parcela = data.habilitaciones_parcela?.[0];
    const contexto = data.contexto_territorial;
    const cobertura = data.cobertura_datos;
    const address = ubicacion.direccion_normalizada
        || ubicacion.direccion_original
        || 'Dirección no identificada';
    const area = ficha?.superficie_total ?? ficha?.superficie_cubierta;
    const formatValue = (value) => {
        if (value == null || value === '') return 'Dato no disponible';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };
    const porcentajeCobertura = (campo) => {
        const valor = cobertura?.campos?.[campo]?.cobertura;
        return typeof valor === 'number' ? `${(valor * 100).toFixed(1)}%` : 'No disponible';
    };
    const etiquetaFuente = (fuente) => ({
        archivo: 'Fuente original',
        catastro: 'Catastro',
        callejero: 'Callejero oficial',
        callejero_fuzzy: 'Callejero aproximado',
        seccion_manzana_parcela: 'Sección, manzana y parcela',
        sin_dato: 'Fuente sin dato',
    }[fuente] || 'Origen no informado');
    const confianzaComuna = {
        archivo: 'Alta',
        catastro: 'Alta',
        callejero: 'Media',
        callejero_fuzzy: 'Baja',
    }[parcela?.comuna_fuente] || 'No disponible';

    return (
        <div className="w-full bg-white rounded-xl shadow-lg border border-slate-200 p-6 mb-6">
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

            {cobertura && (
                <section className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4" aria-label="Cobertura del padrón">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <h4 className="text-sm font-bold text-amber-950">Cobertura del padrón</h4>
                        <span className="text-xs text-amber-900">
                            {cobertura.total_registros.toLocaleString('es-AR')} registros
                        </span>
                    </div>
                    <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {[
                            ['Comuna', 'comuna'],
                            ['Clave SMP', 'smp'],
                            ['Fecha de habilitación', 'fecha_habilitacion'],
                        ].map(([label, campo]) => {
                            const metrica = cobertura.campos?.[campo];
                            const cumple = metrica?.cumple_expectativa;
                            return (
                                <div key={campo} className="rounded-md border border-amber-200 bg-white p-3">
                                    <p className="text-xs font-medium text-slate-600">{label}</p>
                                    <p className="mt-1 text-lg font-bold text-slate-900">
                                        {porcentajeCobertura(campo)}
                                    </p>
                                    {metrica?.expectativa_minima != null && (
                                        <p className={`mt-1 text-xs ${cumple ? 'text-emerald-700' : 'text-rose-700'}`}>
                                            {cumple ? 'Cumple' : 'Debajo'} de la expectativa de{' '}
                                            {(metrica.expectativa_minima * 100).toFixed(0)}%
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                    <p className="mt-3 text-xs text-amber-950">
                        La cobertura es parcial. Los niveles de confianza son indicativos según la fuente, no probabilidades.
                    </p>
                </section>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Comuna</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">
                        {ubicacion.comuna ? `Comuna ${ubicacion.comuna}` : 'No disponible'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                        {parcela?.comuna_fuente
                            ? `${etiquetaFuente(parcela.comuna_fuente)} · Confianza ${confianzaComuna}`
                            : 'Origen del dato no disponible'}
                    </p>
                </div>
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Superficie catastral</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">
                        {area != null ? `${area} m²` : 'No disponible'}
                    </p>
                </div>
                <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                    <p className="text-xs text-slate-500 font-medium">Habilitaciones en la comuna</p>
                    <p className="text-sm font-bold text-slate-800 mt-1">
                        {contexto ? contexto.total_habilitaciones.toLocaleString('es-AR') : 'No disponible'}
                    </p>
                </div>
            </div>

            <p className="text-sm text-slate-700">
                Actividad detectada: <strong>{data.actividad_detectada || 'No identificada'}</strong>
            </p>
            {data.mensaje && (
                <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    {data.mensaje}
                </p>
            )}

            {(ficha || parcela) && (
                <section className="mt-5 border-t border-slate-100 pt-4">
                    <h4 className="text-sm font-bold text-slate-800">Parcela y ficha catastral</h4>
                    <p className="mt-1 text-sm text-slate-600">
                        SMP: {formatValue(ficha?.smp || parcela?.smp)}
                        {parcela?.smp_fuente ? ` · Origen: ${etiquetaFuente(parcela.smp_fuente)}` : ''}
                        {parcela?.seccion ? ` · Sección: ${parcela.seccion}` : ''}
                        {parcela?.manzana ? ` · Manzana: ${parcela.manzana}` : ''}
                        {parcela?.parcela ? ` · Parcela: ${parcela.parcela}` : ''}
                        {ficha?.direccion ? ` · Dirección catastral: ${ficha.direccion}` : ''}
                        {ficha?.pisos_sobre_rasante != null
                            ? ` · Pisos: ${ficha.pisos_sobre_rasante}`
                            : ''}
                        {ficha?.unidades_funcionales != null
                            ? ` · Unidades funcionales: ${ficha.unidades_funcionales}`
                            : ''}
                    </p>
                    {parcela?.smp && (
                        <p className="mt-1 text-xs text-slate-500">
                            Confianza estructural alta: componentes presentes y normalizados; clave no verificada independientemente.
                        </p>
                    )}
                    {ficha?.ficha && (
                        <details className="mt-2 text-sm">
                            <summary className="cursor-pointer font-medium text-blue-700">
                                Ver todos los atributos originales de EPOK
                            </summary>
                            <dl className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                                {Object.entries(ficha.ficha).map(([key, value]) => (
                                    <div key={key} className="rounded bg-slate-50 p-2">
                                        <dt className="text-xs font-semibold text-slate-500">{key}</dt>
                                        <dd className="break-words text-sm text-slate-700">
                                            {formatValue(value)}
                                        </dd>
                                    </div>
                                ))}
                            </dl>
                        </details>
                    )}
                </section>
            )}

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
                                    {[item.calles || 'Dirección no disponible', item.anio || 'Año no disponible',
                                        item.superficie != null ? `${item.superficie} m²` : 'Superficie no disponible']
                                        .join(' · ')}
                                </p>
                                <p className="mt-1 text-xs text-slate-500">
                                    Fecha: {formatValue(item.fecha_habilitacion)}
                                    {item.fecha_fuente
                                        ? ` · ${etiquetaFuente(item.fecha_fuente)} · Confianza ${item.fecha_fuente === 'archivo' && item.fecha_habilitacion ? 'Alta' : 'No disponible'}`
                                        : ''}
                                </p>
                                <details className="mt-2 text-xs">
                                    <summary className="cursor-pointer text-blue-700">
                                        Ver todos los datos del registro
                                    </summary>
                                    <dl className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                                        {Object.entries(item).map(([key, value]) => (
                                            <div key={key} className="rounded bg-white p-2">
                                                <dt className="font-semibold text-slate-500">{key}</dt>
                                                <dd className="break-words text-slate-700">
                                                    {formatValue(value)}
                                                </dd>
                                            </div>
                                        ))}
                                    </dl>
                                </details>
                            </li>
                        ))}
                    </ul>
                </section>
            )}

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
                                ) : fuente.nombre}
                            </li>
                        ))}
                    </ul>
                </section>
            )}
        </div>
    );
};