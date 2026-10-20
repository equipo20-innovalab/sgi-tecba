from pydantic import BaseModel

class RequisitoResponse(BaseModel):
    id: int
    rubro: str
    tramite: str
    etapa: str | None
    orden: int | None
    obligatorio: str | None
    aplica_cuando: str | None
    documentacion_requerida: str
    organismo: str | None
    link_oficial: str | None
    
    class Config:
        from_attributes = True

class ChecklistResponse(BaseModel):
    rubro: str
    total: int
    requisitos: list[RequisitoResponse]