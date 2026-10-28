"""Construye el índice local `epok_direcciones` desde `epok_fichas.puertas`.

Uso (desde backend-api):
    .venv\\Scripts\\python.exe scripts\\cargar_epok_direcciones.py

Es idempotente: vacía y vuelve a cargar el índice. No escribe credenciales en el
código; lee `DATABASE_URL` desde `.env`.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from app.services.text_utils import calle_base, normalizar_calle  # noqa: E402


def _fecha(value: str | None):
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def main() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    total = 0

    with psycopg.connect(url, connect_timeout=30) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE epok_direcciones RESTART IDENTITY")
            cur.execute("""
                CREATE TEMP TABLE tmp_epok_direcciones (
                    smp TEXT,
                    calle TEXT,
                    calle_normalizada TEXT,
                    calle_base TEXT,
                    altura INTEGER,
                    codigo_calle INTEGER,
                    puerta_principal BOOLEAN,
                    puerta_oficial BOOLEAN,
                    fuente TEXT,
                    fecha_actualizacion DATE
                ) ON COMMIT DROP
                """)
            cur.execute(
                "SELECT smp, puertas FROM epok_fichas WHERE puertas IS NOT NULL"
            )
            fichas = cur.fetchall()

            with cur.copy("""
                COPY tmp_epok_direcciones (
                    smp, calle, calle_normalizada, calle_base, altura, codigo_calle,
                    puerta_principal, puerta_oficial, fuente, fecha_actualizacion
                ) FROM STDIN
                """) as copy:
                for smp, puertas in fichas:
                    if not isinstance(puertas, list):
                        continue
                    for puerta in puertas:
                        if not isinstance(puerta, dict):
                            continue
                        calle = (puerta.get("calle") or "").strip()
                        try:
                            altura = int(puerta.get("altura"))
                            codigo_calle = int(puerta.get("codigo_calle"))
                        except (TypeError, ValueError):
                            continue
                        if not calle or altura <= 0 or codigo_calle <= 0:
                            continue
                        copy.write_row(
                            (
                                smp,
                                calle,
                                normalizar_calle(calle),
                                calle_base(calle),
                                altura,
                                codigo_calle,
                                bool(puerta.get("puerta_principal")),
                                bool(puerta.get("puerta_oficial")),
                                puerta.get("fuente"),
                                _fecha(puerta.get("fecha_actualizacion")),
                            )
                        )
                        total += 1

            cur.execute("""
                INSERT INTO epok_direcciones (
                    smp, calle, calle_normalizada, calle_base, altura, codigo_calle,
                    puerta_principal, puerta_oficial, fuente, fecha_actualizacion
                )
                SELECT
                    smp, calle, calle_normalizada, calle_base, altura, codigo_calle,
                    puerta_principal, puerta_oficial, fuente, fecha_actualizacion
                FROM tmp_epok_direcciones
                ON CONFLICT DO NOTHING
                """)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM epok_direcciones")
            print(f"Direcciones EPOK cargadas: {cur.fetchone()[0]} (leídas: {total})")


if __name__ == "__main__":
    main()
