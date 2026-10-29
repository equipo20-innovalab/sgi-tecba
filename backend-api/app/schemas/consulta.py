from pydantic import BaseModel, Field, model_validator
from typing import Any, Optional


class ConsultaRequest(BaseModel):
    # Modo 1: Lenguaje natural
    texto: Optional[str] = Field(None, description="Ej: 'Quiero abrir una cafetería en Av. Corrientes 2500'")
    
    # Modo 2: Estructurado 
    rubro: Optional[str] = Field(None, description="Ej: 'Cafetería'")
    direccion: Optional[str] = Field(None, description="Ej: 'Av. Corrientes 2500'")
    
    sesion_id: Optional[str] = None

    @model_validator(mode='after')
    def validar_inputs(self):
        if not self.texto and not (self.rubro and self.direccion):
            raise ValueError("Enviar 'texto' o la combinación de 'rubro' y 'direccion'")
        return self


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


class HabilitacionParcela(BaseModel):
    solicitud: Optional[int] = None
    tipo_tramite: Optional[str] = None
    tipo_expediente: Optional[str] = None
    subtipo_expediente: Optional[str] = None
    fecha_habilitacion: Optional[str] = None
    fecha_fuente: Optional[str] = None
    numero_expediente: Optional[str] = None
    codigo_rubro: Optional[float] = None
    smp: str
    smp_fuente: Optional[str] = None
    seccion: Optional[str]
    manzana: Optional[str]
    parcela: Optional[str]
    calles: Optional[str]
    comuna: Optional[int]
    comuna_fuente: Optional[str] = None
    descripcion_rubro: Optional[str]
    anio: Optional[int]
    superficie: Optional[float]
    razon_social: Optional[str] = None
    partida_matriz: Optional[str] = None
    origen: Optional[str] = None


class FichaCatastral(BaseModel):
    smp: str
    direccion: Optional[str]
    superficie_total: Optional[float]
    superficie_cubierta: Optional[float]
    pisos_sobre_rasante: Optional[int]
    unidades_funcionales: Optional[int]
    lat: Optional[float]
    lng: Optional[float]
    ficha: Optional[dict[str, Any]] = None
    puertas: Optional[Any] = None


class ContextoTerritorial(BaseModel):
    comuna: Optional[int]
    total_habilitaciones: int
    rubros_top: list[dict]


class CoberturaCampo(BaseModel):
    registros_con_dato: int
    registros_sin_dato: int
    cobertura: float
    expectativa_minima: Optional[float] = None
    cumple_expectativa: Optional[bool] = None
    fuentes: dict[str, int] = Field(default_factory=dict)


class CoberturaDatos(BaseModel):
    total_registros: int
    campos: dict[str, CoberturaCampo]


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
    habilitaciones_parcela: list[HabilitacionParcela] = Field(default_factory=list)
    ficha_catastral: Optional[FichaCatastral]
    codigo_urbanistico: Optional[dict[str, Any]] = None
    contexto_territorial: Optional[ContextoTerritorial]
    cobertura_datos: Optional[CoberturaDatos] = None
    pasos_sugeridos: list[str]
    respuesta_ia: Optional[str] = None      # TODO: Sprint 5-6
    fuentes: list[FuenteUsada]
    mensaje: Optional[str] = None           # aclaraciones si algo no se detectó