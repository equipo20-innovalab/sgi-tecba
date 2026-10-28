from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Verifica el estado del backend y las tablas de la DB."""
    try:
        total_rubros = db.execute(
            text("SELECT count(*) FROM rubros_requisitos")
        ).scalar()
        total_hab = db.execute(text("SELECT count(*) FROM habilitaciones")).scalar()
        total_epok = db.execute(text("SELECT count(*) FROM epok_fichas")).scalar()
        total_cu = db.execute(text("SELECT count(*) FROM codigo_urbanistico")).scalar()
        total_dir = db.execute(text("SELECT count(*) FROM epok_direcciones")).scalar()
        rls = db.execute(text("""
            SELECT relname, relrowsecurity
            FROM pg_class
            WHERE relname IN ('epok_fichas', 'habilitaciones', 'rubros_requisitos')
            ORDER BY relname
            """)).all()
        postgis = db.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
        ).scalar()
        return {
            "status": "ok",
            "database": "connected",
            "tablas": {
                "rubros_requisitos": total_rubros,
                "habilitaciones": total_hab,
                "epok_fichas": total_epok,
                "codigo_urbanistico": total_cu,
                "epok_direcciones": total_dir,
            },
            "rls": {nombre: activo for nombre, activo in rls},
            "postgis": bool(postgis),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
