"""Cobertura, dashboard y alertas del enriquecimiento EPOK.

Este módulo no llama a la API: calcula métricas a partir del padrón procesado
y del estado de ``epok_fichas``, y renderiza un dashboard HTML autocontenido.

El padrón se lee desde ``data/processed/habilitaciones_caba_clean.csv`` para
que la cobertura refleje exactamente los datos publicados por el pipeline, no
una carga previa de PostgreSQL. Los SMP se normalizan con la misma rutina que
usa el enriquecimiento (``limpiar_smp``), de modo que ambos lados del cruce
quedan en el formato catastral ``SSS-MMM-PPP[L]``.
"""

from __future__ import annotations

import csv
import html
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.limpiar_smp import limpiar_smp

RAIZ = Path(__file__).resolve().parents[1]
CSV_PADRON = RAIZ / "data" / "processed" / "habilitaciones_caba_clean.csv"
JSON_COBERTURA = RAIZ / "data" / "processed" / "epok_cobertura.json"
HTML_DASHBOARD = RAIZ / "data" / "processed" / "epok_dashboard.html"

MARCADORES_NULOS = {
    "",
    "NAN",
    "NONE",
    "NULL",
    "NA",
    "N/A",
    "SIN DATO",
    "SIN_DATO",
}


def normalizar_smp_epok(valor: Any) -> str | None:
    """Normaliza un SMP al formato que consulta y guarda EPOK."""
    if valor is None:
        return None
    texto = str(valor).strip().upper()
    if texto in MARCADORES_NULOS:
        return None
    return limpiar_smp(texto)


