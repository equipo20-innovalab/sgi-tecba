from pydantic import BaseModel

class ConteoPorComuna(BaseModel):
    comuna: int
    total_habilitaciones: int

class RubroConteo(BaseModel):
    rubro: str
    total: int