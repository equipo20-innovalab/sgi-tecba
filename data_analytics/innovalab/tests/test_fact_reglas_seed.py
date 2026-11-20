"""Tests de la matriz rubro ↔ requisito generada desde el padrón de habilitaciones."""

from __future__ import annotations

import csv
from decimal import Decimal

import pytest

from scripts.generar_fact_reglas_habilitacion import (
    COLUMNAS,
    CSV_CU,
    SALIDA,
    detectar_tags,
    generar_reglas,
    leer_requisitos,
    leer_rubros,
)
from src.export_postgres import COLUMNAS_FACT, UPSERT_FACT_SQL, leer_fact_reglas


def _filas() -> list[dict[str, str]]:
    with SALIDA.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_columnas_coinciden_con_el_ddl() -> None:
    with SALIDA.open(encoding="utf-8", newline="") as fh:
        cabecera = next(csv.reader(fh))

    assert tuple(cabecera) == COLUMNAS == COLUMNAS_FACT
    assert "regla_id" not in cabecera  # SERIAL lo asigna PostgreSQL


def test_pares_unicos_y_cobertura_universal() -> None:
    filas = _filas()
    pares = [(f["codigo_rubro"], f["requisito_id"]) for f in filas]
    codigos = {c for c, _ in pares}

    assert len(pares) == 5690
    assert len(set(pares)) == len(pares)
    assert len(codigos) == 882
    for n in range(1, 7):
        req = f"REQ_{n:02d}"
        assert {c for c, r in pares if r == req} == codigos


def test_deteccion_de_tags_por_palabra_clave() -> None:
    assert detectar_tags("CAFÉ BAR") == ["universal", "alimentos", "inflamables"]
    assert detectar_tags("GIMNASIO") == [
        "universal", "actividad_fisica", "edilicio", "ruido",
    ]
    assert detectar_tags("FERRETERIA INDUSTRIAL") == ["universal", "inflamables", "ruido"]
    assert detectar_tags("COM.MIN.DE ROPA CONFECCION.") == ["universal", "edilicio"]
    assert detectar_tags("OFICINA COMERCIAL") == ["universal"]


def test_no_hay_falsos_positivos_por_substring() -> None:
    assert "alimentos" not in detectar_tags("COM.MIN.DE CALZADOS, TALABARTERIA")
    assert "alimentos" not in detectar_tags("COM. DE AUTOMOTORES Y EMBARCACIONES")


def test_reglas_de_superficie_y_obligatoriedad() -> None:
    filas = _filas()
    req7 = [f for f in filas if f["requisito_id"] == "REQ_07"]
    req10 = [f for f in filas if f["requisito_id"] == "REQ_10"]

    assert {f["condicion_superficie_min"] for f in req7} == {"0", "500"}
    condicionales = [f for f in req7 if f["condicion_superficie_min"] == "500"]
    obligatorios = [f for f in req7 if f["condicion_superficie_min"] == "0"]
    assert all(f["obligatoriedad"] == "condicional" for f in condicionales)
    assert all(f["obligatoriedad"] == "obligatorio" for f in obligatorios)
    assert all("500 m2" in f["nota_condicion"] for f in condicionales)
    assert req10 and all(f["obligatoriedad"] == "condicional" for f in req10)

    assert {f["obligatoriedad"] for f in filas} <= {"obligatorio", "condicional", "opcional"}
    assert {f["condicion_tipo_tramite"] for f in filas} == {"TODOS"}
    assert all(int(f["condicion_superficie_min"]) >= 0 for f in filas)


def test_el_generador_reproduce_el_csv_versionado() -> None:
    esperadas = generar_reglas(leer_rubros(), leer_requisitos())
    escritas = [
        {columna: fila[columna] for columna in COLUMNAS}
        for fila in _filas()
    ]
    assert esperadas == escritas


def test_loader_convierte_campos_numericos() -> None:
    filas = leer_fact_reglas()
    primera = filas[0]

    assert isinstance(primera["codigo_rubro"], Decimal)
    assert isinstance(primera["condicion_superficie_min"], Decimal)
    assert "ON CONFLICT (codigo_rubro, requisito_id) DO UPDATE" in UPSERT_FACT_SQL


def test_rechaza_el_codigo_urbanistico_como_fuente_de_rubros() -> None:
    with pytest.raises(ValueError, match="no tiene códigos de rubro"):
        leer_rubros(CSV_CU)
