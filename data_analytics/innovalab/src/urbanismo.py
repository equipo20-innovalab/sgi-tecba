"""Integración del Código Urbanístico con habilitaciones y fichas EPOK.

Este módulo convierte el Código Urbanístico limpio en un artefacto
consultable y auditable:

1. **Validación de SMP**: normaliza la clave Sección-Manzana-Parcela y la
   clasifica según su formato catastral (``estandar``, ``ampliado``,
   ``placeholder``, ``invalido``, ``sin_dato``).
2. **Panel por SMP**: cruza el Código Urbanístico con el padrón de
   habilitaciones y con las fichas EPOK (una fila por SMP).
3. **Reglas de compatibilidad explícitas y versionadas**: se leen desde
   ``db/seed/reglas_compatibilidad_urbanistica.json``. La primera regla que
   coincide define el estado. Las reglas describen **señales de fricción**,
   no permisos de uso ni habilitaciones.
4. **Reporte de cobertura**: cuantifica cuántos SMP de habilitaciones tienen
   fila en el Código Urbanístico y cuántos tienen ficha EPOK.

Advertencia
-----------
El resultado de compatibilidad es orientativo y no reemplaza la consulta
normativa ni la intervención de un profesional. ``compatible`` significa
"no se detectaron señales de fricción en los campos disponibles", no
"el rubro está permitido".
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_loader import PROCESSED_DIR

RAIZ = Path(__file__).resolve().parents[1]
RUTA_REGLAS = RAIZ / "db" / "seed" / "reglas_compatibilidad_urbanistica.json"
CSV_CODIGO = PROCESSED_DIR / "codigo_urbanistico_limpio.csv"
CSV_HABILITACIONES = PROCESSED_DIR / "habilitaciones_caba_clean.csv"
CSV_SMP = PROCESSED_DIR / "urbanismo_smp.csv"
JSON_COBERTURA = PROCESSED_DIR / "urbanismo_cobertura.json"

# Versión de respaldo: la fuente de verdad es el archivo de reglas.
VERSION_REGLAS = "1.0.0"

ESTADOS_COMPATIBILIDAD = (
    "compatible",
    "requiere_revision",
    "no_compatible",
    "no_verificable",
)

CLASIFICACIONES_SMP = (
    "estandar",
    "ampliado",
    "placeholder",
    "invalido",
    "sin_dato",
)

# Formatos catastrales observados en CABA. El orden importa: un placeholder
# (parcela 000) también puede cumplir el formato estándar, por eso se evalúa
# primero.
PATRON_SMP_ESTANDAR = re.compile(r"^\d{3}-\d{3}[A-Z]?-\d{3}[A-Z]?$")
PATRON_SMP_AMPLIADO = re.compile(r"^\d{3}-[0-9A-ZÑ]{3,4}-[0-9A-ZÑ]{2,5}$")
PATRON_SMP_PLACEHOLDER = re.compile(r"^\d{3}-[0-9A-ZÑ]{3,4}-0{3,4}$")

MARCADORES_NULOS = {
    "",
    "NAN",
    "NONE",
    "NULL",
    "NA",
    "N/A",
    "SIN DATO",
    "SIN_DATO",
}

# Familias de distrito especial (``dist_1_grp``). ``ninguno`` significa que la
# parcela no está alcanzada por un distrito especial; ``sin_dato`` es un valor
# explícito del dataset y se trata como dato faltante.
FAMILIAS_DISTRITO = (
    "ninguno",
    "APH",
    "U",
    "UP",
    "UF",
    "AE",
    "RUA",
    "EE",
    "ESPACIO_PUBLICO",
    "AREA_RENOVACION",
    "sin_dato",
    "otro",
)

# Flags del Código Urbanístico que se exponen como booleanos en el panel.
FLAGS_CODIGO = {
    "catalogado": "catalogado",
    "rh": "riesgo_hidrico",
    "lep": "linea_edificacion_particularizada",
    "ensanche": "ensanche",
    "apertura": "apertura",
    "anac": "cono_aeroparque",
    "ci_digital": "cinturon_digital",
    "rivolta": "altura_esquina_rivolta",
}

# Columnas del artefacto por SMP, en orden estable.
COLUMNAS_PANEL = (
    "smp",
    "smp_clasificacion",
    "smp_valido",
    "codigo_presente",
    "epok_presente",
    "n_habilitaciones",
    "n_comunas_habilitaciones",
    "primer_anio",
    "ultimo_anio",
    "familia_distrito",
    "estado_compatibilidad",
    "regla_id",
    "motivo",
    "reglas_version",
    "uso_1",
    "uso_2",
    "uso_3",
    "dist_1_grp",
    "dist_1_esp",
    "catalogado",
    "riesgo_hidrico",
    "linea_edificacion_particularizada",
    "ensanche",
    "apertura",
    "cono_aeroparque",
    "cinturon_digital",
    "altura_esquina_rivolta",
    "uni_edif_1",
    "fot_em_1",
    "fot_pl_1",
    "fot_sl_1",
    "dist_cpu_1",
    "dist_cpu_1_vigente",
    "tipo_mza",
    "barrio",
    "comuna_codigo",
    "epok_direccion",
    "epok_superficie_total",
    "epok_superficie_cubierta",
    "epok_pisos_sobre_rasante",
    "epok_unidades_funcionales",
    "epok_lng",
    "epok_lat",
    "calculado_en",
)

COLUMNAS_CODIGO_PANEL = (
    "smp",
    "uso_1",
    "uso_2",
    "uso_3",
    "dist_1_grp",
    "dist_1_esp",
    "catalogado",
    "rh",
    "lep",
    "ensanche",
    "apertura",
    "anac",
    "ci_digital",
    "rivolta",
    "uni_edif_1",
    "fot_em_1",
    "fot_pl_1",
    "fot_sl_1",
    "dist_cpu_1",
    "tipo_mza",
    "barrio",
    "comuna",
)


# ---------------------------------------------------------------------------
# SMP: normalización, clasificación y validación
# ---------------------------------------------------------------------------
def normalizar_smp(valor: Any) -> str | None:
    """Normaliza un SMP sin inventar dígitos.

    Solo recorta espacios, unifica mayúsculas y guiones tipográficos. No
    completa secciones, manzanas ni parcelas faltantes: hacerlo generaría
    cruces falsos entre fuentes.
    """
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass

    texto = str(valor).strip().upper()
    texto = texto.replace("–", "-").replace("—", "-")
    texto = re.sub(r"\s+", "", texto)
    if texto in MARCADORES_NULOS:
        return None
    return texto


def clasificar_smp(valor: Any) -> str:
    """Devuelve la clasificación catastral de un SMP.

    * ``estandar``: sección-manzana-parcela numéricos, con una letra opcional
      al final de manzana y/o parcela (p. ej. ``016-081B-001``).
    * ``ampliado``: manzana o parcela con longitudes no estándar o caracteres
      fuera de ``A-Z`` (p. ej. ``004-001-007Ñ``).
    * ``placeholder``: parcela en ceros (``...-000``/``...-0000``); no
      identifica una parcela real.
    * ``invalido``: tiene contenido pero no cumple ningún formato catastral.
    * ``sin_dato``: nulo o marcador de ausencia.
    """
    normalizado = normalizar_smp(valor)
    if normalizado is None:
        return "sin_dato"
    if PATRON_SMP_PLACEHOLDER.match(normalizado):
        return "placeholder"
    if PATRON_SMP_ESTANDAR.match(normalizado):
        return "estandar"
    if PATRON_SMP_AMPLIADO.match(normalizado):
        return "ampliado"
    return "invalido"


def clasificar_smps(serie: pd.Series) -> pd.Series:
    """Versión vectorizada de :func:`clasificar_smp`."""
    normalizada = serie.map(normalizar_smp)
    resultado = pd.Series("invalido", index=serie.index, dtype="object")

    sin_dato = normalizada.isna()
    resultado[sin_dato] = "sin_dato"

    con_dato = ~sin_dato
    placeholder = con_dato & normalizada.str.match(PATRON_SMP_PLACEHOLDER)
    estandar = con_dato & ~placeholder & normalizada.str.match(PATRON_SMP_ESTANDAR)
    ampliado = (
        con_dato
        & ~placeholder
        & ~estandar
        & normalizada.str.match(PATRON_SMP_AMPLIADO)
    )

    resultado[placeholder] = "placeholder"
    resultado[estandar] = "estandar"
    resultado[ampliado] = "ampliado"
    return resultado


def es_smp_valido(clasificacion: str) -> bool:
    """True solo para SMP que identifican una parcela catastral utilizable."""
    return clasificacion in {"estandar", "ampliado"}


def resumir_smps(serie: pd.Series) -> dict[str, Any]:
    """Resume la clasificación de una serie de SMP con ejemplos."""
    clasificacion = clasificar_smps(serie)
    conteo = clasificacion.value_counts().reindex(CLASIFICACIONES_SMP, fill_value=0)
    total = int(len(clasificacion))
    validos = int(conteo["estandar"] + conteo["ampliado"])

    normalizados = serie.map(normalizar_smp)
    ejemplos: dict[str, list[str]] = {}
    for estado in ("invalido", "placeholder"):
        mascara = clasificacion.eq(estado) & normalizados.notna()
        ejemplos[estado] = (
            sorted(set(normalizados[mascara].astype(str).tolist()))[:10]
        )

    return {
        "total": total,
        "validos": validos,
        "cobertura_valida": round(validos / total, 4) if total else 0.0,
        "clasificacion": {estado: int(conteo[estado]) for estado in CLASIFICACIONES_SMP},
        "ejemplos": ejemplos,
    }


def validar_smps(
    serie: pd.Series,
    *,
    max_placeholder: float = 0.01,
) -> dict[str, Any]:
    """Valida una serie de SMP y devuelve el resumen más los errores.

    Un ``placeholder`` no es un error fatal (el Código Urbanístico trae
    parcelas ``000``), pero se controla su proporción. Un SMP ``invalido``
    siempre es un error de contrato.
    """
    resumen = resumir_smps(serie)
    errores: list[str] = []
    if resumen["clasificacion"]["invalido"]:
        errores.append(
            f"{resumen['clasificacion']['invalido']} SMP con formato inválido "
            f"(ejemplos: {resumen['ejemplos']['invalido']})"
        )
    proporcion_placeholder = (
        resumen["clasificacion"]["placeholder"] / resumen["total"]
        if resumen["total"]
        else 0.0
    )
    if proporcion_placeholder > max_placeholder:
        errores.append(
            f"{proporcion_placeholder:.1%} de SMP son placeholder "
            f"(máximo {max_placeholder:.1%})"
        )
    return {
        **resumen,
        "max_placeholder": max_placeholder,
        "errores": errores,
        "valido": not errores,
    }


# ---------------------------------------------------------------------------
# Reglas de compatibilidad
# ---------------------------------------------------------------------------
def _sha256_archivo(ruta: Path) -> str:
    """Huella SHA-256 de un archivo."""
    digest = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def cargar_reglas(
    ruta: Path | str = RUTA_REGLAS,
    *,
    version: str | None = None,
) -> dict[str, Any]:
    """Carga y valida el archivo versionado de reglas.

    La estructura mínima es ``version``, ``fecha``, ``reglas`` (lista no
    vacía) y, por cada regla, ``id``, ``estado``, ``cuando`` y ``motivo``.
    El orden de evaluación es ascendente por ``prioridad`` y, a igual
    prioridad, el orden del archivo.
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de reglas: {ruta}")

    reglas = json.loads(ruta.read_text(encoding="utf-8"))
    for clave in ("version", "fecha", "reglas"):
        if clave not in reglas:
            raise ValueError(f"El archivo de reglas no tiene la clave '{clave}'.")

    if version is not None and str(reglas["version"]) != str(version):
        raise ValueError(
            f"Versión de reglas inesperada: {reglas['version']} (se esperaba {version})."
        )

    lista = reglas["reglas"]
    if not isinstance(lista, list) or not lista:
        raise ValueError("El archivo de reglas debe contener una lista no vacía.")

    ids: set[str] = set()
    for indice, regla in enumerate(lista, start=1):
        faltantes = {"id", "estado", "cuando", "motivo"} - set(regla)
        if faltantes:
            raise ValueError(f"Regla #{indice} incompleta: faltan {sorted(faltantes)}.")
        if regla["id"] in ids:
            raise ValueError(f"Regla duplicada: {regla['id']}.")
        ids.add(regla["id"])
        if regla["estado"] not in ESTADOS_COMPATIBILIDAD:
            raise ValueError(
                f"Estado inválido en la regla {regla['id']}: {regla['estado']}."
            )
        if not isinstance(regla["cuando"], dict):
            raise ValueError(f"'cuando' debe ser un objeto en la regla {regla['id']}.")
        if not isinstance(regla["motivo"], str) or not regla["motivo"].strip():
            raise ValueError(f"La regla {regla['id']} no tiene un motivo textual.")

    reglas["_ruta"] = str(ruta)
    reglas["_sha256"] = _sha256_archivo(ruta)
    reglas["_ordenadas"] = sorted(
        lista,
        key=lambda regla: (float(regla.get("prioridad", 9999)), lista.index(regla)),
    )
    return reglas


