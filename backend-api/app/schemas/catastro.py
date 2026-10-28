from pydantic import BaseModel
from app.schemas.urbanismo import Zonificacion


class CatastroResponse(BaseModel):
    smp: str
    direccion: str | None
    superficie_total: float | None
    superficie_cubierta: float | None
    lat: float | None
    lng: float | None
    pisos_sobre_rasante: int | None
    unidades_funcionales: int | None
    barrio: str | None = None
    comuna: int | None = None
    zonificacion: Zonificacion | None = None

    class Config:
        from_attributes = True
