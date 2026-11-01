"""Validaciones de contrato para publicar el padrón de habilitaciones."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from src.urbanismo import clasificar_smp, normalizar_smp

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
    "smp_fuente",
    "fecha_fuente",
    "comuna_fuente",
}

EXPECTATIONS_POR_COLUMNA: dict[str, float | None] = {
    "solicitud": None,
    "tipo_tramite": None,
    "tipo_expediente": None,
    "subtipo_expediente": None,
    "fecha_habilitacion": 0.70,
    "numero_expediente": None,
    "codigo_rubro": 0.65,
    "descripcion_rubro": None,
    "superficie": None,
    "seccion": None,
    "manzana": None,
    "parcela": None,
    "calles": 0.95,
    "comuna": 0.90,
    "razon_social": 0.10,
    "partida_matriz": None,
    "origen": 1.0,
    "anio": 1.0,
    "smp": 0.75,
    "smp_fuente": 1.0,
    "fecha_fuente": 1.0,
    "comuna_fuente": 1.0,
}

FUENTES_VALIDAS = {
    "comuna_fuente": {"archivo", "catastro", "callejero", "callejero_fuzzy", "sin_dato"},
    "smp_fuente": {"seccion_manzana_parcela", "sin_dato"},
    "fecha_fuente": {"archivo", "sin_dato"},
}

MIN_FILAS = 200_000


def _mascara_con_dato(df: pd.DataFrame, columna: str) -> pd.Series:
    if columna not in df.columns:
        return pd.Series(False, index=df.index)
    presente = df[columna].notna()
    if columna == "superficie":
        presente &= pd.to_numeric(df[columna], errors="coerce").gt(0)
    elif columna == "tipo_tramite":
        valores = df[columna].astype("string").str.strip().str.casefold()
        presente &= ~valores.isin({"", "sin especificar", "sin dato"})
    return presente


def validar_habilitaciones(df: pd.DataFrame) -> None:
    """Lanza ValueError si el padrón no cumple el contrato de publicación."""
    errores = []
    faltantes = COLUMNAS_ESPERADAS - set(df.columns)
    if faltantes:
        errores.append(f"faltan columnas: {sorted(faltantes)}")
        raise ValueError("El padrón no cumple el contrato: " + "; ".join(errores))

    if len(df) < MIN_FILAS:
        errores.append(f"solo {len(df):,} filas (mínimo {MIN_FILAS:,})")

    comuna = pd.to_numeric(df["comuna"], errors="coerce")
    fuera_de_rango = comuna.notna() & ~comuna.between(1, 15)
    if fuera_de_rango.any():
        errores.append(f"{int(fuera_de_rango.sum())} comunas fuera del rango 1..15")
    if comuna.notna().mean() < 0.90:
        errores.append(f"cobertura de comuna inferior al 90% ({comuna.notna().mean():.1%})")

    for columna, fuentes_validas in FUENTES_VALIDAS.items():
        fuentes = set(df[columna].dropna().unique())
        invalidas = fuentes - fuentes_validas
        if not fuentes or invalidas or df[columna].isna().any():
            errores.append(f"valores inválidos en {columna}: {sorted(invalidas)}")

    anio = pd.to_numeric(df["anio"], errors="coerce")
    if anio.isna().any() or not anio.between(2015, 2026).all():
        errores.append("anio debe estar completo y dentro del rango 2015..2026")

    superficie = pd.to_numeric(df["superficie"], errors="coerce")
    if (superficie < 0).any():
        errores.append(f"{int((superficie < 0).sum())} superficies negativas")

    for columna, cobertura_minima in EXPECTATIONS_POR_COLUMNA.items():
        cobertura = df[columna].notna().mean()
        if cobertura_minima is not None and cobertura < cobertura_minima:
            errores.append(
                f"{columna}: cobertura {cobertura:.1%} "
                f"(mínimo {cobertura_minima:.1%})"
            )

    duplicadas = int(df.duplicated().sum())
    if duplicadas:
        errores.append(f"{duplicadas:,} filas duplicadas completas")

    fechas_validas = pd.to_datetime(df["fecha_habilitacion"], errors="coerce").notna().mean()
    if fechas_validas < 0.70:
        errores.append(f"solo {fechas_validas:.1%} de fechas válidas (mínimo 70%)")

    if not df["origen"].astype("string").str.endswith(".csv", na=False).all():
        errores.append("origen debe contener nombres de archivos CSV")
    if df["origen"].nunique() < 7:
        errores.append("se requieren al menos 7 archivos fuente")

    if errores:
        raise ValueError("El padrón no cumple el contrato: " + "; ".join(errores))


def generar_reporte_calidad(df: pd.DataFrame) -> dict:
    """Devuelve cobertura y estado contra la expectation de cada columna."""
    columnas = {}
    for columna, cobertura_minima in EXPECTATIONS_POR_COLUMNA.items():
        presentes = int(_mascara_con_dato(df, columna).sum())
        cobertura = presentes / len(df) if len(df) else 0.0
        columnas[columna] = {
            "presentes": presentes,
            "sin_dato": len(df) - presentes,
            "cobertura": round(cobertura, 4),
            "expectativa_minima": cobertura_minima,
            "cumple": (
                cobertura >= cobertura_minima
                if cobertura_minima is not None
                else None
            ),
        }

    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_registros": len(df),
        "columnas": columnas,
        "fuentes": {
            columna: {
                str(fuente): int(cantidad)
                for fuente, cantidad in df[columna].value_counts(dropna=False).items()
            }
            if columna in df.columns
            else {"columna_ausente": len(df)}
            for columna in FUENTES_VALIDAS
        },
    }


def guardar_reporte_calidad(df: pd.DataFrame, destino: Path) -> dict:
    """Guarda el reporte JSON de forma atómica y devuelve su contenido."""
    reporte = generar_reporte_calidad(df)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(f".{destino.name}.tmp")
    try:
        temporal.write_text(
            json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporal.replace(destino)
    finally:
        temporal.unlink(missing_ok=True)
    return reporte


def validar_codigo_urbanistico(ruta: Path, max_placeholder: float = 0.01) -> int:
    """Verifica que el CSV catastral tenga una clave SMP completa, única y válida.

    Reglas:
    * el archivo debe tener la columna ``smp``;
    * no se admiten SMP vacías;
    * no se admiten SMP duplicadas;
    * no se admiten SMP con formato inválido;
    * los ``placeholder`` (parcela ``000``) se toleran hasta ``max_placeholder``.

    Devuelve la cantidad de SMP únicas.
    """
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el CSV del Código Urbanístico: {ruta}")

    claves: set[str] = set()
    invalidos: list[str] = []
    placeholders = 0
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if not lector.fieldnames or "smp" not in lector.fieldnames:
            raise ValueError("El CSV del Código Urbanístico debe incluir una columna 'smp'.")
        for numero_fila, fila in enumerate(lector, start=2):
            smp = normalizar_smp(fila.get("smp"))
            if not smp:
                raise ValueError(
                    f"SMP vacía en el CSV del Código Urbanístico, fila {numero_fila}."
                )
            if smp in claves:
                raise ValueError(f"SMP duplicada en el CSV del Código Urbanístico: {smp}")
            claves.add(smp)

            clasificacion = clasificar_smp(smp)
            if clasificacion == "invalido":
                invalidos.append(smp)
            elif clasificacion == "placeholder":
                placeholders += 1

    if not claves:
        raise ValueError("El CSV del Código Urbanístico no contiene registros.")
    if invalidos:
        ejemplos = ", ".join(sorted(set(invalidos))[:10])
        raise ValueError(
            f"{len(invalidos)} SMP con formato inválido en el Código Urbanístico "
            f"(ejemplos: {ejemplos})."
        )

    proporcion_placeholder = placeholders / len(claves)
    if proporcion_placeholder > max_placeholder:
        raise ValueError(
            f"{proporcion_placeholder:.1%} de SMP son placeholder de parcela 000 "
            f"(máximo permitido {max_placeholder:.1%})."
        )
    return len(claves)