def _mascara_operadores(serie: pd.Series, operadores: dict[str, Any]) -> pd.Series:
    """Evalúa operadores de comparación sobre una columna."""
    mascara = pd.Series(True, index=serie.index)
    for operador, valor in operadores.items():
        if operador == "eq":
            parcial = serie.eq(valor)
        elif operador == "ne":
            parcial = serie.ne(valor)
        elif operador == "in":
            parcial = serie.isin(list(valor))
        elif operador == "not_in":
            parcial = ~serie.isin(list(valor))
        elif operador == "gte":
            parcial = pd.to_numeric(serie, errors="coerce").ge(valor)
        elif operador == "lte":
            parcial = pd.to_numeric(serie, errors="coerce").le(valor)
        elif operador == "es_nulo":
            parcial = serie.isna() if valor else serie.notna()
        else:
            raise ValueError(f"Operador de regla no soportado: {operador}")
        mascara &= parcial.fillna(False)
    return mascara.astype(bool)


def _mascara_condicion(df: pd.DataFrame, condicion: dict[str, Any]) -> pd.Series:
    """Convierte el bloque ``cuando`` de una regla en una máscara booleana.

    Las claves se combinan con AND. Una lista de valores significa "el valor
    está en la lista". Un diccionario permite operadores explícitos
    (``eq``, ``ne``, ``in``, ``not_in``, ``gte``, ``lte``, ``es_nulo``).
    """
    mascara = pd.Series(True, index=df.index)
    for campo, esperado in condicion.items():
        if campo not in df.columns:
            raise ValueError(f"La regla usa una columna inexistente: {campo}")
        serie = df[campo]

        if isinstance(esperado, dict):
            parcial = _mascara_operadores(serie, esperado)
        elif isinstance(esperado, (list, tuple, set)):
            parcial = serie.isin(list(esperado))
        elif isinstance(esperado, bool):
            parcial = serie.eq(esperado)
        else:
            parcial = serie.eq(esperado)

        mascara &= parcial.fillna(False)
    return mascara.astype(bool)


