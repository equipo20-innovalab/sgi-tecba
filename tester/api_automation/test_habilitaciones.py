"""
test_habilitaciones.py — Tests del módulo de habilitaciones

Endpoints cubiertos:
  GET /api/v1/habilitaciones/cobertura                       → cobertura de datos (NUEVO)
  GET /api/v1/habilitaciones/por-comuna/{comuna}             → conteo por comuna
  GET /api/v1/habilitaciones/rubros-por-comuna/{comuna}      → top rubros por comuna
  GET /api/v1/habilitaciones/buscar-cafeterias               → búsqueda de cafeterías
"""


# ─── GET /api/v1/habilitaciones/cobertura (NUEVO) ────────────────────────────

def test_cobertura_retorna_200(client):
    response = client.get("/api/v1/habilitaciones/cobertura")
    assert response.status_code == 200


def test_cobertura_estructura_basica(client):
    """La respuesta debe tener total_registros y campos (según CoberturaDatos)."""
    response = client.get("/api/v1/habilitaciones/cobertura")
    data = response.json()
    assert "total_registros" in data, "Falta el campo 'total_registros'"
    assert "campos" in data, "Falta el campo 'campos'"
    assert isinstance(data["campos"], dict)


def test_cobertura_total_registros_positivo(client):
    """Si hay datos cargados, el total debe ser mayor a 0."""
    response = client.get("/api/v1/habilitaciones/cobertura")
    data = response.json()
    assert data["total_registros"] >= 0


def test_cobertura_campos_tienen_estructura_correcta(client):
    """Cada campo de cobertura debe tener registros_con_dato, registros_sin_dato y cobertura."""
    response = client.get("/api/v1/habilitaciones/cobertura")
    campos = response.json().get("campos", {})
    for nombre_campo, info in campos.items():
        assert "registros_con_dato" in info, f"Campo '{nombre_campo}' le falta 'registros_con_dato'"
        assert "registros_sin_dato" in info, f"Campo '{nombre_campo}' le falta 'registros_sin_dato'"
        assert "cobertura" in info, f"Campo '{nombre_campo}' le falta 'cobertura'"
        assert 0.0 <= info["cobertura"] <= 100.0, (
            f"La cobertura de '{nombre_campo}' está fuera del rango [0, 100]"
        )


# ─── GET /api/v1/habilitaciones/por-comuna/{comuna} ──────────────────────────

def test_por_comuna_retorna_200(client):
    response = client.get("/api/v1/habilitaciones/por-comuna/3")
    assert response.status_code == 200


def test_por_comuna_estructura(client):
    """La respuesta debe tener 'comuna' y 'total_habilitaciones'."""
    response = client.get("/api/v1/habilitaciones/por-comuna/3")
    data = response.json()
    assert "comuna" in data
    assert "total_habilitaciones" in data


def test_por_comuna_devuelve_la_misma_comuna(client):
    """El campo 'comuna' en la respuesta debe coincidir con el pedido."""
    response = client.get("/api/v1/habilitaciones/por-comuna/5")
    data = response.json()
    assert data["comuna"] == 5


def test_por_comuna_total_es_entero_no_negativo(client):
    response = client.get("/api/v1/habilitaciones/por-comuna/1")
    data = response.json()
    assert isinstance(data["total_habilitaciones"], int)
    assert data["total_habilitaciones"] >= 0


def test_por_comuna_inexistente_devuelve_cero(client):
    """Una comuna inexistente (ej: 99) no debe romper, debe devolver 0."""
    response = client.get("/api/v1/habilitaciones/por-comuna/99")
    assert response.status_code == 200
    data = response.json()
    assert data["total_habilitaciones"] == 0


# ─── GET /api/v1/habilitaciones/rubros-por-comuna/{comuna} ───────────────────

def test_rubros_por_comuna_retorna_200(client):
    response = client.get("/api/v1/habilitaciones/rubros-por-comuna/3")
    assert response.status_code == 200


def test_rubros_por_comuna_devuelve_lista(client):
    response = client.get("/api/v1/habilitaciones/rubros-por-comuna/3")
    assert isinstance(response.json(), list)


def test_rubros_por_comuna_respeta_limit(client):
    """El parámetro limit debe limitar la cantidad de resultados."""
    response = client.get("/api/v1/habilitaciones/rubros-por-comuna/3?limit=5")
    data = response.json()
    assert len(data) <= 5


def test_rubros_por_comuna_estructura_items(client):
    """Cada item debe tener 'rubro' y 'total'."""
    response = client.get("/api/v1/habilitaciones/rubros-por-comuna/3?limit=3")
    for item in response.json():
        assert "rubro" in item
        assert "total" in item
        assert isinstance(item["total"], int)
        assert item["total"] > 0


def test_rubros_por_comuna_limit_maximo(client):
    """El límite máximo permitido es 100."""
    response = client.get("/api/v1/habilitaciones/rubros-por-comuna/3?limit=100")
    assert response.status_code == 200


def test_rubros_por_comuna_limit_fuera_de_rango(client):
    """Un limit=0 o limit=101 debe devolver 422 por validación."""
    r_cero = client.get("/api/v1/habilitaciones/rubros-por-comuna/3?limit=0")
    assert r_cero.status_code == 422

    r_excede = client.get("/api/v1/habilitaciones/rubros-por-comuna/3?limit=101")
    assert r_excede.status_code == 422


# ─── GET /api/v1/habilitaciones/buscar-cafeterias ────────────────────────────

def test_buscar_cafeterias_retorna_200(client):
    response = client.get("/api/v1/habilitaciones/buscar-cafeterias")
    assert response.status_code == 200


def test_buscar_cafeterias_devuelve_lista(client):
    response = client.get("/api/v1/habilitaciones/buscar-cafeterias")
    assert isinstance(response.json(), list)


def test_buscar_cafeterias_con_limite(client):
    response = client.get("/api/v1/habilitaciones/buscar-cafeterias?limit=10")
    data = response.json()
    assert len(data) <= 10


def test_buscar_cafeterias_filtro_por_comuna(client):
    """Filtrar por comuna no debe romper el endpoint."""
    response = client.get("/api/v1/habilitaciones/buscar-cafeterias?comuna=3&limit=5")
    assert response.status_code == 200


def test_buscar_cafeterias_limit_maximo(client):
    """El límite máximo es 200."""
    response = client.get("/api/v1/habilitaciones/buscar-cafeterias?limit=200")
    assert response.status_code == 200


def test_buscar_cafeterias_limit_fuera_de_rango(client):
    """limit=0 o limit=201 deben devolver 422."""
    r_cero = client.get("/api/v1/habilitaciones/buscar-cafeterias?limit=0")
    assert r_cero.status_code == 422

    r_excede = client.get("/api/v1/habilitaciones/buscar-cafeterias?limit=201")
    assert r_excede.status_code == 422
