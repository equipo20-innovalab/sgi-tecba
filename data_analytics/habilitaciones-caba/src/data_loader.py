"""Carga de datos crudos del proyecto Inovalab.

Estructura de datos (rutas relativas al raíz del proyecto, resueltas con pathlib):

    data/raw/       CSV crudos exportados del portal de datos abiertos del GCBA
    data/processed/ datasets limpios generados por el pipeline
    data/geo/       capas geográficas oficiales (descargadas on demand)
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
GEO_DIR = PROJECT_ROOT / "data" / "geo"

# Exportación manual "Solicitud;All" (20 filas, sin estructura tabular): se excluye.
ARCHIVOS_EXCLUIDOS = {"habilitaciones-aprobadas2022.csv"}


def listar_archivos_raw() -> list[Path]:
    """CSV de data/raw/ en orden de carga, excluyendo los no tabulares."""
    return [
        ruta
        for ruta in sorted(RAW_DIR.glob("*.csv"))
        if ruta.name not in ARCHIVOS_EXCLUIDOS
    ]


def _leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee un CSV del padrón de CABA.

    Los exports mezclan formatos: el histórico usa ';' con latin1 y los archivos
    modernos (2025) usan ',' con utf-8-sig. Se prueba ';' primero y se hace
    fallback a ',' si el parser falla.
    """
    try:
        return pd.read_csv(ruta, sep=";", encoding="latin1", low_memory=False)
    except Exception:
        return pd.read_csv(ruta, sep=",", encoding="utf-8-sig", low_memory=False)


def load_raw() -> pd.DataFrame:
    """Carga y concatena todos los CSV de data/raw/.

    Agrega dos columnas de procedencia:
        origen: nombre del archivo fuente
        anio:   año detectado en el nombre del archivo
    """
    rutas = listar_archivos_raw()
    if not rutas:
        raise FileNotFoundError(f"No se encontraron CSV en {RAW_DIR}")

    excluidos = sorted(
        ruta.name for ruta in RAW_DIR.glob("*.csv") if ruta.name in ARCHIVOS_EXCLUIDOS
    )
    partes = []
    for ruta in rutas:
        df = _leer_csv(ruta)
        match = re.search(r"(20\d{2})", ruta.name)
        meta = pd.DataFrame(
            {"origen": ruta.name, "anio": int(match.group(1)) if match else pd.NA},
            index=df.index,
        )
        df = pd.concat([df, meta], axis=1)
        partes.append(df)
        print(f"OK  {ruta.name:<40} {df.shape[0]:>7} filas x {df.shape[1]:>3} columnas")

    if excluidos:
        print(f"Excluidos (sin estructura tabular): {', '.join(excluidos)}")

    df = pd.concat(partes, ignore_index=True, sort=False)
    print(f"Total crudo: {df.shape[0]} filas x {df.shape[1]} columnas")
    return df


def load_processed(nombre: str = "habilitaciones_caba_clean.csv") -> pd.DataFrame:
    """Relee el dataset limpio generado por el pipeline."""
    ruta = PROCESSED_DIR / nombre
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}. Ejecutá primero el notebook 01.")
    try:
        return pd.read_csv(ruta, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(ruta, encoding="latin1", low_memory=False)