def evaluar_compatibilidad_df(
    df: pd.DataFrame,
    reglas: dict[str, Any],
) -> pd.DataFrame:
    """Aplica las reglas a un DataFrame y devuelve estado, regla y motivo.

    La primera regla que coincide (según ``prioridad``) gana. Si ninguna
    coincide, se usa ``no_verificable`` como estado conservador.
    """
    resultado = pd.DataFrame(
        {
            "estado_compatibilidad": "no_verificable",
            "regla_id": pd.NA,
            "motivo": "Ninguna regla coincidió; se aplica el estado conservador.",
        },
        index=df.index,
        dtype="object",
    )
    asignado = pd.Series(False, index=df.index)

    for regla in reglas["_ordenadas"]:
        mascara = _mascara_condicion(df, regla["cuando"]) & ~asignado
        if not mascara.any():
            continue
        resultado.loc[mascara, "estado_compatibilidad"] = regla["estado"]
        resultado.loc[mascara, "regla_id"] = regla["id"]
        resultado.loc[mascara, "motivo"] = regla["motivo"]
        asignado |= mascara

    return resultado


def evaluar_compatibilidad(fila: pd.Series | dict, reglas: dict[str, Any]) -> dict[str, Any]:
    """Evalúa una sola parcela. Útil para pruebas y para el backend."""
    df = pd.DataFrame([dict(fila)])
    resultado = evaluar_compatibilidad_df(df, reglas).iloc[0]
    return {
        "estado_compatibilidad": resultado["estado_compatibilidad"],
        "regla_id": None if pd.isna(resultado["regla_id"]) else resultado["regla_id"],
        "motivo": resultado["motivo"],
        "reglas_version": reglas["version"],
    }


