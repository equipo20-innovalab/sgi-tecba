from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Verifica el estado del backend y las tablas de la DB."""
    try:
        total_rubros = db.execute(text("SELECT count(*) FROM rubros_requisitos")).scalar()
        total_hab = db.execute(text("SELECT count(*) FROM habilitaciones")).scalar()
        total_epok = db.execute(text("SELECT count(*) FROM epok_fichas")).scalar()
        return {
            "status": "ok",
            "database": "connected",
            "tablas": {
                "rubros_requisitos": total_rubros,
                "habilitaciones": total_hab,
                "epok_fichas": total_epok,
            }
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}