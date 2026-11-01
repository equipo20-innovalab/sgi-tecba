/**
 * @file HomeCards.jsx
 * @description Accesos directos a las secciones de exploración del sistema.
 * @author Equipo Frontend - SGI TECBA
 */

const SECCIONES = [
    {
        href: '#/rubros',
        icono: '📚',
        titulo: 'Rubros y requisitos',
        detalle: 'Consultá la documentación y los trámites de cada actividad, y mirá el ranking por comuna.',
        etiqueta: 'Catálogo',
    },
    {
        href: '#/cobertura',
        icono: '📊',
        titulo: 'Cobertura del padrón',
        detalle: 'Qué porcentaje de registros tiene cada campo y cuáles cumplen las expectativas mínimas.',
        etiqueta: 'Calidad de datos',
    },
    {
        href: '#/fuentes',
        icono: '🧭',
        titulo: 'Fuentes y metodología',
        detalle: 'De dónde salen los datos, cómo se cruzan y qué límites tiene la información.',
        etiqueta: 'Transparencia',
    },
];

export const HomeCards = () => (
    <section className="mt-10" aria-label="Explorar el sistema">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-xl font-bold text-gcba-dark">Explorar el sistema</h2>
            <span className="text-xs text-slate-500">Datos abiertos de la Ciudad, cruzados y explicados</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {SECCIONES.map((seccion) => (
                <a
                    key={seccion.href}
                    href={seccion.href}
                    className="group flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-gcba-secondary hover:shadow-md focus:outline-none focus:ring-2 focus:ring-gcba-primary/30"
                >
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-2xl" aria-hidden="true">{seccion.icono}</span>
                        <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                            {seccion.etiqueta}
                        </span>
                    </div>
                    <h3 className="mt-3 text-base font-bold text-slate-900 group-hover:text-gcba-primary">
                        {seccion.titulo}
                    </h3>
                    <p className="mt-1 flex-1 text-sm text-slate-600">{seccion.detalle}</p>
                    <span className="mt-3 text-xs font-semibold text-gcba-secondary group-hover:underline">
                        Entrar →
                    </span>
                </a>
            ))}
        </div>
    </section>
);
