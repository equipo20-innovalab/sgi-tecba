from datetime import date
from pydantic import BaseModel, Field


class Zonificacion(BaseModel):
    """Zonificación y parámetros del Código Urbanístico para un SMP."""

    smp: str
    barrio: str | None = None
    comuna: int | None = None

    zona: str | None = None
    zona_fuente: str | None = None
    distrito_especial: str | None = None
    zona_secundaria: str | None = None

    grado_mixtura: int | None = None
    grado_mixtura_label: str | None = None
    usos: list[int] = Field(default_factory=list)

    edificabilidad: float | None = None
    edificabilidad_unidad: str = "no documentada"
    fot: float | None = None

    catalogado: bool | None = None
    tipo_manzana: str | None = None
    restricciones: list[str] = Field(default_factory=list)

    actividad_permitida: str = "A verificar"
    motivo_actividad: str = (
        "El Código Urbanístico define el grado de mixtura del suelo; "
        "la habilitación concreta del rubro requiere el Cuadro de Usos del "
        "Suelo N° 3.3 y la normativa complementaria."
    )

    fuente: str
    fuente_fecha: date | None = None
