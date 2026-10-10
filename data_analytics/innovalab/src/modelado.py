"""Construcción de datasets y evaluación para los modelos (notebook 02).

Dos problemas:

1. **Regresión** — tendencia de habilitaciones por (comuna, año).
2. **Clasificación** — predecir la comuna de un local a partir de su perfil de
   actividad (superficie, tipo de trámite, rubro y año). No usa `seccion`,
   `manzana` ni `calles`: esos campos son el mapeo determinístico que ya
   resuelve `src/geografia.py` y constituirían fuga de información.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TOP_RUBROS = 10


def agregado_comuna_anio(df: pd.DataFrame) -> pd.DataFrame:
    """Cantidad de habilitaciones por comuna y año del archivo (target de regresión)."""
    ag = (
        df.dropna(subset=["comuna"])
        .groupby(["comuna", "anio"])
        .size()
        .rename("habilitaciones")
        .reset_index()
    )
    ag["comuna"] = ag["comuna"].astype(int)
    return ag


def features_comuna(
    df: pd.DataFrame, top_rubros: int = TOP_RUBROS
) -> tuple[pd.DataFrame, pd.Series]:
    """Matriz X (perfil de actividad) y target y (comuna) para clasificación."""
    base = df.dropna(subset=["comuna"]).copy()
    frecuentes = base["descripcion_rubro"].value_counts().head(top_rubros).index
    base["rubro_grupo"] = base["descripcion_rubro"].where(
        base["descripcion_rubro"].isin(frecuentes), "Otros"
    )

    numericas = pd.DataFrame(
        {
            "log_superficie": np.log1p(base["superficie"].fillna(0)),
            "anio": base["anio"].astype(float),
        },
        index=base.index,
    )
    dummies = pd.concat(
        [
            pd.get_dummies(base["tipo_tramite"], prefix="tram", drop_first=True),
            pd.get_dummies(base["rubro_grupo"], prefix="rubro", drop_first=True),
        ],
        axis=1,
    )
    X = pd.concat([numericas, dummies], axis=1).astype(float)
    y = base["comuna"].astype(int)
    return X, y


def comparar_clasificadores(
    modelos: dict,
    X_entrena: pd.DataFrame,
    y_entrena: pd.Series,
    X_prueba: pd.DataFrame,
    y_prueba: pd.Series,
) -> pd.DataFrame:
    """Entrena cada clasificador y devuelve accuracy y F1 (macro/weighted)."""
    from sklearn.metrics import accuracy_score, f1_score

    filas = []
    for nombre, modelo in modelos.items():
        modelo.fit(X_entrena, y_entrena)
        pred = modelo.predict(X_prueba)
        filas.append(
            {
                "modelo": nombre,
                "accuracy": accuracy_score(y_prueba, pred),
                "f1_macro": f1_score(y_prueba, pred, average="macro", zero_division=0),
                "f1_weighted": f1_score(y_prueba, pred, average="weighted", zero_division=0),
            }
        )
    return pd.DataFrame(filas).set_index("modelo").sort_values("accuracy", ascending=False)
