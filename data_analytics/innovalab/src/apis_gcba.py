"""Clientes de las APIs públicas del GCBA usadas por Innovalab.

Tres fuentes, con contratos **verificados en vivo** (oct-2026):

1. **EPOK Catastro** — `GET /catastro/parcela/?smp=<SMP>` → JSON con la ficha
   del inmueble: superficie total/cubierta, centroide, dirección, partida,
   puertas, pisos, etc. Es la fuente de "¿cómo es el local? ¿cuántos m²?".

2. **BA Data (CKAN)** — `https://data.buenosaires.gob.ar/api/3/action/...`
   Portal de datos abiertos: `package_search`, `package_show`,
   `datastore_search`. De ahí salen los datasets (habilitaciones, Código
   Urbanístico, etc.).

3. **USIG normalizar** — `GET /normalizar/?direccion=...&geocodificar=TRUE`
   Normaliza/geocodifica direcciones. ⚠️ **Hoy caído o muy lento** (>45s):
   el cliente lo trata con timeout corto y devuelve `None` para que el
   pipeline siga con la lógica de callejero/catastro (fallback).

Diseño: timeouts, reintentos limitados, caché en memoria (para no apurar las
APIs del Estado) y degradación gracia (una API caída no tumba el proceso).
"""

from __future__ import annotations

import time
from typing import Any

import requests

# --------------------------------------------------------------------------- #
# configuración
# --------------------------------------------------------------------------- #

EPOK_BASE = "https://epok.buenosaires.gob.ar/catastro"
BA_DATA_CKAN = "https://data.buenosaires.gob.ar/api/3/action"
USIG_NORMALIZAR = "http://servicios.usig.buenosaires.gob.ar/normalizar/"

# Timeouts cortos: las APIs del Estado pueden ser lentas y no queremos colgar
# el pipeline. USIG hoy supera los 45s, por eso su timeout es el más ajustado.
TIMEOUT_EPOK = 30
TIMEOUT_BADATA = 30
TIMEOUT_USIG = 12  # USIG actualmente no responde; corto para no bloquear

_REINTENTOS = 2
_ESPERA_REINTENTO = 1.5  # segundos; se duplica por reintento

_USER_AGENT = "inovalab/1.0 (+https://github.com/equipo20-innovalab)"

# Caché simple en memoria: clave -> valor. Evita repetir llamadas idénticas
# dentro de un mismo proceso de ETL.
_CACHE: dict[str, Any] = {}


def _get(url: str, *, params: dict | None = None, timeout: int,
         reintentos: int = _REINTENTOS) -> requests.Response | None:
    """GET con reintentos limitados. Devuelve None si definitivamente falla."""
    espera = _ESPERA_REINTENTO
    for intento in range(reintentos + 1):
        try:
            resp = requests.get(
                url, params=params, timeout=timeout,
                headers={"User-Agent": _USER_AGENT},
            )
            resp.raise_for_status()
            return resp
        except requests.Timeout:
            if intento == reintentos:
                return None
        except requests.RequestException:
            if intento == reintentos:
                return None
        time.sleep(espera)
        espera *= 2
    return None


def _cache_clave(url: str, params: dict | None) -> str:
    return url + "|" + str(sorted((params or {}).items()))


# --------------------------------------------------------------------------- #
# EPOK Catastro
# --------------------------------------------------------------------------- #

def consultar_epok_por_smp(smp: str) -> dict | None:
    """Ficha catastral de una parcela por su SMP (ej: '01-001-001A').

    Devuelve dict con claves útiles: `superficie_total`, `superficie_cubierta`,
    `centroide` [lng, lat], `direccion`, `pdamatriz`, `puertas`, etc.
    Devuelve None si la parcela no existe o EPOK no responde.
    """
    if not smp or not isinstance(smp, str):
        return None
    smp = smp.strip()
    clave = _cache_clave(EPOK_BASE + "/parcela", {"smp": smp})
    if clave in _CACHE:
        return _CACHE[clave]

    resp = _get(EPOK_BASE + "/parcela/", params={"smp": smp}, timeout=TIMEOUT_EPOK)
    if resp is None:
        return None
    try:
        # EPOK responde Content-Type text/javascript pero el cuerpo es JSON
        datos = resp.json()
    except ValueError:
        return None
    _CACHE[clave] = datos
    return datos


def consultar_epok_por_coordenadas(lng: float, lat: float) -> dict | None:
    """Ficha catastral del punto (lng, lat) en WGS84 (EPSG:4326)."""
    clave = _cache_clave(EPOK_BASE + "/parcela", {"lng": lng, "lat": lat})
    if clave in _CACHE:
        return _CACHE[clave]
    resp = _get(EPOK_BASE + "/parcela/", params={"lng": lng, "lat": lat},
                timeout=TIMEOUT_EPOK)
    if resp is None:
        return None
    try:
        datos = resp.json()
    except ValueError:
        return None
    _CACHE[clave] = datos
    return datos


