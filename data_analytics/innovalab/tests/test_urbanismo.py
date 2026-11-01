"""Tests de la integración Código Urbanístico + habilitaciones + EPOK."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src import urbanismo
from src.data_validation import validar_codigo_urbanistico
from src.urbanismo import (
    COLUMNAS_PANEL,
    cargar_reglas,
    clasificar_smp,
    clasificar_smps,
    construir_panel_smp,
    escribir_artefactos_urbanismo,
    evaluar_compatibilidad,
    evaluar_compatibilidad_df,
    familia_distrito,
    generar_cobertura,
    normalizar_smp,
    resumir_smps,
    validar_smps,
)

COLUMNAS_CODIGO = [
    "smp", "uso_1", "uso_2", "uso_3", "dist_1_grp", "dist_1_esp",
    "catalogado", "rh", "lep", "ensanche", "apertura", "anac", "ci_digital",
    "rivolta", "uni_edif_1", "fot_em_1", "fot_pl_1", "fot_sl_1",
    "dist_cpu_1", "tipo_mza", "barrio", "comuna",
]


def _fila_codigo(**cambios) -> dict:
    fila = {columna: pd.NA for columna in COLUMNAS_CODIGO}
    fila.update(
        {
            "uso_1": 2,
            "uso_2": 0,
            "uso_3": 0,
            "catalogado": 0,
            "rh": 0,
            "lep": 0,
            "ensanche": 0,
            "apertura": 0,
            "anac": 0,
            "ci_digital": 0,
            "rivolta": 0,
            "uni_edif_1": 18.0,
            "fot_em_1": 3.0,
            "fot_pl_1": 3.0,
            "fot_sl_1": 3.0,
            "dist_cpu_1": "R2b II",
            "tipo_mza": "TIPICA",
            "barrio": "CENTRO",
            "comuna": 1,
        }
    )
    fila.update(cambios)
    return fila


@pytest.fixture(scope="module")
def reglas() -> dict:
    return cargar_reglas()


@pytest.fixture(scope="module")
def codigo() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _fila_codigo(smp="001-001-001", barrio="A"),
            _fila_codigo(
                smp="001-002-001", dist_1_grp="APH", dist_1_esp="APH 1",
                catalogado=1, barrio="B",
            ),
            _fila_codigo(smp="001-003-001", apertura=1, comuna=2, barrio="C"),
            _fila_codigo(smp="001-004-000", uso_1=1, comuna=2, barrio="D"),
            _fila_codigo(
                smp="001-006-001", dist_1_grp="Espacio Publico", comuna=3,
                barrio="E",
            ),
            _fila_codigo(smp="001-007-001", rh=1, comuna=3, barrio="F"),
            _fila_codigo(smp="001-008-001", barrio="G"),
        ]
    )


@pytest.fixture(scope="module")
def habilitaciones() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"smp": "001-001-001", "comuna": 1, "anio": 2020},
            {"smp": "001-001-001", "comuna": 1, "anio": 2021},
            {"smp": "001-002-001", "comuna": 1, "anio": 2022},
            {"smp": "001-003-001", "comuna": 2, "anio": 2023},
            {"smp": "002-001-001", "comuna": 4, "anio": 2024},
            {"smp": "001-004-000", "comuna": 2, "anio": 2020},
            {"smp": "001-1-1", "comuna": 5, "anio": 2024},
            {"smp": None, "comuna": 6, "anio": 2024},
        ]
    )


@pytest.fixture(scope="module")
def epok() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "smp": "001-001-001", "direccion": "CALLE 1",
                "superficie_total": 100.0, "superficie_cubierta": 90.0,
                "pisos_sobre_rasante": 2, "unidades_funcionales": 1,
                "lng": -58.4, "lat": -34.6,
            },
            {
                "smp": "001-003-001", "direccion": "CALLE 3",
                "superficie_total": 200.0, "superficie_cubierta": 180.0,
                "pisos_sobre_rasante": 3, "unidades_funcionales": 2,
                "lng": -58.41, "lat": -34.61,
            },
            {
                "smp": "002-001-001", "direccion": "CALLE 2",
                "superficie_total": 50.0, "superficie_cubierta": 45.0,
                "pisos_sobre_rasante": 1, "unidades_funcionales": 1,
                "lng": -58.42, "lat": -34.62,
            },
        ]
    )


@pytest.fixture(scope="module")
def panel(codigo, habilitaciones, epok, reglas) -> pd.DataFrame:
    return construir_panel_smp(
        codigo,
        habilitaciones,
        epok,
        reglas,
        calculado_en="2026-10-28T00:00:00Z",
    )


# --- SMP -------------------------------------------------------------------
def test_normalizar_smp_no_inventa_digitos():
    assert normalizar_smp(" 001-001-001 ") == "001-001-001"
    assert normalizar_smp("001–001–001") == "001-001-001"
    assert normalizar_smp("001 001 001") == "001001001"
    assert normalizar_smp(None) is None
    assert normalizar_smp("") is None
    assert normalizar_smp("nan") is None
    assert normalizar_smp("001-1-1") == "001-1-1"


def test_clasificar_smp_por_formato():
    assert clasificar_smp("001-001-001") == "estandar"
    assert clasificar_smp("016-081B-001") == "estandar"
    assert clasificar_smp("004-001-007Ñ") == "ampliado"
    assert clasificar_smp("001-001-000") == "placeholder"
    assert clasificar_smp("001-1-1") == "invalido"
    assert clasificar_smp(None) == "sin_dato"


def test_clasificar_smps_vectorizado_respeta_placeholder():
    serie = pd.Series(
        ["001-001-001", "001-001-000", "004-001-007Ñ", "001-1-1", None]
    )
    clasificacion = clasificar_smps(serie)
    assert clasificacion.tolist() == [
        "estandar", "placeholder", "ampliado", "invalido", "sin_dato"
    ]


def test_resumir_y_validar_smps():
    serie = pd.Series(["001-001-001", "001-001-000", "001-1-1", None])
    resumen = resumir_smps(serie)
    assert resumen["total"] == 4
    assert resumen["validos"] == 1
    assert resumen["clasificacion"] == {
        "estandar": 1,
        "ampliado": 0,
        "placeholder": 1,
        "invalido": 1,
        "sin_dato": 1,
    }
    assert "001-1-1" in resumen["ejemplos"]["invalido"]

    validacion = validar_smps(serie, max_placeholder=0.5)
    assert not validacion["valido"]
    assert any("formato inválido" in error for error in validacion["errores"])

    solo_validos = validar_smps(pd.Series(["001-001-001", "016-081B-001"]))
    assert solo_validos["valido"]


def test_familia_distrito_agrupa_variantes():
    assert familia_distrito(None) == "ninguno"
    assert familia_distrito("Sin dato") == "sin_dato"
    assert familia_distrito("APH 1") == "APH"
    assert familia_distrito("UP/APH 2") == "UP"
    assert familia_distrito("U") == "U"
    assert familia_distrito("Espacio Publico") == "ESPACIO_PUBLICO"
    assert familia_distrito("Area de Renovacion") == "AREA_RENOVACION"
    assert familia_distrito("Distrito raro") == "otro"


# --- reglas ----------------------------------------------------------------
def test_cargar_reglas_versionadas(reglas):
    assert reglas["version"] == "1.0.0"
    assert reglas["fecha"] == "2026-10-28"
    assert len(reglas["reglas"]) >= 10
    assert "NO constituye permiso" in reglas["advertencia"]
    assert reglas["_sha256"]
    prioridades = [regla["prioridad"] for regla in reglas["_ordenadas"]]
    assert prioridades == sorted(prioridades)


def test_cargar_reglas_rechaza_version_inesperada(tmp_path):
    with pytest.raises(ValueError, match="Versión de reglas inesperada"):
        cargar_reglas(urbanismo.RUTA_REGLAS, version="9.9.9")


def test_cargar_reglas_rechaza_estado_invalido(tmp_path):
    ruta = tmp_path / "reglas.json"
    ruta.write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "fecha": "2026-10-28",
                "reglas": [
                    {
                        "id": "X",
                        "estado": "permitido",
                        "cuando": {},
                        "motivo": "x",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Estado inválido"):
        cargar_reglas(ruta)


def test_precedencia_de_reglas(reglas):
    fila = {
        "smp_clasificacion": "estandar",
        "codigo_presente": True,
        "familia_distrito": "APH",
        "catalogado": True,
        "apertura": True,
        "ensanche": False,
        "riesgo_hidrico": False,
        "linea_edificacion_particularizada": False,
        "cono_aeroparque": False,
    }
    # apertura (31) gana sobre patrimonio (40) y distrito especial (50).
    assert evaluar_compatibilidad(fila, reglas)["regla_id"] == "AFECTACION_APERTURA"

    fila["apertura"] = False
    assert evaluar_compatibilidad(fila, reglas)["regla_id"] == "PATRIMONIO_CATALOGADO"

    fila["catalogado"] = False
    assert evaluar_compatibilidad(fila, reglas)["regla_id"] == "DISTRITO_ESPECIAL"


def test_evaluar_compatibilidad_df_sin_regla_coincidente(reglas):
    df = pd.DataFrame(
        [
            {
                "smp_clasificacion": "estandar",
                "codigo_presente": True,
                "familia_distrito": "ninguno",
                "catalogado": False,
                "apertura": False,
                "ensanche": False,
                "riesgo_hidrico": False,
                "linea_edificacion_particularizada": False,
                "cono_aeroparque": False,
            }
        ]
    )
    resultado = evaluar_compatibilidad_df(df, reglas)
    assert resultado.iloc[0]["estado_compatibilidad"] == "compatible"
    assert resultado.iloc[0]["regla_id"] == "SIN_SENALES_DE_FRICCION"


# --- panel -----------------------------------------------------------------
def test_panel_une_codigo_habilitaciones_y_epok(panel):
    assert list(panel.columns) == list(COLUMNAS_PANEL)
    assert panel["smp"].is_unique
    assert len(panel) == 9

    fila = panel.set_index("smp").loc["001-001-001"]
    assert fila["smp_clasificacion"] == "estandar"
    assert bool(fila["codigo_presente"])
    assert bool(fila["epok_presente"])
    assert fila["n_habilitaciones"] == 2
    assert fila["n_comunas_habilitaciones"] == 1
    assert fila["primer_anio"] == 2020
    assert fila["ultimo_anio"] == 2021
    assert fila["epok_direccion"] == "CALLE 1"
    assert fila["estado_compatibilidad"] == "compatible"


def test_panel_marca_estados_de_friccion(panel):
    por_smp = panel.set_index("smp")["estado_compatibilidad"].to_dict()
    assert por_smp["001-001-001"] == "compatible"
    assert por_smp["001-002-001"] == "requiere_revision"  # catalogado
    assert por_smp["001-003-001"] == "no_compatible"       # apertura
    assert por_smp["001-004-000"] == "no_verificable"      # placeholder
    assert por_smp["001-006-001"] == "no_compatible"       # espacio público
    assert por_smp["001-007-001"] == "requiere_revision"   # riesgo hídrico
    assert por_smp["001-008-001"] == "compatible"
    assert por_smp["002-001-001"] == "no_verificable"      # CU ausente
    assert por_smp["001-1-1"] == "no_verificable"          # inválido


def test_panel_marca_cpu_derogado(panel):
    assert panel["dist_cpu_1_vigente"].eq(False).all()
    assert set(panel["dist_cpu_1_vigente"].unique()) == {False}


# --- cobertura -------------------------------------------------------------
def test_cobertura_metricas(codigo, habilitaciones, panel, reglas, epok):
    cobertura = generar_cobertura(
        codigo,
        habilitaciones,
        panel,
        reglas,
        fuentes={"codigo_urbanistico": {"ruta": "codigo.csv"}},
        generado_en="2026-10-28T00:00:00Z",
    )
    resumen = cobertura["resumen"]
    assert resumen["smp_codigo"] == 7
    assert resumen["smp_habilitaciones"] == 6
    assert resumen["smp_interseccion"] == 4
    assert resumen["cobertura_habilitaciones_por_smp"] == pytest.approx(4 / 6, abs=1e-4)
    assert resumen["cobertura_codigo_usado_por_habilitaciones"] == pytest.approx(4 / 7, abs=1e-4)
    assert resumen["habilitaciones"] == 8
    assert resumen["habilitaciones_con_smp"] == 7
    assert resumen["habilitaciones_con_codigo"] == 5
    assert resumen["habilitaciones_con_epok"] == 4
    assert resumen["habilitaciones_con_codigo_y_epok"] == 3
    assert resumen["pct_habilitaciones_con_codigo"] == pytest.approx(5 / 8, abs=1e-4)

    assert cobertura["estados_smp"] == {
        "compatible": 2,
        "no_compatible": 2,
        "no_verificable": 3,
        "requiere_revision": 2,
    }
    assert cobertura["estados_habilitaciones"] == {
        "compatible": 2,
        "no_compatible": 1,
        "no_verificable": 3,
        "requiere_revision": 1,
        "sin_smp": 1,
    }
    assert cobertura["clasificacion_smp"]["clasificacion"]["placeholder"] == 1
    assert cobertura["clasificacion_habilitaciones"]["clasificacion"]["invalido"] == 1
    assert cobertura["reglas"]["version"] == "1.0.0"
    assert cobertura["reglas"]["sha256"]
    assert cobertura["flags"]["apertura"]["si"] == 1
    assert any("no constituye permiso" in texto.lower() for texto in cobertura["limitaciones"])


def test_cobertura_sin_epok(codigo, habilitaciones, panel, reglas):
    cobertura = generar_cobertura(codigo, habilitaciones, panel, reglas)
    assert cobertura["resumen"]["smp_epok"] == 3
    assert cobertura["fuentes"] == {}


# --- artefactos ------------------------------------------------------------
def test_escribir_artefactos_es_atomico_y_hashea(panel, codigo, habilitaciones, reglas, tmp_path):
    cobertura = generar_cobertura(
        codigo, habilitaciones, panel, reglas, generado_en="2026-10-28T00:00:00Z"
    )
    ruta_csv = tmp_path / "urbanismo_smp.csv"
    ruta_json = tmp_path / "urbanismo_cobertura.json"

    resultado = escribir_artefactos_urbanismo(
        panel, cobertura, ruta_csv=ruta_csv, ruta_json=ruta_json
    )
    assert ruta_csv.is_file()
    assert ruta_json.is_file()

    leido = pd.read_csv(ruta_csv)
    assert len(leido) == len(panel)
    assert list(leido.columns) == list(COLUMNAS_PANEL)

    meta = json.loads(ruta_json.read_text(encoding="utf-8"))
    assert meta["artefacto"]["filas"] == len(panel)
    assert meta["artefacto"]["sha256"] == resultado["artefacto"]["sha256"]
    assert len(meta["artefacto"]["sha256"]) == 64


# --- validación de archivo -------------------------------------------------
def test_validar_codigo_urbanistico_acepta_placeholder(tmp_path):
    ruta = tmp_path / "codigo.csv"
    ruta.write_text(
        "smp,uso_1\n001-001-001,1\n001-001-000,1\n", encoding="utf-8"
    )
    assert validar_codigo_urbanistico(ruta, max_placeholder=0.5) == 2


def test_validar_codigo_urbanistico_rechaza_invalido(tmp_path):
    ruta = tmp_path / "codigo.csv"
    ruta.write_text("smp,uso_1\n001-1-1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="formato inválido"):
        validar_codigo_urbanistico(ruta)


def test_validar_codigo_urbanistico_rechaza_exceso_placeholder(tmp_path):
    ruta = tmp_path / "codigo.csv"
    ruta.write_text(
        "smp,uso_1\n001-001-001,1\n001-002-000,1\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="placeholder"):
        validar_codigo_urbanistico(ruta, max_placeholder=0.1)
