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

-- -----------------------------------------------------------------------------
-- codigo_urbanistico: una fila por SMP con los parámetros del Código
-- Urbanístico (BA Data, actualizado al 31/12/2024). El CSV original usa
-- sufijos de SMP en minúscula; el backend los normaliza a mayúscula.
-- Carga: python scripts/cargar_codigo_urbanistico.py
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS codigo_urbanistico (
    smp             TEXT PRIMARY KEY,
    smp_raw         TEXT NOT NULL,
    barrio          TEXT,
    comuna          SMALLINT,
    dist_cpu_1      TEXT,
    dist_cpu_2      TEXT,
    dist_1_esp      TEXT,
    zona_1          TEXT,
    zona_2          TEXT,
    uso_1           SMALLINT,
    uso_2           SMALLINT,
    uso_3           SMALLINT,
    uni_edif_1      DOUBLE PRECISION,
    uni_edif_2      DOUBLE PRECISION,
    uni_edif_3      DOUBLE PRECISION,
    uni_edif_4      DOUBLE PRECISION,
    fot_em_1        DOUBLE PRECISION,
    fot_em_2        DOUBLE PRECISION,
    fot_pl_1        DOUBLE PRECISION,
    fot_pl_2        DOUBLE PRECISION,
    fot_sl_1        DOUBLE PRECISION,
    fot_sl_2        DOUBLE PRECISION,
    catalogado      BOOLEAN,
    tipo_mza        TEXT,
    sm              TEXT,
    alicuota        DOUBLE PRECISION,
    inc_uva_21      DOUBLE PRECISION,
    cpu_obs         TEXT,
    memo            TEXT,
    adps            TEXT,
    ae_fot_bas      DOUBLE PRECISION,
    raw             JSONB NOT NULL,
    fuente          TEXT NOT NULL DEFAULT 'BA Data - Código Urbanístico 2024-12-31',
    fuente_fecha    DATE NOT NULL DEFAULT DATE '2024-12-31',
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_barrio
    ON codigo_urbanistico (barrio);
CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_comuna
    ON codigo_urbanistico (comuna);
CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_zona
    ON codigo_urbanistico (dist_cpu_1);

-- -----------------------------------------------------------------------------
-- epok_direcciones: índice local de puertas EPOK (calle + altura), construido
-- desde epok_fichas.puertas. Evita depender de USIG para direcciones exactas.
-- Carga: python scripts/cargar_epok_direcciones.py
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS epok_direcciones (
    id                   BIGSERIAL PRIMARY KEY,
    smp                  TEXT NOT NULL REFERENCES epok_fichas(smp) ON DELETE CASCADE,
    calle                TEXT NOT NULL,
    calle_normalizada    TEXT NOT NULL,
    calle_base           TEXT NOT NULL,
    altura               INTEGER NOT NULL,
    codigo_calle         INTEGER NOT NULL,
    puerta_principal     BOOLEAN NOT NULL DEFAULT FALSE,
    puerta_oficial       BOOLEAN NOT NULL DEFAULT FALSE,
    fuente               TEXT,
    fecha_actualizacion  DATE,
    actualizado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_epok_direcciones_codigo_altura
    ON epok_direcciones (codigo_calle, altura);
CREATE INDEX IF NOT EXISTS idx_epok_direcciones_calle_altura
    ON epok_direcciones (calle_normalizada, altura);
CREATE INDEX IF NOT EXISTS idx_epok_direcciones_base_altura
    ON epok_direcciones (calle_base, altura);
CREATE INDEX IF NOT EXISTS idx_epok_direcciones_smp
    ON epok_direcciones (smp);
CREATE UNIQUE INDEX IF NOT EXISTS uq_epok_direcciones_smp_calle_altura
    ON epok_direcciones (smp, codigo_calle, altura, calle);
