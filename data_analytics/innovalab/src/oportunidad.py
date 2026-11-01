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

# Componentes que forman la nota (en el orden en que se documentan).
COMPONENTES = ("crecimiento", "baja_saturacion", "subrepresentacion")

# Versión de la fórmula. Se incrementa cuando cambian pesos, normalizaciones o
# la definición de algún componente. El changelog narrativo vive en
# docs/indice_oportunidad_formula.md y el legible por máquina en VERSIONES_FORMULA.
VERSION_FORMULA = "1.0.0"

VERSIONES_FORMULA: list[dict] = [
    {
        "version": "1.0.0",
        "fecha": "2026-10-28",
        "cambios": [
            "Primera versión versionada y persistida del índice.",
            "Pesos 40/40/20 sobre crecimiento, baja saturación y subrepresentación.",
            "El crecimiento se mide sobre la cuota del rubro en la comuna (no sobre el conteo crudo).",
            "Se agregan artefacto reproducible (CSV + metadatos), tabla consultable y backtest mínimo.",
        ],
        "pesos": PESOS_DEFECTO,
    }
]

# Columnas de features usadas por el clustering de comunas.
FEATURES_COMUNA = [
    "n_licencias",
    "rubros_distintos",
    "superficie_promedio",
    "tasa_nuevas",
    "diversidad_top10",
]


def _normalizar_pesos(pesos: dict[str, float] | None = None) -> pd.Series:
    """Completa y normaliza los pesos para que sumen 1.

    Es la única fuente de verdad de los pesos efectivos: la usan tanto el
    cálculo del índice como el artefacto persistido y la explicación.
    """
    combinados = {**PESOS_DEFECTO, **(pesos or {})}
    serie = pd.Series(combinados, dtype=float)
    if serie.sum() <= 0:
        raise ValueError("Los pesos deben sumar un valor positivo.")
    return serie / serie.sum()


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
    normalizados = _normalizar_pesos(pesos)

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


# ---------------------------------------------------------------------------
# Artefacto reproducible, explicable y backtest
# ---------------------------------------------------------------------------

# Orden estable de columnas del artefacto (CSV y tabla Postgres).
COLUMNAS_ARTEFACTO = (
    "comuna",
    "rubro",
    "oportunidad",
    "componente_crecimiento",
    "componente_baja_saturacion",
    "componente_subrepresentacion",
    "peso_crecimiento",
    "peso_baja_saturacion",
    "peso_subrepresentacion",
    "aporte_crecimiento",
    "aporte_baja_saturacion",
    "aporte_subrepresentacion",
    "crecimiento",
    "saturacion",
    "subrepresentacion",
    "n_licencias",
    "n_nuevas",
    "superficie_promedio",
    "anio_ref",
    "formula_version",
    "calculado_en",
    "explicacion",
)


