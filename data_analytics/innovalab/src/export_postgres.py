"""Carga datos hacia PostgreSQL.

Cubre cuatro fuentes:

1. `rubros_requisitos` (desde `db/seed/rubros_requisitos.csv`, versionado): tabla
   de referencia rubro → trámites + documentación. Idempotente (UPSERT).
2. `habilitaciones` (desde `data/processed/habilitaciones_caba_clean.csv`, NO
   versionado — se genera corriendo el pipeline): padrón completo de ~217k filas.
   Recarga con TRUNCATE + COPY.
3. `indice_oportunidad` (desde el padrón): calcula el índice, escribe un
   artefacto reproducible (`indice_oportunidad.csv` + `_meta.json`) y lo carga
   con historial en `indice_oportunidad` / `indice_oportunidad_meta`.
4. `codigo_urbanistico` + `urbanismo_smp` + `urbanismo_cobertura`: carga el
   Código Urbanístico aplanado, valida los SMP y cruza el padrón con EPOK
   usando las reglas versionadas de `db/seed/reglas_compatibilidad_urbanistica.json`.

Requiere PostgreSQL. Usa `DATABASE_URL` si está definido; si no, cae al socket
local con la base `innovalab` (o `PGDATABASE`).

Uso:
    python src/export_postgres.py                  # carga rubros_requisitos
    python src/export_postgres.py --habilitaciones # carga el padrón
    python src/export_postgres.py --codigo-urbanistico # CU + urbanismo + artefactos
    python src/export_postgres.py --oportunidad    # índice + artefacto + tabla
    python src/export_postgres.py --all            # carga todas las fuentes
    python src/export_postgres.py --dry-run        # solo valida, no escribe
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

RAIZ = Path(__file__).resolve().parent.parent
# Permite `from src.oportunidad import ...` tanto si se ejecuta como script
# (python src/export_postgres.py) como si se importa desde pytest.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

CSV_SEED = RAIZ / "db" / "seed" / "rubros_requisitos.csv"
CSV_HAB = RAIZ / "data" / "processed" / "habilitaciones_caba_clean.csv"
CSV_CODIGO = CSV_HAB.with_name("codigo_urbanistico_limpio.csv")
CSV_OPORTUNIDAD = CSV_HAB.with_name("indice_oportunidad.csv")
JSON_OPORTUNIDAD_META = CSV_HAB.with_name("indice_oportunidad_meta.json")
CSV_URBANISMO = CSV_HAB.with_name("urbanismo_smp.csv")
JSON_URBANISMO_COBERTURA = CSV_HAB.with_name("urbanismo_cobertura.json")
RUTA_REGLAS_URBANISMO = RAIZ / "db" / "seed" / "reglas_compatibilidad_urbanistica.json"


def _dsn() -> str:
    """DSN de PostgreSQL.

    Prioriza ``DATABASE_URL`` y, si no está definido, cae al socket local con
    la base ``innovalab`` (el mismo default que usa ``psql -d innovalab``).
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        dsn = os.environ.get("PGDATABASE") or "dbname=innovalab"
    if dsn.startswith("postgresql+psycopg://"):
        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return dsn


# --- rubros_requisitos -------------------------------------------------------
COLUMNAS = ("rubro", "tramite", "etapa", "orden", "obligatorio", "aplica_cuando",
            "documentacion_requerida", "organismo", "link_oficial")

UPSERT_SQL = """
    INSERT INTO rubros_requisitos (rubro, tramite, etapa, orden, obligatorio, aplica_cuando,
                                   documentacion_requerida, organismo, link_oficial)
    VALUES (%(rubro)s, %(tramite)s, %(etapa)s, %(orden)s, %(obligatorio)s, %(aplica_cuando)s,
            %(documentacion_requerida)s, %(organismo)s, %(link_oficial)s)
    ON CONFLICT (rubro, tramite) DO UPDATE
        SET etapa                   = EXCLUDED.etapa,
            orden                   = EXCLUDED.orden,
            obligatorio             = EXCLUDED.obligatorio,
            aplica_cuando           = EXCLUDED.aplica_cuando,
            documentacion_requerida = EXCLUDED.documentacion_requerida,
            organismo               = EXCLUDED.organismo,
            link_oficial            = EXCLUDED.link_oficial,
            actualizado_en          = now()
"""

# --- habilitaciones ----------------------------------------------------------
COLS_HAB = (
    "solicitud", "tipo_tramite", "tipo_expediente", "subtipo_expediente",
    "fecha_habilitacion", "fecha_fuente", "numero_expediente", "codigo_rubro", "descripcion_rubro",
    "superficie", "seccion", "manzana", "parcela", "smp", "smp_fuente", "calles", "comuna",
    "comuna_fuente", "razon_social", "partida_matriz", "origen", "anio",
)
INT_HAB = {"solicitud", "comuna", "anio"}
FLOAT_HAB = {"codigo_rubro", "superficie"}


