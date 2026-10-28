from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import SessionLocal
from app.main import app

client = TestClient(app)


def test_health_incluye_urbanismo_y_rls():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["tablas"]["codigo_urbanistico"] == 318127
    assert data["tablas"]["epok_direcciones"] == 62890
    assert data["rls"]["epok_fichas"] is True
    assert data["rls"]["habilitaciones"] is True
    assert data["rls"]["rubros_requisitos"] is True
    assert data["postgis"] is False


def test_join_epok_codigo_urbanistico_completo():
    with SessionLocal() as db:
        total = db.execute(text("""
                SELECT count(*)
                FROM epok_fichas f
                JOIN codigo_urbanistico c ON c.smp = upper(f.smp)
                """)).scalar()
    assert total == 19608


def test_geocodificar_corrientes_2500():
    response = client.get(
        "/api/v1/geocodificar", params={"direccion": "Av. Corrientes 2500"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["smp"] == "009-028-010B"
    assert data["barrio"] == "BALVANERA"
    assert data["comuna"] == 3
    assert data["altura"] == 2500
    assert data["candidatos"][0]["smp"] == "009-028-010B"


def test_geocodificar_corrientes_2502():
    response = client.get(
        "/api/v1/geocodificar", params={"direccion": "Av. Corrientes 2502"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["smp"] == "009-019-001"
    assert data["altura"] == 2502


def test_geocodificar_direccion_ambigua_devuelve_candidatos():
    response = client.get(
        "/api/v1/geocodificar", params={"direccion": "Directorio 1001"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["smp"] == "040-013-009"
    assert len(data["candidatos"]) == 2


def test_urbanismo_por_smp():
    response = client.get("/api/v1/urbanismo/009-028-010B")
    assert response.status_code == 200
    data = response.json()
    assert data["zona"] == "C3 I"
    assert data["barrio"] == "BALVANERA"
    assert data["comuna"] == 3
    assert data["grado_mixtura"] == 4
    assert data["grado_mixtura_label"] == "Grado 4 - alta mixtura"
    assert data["edificabilidad"] == 31.2
    assert data["fot"] == 4.0
    assert data["actividad_permitida"] == "A verificar"


def test_catastro_incluye_zonificacion():
    response = client.get("/api/v1/catastro/009-028-010B")
    assert response.status_code == 200
    data = response.json()
    assert data["superficie_total"] == 287.0
    assert data["superficie_cubierta"] == 286.0
    assert data["zonificacion"]["zona"] == "C3 I"
    assert data["barrio"] == "BALVANERA"
    assert data["comuna"] == 3
