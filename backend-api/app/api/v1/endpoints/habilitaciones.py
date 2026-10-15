from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.core.database import get_db
from app.models.habilitacion import Habilitacion
from app.schemas.habilitacion import ConteoPorComuna, RubroConteo

router = APIRouter()

@router.get("/habilitaciones/por-comuna/{comuna}", response_model=ConteoPorComuna)
def habilitaciones_por_comuna(comuna: int, db: Session = Depends(get_db)):
    """Cuenta habilitaciones totales en una comuna."""
    total = db.query(Habilitacion).filter(Habilitacion.comuna == comuna).count()
    return ConteoPorComuna(comuna=comuna, total_habilitaciones=total)

@router.get("/habilitaciones/rubros-por-comuna/{comuna}", response_model=list[RubroConteo])
def rubros_por_comuna(
    comuna: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Top rubros habilitados en una comuna."""
    resultados = (
        db.query(
            Habilitacion.descripcion_rubro.label("rubro"),
            func.count(Habilitacion.id).label("total"),
        )
        .filter(Habilitacion.comuna == comuna)
        .filter(Habilitacion.descripcion_rubro.isnot(None))
        .group_by(Habilitacion.descripcion_rubro)
        .order_by(func.count(Habilitacion.id).desc())
        .limit(limit)
        .all()
    )
    return [RubroConteo(rubro=r.rubro, total=r.total) for r in resultados]

@router.get("/habilitaciones/buscar-cafeterias")
def buscar_cafeterias(
    comuna: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Busca cafeterías/pizzerías (insensible a acentos)."""
    query = db.query(Habilitacion).filter(
        text("unaccent(descripcion_rubro) ILIKE unaccent(:patron)")
    ).params(patron="%cafeter%")
    
    if comuna:
        query = query.filter(Habilitacion.comuna == comuna)
    
    return query.limit(limit).all()