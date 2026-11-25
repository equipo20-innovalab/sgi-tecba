"""Tests estructurales del catálogo de requisitos del schema versionado.

El schema se aplica en CI con ``ON_ERROR_STOP``, así que estos tests no
necesitan base de datos: verifican que los objetos que espera TECBA sigan
presentes y que la vinculación use las claves reales del modelo.
"""

from __future__ import annotations

from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"


def test_schema_contiene_catalogo_y_matriz():
    sql = SCHEMA.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS dim_requisitos" in sql
    assert "CREATE TABLE IF NOT EXISTS fact_reglas_habilitacion" in sql
    assert "CREATE OR REPLACE VIEW requisitos_por_smp" in sql


def test_catalogo_expone_trazabilidad():
    sql = SCHEMA.read_text(encoding="utf-8")

    inicio = sql.index("CREATE TABLE IF NOT EXISTS dim_requisitos")
    fin = sql.index("CREATE TABLE IF NOT EXISTS fact_reglas_habilitacion")
    bloque = sql[inicio:fin]

    for columna in (
        "url_oficial",
        "tipo_accion",
        "organismo_emisor",
        "fuente_normativa",
        "fecha_actualizacion",
    ):
        assert columna in bloque


def test_matriz_usa_el_codigo_de_rubro_real():
    sql = SCHEMA.read_text(encoding="utf-8")

    inicio = sql.index("CREATE TABLE IF NOT EXISTS fact_reglas_habilitacion")
    fin = sql.index("CREATE OR REPLACE VIEW requisitos_por_smp")
    bloque = sql[inicio:fin]

    assert "codigo_rubro" in bloque and "NUMERIC NOT NULL" in bloque
    assert "REFERENCES dim_requisitos (requisito_id)" in bloque
