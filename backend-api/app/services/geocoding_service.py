"""
Geocodificación de direcciones CABA.
- Mock para el caso piloto (Corrientes 2500)
- USIG real con timeout corto (fallback a None si falla)
"""
import httpx
from app.schemas.consulta import Ubicacion


# Mock para las direcciones del caso piloto
MOCK_GEOCODING: dict[str, dict] = {
    "corrientes 2500": {
        "lat": -34.6042,
        "lng": -58.4037,
        "comuna": 3,
        "direccion": "Av. Corrientes 2500, CABA",
    },
}


def geocodificar(direccion: str | None) -> Ubicacion:
    """
    Convierte una dirección a coordenadas.
    Estrategia:
    1. Mock (rápido, para el caso piloto)
    2. USIG real (timeout 5s, fallback a None)
    """
    if not direccion:
        return Ubicacion()

    dir_lower = direccion.lower().strip()

    # 1. Mock para el caso piloto
    for key, coords in MOCK_GEOCODING.items():
        if key in dir_lower:
            return Ubicacion(
                direccion_original=direccion,
                direccion_normalizada=coords["direccion"],
                lat=coords["lat"],
                lng=coords["lng"],
                comuna=coords["comuna"],
            )

    # 2. USIG real
    try:
        return _geocodificar_usig(direccion)
    except Exception:
        # Fallback: solo la dirección original sin coords
        return Ubicacion(direccion_original=direccion)


def _geocodificar_usig(direccion: str) -> Ubicacion:
    """
    Llama a USIG normalizar para geocodificar.
    Doc: http://servicios.usig.buenosaires.gob.ar/normalizar
    """
    url = "http://servicios.usig.buenosaires.gob.ar/normalizar/"
    params = {
        "direccion": direccion,
        "geocodificar": "true",
        "maxOptions": 1,
    }
    with httpx.Client(timeout=5.0) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    # USIG devuelve { "normalizado": "...", "direccionesNormalizadas": [ { "coordenadas": {"x":..,"y":..}, ... } ] }
    direcciones = data.get("direccionesNormalizadas") or []
    if not direcciones:
        return Ubicacion(direccion_original=direccion)

    d = direcciones[0]
    coords = d.get("coordenadas") or {}
    lat = coords.get("y")
    lng = coords.get("x")

    return Ubicacion(
        direccion_original=direccion,
        direccion_normalizada=d.get("direccion"),
        lat=float(lat) if lat else None,
        lng=float(lng) if lng else None,
        comuna=d.get("comuna"),  # puede o no venir
    )