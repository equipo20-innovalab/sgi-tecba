"""
Orquestador del endpoint /consulta.
Flujo: texto → actividad + dirección → geocoding → 3 fuentes → respuesta.
"""

from sqlalchemy.orm import Session
from app.schemas.consulta import (
    ConsultaRequest,
    ConsultaResponse,
    FichaCatastral,
    FuenteUsada,
    Ubicacion,
)
from app.services.extraccion_service import extraer_actividad, extraer_direccion
from app.services.geocoding_service import (
    geocodificar,
    obtener_ficha_epok_por_smp,
    obtener_smp_por_coordenadas,
)
from app.services.fuentes_service import (
    obtener_requisitos,
    obtener_competencia_cercana,
    obtener_ficha_catastral,
    obtener_contexto_territorial,
    construir_camino_feliz,
)
from app.services.urbanismo_service import obtener_zonificacion

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


def _formatear_m2(valor: float | None) -> str:
    return "No disponible" if valor is None else f"{valor:g} m²"


def _ficha_desde_epok(data: dict | None) -> FichaCatastral | None:
    if not data or not data.get("smp"):
        return None
    centroide = data.get("centroide") or [None, None]
    return FichaCatastral(
        smp=data["smp"],
        direccion=data.get("direccion"),
        superficie_total=_num(data.get("superficie_total")),
        superficie_cubierta=_num(data.get("superficie_cubierta")),
        pisos_sobre_rasante=_int(data.get("pisos_sobre_rasante")),
        unidades_funcionales=_int(data.get("unidades_funcionales")),
        lat=_num(centroide[1]) if len(centroide) > 1 else None,
        lng=_num(centroide[0]) if len(centroide) > 0 else None,
    )


def procesar_consulta(db: Session, req: ConsultaRequest) -> ConsultaResponse:
    """Flujo completo del endpoint."""
    # 1. Prioridad al modo estructurado
    if req.rubro and req.direccion:
        actividad = req.rubro
        direccion = req.direccion
        tiene_altura = True
    elif req.texto:
        actividad = extraer_actividad(req.texto)
        direccion, tiene_altura = extraer_direccion(req.texto)
    else:
        actividad = None
        direccion = None
        tiene_altura = False

    # 2. Geocodificación
    if direccion and tiene_altura:
        ubicacion = geocodificar(direccion, db)
    else:
        ubicacion = Ubicacion(direccion_original=direccion)
    if ubicacion.lat and ubicacion.lng and not ubicacion.smp:
        smp = obtener_smp_por_coordenadas(ubicacion.lat, ubicacion.lng)
        if smp:
            ubicacion.smp = smp

    # 3. Consultar las 3 fuentes
    requisitos = obtener_requisitos(db, actividad)
    competencia = obtener_competencia_cercana(db, actividad, ubicacion.comuna)

    # Ahora ficha se va a buscar con el SMP encontrado
    ficha = obtener_ficha_catastral(db, ubicacion.smp)
    if ficha is None and ubicacion.smp:
        ficha = _ficha_desde_epok(obtener_ficha_epok_por_smp(ubicacion.smp))

    zonificacion = obtener_zonificacion(db, ubicacion.smp)
    if zonificacion:
        ubicacion.barrio = ubicacion.barrio or zonificacion.barrio
        ubicacion.comuna = ubicacion.comuna or zonificacion.comuna

    contexto = obtener_contexto_territorial(db, ubicacion.comuna)

    # 4. Camino feliz
    pasos = construir_camino_feliz(requisitos)

    # 5. Mensaje si falta info
    mensaje = None
    if not actividad:
        mensaje = (
            "No pude identificar la actividad. ¿Podés especificar qué rubro "
            "querés abrir? (ej: cafetería, pizzería)"
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
    elif len(ubicacion.candidatos) > 1:
        mensaje = (
            "La dirección coincide con más de una parcela. "
            f"Se usó {ubicacion.smp}; revisá los candidatos si necesitás precisión."
        )

    # 6. Mapeo para el Frontend
    land_area = _formatear_m2(ficha.superficie_total if ficha else None)
    covered_area = _formatear_m2(ficha.superficie_cubierta if ficha else None)

    obs_texto = f"Se encontraron {len(requisitos)} requisitos."
    if ubicacion.comuna:
        obs_texto += f" Comuna {ubicacion.comuna}."
    if zonificacion and zonificacion.zona:
        obs_texto += f" Zona {zonificacion.zona}."
    if contexto and contexto.total_habilitaciones:
        obs_texto += f" ({contexto.total_habilitaciones} habilitaciones en la zona)."

    if zonificacion and zonificacion.edificabilidad:
        max_height = (
            f"{zonificacion.edificabilidad:g} "
            "(edificabilidad; unidad no documentada)"
        )
    else:
        max_height = "A verificar"

    return ConsultaResponse(
        # Campos originales
        actividad_detectada=actividad,
        ubicacion=ubicacion,
        requisitos=requisitos,
        competencia_cercana=competencia,
        ficha_catastral=ficha,
        zonificacion=zonificacion,
        contexto_territorial=contexto,
        pasos_sugeridos=pasos,
        respuesta_ia=None,
        fuentes=FUENTES_MVP,
        mensaje=mensaje,
        # Mapeo para el Frontend
        address=(
            ubicacion.direccion_normalizada
            if ubicacion.direccion_normalizada
            else "Dirección no detectada"
        ),
        district=(
            zonificacion.zona if zonificacion and zonificacion.zona else "No disponible"
        ),
        landArea=land_area,
        coveredArea=covered_area,
        maxHeight=max_height,
        viabilityStatus="A verificar",
        activity=actividad if actividad else "No detectada",
        observaciones=obs_texto,
        rawData={
            "lat": ubicacion.lat,
            "lng": ubicacion.lng,
            "smp": ubicacion.smp,
            "zonificacion": zonificacion.model_dump() if zonificacion else None,
            "requisitos": [r.model_dump() for r in requisitos],
        },
    )
