"""
test_mapa.py — Tests del módulo de mapa (NUEVO en commit c40f0e6)

Endpoints cubiertos:
  GET /api/v1/mapa/comunas     → GeoJSON de comunas (desde archivo en disco)
  GET /api/v1/mapa/parcelas    → parcelas con coordenadas, filtros y paginación
"""


# ─── GET /api/v1/mapa/comunas ─────────────────────────────────────────────────

def test_mapa_comunas_responde(client):
    """El endpoint debe responder (200 si el archivo existe, 404 si no)."""
    response = client.get("/api/v1/mapa/comunas")
    assert response.status_code in (200, 404)


def test_mapa_comunas_si_existe_es_geojson(client):
    """Si el archivo GeoJSON existe, la respuesta debe ser un FeatureCollection."""
    response = client.get("/api/v1/mapa/comunas")
    if response.status_code == 200:
        data = response.json()
        assert "type" in data, "Falta el campo 'type' en el GeoJSON"
        assert data["type"] == "FeatureCollection"
        assert "features" in data, "Falta el campo 'features' en el GeoJSON"
        assert isinstance(data["features"], list)


def test_mapa_comunas_si_falta_archivo_devuelve_404(client):
    """Si el archivo no existe, debe devolver 404 con mensaje descriptivo."""
    response = client.get("/api/v1/mapa/comunas")
    if response.status_code == 404:
        data = response.json()
        assert "detail" in data


# ─── GET /api/v1/mapa/parcelas ────────────────────────────────────────────────

def test_mapa_parcelas_sin_filtros_retorna_200(client):
    """Sin filtros debe responder 200 con la estructura correcta."""
    response = client.get("/api/v1/mapa/parcelas")
    assert response.status_code == 200


def test_mapa_parcelas_estructura_respuesta(client):
    """La respuesta debe tener: total, limite, offset, features."""
    response = client.get("/api/v1/mapa/parcelas")
    data = response.json()
    assert "total" in data
    assert "limite" in data
    assert "offset" in data
    assert "features" in data
    assert isinstance(data["features"], list)


def test_mapa_parcelas_valores_paginacion_por_defecto(client):
    """Los valores default son limite=20000, offset=0."""
    response = client.get("/api/v1/mapa/parcelas")
    data = response.json()
    assert data["limite"] == 20000
    assert data["offset"] == 0


def test_mapa_parcelas_total_no_negativo(client):
    response = client.get("/api/v1/mapa/parcelas")
    data = response.json()
    assert data["total"] >= 0


# ─── Filtro: comuna ───────────────────────────────────────────────────────────

def test_mapa_parcelas_filtro_comuna_valida(client):
    """Comunas del 1 al 15 son válidas en CABA."""
    response = client.get("/api/v1/mapa/parcelas?comuna=3")
    assert response.status_code == 200


def test_mapa_parcelas_todas_las_comunas(client):
    """Verificar que el parámetro commune acepta el rango completo."""
    for comuna in [1, 8, 15]:
        response = client.get(f"/api/v1/mapa/parcelas?comuna={comuna}")
        assert response.status_code == 200, f"Falló con comuna={comuna}"


def test_mapa_parcelas_comuna_cero_invalida(client):
    """comuna=0 está fuera del rango ge=1 → debe devolver 422."""
    response = client.get("/api/v1/mapa/parcelas?comuna=0")
    assert response.status_code == 422


def test_mapa_parcelas_comuna_16_invalida(client):
    """comuna=16 está fuera del rango le=15 → debe devolver 422."""
    response = client.get("/api/v1/mapa/parcelas?comuna=16")
    assert response.status_code == 422


# ─── Filtro: bounding box (bbox) ──────────────────────────────────────────────

def test_mapa_parcelas_bbox_completo_valido(client):
    """Un bbox completo y válido para CABA debe devolver 200."""
    params = "oeste=-58.53&sur=-34.71&este=-58.33&norte=-34.52"
    response = client.get(f"/api/v1/mapa/parcelas?{params}")
    assert response.status_code == 200


def test_mapa_parcelas_bbox_incompleto_3_params(client):
    """Si se envían solo 3 de los 4 parámetros del bbox, debe devolver 422."""
    params = "oeste=-58.53&sur=-34.71&este=-58.33"   # falta norte
    response = client.get(f"/api/v1/mapa/parcelas?{params}")
    assert response.status_code == 422


