"""
Servicios de recuperación de datos de las 3 fuentes:
- BA Data (habilitaciones)
- EPOK (epok_fichas)
- Checklist curado (rubros_requisitos)
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import re
import unicodedata
from app.models.rubro_requisito import RubroRequisito
from app.models.habilitacion import Habilitacion
from app.models.epok_ficha import EpokFicha
from app.models.codigo_urbanistico import CodigoUrbanistico
from app.schemas.consulta import (
    RequisitoItem, CompetenciaItem, FichaCatastral, ContextoTerritorial,
    HabilitacionParcela, CoberturaCampo, CoberturaDatos,
)

EXPECTATIVAS_COBERTURA = {
    "solicitud": None,
    "tipo_tramite": None,
    "tipo_expediente": None,
    "subtipo_expediente": None,
    "fecha_habilitacion": 0.70,
    "numero_expediente": None,
    "codigo_rubro": 0.65,
    "descripcion_rubro": None,
    "superficie": None,
    "seccion": None,
    "manzana": None,
    "parcela": None,
    "calles": 0.95,
    "comuna": 0.90,
    "razon_social": 0.10,
    "partida_matriz": None,
    "origen": 1.0,
    "anio": 1.0,
    "smp": 0.75,
    "comuna_fuente": 1.0,
    "smp_fuente": 1.0,
    "fecha_fuente": 1.0,
}


def obtener_cobertura_datos(db: Session) -> CoberturaDatos:
    """Resume cobertura real del padrón y su trazabilidad de origen."""
    columnas = list(EXPECTATIVAS_COBERTURA)

    def expresion_con_dato(columna: str):
        valor = getattr(Habilitacion, columna)
        if columna == "superficie":
            return func.count(func.nullif(valor, 0))
        if columna == "tipo_tramite":
            texto = func.lower(func.trim(valor))
            return func.count(
                func.nullif(
                    func.nullif(func.nullif(texto, ""), "sin especificar"),
                    "sin dato",
                )
            )
        return func.count(valor)

    metricas = db.query(
        func.count(Habilitacion.id),
        *(expresion_con_dato(columna) for columna in columnas),
    ).one()
    total = int(metricas[0] or 0)
    if not total:
        return CoberturaDatos(total_registros=0, campos={})

    conteos_fuente = {}
    for columna in ("comuna_fuente", "smp_fuente", "fecha_fuente"):
        conteos_fuente[columna] = {
            str(fuente or "sin_dato"): int(cantidad)
            for fuente, cantidad in (
                db.query(getattr(Habilitacion, columna), func.count(Habilitacion.id))
                .group_by(getattr(Habilitacion, columna))
                .all()
            )
        }

    fuente_por_columna = {
        "comuna": "comuna_fuente",
        "smp": "smp_fuente",
        "fecha_habilitacion": "fecha_fuente",
    }
    campos = {}
    for indice, columna in enumerate(columnas, start=1):
        presentes = int(metricas[indice] or 0)
        cobertura = presentes / total
        expectativa = EXPECTATIVAS_COBERTURA[columna]
        campos[columna] = CoberturaCampo(
            registros_con_dato=presentes,
            registros_sin_dato=total - presentes,
            cobertura=round(cobertura, 4),
            expectativa_minima=expectativa,
            cumple_expectativa=(cobertura >= expectativa) if expectativa is not None else None,
            fuentes=conteos_fuente.get(fuente_por_columna.get(columna, columna), {}),
        )
    return CoberturaDatos(total_registros=total, campos=campos)


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
        ficha=f.ficha,
        puertas=f.puertas,
    )


def _normalizar_tokens(valor: str) -> set[str]:
    sin_acentos = unicodedata.normalize("NFKD", valor)
    plano = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+", plano.lower()))


def _tokens_calle(tokens: set[str]) -> set[str]:
    return tokens - {
        "av", "avda", "avenida", "calle", "c", "pasaje", "pje",
        "diagonal", "diag", "autopista",
    }


def _habilitacion_parcela(row: Habilitacion) -> HabilitacionParcela:
    return HabilitacionParcela(
        solicitud=row.solicitud,
        tipo_tramite=row.tipo_tramite,
        tipo_expediente=row.tipo_expediente,
        subtipo_expediente=row.subtipo_expediente,
        fecha_habilitacion=row.fecha_habilitacion.isoformat() if row.fecha_habilitacion else None,
        fecha_fuente=row.fecha_fuente,
        numero_expediente=row.numero_expediente,
        codigo_rubro=float(row.codigo_rubro) if row.codigo_rubro is not None else None,
        smp=row.smp,
        smp_fuente=row.smp_fuente,
        seccion=row.seccion,
        manzana=row.manzana,
        parcela=row.parcela,
        calles=row.calles,
        comuna=row.comuna,
        comuna_fuente=row.comuna_fuente,
        descripcion_rubro=row.descripcion_rubro,
        anio=row.anio,
        superficie=row.superficie,
        razon_social=row.razon_social,
        partida_matriz=row.partida_matriz,
        origen=row.origen,
    )


def obtener_codigo_urbanistico(db: Session, smp: str | None) -> dict | None:
    if not smp:
        return None
    row = db.query(CodigoUrbanistico).filter(CodigoUrbanistico.smp == smp).first()
    return row.datos if row else None


def obtener_habilitaciones_por_smp(
    db: Session, smp: str | None
) -> list[HabilitacionParcela]:
    if not smp:
        return []
    rows = (
        db.query(Habilitacion)
        .filter(Habilitacion.smp == smp)
        .order_by(Habilitacion.anio.desc().nullslast(), Habilitacion.id.desc())
        .all()
    )
    return [_habilitacion_parcela(row) for row in rows]


def obtener_habilitaciones_por_direccion(
    db: Session, direccion: str | None, comuna: int | None
) -> list[HabilitacionParcela]:
    """Relaciona una dirección solo si calle y altura coinciden exactamente en el padrón."""
    if not direccion:
        return []

    match = re.fullmatch(r"\s*(.+?)\s+(\d{1,5})\s*", direccion)
    if not match:
        return []
    calle, altura = match.groups()
    tokens_calle = _tokens_calle(_normalizar_tokens(calle))
    if not tokens_calle:
        return []

    query = db.query(Habilitacion).filter(
        Habilitacion.smp.isnot(None),
        Habilitacion.smp != "",
        Habilitacion.calles.op("~*")(rf"(^|[^0-9]){altura}([^0-9]|$)"),
    )
    if comuna is not None:
        query = query.filter(Habilitacion.comuna == comuna)
    for token in tokens_calle:
        query = query.filter(
            func.unaccent(func.lower(Habilitacion.calles)).ilike(f"%{token}%")
        )

    matches: list[HabilitacionParcela] = []
    for row in query.order_by(Habilitacion.anio.desc().nullslast()).all():
        for tramo in (row.calles or "").split(";"):
            tokens_tramo = _normalizar_tokens(tramo)
            if altura not in tokens_tramo:
                continue
            tokens_direccion = _tokens_calle(tokens_tramo - {altura})
            if tokens_direccion == tokens_calle:
                matches.append(_habilitacion_parcela(row))
                break

    return matches


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