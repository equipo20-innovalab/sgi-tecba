from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.consulta import Ubicacion
from app.services.geocoding_service import geocodificar

router = APIRouter()


@router.get(
    "/geocodificar",
    response_model=Ubicacion,
    summary="Normaliza una dirección y devuelve su SMP",
)
def geocodificar_endpoint(
    direccion: str = Query(..., min_length=3, description="Ej: Av. Corrientes 2500"),
    db: Session = Depends(get_db),
):
    return geocodificar(direccion, db)
