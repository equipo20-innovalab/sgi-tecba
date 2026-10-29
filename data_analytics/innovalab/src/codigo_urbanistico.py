"""Preparación reproducible del Código Urbanístico desde el CSV original."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_loader import PROCESSED_DIR, RAW_DIR
from src.urbanismo import normalizar_smp

RAW_CODIGO = RAW_DIR / "codigo-urbanistico.csv"
OUTPUT_CODIGO = PROCESSED_DIR / "codigo_urbanistico_limpio.csv"
COLUMNAS_CLAVE = ["smp", "uso_1", "uni_edif_1", "fot_em_1", "comuna"]
COLUMNAS_NUMERICAS = ["uni_edif_1", "uso_1", "fot_em_1", "fot_pl_1", "fot_sl_1", "comuna"]


def limpiar_codigo_urbanistico(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica las reglas de limpieza documentadas en el notebook 04."""
    faltantes = [columna for columna in COLUMNAS_CLAVE if columna not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas clave en el Código Urbanístico: {faltantes}")

    limpio = df.copy()
    for columna in limpio.select_dtypes(include=["object", "string"]).columns:
        limpio[columna] = limpio[columna].astype("string").str.strip()
        limpio[columna] = limpio[columna].replace(
            r"(?i)^(?:nan|none|null|na|n/a)?$", pd.NA, regex=True
        )

    limpio["smp"] = limpio["smp"].map(normalizar_smp).astype("string")
    for columna in COLUMNAS_NUMERICAS:
        if columna in limpio.columns:
            limpio[columna] = pd.to_numeric(limpio[columna], errors="coerce")

    limpio = limpio.dropna(subset=COLUMNAS_CLAVE).copy()
    limpio["smp"] = limpio["smp"].astype("string")
    limpio["comuna"] = limpio["comuna"].astype("Int64")
    limpio = limpio.reset_index(drop=True)

    if limpio.empty:
        raise ValueError("La limpieza dejó el Código Urbanístico sin registros.")
    if limpio["smp"].isna().any():
        raise ValueError("El Código Urbanístico contiene SMP nulas.")
    if not limpio["smp"].is_unique:
        raise ValueError("El Código Urbanístico contiene SMP duplicadas.")
    return limpio


def construir_codigo_urbanistico(
    raw: Path = RAW_CODIGO, output: Path = OUTPUT_CODIGO
) -> int:
    """Limpia el CSV de origen y publica su versión procesada de forma atómica."""
    if not raw.is_file():
        raise FileNotFoundError(f"No se encontró el CSV original del Código Urbanístico: {raw}")

    df = pd.read_csv(raw, sep=None, engine="python", dtype={"smp": str})
    limpio = limpiar_codigo_urbanistico(df)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporal = output.with_name(f".{output.name}.tmp")
    try:
        limpio.to_csv(temporal, index=False)
        temporal.replace(output)
    finally:
        temporal.unlink(missing_ok=True)
    return len(limpio)