def metros_cuadrados(ficha: dict | None) -> dict | None:
    """Extrae superficies útiles de una ficha EPOK (None si no hay).

    Devuelve {'total': float|None, 'cubierta': float|None}.
    """
    if not ficha:
        return None

    def _num(valor):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    return {
        "total": _num(ficha.get("superficie_total")),
        "cubierta": _num(ficha.get("superficie_cubierta")),
    }


# --------------------------------------------------------------------------- #
# USIG normalizar  (⚠️ caído hoy → degrada a None)
# --------------------------------------------------------------------------- #

def normalizar_direccion_usig(
    direccion: str,
    *,
    geocodificar: bool = True,
    tipo_resultado: str = "calle_altura",
    max_options: int = 5,
) -> dict | None:
    """Normaliza una dirección con USIG y (opcionalmente) la geocodifica.

    `direccion` en formato "calle altura, partido" o "calle y calle, partido".
    Devuelve la respuesta de USIG como dict, o **None** si el servicio no
    responde (hoy el caso habitual: timeout >45s). El caller debe hacer
    fallback a la lógica de callejero/catastro.
    """
    if not direccion:
        return None
    params = {
        "direccion": direccion,
        "geocodificar": "TRUE" if geocodificar else "FALSE",
        "tipoResultado": tipo_resultado,
        "maxOptions": max_options,
    }
    clave = _cache_clave(USIG_NORMALIZAR, params)
    if clave in _CACHE:
        return _CACHE[clave]

    resp = _get(USIG_NORMALIZAR, params=params, timeout=TIMEOUT_USIG, reintentos=1)
    if resp is None:
        return None
    try:
        datos = resp.json()
    except ValueError:
        # USIG a veces devuelve texto/HTML ante direcciones mal formadas
        return None
    _CACHE[clave] = datos
    return datos


# --------------------------------------------------------------------------- #
# BA Data (CKAN)
# --------------------------------------------------------------------------- #

def _ckan(action: str, params: dict, timeout: int = TIMEOUT_BADATA) -> Any:
    """Llama a la API CKAN de BA Data y devuelve `result` (o None)."""
    url = f"{BA_DATA_CKAN}/{action}"
    clave = _cache_clave(url, params)
    if clave in _CACHE:
        return _CACHE[clave]
    resp = _get(url, params=params, timeout=timeout)
    if resp is None:
        return None
    try:
        datos = resp.json()
    except ValueError:
        return None
    if not datos.get("success"):
        return None
    resultado = datos.get("result")
    _CACHE[clave] = resultado
    return resultado


def buscar_datasets_badata(consulta: str, filas: int = 10) -> list[dict]:
    """Busca datasets en BA Data (CKAN). Devuelve lista de metadatos."""
    resultado = _ckan("package_search", {"q": consulta, "rows": filas})
    if not resultado:
        return []
    return resultado.get("results", [])


def detalle_dataset_badata(nombre: str) -> dict | None:
    """Metadatos + recursos (archivos) de un dataset por su `name`."""
    resultado = _ckan("package_show", {"id": nombre})
    return resultado or None


def recursos_descargables(nombre: str) -> list[dict]:
    """Solo los recursos de un dataset que parecen archivos (CSV/JSON/XLSX)."""
    detalle = detalle_dataset_badata(nombre)
    if not detalle:
        return []
    extensiones = (".csv", ".json", ".xlsx", ".xls", ".geojson", ".zip")
    return [
        r for r in detalle.get("resources", [])
        if any(str(r.get("url", "")).lower().endswith(ext) for ext in extensiones)
    ]


# --------------------------------------------------------------------------- #
# utilidad de diagnóstico
# --------------------------------------------------------------------------- #

def estado_apis() -> dict[str, str]:
    """Sondea las 3 APIs y reporta su estado (para logs del ETL/monitor)."""
    epok = consultar_epok_por_smp("01-001-001A")
    badata = buscar_datasets_badata("habilitaciones", filas=1)
    usig = normalizar_direccion_usig("callao y corrientes", geocodificar=False)
    return {
        "epok": "ok" if epok else "no responde",
        "badata": "ok" if badata else "no responde",
        "usig": "ok" if usig else "no responde (timeout esperado hoy)",
    }


if __name__ == "__main__":  # pragma: no cover - diagnóstico manual
    print(estado_apis())
