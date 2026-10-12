"""Asignación de comuna con capas geográficas oficiales del GCBA.

Fuentes (data.buenosaires.gob.ar, descargadas a data/geo/):
    comunas.geojson          límites de las 15 comunas
    manzanas_catastrales.csv polígonos catastrales con clave sección-manzana
    callejero.csv            nomenclador oficial con comuna por calle
                             (y comuna por lado par/impar)

Estrategia híbrida, en orden de prioridad:
    1. comuna ya informada en el archivo fuente (esquema moderno 2025/2026)
    2. catastro: (sección, manzana) -> polígono catastral -> punto -> comuna
    3. callejero: nombre de calle oficial -> comuna (par/impar si hay altura)
    4. callejero con coincidencia aproximada (difflib, similitud >= 0.90)

La columna `comuna_fuente` deja trazabilidad de qué regla aplicó en cada fila.
"""

from __future__ import annotations

import difflib
import json
import re
import urllib.request
from pathlib import Path

import pandas as pd
from shapely import wkt
from shapely.geometry import shape
from shapely.prepared import prep

from .data_loader import GEO_DIR

FUENTES = {
    "comunas": (
        "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
        "innovacion-transformacion-digital/comunas/comunas.geojson",
        "comunas.geojson",
    ),
    "manzanas": (
        "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
        "secretaria-de-desarrollo-urbano/manzanas/manzanas_catastrales.csv",
        "manzanas_catastrales.csv",
    ),
    "callejero": (
        "https://cdn.buenosaires.gob.ar/datosabiertos/datasets/"
        "jefatura-de-gabinete-de-ministros/calles/callejero.csv",
        "callejero.csv",
    ),
}

_SIMILITUD_MINIMA = 0.90
_CACHE: dict = {}


