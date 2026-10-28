from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.endpoints import health, rubros, habilitaciones, catastro, consulta

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])
app.include_router(rubros.router, prefix=settings.API_V1_STR, tags=["rubros"])
app.include_router(habilitaciones.router, prefix=settings.API_V1_STR, tags=["habilitaciones"])
app.include_router(catastro.router, prefix=settings.API_V1_STR, tags=["catastro"])
app.include_router(consulta.router, prefix=settings.API_V1_STR, tags=["consulta"])

@app.get("/")
def root():
    return {
        "message": "TECBA - Sistema de Gestión Inteligente",
        "version": settings.VERSION,
        "docs": "/docs",
    }