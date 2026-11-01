#!/usr/bin/env python3
"""Genera el fixture pequeño y sanitizado que se versiona para la demo.

El dataset completo pesa ~89 MB, se guarda con Git LFS y depende de
PostgreSQL 18. Para demos, CI y onboarding no hace falta: alcanza con una
muestra chica, reproducible y sin identificadores directos de personas o
empresas.

Qué hace:

1. Lee el padrón procesado (`data/processed/habilitaciones_caba_clean.csv`).
2. Normaliza los SMP con `limpiar_smp` y elige una muestra estratificada por
   comuna entre los SMP que tienen ficha EPOK.
3. Sanitiza los identificadores directos (solicitud, expediente, razón social,
   partida matriz) y deja intacta la estructura urbana (SMP, comuna, rubro,
   superficies, fechas) para que los cruces sigan funcionando.
4. Escribe `db/demo/habilitaciones_demo.csv`, `db/demo/epok_fichas_demo.csv` y
   `db/demo/FIXTURE.json` con hashes y versión de la fuente.

Los CSV son deterministas para una misma semilla y fecha: regenerarlos con los
mismos parámetros produce bytes idénticos. Eso permite testear la integridad
del fixture sin depender de la base.

Uso:
    python scripts/generar_demo.py                     # 150 habilitaciones, 30 SMP
    python scripts/generar_demo.py --filas 80 --smps 20
    python scripts/generar_demo.py --sin-epok          # solo padrón (tests)
    python scripts/generar_demo.py --entrada /tmp/padron.csv --salida /tmp/demo

Requiere PostgreSQL solo para leer `epok_fichas`; con `--sin-epok` no se
conecta a la base.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.export_postgres import COLS_HAB  # noqa: E402
from src.limpiar_smp import limpiar_smp  # noqa: E402

CSV_PADRON = RAIZ / "data" / "processed" / "habilitaciones_caba_clean.csv"
DIR_DEMO = RAIZ / "db" / "demo"
VERSION_FIXTURE = "1.0.0"
VERSION_SANITIZACION = "1.0.0"
SEMILLA = 20261028
PATRON_SMP = re.compile(r"^\d{3}-\d{3,4}-\d{2,3}[A-Z]?$")

COLUMNAS_EPOK = (
    "smp", "ficha", "lng", "lat", "direccion",
    "superficie_total", "superficie_cubierta", "frente", "fondo",
    "pisos_sobre_rasante", "unidades_funcionales", "propiedad_horizontal",
    "puertas", "actualizado_en", "estado", "intentos", "ultimo_error",
    "ultimo_intento_en",
)

CAMPOS_SANITIZADOS = ("solicitud", "numero_expediente", "razon_social", "partida_matriz")


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        dsn = os.environ.get("PGDATABASE") or "dbname=innovalab"
    if dsn.startswith("postgresql+psycopg://"):
        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
    return dsn


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor).strip()


def leer_padron(ruta: Path) -> list[dict[str, str]]:
    """Lee el padrón completo como dicts de texto, sin inferir tipos."""
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el padrón: {ruta}\n"
            "  Se genera con python -m src.run_pipeline --build-only."
        )
    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        faltantes = [c for c in COLS_HAB if c not in (lector.fieldnames or [])]
        if faltantes:
            raise ValueError(f"Al padrón le faltan columnas: {faltantes}")
        return [{c: _texto(fila.get(c)) for c in COLS_HAB} for fila in lector]


def _comuna_principal(filas: list[dict[str, str]]) -> str:
    conteo = Counter(fila["comuna"] or "sin_dato" for fila in filas)
    return sorted(conteo.items(), key=lambda item: (-item[1], item[0]))[0][0]


def elegir_smps(
    por_smp: dict[str, list[dict[str, str]]],
    elegibles: set[str],
    cantidad: int,
    rng: random.Random,
) -> list[str]:
    """Elige SMP elegibles de forma estratificada por comuna."""
    por_comuna: dict[str, list[str]] = defaultdict(list)
    for smp in sorted(elegibles):
        por_comuna[_comuna_principal(por_smp[smp])].append(smp)

    # Dentro de cada comuna, priorizar los SMP con más filas aprovechables para
    # que el fixture llegue al cupo sin quedar con parcelas de una sola fila.
    for lista in por_comuna.values():
        rng.shuffle(lista)
        lista.sort(key=lambda smp: len(por_smp[smp]), reverse=True)

    seleccion: list[str] = []
    comunas = sorted(por_comuna)
    while len(seleccion) < cantidad and any(por_comuna[c] for c in comunas):
        for comuna in comunas:
            if len(seleccion) >= cantidad:
                break
            if por_comuna[comuna]:
                seleccion.append(por_comuna[comuna].pop(0))
    return sorted(seleccion)


def elegir_filas(
    por_smp: dict[str, list[dict[str, str]]],
    smps: list[str],
    total: int,
    rng: random.Random,
) -> list[dict[str, str]]:
    """Reparte el cupo entre los SMP elegidos y baraja cada grupo."""
    cupo = max(1, total // max(1, len(smps)))
    elegidas: list[dict[str, str]] = []
    for smp in smps:
        candidatas = por_smp[smp]
        rng.shuffle(candidatas)
        elegidas.extend(candidatas[:cupo])

    # Si faltan filas, completar con el resto de los SMP (sin repetir).
    if len(elegidas) < total:
        restantes = [
            fila
            for smp in smps
            for fila in por_smp[smp]
            if fila not in elegidas
        ]
        rng.shuffle(restantes)
        elegidas.extend(restantes[: total - len(elegidas)])

    return elegidas[:total]


def sanitizar(filas: list[dict[str, str]]) -> list[dict[str, str]]:
    """Reemplaza identificadores directos conservando la estructura urbana."""
    salida = []
    for indice, fila in enumerate(filas, 1):
        limpia = dict(fila)
        limpia["solicitud"] = str(9_000_000 + indice)
        limpia["numero_expediente"] = f"EX-2026-DEMO-{indice:06d}"
        limpia["razon_social"] = f"EMPRESA DEMO {indice:04d}"
        limpia["partida_matriz"] = f"DEMO-{indice:06d}"
        salida.append(limpia)
    return salida


def leer_epok(smps: list[str]) -> tuple[list[dict], int, str]:
    """Lee las fichas EPOK de los SMP elegidos. Devuelve filas, versión y DSN.

    Tolera bases creadas con el esquema anterior: si faltan las columnas de
    seguimiento, las completa con valores neutros para que el fixture se pueda
    generar igual.
    """
    import psycopg

    dsn = _dsn()
    with psycopg.connect(dsn, connect_timeout=5) as conn, conn.cursor() as cur:
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'epok_fichas'
            """
        )
        existentes = {fila[0] for fila in cur.fetchall()}

        columnas = [
            "smp", "lng", "lat", "direccion",
            "superficie_total", "superficie_cubierta", "frente", "fondo",
            "pisos_sobre_rasante", "unidades_funcionales", "propiedad_horizontal",
            "puertas", "actualizado_en",
        ]
        opcionales = {
            "estado": "'ok'",
            "intentos": "0",
            "ultimo_error": "NULL::text",
            "ultimo_intento_en": "NULL::timestamptz",
        }
        for nombre, relleno in opcionales.items():
            columnas.append(nombre if nombre in existentes else f"{relleno} AS {nombre}")

        filtro_estado = (
            "AND (estado IS NULL OR estado = 'ok')" if "estado" in existentes else ""
        )
        cur.execute(
            f"""
            SELECT {', '.join(columnas)}
            FROM epok_fichas
            WHERE ficha IS NOT NULL AND smp = ANY(%s) {filtro_estado}
            ORDER BY smp
            """,
            (smps,),
        )
        filas = cur.fetchall()
    return [dict(zip(COLUMNAS_EPOK[0:1] + COLUMNAS_EPOK[2:], fila)) for fila in filas], version, dsn