def test_mapa_parcelas_bbox_oeste_mayor_que_este(client):
    """oeste >= este es inválido geográficamente → 422."""
    params = "oeste=-58.33&sur=-34.71&este=-58.53&norte=-34.52"
    response = client.get(f"/api/v1/mapa/parcelas?{params}")
    assert response.status_code == 422


def test_mapa_parcelas_bbox_sur_mayor_que_norte(client):
    """sur >= norte es inválido geográficamente → 422."""
    params = "oeste=-58.53&sur=-34.52&este=-58.33&norte=-34.71"
    response = client.get(f"/api/v1/mapa/parcelas?{params}")
    assert response.status_code == 422


def test_mapa_parcelas_bbox_oeste_fuera_de_rango(client):
    """oeste=-181 está fuera del rango ge=-180 → 422."""
    params = "oeste=-181&sur=-34.71&este=-58.33&norte=-34.52"
    response = client.get(f"/api/v1/mapa/parcelas?{params}")
    assert response.status_code == 422


# ─── Filtro: rubro ────────────────────────────────────────────────────────────

def test_mapa_parcelas_filtro_rubro(client):
    """Filtrar por rubro no debe romper el endpoint."""
    response = client.get("/api/v1/mapa/parcelas?rubro=cafeteria")
    assert response.status_code == 200


def test_mapa_parcelas_rubro_vacio_invalido(client):
    """rubro='' no cumple min_length=1 → 422."""
    response = client.get("/api/v1/mapa/parcelas?rubro=")
    assert response.status_code == 422


def test_mapa_parcelas_rubro_muy_largo_invalido(client):
    """Un rubro de 121 chars supera max_length=120 → 422."""
    rubro_largo = "A" * 121
    response = client.get(f"/api/v1/mapa/parcelas?rubro={rubro_largo}")
    assert response.status_code == 422


# ─── Paginación: limite y offset ──────────────────────────────────────────────

def test_mapa_parcelas_limite_minimo(client):
    """limite=1 es el mínimo permitido."""
    response = client.get("/api/v1/mapa/parcelas?limite=1")
    assert response.status_code == 200
    data = response.json()
    assert data["limite"] == 1
    assert len(data["features"]) <= 1


def test_mapa_parcelas_limite_maximo(client):
    """limite=20000 es el máximo permitido."""
    response = client.get("/api/v1/mapa/parcelas?limite=20000")
    assert response.status_code == 200


def test_mapa_parcelas_limite_cero_invalido(client):
    """limite=0 está fuera del rango ge=1 → 422."""
    response = client.get("/api/v1/mapa/parcelas?limite=0")
    assert response.status_code == 422


def test_mapa_parcelas_limite_excede_maximo(client):
    """limite=20001 supera le=20000 → 422."""
    response = client.get("/api/v1/mapa/parcelas?limite=20001")
    assert response.status_code == 422


def test_mapa_parcelas_offset_valido(client):
    """Un offset positivo es válido."""
    response = client.get("/api/v1/mapa/parcelas?offset=10")
    assert response.status_code == 200
    data = response.json()
    assert data["offset"] == 10


def test_mapa_parcelas_offset_negativo_invalido(client):
    """offset negativo está fuera del rango ge=0 → 422."""
    response = client.get("/api/v1/mapa/parcelas?offset=-1")
    assert response.status_code == 422


# ─── Estructura de cada feature ───────────────────────────────────────────────

def test_mapa_parcelas_estructura_features(client):
    """
    Si hay features, cada una debe tener los campos del schema ParcelaMapa.
    Usamos limite=5 para no sobrecargar la DB.
    """
    response = client.get("/api/v1/mapa/parcelas?limite=5")
    features = response.json().get("features", [])

    for feature in features:
        assert "smp" in feature, "Falta 'smp' en el feature"
        assert "lat" in feature, "Falta 'lat' en el feature"
        assert "lng" in feature, "Falta 'lng' en el feature"
        assert "total_habilitaciones" in feature, "Falta 'total_habilitaciones'"
        assert "rubros" in feature, "Falta 'rubros' en el feature"
        assert isinstance(feature["rubros"], list)
        assert feature["total_habilitaciones"] >= 0
