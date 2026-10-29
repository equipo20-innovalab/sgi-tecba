-- =============================================================================
-- Carga el fixture pequeño y sanitizado de demo (db/demo).
--
-- Se ejecuta solo sobre una base vacía, después de db/schema.sql. Pensado para
-- `docker compose up` (init automático) y para CI:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/demo/init_demo.sql
--
-- Rutas: por defecto asume el layout de la imagen de PostgreSQL
-- (/docker-entrypoint-initdb.d/...). Fuera de Docker se pasan los directorios:
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/demo/init_demo.sql \
--        -v demo_dir="$PWD/db/demo" \
--        -v seed_dir="$PWD/db/seed"
--
-- Con -v demo_limpiar=1 se vacían las tablas antes de cargar (útil para
-- reejecutar el fixture en una base de desarrollo).
-- =============================================================================

\set ON_ERROR_STOP on

\if :{?demo_dir}
\else
  \set demo_dir '/docker-entrypoint-initdb.d/demo'
\endif
\if :{?seed_dir}
\else
  \set seed_dir '/docker-entrypoint-initdb.d/seed'
\endif

\if :{?demo_limpiar}
TRUNCATE TABLE habilitaciones, epok_fichas, rubros_requisitos RESTART IDENTITY;
\endif

\cd :seed_dir
\echo 'Cargando rubros_requisitos desde' :'seed_dir'
\copy rubros_requisitos (rubro, tramite, etapa, orden, obligatorio, aplica_cuando, documentacion_requerida, organismo, link_oficial) FROM 'rubros_requisitos.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

\cd :demo_dir
\echo 'Cargando habilitaciones demo desde' :'demo_dir'
\copy habilitaciones (solicitud, tipo_tramite, tipo_expediente, subtipo_expediente, fecha_habilitacion, fecha_fuente, numero_expediente, codigo_rubro, descripcion_rubro, superficie, seccion, manzana, parcela, smp, smp_fuente, calles, comuna, comuna_fuente, razon_social, partida_matriz, origen, anio) FROM 'habilitaciones_demo.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

\echo 'Cargando epok_fichas demo desde' :'demo_dir'
\copy epok_fichas (smp, ficha, lng, lat, direccion, superficie_total, superficie_cubierta, frente, fondo, pisos_sobre_rasante, unidades_funcionales, propiedad_horizontal, puertas, actualizado_en, estado, intentos, ultimo_error, ultimo_intento_en) FROM 'epok_fichas_demo.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

-- Las secuencias de las tablas cargadas por COPY ya avanzan solas, pero los
-- IDs de `rubros_requisitos` se generan con el DEFAULT; se recalcula igual por
-- si el CSV cambia de orden.
SELECT setval(pg_get_serial_sequence('rubros_requisitos', 'id'),
              COALESCE((SELECT max(id) FROM rubros_requisitos), 1));

ANALYZE habilitaciones;
ANALYZE epok_fichas;
ANALYZE rubros_requisitos;