def _apta(fila: dict[str, str]) -> bool:
    """True si la fila tiene los datos mínimos para una demo legible."""
    return bool(
        fila["smp"]
        and fila["fecha_habilitacion"]
        and fila["codigo_rubro"]
        and fila["comuna"]
    )


def escribir_habilitaciones(filas: list[dict[str, str]], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=COLS_HAB, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows(filas)


def escribir_epok(filas: list[dict], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=COLUMNAS_EPOK, lineterminator="\n")
        escritor.writeheader()
        for fila in filas:
            salida = dict(fila)
            # `ficha` se compacta: la respuesta completa de EPOK puede pesar
            # cientos de KB por parcela y no aporta a la demo.
            salida["ficha"] = json.dumps(
                {
                    "smp": fila["smp"],
                    "direccion": fila["direccion"],
                    "superficie_total": fila["superficie_total"],
                    "superficie_cubierta": fila["superficie_cubierta"],
                    "frente": fila["frente"],
                    "fondo": fila["fondo"],
                    "pisos_sobre_rasante": fila["pisos_sobre_rasante"],
                    "unidades_funcionales": fila["unidades_funcionales"],
                    "propiedad_horizontal": fila["propiedad_horizontal"],
                    "centroide": [fila["lng"], fila["lat"]],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            salida["puertas"] = json.dumps(fila["puertas"], ensure_ascii=False, sort_keys=True) if fila["puertas"] is not None else ""
            for campo in ("actualizado_en", "ultimo_intento_en"):
                valor = salida[campo]
                salida[campo] = valor.isoformat() if hasattr(valor, "isoformat") else ("" if valor is None else str(valor))
            salida["ultimo_error"] = salida["ultimo_error"] or ""
            escritor.writerow(salida)


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _ruta_legible(ruta: Path) -> str:
    """Ruta relativa a la raíz del proyecto cuando es posible (metadata portable)."""
    try:
        return str(ruta.resolve().relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera el fixture sanitizado de demo.")
    parser.add_argument("--entrada", default=str(CSV_PADRON), help="CSV del padrón procesado.")
    parser.add_argument("--salida", default=str(DIR_DEMO), help="Directorio de salida del fixture.")
    parser.add_argument("--filas", type=int, default=150, help="Habilitaciones a incluir. Default 150.")
    parser.add_argument("--smps", type=int, default=30, help="SMP distintos a incluir. Default 30.")
    parser.add_argument("--semilla", type=int, default=SEMILLA, help=f"Semilla aleatoria. Default {SEMILLA}.")
    parser.add_argument("--fecha", default=None, help="Fecha ISO de generación (para reproducibilidad).")
    parser.add_argument("--sin-epok", action="store_true", help="No consulta ni escribe fichas EPOK.")
    args = parser.parse_args()

    if args.filas <= 0 or args.smps <= 0:
        print("ERROR: --filas y --smps deben ser mayores a 0.", file=sys.stderr)
        return 2

    fecha = args.fecha or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rng = random.Random(args.semilla)
    entrada = Path(args.entrada)
    salida = Path(args.salida)

    filas = leer_padron(entrada)
    por_smp: dict[str, list[dict[str, str]]] = defaultdict(list)
    for fila in filas:
        smp = limpiar_smp(fila["smp"])
        if smp and PATRON_SMP.match(smp) and _apta(fila):
            fila["smp"] = smp
            por_smp[smp].append(fila)

    if not por_smp:
        print("ERROR: el padrón no tiene SMP válidos.", file=sys.stderr)
        return 2

    if args.sin_epok:
        elegibles = set(por_smp)
        epok_filas: list[dict] = []
        version_pg = "no consultado"
    else:
        todos = sorted(por_smp)
        epok_existentes = set()
        try:
            import psycopg

            with psycopg.connect(_dsn(), connect_timeout=5) as conn, conn.cursor() as cur:
                cur.execute("SELECT smp FROM epok_fichas WHERE ficha IS NOT NULL")
                epok_existentes = {fila[0] for fila in cur.fetchall()}
        except Exception as exc:  # noqa: BLE001 - el mensaje importa más que el tipo
            print(f"ERROR: no se pudo leer epok_fichas ({exc}).", file=sys.stderr)
            print("  Usá --sin-epok para generar solo el padrón.", file=sys.stderr)
            return 2
        elegibles = set(todos) & epok_existentes
        if not elegibles:
            print("ERROR: ningún SMP del padrón tiene ficha EPOK.", file=sys.stderr)
            return 2
        if len(elegibles) < args.smps:
            print(
                f"AVISO: solo hay {len(elegibles):,} SMP con ficha; "
                f"se ajusta --smps a ese valor.",
                file=sys.stderr,
            )

    smps = elegir_smps(por_smp, elegibles, min(args.smps, len(elegibles)), rng)
    seleccion = elegir_filas(por_smp, smps, args.filas, rng)
    seleccion.sort(key=lambda f: (f["smp"], f["fecha_habilitacion"], f["codigo_rubro"], f["descripcion_rubro"]))
    sanitizadas = sanitizar(seleccion)

    ruta_hab = salida / "habilitaciones_demo.csv"
    escribir_habilitaciones(sanitizadas, ruta_hab)

    epok_filas: list[dict] = []
    version_pg = "no consultado"
    if not args.sin_epok:
        epok_filas, version_pg, _ = leer_epok(smps)
        escribir_epok(epok_filas, salida / "epok_fichas_demo.csv")

    metadata = {
        "version_fixture": VERSION_FIXTURE,
        "version_sanitizacion": VERSION_SANITIZACION,
        "generado_en": fecha,
        "semilla": args.semilla,
        "fuente": {
            "padron": _ruta_legible(entrada),
            "epok": "epok_fichas (ficha compactada)" if not args.sin_epok else "no incluida",
            "postgres_version": version_pg,
            "dump_referencia": "PostgreSQL 18.3 (db/innovalab_dump.sql)",
        },
        "sanitizacion": {
            "reemplazados": list(CAMPOS_SANITIZADOS),
            "conservados": [
                c for c in COLS_HAB if c not in CAMPOS_SANITIZADOS
            ],
            "nota": (
                "Pseudonimizado, no anonimizado: se quitaron identificadores "
                "directos, pero combinaciones de SMP, rubro y fecha podrían "
                "seguir siendo singulares. No usar para inferir negocios reales."
            ),
        },
        "archivos": {
            "habilitaciones_demo.csv": {
                "filas": len(sanitizadas),
                "smp": len({f["smp"] for f in sanitizadas}),
                "sha256": sha256(ruta_hab),
            }
        },
    }
    if not args.sin_epok:
        ruta_epok = salida / "epok_fichas_demo.csv"
        metadata["archivos"]["epok_fichas_demo.csv"] = {
            "filas": len(epok_filas),
            "sha256": sha256(ruta_epok),
        }

    (salida / "FIXTURE.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"Fixture {VERSION_FIXTURE}: {len(sanitizadas):,} habilitaciones · "
        f"{len({f['smp'] for f in sanitizadas}):,} SMP · {len(epok_filas):,} fichas EPOK"
    )
    print(f"Salida: {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
