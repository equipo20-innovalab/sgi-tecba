"""
test_health.py — Tests del endpoint GET /api/v1/health

Qué verifica:
- El endpoint responde con HTTP 200
- La estructura de la respuesta es correcta
- Se reportan las 4 tablas (rubros_requisitos, habilitaciones, epok_fichas, codigo_urbanistico)
- Los conteos son números no negativos
"""


def test_health_retorna_200(client):
    """El endpoint debe responder siempre, incluso si la DB falla."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_status_es_ok_o_error(client):
    """El campo 'status' solo puede ser 'ok' o 'error'."""
    response = client.get("/api/v1/health")
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "error")


def test_health_con_db_conectada_tiene_4_tablas(client):
    """
    Cuando la DB está conectada, la respuesta debe incluir las 4 tablas.
    NOTA: este commit agregó 'codigo_urbanistico' — antes eran solo 3.
    """
    response = client.get("/api/v1/health")
    data = response.json()

    if data["status"] == "ok":
        assert data["database"] == "connected"
        tablas = data["tablas"]
        assert "rubros_requisitos" in tablas, "Falta la tabla rubros_requisitos"
        assert "habilitaciones" in tablas, "Falta la tabla habilitaciones"
        assert "epok_fichas" in tablas, "Falta la tabla epok_fichas"
        assert "codigo_urbanistico" in tablas, "Falta la tabla codigo_urbanistico (nueva)"


def test_health_conteos_son_enteros_no_negativos(client):
    """Los conteos de filas deben ser números enteros >= 0."""
    response = client.get("/api/v1/health")
    data = response.json()

    if data["status"] == "ok":
        for tabla, conteo in data["tablas"].items():
            assert isinstance(conteo, int), f"El conteo de '{tabla}' no es entero"
            assert conteo >= 0, f"El conteo de '{tabla}' es negativo"


def test_health_rubros_minimo_esperado(client):
    """
    rubros_requisitos debe tener al menos 12 filas (7 General + 5 Cafetería).
    Si hay menos, los datos no se cargaron correctamente.
    """
    response = client.get("/api/v1/health")
    data = response.json()

    if data["status"] == "ok":
        assert data["tablas"]["rubros_requisitos"] >= 12, (
            "rubros_requisitos tiene menos de 12 filas. "
            "Verificá que el CSV fue cargado con: "
            "docker cp db/seed/rubros_requisitos.csv tecba-postgres:/tmp/rubros.csv"
        )
