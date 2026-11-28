"""
test_rubros.py — Tests del módulo de rubros

Endpoints cubiertos:
  GET /api/v1/rubros                         → lista de rubros disponibles
  GET /api/v1/rubros/{rubro}/requisitos      → checklist completo por rubro
"""


# ─── GET /api/v1/rubros ───────────────────────────────────────────────────────

def test_listar_rubros_retorna_200(client):
    response = client.get("/api/v1/rubros")
    assert response.status_code == 200


def test_listar_rubros_devuelve_lista(client):
    response = client.get("/api/v1/rubros")
    assert isinstance(response.json(), list)


def test_listar_rubros_no_vacia(client):
    """Debe haber al menos un rubro cargado en la DB."""
    response = client.get("/api/v1/rubros")
    data = response.json()
    assert len(data) > 0, "La lista de rubros está vacía. ¿Se cargó el CSV?"


def test_listar_rubros_son_strings(client):
    """Todos los elementos de la lista deben ser strings."""
    response = client.get("/api/v1/rubros")
    for rubro in response.json():
        assert isinstance(rubro, str), f"Se esperaba string, se obtuvo: {type(rubro)}"


def test_listar_rubros_contiene_general(client):
    """El rubro 'General' siempre debe existir (es la base de todos los checklists)."""
    response = client.get("/api/v1/rubros")
    rubros = response.json()
    assert "General" in rubros, "El rubro 'General' no está en la lista"


def test_listar_rubros_contiene_cafeteria(client):
    """'Cafetería' es el rubro de ejemplo del proyecto."""
    response = client.get("/api/v1/rubros")
    rubros = response.json()
    assert "Cafetería" in rubros, "El rubro 'Cafetería' no está en la lista"


# ─── GET /api/v1/rubros/{rubro}/requisitos ────────────────────────────────────

def test_requisitos_cafeteria_retorna_200(client):
    response = client.get("/api/v1/rubros/Cafetería/requisitos")
    assert response.status_code == 200


def test_requisitos_cafeteria_estructura(client):
    """La respuesta debe tener los campos: rubro, total, requisitos."""
    response = client.get("/api/v1/rubros/Cafetería/requisitos")
    data = response.json()
    assert "rubro" in data
    assert "total" in data
    assert "requisitos" in data


def test_requisitos_cafeteria_total_correcto(client):
    """Cafetería = 7 General + 5 específicos = 12 requisitos."""
    response = client.get("/api/v1/rubros/Cafetería/requisitos")
    data = response.json()
    assert data["total"] == 12, (
        f"Se esperaban 12 requisitos, se obtuvieron {data['total']}. "
        "Verificá que el CSV fue cargado correctamente."
    )
    assert len(data["requisitos"]) == 12


def test_requisitos_campos_de_cada_item(client):
    """Cada requisito debe tener los campos definidos en el schema."""
    response = client.get("/api/v1/rubros/Cafetería/requisitos")
    requisitos = response.json()["requisitos"]
    campos_obligatorios = {"id", "rubro", "tramite", "documentacion_requerida"}
    for req in requisitos:
        for campo in campos_obligatorios:
            assert campo in req, f"Al requisito le falta el campo '{campo}'"


def test_requisitos_rubro_inexistente_retorna_requisitos_generales(client):
    """Si el rubro no tiene requisitos específicos, devuelve 200 con el checklist General como fallback."""
    response = client.get("/api/v1/rubros/RubroQueNoExiste123/requisitos")
    assert response.status_code == 200
    data = response.json()
    assert data["rubro"] == "RubroQueNoExiste123"
    assert data["total"] == 7  # 7 requisitos generales base


def test_requisitos_rubro_general_retorna_7(client):
    """El rubro General solo tiene sus 7 requisitos propios."""
    response = client.get("/api/v1/rubros/General/requisitos")
    if response.status_code == 200:
        data = response.json()
        assert data["total"] == 7


def test_requisitos_rubro_con_tilde(client):
    """Los rubros con tildes (Cafetería) deben funcionar correctamente."""
    r1 = client.get("/api/v1/rubros/Cafetería/requisitos")
    assert r1.status_code == 200
