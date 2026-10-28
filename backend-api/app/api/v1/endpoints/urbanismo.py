from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.urbanismo import Zonificacion
from app.services.geocoding_service import obtener_smp_por_coordenadas
from app.services.urbanismo_service import obtener_zonificacion

router = APIRouter()


@router.get("/urbanismo/{smp}", response_model=Zonificacion)
def get_urbanismo_por_smp(smp: str, db: Session = Depends(get_db)):
    zonificacion = obtener_zonificacion(db, smp)
    if not zonificacion:
        raise HTTPException(
            status_code=404,
            detail=f"No hay datos del Código Urbanístico para SMP '{smp}'",
        )
    return zonificacion


@router.get("/urbanismo", response_model=Zonificacion)
def get_urbanismo_por_coordenadas(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
):
    smp = obtener_smp_por_coordenadas(lat, lng)
    if not smp:
        raise HTTPException(
            status_code=404, detail="No se encontró una parcela EPOK en ese punto"
        )
    zonificacion = obtener_zonificacion(db, smp)
    if not zonificacion:
        raise HTTPException(
            status_code=404,
            detail=f"No hay datos del Código Urbanístico para SMP '{smp}'",
        )
    return zonificacion
