import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from app.core.data_paths import get_innovalab_data_dir
from app.core.database import get_db
from app.models.epok_ficha import EpokFicha
from app.models.habilitacion import Habilitacion
from app.schemas.mapa import ParcelaMapa, ParcelasMapaResponse

router = APIRouter()


@router.get("/mapa/comunas")
def obtener_comunas():
    path = get_innovalab_data_dir() / "geo" / "comunas.geojson"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró la capa GeoJSON de comunas: {path}",
        )
    with path.open(encoding="utf-8") as geojson_file:
        return JSONResponse(content=json.load(geojson_file))


@router.get("/mapa/parcelas", response_model=ParcelasMapaResponse)
def obtener_parcelas_mapa(
    oeste: float | None = Query(None, ge=-180, le=180),
    sur: float | None = Query(None, ge=-90, le=90),
    este: float | None = Query(None, ge=-180, le=180),
    norte: float | None = Query(None, ge=-90, le=90),
    comuna: int | None = Query(None, ge=1, le=15),
    rubro: str | None = Query(None, min_length=1, max_length=120),
    limite: int = Query(20000, ge=1, le=20000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    bounds = (oeste, sur, este, norte)
    if any(value is not None for value in bounds) and any(value is None for value in bounds):
        raise HTTPException(
            status_code=422,
            detail="Para filtrar el mapa envía oeste, sur, este y norte.",
        )
    if oeste is not None and oeste >= este:
        raise HTTPException(status_code=422, detail="oeste debe ser menor que este.")
    if sur is not None and sur >= norte:
        raise HTTPException(status_code=422, detail="sur debe ser menor que norte.")

    query = (
        db.query(EpokFicha.smp)
        .join(Habilitacion, Habilitacion.smp == EpokFicha.smp)
        .filter(EpokFicha.lat.isnot(None), EpokFicha.lng.isnot(None))
    )
    if oeste is not None:
        query = query.filter(
            EpokFicha.lng.between(oeste, este),
            EpokFicha.lat.between(sur, norte),
        )
    if comuna is not None:
        query = query.filter(Habilitacion.comuna == comuna)
    if rubro:
        query = query.filter(
            func.unaccent(func.lower(Habilitacion.descripcion_rubro))
            .ilike(func.unaccent(f"%{rubro.strip().lower()}%"))
        )

    total = query.with_entities(func.count(distinct(EpokFicha.smp))).scalar() or 0
    rows = (
        query.with_entities(
            EpokFicha.smp,
            EpokFicha.lat,
            EpokFicha.lng,
            EpokFicha.direccion,
            func.count(distinct(Habilitacion.id)).label("total_habilitaciones"),
            func.array_remove(
                func.array_agg(distinct(Habilitacion.descripcion_rubro)), None
            ).label("rubros"),
        )
        .group_by(
            EpokFicha.smp,
            EpokFicha.lat,
            EpokFicha.lng,
            EpokFicha.direccion,
        )
        .order_by(EpokFicha.smp)
        .offset(offset)
        .limit(limite)
        .all()
    )
    features = [
        ParcelaMapa(
            smp=row.smp,
            lat=row.lat,
            lng=row.lng,
            direccion=row.direccion,
            total_habilitaciones=row.total_habilitaciones,
            rubros=row.rubros or [],
        )
        for row in rows
    ]
    return ParcelasMapaResponse(
        total=total,
        limite=limite,
        offset=offset,
        features=features,
    )