def leer_padron(ruta: str | Path = CSV_PADRON) -> dict:
    """Lee el padrón procesado y agrega los conteos necesarios para el reporte.

    Devuelve los SMP distintos normalizados y contadores por SMP, año y comuna.
    Los registros sin SMP se conservan en los totales pero no en ``smps``.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el padrón procesado: {ruta}\n"
            "  Se genera con python -m src.run_pipeline --build-only."
        )

    total = sin_smp = 0
    smps: set[str] = set()
    por_smp: Counter[str] = Counter()
    por_anio: dict[str, Counter[str | None]] = {}
    por_comuna: dict[str, Counter[str | None]] = {}

    with ruta.open(encoding="utf-8-sig", newline="") as fh:
        lector = csv.DictReader(fh)
        for fila in lector:
            total += 1
            smp = normalizar_smp_epok(fila.get("smp"))
            anio = (fila.get("anio") or "").strip() or "sin_dato"
            comuna = (fila.get("comuna") or "").strip() or "sin_dato"

            if smp is None:
                sin_smp += 1
            else:
                smps.add(smp)
                por_smp[smp] += 1

            por_anio.setdefault(anio, Counter())[smp] += 1
            por_comuna.setdefault(comuna, Counter())[smp] += 1

    return {
        "ruta": str(ruta),
        "total_habilitaciones": total,
        "habilitaciones_sin_smp": sin_smp,
        "smps": sorted(smps),
        "habilitaciones_por_smp": dict(por_smp),
        "por_anio": por_anio,
        "por_comuna": por_comuna,
    }


def _aware(valor: datetime | None) -> datetime | None:
    if valor is None:
        return None
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


def seleccionar_candidatos(
    smps: list[str],
    estado: dict[str, dict],
    *,
    max_edad_dias: int | None = 30,
    max_intentos: int = 3,
    solo_pendientes: bool = False,
    todo: bool = False,
    reintentar: bool = False,
    limite: int | None = None,
    ahora: datetime | None = None,
) -> tuple[list[str], dict[str, int]]:
    """Elige qué SMP consultar en esta corrida.

    - Sin fila en ``epok_fichas``: siempre.
    - Fila fallida: si no agotó ``max_intentos`` o si ``reintentar=True``.
    - Fila resuelta: solo si superó ``max_edad_dias`` y no se pidió
      ``solo_pendientes``. ``max_edad_dias=None`` desactiva el refresh.
    - ``todo=True`` ignora el estado y devuelve todos los SMP del padrón.
    """
    ahora = _aware(ahora) or datetime.now(timezone.utc)
    corte = (
        ahora - timedelta(days=max_edad_dias)
        if max_edad_dias is not None
        else None
    )

    candidatos: list[str] = []
    motivos = {"nuevos": 0, "fallidos": 0, "desactualizados": 0, "forzados": 0}

    for smp in sorted(set(smps)):
        fila = estado.get(smp)

        if todo:
            candidatos.append(smp)
            motivos["forzados"] += 1
        elif fila is None:
            candidatos.append(smp)
            motivos["nuevos"] += 1
        elif not fila.get("resuelto"):
            intentos = int(fila.get("intentos") or 0)
            if reintentar or intentos < max_intentos:
                candidatos.append(smp)
                motivos["fallidos"] += 1
        elif not solo_pendientes and corte is not None:
            actualizado = _aware(fila.get("actualizado_en"))
            if actualizado is None or actualizado < corte:
                candidatos.append(smp)
                motivos["desactualizados"] += 1

    if limite is not None:
        candidatos = candidatos[: max(limite, 0)]

    return candidatos, motivos


def _resumen_grupo(conteo: Counter[str | None], resueltos: set[str]) -> dict:
    total = sum(conteo.values())
    con_smp = sum(cantidad for smp, cantidad in conteo.items() if smp)
    con_ficha = sum(cantidad for smp, cantidad in conteo.items() if smp in resueltos)
    return {
        "habilitaciones": total,
        "con_smp": con_smp,
        "con_ficha": con_ficha,
        "cobertura": (con_ficha / total) if total else None,
    }


def _clave_orden(valor: str) -> tuple[int, Any]:
    try:
        return (0, int(valor))
    except (TypeError, ValueError):
        return (1, str(valor))


def evaluar_alertas(
    reporte: dict,
    *,
    min_cobertura_smp: float = 0.80,
    min_cobertura_hab: float = 0.80,
    max_edad_dias: int = 30,
    max_fallidas: int = 100,
    max_pendientes_smp: int = 5000,
) -> list[dict]:
    """Genera alertas accionables a partir del reporte de cobertura."""
    cobertura = reporte["cobertura"]
    fichas = reporte["fichas"]
    alertas: list[dict] = []

    def agregar(codigo: str, nivel: str, mensaje: str, valor=None, umbral=None):
        alertas.append(
            {
                "codigo": codigo,
                "nivel": nivel,
                "mensaje": mensaje,
                "valor": valor,
                "umbral": umbral,
            }
        )

    if cobertura["smp_padron"] == 0:
        agregar(
            "SIN_PADRON",
            "critica",
            "El padrón no tiene SMP distintos: no se puede calcular cobertura.",
        )
        return alertas

    if fichas["resueltas"] == 0:
        agregar(
            "SIN_FICHAS",
            "critica",
            "No hay fichas EPOK resueltas; el enriquecimiento nunca completó una parcela.",
        )

    if cobertura["cobertura_smp"] < min_cobertura_smp:
        agregar(
            "COBERTURA_SMP_BAJA",
            "advertencia",
            f"Cobertura de SMP resueltos {cobertura['cobertura_smp']:.1%} "
            f"por debajo del objetivo {min_cobertura_smp:.0%}.",
            round(cobertura["cobertura_smp"], 4),
            min_cobertura_smp,
        )

    if cobertura["cobertura_habilitaciones"] < min_cobertura_hab:
        agregar(
            "COBERTURA_HABILITACIONES_BAJA",
            "advertencia",
            f"Cobertura de habilitaciones con ficha "
            f"{cobertura['cobertura_habilitaciones']:.1%} por debajo del objetivo "
            f"{min_cobertura_hab:.0%}.",
            round(cobertura["cobertura_habilitaciones"], 4),
            min_cobertura_hab,
        )

    if fichas["desactualizadas"] > 0:
        agregar(
            "FICHAS_DESACTUALIZADAS",
            "advertencia",
            f"{fichas['desactualizadas']:,} fichas resueltas superan "
            f"{max_edad_dias} días sin actualización.",
            fichas["desactualizadas"],
            max_edad_dias,
        )

    if fichas["fallidas"] > max_fallidas:
        agregar(
            "FICHAS_FALLIDAS",
            "advertencia",
            f"{fichas['fallidas']:,} SMP fallaron y superan el máximo de "
            f"{max_fallidas:,}.",
            fichas["fallidas"],
            max_fallidas,
        )

    if cobertura["smp_pendientes"] > max_pendientes_smp:
        agregar(
            "COLA_PENDIENTE",
            "advertencia",
            f"{cobertura['smp_pendientes']:,} SMP pendientes superan el máximo "
            f"de {max_pendientes_smp:,}.",
            cobertura["smp_pendientes"],
            max_pendientes_smp,
        )

    if fichas["antiguedad_dias"] is None:
        agregar(
            "SIN_ACTUALIZACION",
            "critica",
            "No hay una fecha de última actualización de fichas resueltas.",
        )
    elif fichas["antiguedad_dias"] > max_edad_dias:
        agregar(
            "SLA_VENCIDO",
            "critica",
            f"La última ficha se actualizó hace {fichas['antiguedad_dias']} días; "
            f"el SLA es de {max_edad_dias} días.",
            fichas["antiguedad_dias"],
            max_edad_dias,
        )

    comunas_sin = [
        fila["comuna"]
        for fila in reporte["por_comuna"]
        if fila["habilitaciones"] >= 100 and fila["con_ficha"] == 0
    ]
    if comunas_sin:
        agregar(
            "COMUNAS_SIN_COBERTURA",
            "advertencia",
            "Comunas con al menos 100 habilitaciones y 0% de cobertura: "
            + ", ".join(comunas_sin[:8])
            + ("…" if len(comunas_sin) > 8 else ""),
            len(comunas_sin),
            0,
        )

    anios_sin = [
        fila["anio"]
        for fila in reporte["por_anio"]
        if fila["habilitaciones"] >= 100 and fila["con_ficha"] == 0
    ]
    if anios_sin:
        agregar(
            "ANIOS_SIN_COBERTURA",
            "advertencia",
            "Años con al menos 100 habilitaciones y 0% de cobertura: "
            + ", ".join(anios_sin),
            len(anios_sin),
            0,
        )

    return alertas


def construir_reporte(
    padron: dict,
    estado: dict[str, dict],
    *,
    umbrales: dict | None = None,
    ahora: datetime | None = None,
) -> dict:
    """Arma el reporte JSON de cobertura a partir del padrón y las fichas."""
    umbrales = {
        "min_cobertura_smp": 0.80,
        "min_cobertura_hab": 0.80,
        "max_edad_dias": 30,
        "max_fallidas": 100,
        "max_pendientes_smp": 5000,
        **(umbrales or {}),
    }
    ahora = _aware(ahora) or datetime.now(timezone.utc)

    resueltos = {smp for smp, fila in estado.items() if fila.get("resuelto")}
    resueltas = [fila for fila in estado.values() if fila.get("resuelto")]

    corte = ahora - timedelta(days=umbrales["max_edad_dias"])
    desactualizadas = 0
    for fila in resueltas:
        actualizado = _aware(fila.get("actualizado_en"))
        if actualizado is None or actualizado < corte:
            desactualizadas += 1

    fechas = [
        fecha
        for fecha in (_aware(fila.get("actualizado_en")) for fila in resueltas)
        if fecha is not None
    ]
    ultima = max(fechas) if fechas else None
    antiguedad = (ahora - ultima).days if ultima else None

    smps_padron = padron["smps"]
    smps_resueltos = len(set(smps_padron) & resueltos)
    total_hab = padron["total_habilitaciones"]
    hab_con_ficha = sum(
        cantidad
        for smp, cantidad in padron["habilitaciones_por_smp"].items()
        if smp in resueltos
    )

    cobertura = {
        "habilitaciones": total_hab,
        "habilitaciones_con_smp": total_hab - padron["habilitaciones_sin_smp"],
        "habilitaciones_sin_smp": padron["habilitaciones_sin_smp"],
        "habilitaciones_con_ficha": hab_con_ficha,
        "cobertura_habilitaciones": (hab_con_ficha / total_hab) if total_hab else 0.0,
        "smp_padron": len(smps_padron),
        "smp_resueltos": smps_resueltos,
        "smp_pendientes": len(smps_padron) - smps_resueltos,
        "cobertura_smp": (smps_resueltos / len(smps_padron)) if smps_padron else 0.0,
    }

    intentos = [int(fila.get("intentos") or 0) for fila in estado.values()]
    fichas = {
        "total": len(estado),
        "resueltas": len(resueltas),
        "fallidas": len(estado) - len(resueltas),
        "en_padron": len(set(estado) & set(smps_padron)),
        "desactualizadas": desactualizadas,
        "intentos_promedio": (sum(intentos) / len(intentos)) if intentos else 0.0,
        "ultima_actualizacion": ultima.isoformat() if ultima else None,
        "antiguedad_dias": antiguedad,
    }

    por_anio = [
        {"anio": anio, **_resumen_grupo(conteo, resueltos)}
        for anio, conteo in sorted(
            padron["por_anio"].items(), key=lambda item: _clave_orden(item[0])
        )
    ]
    por_comuna = [
        {"comuna": comuna, **_resumen_grupo(conteo, resueltos)}
        for comuna, conteo in sorted(
            padron["por_comuna"].items(), key=lambda item: _clave_orden(item[0])
        )
    ]

    reporte = {
        "generado_en": ahora.isoformat(),
        "fuente": {
            "padron": padron["ruta"],
            "fichas": "epok_fichas",
        },
        "umbrales": umbrales,
        "cobertura": cobertura,
        "fichas": fichas,
        "por_anio": por_anio,
        "por_comuna": por_comuna,
    }
    reporte["alertas"] = evaluar_alertas(reporte, **umbrales)
    return reporte


def _pct(valor: float | None) -> str:
    if valor is None:
        return "s/d"
    return f"{valor:.1%}".replace(".", ",")


def _barra(valor: float | None) -> str:
    pct = 0.0 if valor is None else max(0.0, min(1.0, valor)) * 100
    return (
        '<div class="bar"><span style="width:'
        f'{pct:.1f}%"></span></div>'
    )


def _tabla_grupo(titulo: str, clave: str, filas: list[dict]) -> str:
    cuerpo = []
    for fila in filas:
        cuerpo.append(
            "<tr>"
            f"<td>{html.escape(str(fila[clave]))}</td>"
            f"<td>{fila['habilitaciones']:,}</td>"
            f"<td>{fila['con_smp']:,}</td>"
            f"<td>{fila['con_ficha']:,}</td>"
            f"<td>{_barra(fila['cobertura'])}</td>"
            f"<td>{_pct(fila['cobertura'])}</td>"
            "</tr>"
        )
    return (
        f"<h2>{html.escape(titulo)}</h2>"
        '<table><thead><tr>'
        f"<th>{html.escape(clave.capitalize())}</th>"
        "<th>Habilitaciones</th><th>Con SMP</th><th>Con ficha</th>"
        "<th>Cobertura</th><th>%</th>"
        "</tr></thead><tbody>"
        + "".join(cuerpo)
        + "</tbody></table>"
    )


def render_dashboard(reporte: dict) -> str:
    """Renderiza un dashboard HTML autocontenido (sin JavaScript ni CDN)."""
    cobertura = reporte["cobertura"]
    fichas = reporte["fichas"]
    alertas = reporte["alertas"]

    tarjetas = [
        ("SMP resueltos", _pct(cobertura["cobertura_smp"]),
         f"{cobertura['smp_resueltos']:,} / {cobertura['smp_padron']:,}", _barra(cobertura["cobertura_smp"])),
        ("Habilitaciones con ficha", _pct(cobertura["cobertura_habilitaciones"]),
         f"{cobertura['habilitaciones_con_ficha']:,} / {cobertura['habilitaciones']:,}",
         _barra(cobertura["cobertura_habilitaciones"])),
        ("Fichas resueltas", f"{fichas['resueltas']:,}",
         f"{fichas['fallidas']:,} fallidas · {fichas['en_padron']:,} en el padrón", ""),
        ("Pendientes", f"{cobertura['smp_pendientes']:,}",
         "SMP sin ficha en el padrón actual", ""),
        ("Desactualizadas", f"{fichas['desactualizadas']:,}",
         f"SLA {reporte['umbrales']['max_edad_dias']} días", ""),
        ("Última actualización", _fecha_corta(fichas["ultima_actualizacion"]),
         f"hace {fichas['antiguedad_dias']} días" if fichas["antiguedad_dias"] is not None else "s/d", ""),
    ]
    tarjetas_html = "".join(
        '<div class="card">'
        f"<div class=\"label\">{html.escape(label)}</div>"
        f"<div class=\"value\">{html.escape(valor)}</div>"
        f"<div class=\"hint\">{html.escape(detalle)}</div>"
        f"{barra}"
        "</div>"
        for label, valor, detalle, barra in tarjetas
    )

    if alertas:
        alertas_html = "".join(
            f'<li class="alert {html.escape(a["nivel"])}">'
            f'<strong>{html.escape(a["codigo"])}</strong> '
            f'<span class="nivel">{html.escape(a["nivel"])}</span><br>'
            f'{html.escape(a["mensaje"])}'
            "</li>"
            for a in alertas
        )
    else:
        alertas_html = '<li class="alert ok">Sin alertas: la cobertura cumple los umbrales.</li>'

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cobertura EPOK · Innovalab</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 32px; font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f4f6f8; color: #1c2733; }}
  main {{ max-width: 1080px; margin: 0 auto; }}
  h1 {{ margin: 0 0 4px; font-size: 30px; }}
  h2 {{ margin: 32px 0 10px; font-size: 19px; }}
  .sub {{ color: #607080; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }}
  .card {{ background: #fff; border: 1px solid #dfe5ea; border-radius: 10px; padding: 16px; }}
  .label {{ color: #607080; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }}
  .value {{ font-size: 28px; font-weight: 700; margin: 4px 0; }}
  .hint {{ color: #607080; font-size: 12px; min-height: 18px; }}
  .bar {{ height: 7px; background: #e8edf1; border-radius: 99px; overflow: hidden; margin-top: 10px; }}
  .bar span {{ display: block; height: 100%; background: #1f7a5c; }}
  ul.alerts {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }}
  .alert {{ background: #fff; border-left: 5px solid #c28b00; border-radius: 6px; padding: 12px 14px; }}
  .alert.critica {{ border-left-color: #b3261e; }}
  .alert.ok {{ border-left-color: #1f7a5c; color: #1f7a5c; }}
  .nivel {{ color: #607080; font-size: 11px; text-transform: uppercase; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #dfe5ea; border-radius: 8px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #edf1f4; font-size: 13px; }}
  th {{ background: #f8fafb; color: #607080; font-weight: 600; }}
  tr:last-child td {{ border-bottom: 0; }}
  td .bar {{ margin: 0; width: 120px; }}
  footer {{ margin-top: 28px; color: #607080; font-size: 12px; }}
</style>
</head>
<body>
<main>
  <h1>Cobertura EPOK</h1>
  <div class="sub">Generado {html.escape(reporte['generado_en'])} · Fuente: {html.escape(reporte['fuente']['fichas'])} + padrón procesado</div>
  <div class="grid">{tarjetas_html}</div>
  <h2>Alertas</h2>
  <ul class="alerts">{alertas_html}</ul>
  {_tabla_grupo("Cobertura por año", "anio", reporte["por_anio"])}
  {_tabla_grupo("Cobertura por comuna", "comuna", reporte["por_comuna"])}
  <footer>
    Umbrales: cobertura SMP ≥ {_pct(reporte['umbrales']['min_cobertura_smp'])},
    habilitaciones ≥ {_pct(reporte['umbrales']['min_cobertura_hab'])},
    SLA ≤ {reporte['umbrales']['max_edad_dias']} días,
    fallidas ≤ {reporte['umbrales']['max_fallidas']:,},
    pendientes ≤ {reporte['umbrales']['max_pendientes_smp']:,}.
  </footer>
</main>
</body>
</html>
"""


