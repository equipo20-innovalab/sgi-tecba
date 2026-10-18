"""
Orquestador del endpoint /consulta.
Flujo: texto → actividad + dirección → geocoding → 3 fuentes → respuesta.
"""
from sqlalchemy.orm import Session
from app.schemas.consulta import (
    ConsultaRequest, ConsultaResponse, FuenteUsada,
)
from app.services.extraccion_service import extraer_actividad, extraer_direccion
from app.services.geocoding_service import geocodificar
from app.services.fuentes_service import (
    obtener_requisitos,
    obtener_competencia_cercana,
    obtener_ficha_catastral,
    obtener_contexto_territorial,
    construir_camino_feliz,
)


# Fuentes fijas del MVP (trazabilidad)
FUENTES_MVP = [
    FuenteUsada(
        nombre="BA Data - Padrón de habilitaciones",
        tipo="padron",
        url="https://data.buenosaires.gob.ar/dataset/habilitaciones-aprobadas",
    ),
    FuenteUsada(
        nombre="EPOK - Catastro GCBA",
        tipo="catastro",
        url="https://epok.buenosaires.gob.ar/catastro/",
    ),
    FuenteUsada(
        nombre="Checklist TECBA (curado)",
        tipo="curado",
    ),
]


def procesar_consulta(db: Session, req: ConsultaRequest) -> ConsultaResponse:
    """Flujo completo del endpoint."""
    # PRIORIDAD AL MODO ESTRUCTURADO
    if req.rubro and req.direccion:
        actividad = req.rubro
        direccion = req.direccion
        tiene_altura = True
    elif req.texto:
        actividad = extraer_actividad(req.texto)
        direccion, tiene_altura = extraer_direccion(req.texto)
    else:
        # Fallback
        actividad = None
        direccion = None
        tiene_altura = False

    # 2. Geocodificación
    if direccion and tiene_altura:
        ubicacion = geocodificar(direccion)
    else:
        # No geocodificamos si no hay altura → no adivinamos
        from app.schemas.consulta import Ubicacion
        ubicacion = Ubicacion(direccion_original=direccion)

    # 3. Consultar las 3 fuentes
    requisitos = obtener_requisitos(db, actividad)
    competencia = obtener_competencia_cercana(db, actividad, ubicacion.comuna)
    ficha = obtener_ficha_catastral(db, ubicacion.smp)
    contexto = obtener_contexto_territorial(db, ubicacion.comuna)

    # 4. Camino feliz
    pasos = construir_camino_feliz(requisitos)

    # 5. Mensaje si falta info (caso 3 de QA)
    mensaje = None
    if not actividad:
        mensaje = (
            "No pude identificar la actividad. "
            "¿Podés especificar qué rubro querés abrir? (ej: cafetería, pizzería)"
        )
    elif not direccion:
        mensaje = (
            "No pude identificar la dirección. "
            "¿Podés especificar dónde querés abrir el local?"
        )
    elif not tiene_altura:
        mensaje = (
            f"Encontré la calle '{direccion}' pero me falta la altura. "
            "¿Podés especificar el número o la esquina más cercana?"
        )

    return ConsultaResponse(
        actividad_detectada=actividad,
        ubicacion=ubicacion,
        requisitos=requisitos,
        competencia_cercana=competencia,
        ficha_catastral=ficha,
        contexto_territorial=contexto,
        pasos_sugeridos=pasos,
        respuesta_ia=None,  # TODO: Sprint 5-6
        fuentes=FUENTES_MVP,
        mensaje=mensaje,
    )