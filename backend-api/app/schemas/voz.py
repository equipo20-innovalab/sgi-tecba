from pydantic import BaseModel, Field


class TranscripcionResponse(BaseModel):
    """Resultado de transcribir el audio del dictado."""

    texto: str = Field(..., description="Texto reconocido en español rioplatense")
