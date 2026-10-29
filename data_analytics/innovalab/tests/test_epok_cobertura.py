"""Tests de cobertura, dashboard, alertas y política incremental de EPOK."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone

from src import epok_cobertura as ec
from src.enriquecer_epok import _ficha_valida, extraer_campos

AHORA = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


def _escribir_padron(tmp_path, filas):
    ruta = tmp_path / "padron.csv"
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=["smp", "anio", "comuna"])
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


def _fila(resuelto, intentos=1, dias=1):
    return {
        "resuelto": resuelto,
        "estado": "ok" if resuelto else "fallido",
        "intentos": intentos,
        "actualizado_en": AHORA - timedelta(days=dias),
        "ultimo_error": None,
    }


def test_normalizar_smp_epok_padrea_y_descarta_marcadores():
    assert ec.normalizar_smp_epok("038-27-20") == "038-027-020"
    assert ec.normalizar_smp_epok(" 038-027-020 ") == "038-027-020"
    assert ec.normalizar_smp_epok("sin dato") is None
    assert ec.normalizar_smp_epok("") is None
    assert ec.normalizar_smp_epok(None) is None


def test_leer_padron_agrega_por_smp_anio_y_comuna(tmp_path):
    ruta = _escribir_padron(
        tmp_path,
        [
            {"smp": "038-27-20", "anio": "2015", "comuna": "1"},
            {"smp": "038-027-020", "anio": "2016", "comuna": "1"},
            {"smp": "031-42-19", "anio": "2020", "comuna": "2"},
            {"smp": "", "anio": "2020", "comuna": "2"},
        ],
    )

    padron = ec.leer_padron(ruta)

    assert padron["total_habilitaciones"] == 4
    assert padron["habilitaciones_sin_smp"] == 1
    assert padron["smps"] == ["031-042-019", "038-027-020"]
    assert padron["habilitaciones_por_smp"]["038-027-020"] == 2
    assert sum(padron["por_anio"]["2015"].values()) == 1
    assert sum(padron["por_anio"]["2020"].values()) == 2
    assert sum(padron["por_comuna"]["1"].values()) == 2


def test_seleccionar_candidatos_aplica_politica_incremental():
    estado = {
        "A": _fila(False, intentos=1),
        "B": _fila(False, intentos=3),
        "C": _fila(True, dias=40),
        "D": _fila(True, dias=1),
    }
    smps = ["A", "B", "C", "D", "E"]

    candidatos, motivos = ec.seleccionar_candidatos(
        smps, estado, max_edad_dias=30, max_intentos=3, ahora=AHORA
    )
    assert candidatos == ["A", "C", "E"]
    assert motivos == {
        "nuevos": 1,
        "fallidos": 1,
        "desactualizados": 1,
        "forzados": 0,
    }

    solo_pendientes, _ = ec.seleccionar_candidatos(
        smps, estado, max_edad_dias=30, solo_pendientes=True, ahora=AHORA
    )
    assert solo_pendientes == ["A", "E"]

    con_reintento, _ = ec.seleccionar_candidatos(
        smps, estado, max_edad_dias=30, reintentar=True, ahora=AHORA
    )
    assert con_reintento == ["A", "B", "C", "E"]

    todos, motivos_todos = ec.seleccionar_candidatos(
        smps, estado, todo=True, ahora=AHORA
    )
    assert todos == smps
    assert motivos_todos["forzados"] == 5

    limitados, _ = ec.seleccionar_candidatos(
        smps, estado, max_edad_dias=30, limite=2, ahora=AHORA
    )
    assert limitados == ["A", "C"]


def test_seleccionar_candidatos_sin_refresh():
    estado = {"A": _fila(True, dias=90)}
    candidatos, _ = ec.seleccionar_candidatos(
        ["A"], estado, max_edad_dias=None, ahora=AHORA
    )
    assert candidatos == []


def _reporte_base(tmp_path, comuna="1"):
    ruta = _escribir_padron(
        tmp_path,
        [
            {"smp": "038-27-20", "anio": "2015", "comuna": comuna},
            {"smp": "038-027-020", "anio": "2016", "comuna": comuna},
            {"smp": "031-42-19", "anio": "2020", "comuna": comuna},
            {"smp": "", "anio": "2020", "comuna": comuna},
        ],
    )
    padron = ec.leer_padron(ruta)
    estado = {
        "038-027-020": _fila(True, dias=1),
        "031-042-019": _fila(False, intentos=3, dias=1),
        "099-999-999": _fila(True, dias=90),
    }
    return ec.construir_reporte(
        padron,
        estado,
        umbrales={
            "min_cobertura_smp": 0.80,
            "min_cobertura_hab": 0.80,
            "max_edad_dias": 30,
            "max_fallidas": 0,
            "max_pendientes_smp": 0,
        },
        ahora=AHORA,
    )


def test_construir_reporte_calcula_cobertura(tmp_path):
    reporte = _reporte_base(tmp_path)
    cobertura = reporte["cobertura"]
    fichas = reporte["fichas"]

    assert cobertura["habilitaciones"] == 4
    assert cobertura["habilitaciones_sin_smp"] == 1
    assert cobertura["habilitaciones_con_ficha"] == 2
    assert cobertura["cobertura_habilitaciones"] == 0.5
    assert cobertura["smp_padron"] == 2
    assert cobertura["smp_resueltos"] == 1
    assert cobertura["smp_pendientes"] == 1
    assert cobertura["cobertura_smp"] == 0.5

    assert fichas["total"] == 3
    assert fichas["resueltas"] == 2
    assert fichas["fallidas"] == 1
    assert fichas["en_padron"] == 2
    assert fichas["desactualizadas"] == 1
    assert fichas["antiguedad_dias"] == 1
    assert reporte["por_anio"][0]["anio"] == "2015"
    assert reporte["por_comuna"][0]["comuna"] == "1"


def test_alertas_detectan_cobertura_fallos_y_sla(tmp_path):
    reporte = _reporte_base(tmp_path)
    codigos = {alerta["codigo"] for alerta in reporte["alertas"]}

    assert "COBERTURA_SMP_BAJA" in codigos
    assert "COBERTURA_HABILITACIONES_BAJA" in codigos
    assert "FICHAS_DESACTUALIZADAS" in codigos
    assert "FICHAS_FALLIDAS" in codigos
    assert "COLA_PENDIENTE" in codigos
    assert "COMUNAS_SIN_COBERTURA" not in codigos  # la comuna sí tiene cobertura

    # Sin fichas resueltas y sin fecha => alertas críticas.
    padron = ec.leer_padron(_escribir_padron(tmp_path, [
        {"smp": "031-42-19", "anio": "2020", "comuna": "2"},
    ]))
    vacio = ec.construir_reporte(
        padron,
        {"031-042-019": _fila(False, intentos=1)},
        ahora=AHORA,
    )
    codigos_vacio = {a["codigo"] for a in vacio["alertas"]}
    assert "SIN_FICHAS" in codigos_vacio
    assert "SIN_ACTUALIZACION" in codigos_vacio
    assert any(a["nivel"] == "critica" for a in vacio["alertas"])


def test_dashboard_escapa_datos_y_muestra_metricas(tmp_path):
    reporte = _reporte_base(tmp_path, comuna="<script>")
    html_render = ec.render_dashboard(reporte)

    assert html_render.startswith("<!doctype html>")
    assert "Cobertura EPOK" in html_render
    assert "50,0%" in html_render
    assert "COBERTURA_SMP_BAJA" in html_render
    assert "<script>" not in html_render
    assert "&lt;script&gt;" in html_render


def test_guardar_reporte_escribe_json_y_html(tmp_path):
    reporte = _reporte_base(tmp_path)
    ruta_json = tmp_path / "cobertura.json"
    ruta_html = tmp_path / "dashboard.html"

    guardadas = ec.guardar_reporte(reporte, ruta_json, ruta_html)

    assert guardadas == (ruta_json, ruta_html)
    assert json.loads(ruta_json.read_text(encoding="utf-8"))["cobertura"]["smp_padron"] == 2
    assert "Cobertura EPOK" in ruta_html.read_text(encoding="utf-8")


def test_extraer_campos_y_ficha_valida():
    ficha = {
        "centroide": ["-58.4", "-34.6"],
        "direccion": "CALLE 1",
        "superficie_total": "100.5",
        "superficie_cubierta": "80",
        "frente": "10",
        "fondo": "20",
        "pisos_sobre_rasante": "2",
        "unidades_funcionales": "3",
        "propiedad_horizontal": "PH",
        "puertas": [{"calle": "1"}],
    }
    campos = extraer_campos(ficha)
    assert campos["lng"] == -58.4
    assert campos["lat"] == -34.6
    assert campos["superficie_total"] == 100.5
    assert campos["pisos_sobre_rasante"] == 2
    assert campos["unidades_funcionales"] == 3

    assert _ficha_valida(ficha)
    assert _ficha_valida({"superficie_total": "10"})
    assert not _ficha_valida({})
    assert not _ficha_valida(None)