def construir_artefacto_oportunidad(
    df: pd.DataFrame,
    *,
    pesos: dict[str, float] | None = None,
    anio_ref: int | None = None,
    min_licencias: int = 5,
    top_rubros: int | None = None,
    calculado_en: object | None = None,
    version: str = VERSION_FORMULA,
) -> pd.DataFrame:
    """Calcula el índice y devuelve una tabla plana lista para persistir.

    A diferencia de ``indice_oportunidad`` (que devuelve un DataFrame con
    índice ``(comuna, rubro)`` pensado para explorar), esta función produce
    **una fila por combinación** con todo lo necesario para auditar el score:

    * la nota y sus tres componentes (0-100),
    * los pesos efectivos normalizados y el aporte de cada componente,
    * las métricas crudas (crecimiento, saturación, subrepresentación),
    * ``n_licencias``, ``n_nuevas``, ``superficie_promedio`` y ``anio_ref``,
    * ``formula_version``, ``calculado_en`` y una ``explicacion`` textual.

    Es determinista para los mismos datos, pesos y ``calculado_en``.
    """
    if df is None or len(df) == 0:
        raise ValueError("El DataFrame de entrada está vacío.")

    if anio_ref is None and "anio" in df.columns:
        # Último año con masa crítica (>=100 filas). Evita tomar años con 1-2
        # registros (p. ej. 2026) como referencia del cálculo. Si no hubiera
        # ningún año con masa crítica, se usa el máximo disponible.
        conteo = pd.to_numeric(df["anio"], errors="coerce").dropna()
        conteo = conteo.astype(int).value_counts().sort_index()
        suficientes = conteo[conteo >= 100]
        if len(suficientes):
            anio_ref = int(suficientes.index.max())
        elif len(conteo):
            anio_ref = int(conteo.index.max())

    tabla = preparar_features_comuna_rubro(
        df,
        anio_ref=anio_ref,
        min_licencias=min_licencias,
        top_rubros=top_rubros,
    )
    if len(tabla) == 0:
        raise ValueError(
            "El índice quedó vacío: probá con un min_licencias más bajo o "
            "con más datos de entrada."
        )

    opp = indice_oportunidad(tabla, pesos=pesos)
    normalizados = _normalizar_pesos(pesos)

    if calculado_en is None:
        calculado_en = pd.Timestamp.now(tz="UTC")
    else:
        calculado_en = pd.Timestamp(calculado_en)
        if calculado_en.tzinfo is None:
            calculado_en = calculado_en.tz_localize("UTC")

    indice = opp.index
    artefacto = pd.DataFrame(
        {
            "comuna": indice.get_level_values("comuna").astype(int),
            "rubro": indice.get_level_values("rubro").astype(str),
            "oportunidad": opp["oportunidad"].to_numpy(),
            "componente_crecimiento": opp["componente_crecimiento"].to_numpy(),
            "componente_baja_saturacion": opp["componente_baja_saturacion"].to_numpy(),
            "componente_subrepresentacion": opp["componente_subrepresentacion"].to_numpy(),
            "peso_crecimiento": float(normalizados["crecimiento"]),
            "peso_baja_saturacion": float(normalizados["baja_saturacion"]),
            "peso_subrepresentacion": float(normalizados["subrepresentacion"]),
            "crecimiento": opp["crecimiento"].to_numpy(),
            "saturacion": opp["saturacion"].to_numpy(),
            "subrepresentacion": opp["subrepresentacion"].to_numpy(),
            "n_licencias": opp["n_licencias"].astype(int).to_numpy(),
            "n_nuevas": opp["n_nuevas"].fillna(0).astype(int).to_numpy(),
            "superficie_promedio": opp["superficie_promedio"].to_numpy(),
            "anio_ref": anio_ref,
            "formula_version": version,
            "calculado_en": calculado_en,
        }
    )

    for componente in COMPONENTES:
        artefacto[f"aporte_{componente}"] = (
            artefacto[f"componente_{componente}"]
            * float(normalizados[componente])
        ).round(2)

    artefacto["explicacion"] = artefacto.apply(
        lambda fila: explicar_oportunidad(fila)["resumen"], axis=1
    )

    return artefacto.loc[:, list(COLUMNAS_ARTEFACTO)].sort_values(
        ["comuna", "rubro"], ignore_index=True
    )


