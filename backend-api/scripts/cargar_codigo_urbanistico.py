"""Carga el CSV oficial del Código Urbanístico en Supabase.

Uso (desde backend-api):
    .venv\\Scripts\\python.exe scripts\\cargar_codigo_urbanistico.py

El script es idempotente: vacía y vuelve a cargar `codigo_urbanistico`.
No escribe credenciales en el código; lee `DATABASE_URL` desde `.env`.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.services.text_utils import normalizar_smp  # noqa: E402

CSV_URL = (
    "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
    "secretaria-de-desarrollo-urbano/codigo-urbanistico/"
    "codigo-urbanistico.csv"
)

COLUMNS = [
    "smp",
    "smp_raw",
    "barrio",
    "comuna",
    "dist_cpu_1",
    "dist_cpu_2",
    "dist_1_esp",
    "zona_1",
    "zona_2",
    "uso_1",
    "uso_2",
    "uso_3",
    "uni_edif_1",
    "uni_edif_2",
    "uni_edif_3",
    "uni_edif_4",
    "fot_em_1",
    "fot_em_2",
    "fot_pl_1",
    "fot_pl_2",
    "fot_sl_1",
    "fot_sl_2",
    "catalogado",
    "tipo_mza",
    "sm",
    "alicuota",
    "inc_uva_21",
    "cpu_obs",
    "memo",
    "adps",
    "ae_fot_bas",
    "raw",
]


def _text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _int(value: str | None) -> int | None:
    value = _text(value)
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _float(value: str | None) -> float | None:
    value = _text(value)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _bool(value: str | None) -> bool | None:
    value = _text(value)
    if value is None:
        return None
    return value.upper() in {"1", "TRUE", "SI", "SÍ"}


def _row(row: dict[str, str]) -> tuple[object, ...]:
    raw = json.dumps(row, ensure_ascii=False)
    return (
        normalizar_smp(row.get("smp")),
        _text(row.get("smp")),
        _text(row.get("barrio")),
        _int(row.get("comuna")),
        _text(row.get("dist_cpu_1")),
        _text(row.get("dist_cpu_2")),
        _text(row.get("dist_1_esp")),
        _text(row.get("zona_1")),
        _text(row.get("zona_2")),
        _int(row.get("uso_1")),
        _int(row.get("uso_2")),
        _int(row.get("uso_3")),
        _float(row.get("uni_edif_1")),
        _float(row.get("uni_edif_2")),
        _float(row.get("uni_edif_3")),
        _float(row.get("uni_edif_4")),
        _float(row.get("fot_em_1")),
        _float(row.get("fot_em_2")),
        _float(row.get("fot_pl_1")),
        _float(row.get("fot_pl_2")),
        _float(row.get("fot_sl_1")),
        _float(row.get("fot_sl_2")),
        _bool(row.get("catalogado")),
        _text(row.get("tipo_mza")),
        _text(row.get("sm")),
        _float(row.get("alicuota")),
        _float(row.get("inc_uva_21")),
        _text(row.get("cpu_obs")),
        _text(row.get("memo")),
        _text(row.get("adps")),
        _float(row.get("ae_fot_bas")),
        raw,
    )


def main() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    copy_sql = "COPY codigo_urbanistico (" + ", ".join(COLUMNS) + ") FROM STDIN"

    print("Descargando Código Urbanístico...")
    with urllib.request.urlopen(CSV_URL, timeout=180) as response:
        text = io.TextIOWrapper(
            response, encoding="utf-8", errors="replace", newline=""
        )
        reader = csv.DictReader(text)
        if not reader.fieldnames or "smp" not in reader.fieldnames:
            raise RuntimeError("El CSV no tiene la columna smp")

        with psycopg.connect(url, connect_timeout=30) as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE codigo_urbanistico")
                with cur.copy(copy_sql) as copy:
                    total = 0
                    for row in reader:
                        if not _text(row.get("smp")):
                            continue
                        copy.write_row(_row(row))
                        total += 1
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM codigo_urbanistico")
                print(
                    f"Código Urbanístico cargado: {cur.fetchone()[0]} filas "
                    f"(leídas: {total})"
                )


if __name__ == "__main__":
    main()