def familia_distrito(valor: Any) -> str:
    """Agrupa ``dist_1_grp`` en familias estables para las reglas."""
    if valor is None:
        return "ninguno"
    try:
        if pd.isna(valor):
            return "ninguno"
    except (TypeError, ValueError):
        pass

    texto = re.sub(r"\s+", " ", str(valor).strip().upper())
    if texto in {"", "SIN DATO", "SIN_DATO"}:
        return "sin_dato"
    if texto.startswith("APH"):
        return "APH"
    if texto.startswith("UP"):
        return "UP"
    if texto == "U":
        return "U"
    if texto.startswith("UF"):
        return "UF"
    if texto.startswith("AE"):
        return "AE"
    if texto.startswith("RUA"):
        return "RUA"
    if texto.startswith("EE"):
        return "EE"
    if texto.startswith("ESPACIO PUBLICO") or texto.startswith("ESPACIO_PUBLICO"):
        return "ESPACIO_PUBLICO"
    if texto.startswith("AREA DE RENOVACION") or texto.startswith("AREA_RENOVACION"):
        return "AREA_RENOVACION"
    return "otro"


def _booleano_flag(serie: pd.Series, *, positivo_mayor_que_cero: bool = False) -> pd.Series:
    """Convierte un flag 0/1 del Código Urbanístico en booleano nullable.

    Los valores ausentes quedan como ``pd.NA``: no se interpretan como
    "sin afectación", porque eso ocultaría datos faltantes.
    """
    numerico = pd.to_numeric(serie, errors="coerce")
    resultado = pd.Series(pd.NA, index=serie.index, dtype="boolean")
    if positivo_mayor_que_cero:
        resultado[numerico.gt(0)] = True
        resultado[numerico.eq(0)] = False
    else:
        resultado[numerico.eq(1)] = True
        resultado[numerico.eq(0)] = False
    return resultado


