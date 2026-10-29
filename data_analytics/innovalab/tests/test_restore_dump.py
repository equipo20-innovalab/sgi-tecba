"""Tests del script de restore (sin base de datos ni Docker).

El script se prueba en sus modos puros: detección de versión, filtrado de
meta-comandos de PostgreSQL 18 y guardas de seguridad. La restauración real
contra un servidor se ejecuta en CI (`.github/workflows/analytics-demo-restore.yml`).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "restore_dump.sh"

DUMP_EJEMPLO = """--
-- PostgreSQL database dump
--

\\restrict TOKEN_DE_PRUEBA

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET transaction_timeout = 0;
CREATE TABLE public.demo (id integer);
ALTER TABLE public.demo OWNER TO postgres;
COPY public.demo (id) FROM stdin;
1
2
\\.
\\unrestrict TOKEN_DE_PRUEBA
"""


def _ejecutar(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    entorno = {**os.environ, "DATABASE_URL": "", "PGDATABASE": ""}
    if env:
        entorno.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=entorno,
        check=False,
    )


def _dump(tmp_path: Path, contenido: str = DUMP_EJEMPLO) -> Path:
    ruta = tmp_path / "dump.sql"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def test_help_lista_opciones():
    resultado = _ejecutar("--help")
    assert resultado.returncode == 0
    assert "Opciones:" in resultado.stderr
    assert "--solo-filtrar" in resultado.stderr


def test_version_es_semver():
    resultado = _ejecutar("--version")
    assert resultado.returncode == 0
    partes = resultado.stdout.strip().split(".")
    assert len(partes) == 3
    assert all(parte.isdigit() for parte in partes)


def test_info_detecta_version_del_dump(tmp_path):
    dump = _dump(tmp_path)
    resultado = _ejecutar(str(dump), "--info", "--servidor-major", "15")
    assert resultado.returncode == 0
    assert "18.3" in resultado.stdout
    assert "major 15" in resultado.stdout
    assert "filtrarán" in resultado.stdout


def test_detecta_puntero_lfs(tmp_path):
    ruta = tmp_path / "dump.sql"
    ruta.write_text(
        "version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 10\n",
        encoding="utf-8",
    )
    resultado = _ejecutar(str(ruta), "--info", "--servidor-major", "18")
    assert resultado.returncode == 3
    assert "git lfs pull" in resultado.stderr


def test_archivo_inexistente(tmp_path):
    resultado = _ejecutar(str(tmp_path / "no-existe.sql"), "--info", "--servidor-major", "18")
    assert resultado.returncode == 2
    assert "no existe el dump" in resultado.stderr


def test_owner_invalido(tmp_path):
    dump = _dump(tmp_path)
    resultado = _ejecutar(
        str(dump), "--solo-filtrar", "--servidor-major", "18", "--owner", "bad;drop"
    )
    assert resultado.returncode == 2
    assert "--owner" in resultado.stderr


def test_filtra_para_servidor_15(tmp_path):
    dump = _dump(tmp_path)
    resultado = _ejecutar(
        str(dump), "--solo-filtrar", "--servidor-major", "15", "--owner", "demo_rol"
    )
    assert resultado.returncode == 0
    salida = resultado.stdout
    assert "\\restrict" not in salida
    assert "\\unrestrict" not in salida
    assert "transaction_timeout" not in salida
    assert 'OWNER TO "demo_rol"' in salida
    # Los datos del COPY deben sobrevivir al filtrado.
    assert "COPY public.demo (id) FROM stdin;" in salida
    assert "\n1\n2\n" in salida


def test_conserva_transaction_timeout_en_servidor_18(tmp_path):
    dump = _dump(tmp_path)
    resultado = _ejecutar(str(dump), "--solo-filtrar", "--servidor-major", "18")
    assert resultado.returncode == 0
    assert "SET transaction_timeout" in resultado.stdout
    assert "\\restrict" not in resultado.stdout
    assert "OWNER TO postgres" in resultado.stdout  # sin --owner no se reasigna


def test_salida_a_archivo(tmp_path):
    dump = _dump(tmp_path)
    destino = tmp_path / "filtrado.sql"
    resultado = _ejecutar(
        str(dump),
        "--solo-filtrar",
        "--servidor-major",
        "15",
        "--salida",
        str(destino),
    )
    assert resultado.returncode == 0
    assert destino.exists()
    contenido = destino.read_text(encoding="utf-8")
    assert "\\restrict" not in contenido
    assert "transaction_timeout" not in contenido


def test_solo_filtrar_no_requiere_servidor(tmp_path):
    """Sin --servidor-major ni base disponible, el modo filtro no debe colgarse."""
    dump = _dump(tmp_path)
    resultado = _ejecutar(str(dump), "--solo-filtrar")
    assert resultado.returncode == 0
    assert "transaction_timeout" not in resultado.stdout


def test_avisa_si_no_puede_detectar_version(tmp_path):
    dump = _dump(tmp_path, "CREATE TABLE public.demo (id integer);\n")
    resultado = _ejecutar(str(dump), "--info", "--servidor-major", "18")
    assert resultado.returncode == 0
    assert "desconocida" in resultado.stdout
