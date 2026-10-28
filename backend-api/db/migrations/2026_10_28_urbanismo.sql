-- =============================================================================
-- Urbanismo: Código Urbanístico + índice local de direcciones EPOK
-- Ejecutar con: psql "$DATABASE_URL" -f db/migrations/2026_10_28_urbanismo.sql
-- =============================================================================

-- Código Urbanístico (BA Data, actualizado al 31/12/2024).
-- El CSV original trae el sufijo de SMP en minúscula; el backend normaliza a
-- mayúscula para hacer join con EPOK.
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

-- Direcciones oficiales de EPOK, desnormalizadas desde epok_fichas.puertas
-- para resolver "calle + altura" sin depender siempre de USIG.
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
