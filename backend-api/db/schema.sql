-- =============================================================================
-- Esquema de datos de referencia para el backend (habilitaciones CABA)
-- Fuente de verdad: db/seed/rubros_requisitos.csv (curado manualmente)
--
-- Uso:  psql "$DATABASE_URL" -f db/schema.sql
-- Luego: python src/export_postgres.py   (carga el CSV hacia Postgres)
-- =============================================================================

-- Evita avisos de "already exists" al correr el script más de una vez.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- Para búsqueda insensible a acentos en el backend (unaccent(...)).
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- -----------------------------------------------------------------------------
-- rubros_requisitos: checklist para abrir un local comercial. Para cada rubro
-- (o "General" si aplica a todos), lista cada requisito/trámite ordenado por
-- etapa, con su documentación, organismo y link oficial.
--
-- Columnas de checklist:
--   etapa         -> previo | habilitacion | rubro | tributario | operativo
--   orden         -> posición dentro de la etapa (para presentar en orden)
--   obligatorio   -> Obligatorio | Opcional | Condicional
--   aplica_cuando -> condición para los "Condicional" (NULL si no aplica)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rubros_requisitos (
    id                      SERIAL PRIMARY KEY,
    rubro                   TEXT        NOT NULL,
    tramite                 TEXT        NOT NULL,
    etapa                   TEXT,
    orden                   INTEGER,
    obligatorio             TEXT,
    aplica_cuando           TEXT,
    documentacion_requerida TEXT        NOT NULL,
    organismo               TEXT,
    link_oficial            TEXT,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_rubros_requisitos_rubro_tramite UNIQUE (rubro, tramite)
);

-- Índice para la consulta típica del backend: filtrar por rubro sin importar mayúsculas/acentos.
CREATE INDEX IF NOT EXISTS idx_rubros_requisitos_rubro
    ON rubros_requisitos (LOWER(rubro));

-- -----------------------------------------------------------------------------
-- habilitaciones: padrón completo de habilitaciones comerciales de la CABA
-- (216.991 filas). Fuente: data/processed/habilitaciones_caba_clean.csv,
-- que se genera corriendo el pipeline (notebook 01). NO está en el repo.
--
-- Carga: python src/export_postgres.py --habilitaciones
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS habilitaciones (
    id                  BIGSERIAL PRIMARY KEY,
    solicitud           BIGINT,
    tipo_tramite        TEXT,
    tipo_expediente     TEXT,
    subtipo_expediente  TEXT,
    fecha_habilitacion  DATE,
    numero_expediente   TEXT,
    codigo_rubro        NUMERIC,
    descripcion_rubro   TEXT,
    superficie          DOUBLE PRECISION,
    seccion             TEXT,
    manzana             TEXT,
    parcela             TEXT,
    smp                 TEXT,
    calles              TEXT,
    comuna              SMALLINT,
    comuna_fuente       TEXT,
    razon_social        TEXT,
    partida_matriz      TEXT,
    origen              TEXT,
    anio                SMALLINT
);

-- Índices para las consultas típicas del backend.
CREATE INDEX IF NOT EXISTS idx_habilitaciones_comuna  ON habilitaciones (comuna);
CREATE INDEX IF NOT EXISTS idx_habilitaciones_anio    ON habilitaciones (anio);
CREATE INDEX IF NOT EXISTS idx_habilitaciones_rubro   ON habilitaciones (codigo_rubro);
CREATE INDEX IF NOT EXISTS idx_habilitaciones_smp     ON habilitaciones (smp);
CREATE INDEX IF NOT EXISTS idx_habilitaciones_com_rub ON habilitaciones (comuna, codigo_rubro);

-- -----------------------------------------------------------------------------
-- epok_fichas: perfil catastral oficial por SMP, traído de la API EPOK del
-- GCBA. Una fila por propiedad (SMP), no por habilitación: muchas habilitaciones
-- comparten el mismo inmueble.
--
-- Se llena con: python src/enriquecer_epok.py   (reanudable, llama a EPOK)
-- El backend la joinea con habilitaciones por smp.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS epok_fichas (
    smp                    TEXT PRIMARY KEY,
    ficha                  JSONB,              -- respuesta completa de EPOK
    lng                    DOUBLE PRECISION,   -- centroide (para mapa)
    lat                    DOUBLE PRECISION,
    direccion              TEXT,
    superficie_total       DOUBLE PRECISION,
    superficie_cubierta    DOUBLE PRECISION,
    frente                 DOUBLE PRECISION,
    fondo                  DOUBLE PRECISION,
    pisos_sobre_rasante    SMALLINT,
    unidades_funcionales   INTEGER,
    propiedad_horizontal   TEXT,
    puertas                JSONB,              -- accesos (calle/altura)
    actualizado_en         TIMESTAMPTZ NOT NULL DEFAULT now()
);
