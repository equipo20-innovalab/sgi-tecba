"""Geocodificación de direcciones CABA.

Estrategia:
1. Índice local `epok_direcciones` (calle + altura).
2. USIG para normalizar y obtener `codigo_calle` + `altura`.
3. EPOK por `codigo_calle` + `altura`.
4. EPOK por coordenadas.
"""

from __future__ import annotations

import re

import httpx
from sqlalchemy.orm import Session

from app.models.codigo_urbanistico import CodigoUrbanistico
from app.models.epok_direccion import EpokDireccion
from app.models.epok_ficha import EpokFicha
from app.schemas.consulta import Ubicacion
from app.services.text_utils import calle_base, normalizar_calle, normalizar_smp

EPOK_PARCELA_URL = "https://epok.buenosaires.gob.ar/catastro/parcela/"


def _num(valor) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _int(valor) -> int | None:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def extraer_calle_altura(direccion: str | None) -> tuple[str | None, int | None]:
    """Separa "Av. Corrientes 2500, CABA" en ("Av. Corrientes", 2500)."""
    if not direccion:
        return None, None
    texto = direccion.strip().rstrip(".")
    match = re.match(r"^(?P<calle>.*?)\s+(?P<altura>\d{1,5})\b", texto)
    if not match:
        return texto or None, None
    calle = match.group("calle").strip(" ,")
    return calle or None, int(match.group("altura"))


def _enriquecer(db: Session | None, ubicacion: Ubicacion) -> Ubicacion:
    if db is None or not ubicacion.smp:
        return ubicacion

    ficha = db.query(EpokFicha).filter(EpokFicha.smp == ubicacion.smp).first()
    if ficha:
        if ubicacion.lat is None:
            ubicacion.lat = ficha.lat
        if ubicacion.lng is None:
            ubicacion.lng = ficha.lng
        if not ubicacion.direccion_normalizada:
            ubicacion.direccion_normalizada = ficha.direccion

    cu = (
        db.query(CodigoUrbanistico)
        .filter(CodigoUrbanistico.smp == normalizar_smp(ubicacion.smp))
        .first()
    )
    if cu:
        ubicacion.barrio = ubicacion.barrio or cu.barrio
        ubicacion.comuna = ubicacion.comuna or cu.comuna

    return ubicacion


def _buscar_direccion_local(
    db: Session | None,
    calle: str | None,
    altura: int | None,
) -> Ubicacion | None:
    if db is None or not calle or not altura:
        return None

    normalizada = normalizar_calle(calle)
    base = calle_base(calle)
    rows = (
        db.query(EpokDireccion)
        .filter(
            EpokDireccion.calle_normalizada == normalizada,
            EpokDireccion.altura == altura,
        )
        .order_by(EpokDireccion.smp)
        .all()
    )
    if not rows:
        rows = (
            db.query(EpokDireccion)
            .filter(
                EpokDireccion.calle_base == base,
                EpokDireccion.altura == altura,
            )
            .order_by(EpokDireccion.smp)
            .all()
        )
    if not rows:
        return None

    principales = [r for r in rows if r.puerta_principal] or rows
    elegida = principales[0]
    candidatos = [
        {
            "smp": r.smp,
            "calle": r.calle,
            "altura": r.altura,
            "codigo_calle": r.codigo_calle,
            "puerta_principal": r.puerta_principal,
        }
        for r in rows
    ]
    return _enriquecer(
        db,
        Ubicacion(
            direccion_original=calle,
            direccion_normalizada=f"{elegida.calle} {elegida.altura}, CABA",
            smp=elegida.smp,
            calle=elegida.calle,
            altura=elegida.altura,
            candidatos=candidatos,
        ),
    )


def _ubicacion_desde_ficha(
    db: Session | None,
    ficha: dict,
    direccion_original: str | None = None,
    direccion_normalizada: str | None = None,
    calle: str | None = None,
    altura: int | None = None,
) -> Ubicacion:
    centroide = ficha.get("centroide") or [None, None]
    return _enriquecer(
        db,
        Ubicacion(
            direccion_original=direccion_original,
            direccion_normalizada=direccion_normalizada or ficha.get("direccion"),
            smp=ficha.get("smp"),
            calle=calle,
            altura=altura,
            lat=_num(centroide[1]) if len(centroide) > 1 else None,
            lng=_num(centroide[0]) if len(centroide) > 0 else None,
        ),
    )


