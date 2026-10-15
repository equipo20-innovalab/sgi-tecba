from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.epok_ficha import EpokFicha
from app.schemas.catastro import CatastroResponse

router = APIRouter()

@router.get("/catastro/{smp}", response_model=CatastroResponse)
def get_catastro(smp: str, db: Session = Depends(get_db)):
    """Ficha catastral de un inmueble por SMP (ej: '001-001-008A')."""
    ficha = db.query(EpokFicha).filter(EpokFicha.smp == smp).first()
    if not ficha:
        raise HTTPException(status_code=404, detail=f"No hay ficha para SMP '{smp}'")
    return ficha