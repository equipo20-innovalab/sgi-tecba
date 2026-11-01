"""
Geocodificación de direcciones CABA.

Estrategia (en orden):
1. Mock del caso piloto (Corrientes 2500): rápido y determinístico.
2. Catastro local (tabla epok_fichas): direcciones reales con lat/lng.
3. USIG real (timeout corto; fallback a ubicación sin coordenadas).
"""
import re
import unicodedata

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

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

# Palabras que no aportan al nombre de la calle
_STOPWORDS = {
    "av", "avenida", "calle", "gral", "general", "dr", "doctor", "dra", "doctora",
    "pje", "pasaje", "de", "del", "la", "las", "los", "el", "y",
}


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", _sin_acentos(texto).lower()).strip()


def _parsear_direccion(direccion: str) -> tuple[list[str], int | None]:
    """Devuelve (tokens significativos de la calle, altura)."""
    normalizada = _normalizar(direccion)
    numero = None
    coincidencia = re.search(r"(\d+)\s*$", normalizada)
    calle = normalizada
    if coincidencia:
        numero = int(coincidencia.group(1))
        calle = normalizada[: coincidencia.start()].strip()
    tokens = [
        t for t in re.findall(r"[a-z]+", calle) if t not in _STOPWORDS and len(t) >= 3
    ]
    return tokens, numero


def _altura_de(direccion: str) -> int | None:
    coincidencia = re.search(r"(\d+)\s*$", _normalizar(direccion))
    return int(coincidencia.group(1)) if coincidencia else None


def _geocodificar_catastro(db: Session, direccion: str) -> Ubicacion | None:
    """Busca la dirección en epok_fichas (catastro local) y devuelve lat/lng + SMP."""
    tokens, altura = _parsear_direccion(direccion)
    if not tokens:
        return None

    # El token más largo suele ser el más distintivo del nombre de la calle
    token = max(tokens, key=len)
    filas = db.execute(
        text(
            """
            SELECT direccion, smp, lat, lng
            FROM epok_fichas
            WHERE direccion ILIKE :patron
              AND lat IS NOT NULL
              AND lng IS NOT NULL
            LIMIT 500
            """
        ),
        {"patron": f"%{token}%"},
    ).mappings().all()
    if not filas:
        return None

    def puntaje(fila):
        dir_norm = _normalizar(fila["direccion"])
        tokens_presentes = sum(1 for t in tokens if t in dir_norm)
        altura_fila = _altura_de(fila["direccion"])
        if altura is not None and altura_fila is not None:
            distancia = abs(altura_fila - altura)
        else:
            distancia = 10**9
        return (-tokens_presentes, distancia)

    mejor = min(filas, key=puntaje)
    dir_mejor = _normalizar(mejor["direccion"])
    if not any(t in dir_mejor for t in tokens):
        return None

    comuna = db.execute(
        text(
            "SELECT comuna FROM habilitaciones "
            "WHERE smp = :smp AND comuna IS NOT NULL LIMIT 1"
        ),
        {"smp": mejor["smp"]},
    ).scalar()

    return Ubicacion(
        direccion_original=direccion,
        direccion_normalizada=f"{mejor['direccion']}, CABA",
        lat=float(mejor["lat"]),
        lng=float(mejor["lng"]),
        comuna=comuna,
        smp=mejor["smp"],
    )


def geocodificar(direccion: str | None, db: Session | None = None) -> Ubicacion:
    """
    Convierte una dirección a coordenadas.
    Estrategia:
    1. Mock (rápido, para el caso piloto)
    2. Catastro local (epok_fichas) con direcciones reales de CABA
    3. USIG real (timeout 5s, fallback a None)
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

    # 2. Catastro local (datos reales cargados desde el dump)
    if db is not None:
        try:
            ubicacion_catastro = _geocodificar_catastro(db, direccion)
        except Exception:
            db.rollback()
            ubicacion_catastro = None
        if ubicacion_catastro is not None and ubicacion_catastro.lat is not None:
            return ubicacion_catastro

    # 3. USIG real
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
