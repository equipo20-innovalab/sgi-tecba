"""
test_catastro.py — Tests del endpoint GET /api/v1/catastro/{smp}

El SMP (Sección-Manzana-Parcela) identifica inmuebles en CABA.
Formato típico: '001-001-008A'

NOTA: Los tests que verifican datos reales requieren que el dump
      innovalab_dump.sql esté cargado en la DB.
"""


# ─── Tests que no dependen del dump ──────────────────────────────────────────

def test_catastro_smp_inexistente_retorna_404(client):
    """Un SMP que no existe debe devolver 404, no 500."""
    response = client.get("/api/v1/catastro/SMP-QUE-NO-EXISTE")
    assert response.status_code == 404


def test_catastro_smp_vacio_retorna_error(client):
    """Una ruta sin SMP no debe matchear el endpoint de catastro."""
    response = client.get("/api/v1/catastro/")
    # Puede devolver 404 (no existe la ruta) o 405 (método no permitido)
    assert response.status_code in (404, 405, 422)


def test_catastro_smp_muy_largo(client):
    """Un SMP demasiado largo debe devolver 404 (no existe) y no 500."""
    smp_largo = "A" * 200
    response = client.get(f"/api/v1/catastro/{smp_largo}")
    assert response.status_code in (404, 422)


# ─── Tests con datos reales (requieren dump cargado) ─────────────────────────

def test_catastro_smp_ejemplo_responde(client):
    """
    Intenta buscar un SMP de ejemplo.
    Si el dump no está cargado, devuelve 404 — eso es aceptable.
    Si está cargado, la estructura debe ser correcta.
    """
    response = client.get("/api/v1/catastro/001-001-008A")
    assert response.status_code in (200, 404)


def test_catastro_estructura_si_existe(client):
    """Si el SMP existe, la respuesta debe tener los campos del schema CatastroResponse."""
    response = client.get("/api/v1/catastro/001-001-008A")

    if response.status_code == 200:
        data = response.json()
        # Campos obligatorios según CatastroResponse
        assert "smp" in data
        assert data["smp"] == "001-001-008A"
        # Campos opcionales (pueden ser null)
        campos_opcionales = [
            "direccion", "superficie_total", "superficie_cubierta",
            "lat", "lng", "pisos_sobre_rasante", "unidades_funcionales"
        ]
        for campo in campos_opcionales:
            assert campo in data, f"Falta el campo '{campo}' en la respuesta"


def test_catastro_coordenadas_son_numericas(client):
    """Si lat/lng están presentes, deben ser números flotantes válidos."""
    response = client.get("/api/v1/catastro/001-001-008A")

    if response.status_code == 200:
        data = response.json()
        if data.get("lat") is not None:
            assert isinstance(data["lat"], float)
            assert -90 <= data["lat"] <= 90, "Latitud fuera de rango"
        if data.get("lng") is not None:
            assert isinstance(data["lng"], float)
            assert -180 <= data["lng"] <= 180, "Longitud fuera de rango"
