"""Carga datos hacia PostgreSQL.

Cubre tres fuentes:

1. `rubros_requisitos` (desde `db/seed/rubros_requisitos.csv`, versionado): tabla
   de referencia rubro → trámites + documentación. Idempotente (UPSERT).
2. `habilitaciones` (desde `data/processed/habilitaciones_caba_clean.csv`, NO
   versionado — se genera corriendo el pipeline): padrón completo de ~217k filas.
   Recarga con TRUNCATE + COPY.
3. `indice_oportunidad` (desde el padrón): calcula el índice, escribe un
   artefacto reproducible (`indice_oportunidad.csv` + `_meta.json`) y lo carga
   con historial en `indice_oportunidad` / `indice_oportunidad_meta`.

Requiere la variable de entorno DATABASE_URL (o bien PGHOST/PGPORT/PGUSER/
PGPASSWORD/PGDATABASE, que psycopg lee automáticamente).

Uso:
    python src/export_postgres.py                  # carga rubros_requisitos
    python src/export_postgres.py --habilitaciones # carga el padrón
    python src/export_postgres.py --codigo-urbanistico # carga Código Urbanístico
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


def cargar_codigo_urbanistico(
    ruta: Path = CSV_CODIGO, dry_run: bool = False
) -> int:
    """Carga todos los atributos del Código Urbanístico preservando el CSV en JSONB."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el CSV del Código Urbanístico: {ruta}")

    dsn = os.environ.get("DATABASE_URL")
    if dsn and dsn.startswith("postgresql+psycopg://"):
        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)

    total = 0
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        if not lector.fieldnames or "smp" not in lector.fieldnames:
            raise ValueError("El CSV del Código Urbanístico debe incluir una columna 'smp'.")

        if dry_run:
            for fila in lector:
                if (fila.get("smp") or "").strip():
                    total += 1
            return total

        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS codigo_urbanistico (
                    smp TEXT PRIMARY KEY,
                    datos JSONB NOT NULL
                )
                """
            )
            cur.execute("TRUNCATE codigo_urbanistico")
            with cur.copy(
                "COPY codigo_urbanistico (smp, datos) FROM STDIN"
            ) as copy:
                for fila in lector:
                    smp = (fila.get("smp") or "").strip()
                    if not smp:
                        continue
                    copy.write_row((smp, Jsonb(fila)))
                    total += 1
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
    parser.add_argument("--codigo-urbanistico", action="store_true", help="Carga todos los datos del Código Urbanístico.")
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
        print(f"[codigo_urbanistico] CSV: {CSV_CODIGO}")
        if not args.dry_run:
            err = _requiere_db()
            if err:
                return err
        filas_codigo = cargar_codigo_urbanistico(dry_run=args.dry_run)
        print(f"[codigo_urbanistico] filas cargadas: {filas_codigo}")

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
