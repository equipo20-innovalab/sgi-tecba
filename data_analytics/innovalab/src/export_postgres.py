"""Carga datos hacia PostgreSQL.

Cubre dos fuentes:

1. `rubros_requisitos` (desde `db/seed/rubros_requisitos.csv`, versionado): tabla
   de referencia rubro → trámites + documentación. Idempotente (UPSERT).
2. `habilitaciones` (desde `data/processed/habilitaciones_caba_clean.csv`, NO
   versionado — se genera corriendo el pipeline): padrón completo de ~217k filas.
   Recarga con TRUNCATE + COPY.

Requiere la variable de entorno DATABASE_URL (o bien PGHOST/PGPORT/PGUSER/
PGPASSWORD/PGDATABASE, que psycopg lee automáticamente).

Uso:
    python src/export_postgres.py                  # carga rubros_requisitos
    python src/export_postgres.py --habilitaciones # carga el padrón
    python src/export_postgres.py --all            # carga ambas
    python src/export_postgres.py --dry-run        # solo valida, no escribe
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date
from pathlib import Path

import psycopg

RAIZ = Path(__file__).resolve().parent.parent
CSV_SEED = RAIZ / "db" / "seed" / "rubros_requisitos.csv"
CSV_HAB = RAIZ.parent.parent / "innovalab" / "data" / "processed" / "habilitaciones_caba_clean.csv"
# Ruta alternativa por si el CSV vive junto al script (carpeta local innovalab).
if not CSV_HAB.exists():
    CSV_HAB = Path.home() / "OneDrive" / "Escritorio" / "innovalab" / "data" / "processed" / "habilitaciones_caba_clean.csv"

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
    "fecha_habilitacion", "numero_expediente", "codigo_rubro", "descripcion_rubro",
    "superficie", "seccion", "manzana", "parcela", "smp", "calles", "comuna",
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
            "  Se genera corriendo el pipeline (notebook/01_exploracion_y_limpieza.ipynb)."
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
    parser = argparse.ArgumentParser(description="Carga datos de referencia y habilitaciones hacia PostgreSQL.")
    parser.add_argument("--rubros", action="store_true", help="Carga rubros_requisitos.")
    parser.add_argument("--habilitaciones", action="store_true", help="Carga el padrón de habilitaciones.")
    parser.add_argument("--all", action="store_true", help="Carga ambas fuentes.")
    parser.add_argument("--dry-run", action="store_true", help="Solo valida, no escribe en la BD.")
    args = parser.parse_args()

    # Por defecto carga solo rubros; --all carga ambas.
    cargar_rubros_flag = args.rubros or args.all or not (args.habilitaciones)
    cargar_hab_flag = args.habilitaciones or args.all

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

    if args.dry_run:
        print("Dry-run: no se escribió nada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
