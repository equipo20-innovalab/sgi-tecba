from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.consulta import ConsultaRequest, ConsultaResponse
from app.services.consulta_service import procesar_consulta

router = APIRouter()


@router.post(
    "/consulta",
    response_model=ConsultaResponse,
    summary="Consulta en lenguaje natural",
    description=(
        "Endpoint central del MVP. Recibe una consulta en lenguaje natural, "
        "extrae la actividad y la ubicación, geocodifica la dirección, "
        "consulta las 3 fuentes (BA Data, EPOK, checklist) y devuelve "
        "una respuesta integrada con trazabilidad de fuentes.\n\n"
        "Ejemplo: `{\"texto\": \"Quiero abrir una cafetería en Av. Corrientes 2500\"}`"
    ),
)
def consulta(req: ConsultaRequest, db: Session = Depends(get_db)):
    try:
        return procesar_consulta(db, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando consulta: {e}")