from __future__ import annotations

import pandas as pd
import pytest

from src import data_validation
from src.codigo_urbanistico import limpiar_codigo_urbanistico
from src.cleaning import limpiar
from src.data_validation import validar_codigo_urbanistico, validar_habilitaciones


def _padron_valido(filas: int = 2) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "solicitud": range(filas),
            "tipo_tramite": ["Inicial"] * filas,
            "tipo_expediente": ["Comercial"] * filas,
            "subtipo_expediente": ["Local"] * filas,
            "fecha_habilitacion": ["2020-01-01"] * filas,
            "numero_expediente": ["A-1"] * filas,
            "codigo_rubro": [1.0] * filas,
            "descripcion_rubro": ["Rubro"] * filas,
            "superficie": [10.0] * filas,
            "seccion": ["001"] * filas,
            "manzana": ["001"] * filas,
            "parcela": ["001"] * filas,
            "calles": ["Calle 123"] * filas,
            "comuna": [1] * filas,
            "razon_social": ["Comercio"] * filas,
            "partida_matriz": ["1"] * filas,
            "origen": [f"fuente-{i % 7}.csv" for i in range(filas)],
            "anio": [2020] * filas,
            "smp": [f"001-001-{i:03d}" for i in range(filas)],
            "smp_fuente": ["seccion_manzana_parcela"] * filas,
            "fecha_fuente": ["archivo"] * filas,
            "comuna_fuente": ["archivo"] * filas,
        }
    )


def test_valida_contrato_completo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data_validation, "MIN_FILAS", 7)
    validar_habilitaciones(_padron_valido(7))


def test_rechaza_columnas_faltantes() -> None:
    with pytest.raises(ValueError, match="faltan columnas"):
        validar_habilitaciones(pd.DataFrame({"solicitud": [1]}))


def test_rechaza_comuna_fuera_de_rango(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data_validation, "MIN_FILAS", 7)
    df = _padron_valido(7)
    df.loc[0, "comuna"] = 16

    with pytest.raises(ValueError, match="fuera del rango 1..15"):
        validar_habilitaciones(df)


def test_rechaza_smp_duplicada_en_codigo_urbanistico(tmp_path) -> None:
    ruta = tmp_path / "codigo.csv"
    ruta.write_text("smp,uso_1\n001-001-001,1\n001-001-001,2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SMP duplicada"):
        validar_codigo_urbanistico(ruta)


def test_limpia_codigo_urbanistico_y_normaliza_smp() -> None:
    df = pd.DataFrame(
        {
            "smp": [" 001-001-001 ", "002-002-002"],
            "uso_1": ["1", "2"],
            "uni_edif_1": ["10", "20"],
            "fot_em_1": ["3", "4"],
            "fot_pl_1": ["nan", "5"],
            "fot_sl_1": ["", "6"],
            "comuna": ["1", "2"],
        }
    )

    limpio = limpiar_codigo_urbanistico(df)

    assert limpio["smp"].tolist() == ["001-001-001", "002-002-002"]
    assert limpio["comuna"].tolist() == [1, 2]
    assert pd.isna(limpio.loc[0, "fot_pl_1"])


def test_limpieza_asigna_fuente_a_smp_y_fecha() -> None:
    df = pd.DataFrame(
        {
            "seccion": ["001", "inválida"],
            "manzana": ["002", "003"],
            "parcela": ["004", "005"],
            "fecha_habilitacion": ["2020-01-01", None],
            "superficie": [10, 20],
        }
    )

    limpio = limpiar(df)

    assert limpio["smp_fuente"].tolist() == [
        "seccion_manzana_parcela",
        "sin_dato",
    ]
    assert limpio["fecha_fuente"].tolist() == ["archivo", "sin_dato"]


def test_reporte_calidad_incluye_expectativas_y_fuentes() -> None:
    reporte = data_validation.generar_reporte_calidad(_padron_valido(7))

    assert reporte["columnas"]["comuna"]["cobertura"] == 1.0
    assert reporte["columnas"]["smp"]["expectativa_minima"] == 0.75
    assert reporte["fuentes"]["fecha_fuente"]["archivo"] == 7