def explicar_oportunidad(fila: pd.Series | dict) -> dict:
    """Desglosa por qué una combinación (comuna, rubro) obtuvo su nota.

    Devuelve los aportes de cada componente, la suma de aportes y un texto
    legible. La suma puede diferir en ±0,1 de ``oportunidad`` por redondeo:
    ese residuo se informa en ``diferencia_redondeo``.
    """
    oportunidad = float(fila["oportunidad"])
    aportes = {
        componente: round(
            float(fila[f"componente_{componente}"]) * float(fila[f"peso_{componente}"]),
            2,
        )
        for componente in COMPONENTES
    }
    suma = round(sum(aportes.values()), 2)
    pesos = {componente: float(fila[f"peso_{componente}"]) for componente in COMPONENTES}

    detalle = " + ".join(
        f"{componente} {float(fila[f'componente_{componente}']):.1f}×{pesos[componente]:.2f} ({aportes[componente]:.1f})"
        for componente in COMPONENTES
    )
    resumen = (
        f"Oportunidad {oportunidad:.1f} = {detalle} · "
        f"n_licencias={int(fila['n_licencias'])} · fórmula {fila['formula_version']}"
    )

    return {
        "oportunidad": oportunidad,
        "formula_version": str(fila["formula_version"]),
        "pesos": pesos,
        "componentes": {
            componente: float(fila[f"componente_{componente}"])
            for componente in COMPONENTES
        },
        "aportes": aportes,
        "suma_aportes": suma,
        "diferencia_redondeo": round(oportunidad - suma, 2),
        "n_licencias": int(fila["n_licencias"]),
        "resumen": resumen,
    }


def metadatos_artefacto(
    artefacto: pd.DataFrame,
    *,
    fuente: str | None = None,
    fuente_sha256: str | None = None,
    parametros: dict | None = None,
    notas: str | None = None,
) -> dict:
    """Metadatos de la corrida que acompañan al CSV del índice.

    Incluye versión de fórmula, fecha de cálculo, pesos efectivos, parámetros
    y huella del archivo de origen para poder reproducir el artefacto.
    """
    if artefacto is None or len(artefacto) == 0:
        raise ValueError("No se pueden generar metadatos de un artefacto vacío.")

    calculado_en = pd.Timestamp(artefacto["calculado_en"].iloc[0])
    return {
        "formula_version": str(artefacto["formula_version"].iloc[0]),
        "calculado_en": calculado_en.isoformat(),
        "pesos": {
            "crecimiento": float(artefacto["peso_crecimiento"].iloc[0]),
            "baja_saturacion": float(artefacto["peso_baja_saturacion"].iloc[0]),
            "subrepresentacion": float(artefacto["peso_subrepresentacion"].iloc[0]),
        },
        "parametros": parametros or {},
        "n_filas": int(len(artefacto)),
        "n_comunas": int(artefacto["comuna"].nunique()),
        "n_rubros": int(artefacto["rubro"].nunique()),
        "anio_ref": int(artefacto["anio_ref"].iloc[0]),
        "fuente": fuente,
        "fuente_sha256": fuente_sha256,
        "notas": notas,
    }


def _anios_elegibles(base: pd.DataFrame, min_registros: int) -> list[int]:
    """Años con al menos ``min_registros`` filas, de menor a mayor."""
    conteo = base.groupby("anio").size()
    return [int(anio) for anio, n in conteo.items() if int(n) >= min_registros]


