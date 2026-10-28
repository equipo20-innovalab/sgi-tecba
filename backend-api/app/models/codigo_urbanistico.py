from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class CodigoUrbanistico(Base):
    """Datos del Código Urbanístico de CABA, una fila por SMP. READ-ONLY."""

    __tablename__ = "codigo_urbanistico"

    smp = Column(String, primary_key=True, index=True)
    smp_raw = Column(String, nullable=False)
    barrio = Column(String, index=True)
    comuna = Column(SmallInteger, index=True)

    dist_cpu_1 = Column(String, index=True)
    dist_cpu_2 = Column(String)
    dist_1_esp = Column(String)
    zona_1 = Column(String)
    zona_2 = Column(String)

    uso_1 = Column(SmallInteger)
    uso_2 = Column(SmallInteger)
    uso_3 = Column(SmallInteger)

    uni_edif_1 = Column(Float)
    uni_edif_2 = Column(Float)
    uni_edif_3 = Column(Float)
    uni_edif_4 = Column(Float)

    fot_em_1 = Column(Float)
    fot_em_2 = Column(Float)
    fot_pl_1 = Column(Float)
    fot_pl_2 = Column(Float)
    fot_sl_1 = Column(Float)
    fot_sl_2 = Column(Float)

    catalogado = Column(Boolean)
    tipo_mza = Column(String)
    sm = Column(String)
    alicuota = Column(Float)
    inc_uva_21 = Column(Float)
    cpu_obs = Column(String)
    memo = Column(String)
    adps = Column(String)
    ae_fot_bas = Column(Float)

    raw = Column(JSONB, nullable=False)
    fuente = Column(
        String,
        nullable=False,
        server_default=text("'BA Data - Código Urbanístico 2024-12-31'"),
    )
    fuente_fecha = Column(
        Date, nullable=False, server_default=text("DATE '2024-12-31'")
    )
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now())