def _preparar_codigo(codigo: pd.DataFrame) -> pd.DataFrame:
    """Normaliza y selecciona las columnas del Código Urbanístico para el panel."""
    faltantes = [columna for columna in COLUMNAS_CODIGO_PANEL if columna not in codigo.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas del Código Urbanístico: {faltantes}")

    base = codigo.loc[:, list(COLUMNAS_CODIGO_PANEL)].copy()
    base["smp"] = base["smp"].map(normalizar_smp)
    base = base.dropna(subset=["smp"]).drop_duplicates(subset=["smp"], keep="first")
    base["familia_distrito"] = base["dist_1_grp"].map(familia_distrito)

    for origen, destino in FLAGS_CODIGO.items():
        base[destino] = _booleano_flag(
            base[origen], positivo_mayor_que_cero=(origen == "rivolta")
        )

    return base.rename(columns={"comuna": "comuna_codigo"})


def _preparar_habilitaciones(habilitaciones: pd.DataFrame) -> pd.DataFrame:
    """Agrega el padrón por SMP para incorporarlo al panel."""
    base = habilitaciones.copy()
    if "smp" not in base.columns:
        raise ValueError("El padrón de habilitaciones no tiene la columna 'smp'.")
    base["smp"] = base["smp"].map(normalizar_smp)
    base = base.dropna(subset=["smp"])

    agregado = (
        base.groupby("smp", as_index=False)
        .agg(
            n_habilitaciones=("smp", "size"),
            n_comunas_habilitaciones=(
                "comuna",
                lambda serie: serie.dropna().nunique(),
            ),
            primer_anio=("anio", "min"),
            ultimo_anio=("anio", "max"),
        )
    )
    agregado["n_comunas_habilitaciones"] = agregado["n_comunas_habilitaciones"].astype(
        "Int64"
    )
    for columna in ("primer_anio", "ultimo_anio"):
        agregado[columna] = pd.to_numeric(
            agregado[columna], errors="coerce"
        ).astype("Int64")
    return agregado


def _preparar_epok(epok: pd.DataFrame | None) -> pd.DataFrame:
    """Selecciona y renombra los campos EPOK útiles para el panel."""
    columnas = {
        "smp": "smp",
        "direccion": "epok_direccion",
        "superficie_total": "epok_superficie_total",
        "superficie_cubierta": "epok_superficie_cubierta",
        "pisos_sobre_rasante": "epok_pisos_sobre_rasante",
        "unidades_funcionales": "epok_unidades_funcionales",
        "lng": "epok_lng",
        "lat": "epok_lat",
    }
    if epok is None or len(epok) == 0:
        return pd.DataFrame(columns=list(columnas.values()))

    disponibles = {origen: destino for origen, destino in columnas.items() if origen in epok.columns}
    base = epok.loc[:, list(disponibles)].rename(columns=disponibles).copy()
    base["smp"] = base["smp"].map(normalizar_smp)
    base = base.dropna(subset=["smp"]).drop_duplicates(subset=["smp"], keep="first")
    for columna in disponibles.values():
        if columna != "smp" and columna not in base.columns:
            base[columna] = pd.NA
    return base


def construir_panel_smp(
    codigo: pd.DataFrame,
    habilitaciones: pd.DataFrame,
    epok: pd.DataFrame | None = None,
    reglas: dict[str, Any] | None = None,
    *,
    calculado_en: Any | None = None,
) -> pd.DataFrame:
    """Construye el panel de una fila por SMP.

    Une el universo de SMP del Código Urbanístico, del padrón y de EPOK.
    Los SMP que solo aparecen en habilitaciones/EPOK quedan con
    ``codigo_presente=False`` y, por regla, en ``no_verificable``.
    """
    reglas = cargar_reglas() if reglas is None else reglas
    if calculado_en is None:
        calculado_en = pd.Timestamp.now(tz="UTC")
    else:
        calculado_en = pd.Timestamp(calculado_en)
        if calculado_en.tzinfo is None:
            calculado_en = calculado_en.tz_localize("UTC")

    codigo_base = _preparar_codigo(codigo)
    habilitaciones_base = _preparar_habilitaciones(habilitaciones)
    epok_base = _preparar_epok(epok)

    smps = pd.Index(
        sorted(
            set(codigo_base["smp"])
            | set(habilitaciones_base["smp"])
            | set(epok_base["smp"].dropna())
        ),
        dtype="object",
    )
    panel = pd.DataFrame({"smp": smps})
    panel["smp_clasificacion"] = clasificar_smps(panel["smp"])
    panel["smp_valido"] = panel["smp_clasificacion"].map(es_smp_valido).astype(bool)

    panel = panel.merge(codigo_base, on="smp", how="left")
    panel = panel.merge(habilitaciones_base, on="smp", how="left")
    panel = panel.merge(epok_base, on="smp", how="left")

    panel["codigo_presente"] = panel["familia_distrito"].notna()
    panel["epok_presente"] = panel["epok_direccion"].notna() | panel[
        "epok_superficie_total"
    ].notna()
    panel["n_habilitaciones"] = (
        pd.to_numeric(panel["n_habilitaciones"], errors="coerce").fillna(0).astype(int)
    )
    panel["n_comunas_habilitaciones"] = pd.to_numeric(
        panel["n_comunas_habilitaciones"], errors="coerce"
    ).astype("Int64")
    panel["familia_distrito"] = panel["familia_distrito"].fillna("ninguno")
    panel["dist_cpu_1_vigente"] = False
    panel["reglas_version"] = str(reglas["version"])
    panel["calculado_en"] = calculado_en

    evaluacion = evaluar_compatibilidad_df(panel, reglas)
    panel = pd.concat([panel, evaluacion], axis=1)

    for columna in COLUMNAS_PANEL:
        if columna not in panel.columns:
            panel[columna] = pd.NA

    panel = panel.loc[:, list(COLUMNAS_PANEL)]
    panel = panel.sort_values("smp", ignore_index=True)
    return panel


# ---------------------------------------------------------------------------
# Cobertura
# ---------------------------------------------------------------------------
def _conteo(serie: pd.Series) -> dict[str, int]:
    """Conteo ordenado y serializable, incluyendo nulos como 'sin_dato'."""
    valores = serie.astype("object").where(serie.notna(), "sin_dato")
    return {
        str(clave): int(valor)
        for clave, valor in valores.value_counts(dropna=False).sort_index().items()
    }


def _flags_resumen(panel: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Cuenta True/False/sin_dato de cada flag del panel."""
    resumen: dict[str, dict[str, int]] = {}
    for destino in FLAGS_CODIGO.values():
        serie = panel[destino]
        resumen[destino] = {
            "si": int(serie.eq(True).sum()),
            "no": int(serie.eq(False).sum()),
            "sin_dato": int(serie.isna().sum()),
        }
    return resumen


def generar_cobertura(
    codigo: pd.DataFrame,
    habilitaciones: pd.DataFrame,
    panel: pd.DataFrame,
    reglas: dict[str, Any],
    *,
    fuentes: dict[str, Any] | None = None,
    parametros: dict[str, Any] | None = None,
    generado_en: Any | None = None,
) -> dict[str, Any]:
    """Calcula el reporte de cobertura del cruce CU + habilitaciones + EPOK."""
    if generado_en is None:
        generado_en = datetime.now(timezone.utc)
    elif isinstance(generado_en, (pd.Timestamp, datetime)):
        generado_en = pd.Timestamp(generado_en).to_pydatetime()

    codigo_smp = codigo["smp"].map(normalizar_smp)
    hab_smp = (
        habilitaciones["smp"].map(normalizar_smp)
        if "smp" in habilitaciones.columns
        else pd.Series(pd.NA, index=habilitaciones.index, dtype="object")
    )

    set_codigo = set(codigo_smp.dropna())
    set_hab = set(hab_smp.dropna())
    set_interseccion = set_codigo & set_hab
    set_epok = set(panel.loc[panel["epok_presente"], "smp"])

    n_hab = int(len(habilitaciones))
    n_hab_con_smp = int(hab_smp.notna().sum())
    n_hab_con_codigo = int(hab_smp.isin(set_codigo).sum())
    n_hab_con_epok = int(hab_smp.isin(set_epok).sum())
    n_hab_con_codigo_y_epok = int(
        (hab_smp.isin(set_codigo) & hab_smp.isin(set_epok)).sum()
    )

    estados_hab = hab_smp.map(
        panel.set_index("smp")["estado_compatibilidad"].to_dict()
    ).fillna("no_verificable")
    estados_hab[hab_smp.isna()] = "sin_smp"

    resumen = {
        "smp_codigo": int(len(set_codigo)),
        "smp_habilitaciones": int(len(set_hab)),
        "smp_epok": int(len(set_epok)),
        "smp_interseccion": int(len(set_interseccion)),
        "smp_codigo_y_epok": int(len(set_codigo & set_epok)),
        "cobertura_habilitaciones_por_smp": (
            round(len(set_interseccion) / len(set_hab), 4) if set_hab else 0.0
        ),
        "cobertura_codigo_usado_por_habilitaciones": (
            round(len(set_interseccion) / len(set_codigo), 4) if set_codigo else 0.0
        ),
        "habilitaciones": n_hab,
        "habilitaciones_con_smp": n_hab_con_smp,
        "habilitaciones_con_codigo": n_hab_con_codigo,
        "habilitaciones_con_epok": n_hab_con_epok,
        "habilitaciones_con_codigo_y_epok": n_hab_con_codigo_y_epok,
        "pct_habilitaciones_con_smp": (
            round(n_hab_con_smp / n_hab, 4) if n_hab else 0.0
        ),
        "pct_habilitaciones_con_codigo": (
            round(n_hab_con_codigo / n_hab, 4) if n_hab else 0.0
        ),
        "pct_habilitaciones_con_epok": (
            round(n_hab_con_epok / n_hab, 4) if n_hab else 0.0
        ),
        "pct_habilitaciones_con_codigo_y_epok": (
            round(n_hab_con_codigo_y_epok / n_hab, 4) if n_hab else 0.0
        ),
    }

    return {
        "generado_en": pd.Timestamp(generado_en).isoformat(),
        "reglas": {
            "version": str(reglas["version"]),
            "fecha": str(reglas["fecha"]),
            "ruta": reglas.get("_ruta"),
            "sha256": reglas.get("_sha256"),
            "advertencia": reglas.get("advertencia"),
        },
        "fuentes": fuentes or {},
        "parametros": parametros or {},
        "resumen": resumen,
        "clasificacion_smp": resumir_smps(codigo["smp"]),
        "clasificacion_habilitaciones": resumir_smps(
            habilitaciones["smp"] if "smp" in habilitaciones.columns else pd.Series(dtype="object")
        ),
        "estados_smp": _conteo(panel["estado_compatibilidad"]),
        "estados_habilitaciones": _conteo(estados_hab),
        "familias_distrito": _conteo(panel["familia_distrito"]),
        "flags": _flags_resumen(panel),
        "limitaciones": [
            "La compatibilidad es orientativa y no constituye permiso de uso ni habilitación.",
            "El Código Urbanístico no publica un campo de 'uso permitido' por rubro; "
            "uso_1/2/3 son 'mixtura de uso' y no deben interpretarse como autorización.",
            "dist_cpu_1 pertenece al Código de Planeamiento Urbano derogado; "
            "se conserva como contexto y se marca dist_cpu_1_vigente=false.",
            "Un SMP placeholder (parcela 000) no identifica una parcela real.",
            "La ausencia de ficha EPOK no implica que la parcela no exista.",
        ],
    }


def escribir_artefactos_urbanismo(
    panel: pd.DataFrame,
    cobertura: dict[str, Any],
    *,
    ruta_csv: Path | str = CSV_SMP,
    ruta_json: Path | str = JSON_COBERTURA,
) -> dict[str, Any]:
    """Escribe el panel CSV y el reporte JSON de forma atómica.

    El JSON incluye el SHA-256 del CSV recién escrito para poder verificar
    que ambos artefactos corresponden a la misma corrida.
    """
    ruta_csv = Path(ruta_csv)
    ruta_json = Path(ruta_json)
    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    ruta_json.parent.mkdir(parents=True, exist_ok=True)

    temporal_csv = ruta_csv.with_name(f".{ruta_csv.name}.tmp")
    try:
        panel.to_csv(temporal_csv, index=False, encoding="utf-8")
        temporal_csv.replace(ruta_csv)
    finally:
        temporal_csv.unlink(missing_ok=True)

    cobertura = {
        **cobertura,
        "artefacto": {
            "csv": str(ruta_csv),
            "sha256": _sha256_archivo(ruta_csv),
            "filas": int(len(panel)),
            "columnas": list(panel.columns),
        },
    }

    temporal_json = ruta_json.with_name(f".{ruta_json.name}.tmp")
    try:
        temporal_json.write_text(
            json.dumps(cobertura, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )
        temporal_json.replace(ruta_json)
    finally:
        temporal_json.unlink(missing_ok=True)

    return cobertura


def metadatos_urbanismo(
    panel: pd.DataFrame,
    cobertura: dict[str, Any],
) -> dict[str, Any]:
    """Resumen legible para logs y para la tabla de cobertura."""
    resumen = cobertura["resumen"]
    return {
        "reglas_version": cobertura["reglas"]["version"],
        "reglas_sha256": cobertura["reglas"].get("sha256"),
        "n_smp": int(len(panel)),
        "n_smp_codigo": resumen["smp_codigo"],
        "n_smp_habilitaciones": resumen["smp_habilitaciones"],
        "n_smp_interseccion": resumen["smp_interseccion"],
        "cobertura_habilitaciones_por_smp": resumen["cobertura_habilitaciones_por_smp"],
        "estados_smp": cobertura["estados_smp"],
        "estados_habilitaciones": cobertura["estados_habilitaciones"],
    }


def validar_reglas_version(reglas: dict[str, Any], esperada: str = VERSION_REGLAS) -> None:
    """Falla si el archivo de reglas no declara la versión esperada."""
    if str(reglas.get("version")) != str(esperada):
        raise ValueError(
            f"Versión de reglas {reglas.get('version')} distinta de la esperada {esperada}."
        )


def fecha_iso(valor: date | datetime | pd.Timestamp) -> str:
    """Normaliza fechas para los metadatos JSON."""
    return pd.Timestamp(valor).isoformat()
