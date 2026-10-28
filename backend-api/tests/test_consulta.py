from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_consulta_cafeteria_corrientes_2500():
    response = client.post(
        "/api/v1/consulta",
        json={"texto": "Quiero abrir una cafetería en Av. Corrientes 2500"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["actividad_detectada"] == "Cafetería"
    assert data["ubicacion"]["smp"] == "009-028-010B"
    assert data["ubicacion"]["barrio"] == "BALVANERA"
    assert data["ubicacion"]["comuna"] == 3

    assert data["district"] == "C3 I"
    assert data["landArea"] == "287 m²"
    assert data["coveredArea"] == "286 m²"
    assert data["maxHeight"].startswith("31.2")
    assert data["viabilityStatus"] == "A verificar"
    assert data["zonificacion"]["grado_mixtura"] == 4
    assert data["zonificacion"]["actividad_permitida"] == "A verificar"

    assert len(data["requisitos"]) == 12
    assert len(data["competencia_cercana"]) > 0
    assert data["rawData"]["smp"] == "009-028-010B"


def test_consulta_estructurada_sin_tilde():
    response = client.post(
        "/api/v1/consulta",
        json={"rubro": "Cafeteria", "direccion": "Av. Corrientes 2500"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ubicacion"]["smp"] == "009-028-010B"
    assert len(data["requisitos"]) == 12


def test_requisitos_acepta_con_y_sin_tilde():
    sin_tilde = client.get("/api/v1/rubros/Cafeteria/requisitos")
    con_tilde = client.get("/api/v1/rubros/Cafetería/requisitos")
    assert sin_tilde.status_code == 200
    assert con_tilde.status_code == 200
    assert sin_tilde.json()["total"] == 12
    assert con_tilde.json()["total"] == 12
