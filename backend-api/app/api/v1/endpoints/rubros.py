from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.rubro_requisito import RubroRequisito
from app.schemas.rubro import ChecklistResponse

router = APIRouter()

@router.get("/rubros", response_model=list[str])
def listar_rubros(db: Session = Depends(get_db)):
    """Lista todos los rubros disponibles."""
    rubros = db.query(RubroRequisito.rubro).distinct().order_by(RubroRequisito.rubro).all()
    return [r[0] for r in rubros]

@router.get("/rubros/{rubro}/requisitos", response_model=ChecklistResponse)
def get_requisitos(rubro: str, db: Session = Depends(get_db)):
    """Devuelve el checklist para abrir un local del rubro dado."""
    rubros_a_buscar = ["General", rubro.capitalize()]
    
    requisitos = (
        db.query(RubroRequisito)
        .filter(RubroRequisito.rubro.in_(rubros_a_buscar))
        .order_by(RubroRequisito.etapa, RubroRequisito.orden)
        .all()
    )
    
    if not requisitos:
        raise HTTPException(status_code=404, detail=f"No hay requisitos para '{rubro}'")
    
    return ChecklistResponse(rubro=rubro, total=len(requisitos), requisitos=requisitos)