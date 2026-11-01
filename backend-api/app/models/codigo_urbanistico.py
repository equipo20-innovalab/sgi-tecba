from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class CodigoUrbanistico(Base):
    __tablename__ = "codigo_urbanistico"

    smp = Column(String, primary_key=True, index=True)
    datos = Column(JSONB, nullable=False)
