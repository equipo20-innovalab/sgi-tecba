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
-- codigo_urbanistico: atributos completos del Código Urbanístico por parcela.
-- Fuente: data/processed/codigo_urbanistico_limpio.csv (318.126 SMP).
-- Los nombres y valores originales de todas las columnas se preservan en JSONB
-- (`datos`) y, además, se aplanan las columnas consultables más usadas.
-- Carga: python src/export_postgres.py --codigo-urbanistico
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS codigo_urbanistico (
    gid              BIGINT,
    smp              TEXT PRIMARY KEY,
    seccion          TEXT,
    manzana          TEXT,
    parcela          TEXT,
    uni_edif_1       DOUBLE PRECISION,
    uni_edif_2       DOUBLE PRECISION,
    uni_edif_3       DOUBLE PRECISION,
    uni_edif_4       DOUBLE PRECISION,
    uso_1            SMALLINT,
    uso_2            SMALLINT,
    uso_3            SMALLINT,
    dist_1_grp       TEXT,
    dist_1_esp       TEXT,
    dist_2_grp       TEXT,
    dist_2_esp       TEXT,
    dist_3_grp       TEXT,
    dist_3_esp       TEXT,
    dist_4_grp       TEXT,
    dist_4_esp       TEXT,
    zona_1           TEXT,
    zona_2           TEXT,
    anac             SMALLINT,
    ci_digital       SMALLINT,
    rh               SMALLINT,
    lep              SMALLINT,
    ensanche         SMALLINT,
    apertura         SMALLINT,
    catalogado       SMALLINT,
    tipo_mza         TEXT,
    rivolta          SMALLINT,
    barrio           TEXT,
    comuna           SMALLINT,
    plano_l          DOUBLE PRECISION,
    plano_l_ob       TEXT,
    dist_cpu_1       TEXT,
    dist_cpu_2       TEXT,
    fot_em_1         DOUBLE PRECISION,
    fot_em_2         DOUBLE PRECISION,
    fot_pl_1         DOUBLE PRECISION,
    fot_pl_2         DOUBLE PRECISION,
    fot_sl_1         DOUBLE PRECISION,
    fot_sl_2         DOUBLE PRECISION,
    cpu_base         TEXT,
    ae_fot_bas       DOUBLE PRECISION,
    cpu_obs          TEXT,
    alicuota         DOUBLE PRECISION,
    inc_uva_21       DOUBLE PRECISION,
    sm               TEXT,
    adps             TEXT,
    memo             DOUBLE PRECISION,
    microcentr       TEXT,
    datos            JSONB NOT NULL,
    cargado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Migración para instalaciones que ya tenían la tabla mínima (smp, datos).
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS gid BIGINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS seccion TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS manzana TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS parcela TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS uni_edif_1 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS uni_edif_2 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS uni_edif_3 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS uni_edif_4 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS uso_1 SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS uso_2 SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS uso_3 SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_1_grp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_1_esp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_2_grp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_2_esp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_3_grp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_3_esp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_4_grp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_4_esp TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS zona_1 TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS zona_2 TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS anac SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS ci_digital SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS rh SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS lep SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS ensanche SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS apertura SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS catalogado SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS tipo_mza TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS rivolta SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS barrio TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS comuna SMALLINT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS plano_l DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS plano_l_ob TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_cpu_1 TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS dist_cpu_2 TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS fot_em_1 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS fot_em_2 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS fot_pl_1 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS fot_pl_2 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS fot_sl_1 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS fot_sl_2 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS cpu_base TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS ae_fot_bas DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS cpu_obs TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS alicuota DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS inc_uva_21 DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS sm TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS adps TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS memo DOUBLE PRECISION;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS microcentr TEXT;
ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS cargado_en TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_comuna
    ON codigo_urbanistico (comuna);
CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_distrito
    ON codigo_urbanistico (dist_1_grp);
CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_uso
    ON codigo_urbanistico (uso_1);
CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_sm
    ON codigo_urbanistico (sm);

-- -----------------------------------------------------------------------------
-- urbanismo_cobertura: historial de corridas de integración CU + habilitaciones
-- + EPOK. Guarda métricas, versión y huella de las reglas y de las fuentes.
-- Carga: python src/export_postgres.py --codigo-urbanistico
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS urbanismo_cobertura (
    corrida_id                              BIGSERIAL PRIMARY KEY,
    reglas_version                          TEXT        NOT NULL,
    reglas_fecha                            DATE,
    reglas_sha256                           TEXT,
    generado_en                             TIMESTAMPTZ NOT NULL,
    fuente_codigo                           TEXT,
    fuente_codigo_sha256                    TEXT,
    fuente_habilitaciones                   TEXT,
    fuente_habilitaciones_sha256            TEXT,
    n_smp_codigo                            INTEGER     NOT NULL,
    n_smp_habilitaciones                    INTEGER     NOT NULL,
    n_smp_epok                              INTEGER,
    n_smp_interseccion                      INTEGER     NOT NULL,
    n_smp_codigo_y_epok                     INTEGER,
    cobertura_habilitaciones_por_smp        DOUBLE PRECISION,
    cobertura_codigo_usado_por_habilitaciones DOUBLE PRECISION,
    n_habilitaciones                        INTEGER     NOT NULL,
    n_habilitaciones_con_smp                INTEGER,
    n_habilitaciones_con_codigo             INTEGER,
    n_habilitaciones_con_epok               INTEGER,
    n_habilitaciones_con_codigo_y_epok      INTEGER,
    pct_habilitaciones_con_smp              DOUBLE PRECISION,
    pct_habilitaciones_con_codigo           DOUBLE PRECISION,
    pct_habilitaciones_con_epok             DOUBLE PRECISION,
    pct_habilitaciones_con_codigo_y_epok    DOUBLE PRECISION,
    clasificacion_codigo                    JSONB,
    clasificacion_habilitaciones            JSONB,
    estados_smp                             JSONB,
    estados_habilitaciones                  JSONB,
    familias_distrito                       JSONB,
    flags                                   JSONB,
    limitaciones                            JSONB,
    parametros                              JSONB,
    notas                                   TEXT,
    creado_en                               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_urbanismo_cobertura_reglas
    ON urbanismo_cobertura (reglas_version, generado_en DESC);

-- -----------------------------------------------------------------------------
-- urbanismo_smp: panel vigente, una fila por SMP, con la clasificación de la
-- clave, la presencia en CU/EPOK, los flags y el estado de compatibilidad
-- según la versión de reglas indicada. Se recarga en cada corrida.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS urbanismo_smp (
    smp                    TEXT PRIMARY KEY,
    smp_clasificacion      TEXT        NOT NULL,
    smp_valido             BOOLEAN     NOT NULL,
    codigo_presente        BOOLEAN     NOT NULL,
    epok_presente          BOOLEAN     NOT NULL,
    familia_distrito       TEXT        NOT NULL,
    estado_compatibilidad  TEXT        NOT NULL,
    regla_id               TEXT,
    motivo                 TEXT,
    reglas_version         TEXT        NOT NULL,
    n_habilitaciones       INTEGER     NOT NULL DEFAULT 0,
    n_comunas_habilitaciones SMALLINT,
    primer_anio            SMALLINT,
    ultimo_anio            SMALLINT,
    flags                  JSONB       NOT NULL DEFAULT '{}'::jsonb,
    calculado_en           TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_urbanismo_smp_clasificacion
        CHECK (smp_clasificacion IN ('estandar', 'ampliado', 'placeholder', 'invalido', 'sin_dato')),
    CONSTRAINT ck_urbanismo_smp_estado
        CHECK (estado_compatibilidad IN ('compatible', 'requiere_revision', 'no_compatible', 'no_verificable'))
);

CREATE INDEX IF NOT EXISTS idx_urbanismo_smp_estado
    ON urbanismo_smp (estado_compatibilidad);
CREATE INDEX IF NOT EXISTS idx_urbanismo_smp_clasificacion
    ON urbanismo_smp (smp_clasificacion);
CREATE INDEX IF NOT EXISTS idx_urbanismo_smp_familia
    ON urbanismo_smp (familia_distrito);

-- Vista estable del panel vigente (la tabla ya contiene una sola corrida).
CREATE OR REPLACE VIEW urbanismo_smp_actual AS
SELECT *
FROM urbanismo_smp;

-- Vista de la última corrida de cobertura.
CREATE OR REPLACE VIEW urbanismo_cobertura_actual AS
SELECT c.*
FROM urbanismo_cobertura AS c
WHERE c.corrida_id = (SELECT max(corrida_id) FROM urbanismo_cobertura);

-- Cruce listo para consultar: una fila por habilitación, con la parcela del
-- Código Urbanístico, el estado de compatibilidad y el perfil EPOK cuando
-- existe. No duplica el padrón: es una vista.
CREATE OR REPLACE VIEW urbanismo_habilitaciones AS
SELECT
    h.solicitud,
    h.fecha_habilitacion,
    h.anio,
    h.codigo_rubro,
    h.descripcion_rubro,
    h.superficie,
    h.comuna,
    h.smp,
    u.smp_clasificacion,
    u.codigo_presente,
    u.epok_presente,
    u.familia_distrito,
    u.estado_compatibilidad,
    u.regla_id,
    u.motivo,
    u.reglas_version,
    c.uso_1,
    c.uso_2,
    c.uso_3,
    c.dist_1_grp,
    c.dist_1_esp,
    c.catalogado,
    c.rh,
    c.lep,
    c.ensanche,
    c.apertura,
    c.anac,
    c.ci_digital,
    c.rivolta,
    c.dist_cpu_1,
    e.direccion              AS epok_direccion,
    e.superficie_total       AS epok_superficie_total,
    e.superficie_cubierta    AS epok_superficie_cubierta,
    e.pisos_sobre_rasante    AS epok_pisos_sobre_rasante,
    e.unidades_funcionales   AS epok_unidades_funcionales,
    e.lng                    AS epok_lng,
    e.lat                    AS epok_lat
FROM habilitaciones AS h
LEFT JOIN urbanismo_smp AS u ON u.smp = h.smp
LEFT JOIN codigo_urbanistico AS c ON c.smp = h.smp
LEFT JOIN epok_fichas AS e ON e.smp = h.smp;

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