def backtest_oportunidad(
    df: pd.DataFrame,
    *,
    anio_corte: int | None = None,
    anio_evaluacion: int | None = None,
    pesos: dict[str, float] | None = None,
    min_licencias: int = 5,
    top_rubros: int | None = None,
    top_k: int = 10,
    min_registros_anio: int = 100,
) -> dict:
    """Backtest mínimo: entrena el índice con datos hasta un año y lo contrasta
    contra el crecimiento realizado en el año siguiente.

    Evita fuga de información: el artefacto se calcula **solo** con filas
    ``anio <= anio_corte``. El contraste usa el cambio de cuota del rubro
    dentro de su comuna (la misma métrica que alimenta el componente de
    crecimiento), entre ``anio_corte`` y ``anio_evaluacion``.

    Devuelve un dict con la correlación de rangos (Spearman) y la tasa de
    acierto del top-k. Un valor cercano a 0 indica que el índice no anticipa
    el crecimiento relativo; no debe leerse como validación causal.
    """
    base = df.copy()
    if "descripcion_rubro" not in base.columns:
        raise ValueError("El DataFrame debe incluir 'descripcion_rubro'.")
    base["rubro"] = base["descripcion_rubro"].map(_corregir_mojibake)
    base = base.dropna(subset=["comuna", "rubro", "anio"])
    base["comuna"] = base["comuna"].astype(int)
    base["anio"] = base["anio"].astype(int)

    elegibles = _anios_elegibles(base, min_registros_anio)
    if len(elegibles) < 2:
        raise ValueError(
            "Se necesitan al menos dos años con datos suficientes para hacer "
            "el backtest."
        )

    if anio_evaluacion is None:
        anio_evaluacion = elegibles[-1]
    if anio_corte is None:
        previos = [anio for anio in elegibles if anio < anio_evaluacion]
        if not previos:
            raise ValueError(
                f"No hay un año anterior a {anio_evaluacion} con datos suficientes."
            )
        anio_corte = previos[-1]

    if anio_corte >= anio_evaluacion:
        raise ValueError("anio_corte debe ser menor que anio_evaluacion.")

    train = base[base["anio"] <= anio_corte]
    artefacto = construir_artefacto_oportunidad(
        train,
        pesos=pesos,
        min_licencias=min_licencias,
        top_rubros=top_rubros,
    )

    ventana = base[base["anio"].isin([anio_corte, anio_evaluacion])]
    conteos = ventana.groupby(["comuna", "rubro", "anio"]).size().rename("n").reset_index()
    totales = ventana.groupby(["comuna", "anio"]).size().rename("total").reset_index()
    conteos = conteos.merge(totales, on=["comuna", "anio"], how="left")
    conteos["cuota"] = conteos["n"] / conteos["total"].replace(0, np.nan)
    pivote = conteos.pivot_table(
        index=["comuna", "rubro"], columns="anio", values="cuota"
    )

    resultado = {
        "formula_version": VERSION_FORMULA,
        "anio_corte": int(anio_corte),
        "anio_evaluacion": int(anio_evaluacion),
        "n_entrenamiento": int(len(train)),
        "n_comparables": 0,
        "spearman": None,
        "top_k": int(top_k),
        "top_k_hit_rate": None,
        "pesos": _normalizar_pesos(pesos).round(4).to_dict(),
        "min_licencias": int(min_licencias),
        "top_rubros": top_rubros,
        "notas": (
            "Backtest descriptivo de una sola ventana; no es validación causal. "
            "La cobertura del padrón varía fuerte entre años, por eso se usa "
            "cuota (share) y no conteo crudo."
        ),
    }

    if anio_corte not in pivote.columns or anio_evaluacion not in pivote.columns:
        return resultado

    cuota_inicial = pivote[anio_corte]
    cuota_final = pivote[anio_evaluacion]
    anios_ventana = max(1, int(anio_evaluacion) - int(anio_corte))
    realizado = (
        (cuota_final / cuota_inicial.replace(0, np.nan)) ** (1.0 / anios_ventana) - 1.0
    ).rename("crecimiento_realizado")

    comparables = (
        artefacto.set_index(["comuna", "rubro"])["oportunidad"]
        .to_frame()
        .join(realizado, how="inner")
        .dropna()
    )
    resultado["n_comparables"] = int(len(comparables))
    if len(comparables) < 2:
        return resultado

    if (
        comparables["oportunidad"].nunique() > 1
        and comparables["crecimiento_realizado"].nunique() > 1
    ):
        correlacion = comparables["oportunidad"].rank().corr(
            comparables["crecimiento_realizado"].rank()
        )
        if pd.notna(correlacion):
            resultado["spearman"] = round(float(correlacion), 3)

    k = min(int(top_k), len(comparables))
    if k > 0:
        top_predicho = set(comparables["oportunidad"].nlargest(k).index)
        top_real = set(comparables["crecimiento_realizado"].nlargest(k).index)
        resultado["top_k"] = k
        resultado["top_k_hit_rate"] = round(len(top_predicho & top_real) / k, 3)

    return resultado
