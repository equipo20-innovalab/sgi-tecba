"""
Extracción de actividad (rubro) y dirección desde texto natural.
Sprint 5-6: reemplazar por LLM/embeddings para mayor precisión.
"""
import re


# Mapeo de sinónimos → rubro en la BD
# Ampliar cuando se agreguen más rubros
RUBROS_MAP: dict[str, list[str]] = {
    "Cafetería": [
        "cafetería", "cafeteria", "café", "cafe",
        "confitería", "confiteria", "bar", "cafetero",
    ],
    "Pizzería": [
        "pizzería", "pizzeria", "pizza",
    ],
    # Futuros rubros (para cuando escalen)
    # "Restaurante": ["restaurante", "resto", "parrilla"],
}


def extraer_actividad(texto: str) -> str | None:
    """
    Detecta el rubro/actividad mencionada en el texto.
    Devuelve el nombre canónico (ej: "Cafetería") o None.
    """
    texto_lower = texto.lower()
    for rubro, sinonimos in RUBROS_MAP.items():
        if any(s in texto_lower for s in sinonimos):
            return rubro
    return None


def extraer_smp(texto: str) -> str | None:
    """Detecta un identificador catastral explícito en formato sección-manzana-parcela."""
    match = re.search(r"\b(\d{1,3}-\d{1,3}-\d{1,4}[A-Za-z]?)\b", texto)
    return match.group(1).upper() if match else None


def extraer_direccion(texto: str) -> tuple[str | None, bool]:
    """
    Extrae la dirección del texto.
    
    Devuelve:
        (direccion, tiene_altura)
        - direccion: string con la dirección o None
        - tiene_altura: True si tiene número de altura
    
    Ejemplos:
        "en Av. Corrientes 2500"           → ("Av. Corrientes 2500", True)
        "sobre la calle Corrientes"         → ("Corrientes", False)
        "esquina de Av. Corrientes y Pueyrredón" → ("Av. Corrientes y Pueyrredón", True)
    """
    # 1. Patrón calle + altura: "en/sobre/por <calle> <numero>"
    patron_altura = (
        r"(?:en|sobre|por|calle|avenida|av\.?|avda\.?)\s+"
        r"([A-ZÁÉÍÓÚÑ][\w\s\.]+?)\s+(\d{3,5})\b"
    )
    match = re.search(patron_altura, texto, re.IGNORECASE)
    if match:
        return f"{match.group(1).strip()} {match.group(2)}", True

    # 2. Patrón esquina: "<calle1> y <calle2>"
    patron_esquina = (
        r"(?:esquina\s+de\s+|en\s+|sobre\s+)?"
        r"([A-ZÁÉÍÓÚÑ][\w\s\.]+?)\s+y\s+([A-ZÁÉÍÓÚÑ][\w\s\.]+)"
    )
    match = re.search(patron_esquina, texto, re.IGNORECASE)
    if match:
        # Limpiar la segunda calle por si agarra palabras siguientes
        calle1 = match.group(1).strip()
        calle2 = match.group(2).strip().split()[0]  # solo la primera palabra
        return f"{calle1} y {calle2}", True

    # 3. Patrón calle sin altura: "sobre la calle <nombre>"
    patron_sin_altura = (
        r"(?:sobre|en|por|calle|avenida|av\.?|avda\.?)\s+"
        r"(?:la\s+)?(?:calle\s+)?([A-ZÁÉÍÓÚÑ][\w\s\.]+?)(?:\.|,|$|\s+de\s+|\s+para\s+)"
    )
    match = re.search(patron_sin_altura, texto, re.IGNORECASE)
    if match:
        calle = match.group(1).strip()
        if len(calle) > 3:  # evitar falsos positivos cortos
            return calle, False

    # 4. Fallback: "<calle> <altura>" sin preposición (ej: "Suipacha 384")
    patron_desnudo = (
        r"(?<![\w-])"
        r"([A-ZÁÉÍÓÚÑ][\w\.]+(?:\s+[A-ZÁÉÍÓÚÑ][\w\.]+){0,2})\s+"
        r"(\d{3,5})(?!\s*[-/])"
    )
    match = re.search(patron_desnudo, texto, re.IGNORECASE)
    if match:
        candidato = match.group(1).strip()
        if candidato.lower() not in {"smp", "comuna"}:
            return f"{candidato} {match.group(2)}", True

    return None, False