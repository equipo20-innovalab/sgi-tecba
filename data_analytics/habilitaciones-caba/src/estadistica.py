"""Estadística descriptiva y de concentración.

Sin dependencias nuevas: numpy y pandas. Pensado para el dataset de
habilitaciones (mayormente categórico y con `superficie` zero-inflated).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def agrupar_top(serie: pd.Series, top: int = 15, etiqueta: str = "Otros") -> pd.Series:
    """Colapsa las categorías menos frecuentes de una serie en `etiqueta`."""
    frecuentes = serie.value_counts().head(top).index
    return serie.where(serie.isin(frecuentes), etiqueta)


def chi2_asociacion(serie_a: pd.Series, serie_b: pd.Series) -> pd.Series:
    """Chi-cuadrado de independencia + V de Cramér sobre dos series categóricas."""
    tabla = pd.crosstab(serie_a, serie_b)
    chi2, p, gl, esperada = chi2_contingency(tabla, correction=False)
    n = int(tabla.values.sum())
    k = min(tabla.shape) - 1
    v = float(np.sqrt(chi2 / (n * k))) if k > 0 else float("nan")
    return pd.Series(
        {
            "chi2": chi2,
            "p_valor": p,
            "gl": gl,
            "n": n,
            "cramers_v": v,
            "celdas_esperadas<5": int((esperada < 5).sum()),
            "celdas": int(esperada.size),
        }
    )



def gini(valores) -> float:
    """Índice de Gini: 0 = reparto perfecto, ->1 = máxima concentración."""
    x = np.sort(np.asarray(valores, dtype=float))
    x = x[~np.isnan(x)]
    n = x.size
    if n == 0 or x.sum() == 0:
        return float("nan")
    indice = np.arange(1, n + 1)
    return float(2 * (indice * x).sum() / (n * x.sum()) - (n + 1) / n)


def lorenz(valores) -> tuple[np.ndarray, np.ndarray]:
    """Curva de Lorenz: (proporción acumulada de categorías, de registros)."""
    x = np.sort(np.asarray(valores, dtype=float))
    proporcion = np.concatenate([[0.0], np.cumsum(x) / x.sum()])
    categorias = np.linspace(0.0, 1.0, proporcion.size)
    return categorias, proporcion


def cuartiles(serie, nombre: str = "valor") -> pd.Series:
    """Q1/Q2/Q3, IQR, bigotes de Tukey y outliers de una serie numérica."""
    s = pd.Series(serie).dropna().astype(float)
    q1, q2, q3 = s.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    return pd.Series(
        {
            "n": int(s.size),
            "min": s.min(),
            "Q1": q1,
            "Q2 (mediana)": q2,
            "Q3": q3,
            "IQR": iqr,
            "bigote_sup (Q3+1.5·IQR)": q3 + 1.5 * iqr,
            "max": s.max(),
            "p90": s.quantile(0.90),
            "p99": s.quantile(0.99),
            "outliers_sup": int((s > q3 + 1.5 * iqr).sum()),
        },
        name=nombre,
    )


def cuartiles_por_grupo(
    df: pd.DataFrame,
    grupo: str,
    valor: str,
    solo_positivos: bool = True,
    min_casos: int = 30,
) -> pd.DataFrame:
    """Cuartiles de `valor` dentro de cada categoría de `grupo`.

    Omite grupos con menos de `min_casos` observaciones para que los
    cuartiles sean interpretables.
    """
    base = df[[grupo, valor]].dropna()
    if solo_positivos:
        base = base[base[valor] > 0]

    filas = []
    for clave, sub in base.groupby(grupo):
        if len(sub) < min_casos:
            continue
        q1, q2, q3 = sub[valor].quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        filas.append(
            {
                grupo: clave,
                "n": len(sub),
                "Q1": q1,
                "mediana": q2,
                "Q3": q3,
                "IQR": iqr,
                "max": sub[valor].max(),
                "outliers": int((sub[valor] > q3 + 1.5 * iqr).sum()),
            }
        )
    return pd.DataFrame(filas).set_index(grupo)


def concentracion(conteos) -> pd.Series:
    """Gini y cuotas de una serie de conteos por categoría."""
    c = pd.Series(conteos).astype(float).sort_values(ascending=False)
    total = c.sum()
    acumulada = c.cumsum() / total
    return pd.Series(
        {
            "categorias": int(c.size),
            "total": int(total),
            "Gini": gini(c.values),
            "top_1 (%)": 100 * c.iloc[:1].sum() / total,
            "top_3 (%)": 100 * c.iloc[:3].sum() / total,
            "top_5 (%)": 100 * c.iloc[:5].sum() / total,
            "cat_hasta_50%": int((acumulada < 0.5).sum() + 1),
        }
    )
