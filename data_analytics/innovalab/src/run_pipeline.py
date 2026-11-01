"""Construye, valida y publica el padrón de habilitaciones."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from src.codigo_urbanistico import construir_codigo_urbanistico
from src.cleaning import limpiar
from src.data_loader import PROCESSED_DIR, load_raw
from src.data_validation import (
    guardar_reporte_calidad,
    validar_codigo_urbanistico,
    validar_habilitaciones,
)
from src.geografia import asignar_comuna

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_CSV = PROCESSED_DIR / "habilitaciones_caba_clean.csv"
CSV_CODIGO = PROCESSED_DIR / "codigo_urbanistico_limpio.csv"
REPORTE_CALIDAD = PROCESSED_DIR / "reporte_calidad.json"


def construir_padron() -> int:
    """Procesa las fuentes locales y reemplaza los CSV solo tras validar."""
    print("[pipeline] Cargando fuentes crudas")
    df = limpiar(load_raw())
    print("[pipeline] Asignando comunas")
    df = asignar_comuna(df)
    reporte = guardar_reporte_calidad(df, REPORTE_CALIDAD)
    validar_habilitaciones(df)
    filas_codigo = construir_codigo_urbanistico()
    validar_codigo_urbanistico(CSV_CODIGO)
    print(f"[pipeline] Código Urbanístico validado: {filas_codigo:,} parcelas")
    print(
        f"[pipeline] Cobertura general: "
        f"{reporte['columnas']['comuna']['cobertura']:.1%} comuna, "
        f"{reporte['columnas']['smp']['cobertura']:.1%} SMP, "
        f"{reporte['columnas']['fecha_habilitacion']['cobertura']:.1%} fecha"
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    temporal = OUTPUT_CSV.with_name(f".{OUTPUT_CSV.name}.tmp")
    try:
        df.to_csv(temporal, index=False, encoding="utf-8-sig")
        temporal.replace(OUTPUT_CSV)
    finally:
        temporal.unlink(missing_ok=True)

    print(f"[pipeline] Validación OK: {len(df):,} filas, {len(df.columns)} columnas")
    print(f"[pipeline] CSV publicado: {OUTPUT_CSV}")
    return len(df)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Procesa, valida y actualiza PostgreSQL con el padrón de habilitaciones."
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Construye y valida el CSV sin conectar a PostgreSQL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Construye, valida y comprueba la carga sin escribir en PostgreSQL.",
    )
    args = parser.parse_args()

    if not args.build_only and not args.dry_run and not os.environ.get("DATABASE_URL"):
        print("ERROR: definí DATABASE_URL o ejecutá con --build-only.", file=sys.stderr)
        return 2

    try:
        construir_padron()
    except Exception as exc:
        print(f"ERROR de procesamiento o validación: {exc}", file=sys.stderr)
        return 1

    if args.build_only:
        return 0

    exportador = [sys.executable, str(PROJECT_ROOT / "src" / "export_postgres.py"), "--all"]
    preflight = subprocess.run(
        [*exportador, "--dry-run"], cwd=PROJECT_ROOT, check=False
    )
    if preflight.returncode != 0 or args.dry_run:
        return preflight.returncode
    return subprocess.run(exportador, cwd=PROJECT_ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())