def leer_seed(ruta: Path = CSV_SEED) -> list[dict[str, str]]:
    """Lee el CSV seed y devuelve una lista de filas como dicts."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el CSV seed: {ruta}")

    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        faltantes = [c for c in COLUMNAS if c not in (lector.fieldnames or [])]
        if faltantes:
            raise ValueError(f"El CSV no tiene las columnas requeridas: {faltantes}")

        filas: list[dict[str, str]] = []
        for fila in lector:
            limpia = {c: (fila.get(c) or "").strip() for c in COLUMNAS}
            if not limpia["rubro"] or not limpia["tramite"]:
                continue
            # Columnas opcionales: cadena vacía -> NULL.
            for opcional in ("etapa", "obligatorio", "aplica_cuando", "organismo", "link_oficial"):
                limpia[opcional] = limpia[opcional] or None
            # 'orden' es entero; vacío -> NULL.
            limpia["orden"] = int(limpia["orden"]) if limpia["orden"] else None
            filas.append(limpia)
    return filas


def cargar_rubros(filas: list[dict[str, str]], dry_run: bool = False) -> int:
    """Conecta a Postgres y hace UPSERT de las filas. Devuelve la cantidad escrita."""
    if dry_run:
        return len(filas)
    dsn = os.environ.get("DATABASE_URL")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.executemany(UPSERT_SQL, filas)
    return len(filas)


def _conv_hab(campo: str, valor: str | None) -> object:
    """Convierte un campo del CSV al tipo nativo de Python (None = NULL)."""
    v = (valor or "").strip()
    if v == "" or v.lower() == "nan":
        return None
    if campo in INT_HAB:
        try:
            return int(float(v))
        except ValueError:
            return None
    if campo in FLOAT_HAB:
        try:
            return float(v)
        except ValueError:
            return None
    if campo == "fecha_habilitacion":
        try:
            return date.fromisoformat(v[:10])
        except ValueError:
            return None
    return v


def leer_habilitaciones(ruta: Path = CSV_HAB) -> list[tuple]:
    """Lee el CSV de habilitaciones y devuelve tuplas tipadas para COPY."""
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el CSV de habilitaciones: {ruta}\n"
            "  Se genera con python -m src.run_pipeline --build-only."
        )
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        faltantes = [c for c in COLS_HAB if c not in (lector.fieldnames or [])]
        if faltantes:
            raise ValueError(f"El CSV de habilitaciones no tiene las columnas: {faltantes}")
        return [tuple(_conv_hab(c, fila.get(c)) for c in COLS_HAB) for fila in lector]


def cargar_habilitaciones(registros: list[tuple], dry_run: bool = False) -> int:
    """TRUNCATE + COPY de habilitaciones. Devuelve la cantidad escrita."""
    if dry_run:
        return len(registros)
    dsn = os.environ.get("DATABASE_URL")
    cols = ", ".join(COLS_HAB)
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE habilitaciones RESTART IDENTITY")
        with cur.copy(f"COPY habilitaciones ({cols}) FROM STDIN") as copy:
            for reg in registros:
                copy.write_row(reg)
    return len(registros)


# --- codigo_urbanistico ------------------------------------------------------
# Mantener sincronizado con db/schema.sql. La tabla conserva la fila completa
# en JSONB y aplana las columnas consultables.
COLS_CODIGO = (
    ("gid", "BIGINT"),
    ("seccion", "TEXT"),
    ("manzana", "TEXT"),
    ("parcela", "TEXT"),
    ("uni_edif_1", "DOUBLE PRECISION"),
    ("uni_edif_2", "DOUBLE PRECISION"),
    ("uni_edif_3", "DOUBLE PRECISION"),
    ("uni_edif_4", "DOUBLE PRECISION"),
    ("uso_1", "SMALLINT"),
    ("uso_2", "SMALLINT"),
    ("uso_3", "SMALLINT"),
    ("dist_1_grp", "TEXT"),
    ("dist_1_esp", "TEXT"),
    ("dist_2_grp", "TEXT"),
    ("dist_2_esp", "TEXT"),
    ("dist_3_grp", "TEXT"),
    ("dist_3_esp", "TEXT"),
    ("dist_4_grp", "TEXT"),
    ("dist_4_esp", "TEXT"),
    ("zona_1", "TEXT"),
    ("zona_2", "TEXT"),
    ("anac", "SMALLINT"),
    ("ci_digital", "SMALLINT"),
    ("rh", "SMALLINT"),
    ("lep", "SMALLINT"),
    ("ensanche", "SMALLINT"),
    ("apertura", "SMALLINT"),
    ("catalogado", "SMALLINT"),
    ("tipo_mza", "TEXT"),
    ("rivolta", "SMALLINT"),
    ("barrio", "TEXT"),
    ("comuna", "SMALLINT"),
    ("plano_l", "DOUBLE PRECISION"),
    ("plano_l_ob", "TEXT"),
    ("dist_cpu_1", "TEXT"),
    ("dist_cpu_2", "TEXT"),
    ("fot_em_1", "DOUBLE PRECISION"),
    ("fot_em_2", "DOUBLE PRECISION"),
    ("fot_pl_1", "DOUBLE PRECISION"),
    ("fot_pl_2", "DOUBLE PRECISION"),
    ("fot_sl_1", "DOUBLE PRECISION"),
    ("fot_sl_2", "DOUBLE PRECISION"),
    ("cpu_base", "TEXT"),
    ("ae_fot_bas", "DOUBLE PRECISION"),
    ("cpu_obs", "TEXT"),
    ("alicuota", "DOUBLE PRECISION"),
    ("inc_uva_21", "DOUBLE PRECISION"),
    ("sm", "TEXT"),
    ("adps", "TEXT"),
    ("memo", "DOUBLE PRECISION"),
    ("microcentr", "TEXT"),
    ("datos", "JSONB"),
)
INT_CODIGO = {
    "gid", "uso_1", "uso_2", "uso_3", "anac", "ci_digital", "rh", "lep",
    "ensanche", "apertura", "catalogado", "rivolta", "comuna",
}
FLOAT_CODIGO = {
    "uni_edif_1", "uni_edif_2", "uni_edif_3", "uni_edif_4", "plano_l",
    "fot_em_1", "fot_em_2", "fot_pl_1", "fot_pl_2", "fot_sl_1", "fot_sl_2",
    "ae_fot_bas", "alicuota", "inc_uva_21", "memo",
}
SQL_TABLA_CODIGO = (
    "CREATE TABLE IF NOT EXISTS codigo_urbanistico ("
    "smp TEXT PRIMARY KEY, datos JSONB NOT NULL);\n"
    + "\n".join(
        f"ALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS {nombre} {tipo};"
        for nombre, tipo in COLS_CODIGO
    )
    + "\nALTER TABLE codigo_urbanistico ADD COLUMN IF NOT EXISTS cargado_en "
      "TIMESTAMPTZ NOT NULL DEFAULT now();\n"
      "CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_comuna ON codigo_urbanistico (comuna);\n"
      "CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_distrito ON codigo_urbanistico (dist_1_grp);\n"
      "CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_uso ON codigo_urbanistico (uso_1);\n"
      "CREATE INDEX IF NOT EXISTS idx_codigo_urbanistico_sm ON codigo_urbanistico (sm);\n"
)
COLS_CODIGO_COPY = ("smp",) + tuple(nombre for nombre, _ in COLS_CODIGO)


def _python(valor):
    """Convierte escalares de numpy/pandas a tipos nativos de Python."""
    import pandas as pd

    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(valor, "item"):
        try:
            return valor.item()
        except (ValueError, AttributeError):
            pass
    return valor


def _conv_codigo(campo: str, valor):
    """Convierte un campo del Código Urbanístico al tipo de PostgreSQL."""
    valor = _python(valor)
    if valor is None:
        return None
    if campo in INT_CODIGO:
        try:
            return int(float(valor))
        except (TypeError, ValueError):
            return None
    if campo in FLOAT_CODIGO:
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None
    texto = str(valor).strip()
    return texto or None


def cargar_codigo_urbanistico(
    ruta: Path = CSV_CODIGO,
    dry_run: bool = False,
    df=None,
) -> int:
    """Carga el Código Urbanístico aplanado y conserva la fila completa en JSONB.

    Valida la clave SMP (sin nulos, duplicados ni formatos inválidos) antes de
    escribir. Los ``placeholder`` de parcela ``000`` se aceptan porque existen
    en la fuente oficial.
    """
    import pandas as pd

    from src.urbanismo import clasificar_smps, normalizar_smp

    if df is None:
        if not ruta.exists():
            raise FileNotFoundError(f"No se encontró el CSV del Código Urbanístico: {ruta}")
        df = pd.read_csv(ruta, encoding="utf-8-sig", low_memory=False)

    if "smp" not in df.columns:
        raise ValueError("El CSV del Código Urbanístico debe incluir una columna 'smp'.")

    base = df.copy()
    base["smp"] = base["smp"].map(normalizar_smp)
    if base["smp"].isna().any():
        raise ValueError("El Código Urbanístico contiene SMP nulas o vacías.")
    if base["smp"].duplicated().any():
        duplicadas = base.loc[base["smp"].duplicated(), "smp"].head(5).tolist()
        raise ValueError(f"El Código Urbanístico contiene SMP duplicadas: {duplicadas}")
    clasificacion = clasificar_smps(base["smp"])
    if clasificacion.eq("invalido").any():
        ejemplos = base.loc[clasificacion.eq("invalido"), "smp"].head(10).tolist()
        raise ValueError(
            f"El Código Urbanístico contiene SMP con formato inválido: {ejemplos}"
        )

    total = len(base)
    if dry_run:
        return total

    columnas_datos = list(base.columns)
    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
        cur.execute(SQL_TABLA_CODIGO)
        cur.execute("TRUNCATE codigo_urbanistico")
        with cur.copy(
            f"COPY codigo_urbanistico ({', '.join(COLS_CODIGO_COPY)}) FROM STDIN"
        ) as copy:
            for valores in base.loc[:, columnas_datos].itertuples(index=False, name=None):
                fila = dict(zip(columnas_datos, valores))
                smp = fila.pop("smp")
                datos = {columna: _python(valor) for columna, valor in fila.items()}
                datos["smp"] = smp
                copy.write_row(
                    (smp,)
                    + tuple(
                        Jsonb(datos) if nombre == "datos" else _conv_codigo(nombre, fila.get(nombre))
                        for nombre in COLS_CODIGO_COPY[1:]
                    )
                )
    return total



# --- indice_oportunidad ------------------------------------------------------
# Mantener sincronizado con db/schema.sql (mismas columnas y tipos).
SQL_TABLA_OPORTUNIDAD = """
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

    CREATE OR REPLACE VIEW indice_oportunidad_actual AS
    SELECT i.*
    FROM indice_oportunidad AS i
    WHERE i.calculo_id = (SELECT max(calculo_id) FROM indice_oportunidad_meta);
