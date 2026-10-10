"""Tests unitarios de src/estadistica.py (valores conocidos)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.estadistica import (
    agrupar_top,
    chi2_asociacion,
    concentracion,
    cuartiles,
    gini,
    lorenz,
)


def test_gini_reparto_igualitario():
    assert gini([5, 5, 5, 5]) == pytest.approx(0.0)


def test_gini_maxima_concentracion():
    # con n=4, la máxima desigualdad da (n-1)/n = 0.75
    assert gini([0, 0, 0, 10]) == pytest.approx(0.75)


def test_lorenz_extremos():
    x, y = lorenz([1, 1, 1, 1])
    assert y[0] == pytest.approx(0.0)
    assert y[-1] == pytest.approx(1.0)
    assert len(x) == len(y) == 5


def test_cuartiles_valores_conocidos():
    q = cuartiles(range(1, 11))
    assert q["Q1"] == pytest.approx(3.25)
    assert q["Q2 (mediana)"] == pytest.approx(5.5)
    assert q["Q3"] == pytest.approx(7.75)
    assert q["IQR"] == pytest.approx(4.5)


def test_cuartiles_outliers():
    q = cuartiles([1, 2, 3, 4, 5, 100])
    assert q["outliers_sup"] == 1
    assert q["max"] == 100


def test_concentracion_cuotas():
    c = concentracion({"a": 90, "b": 5, "c": 5})
    assert c["categorias"] == 3
    assert c["total"] == 100
    assert c["top_1 (%)"] == pytest.approx(90.0)
    assert c["cat_hasta_50%"] == 1


def test_chi2_independencia_perfecta():
    a = ["A"] * 10 + ["B"] * 10
    b = (["X", "Y"] * 10)
    r = chi2_asociacion(a, b)
    assert r["p_valor"] > 0.05
    assert r["cramers_v"] == pytest.approx(0.0, abs=1e-9)


def test_chi2_asociacion_perfecta():
    a = ["A"] * 10 + ["B"] * 10
    b = ["X"] * 10 + ["Y"] * 10
    r = chi2_asociacion(a, b)
    assert r["p_valor"] < 1e-4
    assert r["cramers_v"] == pytest.approx(1.0)


def test_agrupar_top_colapsa_cola():
    serie = pd.Series(["x"] * 5 + ["y"] * 3 + ["z"] * 1 + ["w"] * 1)
    agrupada = agrupar_top(serie, top=2, etiqueta="Otros")
    assert set(agrupada.unique()) == {"x", "y", "Otros"}
    assert (agrupada == "Otros").sum() == 2