def geocodificar(direccion: str | None, db: Session | None = None) -> Ubicacion:
    """Convierte una dirección en una ubicación con SMP cuando es posible."""
    if not direccion:
        return Ubicacion()

    calle, altura = extraer_calle_altura(direccion)

    local = _buscar_direccion_local(db, calle, altura)
    if local:
        local.direccion_original = direccion
        return local

    usig = _geocodificar_usig(direccion)
    if usig:
        codigo_calle = usig.get("codigo_calle")
        altura_usig = usig.get("altura")
        if db is not None and codigo_calle and altura_usig:
            fila = (
                db.query(EpokDireccion)
                .filter(
                    EpokDireccion.codigo_calle == int(codigo_calle),
                    EpokDireccion.altura == int(altura_usig),
                )
                .order_by(EpokDireccion.smp)
                .first()
            )
            if fila:
                return _enriquecer(
                    db,
                    Ubicacion(
                        direccion_original=direccion,
                        direccion_normalizada=usig.get("direccion")
                        or f"{fila.calle} {fila.altura}, CABA",
                        smp=fila.smp,
                        calle=fila.calle,
                        altura=fila.altura,
                        candidatos=[],
                    ),
                )

        if codigo_calle and altura_usig:
            ficha = obtener_ficha_epok_por_codigo_calle(
                int(codigo_calle), int(altura_usig)
            )
            if ficha:
                return _ubicacion_desde_ficha(
                    db,
                    ficha,
                    direccion_original=direccion,
                    direccion_normalizada=usig.get("direccion"),
                    calle=calle,
                    altura=int(altura_usig),
                )

        if usig.get("lat") and usig.get("lng"):
            ficha = obtener_ficha_epok_por_coordenadas(usig["lat"], usig["lng"])
            if ficha:
                return _ubicacion_desde_ficha(
                    db,
                    ficha,
                    direccion_original=direccion,
                    direccion_normalizada=usig.get("direccion"),
                    calle=calle,
                    altura=altura,
                )

    return Ubicacion(
        direccion_original=direccion,
        direccion_normalizada=direccion,
        calle=calle,
        altura=altura,
    )


def _geocodificar_usig(direccion: str) -> dict | None:
    """Normaliza con USIG. Devuelve None si el servicio falla o no encuentra."""
    url = "http://servicios.usig.buenosaires.gob.ar/normalizar/"
    params = {"direccion": direccion, "geocodificar": "true", "maxOptions": 1}
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except Exception:
        return None

    direcciones = data.get("direccionesNormalizadas") or []
    if not direcciones:
        return None

    d = direcciones[0]
    coords = d.get("coordenadas") or {}
    return {
        "direccion": d.get("direccion"),
        "lat": _num(coords.get("y")),
        "lng": _num(coords.get("x")),
        "comuna": _int(d.get("comuna")),
        "codigo_calle": _int(d.get("cod_calle") or d.get("codigo_calle")),
        "altura": _int(d.get("altura")),
    }


def obtener_ficha_epok_por_coordenadas(lat: float, lng: float) -> dict | None:
    """Devuelve la ficha EPOK de la parcela que contiene el punto (lat, lng)."""
    if lat is None or lng is None:
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(EPOK_PARCELA_URL, params={"lng": lng, "lat": lat})
            response.raise_for_status()
            data = response.json()
        return data if data.get("smp") else None
    except Exception as e:
        print(f"Error consultando EPOK por coordenadas: {e}")
        return None


def obtener_ficha_epok_por_codigo_calle(codigo_calle: int, altura: int) -> dict | None:
    """Devuelve la ficha EPOK para un código de calle y altura."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                EPOK_PARCELA_URL,
                params={"codigo_calle": codigo_calle, "altura": altura},
            )
            response.raise_for_status()
            data = response.json()
        return data if data.get("smp") else None
    except Exception as e:
        print(f"Error consultando EPOK por código de calle: {e}")
        return None


def obtener_smp_por_coordenadas(lat: float, lng: float) -> str | None:
    """Busca el SMP en la API de EPOK usando lat/lng."""
    ficha = obtener_ficha_epok_por_coordenadas(lat, lng)
    return ficha.get("smp") if ficha else None


def obtener_ficha_epok_por_smp(smp: str | None) -> dict | None:
    """Devuelve la ficha EPOK completa de un SMP (incluye superficies)."""
    if not smp:
        return None
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(EPOK_PARCELA_URL, params={"smp": smp})
            response.raise_for_status()
            data = response.json()
        return data if data.get("smp") else None
    except Exception as e:
        print(f"Error consultando EPOK por SMP: {e}")
        return None
