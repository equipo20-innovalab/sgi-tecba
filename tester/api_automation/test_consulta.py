"""
test_consulta.py — Tests del endpoint POST /api/v1/consulta

Es el endpoint central del MVP. Recibe una consulta en lenguaje natural
(o estructurada) y devuelve información integrada de las 3 fuentes.

IMPORTANTE: Este endpoint puede depender de geocoding externo.
            Los tests están pensados para ser tolerantes a esas fallas.
"""


# ─── Validaciones de input (no dependen de DB ni servicios externos) ──────────

def test_consulta_sin_body_retorna_422(client):
    """Sin body la validación de Pydantic debe devolver 422."""
    response = client.post("/api/v1/consulta")
    assert response.status_code == 422


def test_consulta_body_vacio_retorna_422(client):
    """Un body vacío {} no cumple el model_validator → 422."""
    response = client.post("/api/v1/consulta", json={})
    assert response.status_code == 422


def test_consulta_solo_sesion_id_retorna_422(client):
    """Enviar solo sesion_id sin texto ni rubro+direccion → 422."""
    response = client.post("/api/v1/consulta", json={"sesion_id": "abc123"})
    assert response.status_code == 422


def test_consulta_rubro_sin_direccion_retorna_422(client):
    """El modo estructurado requiere AMBOS: rubro y direccion."""
    response = client.post("/api/v1/consulta", json={"rubro": "Cafetería"})
    assert response.status_code == 422


def test_consulta_direccion_sin_rubro_retorna_422(client):
    """Solo la direccion sin rubro tampoco es válido."""
    response = client.post("/api/v1/consulta", json={"direccion": "Av. Corrientes 2500"})
    assert response.status_code == 422


# ─── Modo 1: Lenguaje natural ─────────────────────────────────────────────────

def test_consulta_texto_natural_acepta_request(client):
    """
    Con un texto válido el endpoint debe aceptar el request.
    Puede devolver 200 (éxito) o 500 (falla en geocoding/servicio externo).
    No debe devolver 422 (error de validación).
    """
    response = client.post(
        "/api/v1/consulta",
        json={"texto": "Quiero abrir una cafetería en Av. Corrientes 2500"}
    )
    assert response.status_code != 422, (
        "El endpoint rechazó un input válido. Revisar el model_validator."
    )


def test_consulta_texto_natural_estructura_respuesta(client):
    """Si el endpoint devuelve 200, la respuesta debe tener los campos del schema."""
    response = client.post(
        "/api/v1/consulta",
        json={"texto": "Quiero abrir una cafetería en Av. Corrientes 2500"}
    )
    if response.status_code == 200:
        data = response.json()
        campos_esperados = [
            "actividad_detectada",
            "ubicacion",
            "requisitos",
            "competencia_cercana",
            "habilitaciones_parcela",
            "pasos_sugeridos",
            "fuentes",
        ]
        for campo in campos_esperados:
            assert campo in data, f"Falta el campo '{campo}' en ConsultaResponse"


def test_consulta_requisitos_es_lista(client):
    """El campo 'requisitos' siempre debe ser una lista (puede estar vacía)."""
    response = client.post(
        "/api/v1/consulta",
        json={"texto": "cafetería en Palermo"}
    )
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data["requisitos"], list)
        assert isinstance(data["fuentes"], list)
        assert isinstance(data["pasos_sugeridos"], list)


# ─── Modo 2: Estructurado (rubro + dirección) ─────────────────────────────────

def test_consulta_modo_estructurado_acepta_request(client):
    """El modo estructurado con rubro + dirección debe ser aceptado."""
    response = client.post(
        "/api/v1/consulta",
        json={"rubro": "Cafetería", "direccion": "Av. Corrientes 2500"}
    )
    assert response.status_code != 422


def test_consulta_modo_estructurado_y_texto_a_la_vez(client):
    """Enviar texto Y rubro+dirección a la vez también debe ser válido."""
    response = client.post(
        "/api/v1/consulta",
        json={
            "texto": "Quiero abrir una cafetería",
            "rubro": "Cafetería",
            "direccion": "Av. Corrientes 2500"
        }
    )
    assert response.status_code != 422


# ─── Estructura de ubicación ──────────────────────────────────────────────────

def test_consulta_ubicacion_tiene_estructura_correcta(client):
    """El sub-objeto 'ubicacion' debe tener los campos del schema Ubicacion."""
    response = client.post(
        "/api/v1/consulta",
        json={"texto": "cafetería en Corrientes 2500"}
    )
    if response.status_code == 200:
        ubicacion = response.json().get("ubicacion", {})
        campos_ubicacion = [
            "direccion_original", "direccion_normalizada",
            "lat", "lng", "comuna", "smp"
        ]
        for campo in campos_ubicacion:
            assert campo in ubicacion, f"Falta '{campo}' en el objeto ubicacion"
