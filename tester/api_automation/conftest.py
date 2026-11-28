"""
conftest.py — Fixtures compartidos para la suite de pruebas QA Automatizadas (SGI TECBA).
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient

# Localiza la carpeta del backend y carga sus variables de entorno (.env)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend-api"
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Asegura que backend-api esté en el sys.path para importar la aplicación
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    Cliente HTTP de pruebas reutilizable para toda la sesión de QA.
    Permite validar los endpoints HTTP conectando a la base de datos.
    """
    with TestClient(app) as c:
        yield c
