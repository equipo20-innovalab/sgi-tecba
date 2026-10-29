"""Enriquece el padrón con el perfil catastral oficial de EPOK (GCBA).

Por cada SMP distinto presente en el padrón procesado, llama a la API EPOK y
guarda la ficha catastral completa en la tabla `epok_fichas` (una fila por
propiedad). Esto completa el dataset con datos que el CSV no trae:

  coordenadas (mapa), pisos, unidades funcionales, frente/fondo, superficies.

Diseño reanudable e incremental:

* los SMP sin fila se consultan siempre;
* los fallidos se reintentan hasta ``--max-intentos``;
* las fichas resueltas se refrescan después de ``--max-edad-dias``;
* ``--solo-pendientes`` limita la corrida a faltantes/fallidos;
* ``--todo`` fuerza una recarga completa.

Cada intento registra estado, cantidad de intentos, último error y fecha de
última actualización. La API usa reintentos con backoff exponencial. Al final
se genera un reporte JSON y un dashboard HTML con la cobertura y alertas.

Uso:
    python src/enriquecer_epok.py --solo-reporte       # dashboard sin llamar a EPOK
    python src/enriquecer_epok.py --probar              # 3 SMP, prueba rápida
    python src/enriquecer_epok.py --limite 500          # primer lote de 500
    python src/enriquecer_epok.py                       # incremental
    python src/enriquecer_epok.py --solo-pendientes     # no refresca vencidas
    python src/enriquecer_epok.py --reintentar          # fallidas agotadas
    python src/enriquecer_epok.py --todo                # recarga completa

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

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))
from apis_gcba import consultar_epok_por_smp  # noqa: E402
from epok_cobertura import (  # noqa: E402
    CSV_PADRON,
    HTML_DASHBOARD,
    JSON_COBERTURA,
    construir_reporte,
    guardar_reporte,
    leer_padron,
    resumen_texto,
    seleccionar_candidatos,
)

COLUMNAS_REQUERIDAS = {"estado", "intentos", "ultimo_error", "ultimo_intento_en"}


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


UPSERT_OK_SQL = """
    INSERT INTO epok_fichas (
        smp, ficha, lng, lat, direccion,
        superficie_total, superficie_cubierta, frente, fondo,
        pisos_sobre_rasante, unidades_funcionales, propiedad_horizontal,
        puertas, actualizado_en, estado, intentos, ultimo_error, ultimo_intento_en
    ) VALUES (
        %(smp)s, %(ficha)s, %(lng)s, %(lat)s, %(direccion)s,
        %(superficie_total)s, %(superficie_cubierta)s, %(frente)s, %(fondo)s,
        %(pisos_sobre_rasante)s, %(unidades_funcionales)s, %(propiedad_horizontal)s,
        %(puertas)s, now(), 'ok', 1, NULL, now()
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
        actualizado_en        = now(),
        estado                = 'ok',
        intentos              = epok_fichas.intentos + 1,
        ultimo_error          = NULL,
        ultimo_intento_en     = now()
"""

# Un fallo no borra la última ficha válida: solo actualiza el estado del intento.
UPSERT_FALLIDO_SQL = """
    INSERT INTO epok_fichas (
        smp, ficha, estado, intentos, ultimo_error, ultimo_intento_en
    ) VALUES (
        %(smp)s, NULL, 'fallido', 1, %(error)s, now()
    )
    ON CONFLICT (smp) DO UPDATE SET
        estado            = 'fallido',
        intentos          = epok_fichas.intentos + 1,
        ultimo_error      = EXCLUDED.ultimo_error,
        ultimo_intento_en = now()
"""

ESTADO_SQL = """
    SELECT
        e.smp,
        (e.ficha IS NOT NULL) AS resuelto,
        COALESCE(
            to_jsonb(e)->>'estado',
            CASE WHEN e.ficha IS NULL THEN 'fallido' ELSE 'ok' END
        ) AS estado,
        COALESCE(NULLIF(to_jsonb(e)->>'intentos', '')::int, 0) AS intentos,
        e.actualizado_en,
        to_jsonb(e)->>'ultimo_error' AS ultimo_error
    FROM epok_fichas AS e
"""


def leer_estado_fichas(conn) -> dict[str, dict]:
    """Estado de cada ficha, tolerante a bases sin las columnas nuevas."""
    with conn.cursor() as cur:
        cur.execute(ESTADO_SQL)
        filas = cur.fetchall()
    return {
        fila[0]: {
            "resuelto": bool(fila[1]),
            "estado": fila[2],
            "intentos": int(fila[3] or 0),
            "actualizado_en": fila[4],
            "ultimo_error": fila[5],
        }
        for fila in filas
    }


def verificar_esquema(conn) -> None:
    """Falla temprano si la tabla no tiene las columnas de seguimiento."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'epok_fichas'
            """
        )
        columnas = {fila[0] for fila in cur.fetchall()}
    faltantes = COLUMNAS_REQUERIDAS - columnas
    if faltantes:
        raise RuntimeError(
            "La tabla epok_fichas no tiene las columnas: "
            + ", ".join(sorted(faltantes))
            + ". Un administrador debe aplicar db/schema.sql "
            "(ALTER TABLE epok_fichas ...)."
        )


def obtener_pendientes(conn, limite: int | None = None) -> list[str]:
    """Compatibilidad: SMP sin ficha resuelta, en formato incremental."""
    padron = leer_padron()
    candidatos, _ = seleccionar_candidatos(
        padron["smps"],
        leer_estado_fichas(conn),
        solo_pendientes=True,
        limite=limite,
    )
    return candidatos


def _ficha_valida(ficha: dict | None) -> bool:
    """True si la ficha de EPOK trae datos reales (no un {} vacío/error)."""
    if not ficha:
        return False
    tiene_coordenadas = bool(ficha.get("centroide"))
    tiene_superficie = ficha.get("superficie_total") not in (None, "")
    return tiene_coordenadas or tiene_superficie


def _mensaje_error(ficha: dict | None) -> str:
    if not ficha:
        return "EPOK no devolvió ficha o se agotaron los reintentos"
    return "EPOK devolvió una ficha sin datos utilizables"


def procesar(
    smps: list[str],
    conn,
    delay: float,
    registrar_fallidos: bool,
    *,
    reintentos: int = 2,
    espera: float = 1.5,
) -> tuple[int, int]:
    """Procesa una lista de SMP. Devuelve (ok, fallidos)."""
    ok = fallidos = 0
    lote_ok: list[dict] = []
    lote_fallido: list[dict] = []

    def _volcar():
        if not lote_ok and not lote_fallido:
            return
        with conn.cursor() as cur:
            if lote_ok:
                cur.executemany(UPSERT_OK_SQL, lote_ok)
            if lote_fallido:
                cur.executemany(UPSERT_FALLIDO_SQL, lote_fallido)
        conn.commit()
        lote_ok.clear()
        lote_fallido.clear()

    for i, smp in enumerate(smps, 1):
        ficha = consultar_epok_por_smp(smp, reintentos=reintentos, espera=espera)
        if _ficha_valida(ficha):
            campos = extraer_campos(ficha)
            campos["puertas"] = Jsonb(campos["puertas"])
            lote_ok.append({"smp": smp, "ficha": Jsonb(ficha), **campos})
            ok += 1
        else:
            fallidos += 1
            if registrar_fallidos:
                lote_fallido.append({"smp": smp, "error": _mensaje_error(ficha)})

        if len(lote_ok) + len(lote_fallido) >= 50:
            _volcar()
            print(f"  … {i}/{len(smps)} procesados (último: {smp})", flush=True)
        if delay:
            time.sleep(delay)

    _volcar()
    return ok, fallidos


def _umbrales(args) -> dict:
    return {
        "min_cobertura_smp": args.alerta_min_cobertura_smp,
        "min_cobertura_hab": args.alerta_min_cobertura_hab,
        "max_edad_dias": args.sla_dias,
        "max_fallidas": args.alerta_max_fallidas,
        "max_pendientes_smp": args.alerta_max_pendientes,
    }


def _generar_reporte(conn, padron: dict, args) -> tuple[dict, tuple[Path, Path] | None]:
    estado = leer_estado_fichas(conn)
    reporte = construir_reporte(padron, estado, umbrales=_umbrales(args))
    rutas = None
    if not args.sin_reporte:
        rutas = guardar_reporte(reporte, args.salida_json, args.salida_html)
    return reporte, rutas


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enriquece el padrón con fichas EPOK, de forma incremental."
    )
    parser.add_argument("--limite", type=int, default=None, help="Procesa solo los primeros N candidatos.")
    parser.add_argument("--delay", type=float, default=0.25, help="Pausa (s) entre llamadas a EPOK. Default 0.25s.")
    parser.add_argument("--probar", action="store_true", help="Prueba rápida con 3 SMP.")
    parser.add_argument("--solo-pendientes", action="store_true", help="No refresca fichas vencidas; solo faltantes y fallidas.")
    parser.add_argument("--todo", action="store_true", help="Refresca todos los SMP del padrón.")
    parser.add_argument("--reintentar", action="store_true", help="Reintenta fallidas aunque hayan agotado --max-intentos.")
    parser.add_argument("--max-intentos", type=int, default=3, help="Intentos máximos para un SMP fallido. Default 3.")
    parser.add_argument("--max-edad-dias", type=int, default=30, help="Refresca fichas con más de N días; 0 desactiva. Default 30.")
    parser.add_argument("--reintentos", type=int, default=2, help="Reintentos HTTP por SMP. Default 2.")
    parser.add_argument("--backoff", type=float, default=1.5, help="Espera inicial entre reintentos; se duplica. Default 1.5s.")
    parser.add_argument("--no-registrar-fallidos", action="store_true", help="No guarda filas de error (se reintentan siempre).")
    parser.add_argument("--solo-reporte", action="store_true", help="Genera reporte y dashboard sin llamar a EPOK.")
    parser.add_argument("--sin-reporte", action="store_true", help="No escribe JSON/HTML al terminar.")
    parser.add_argument("--ruta-padron", default=str(CSV_PADRON), help="CSV del padrón procesado.")
    parser.add_argument("--salida-json", default=str(JSON_COBERTURA), help="Ruta del reporte JSON.")
    parser.add_argument("--salida-html", default=str(HTML_DASHBOARD), help="Ruta del dashboard HTML.")
    parser.add_argument("--alerta-min-cobertura-smp", type=float, default=0.80, help="Objetivo de cobertura de SMP. Default 0.80.")
    parser.add_argument("--alerta-min-cobertura-hab", type=float, default=0.80, help="Objetivo de cobertura de habilitaciones. Default 0.80.")
    parser.add_argument("--alerta-max-fallidas", type=int, default=100, help="Máximo de fichas fallidas sin alerta. Default 100.")
    parser.add_argument("--alerta-max-pendientes", type=int, default=5000, help="Máximo de SMP pendientes sin alerta. Default 5000.")
    parser.add_argument("--sla-dias", type=int, default=30, help="Días máximos desde la última actualización. Default 30.")
    parser.add_argument("--fallar-si-alerta", action="store_true", help="Devuelve código 1 si el reporte tiene alertas.")
    args = parser.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: definí DATABASE_URL (o PG*).", file=sys.stderr)
        return 2

    if args.solo_reporte:
        args.sin_reporte = False

    limite = 3 if args.probar else args.limite
    edad_refresh = None if args.max_edad_dias == 0 else args.max_edad_dias

    try:
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            padron = leer_padron(args.ruta_padron)
            estado = leer_estado_fichas(conn)

            print(
                f"Padrón: {padron['total_habilitaciones']:,} habilitaciones · "
                f"{len(padron['smps']):,} SMP distintos · "
                f"{padron['habilitaciones_sin_smp']:,} sin SMP"
            )
            print(
                f"Fichas en BD: {len(estado):,} · "
                f"resueltas: {sum(1 for f in estado.values() if f['resuelto']):,}"
            )

            if args.solo_reporte:
                reporte, rutas = _generar_reporte(conn, padron, args)
                print(resumen_texto(reporte))
                _imprimir_alertas(reporte)
                if rutas:
                    print(f"Reporte: {rutas[0]}\nDashboard: {rutas[1]}")
                return _codigo_salida(reporte, args)

            verificar_esquema(conn)

            candidatos, motivos = seleccionar_candidatos(
                padron["smps"],
                estado,
                max_edad_dias=edad_refresh,
                max_intentos=args.max_intentos,
                solo_pendientes=args.solo_pendientes,
                todo=args.todo,
                reintentar=args.reintentar,
                limite=limite,
            )
            print(
                f"Candidatos: {len(candidatos):,} "
                f"(nuevos {motivos['nuevos']:,}, fallidos {motivos['fallidos']:,}, "
                f"desactualizados {motivos['desactualizados']:,}, "
                f"forzados {motivos['forzados']:,})"
            )

            if candidatos:
                print(
                    f"Procesando {len(candidatos):,} SMP "
                    f"(delay={args.delay}s, reintentos={args.reintentos}, "
                    f"backoff={args.backoff}s)…"
                )
                t0 = time.time()
                ok, fallidos = procesar(
                    candidatos,
                    conn,
                    args.delay,
                    not args.no_registrar_fallidos,
                    reintentos=args.reintentos,
                    espera=args.backoff,
                )
                print(
                    f"\nListo en {time.time() - t0:.1f}s: "
                    f"{ok:,} fichas OK, {fallidos:,} sin ficha."
                )
            else:
                print("Nada por hacer: no hay candidatos según la política incremental.")

            reporte, rutas = _generar_reporte(conn, padron, args)
            print(resumen_texto(reporte))
            _imprimir_alertas(reporte)
            if rutas:
                print(f"Reporte: {rutas[0]}\nDashboard: {rutas[1]}")
            return _codigo_salida(reporte, args)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _imprimir_alertas(reporte: dict) -> None:
    for alerta in reporte["alertas"]:
        print(f"[{alerta['nivel'].upper()}] {alerta['codigo']}: {alerta['mensaje']}")


def _codigo_salida(reporte: dict, args) -> int:
    if args.fallar_si_alerta and reporte["alertas"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
