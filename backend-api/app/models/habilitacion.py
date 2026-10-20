from sqlalchemy import Column, BigInteger, SmallInteger, String, Float, Date, Numeric
from app.core.database import Base

class Habilitacion(Base):
    """
    Padrón histórico de habilitaciones comerciales de la CABA.
    216.991 filas. READ-ONLY.
    """
    __tablename__ = "habilitaciones"
    
    id = Column(BigInteger, primary_key=True, index=True)
    solicitud = Column(BigInteger, nullable=True)
    tipo_tramite = Column(String)
    tipo_expediente = Column(String)
    subtipo_expediente = Column(String)
    fecha_habilitacion = Column(Date, nullable=True)
    numero_expediente = Column(String)
    codigo_rubro = Column(Numeric)
    descripcion_rubro = Column(String)
    superficie = Column(Float)
    seccion = Column(String)
    manzana = Column(String)
    parcela = Column(String)
    smp = Column(String, index=True)
    calles = Column(String)
    comuna = Column(SmallInteger, index=True)
    comuna_fuente = Column(String)
    razon_social = Column(String)
    partida_matriz = Column(String)
    origen = Column(String)
    anio = Column(SmallInteger, index=True)