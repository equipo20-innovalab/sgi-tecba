"""Tests del módulo de clustering e índice de oportunidad."""

import numpy as np
import pandas as pd
import pytest

from src.oportunidad import (
    PESOS_DEFECTO,
    _min_max,
    clusterizar_comunas,
    evaluar_k,
    indice_oportunidad,
    preparar_features_comuna_rubro,
    recomendar,
)


@pytest.fixture(scope="module")
def df_sintetico() -> pd.DataFrame:
    """Dataset mínimo pero representativo del padrón.

    Combina:
    * tres comunas (1, 2 y 3) — se necesitan ≥3 para que *silhouette*
      tenga sentido con k=2,
    * dos rubros (PIZZERIA y KIOSCO),
    * tres años, con la particularidad de que 2015 tiene muchos más
      registros (replica el sesgo de cobertura real del padrón).
    """
    filas = []
    # comuna 1: pizzerías en crecimiento (pocas en 2015, muchas en 2024)
    for anio, n in [(2015, 5), (2023, 20), (2024, 40)]:
        for _ in range(n):
            filas.append(
                {
                    "comuna": 1,
                    "descripcion_rubro": "PIZZERIA",
                    "anio": anio,
                    "tipo_tramite": "Habilitación",
                    "superficie": 120.0,
                }
            )
    # comuna 1: kioscos, estable y en baja
    for anio, n in [(2015, 30), (2023, 25), (2024, 20)]:
        for _ in range(n):
            filas.append(
                {
                    "comuna": 1,
                    "descripcion_rubro": "KIOSCO",
                    "anio": anio,
                    "tipo_tramite": "Habilitación",
                    "superficie": 20.0,
                }
            )
    # comuna 2: muchos kioscos (saturado), ninguna pizzería
    for anio, n in [(2015, 80), (2023, 90), (2024, 100)]:
        for _ in range(n):
            filas.append(
                {
                    "comuna": 2,
                    "descripcion_rubro": "KIOSCO",
                    "anio": anio,
                    "tipo_tramite": "Habilitación",
                    "superficie": 15.0,
                }
            )
    # comuna 3: mix equilibrado, superficie grande (perfil distinto)
    for anio, n in [(2015, 10), (2023, 12), (2024, 14)]:
        for _ in range(n):
            filas.append(
                {
                    "comuna": 3,
                    "descripcion_rubro": "PIZZERIA",
                    "anio": anio,
                    "tipo_tramite": "Habilitación",
                    "superficie": 300.0,
                }
            )
        for _ in range(n):
            filas.append(
                {
                    "comuna": 3,
                    "descripcion_rubro": "KIOSCO",
                    "anio": anio,
                    "tipo_tramite": "Habilitación",
                    "superficie": 25.0,
                }
            )
    # comunas 4 y 5: perfiles intermedios, para que silhouette tenga
    # margen (necesita 2 < k < n_comunas)
    for comuna, n_piz, n_kio, sup_piz in [(4, 8, 40, 90.0), (5, 30, 12, 180.0)]:
        for anio, escala in [(2015, 1.0), (2023, 1.1), (2024, 1.2)]:
            for _ in range(int(n_piz * escala)):
                filas.append(
                    {
                        "comuna": comuna,
                        "descripcion_rubro": "PIZZERIA",
                        "anio": anio,
                        "tipo_tramite": "Habilitación",
                        "superficie": sup_piz,
                    }
                )
            for _ in range(int(n_kio * escala)):
                filas.append(
                    {
                        "comuna": comuna,
                        "descripcion_rubro": "KIOSCO",
                        "anio": anio,
                        "tipo_tramite": "Habilitación",
                        "superficie": 20.0,
                    }
                )
    # filas inválidas que deben descartarse
    filas.append({"comuna": np.nan, "descripcion_rubro": "PIZZERIA", "anio": 2024,
                  "tipo_tramite": "Habilitación", "superficie": 100.0})
    filas.append({"comuna": 1, "descripcion_rubro": None, "anio": 2024,
                  "tipo_tramite": "Habilitación", "superficie": 100.0})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# _min_max
