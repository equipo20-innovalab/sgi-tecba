"""Tests del módulo de APIs del GCBA (con mocks, sin red).

Los tests no pegan a las APIs reales (sería lento e inestable): mockean
`requests.get` para validar el manejo de respuestas, timeouts y errores.
"""

from unittest.mock import MagicMock, patch

import pytest

from src import apis_gcba
from src.apis_gcba import (
    consultar_epok_por_smp,
    metros_cuadrados,
    normalizar_direccion_usig,
    buscar_datasets_badata,
    recursos_descargables,
)


@pytest.fixture(autouse=True)
def _limpiar_cache():
    """La caché en memoria del módulo no debe filtrar resultados entre tests."""
    apis_gcba._CACHE.clear()
    yield
    apis_gcba._CACHE.clear()


def _resp_json(datos, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = datos
    resp.raise_for_status.return_value = None
    return resp


# --------------------------------------------------------------------------
# metros_cuadrados (función pura)
# --------------------------------------------------------------------------


def test_metros_cuadrados_extrae_totales():
    ficha = {"superficie_total": "1088.00", "superficie_cubierta": "6735.00"}
    assert metros_cuadrados(ficha) == {"total": 1088.0, "cubierta": 6735.0}


def test_metros_cuadrados_devuelve_none_si_no_hay_ficha():
    assert metros_cuadrados(None) is None


def test_metros_cuadrados_tolera_valores_invalidos():
    assert metros_cuadrados({"superficie_total": "abc"}) == {"total": None, "cubierta": None}


# --------------------------------------------------------------------------
# EPOK
# --------------------------------------------------------------------------


@patch("src.apis_gcba.requests.get")
def test_epok_por_smp_parsea_json(mock_get):
    mock_get.return_value = _resp_json({"smp": "001-001-001A", "superficie_total": "10"})
    datos = consultar_epok_por_smp("01-001-001A")
    assert datos["smp"] == "001-001-001A"
    # la URL debe apuntar a EPOK y llevar el SMP
    assert "epok.buenosaires.gob.ar" in mock_get.call_args[0][0]
    assert mock_get.call_args[1]["params"]["smp"] == "01-001-001A"


@patch("src.apis_gcba.requests.get")
def test_epok_devuelve_none_en_timeout(mock_get):
    import requests as req
    mock_get.side_effect = req.Timeout
    assert consultar_epok_por_smp("01-001-001A") is None


def test_epok_rechaza_smp_vacio():
    assert consultar_epok_por_smp("") is None
    assert consultar_epok_por_smp(None) is None


# --------------------------------------------------------------------------
# USIG (debe degradar a None cuando hay timeout)
# --------------------------------------------------------------------------


@patch("src.apis_gcba.requests.get")
def test_usig_devuelve_none_en_timeout(mock_get):
    import requests as req
    mock_get.side_effect = req.Timeout
    assert normalizar_direccion_usig("callao y corrientes") is None


@patch("src.apis_gcba.requests.get")
def test_usig_parsea_respuesta_valida(mock_get):
    mock_get.return_value = _resp_json(
        {"direccionesNormalizadas": [{"direccion": "CALLAO AV. y CORRIENTES AV."}]}
    )
    datos = normalizar_direccion_usig("callao y corrientes")
    assert datos["direccionesNormalizadas"][0]["direccion"].startswith("CALLAO")


# --------------------------------------------------------------------------
# BA Data (CKAN)
# --------------------------------------------------------------------------


@patch("src.apis_gcba.requests.get")
def test_badata_busqueda_devuelve_resultados(mock_get):
    mock_get.return_value = _resp_json(
        {"success": True, "result": {"results": [{"name": "habilitaciones-aprobadas"}]}}
    )
    res = buscar_datasets_badata("habilitaciones")
    assert res[0]["name"] == "habilitaciones-aprobadas"


@patch("src.apis_gcba.requests.get")
def test_badata_falla_graceful(mock_get):
    import requests as req
    mock_get.side_effect = req.ConnectionError
    assert buscar_datasets_badata("x") == []


@patch("src.apis_gcba.detalle_dataset_badata")
def test_recursos_descargables_filtra_extensiones(mock_detalle):
    mock_detalle.return_value = {
        "resources": [
            {"name": "CSV", "url": "https://x/datos.csv"},
            {"name": "XLSX", "url": "https://x/datos.xlsx"},
            {"name": "PNG", "url": "https://x/mapa.png"},  # se descarta
        ]
    }
    rec = recursos_descargables("cualquiera")
    urls = {r["url"] for r in rec}
    assert "https://x/datos.csv" in urls
    assert "https://x/datos.xlsx" in urls
    assert all(not u.endswith(".png") for u in urls)
