from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.epok_ficha import EpokFicha
from app.schemas.catastro import CatastroResponse
from app.services.text_utils import normalizar_smp
from app.services.urbanismo_service import obtener_zonificacion

router = APIRouter()


@router.get("/catastro/{smp}", response_model=CatastroResponse)
def get_catastro(smp: str, db: Session = Depends(get_db)):
    """Ficha catastral de un inmueble por SMP (ej: '001-001-008A')."""
    smp_normalizado = normalizar_smp(smp)
    ficha = db.query(EpokFicha).filter(EpokFicha.smp == smp_normalizado).first()
    if not ficha:
        raise HTTPException(status_code=404, detail=f"No hay ficha para SMP '{smp}'")

    zonificacion = obtener_zonificacion(db, smp_normalizado)
    return CatastroResponse(
        smp=ficha.smp,
        direccion=ficha.direccion,
        superficie_total=ficha.superficie_total,
        superficie_cubierta=ficha.superficie_cubierta,
        lat=ficha.lat,
        lng=ficha.lng,
        pisos_sobre_rasante=ficha.pisos_sobre_rasante,
        unidades_funcionales=ficha.unidades_funcionales,
        barrio=zonificacion.barrio if zonificacion else None,
        comuna=zonificacion.comuna if zonificacion else None,
        zonificacion=zonificacion,
    )
