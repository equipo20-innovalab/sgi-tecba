from pydantic import BaseModel, Field
from typing import Optional


class ConsultaRequest(BaseModel):
    """Consulta en lenguaje natural del usuario."""
    texto: str = Field(..., min_length=3, description="Ej: 'Quiero abrir una cafetería en Av. Corrientes 2500'")
    sesion_id: Optional[str] = Field(None, description="Para preguntas de seguimiento")


class Ubicacion(BaseModel):
    direccion_original: Optional[str] = None
    direccion_normalizada: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    comuna: Optional[int] = None
    smp: Optional[str] = None


class RequisitoItem(BaseModel):
    etapa: Optional[str]
    orden: Optional[int]
    tramite: str
    obligatorio: Optional[str]
    aplica_cuando: Optional[str]
    documentacion_requerida: str
    organismo: Optional[str]
    link_oficial: Optional[str]


class CompetenciaItem(BaseModel):
    descripcion_rubro: Optional[str]
    calles: Optional[str]
    comuna: Optional[int]
    anio: Optional[int]
    superficie: Optional[float]


class FichaCatastral(BaseModel):
    smp: str
    direccion: Optional[str]
    superficie_total: Optional[float]
    superficie_cubierta: Optional[float]
    pisos_sobre_rasante: Optional[int]
    unidades_funcionales: Optional[int]
    lat: Optional[float]
    lng: Optional[float]


class ContextoTerritorial(BaseModel):
    comuna: Optional[int]
    total_habilitaciones: int
    rubros_top: list[dict]


class FuenteUsada(BaseModel):
    nombre: str
    tipo: str          # "padron" | "catastro" | "curado"
    url: Optional[str] = None
    fecha_actualizacion: Optional[str] = None


class ConsultaResponse(BaseModel):
    actividad_detectada: Optional[str]
    ubicacion: Ubicacion
    requisitos: list[RequisitoItem]
    competencia_cercana: list[CompetenciaItem]
    ficha_catastral: Optional[FichaCatastral]
    contexto_territorial: Optional[ContextoTerritorial]
    pasos_sugeridos: list[str]
    respuesta_ia: Optional[str] = None      # TODO: Sprint 5-6
    fuentes: list[FuenteUsada]
    mensaje: Optional[str] = None           # aclaraciones si algo no se detectó