"""
Servicios de recuperación de datos de las 3 fuentes:
- BA Data (habilitaciones)
- EPOK (epok_fichas)
- Checklist curado (rubros_requisitos)
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.models.rubro_requisito import RubroRequisito
from app.models.habilitacion import Habilitacion
from app.models.epok_ficha import EpokFicha
from app.schemas.consulta import (
    RequisitoItem, CompetenciaItem, FichaCatastral, ContextoTerritorial,
)


def obtener_requisitos(db: Session, actividad: str | None) -> list[RequisitoItem]:
    """Fuente 3: checklist curado de requisitos (General + rubro específico)."""
    if not actividad:
        return []
    rows = (
        db.query(RubroRequisito)
        .filter(RubroRequisito.rubro.in_(["General", actividad]))
        .order_by(RubroRequisito.etapa, RubroRequisito.orden)
        .all()
    )
    return [
        RequisitoItem(
            etapa=r.etapa, orden=r.orden, tramite=r.tramite,
            obligatorio=r.obligatorio, aplica_cuando=r.aplica_cuando,
            documentacion_requerida=r.documentacion_requerida,
            organismo=r.organismo, link_oficial=r.link_oficial,
        )
        for r in rows
    ]


def obtener_competencia_cercana(
    db: Session,
    actividad: str | None,
    comuna: int | None,
    limit: int = 20,
) -> list[CompetenciaItem]:
    """Fuente 1: padrón BA Data — competencia en la misma comuna."""
    if not actividad or not comuna:
        return []
    rows = (
        db.query(Habilitacion)
        .filter(Habilitacion.comuna == comuna)
        .filter(
            func.unaccent(func.lower(Habilitacion.descripcion_rubro))
            .ilike(func.unaccent(f"%{actividad.lower()}%"))
        )
        .order_by(Habilitacion.anio.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [
        CompetenciaItem(
            descripcion_rubro=h.descripcion_rubro,
            calles=h.calles,
            comuna=h.comuna,
            anio=h.anio,
            superficie=h.superficie,
        )
        for h in rows
    ]


def obtener_ficha_catastral(db: Session, smp: str | None) -> FichaCatastral | None:
    """Fuente 2: ficha catastral EPOK por SMP."""
    if not smp:
        return None
    f = db.query(EpokFicha).filter(EpokFicha.smp == smp).first()
    if not f:
        return None
    return FichaCatastral(
        smp=f.smp, direccion=f.direccion,
        superficie_total=f.superficie_total,
        superficie_cubierta=f.superficie_cubierta,
        pisos_sobre_rasante=f.pisos_sobre_rasante,
        unidades_funcionales=f.unidades_funcionales,
        lat=f.lat, lng=f.lng,
    )


def obtener_contexto_territorial(
    db: Session, comuna: int | None
) -> ContextoTerritorial | None:
    """Contexto de la comuna: total habilitaciones + top 5 rubros."""
    if not comuna:
        return None
    total = (
        db.query(func.count(Habilitacion.id))
        .filter(Habilitacion.comuna == comuna)
        .scalar()
    )
    rubros = (
        db.query(
            Habilitacion.descripcion_rubro,
            func.count(Habilitacion.id).label("total"),
        )
        .filter(Habilitacion.comuna == comuna)
        .filter(Habilitacion.descripcion_rubro.isnot(None))
        .group_by(Habilitacion.descripcion_rubro)
        .order_by(text("total DESC"))
        .limit(5)
        .all()
    )
    return ContextoTerritorial(
        comuna=comuna,
        total_habilitaciones=total or 0,
        rubros_top=[{"rubro": r[0], "total": r[1]} for r in rubros],
    )


def construir_camino_feliz(requisitos: list[RequisitoItem]) -> list[str]:
    """Ordena los requisitos por etapa para armar el camino del usuario."""
    if not requisitos:
        return []
    orden_etapas = ["previo", "habilitacion", "rubro", "tributario", "operativo"]
    ordenados = sorted(
        requisitos,
        key=lambda r: (
            orden_etapas.index(r.etapa) if r.etapa in orden_etapas else 99,
            r.orden or 0,
        ),
    )
    return [
        f"[{r.etapa or 'sin etapa'}] {r.tramite} ({r.obligatorio or 'Sin especificar'})"
        for r in ordenados
    ]