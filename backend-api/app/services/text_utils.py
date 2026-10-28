"""Utilidades de normalización de texto para direcciones, SMP y rubros."""

import re
import unicodedata

TIPOS_CALLE = {
    "AV": "AV",
    "AVDA": "AV",
    "AVENIDA": "AV",
    "CALLE": "CALLE",
    "PJE": "PJE",
    "PASAJE": "PJE",
    "BV": "BV",
    "BLVD": "BV",
    "BOULEVARD": "BV",
}


def sin_acentos(valor: str) -> str:
    """Quita diacríticos sin cambiar el resto del texto."""
    normalizado = unicodedata.normalize("NFKD", valor)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def normalizar_texto(valor: str | None) -> str:
    """Mayúsculas, sin acentos, sin puntuación y con espacios simples."""
    if valor is None:
        return ""
    texto = sin_acentos(str(valor)).upper()
    texto = re.sub(r"[^A-Z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _partes_calle(calle: str | None) -> tuple[str | None, str]:
    tokens = normalizar_texto(calle).split()
    tipo = None
    base: list[str] = []
    for token in tokens:
        if token in TIPOS_CALLE and tipo is None:
            tipo = TIPOS_CALLE[token]
        else:
            base.append(token)
    return tipo, " ".join(base)


def normalizar_calle(calle: str | None) -> str:
    """Normaliza una calle conservando el tipo de vía de forma canónica.

    Ejemplos:
        "CORRIENTES AV." -> "AV CORRIENTES"
        "Av. Corrientes" -> "AV CORRIENTES"
        "SARMIENTO"      -> "SARMIENTO"
        "SARMIENTO AV."  -> "AV SARMIENTO"
    """
    tipo, base = _partes_calle(calle)
    return f"{tipo} {base}".strip() if tipo else base


def calle_base(calle: str | None) -> str:
    """Nombre de calle sin tipo de vía, para búsquedas tolerantes."""
    return _partes_calle(calle)[1]


def normalizar_smp(smp: str | None) -> str:
    """Normaliza el SMP para el join EPOK ↔ Código Urbanístico."""
    return (smp or "").strip().upper()


def clave_rubro(rubro: str | None) -> str:
    """Clave comparable para rubros: sin acentos, mayúsculas y sin puntuación."""
    return normalizar_texto(rubro)
