"""Tests del fixture de demo versionado y de su generador.

El fixture permite levantar una base reproducible sin Git LFS ni el dump de
89 MB. Estos tests fijan tres cosas: que los archivos sean chicos y no sean
punteros LFS, que la sanitización no deje identificadores directos y que el
generador sea determinista.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR_DEMO = RAIZ / "db" / "demo"
GENERADOR = RAIZ / "scripts" / "generar_demo.py"
META = DIR_DEMO / "FIXTURE.json"
HAB = DIR_DEMO / "habilitaciones_demo.csv"
EPOK = DIR_DEMO / "epok_fichas_demo.csv"

from src.export_postgres import COLS_HAB  # noqa: E402

TAMANO_MAXIMO = 512 * 1024


def _leer(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _sha256(ruta: Path) -> str:
    import hashlib

    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def test_metadata_coincide_con_los_archivos():
    meta = json.loads(META.read_text(encoding="utf-8"))
    assert meta["version_fixture"] == "1.0.0"
    assert meta["version_sanitizacion"] == "1.0.0"

    habilitaciones = meta["archivos"]["habilitaciones_demo.csv"]
    assert habilitaciones["sha256"] == _sha256(HAB)
    assert habilitaciones["filas"] == len(_leer(HAB))

    epok = meta["archivos"]["epok_fichas_demo.csv"]
    assert epok["sha256"] == _sha256(EPOK)
    assert epok["filas"] == len(_leer(EPOK))


def test_archivos_chicos_y_no_son_punteros_lfs():
    for ruta in (HAB, EPOK, META):
        assert ruta.exists(), ruta
        assert ruta.stat().st_size < TAMANO_MAXIMO, f"{ruta} es demasiado grande"
        assert not ruta.read_text(encoding="utf-8").startswith("version https://git-lfs")


def test_columnas_del_padron_son_las_del_contrato():
    with HAB.open(encoding="utf-8", newline="") as fh:
        columnas = next(csv.reader(fh))
    assert columnas == list(COLS_HAB)

    epok = _leer(EPOK)
    esperadas = {
        "smp", "ficha", "lng", "lat", "direccion", "superficie_total",
        "superficie_cubierta", "frente", "fondo", "pisos_sobre_rasante",
        "unidades_funcionales", "propiedad_horizontal", "puertas",
        "actualizado_en", "estado", "intentos", "ultimo_error",
        "ultimo_intento_en",
    }
    assert set(epok[0]) == esperadas


def test_sanitizacion_reemplaza_identificadores_directos():
    filas = _leer(HAB)
    assert filas
    for fila in filas:
        assert re.fullmatch(r"EMPRESA DEMO \d{4}", fila["razon_social"])
        assert re.fullmatch(r"EX-2026-DEMO-\d{6}", fila["numero_expediente"])
        assert re.fullmatch(r"DEMO-\d{6}", fila["partida_matriz"])
        assert 9_000_000 < int(fila["solicitud"]) < 10_000_000


def test_cruce_habilitaciones_epok_por_smp():
    hb = _leer(HAB)
    fichas = _leer(EPOK)
    smps_hab = {fila["smp"] for fila in hb}
    smps_epok = {fila["smp"] for fila in fichas}

    assert smps_hab == smps_epok
    assert len(smps_hab) >= 20
    assert len(hb) >= 100
    # El JSON compacto de la ficha debe ser parseable y apuntar al mismo SMP.
    for fila in fichas:
        ficha = json.loads(fila["ficha"])
        assert ficha["smp"] == fila["smp"]


def test_diversidad_minima_para_una_demo_util():
    filas = _leer(HAB)
    assert len({fila["comuna"] for fila in filas}) >= 5
    assert len({fila["codigo_rubro"] for fila in filas}) >= 10
    assert len({fila["anio"] for fila in filas}) >= 2

    fichas = _leer(EPOK)
    assert len(fichas) == len({fila["smp"] for fila in fichas})
    assert all(fila["estado"] == "ok" for fila in fichas)
    assert all(float(fila["lng"]) < 0 for fila in fichas)
    assert all(float(fila["lat"]) < 0 for fila in fichas)


def _escribir_padron(ruta: Path) -> None:
    filas = []
    for indice, smp in enumerate(
        ["038-27-20", "038-27-20", "031-42-19", "031-42-19", "007-8-27"], start=1
    ):
        fila = {columna: "" for columna in COLS_HAB}
        fila.update(
            {
                "solicitud": str(1000 + indice),
                "tipo_tramite": "Habilitación",
                "fecha_habilitacion": f"2020-0{indice}-01",
                "numero_expediente": f"EX-2020-{indice}",
                "codigo_rubro": "601010",
                "descripcion_rubro": "COM.MIN.DE BEBIDAS",
                "comuna": "1",
                "anio": "2020",
                "smp": smp,
                "razon_social": f"Persona Real {indice}",
                "partida_matriz": str(5000 + indice),
                "calles": "CALLE 1",
            }
        )
        filas.append(fila)

    with ruta.open("w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=list(COLS_HAB))
        escritor.writeheader()
        escritor.writerows(filas)


def _generar(entrada: Path, salida: Path, fecha: str = "2026-10-28T00:00:00+00:00"):
    return subprocess.run(
        [
            sys.executable,
            str(GENERADOR),
            "--entrada", str(entrada),
            "--salida", str(salida),
            "--filas", "4",
            "--smps", "2",
            "--fecha", fecha,
            "--sin-epok",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_generador_es_determinista_y_sanitiza(tmp_path):
    entrada = tmp_path / "padron.csv"
    _escribir_padron(entrada)

    salida_a = tmp_path / "a"
    salida_b = tmp_path / "b"
    for salida in (salida_a, salida_b):
        resultado = _generar(entrada, salida)
        assert resultado.returncode == 0, resultado.stderr

    for nombre in ("habilitaciones_demo.csv", "FIXTURE.json"):
        assert (salida_a / nombre).read_bytes() == (salida_b / nombre).read_bytes()

    filas = _leer(salida_a / "habilitaciones_demo.csv")
    assert len(filas) == 4
    assert {fila["smp"] for fila in filas} == {"038-027-020", "031-042-019"}
    assert all(fila["razon_social"].startswith("EMPRESA DEMO") for fila in filas)

    meta = json.loads((salida_a / "FIXTURE.json").read_text(encoding="utf-8"))
    assert meta["semilla"] == 20261028
    assert meta["fuente"]["epok"] == "no incluida"
    assert "epok_fichas_demo.csv" not in meta["archivos"]


def test_generador_rechaza_cupos_invalidos(tmp_path):
    entrada = tmp_path / "padron.csv"
    _escribir_padron(entrada)
    resultado = subprocess.run(
        [
            sys.executable,
            str(GENERADOR),
            "--entrada", str(entrada),
            "--salida", str(tmp_path / "out"),
            "--filas", "0",
            "--sin-epok",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 2
    assert "--filas" in resultado.stderr