# --------------------------------------------------------------------------


def test_min_max_normaliza_a_un_rango():
    s = pd.Series([10.0, 20.0, 30.0])
    r = _min_max(s)
    assert r.min() == pytest.approx(0.0)
    assert r.max() == pytest.approx(1.0)


def test_min_max_constante_no_divide_por_cero():
    r = _min_max(pd.Series([5.0, 5.0, 5.0]))
    assert (r == 0.5).all()


def test_min_max_con_nan_no_propaga_nan():
    r = _min_max(pd.Series([1.0, np.nan, 3.0]))
    assert not r.isna().any()


# --------------------------------------------------------------------------
# preparar_features_comuna_rubro
# --------------------------------------------------------------------------


def test_features_genera_solo_combinaciones_validas(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    assert not tabla.index.duplicated().any()
    assert tabla.index.names == ["comuna", "rubro"]
    # las filas sin comuna ni rubro no deben aparecer
    assert "PIZZERIA" in tabla.index.get_level_values("rubro")
    assert set(tabla.index.get_level_values("comuna")) <= {1, 2, 3, 4, 5}


def test_features_respeta_min_licencias(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=50)
    assert (tabla["n_licencias"] >= 50).all()


def test_features_top_rubros_limita_el_universo(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, top_rubros=1, min_licencias=1)
    rubros = tabla.index.get_level_values("rubro").unique()
    assert len(rubros) == 1


def test_features_saturacion_es_ratio_sobre_media(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    # en la comuna 2 solo hay KIOSCO: su saturación debe ser exactamente 1
    # (es el único rubro, igual a la media de la comuna)
    assert tabla.loc[(2, "KIOSCO"), "saturacion"] == pytest.approx(1.0)


def test_features_crecimiento_detecta_el_ascenso(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    crece_pizzeria = tabla.loc[(1, "PIZZERIA"), "crecimiento"]
    cae_kiosco = tabla.loc[(1, "KIOSCO"), "crecimiento"]
    assert crece_pizzeria > 0
    assert cae_kiosco < 0
    assert crece_pizzeria > cae_kiosco


def test_features_crecimiento_usa_cuota_no_conteo_crudo():
    """Un año con más registros no debe inflar el crecimiento.

    Se duplica **solo** el año 2024 (misma mezcla de rubros): el crecimiento
    de la cuota debe quedar intacto, porque la cuota del rubro dentro del
    año no cambia aunque haya el doble de filas.
    """
    base = []
    for anio, n_piz, n_kio in [(2015, 5, 45), (2024, 20, 30)]:
        for _ in range(n_piz):
            base.append({"comuna": 1, "descripcion_rubro": "PIZZERIA",
                         "anio": anio, "tipo_tramite": "Habilitación",
                         "superficie": 100.0})
        for _ in range(n_kio):
            base.append({"comuna": 1, "descripcion_rubro": "KIOSCO",
                         "anio": anio, "tipo_tramite": "Habilitación",
                         "superficie": 20.0})
    original = pd.DataFrame(base)
    solo_2024 = original[original["anio"] == 2024]
    duplicado = pd.concat([original, solo_2024], ignore_index=True)

    t1 = preparar_features_comuna_rubro(original, min_licencias=1)
    t2 = preparar_features_comuna_rubro(duplicado, min_licencias=1)
    assert t1.loc[(1, "PIZZERIA"), "crecimiento"] == pytest.approx(
        t2.loc[(1, "PIZZERIA"), "crecimiento"]
    )


# --------------------------------------------------------------------------
# indice_oportunidad
# --------------------------------------------------------------------------


def test_indice_devuelve_valores_entre_0_y_100(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    opp = indice_oportunidad(tabla)
    assert opp["oportunidad"].between(0, 100).all()


def test_indice_agrega_componentes_interpretables(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    opp = indice_oportunidad(tabla)
    for componente in PESOS_DEFECTO:
        assert f"componente_{componente}" in opp.columns


def test_indice_respeta_pesos_custom(df_sintetico):
    """Si el peso de crecimiento es 1 y el resto 0, la nota debe reflejarlo."""
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    opp = indice_oportunidad(
        tabla, pesos={"crecimiento": 1.0, "baja_saturacion": 0.0, "subrepresentacion": 0.0}
    )
    assert opp["oportunidad"].round(1).equals(
        opp["componente_crecimiento"].round(1)
    )


def test_indice_normaliza_pesos_que_no_suman_uno(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    a = indice_oportunidad(tabla, pesos={"crecimiento": 2, "baja_saturacion": 2,
                                         "subrepresentacion": 2})
    b = indice_oportunidad(tabla, pesos={"crecimiento": 1, "baja_saturacion": 1,
                                         "subrepresentacion": 1})
    assert a["oportunidad"].equals(b["oportunidad"])


def test_indice_no_modifica_la_tabla_entrante(df_sintetico):
    tabla = preparar_features_comuna_rubro(df_sintetico, min_licencias=5)
    columnas_antes = list(tabla.columns)
    indice_oportunidad(tabla)
    assert list(tabla.columns) == columnas_antes


# --------------------------------------------------------------------------
# clusterizar_comunas / evaluar_k
# --------------------------------------------------------------------------


def test_clusterizar_devuelve_todas_las_comunas(df_sintetico):
    comunas = clusterizar_comunas(df_sintetico, k=2)
    assert set(comunas.index) == {1, 2, 3, 4, 5}
    assert "cluster" in comunas.columns


def test_clusterizar_dbscan_acepta_eps(df_sintetico):
    comunas = clusterizar_comunas(df_sintetico, metodo="dbscan", eps=2.0, min_samples=2)
    assert comunas["cluster"].notna().all()


def test_evaluar_k_devuelve_una_fila_por_k(df_sintetico):
    tabla_k = evaluar_k(df_sintetico, k_min=2, k_max=4)
    assert list(tabla_k["k"]) == [2, 3, 4]
    assert tabla_k["silhouette"].between(-1, 1).all()


# --------------------------------------------------------------------------
# recomendar
# --------------------------------------------------------------------------


def test_recomendar_filtra_por_comuna(df_sintetico):
    opp = indice_oportunidad(preparar_features_comuna_rubro(df_sintetico, min_licencias=5))
    salida = recomendar(opp, comuna=1, min_licencias=1)
    assert set(salida.index.get_level_values("comuna")) == {1}


def test_recomendar_filtra_por_rubro_parcial(df_sintetico):
    opp = indice_oportunidad(preparar_features_comuna_rubro(df_sintetico, min_licencias=5))
    salida = recomendar(opp, rubro="kios", min_licencias=1)
    assert all("KIOSCO" in r for r in salida.index.get_level_values("rubro"))


def test_recomendar_respeta_top_n(df_sintetico):
    opp = indice_oportunidad(preparar_features_comuna_rubro(df_sintetico, min_licencias=1))
    assert len(recomendar(opp, top_n=1, min_licencias=1)) == 1


def test_recomendar_ordena_descendente(df_sintetico):
    opp = indice_oportunidad(preparar_features_comuna_rubro(df_sintetico, min_licencias=1))
    salida = recomendar(opp, top_n=10, min_licencias=1)
    valores = salida["oportunidad"].tolist()
    assert valores == sorted(valores, reverse=True)


def test_recomendar_devuelve_vacio_si_no_hay_match(df_sintetico):
    opp = indice_oportunidad(preparar_features_comuna_rubro(df_sintetico, min_licencias=5))
    assert recomendar(opp, rubro="NO_EXISTE", min_licencias=1).empty
