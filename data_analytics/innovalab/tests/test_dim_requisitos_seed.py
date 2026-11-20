"""Tests del CSV maestro `dim_requisitos` y de su carga idempotente.

No hacen requests: las URLs se validaron con `curl -L` y con
`--validar-urls` al generar el seed. Acá se comprueba la forma del dataset
y que el loader respete la semántica de `url_oficial` NULL para checklists.
"""

from __future__ import annotations

import csv
from datetime import date

from scripts.generar_dim_requisitos import COLUMNAS, REQUISITOS, SALIDA, generar
from src.export_postgres import COLUMNAS_DIM, UPSERT_DIM_SQL, leer_dim_requisitos


def _filas() -> list[dict[str, str]]:
    with SALIDA.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_columnas_coinciden_con_el_ddl() -> None:
    with SALIDA.open(encoding="utf-8", newline="") as fh:
        cabecera = next(csv.reader(fh))

    assert tuple(cabecera) == COLUMNAS == COLUMNAS_DIM
    assert "fecha_actualizacion" in cabecera


def test_ids_unicos_y_secuenciales() -> None:
    filas = _filas()
    ids = [f["requisito_id"] for f in filas]

    assert len(filas) == 13
    assert len(set(ids)) == len(ids)
    assert ids == [f"REQ_{n:02d}" for n in range(1, 14)]


def test_tipo_accion_y_url_son_coherentes() -> None:
    for fila in _filas():
        assert fila["tipo_accion"] in {"externo", "checklist"}
        url = fila["url_oficial"]
        if fila["tipo_accion"] == "externo":
            assert url.startswith("https://"), fila["requisito_id"]
        else:
            assert url == "", fila["requisito_id"]


def test_trazabilidad_completa_y_fecha_iso() -> None:
    for fila in _filas():
        assert fila["organismo_emisor"].strip()
        assert fila["fuente_normativa"].strip()
        assert fila["documentacion_necesaria"].strip()
        assert fila["pasos_a_seguir"].strip()
        date.fromisoformat(fila["fecha_actualizacion"])


def test_el_script_regenera_el_csv_versionado(tmp_path) -> None:
    destino = tmp_path / "regenerado.csv"
    generar(destino)

    assert destino.read_bytes() == SALIDA.read_bytes()
    assert len(REQUISITOS) == 13


def test_loader_pasa_url_vacia_a_none() -> None:
    filas = leer_dim_requisitos()

    assert len(filas) == 13
    checklist = [f for f in filas if f["tipo_accion"] == "checklist"]
    externos = [f for f in filas if f["tipo_accion"] == "externo"]
    assert len(checklist) == 4
    assert len(externos) == 9
    assert all(f["url_oficial"] is None for f in checklist)
    assert all(f["url_oficial"] for f in externos)
    assert "ON CONFLICT (requisito_id) DO UPDATE" in UPSERT_DIM_SQL
