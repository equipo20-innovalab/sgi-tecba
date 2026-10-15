from sqlalchemy import Column, String, Float, SmallInteger, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base

class EpokFicha(Base):
    """
    Ficha catastral de EPOK por SMP.
    READ-ONLY.
    """
    __tablename__ = "epok_fichas"
    
    smp = Column(String, primary_key=True, index=True)
    ficha = Column(JSONB)
    lng = Column(Float)
    lat = Column(Float)
    direccion = Column(String)
    superficie_total = Column(Float)
    superficie_cubierta = Column(Float)
    frente = Column(Float)
    fondo = Column(Float)
    pisos_sobre_rasante = Column(SmallInteger)
    unidades_funcionales = Column(Integer)
    propiedad_horizontal = Column(String)
    puertas = Column(JSONB)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now())