"""Servicio de zonificación y parámetros del Código Urbanístico."""

from sqlalchemy.orm import Session

from app.models.codigo_urbanistico import CodigoUrbanistico
from app.schemas.urbanismo import Zonificacion
from app.services.text_utils import normalizar_smp

GRADO_MIXTURA_LABELS = {
    0: "Sin dato",
    1: "Grado 1 - baja mixtura",
    2: "Grado 2 - mixtura media A",
    3: "Grado 3 - mixtura media B",
    4: "Grado 4 - alta mixtura",
}


def etiqueta_grado(grado: int | None) -> str | None:
    if grado is None:
        return None
    return GRADO_MIXTURA_LABELS.get(grado, f"Grado {grado}")


def _fot(valor: float | None) -> float | None:
    # El CSV usa -1 y 0 como centinelas para "no corresponde / sin dato".
    if valor is None or valor <= 0:
        return None
    return float(valor)


def _edificabilidad(valor: float | None) -> float | None:
    if valor is None or valor <= 0:
        return None
    return float(valor)


def _restricciones(row: CodigoUrbanistico) -> list[str]:
    restricciones: list[str] = []
    if row.catalogado:
        restricciones.append("Inmueble catalogado")
    if row.adps:
        restricciones.append(f"ADPS: {row.adps}")
    if row.cpu_obs:
        restricciones.append(f"Observaciones CPU: {row.cpu_obs}")
    if row.memo:
        restricciones.append(f"Memo: {row.memo}")
    if row.ae_fot_bas:
        restricciones.append(f"AE FOT base: {row.ae_fot_bas:g}")
    return restricciones


def obtener_zonificacion(db: Session, smp: str | None) -> Zonificacion | None:
    """Devuelve la zonificación CU para un SMP, o None si no existe."""
    smp_normalizado = normalizar_smp(smp)
    if not smp_normalizado:
        return None

    row = (
        db.query(CodigoUrbanistico)
        .filter(CodigoUrbanistico.smp == smp_normalizado)
        .first()
    )
    if not row:
        return None

    usos = [u for u in (row.uso_1, row.uso_2, row.uso_3) if u not in (None, 0)]
    grado = row.uso_1 if row.uso_1 not in (None, 0) else (usos[0] if usos else None)

    zona = row.dist_cpu_1 or row.dist_1_esp or row.zona_1
    if row.dist_cpu_1:
        zona_fuente = "dist_cpu_1"
    elif row.dist_1_esp:
        zona_fuente = "dist_1_esp"
    elif row.zona_1:
        zona_fuente = "zona_1"
    else:
        zona_fuente = None

    return Zonificacion(
        smp=row.smp,
        barrio=row.barrio,
        comuna=row.comuna,
        zona=zona,
        zona_fuente=zona_fuente,
        distrito_especial=row.dist_1_esp,
        zona_secundaria=row.zona_1,
        grado_mixtura=grado,
        grado_mixtura_label=etiqueta_grado(grado),
        usos=usos,
        edificabilidad=_edificabilidad(row.uni_edif_1),
        edificabilidad_unidad="no documentada",
        fot=_fot(row.fot_em_1),
        catalogado=row.catalogado,
        tipo_manzana=row.tipo_mza,
        restricciones=_restricciones(row),
        fuente=row.fuente,
        fuente_fecha=row.fuente_fecha,
    )
