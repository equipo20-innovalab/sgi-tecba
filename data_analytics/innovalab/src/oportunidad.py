"""Clustering geográfico y índice de oportunidad comercial.

Responde a la pregunta del producto: ¿en qué comuna y rubro conviene
abrir un local comercial en la CABA?

Dos piezas:

* ``clusterizar_comunas`` agrupa comunas por perfil de actividad (KMeans
  o DBSCAN sobre features estandarizadas).
* ``indice_oportunidad`` calcula una nota 0-100 por combinación
  (comuna, rubro) combinando crecimiento, saturación y subrepresentación.

El índice es una **herramienta de orientación**, no una predicción: la
fórmula y los pesos quedan documentados para que cualquier revisor pueda
auditarla.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .cleaning import _corregir_mojibake

# Pesos por defecto del índice de oportunidad.
PESOS_DEFECTO = {"crecimiento": 0.40, "baja_saturacion": 0.40, "subrepresentacion": 0.20}

# Columnas de features usadas por el clustering de comunas.
FEATURES_COMUNA = [
    "n_licencias",
    "rubros_distintos",
    "superficie_promedio",
    "tasa_nuevas",
    "diversidad_top10",
]


def _min_max(serie: pd.Series) -> pd.Series:
    """Escala una serie a [0, 1] evitando división por cero.

    Los valores ausentes quedan en 0,5 (punto medio), que es la decisión
    neutra: no penaliza ni beneficia a la observación incompleta.
    """
    s = serie.astype(float)
    if s.notna().sum() == 0:
        return pd.Series(0.5, index=s.index)
    minimo, maximo = np.nanmin(s), np.nanmax(s)
    rango = maximo - minimo
    if not np.isfinite(rango) or rango == 0:
        return pd.Series(0.5, index=s.index)
    return ((s - minimo) / rango).fillna(0.5)


def preparar_features_comuna_rubro(
    df: pd.DataFrame,
    anio_ref: int | None = None,
    min_licencias: int = 5,
    top_rubros: int | None = None,
) -> pd.DataFrame:
    """Construye la tabla (comuna × rubro) con las métricas del índice.

    Parámetros
    ----------
    df : DataFrame limpio del padrón (columnas: comuna, descripcion_rubro,
        anio, tipo_tramite, superficie).
    anio_ref : año de referencia para el crecimiento. Si es None se usa el
        máximo disponible en el dataset.
    min_licencias : descarta combinaciones con menos licencias que este
        umbral, porque el crecimiento calculado sobre pocas observaciones
        no es significativo.
    top_rubros : si se indica, limita el análisis a los N rubros más
        frecuentes del dataset (útil para acelerar y para enfocarse en
        rubros con masa crítica).

    Devuelve
    --------
    DataFrame indexado por (comuna, rubro) con columnas:
        n_licencias, n_nuevas, crecimiento, superficie_promedio,
        saturacion, subrepresentacion, oportunidad
    """
    base = df.copy()
    base["rubro"] = base["descripcion_rubro"].map(_corregir_mojibake)
    base = base.dropna(subset=["comuna", "rubro", "anio"])
    base["comuna"] = base["comuna"].astype(int)
    base["anio"] = base["anio"].astype(int)

    if top_rubros is not None:
        permitidos = base["rubro"].value_counts().head(top_rubros).index
        base = base[base["rubro"].isin(permitidos)]

    if anio_ref is None:
        anio_ref = int(base["anio"].max())

    # --- crecimiento anualizado -------------------------------------------
    # El padrón tiene años con cobertura muy distinta (2015 concentra ~63% de
    # los registros y faltan 2016/2017/2018/2022). Medir crecimiento sobre el
    # conteo crudo mediría la cobertura del archivo, no el mercado. Por eso se
    # mide el crecimiento de la **cuota** del rubro dentro del total de su
    # comuna en cada año: así el efecto "año con más datos" se cancela.
    conteos = (
        base.groupby(["comuna", "rubro", "anio"])
        .size()
        .rename("n")
        .reset_index()
    )
    total_comuna_anio = (
        base.groupby(["comuna", "anio"]).size().rename("total_comuna").reset_index()
    )
    conteos = conteos.merge(total_comuna_anio, on=["comuna", "anio"], how="left")
    conteos["cuota"] = conteos["n"] / conteos["total_comuna"].replace(0, np.nan)

    def _tasa_anual(grupo: pd.DataFrame) -> float:
        """Crecimiento anualizado de la cuota entre primer y último año."""
        grupo = grupo.dropna(subset=["cuota"]).sort_values("anio")
        if len(grupo) < 2:
            return 0.0
        anios = grupo["anio"].to_numpy(dtype=float)
        cuotas = grupo["cuota"].to_numpy(dtype=float)
        if anios[-1] - anios[0] < 1 or cuotas[0] <= 0:
            return 0.0
        return float((cuotas[-1] / cuotas[0]) ** (1.0 / (anios[-1] - anios[0])) - 1.0)

    crecimiento = conteos.groupby(["comuna", "rubro"]).apply(_tasa_anual)

    # --- métricas por combinación ------------------------------------------
    nuevas = (
        base[base["tipo_tramite"].str.lower().str.contains("habilitaci", na=False)]
        .groupby(["comuna", "rubro"])
        .size()
        .rename("n_nuevas")
    )

    agregado = (
        base.groupby(["comuna", "rubro"])
        .agg(
            n_licencias=("rubro", "size"),
            superficie_promedio=("superficie", "mean"),
        )
        .join(crecimiento.rename("crecimiento"))
        .join(nuevas)
        .fillna({"n_nuevas": 0, "crecimiento": 0.0})
        .reset_index()
    )

    agregado = agregado[agregado["n_licencias"] >= min_licencias].copy()

    # --- saturación: licencias del rubro en la comuna sobre la media -------
    #     ratio > 1 => el rubro está sobrerepresentado en esa comuna
    media_comuna = agregado.groupby("comuna")["n_licencias"].transform("mean")
    agregado["saturacion"] = (agregado["n_licencias"] / media_comuna.replace(0, np.nan)).fillna(0.0)

    # --- subrepresentación: cuota de la comuna vs cuota esperada -----------
    total_rubro = agregado.groupby("rubro")["n_licencias"].transform("sum")
    total_comuna = agregado.groupby("comuna")["n_licencias"].transform("sum")
    total = agregado["n_licencias"].sum()
    cuota_observada = agregado["n_licencias"] / total_rubro.replace(0, np.nan)
    cuota_esperada = total_comuna / total
    agregado["subrepresentacion"] = (
        (cuota_esperada - cuota_observada) / cuota_esperada.replace(0, np.nan)
    ).fillna(0.0)

    agregado = agregado.set_index(["comuna", "rubro"]).sort_index()
    return agregado


def indice_oportunidad(
    tabla: pd.DataFrame,
    pesos: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calcula la nota de oportunidad 0-100 por (comuna, rubro).

    La nota combina tres señales, cada una escalada a [0, 1]:

    * ``crecimiento`` (40%): más crecimiento => más oportunidad.
    * ``baja_saturacion`` (40%): menos saturación => más oportunidad.
    * ``subrepresentacion`` (20%): el rubro está poco presente en la comuna
      respecto de lo esperado => más oportunidad.

    Los pesos se normalizan para que sumen 1, así que se puede pasar
    cualquiera y el resto se ajusta automáticamente.
    """
    pesos = {**PESOS_DEFECTO, **(pesos or {})}
    normalizados = pd.Series(pesos, dtype=float)
    normalizados = normalizados / normalizados.sum()

    componentes = pd.DataFrame(index=tabla.index)
    componentes["crecimiento"] = _min_max(tabla["crecimiento"])
    componentes["baja_saturacion"] = 1.0 - _min_max(tabla["saturacion"])
    componentes["subrepresentacion"] = _min_max(tabla["subrepresentacion"])

    ponderado = sum(componentes[c] * normalizados.get(c, 0.0) for c in componentes)
    salida = tabla.copy()
    salida["oportunidad"] = (ponderado * 100).round(1)
    for c in componentes:
        salida[f"componente_{c}"] = (componentes[c] * 100).round(1)
    return salida