"""

COLS_OPORTUNIDAD_COPY = (
    "calculo_id", "formula_version", "calculado_en", "comuna", "rubro",
    "oportunidad", "componente_crecimiento", "componente_baja_saturacion",
    "componente_subrepresentacion", "peso_crecimiento", "peso_baja_saturacion",
    "peso_subrepresentacion", "aporte_crecimiento", "aporte_baja_saturacion",
    "aporte_subrepresentacion", "crecimiento", "saturacion", "subrepresentacion",
    "n_licencias", "n_nuevas", "superficie_promedio", "anio_ref", "explicacion",
)


def _sha256_archivo(ruta: Path) -> str:
    """Huella SHA-256 del archivo de origen (para reproducibilidad)."""
    digest = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def leer_habilitaciones_df(ruta: Path = CSV_HAB):
    """Lee el padrón como DataFrame (import perezoso de pandas)."""
    import pandas as pd

    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el CSV de habilitaciones: {ruta}")
    return pd.read_csv(ruta, encoding="utf-8-sig", low_memory=False)


def _valor_oportunidad(valor, campo: str):
    """Convierte un valor de pandas a un tipo aceptado por PostgreSQL."""
    import pandas as pd

    if campo == "calculado_en":
        return pd.Timestamp(valor).to_pydatetime()
    if campo in {"comuna", "n_licencias", "n_nuevas", "anio_ref"}:
        return None if pd.isna(valor) else int(valor)
    if campo == "rubro":
        return str(valor)
    if campo in {"formula_version", "explicacion"}:
        return str(valor)
    return None if pd.isna(valor) else float(valor)


def cargar_oportunidad(artefacto, meta: dict, dry_run: bool = False) -> int:
    """Inserta la corrida en ``indice_oportunidad_meta`` + ``indice_oportunidad``.

    Es append-only: cada corrida conserva su ``calculo_id`` para auditoría.
    La vista ``indice_oportunidad_actual`` expone solo la última.
    """
    if dry_run:
        return len(artefacto)

    dsn = os.environ.get("DATABASE_URL")
    filas = artefacto.to_dict(orient="records")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(SQL_TABLA_OPORTUNIDAD)
        cur.execute(
            """
            INSERT INTO indice_oportunidad_meta
                (formula_version, calculado_en, pesos, parametros, n_filas,
                 n_comunas, n_rubros, anio_ref, fuente, fuente_sha256, notas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING calculo_id
            """,
            (
                meta["formula_version"],
                meta["calculado_en"],
                Jsonb(meta["pesos"]),
                Jsonb(meta["parametros"]),
                meta["n_filas"],
                meta.get("n_comunas"),
                meta.get("n_rubros"),
                meta.get("anio_ref"),
                meta.get("fuente"),
                meta.get("fuente_sha256"),
                meta.get("notas"),
            ),
        )
        calculo_id = int(cur.fetchone()[0])

        cols = ", ".join(COLS_OPORTUNIDAD_COPY)
        with cur.copy(f"COPY indice_oportunidad ({cols}) FROM STDIN") as copy:
            for fila in filas:
                copy.write_row(
                    (calculo_id,)
                    + tuple(
                        _valor_oportunidad(fila[campo], campo)
                        for campo in COLS_OPORTUNIDAD_COPY[1:]
                    )
                )
    return len(filas)


def exportar_oportunidad(
    *,
    min_licencias: int = 5,
    top_rubros: int | None = None,
    anio_ref: int | None = None,
    dry_run: bool = False,
    cargar_db: bool = True,
) -> dict:
    """Calcula el índice, escribe CSV + metadatos y (opcional) lo carga en Postgres.

    Devuelve los metadatos de la corrida. Aunque falle la carga en la base,
    los artefactos quedan escritos para poder inspeccionarlos o versionarlos.
    """
    from src.oportunidad import construir_artefacto_oportunidad, metadatos_artefacto

    if not CSV_HAB.exists():
        raise FileNotFoundError(f"No se encontró el CSV de habilitaciones: {CSV_HAB}")

    df = leer_habilitaciones_df()
    artefacto = construir_artefacto_oportunidad(
        df,
        min_licencias=min_licencias,
        top_rubros=top_rubros,
        anio_ref=anio_ref,
    )
    meta = metadatos_artefacto(
        artefacto,
        fuente=str(CSV_HAB),
        fuente_sha256=_sha256_archivo(CSV_HAB),
        parametros={
            "min_licencias": int(min_licencias),
            "top_rubros": top_rubros,
        },
    )

    if dry_run:
        return meta

    artefacto.to_csv(CSV_OPORTUNIDAD, index=False, encoding="utf-8")
    JSON_OPORTUNIDAD_META.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[oportunidad] artefacto: {CSV_OPORTUNIDAD}")
    print(f"[oportunidad] metadatos: {JSON_OPORTUNIDAD_META}")

    if cargar_db:
        try:
            cargar_oportunidad(artefacto, meta)
            print(f"[oportunidad] filas cargadas en BD: {len(artefacto):,}")
        except psycopg.Error as exc:
            print(
                "[oportunidad] AVISO: no se pudo cargar en la BD "
                f"({exc.__class__.__name__}: {exc}). El CSV y los metadatos "
                "quedaron escritos.",
                file=sys.stderr,
            )
    return meta


# --- urbanismo ---------------------------------------------------------------
# Mantener sincronizado con db/schema.sql.
SQL_TABLA_URBANISMO = """
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

    CREATE OR REPLACE VIEW urbanismo_smp_actual AS
    SELECT * FROM urbanismo_smp;

    CREATE OR REPLACE VIEW urbanismo_cobertura_actual AS
    SELECT c.*
    FROM urbanismo_cobertura AS c
    WHERE c.corrida_id = (SELECT max(corrida_id) FROM urbanismo_cobertura);
"""

SQL_VISTA_URBANISMO_HABILITACIONES = """
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
"""

COLS_URBANISMO_COPY = (
    "smp", "smp_clasificacion", "smp_valido", "codigo_presente",
    "epok_presente", "familia_distrito", "estado_compatibilidad", "regla_id",
    "motivo", "reglas_version", "n_habilitaciones", "n_comunas_habilitaciones",
    "primer_anio", "ultimo_anio", "flags", "calculado_en",
)


def leer_epok_df():
    """Lee las fichas EPOK de PostgreSQL; devuelve None si no están disponibles."""
    import pandas as pd

    columnas = (
        "smp", "direccion", "superficie_total", "superficie_cubierta",
        "pisos_sobre_rasante", "unidades_funcionales", "lng", "lat",
    )
    try:
        with psycopg.connect(_dsn(), connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(columnas)} FROM epok_fichas")
            filas = cur.fetchall()
        return pd.DataFrame(filas, columns=list(columnas))
    except psycopg.Error as exc:
        print(
            "[urbanismo] AVISO: no se pudo leer epok_fichas "
            f"({exc.__class__.__name__}: {exc}). Se sigue sin EPOK.",
            file=sys.stderr,
        )
        return None


def _valor_urbanismo(valor, campo: str):
    """Convierte un valor del panel a un tipo aceptable por PostgreSQL."""
    import pandas as pd

    if campo == "calculado_en":
        return pd.Timestamp(valor).to_pydatetime()
    if campo == "flags":
        return Jsonb(valor or {})
    if campo in {"smp_valido", "codigo_presente", "epok_presente"}:
        return None if pd.isna(valor) else bool(valor)
    if campo in {"n_habilitaciones", "n_comunas_habilitaciones", "primer_anio", "ultimo_anio"}:
        return None if pd.isna(valor) else int(valor)
    if campo in {"smp", "smp_clasificacion", "familia_distrito", "estado_compatibilidad", "reglas_version"}:
        return str(valor)
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return None
    return str(valor)


def cargar_urbanismo(panel, cobertura: dict, dry_run: bool = False) -> int:
    """Carga la corrida de cobertura y el panel vigente por SMP.

    ``urbanismo_cobertura`` es append-only (historial). ``urbanismo_smp`` se
    recarga completa porque representa el estado vigente de la última corrida.
    """
    import pandas as pd

    from src.urbanismo import FLAGS_CODIGO

    if dry_run:
        return len(panel)

    resumen = cobertura["resumen"]
    fuentes = cobertura.get("fuentes", {})
    fuente_codigo = fuentes.get("codigo_urbanistico", {})
    fuente_hab = fuentes.get("habilitaciones", {})
    reglas = cobertura["reglas"]

    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
        cur.execute(SQL_TABLA_URBANISMO)
        cur.execute(
            """
            INSERT INTO urbanismo_cobertura (
                reglas_version, reglas_fecha, reglas_sha256, generado_en,
                fuente_codigo, fuente_codigo_sha256,
                fuente_habilitaciones, fuente_habilitaciones_sha256,
                n_smp_codigo, n_smp_habilitaciones, n_smp_epok,
                n_smp_interseccion, n_smp_codigo_y_epok,
                cobertura_habilitaciones_por_smp,
                cobertura_codigo_usado_por_habilitaciones,
                n_habilitaciones, n_habilitaciones_con_smp,
                n_habilitaciones_con_codigo, n_habilitaciones_con_epok,
                n_habilitaciones_con_codigo_y_epok,
                pct_habilitaciones_con_smp, pct_habilitaciones_con_codigo,
                pct_habilitaciones_con_epok, pct_habilitaciones_con_codigo_y_epok,
                clasificacion_codigo, clasificacion_habilitaciones,
                estados_smp, estados_habilitaciones, familias_distrito,
                flags, limitaciones, parametros, notas
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s
            )
            RETURNING corrida_id
            """,
            (
                reglas["version"],
                date.fromisoformat(str(reglas["fecha"])[:10]),
                reglas.get("sha256"),
                cobertura["generado_en"],
                fuente_codigo.get("ruta"),
                fuente_codigo.get("sha256"),
                fuente_hab.get("ruta"),
                fuente_hab.get("sha256"),
                resumen["smp_codigo"],
                resumen["smp_habilitaciones"],
                resumen.get("smp_epok"),
                resumen["smp_interseccion"],
                resumen.get("smp_codigo_y_epok"),
                resumen.get("cobertura_habilitaciones_por_smp"),
                resumen.get("cobertura_codigo_usado_por_habilitaciones"),
                resumen["habilitaciones"],
                resumen.get("habilitaciones_con_smp"),
                resumen.get("habilitaciones_con_codigo"),
                resumen.get("habilitaciones_con_epok"),
                resumen.get("habilitaciones_con_codigo_y_epok"),
                resumen.get("pct_habilitaciones_con_smp"),
                resumen.get("pct_habilitaciones_con_codigo"),
                resumen.get("pct_habilitaciones_con_epok"),
                resumen.get("pct_habilitaciones_con_codigo_y_epok"),
                Jsonb(cobertura.get("clasificacion_smp", {})),
                Jsonb(cobertura.get("clasificacion_habilitaciones", {})),
                Jsonb(cobertura.get("estados_smp", {})),
                Jsonb(cobertura.get("estados_habilitaciones", {})),
                Jsonb(cobertura.get("familias_distrito", {})),
                Jsonb(cobertura.get("flags", {})),
                Jsonb(cobertura.get("limitaciones", [])),
                Jsonb(cobertura.get("parametros", {})),
                f"Reglas {reglas['version']} · {len(panel):,} SMP",
            ),
        )

        cur.execute("TRUNCATE urbanismo_smp")
        columnas = list(panel.columns)
        with cur.copy(
            f"COPY urbanismo_smp ({', '.join(COLS_URBANISMO_COPY)}) FROM STDIN"
        ) as copy:
            for valores in panel.itertuples(index=False, name=None):
                fila = dict(zip(columnas, valores))
                flags = {
                    destino: (
                        None
                        if pd.isna(fila[destino])
                        else bool(fila[destino])
                    )
                    for destino in FLAGS_CODIGO.values()
                }
                fila["flags"] = flags
                copy.write_row(
                    tuple(_valor_urbanismo(fila.get(campo), campo) for campo in COLS_URBANISMO_COPY)
                )

        # La vista de habilitaciones solo se puede crear si esas tablas existen.
        cur.execute(
            "SELECT to_regclass('public.habilitaciones'), to_regclass('public.epok_fichas')"
        )
        habilitaciones_existe, epok_existe = cur.fetchone()
        if habilitaciones_existe and epok_existe:
            cur.execute(SQL_VISTA_URBANISMO_HABILITACIONES)

    return len(panel)


def exportar_urbanismo(
    *,
    ruta_reglas: Path = RUTA_REGLAS_URBANISMO,
    dry_run: bool = False,
    cargar_db: bool = True,
    leer_epok: bool = True,
) -> dict:
    """Genera los artefactos de urbanismo y, si se puede, los carga en Postgres.

    Los artefactos (``urbanismo_smp.csv`` y ``urbanismo_cobertura.json``) se
    escriben antes de intentar la carga. Si la base falla (por ejemplo, por
    permisos), la corrida queda auditable en disco.
    """
    import pandas as pd

    from src.urbanismo import (
        cargar_reglas,
        construir_panel_smp,
        escribir_artefactos_urbanismo,
        generar_cobertura,
    )

    if not CSV_CODIGO.exists():
        raise FileNotFoundError(f"No se encontró el CSV del Código Urbanístico: {CSV_CODIGO}")
    if not CSV_HAB.exists():
        raise FileNotFoundError(f"No se encontró el CSV de habilitaciones: {CSV_HAB}")
    if not Path(ruta_reglas).is_file():
        raise FileNotFoundError(f"No se encontró el archivo de reglas: {ruta_reglas}")

    codigo = pd.read_csv(CSV_CODIGO, encoding="utf-8-sig", low_memory=False)
    habilitaciones = leer_habilitaciones_df()
    reglas = cargar_reglas(ruta_reglas)
    epok = leer_epok_df() if leer_epok else None
    calculado_en = pd.Timestamp.now(tz="UTC")

    panel = construir_panel_smp(
        codigo,
        habilitaciones,
        epok,
        reglas,
        calculado_en=calculado_en,
    )
    fuentes = {
        "codigo_urbanistico": {
            "ruta": str(CSV_CODIGO),
            "sha256": _sha256_archivo(CSV_CODIGO),
            "filas": int(len(codigo)),
            "smp_unicos": int(codigo["smp"].nunique()),
        },
        "habilitaciones": {
            "ruta": str(CSV_HAB),
            "sha256": _sha256_archivo(CSV_HAB),
            "filas": int(len(habilitaciones)),
        },
        "epok_fichas": {
            "ruta": "tabla epok_fichas",
            "disponible": epok is not None,
            "filas": None if epok is None else int(len(epok)),
        },
    }
    cobertura = generar_cobertura(
        codigo,
        habilitaciones,
        panel,
        reglas,
        fuentes=fuentes,
        parametros={
            "reglas_version": reglas["version"],
            "epok_disponible": epok is not None,
        },
        generado_en=calculado_en,
    )

    if dry_run:
        return cobertura

    cobertura = escribir_artefactos_urbanismo(panel, cobertura)
    print(f"[urbanismo] panel: {CSV_URBANISMO}")
    print(f"[urbanismo] cobertura: {JSON_URBANISMO_COBERTURA}")

    resumen = cobertura["resumen"]
    print(
        f"[urbanismo] reglas {cobertura['reglas']['version']} · "
        f"{len(panel):,} SMP · "
        f"{resumen['smp_interseccion']:,} SMP en CU y habilitaciones "
        f"({resumen['cobertura_habilitaciones_por_smp']:.1%}) · "
        f"{resumen['habilitaciones_con_codigo']:,}/{resumen['habilitaciones']:,} "
        f"habilitaciones con CU ({resumen['pct_habilitaciones_con_codigo']:.1%}) · "
        f"{resumen['habilitaciones_con_epok']:,} con EPOK"
    )

    if cargar_db:
        try:
            filas_codigo = cargar_codigo_urbanistico(df=codigo)
            filas_smp = cargar_urbanismo(panel, cobertura)
            print(
                f"[urbanismo] filas cargadas en BD: "
                f"{filas_codigo:,} Código Urbanístico · {filas_smp:,} SMP"
            )
        except psycopg.Error as exc:
            print(
                "[urbanismo] AVISO: no se pudo cargar en la BD "
                f"({exc.__class__.__name__}: {exc}). Los artefactos quedaron escritos.",
                file=sys.stderr,
            )
    return cobertura


def contar_en_db(tabla: str) -> int | None:
    """Devuelve la cantidad de filas de una tabla, o None si no hay conexión."""
    dsn = os.environ.get("DATABASE_URL")
    try:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {tabla}")  # tabla fija, no input de usuario
            return int(cur.fetchone()[0])
    except Exception:
        return None


def _requiere_db() -> int | None:
    """Devuelve 2 e imprime error si falta DATABASE_URL; None si está OK."""
    if not os.environ.get("DATABASE_URL"):
        print("ERROR: definí la variable DATABASE_URL antes de cargar.", file=sys.stderr)
        print('  Ejemplo: export DATABASE_URL="postgresql://usuario:clave@localhost:5432/innovalab"', file=sys.stderr)
        return 2
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga datos de referencia, habilitaciones e índice de oportunidad hacia PostgreSQL.")
    parser.add_argument("--rubros", action="store_true", help="Carga rubros_requisitos.")
    parser.add_argument("--habilitaciones", action="store_true", help="Carga el padrón de habilitaciones.")
    parser.add_argument("--codigo-urbanistico", action="store_true", help="Carga y cruza el Código Urbanístico (genera artefactos de urbanismo).")
    parser.add_argument("--reglas", default=str(RUTA_REGLAS_URBANISMO), help="Archivo JSON de reglas de compatibilidad urbanística.")
    parser.add_argument("--sin-epok", action="store_true", help="Omite la lectura de epok_fichas al construir el panel.")
    parser.add_argument("--oportunidad", action="store_true", help="Calcula, exporta y carga el índice de oportunidad.")
    parser.add_argument("--min-licencias", type=int, default=5, help="Umbral de licencias para el índice (default: 5).")
    parser.add_argument("--top-rubros", type=int, default=None, help="Limita el índice a los N rubros más frecuentes.")
    parser.add_argument("--all", action="store_true", help="Carga todas las fuentes (incluye el índice de oportunidad).")
    parser.add_argument("--dry-run", action="store_true", help="Solo valida, no escribe en la BD ni en disco.")
    args = parser.parse_args()

    seleccion_explicita = (
        args.rubros or args.habilitaciones or args.codigo_urbanistico
        or args.oportunidad or args.all
    )
    cargar_rubros_flag = args.rubros or args.all or not seleccion_explicita
    cargar_hab_flag = args.habilitaciones or args.all
    cargar_codigo_flag = args.codigo_urbanistico or args.all
    cargar_oportunidad_flag = args.oportunidad or args.all

    if cargar_rubros_flag:
        filas = leer_seed()
        print(f"[rubros_requisitos] CSV: {CSV_SEED}")
        print(f"[rubros_requisitos] filas leídas: {len(filas)}")
        if not args.dry_run:
            err = _requiere_db()
            if err:
                return err
        escritas = cargar_rubros(filas, dry_run=args.dry_run)
        print(f"[rubros_requisitos] filas escritas (upsert): {escritas}")
        if not args.dry_run:
            total = contar_en_db("rubros_requisitos")
            if total is not None:
                print(f"[rubros_requisitos] total en BD: {total}")

    if cargar_hab_flag:
        print(f"[habilitaciones] CSV: {CSV_HAB}")
        try:
            registros = leer_habilitaciones()
        except FileNotFoundError as exc:
            print(f"[habilitaciones] AVISO: {exc}", file=sys.stderr)
            return 0 if not cargar_rubros_flag else 0
        print(f"[habilitaciones] filas leídas: {len(registros)}")
        if not args.dry_run:
            err = _requiere_db()
            if err:
                return err
        escritas = cargar_habilitaciones(registros, dry_run=args.dry_run)
        print(f"[habilitaciones] filas escritas (COPY): {escritas}")
        if not args.dry_run:
            total = contar_en_db("habilitaciones")
            if total is not None:
                print(f"[habilitaciones] total en BD: {total}")

    if cargar_codigo_flag:
        print(f"[urbanismo] Código Urbanístico: {CSV_CODIGO}")
        print(f"[urbanismo] reglas: {args.reglas}")
        cobertura = exportar_urbanismo(
            ruta_reglas=Path(args.reglas),
            dry_run=args.dry_run,
            cargar_db=not args.dry_run,
            leer_epok=not args.sin_epok,
        )
        if args.dry_run:
            print(
                f"[urbanismo] dry-run · reglas {cobertura['reglas']['version']} · "
                f"{cobertura['resumen']['smp_interseccion']:,} SMP en CU y habilitaciones"
            )

    if cargar_oportunidad_flag:
        print(f"[oportunidad] fuente: {CSV_HAB}")
        cargar_db = bool(os.environ.get("DATABASE_URL")) and not args.dry_run
        if not args.dry_run and not cargar_db:
            print(
                "[oportunidad] AVISO: sin DATABASE_URL; se generan solo los artefactos.",
                file=sys.stderr,
            )
        meta = exportar_oportunidad(
            min_licencias=args.min_licencias,
            top_rubros=args.top_rubros,
            dry_run=args.dry_run,
            cargar_db=cargar_db,
        )
        print(
            f"[oportunidad] fórmula {meta['formula_version']} · "
            f"{meta['n_filas']:,} filas · {meta['n_comunas']} comunas · "
            f"{meta['n_rubros']} rubros"
        )

    if args.dry_run:
        print("Dry-run: no se escribió nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
