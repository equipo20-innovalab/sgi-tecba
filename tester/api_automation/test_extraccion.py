"""
test_extraccion.py — Tests automatizados para el Módulo 1 (Entendimiento del Lenguaje y Extracción).

Cubre los casos de prueba del Plan de QA:
- CP-01: Extracción en consulta formal.
- CP-02: Manejo de lenguaje informal, sinónimos y modismos.
- CP-03: Consulta con ubicación incompleta o sin altura (no adivina coordenadas).
- CP-04: Consulta con esquinas o cruces de calles.
- CP-10: Extracción de identificador catastral SMP.
"""
from app.services.extraccion_service import (
    extraer_actividad,
    extraer_direccion,
    extraer_smp,
)


# ─── CP-01: Consulta Formal ───────────────────────────────────────────────────

def test_cp01_extraccion_consulta_formal():
    """Valida la extracción precisa de actividad y dirección formal."""
    texto = "Quiero abrir una cafetería en Av. Corrientes 2500. ¿Qué tengo que hacer?"
    actividad = extraer_actividad(texto)
    direccion, tiene_altura = extraer_direccion(texto)

    assert actividad == "Cafetería"
    assert "Corrientes" in direccion
    assert "2500" in direccion
    assert tiene_altura is True


# ─── CP-02: Lenguaje Informal, Sinónimos y Modismos ───────────────────────────

def test_cp02_lenguaje_informal_cafe():
    """Términos informales como 'un café' deben normalizarse al rubro Cafetería."""
    texto = "Quiero poner un café en Corrientes 2500"
    actividad = extraer_actividad(texto)
    direccion, tiene_altura = extraer_direccion(texto)

    assert actividad == "Cafetería"
    assert "Corrientes" in direccion
    assert "2500" in direccion
    assert tiene_altura is True


def test_cp02_expendio_cafe_y_medialunas():
    """Frases complejas con 'café y medialunas' deben mapear al rubro Cafetería."""
    texto = "Necesito habilitar un local de expendio de café y medialunas en Av. Corrientes 2500"
    actividad = extraer_actividad(texto)
    direccion, tiene_altura = extraer_direccion(texto)

    assert actividad == "Cafetería"
    assert "Corrientes" in direccion
    assert "2500" in direccion
    assert tiene_altura is True


def test_cp02_variantes_gastronomicas_pizzeria():
    """Variantes como 'pizza' o 'pizzería' deben mapear a Pizzería."""
    assert extraer_actividad("abrir una pizzería") == "Pizzería"
    assert extraer_actividad("local de pizza al paso") == "Pizzería"


def test_cp02_actividad_no_registrada_retorna_none():
    """Un rubro que no figure en los sinónimos debe retornar None y no inventar."""
    assert extraer_actividad("quiero abrir una ferretería industrial") is None


# ─── CP-03: Ubicación Incompleta o Sin Altura ──────────────────────────────────

def test_cp03_ubicacion_sin_altura_no_adivina():
    """
    Regla de seguridad: Si el usuario no indica altura catastral,
    tiene_altura debe ser False para evitar geocodificar arbitrariamente.
    """
    texto = "Quiero abrir una cafetería sobre la calle Corrientes."
    direccion, tiene_altura = extraer_direccion(texto)

    assert "Corrientes" in direccion
    assert tiene_altura is False, "El sistema nunca debe asumir una altura si no fue dada."


# ─── CP-04: Esquinas o Cruces de Calles ───────────────────────────────────────

def test_cp04_consulta_con_esquina():
    """Identifica intersecciones de calles ('calle1 y calle2')."""
    texto = "Quiero poner un local en la esquina de Av. Corrientes y Pueyrredón"
    direccion, tiene_altura = extraer_direccion(texto)

    assert direccion is not None
    assert "Corrientes" in direccion
    assert "Pueyrredón" in direccion or "Pueyrredon" in direccion
    assert tiene_altura is True


# ─── CP-10: Nomenclatura Catastral SMP ────────────────────────────────────────

def test_cp10_extraccion_codigo_smp_valido():
    """Extrae códigos SMP en formato Sección-Manzana-Parcela."""
    assert extraer_smp("Consulta para el inmueble 001-001-008A") == "001-001-008A"
    assert extraer_smp("SMP: 015-023-010B en Comuna 4") == "015-023-010B"
    assert extraer_smp("parcela 03-012-005") == "03-012-005"


def test_cp10_texto_sin_smp_retorna_none():
    """Si no hay código SMP en el texto, devuelve None."""
    assert extraer_smp("Quiero abrir un local en Palermo") is None