def clusterizar_comunas(
    df: pd.DataFrame,
    k: int = 5,
    metodo: str = "kmeans",
    random_state: int = 42,
    eps: float = 0.8,
    min_samples: int = 3,
) -> pd.DataFrame:
    """Segmenta las comunas por perfil de actividad.

    Features por comuna: volumen de licencias, cantidad de rubros
    distintos, superficie promedio, proporción de trámites de habilitación
    nueva y diversidad (1 - concentración del top 10 de rubros).

    Parámetros
    ----------
    k : cantidad de clusters para KMeans (ignorado con ``metodo="dbscan"``).
    metodo : ``"kmeans"`` o ``"dbscan"``.

    Devuelve
    --------
    DataFrame indexado por comuna con las features y la columna ``cluster``.
    """
    base = df.copy()
    base["rubro"] = base["descripcion_rubro"].map(_corregir_mojibake)
    base = base.dropna(subset=["comuna"])
    base["comuna"] = base["comuna"].astype(int)

    nuevas_mask = base["tipo_tramite"].str.lower().str.contains("habilitaci", na=False)

    filas = []
    for comuna, sub in base.groupby("comuna"):
        top = sub["rubro"].value_counts(normalize=True).head(10)
        filas.append(
            {
                "comuna": comuna,
                "n_licencias": len(sub),
                "rubros_distintos": sub["rubro"].nunique(),
                "superficie_promedio": sub["superficie"].mean(),
                "tasa_nuevas": nuevas_mask.loc[sub.index].mean(),
                "diversidad_top10": 1.0 - float(top.sum()) if len(top) else 0.0,
            }
        )

    tabla = pd.DataFrame(filas).set_index("comuna")
    X = StandardScaler().fit_transform(tabla[FEATURES_COMUNA])

    if metodo == "dbscan":
        etiquetas = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(X)
    else:
        etiquetas = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit_predict(X)

    tabla["cluster"] = etiquetas
    return tabla.sort_index()