def descargar_geodata() -> dict[str, Path]:
    """Descarga las capas oficiales a data/geo/ si no están (una sola vez)."""
    rutas = {}
    for clave, (url, nombre) in FUENTES.items():
        destino = GEO_DIR / nombre
        if not destino.exists() or destino.stat().st_size == 0:
            GEO_DIR.mkdir(parents=True, exist_ok=True)
            print(f"Descargando {nombre} ...")
            req = urllib.request.Request(url, headers={"User-Agent": "inovalab/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp, open(
                destino, "wb"
            ) as out:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
            print(f"  -> {destino.stat().st_size:,} bytes")
        rutas[clave] = destino
    return rutas


# --------------------------------------------------------------------------- #
# capas geográficas
# --------------------------------------------------------------------------- #

def _cargar_comunas(ruta: Path) -> list[tuple[int, object]]:
    """Polygons preparados de las 15 comunas (WGS84)."""
    if "comunas" in _CACHE:
        return _CACHE["comunas"]
    with open(ruta, encoding="utf-8") as fh:
        data = json.load(fh)
    poligonos = []
    for feature in data["features"]:
        geom = shape(feature["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        poligonos.append((int(feature["properties"]["comuna"]), prep(geom)))
    _CACHE["comunas"] = poligonos
    return poligonos


def _contenida(punto, poligonos) -> int | None:
    for comuna, geom in poligonos:
        if geom.contains(punto):
            return comuna
    return None


def _canon_seccion(valor) -> int | None:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def _canon_manzana(valor) -> str | None:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    texto = str(valor).strip().upper()
    if not texto or texto in {"NAN", "<NA>", "SIN DATO"}:
        return None
    match = re.match(r"^0*(\d+)([A-Z]*)$", texto)
    if match:
        return f"{int(match.group(1))}{match.group(2)}"
    return texto


def _dicc_manzana_comuna(ruta_manzanas: Path, poligonos) -> dict[tuple, int]:
    """(sección, manzana) -> comuna, vía punto representativo del polígono."""
    if "manzanas" in _CACHE:
        return _CACHE["manzanas"]
    manzanas = pd.read_csv(ruta_manzanas, encoding="utf-8-sig", dtype=str)
    dicc = {}
    for fila in manzanas.itertuples():
        if not isinstance(fila.sm, str) or " - " not in fila.sm:
            continue
        seccion_txt, manzana_txt = fila.sm.split(" - ", 1)
        seccion = _canon_seccion(seccion_txt)
        manzana = _canon_manzana(manzana_txt)
        if seccion is None or manzana is None:
            continue
        try:
            poly = wkt.loads(fila.geometry)
        except (TypeError, ValueError):
            continue
        if not poly.is_valid:
            poly = poly.buffer(0)
        comuna = _contenida(poly.representative_point(), poligonos)
        if comuna is not None:
            dicc[(seccion, manzana)] = comuna
    _CACHE["manzanas"] = dicc
    return dicc


def _dicc_calles_comuna(ruta_callejero: Path) -> dict[str, dict]:
    """NOMBRE CALLE (mayúsculas) -> {'comuna', 'par', 'impar'}.

    El callejero trae un segmento por tramo de cuadra: se colapsa por nombre
    con la moda de cada columna.
    """
    if "calles" in _CACHE:
        return _CACHE["calles"]
    cal = pd.read_csv(ruta_callejero, encoding="utf-8-sig", dtype=str, low_memory=False)
    cal = cal.dropna(subset=["nomoficial"]).copy()
    cal["nom"] = cal["nomoficial"].str.upper().str.strip()
    for col in ("comuna", "com_par", "com_impar"):
        cal[col] = pd.to_numeric(cal[col], errors="coerce")

    def moda(serie: pd.Series):
        modo = serie.mode()
        return int(modo.iloc[0]) if not modo.empty else None

    dicc = (
        cal.groupby("nom")
        .agg(comuna=("comuna", moda), par=("com_par", moda), impar=("com_impar", moda))
        .to_dict(orient="index")
    )
    _CACHE["calles"] = dicc
    return dicc


# --------------------------------------------------------------------------- #
# normalización de la dirección del padrón
# --------------------------------------------------------------------------- #

def _normalizar_calle(valor) -> tuple[str, int | None]:
    """'CORRIENTES AV. 2330' -> ('CORRIENTES AV.', 2330)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "", None
    texto = str(valor).upper().split(";")[0]
    texto = re.sub(r"\s+", " ", texto).strip(" ,;-")
    altura = None
    match = re.search(r"(\d+)\s*[A-Z]?\s*$", texto)
    if match:
        base = texto[: match.start()].strip(" ,;-")
        if base:
            altura = int(match.group(1))
            texto = base
    if not texto or texto in {"NAN", "<NA>", "SIN DATO"}:
        return "", None
    return texto, altura


def _es_trash(nombre: str) -> bool:
    """Callejas numéricas de datos corruptos ('355507', '008B')."""
    if not nombre:
        return True
    digitos = sum(c.isdigit() for c in nombre)
    return digitos / len(nombre) > 0.5


def _resolver_nombre(
    nombre: str, dicc: dict, oficiales: list[str]
) -> tuple[str | None, str | None]:
    """Devuelve (nombre oficial, fuente) o (None, None)."""
    if nombre in dicc:
        return nombre, "callejero"
    if _es_trash(nombre):
        return None, None
    if len(nombre) >= 4:
        for oficial in oficiales:
            if oficial.startswith(nombre + " ") or oficial.startswith(nombre + ","):
                return oficial, "callejero"
            # el candidato agrega el tipo de vía: 'MONTES DE OCA AV.' vs 'MONTES DE OCA'
            if len(oficial) >= 5 and (
                nombre.startswith(oficial + " ") or nombre.startswith(oficial + ",")
            ):
                return oficial, "callejero"
        cercanos = difflib.get_close_matches(
            nombre, oficiales, n=1, cutoff=_SIMILITUD_MINIMA
        )
        if cercanos:
            return cercanos[0], "callejero_fuzzy"
    return None, None


def _comuna_por_altura(entrada: dict, altura: int | None) -> int | None:
    if altura is not None:
        lado = entrada.get("par") if altura % 2 == 0 else entrada.get("impar")
        if lado is not None:
            return lado
    return entrada.get("comuna")


# --------------------------------------------------------------------------- #
# API principal
# --------------------------------------------------------------------------- #

def asignar_comuna(df: pd.DataFrame) -> pd.DataFrame:
    """Completa `comuna` (Int64) y agrega `comuna_fuente` con trazabilidad."""
    rutas = descargar_geodata()
    df = df.copy()

    if "comuna" not in df.columns:
        df["comuna"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
    df["comuna"] = pd.to_numeric(df["comuna"], errors="coerce").astype("Int64")
    df["comuna_fuente"] = pd.Series(pd.NA, index=df.index, dtype="object")
    df.loc[df["comuna"].notna(), "comuna_fuente"] = "archivo"

    # --- 2) catastro: (sección, manzana) ---------------------------------- #
    pendiente = df["comuna"].isna()
    if pendiente.any() and {"seccion", "manzana"} <= set(df.columns):
        poligonos = _cargar_comunas(rutas["comunas"])
        dicc_mz = _dicc_manzana_comuna(rutas["manzanas"], poligonos)
        sub = df.loc[pendiente]
        claves = zip(sub["seccion"].map(_canon_seccion), sub["manzana"].map(_canon_manzana))
        valores = pd.Series(
            [dicc_mz.get(k, pd.NA) for k in claves], index=sub.index, dtype="Int64"
        )
        encontrado = valores.notna()
        df.loc[valores.index[encontrado], "comuna"] = valores[encontrado]
        df.loc[valores.index[encontrado], "comuna_fuente"] = "catastro"

    # --- 3/4) callejero exacto + aproximado ------------------------------- #
    pendiente = df["comuna"].isna()
    if pendiente.any() and "calles" in df.columns:
        dicc_calles = _dicc_calles_comuna(rutas["callejero"])
        oficiales = sorted(dicc_calles)
        sub = df.loc[pendiente]
        normalizadas = sub["calles"].map(_normalizar_calle)

        resuelto: dict[str, tuple[str | None, str | None]] = {}
        for nombre in normalizadas.map(lambda t: t[0]).unique():
            resuelto[nombre] = _resolver_nombre(nombre, dicc_calles, oficiales)

        valores, fuentes = [], []
        for nombre, altura in normalizadas:
            oficial, fuente = resuelto.get(nombre, (None, None))
            if oficial is None:
                valores.append(pd.NA)
                fuentes.append(pd.NA)
            else:
                valores.append(_comuna_por_altura(dicc_calles[oficial], altura))
                fuentes.append(fuente)
        serie = pd.Series(valores, index=sub.index, dtype="Int64")
        fuente_serie = pd.Series(fuentes, index=sub.index, dtype="object")
        encontrado = serie.notna()
        df.loc[serie.index[encontrado], "comuna"] = serie[encontrado]
        df.loc[serie.index[encontrado], "comuna_fuente"] = fuente_serie[encontrado]

    df["comuna_fuente"] = df["comuna_fuente"].fillna("sin_dato")
    return df
