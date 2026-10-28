from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.sql import func
from app.core.database import Base


class EpokDireccion(Base):
    """Índice local de puertas EPOK por calle + altura. READ-ONLY."""

    __tablename__ = "epok_direcciones"

    id = Column(BigInteger, primary_key=True)
    smp = Column(String, index=True, nullable=False)
    calle = Column(String, nullable=False)
    calle_normalizada = Column(String, index=True, nullable=False)
    calle_base = Column(String, index=True, nullable=False)
    altura = Column(Integer, index=True, nullable=False)
    codigo_calle = Column(Integer, index=True, nullable=False)
    puerta_principal = Column(Boolean, nullable=False, default=False)
    puerta_oficial = Column(Boolean, nullable=False, default=False)
    fuente = Column(String)
    fecha_actualizacion = Column(Date)
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now())