def evaluar_k(
    df: pd.DataFrame,
    k_min: int = 2,
    k_max: int = 8,
    random_state: int = 42,
) -> pd.DataFrame:
    """Silhouette score para distintos valores de k.

    Sirve para elegir el número de clusters con criterio, no a ojo.
    """
    base = clusterizar_comunas(df, k=k_min, metodo="kmeans", random_state=random_state)
    X = StandardScaler().fit_transform(base[FEATURES_COMUNA])

    filas = []
    for k in range(k_min, k_max + 1):
        etiquetas = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit_predict(X)
        filas.append(
            {
                "k": k,
                "silhouette": round(float(silhouette_score(X, etiquetas)), 4),
                "cluster_mas_grande": int(pd.Series(etiquetas).value_counts().max()),
                "cluster_mas_chico": int(pd.Series(etiquetas).value_counts().min()),
            }
        )
    return pd.DataFrame(filas)


def recomendar(
    tabla_oportunidad: pd.DataFrame,
    comuna: int | None = None,
    rubro: str | None = None,
    top_n: int = 10,
    min_licencias: int = 10,
) -> pd.DataFrame:
    """Devuelve las mejores oportunidades ordenadas por nota.

    Permite filtrar por comuna y/o por rubro (búsqueda parcial, sin
    distinguir mayúsculas ni acentos).
    """
    salida = tabla_oportunidad[tabla_oportunidad["n_licencias"] >= min_licencias]

    if comuna is not None:
        salida = salida.loc[salida.index.get_level_values("comuna") == int(comuna)]
    if rubro is not None:
        objetivo = str(rubro).strip().lower()
        mascaras = [
            str(r).strip().lower().find(objetivo) >= 0
            for r in salida.index.get_level_values("rubro")
        ]
        salida = salida[np.array(mascaras)]

    columnas = [
        "n_licencias",
        "crecimiento",
        "saturacion",
        "subrepresentacion",
        "oportunidad",
    ]
    columnas = [c for c in columnas if c in salida.columns]
    return salida.sort_values("oportunidad", ascending=False).head(top_n)[columnas]
