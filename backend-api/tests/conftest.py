"""
conftest.py — Fixtures compartidos para todos los tests del backend.

El TestClient de FastAPI levanta la app en memoria sin necesidad de
correr el servidor, pero sí necesita la DB (Docker) disponible.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    Cliente HTTP reutilizable en toda la sesión de tests.
    scope="session" significa que se crea una sola vez para todos los tests.
    """
    with TestClient(app) as c:
        yield c
