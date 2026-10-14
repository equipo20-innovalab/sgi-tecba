"""Enriquece el padrón con el perfil catastral oficial de EPOK (GCBA).

Por cada SMP distinto presente en `habilitaciones`, llama a la API EPOK y
guarda la ficha catastral completa en la tabla `epok_fichas` (una fila por
propiedad). Esto completa el dataset con datos que el CSV no trae:

  coordenadas (mapa), pisos, unidades funcionales, frente/fondo, superficies.

Diseño reanudable: los SMP ya cargados en `epok_fichas` se saltean, así que
se puede cortar y volver a correr sin repetir llamadas. Rate-limit configurable
para no saturar la API del Estado.

Uso:
    python src/enriquecer_epok.py --probar            # 3 SMP, prueba rápida
    python src/enriquecer_epok.py --limite 500        # primer lote de 500
    python src/enriquecer_epok.py                     # todo lo pendiente
    python src/enriquecer_epok.py --reintentar        # reintenta SMP fallidos

Requiere DATABASE_URL (o PG* de psycopg) y el módulo `apis_gcba` en el path.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apis_gcba import consultar_epok_por_smp  # noqa: E402

# SMP que EPOK no resuelve o que sabemos fallan (evita reintentar en vano).
# Se agregan los fallidos en la tabla con ficha NULL si --registrar-fallidos.


def _num(valor) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _int(valor) -> int | None:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def extraer_campos(ficha: dict) -> dict:
    """Extrae los campos consultables de una ficha EPOK completa."""
    centroide = ficha.get("centroide") or [None, None]
    return {
        "lng": _num(centroide[0]) if len(centroide) > 0 else None,
        "lat": _num(centroide[1]) if len(centroide) > 1 else None,
        "direccion": ficha.get("direccion"),
        "superficie_total": _num(ficha.get("superficie_total")),
        "superficie_cubierta": _num(ficha.get("superficie_cubierta")),
        "frente": _num(ficha.get("frente")),
        "fondo": _num(ficha.get("fondo")),
        "pisos_sobre_rasante": _int(ficha.get("pisos_sobre_rasante")),
        "unidades_funcionales": _int(ficha.get("unidades_funcionales")),
        "propiedad_horizontal": ficha.get("propiedad_horizontal"),
        "puertas": ficha.get("puertas"),
    }


UPSERT_SQL = """
    INSERT INTO epok_fichas (
        smp, ficha, lng, lat, direccion,
        superficie_total, superficie_cubierta, frente, fondo,
        pisos_sobre_rasante, unidades_funcionales, propiedad_horizontal,
        puertas, actualizado_en
    ) VALUES (
        %(smp)s, %(ficha)s, %(lng)s, %(lat)s, %(direccion)s,
        %(superficie_total)s, %(superficie_cubierta)s, %(frente)s, %(fondo)s,
        %(pisos_sobre_rasante)s, %(unidades_funcionales)s, %(propiedad_horizontal)s,
        %(puertas)s, now()
    )
    ON CONFLICT (smp) DO UPDATE SET
        ficha                 = EXCLUDED.ficha,
        lng                   = EXCLUDED.lng,
        lat                   = EXCLUDED.lat,
        direccion             = EXCLUDED.direccion,
        superficie_total      = EXCLUDED.superficie_total,
        superficie_cubierta   = EXCLUDED.superficie_cubierta,
        frente                = EXCLUDED.frente,
        fondo                 = EXCLUDED.fondo,
        pisos_sobre_rasante   = EXCLUDED.pisos_sobre_rasante,
        unidades_funcionales  = EXCLUDED.unidades_funcionales,
        propiedad_horizontal  = EXCLUDED.propiedad_horizontal,
        puertas               = EXCLUDED.puertas,
        actualizado_en        = now()
"""

PENDIENTES_SQL = """
    SELECT DISTINCT h.smp
    FROM habilitaciones h
    LEFT JOIN epok_fichas e ON h.smp = e.smp
    WHERE h.smp IS NOT NULL AND e.smp IS NULL
    ORDER BY h.smp
"""


def obtener_pendientes(conn, limite: int | None = None) -> list[str]:
    sql = PENDIENTES_SQL
    params: list = []
    if limite:
        sql += " LIMIT %s"
        params.append(limite)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [fila[0] for fila in cur.fetchall()]


def _ficha_valida(ficha: dict | None) -> bool:
    """True si la ficha de EPOK trae datos reales (no un {} vacío/error)."""
    if not ficha:
        return False
    tiene_coordenadas = bool(ficha.get("centroide"))
    tiene_superficie = ficha.get("superficie_total") not in (None, "")
    return tiene_coordenadas or tiene_superficie


def procesar(smps: list[str], conn, delay: float, registrar_fallidos: bool) -> tuple[int, int]:
    """Procesa una lista de SMP. Devuelve (ok, fallidos)."""
    ok = fallidos = 0
    lote: list[dict] = []

    def _volcar():
        nonlocal lote, ok, fallidos
        if not lote:
            return
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, lote)
        conn.commit()
        ok += sum(1 for f in lote if f["ficha"] is not None)
        fallidos += sum(1 for f in lote if f["ficha"] is None)
        lote = []

    for i, smp in enumerate(smps, 1):
        ficha = consultar_epok_por_smp(smp)
        if _ficha_valida(ficha):
            campos = extraer_campos(ficha)
            campos["puertas"] = Jsonb(campos["puertas"])
            lote.append({"smp": smp, "ficha": Jsonb(ficha), **campos})
        elif registrar_fallidos:
            lote.append({**{"smp": smp, "ficha": None}, **extraer_campos({})})
        else:
            fallidos += 1

        if len(lote) >= 50:
            _volcar()
            print(f"  … {i}/{len(smps)} procesados (último: {smp})", flush=True)
        if delay:
            time.sleep(delay)

    _volcar()
    return ok, fallidos


def main() -> int:
    parser = argparse.ArgumentParser(description="Enriquece habilitaciones con la ficha catastral de EPOK.")
    parser.add_argument("--limite", type=int, default=None, help="Procesa solo los primeros N SMP pendientes.")
    parser.add_argument("--delay", type=float, default=0.25, help="Pausa (s) entre llamadas a EPOK. Default 0.25s.")
    parser.add_argument("--probar", action="store_true", help="Prueba rápida con 3 SMP.")
    parser.add_argument("--registrar-fallidos", action="store_true", help="Guarda fila vacía para SMP sin ficha (evita reintentar).")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: definí DATABASE_URL (o PG*).", file=sys.stderr)
        return 2

    limite = 3 if args.probar else args.limite

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        pendientes = obtener_pendientes(conn, limite)
        total_pend = len(obtener_pendientes(conn))
        print(f"SMP pendientes de enriquecer: {total_pend}")
        if not pendientes:
            print("Nada por hacer: el padrón ya está enriquecido.")
            return 0
        print(f"Procesando {len(pendientes)} SMP (delay={args.delay}s)…")
        t0 = time.time()
        ok, fallidos = procesar(pendientes, conn, args.delay, args.registrar_fallidos)
        dt = time.time() - t0
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM epok_fichas")
            total = cur.fetchone()[0]
        print(f"\nListo en {dt:.1f}s: {ok} fichas OK, {fallidos} sin ficha.")
        print(f"epok_fichas en BD: {total} / {total_pend + total} SMP pendientes restantes: {total_pend - len(pendientes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
