from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class RubroRequisito(Base):
    """
    Checklist de requisitos para abrir un local por rubro.
    Fuente: tabla rubros_requisitos de Data.
    READ-ONLY: no crear ni modificar desde el backend.
    """
    __tablename__ = "rubros_requisitos"
    
    id = Column(Integer, primary_key=True, index=True)
    rubro = Column(String, nullable=False, index=True)
    tramite = Column(String, nullable=False)
    etapa = Column(String, index=True)
    orden = Column(Integer)
    obligatorio = Column(String)
    aplica_cuando = Column(String, nullable=True)
    documentacion_requerida = Column(String, nullable=False)
    organismo = Column(String)
    link_oficial = Column(String)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())