def _fecha_corta(valor: str | None) -> str:
    if not valor:
        return "s/d"
    return valor[:10]


def guardar_reporte(
    reporte: dict,
    ruta_json: str | Path = JSON_COBERTURA,
    ruta_html: str | Path = HTML_DASHBOARD,
) -> tuple[Path, Path]:
    """Escribe JSON y HTML de forma atómica."""
    ruta_json = Path(ruta_json)
    ruta_html = Path(ruta_html)
    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    ruta_html.parent.mkdir(parents=True, exist_ok=True)

    temporal_json = ruta_json.with_name(f".{ruta_json.name}.tmp")
    temporal_html = ruta_html.with_name(f".{ruta_html.name}.tmp")
    try:
        temporal_json.write_text(
            json.dumps(reporte, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporal_html.write_text(render_dashboard(reporte), encoding="utf-8")
        temporal_json.replace(ruta_json)
        temporal_html.replace(ruta_html)
    finally:
        temporal_json.unlink(missing_ok=True)
        temporal_html.unlink(missing_ok=True)

    return ruta_json, ruta_html


def resumen_texto(reporte: dict) -> str:
    """Resumen breve para consola."""
    cobertura = reporte["cobertura"]
    fichas = reporte["fichas"]
    criticas = sum(1 for a in reporte["alertas"] if a["nivel"] == "critica")
    return (
        f"Cobertura EPOK: {_pct(cobertura['cobertura_smp'])} SMP "
        f"({cobertura['smp_resueltos']:,}/{cobertura['smp_padron']:,}) · "
        f"{_pct(cobertura['cobertura_habilitaciones'])} habilitaciones "
        f"({cobertura['habilitaciones_con_ficha']:,}/{cobertura['habilitaciones']:,})\n"
        f"Fichas: {fichas['resueltas']:,} resueltas · {fichas['fallidas']:,} fallidas · "
        f"{fichas['desactualizadas']:,} desactualizadas · "
        f"última {_fecha_corta(fichas['ultima_actualizacion'])}\n"
        f"Alertas: {len(reporte['alertas'])} ({criticas} críticas)"
    )
