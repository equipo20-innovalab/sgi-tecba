"""Data contract del dataset procesado.

Garantiza que `habilitaciones_caba_clean.csv` cumple las condiciones que
asume el EDA, el futuro entrenamiento de ML y los exports para RAG.

    python -m pytest tests/ -v
"""

from __future__ import annotations

import pandas as pd
import pytest

COLUMNAS_ESPERADAS = {
    "solicitud",
    "tipo_tramite",
    "tipo_expediente",
    "subtipo_expediente",
    "fecha_habilitacion",
    "numero_expediente",
    "codigo_rubro",
    "descripcion_rubro",
    "superficie",
    "seccion",
    "manzana",
    "parcela",
    "calles",
    "comuna",
    "razon_social",
    "partida_matriz",
    "origen",
    "anio",
    "smp",
    "comuna_fuente",
}

COMUNAS_FUENTE_VALIDAS = {
    "archivo",
    "catastro",
    "callejero",
    "callejero_fuzzy",
    "sin_dato",
}

# techo de nulos aceptado por columna (%, medido en la corrida de validación)
NULOS_MAX_PCT = {
    "comuna": 10.0,
    "smp": 25.0,
    "codigo_rubro": 35.0,
    "razon_social": 90.0,
    "calles": 5.0,
    "origen": 0.0,
    "anio": 0.0,
    "comuna_fuente": 0.0,
}


def test_archivo_existe(df):
    assert len(df) > 0


def test_esquema_completo(df):
    faltantes = COLUMNAS_ESPERADAS - set(df.columns)
    assert not faltantes, f"faltan columnas: {sorted(faltantes)}"


def test_volumen_minimo(df):
    assert len(df) >= 200_000, f"solo {len(df):,} filas (se esperaban >= 200.000)"


def test_comuna_en_rango(df):
    comuna = df["comuna"].dropna()
    assert comuna.between(1, 15).all(), (
        f"valores de comuna fuera de 1..15: "
        f"{sorted(comuna[~comuna.between(1, 15)].unique())[:10]}"
    )


def test_cobertura_comuna_minima(df):
    cobertura = df["comuna"].notna().mean()
    assert cobertura >= 0.90, f"cobertura de comuna: {cobertura:.1%} (< 90%)"


def test_comuna_fuente_valida(df):
    assert df["comuna_fuente"].notna().any(), "comuna_fuente sin valores"
    invalidas = set(df["comuna_fuente"].dropna().unique()) - COMUNAS_FUENTE_VALIDAS
    assert not invalidas, f"comuna_fuente inválida: {sorted(invalidas)}"


def test_anio_en_rango(df):
    anio = df["anio"]
    assert anio.notna().all(), "anio tiene nulos"
    assert anio.between(2015, 2026).all(), (
        f"años fuera de 2015..2026: {sorted(anio[~anio.between(2015, 2026)].unique())}"
    )


def test_superficie_no_negativa(df):
    negativas = (df["superficie"] < 0).sum()
    assert negativas == 0, f"{negativas} filas con superficie negativa"


def test_nulos_por_columna(df):
    for columna, tope in NULOS_MAX_PCT.items():
        pct = df[columna].isna().mean() * 100
        assert pct <= tope, f"{columna}: {pct:.1f}% nulos (tope {tope}%)"


def test_sin_duplicados_totales(df):
    duplicadas = df.duplicated().sum()
    assert duplicadas == 0, f"{duplicadas} filas duplicadas exactas"


def test_fecha_habilitacion_parseable(df):
    fechas = pd.to_datetime(df["fecha_habilitacion"], errors="coerce")
    parseo = fechas.notna().mean()
    assert parseo >= 0.70, f"solo {parseo:.1%} de fechas válidas (mínimo 70%)"


def test_origenes_consistentes(df):
    assert df["origen"].str.endswith(".csv").all(), "origen con nombres raros"
    assert df["origen"].nunique() >= 7, "se esperaban >= 7 archivos fuente"
