from pydantic import BaseModel


class ParcelaMapa(BaseModel):
    smp: str
    lat: float
    lng: float
    direccion: str | None
    total_habilitaciones: int
    rubros: list[str]


class ParcelasMapaResponse(BaseModel):
    total: int
    limite: int
    offset: int
    features: list[ParcelaMapa]
