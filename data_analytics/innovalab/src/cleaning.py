"""Limpieza y armonización del padrón de habilitaciones de CABA.

Unifica dos esquemas de origen:

* Esquema clásico (2015-2024): solicitud, tipo_tramite, numero_expediente, etc.
* Esquema moderno (2025-2026): razon_social, rubro, domicilio, comuna, etc.

Ambos se normalizan a un esquema común de 16 columnas de contenido más las
dos columnas de procedencia (origen, anio) y la clave catastral SMP
(sección-manzana-parcela) para vinculación externa con APIs del GCBA.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Esquema común: 14 columnas clásicas + 2 enriquecidas
COLUMNAS_CORE = [
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
]
COLUMNAS_EXTRA = ["razon_social", "partida_matriz"]
COLUMNAS_PROCEDENCIA = ["origen", "anio"]

# columnas del esquema moderno (2025/2026) -> esquema común
MAPEO_ESQUEMA_MODERNO = {
    "domicilio": "calles",
    "rubro": "descripcion_rubro",
    "nropartidamatriz": "partida_matriz",
}


def _normalizar_nombre_columna(nombre: str) -> str:
    """Minúsculas + sin BOM/'ï»¿' (efecto de leer latin1 con BOM utf-8)."""
    return (
        str(nombre).replace("\ufeff", "").replace("ï»¿", "").strip().lower()
    )


def _fusionar_columnas_repetidas(df: pd.DataFrame) -> pd.DataFrame:
    """Une columnas que quedaron duplicadas tras normalizar nombres.

    Los exports traen el mismo campo en estilos snake_case y CamelCase
    (ej: 'solicitud' y 'Solicitud'): se combinan tomando por fila el primer
    valor no nulo del grupo (misma semántica que bfill, pero con numpy,
    porque bfill(axis=1) sobre columnas object es extremadamente lento).
    """
    repetidas = df.columns[df.columns.duplicated(keep=False)].unique()
    for nombre in repetidas:
        posiciones = [i for i, col in enumerate(df.columns) if col == nombre]
        bloque = df.iloc[:, posiciones].to_numpy(dtype=object)
        mascara = ~pd.isna(bloque)
        alguna = mascara.any(axis=1)
        indice = mascara.argmax(axis=1)
        filas = np.arange(bloque.shape[0])
        valores = np.where(alguna, bloque[filas, indice], np.nan)
        df.isetitem(posiciones[0], pd.Series(valores, index=df.index))
    return df.loc[:, ~df.columns.duplicated()]


def _corregir_mojibake(valor):
    """Repara texto leído con la codificación equivocada (Ã© -> é)."""
    if not isinstance(valor, str):
        return valor
    valor = valor.strip()
    if not any(marca in valor for marca in ("Ã", "Â", "ï»¿")):
        return valor
    try:
        return valor.encode("latin1").decode("utf-8").strip()
    except (UnicodeEncodeError, UnicodeDecodeError):
        return valor


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Armoniza esquemas, filtra filas inválidas y normaliza tipos.

    Reglas de filas (documentadas en el README):
        - se elimina toda fila sin ningún dato en las columnas de contenido
        - se eliminan duplicados exactos entre archivos anuales
          (la superposición histórica entre exports ronda el 5-17% por archivo)
    """
    df = df.copy()

    # 1) nombres de columna normalizados + columnas repetidas fusionadas
    df.columns = [_normalizar_nombre_columna(c) for c in df.columns]
    df = _fusionar_columnas_repetidas(df)

    # 2) esquema moderno -> esquema común (si el rename genera repetidas, fusionar)
    df = df.rename(columns=MAPEO_ESQUEMA_MODERNO)
    df = _fusionar_columnas_repetidas(df)

    # 3) selección estricta de columnas del esquema común
    seleccionadas = [
        c for c in COLUMNAS_CORE + COLUMNAS_EXTRA + COLUMNAS_PROCEDENCIA if c in df.columns
    ]
    df = df[seleccionadas].copy()

    # 4) texto con encoding corrupto
    for col in df.select_dtypes(include=["object", "str"]).columns:
        df[col] = df[col].map(_corregir_mojibake)

    # 5) filas sin ningún dato útil
    contenido = [c for c in COLUMNAS_CORE + COLUMNAS_EXTRA if c in df.columns]
    df = df.dropna(subset=contenido, how="all")

    # 6) duplicados exactos entre archivos anuales (sin incluir origen/anio)
    df = df.drop_duplicates(subset=contenido)

    # 7) imputaciones documentadas (sin usar medias)
    if "tipo_tramite" in df.columns:
        df["tipo_tramite"] = df["tipo_tramite"].fillna("Sin Especificar")
    if "superficie" in df.columns:
        df["superficie"] = (
            pd.to_numeric(df["superficie"], errors="coerce").fillna(0).astype(float)
        )

    # 8) tipos de datos
    if "fecha_habilitacion" in df.columns:
        df["fecha_habilitacion"] = pd.to_datetime(
            df["fecha_habilitacion"], errors="coerce"
        )
    for col in ("solicitud", "comuna"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    if "codigo_rubro" in df.columns:
        # el padrón trae ~7,5k códigos con decimales (ej: 1.4): se conservan
        df["codigo_rubro"] = pd.to_numeric(
            df["codigo_rubro"], errors="coerce"
        ).astype("Float64")

    # 9) clave catastral SMP: seccion(3)-manzana-parcela, estricta
    #    (si algún componente es inválido la clave queda NA: una SMP mal
    #    formada no sirve para cruzar con catastro)
    if {"seccion", "manzana", "parcela"} <= set(df.columns):
        s = pd.to_numeric(df["seccion"], errors="coerce")
        m = df["manzana"].astype("string").str.strip().str.upper()
        p = df["parcela"].astype("string").str.strip().str.upper()
        seccion_txt = s.map(
            lambda v: f"{int(v):03d}" if pd.notna(v) else None
        ).astype("string")
        invalida = (
            s.isna()
            | ~m.str.match(r"^\d+[A-Z]?$", na=False)
            | ~p.str.match(r"^\d+[A-Z]?$", na=False)
        )
        df["smp"] = (seccion_txt + "-" + m + "-" + p).mask(invalida)

    return df.reset_index(drop=True)
