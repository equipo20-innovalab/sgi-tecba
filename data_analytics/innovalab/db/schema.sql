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
-- versionado con Git LFS y regenerable con python -m src.run_pipeline.
--
-- Carga: python -m src.run_pipeline
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS habilitaciones (
    id                  BIGSERIAL PRIMARY KEY,
    solicitud           BIGINT,
    tipo_tramite        TEXT,
    tipo_expediente     TEXT,
    subtipo_expediente  TEXT,
    fecha_habilitacion  DATE,
    fecha_fuente        TEXT,
    numero_expediente   TEXT,
    codigo_rubro        NUMERIC,
    descripcion_rubro   TEXT,
    superficie          DOUBLE PRECISION,
    seccion             TEXT,
    manzana             TEXT,
    parcela             TEXT,
    smp                 TEXT,
    smp_fuente          TEXT,
    calles              TEXT,
    comuna              SMALLINT,
    comuna_fuente       TEXT,
    razon_social        TEXT,
    partida_matriz      TEXT,
    origen              TEXT,
    anio                SMALLINT
);

ALTER TABLE habilitaciones ADD COLUMN IF NOT EXISTS fecha_fuente TEXT;
ALTER TABLE habilitaciones ADD COLUMN IF NOT EXISTS smp_fuente TEXT;

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

-- -----------------------------------------------------------------------------
-- codigo_urbanistico: atributos completos del Codigo Urbanistico por parcela.
-- Fuente: data/processed/codigo_urbanistico_limpio.csv (318.126 SMP).
-- Los nombres y valores originales de todas las columnas se preservan en JSONB.
-- Carga: python src/export_postgres.py --codigo-urbanistico
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS codigo_urbanistico (
    smp     TEXT PRIMARY KEY,
    datos   JSONB NOT NULL
);

-- -----------------------------------------------------------------------------
-- indice_oportunidad_meta: una fila por corrida del índice (auditoría).
-- Guarda versión de fórmula, fecha de cálculo, pesos efectivos, parámetros y
-- huella del CSV de origen para poder reproducir exactamente el artefacto.
-- Carga: python src/export_postgres.py --oportunidad
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS indice_oportunidad_meta (
    calculo_id       BIGSERIAL PRIMARY KEY,
    formula_version  TEXT        NOT NULL,
    calculado_en     TIMESTAMPTZ NOT NULL,
    pesos            JSONB       NOT NULL,
    parametros       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    n_filas          INTEGER     NOT NULL,
    n_comunas        INTEGER,
    n_rubros         INTEGER,
    anio_ref         SMALLINT,
    fuente           TEXT,
    fuente_sha256    TEXT,
    notas            TEXT,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- indice_oportunidad: score 0-100 por (comuna, rubro) con sus componentes,
-- pesos, aportes y métricas crudas. Append-only: cada corrida agrega filas con
-- su calculo_id. Para consultar la última corrida usar la vista
-- indice_oportunidad_actual.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS indice_oportunidad (
    id                             BIGSERIAL PRIMARY KEY,
    calculo_id                     BIGINT      NOT NULL
        REFERENCES indice_oportunidad_meta (calculo_id) ON DELETE CASCADE,
    formula_version                TEXT        NOT NULL,
    calculado_en                   TIMESTAMPTZ NOT NULL,
    comuna                         SMALLINT    NOT NULL,
    rubro                          TEXT        NOT NULL,
    oportunidad                    NUMERIC(5,1) NOT NULL,
    componente_crecimiento         NUMERIC(5,1) NOT NULL,
    componente_baja_saturacion     NUMERIC(5,1) NOT NULL,
    componente_subrepresentacion   NUMERIC(5,1) NOT NULL,
    peso_crecimiento               NUMERIC(4,3) NOT NULL,
    peso_baja_saturacion           NUMERIC(4,3) NOT NULL,
    peso_subrepresentacion         NUMERIC(4,3) NOT NULL,
    aporte_crecimiento             NUMERIC(5,2) NOT NULL,
    aporte_baja_saturacion         NUMERIC(5,2) NOT NULL,
    aporte_subrepresentacion       NUMERIC(5,2) NOT NULL,
    crecimiento                    DOUBLE PRECISION,
    saturacion                     DOUBLE PRECISION,
    subrepresentacion              DOUBLE PRECISION,
    n_licencias                    INTEGER     NOT NULL,
    n_nuevas                       INTEGER,
    superficie_promedio            DOUBLE PRECISION,
    anio_ref                       SMALLINT,
    explicacion                    TEXT        NOT NULL,
    CONSTRAINT uq_indice_oportunidad_calculo_comuna_rubro
        UNIQUE (calculo_id, comuna, rubro)
);

CREATE INDEX IF NOT EXISTS idx_indice_oportunidad_comuna_rubro
    ON indice_oportunidad (comuna, rubro);
CREATE INDEX IF NOT EXISTS idx_indice_oportunidad_score
    ON indice_oportunidad (oportunidad DESC);
CREATE INDEX IF NOT EXISTS idx_indice_oportunidad_calculo
    ON indice_oportunidad (calculo_id);

-- Última corrida disponible (la de mayor calculo_id).
CREATE OR REPLACE VIEW indice_oportunidad_actual AS
SELECT i.*
FROM indice_oportunidad AS i
WHERE i.calculo_id = (SELECT max(calculo_id) FROM indice_oportunidad_meta);
