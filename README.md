Avances Actuales Frontend https://habilitacioninteligente.vercel.app/
- **Módulo de Consulta Inteligente:** Desarrollo visual de la barra de búsqueda interactiva maquetada con Tailwind CSS
- **Diseño Responsivo:** Adaptación completa del sistema
- **Sistema de Diseño Oficial:** Integración de la librería de estilos Obelisco V2 del GCBA

Stack Tecnológico y Versiones
- **React:** v19.2.8
- **Vite:** v8.3.0
- **Tailwind CSS:** v3.4.19
- **Obelisco V2 (@gcba/obelisco-v2):** v1.19.0
- ~~**Leaflet:** v1.9.4~~ *(Retirado: reemplazado por MapLibre GL + capas oficiales Ciudad 3D)*
- **MapLibre GL:** v6.16.0 — visor 3D con fuentes públicas del GCBA (USIG/EPOK): parcelas, Código Urbanístico, alturas, mixtura, incidencia/alícuota y volumen edificable por SMP.

--------------------------------------------------------------------------------

Innovalab — Capa de Data Analytics  (CABA)

Pipeline reproducible en `data_analytics/innovalab` para **integrar, limpiar, validar y publicar** datos de habilitaciones comerciales de la Ciudad de Buenos Aires en PostgreSQL. Combina el padrón histórico del GCBA, geografía oficial, Código Urbanístico, fichas catastrales EPOK, matriz normativa multirrubro e índice de oportunidad comercial.

> **Alcance:** La capa de datos abastece al backend con información estructurada y trazable. Los resultados tienen carácter orientativo y no reemplazan el acto administrativo oficial.

Métricas y Estado Actual

| Indicador | Valor |
| :--- | :--- |
| Padrón histórico procesado | **216.991 registros · 22 columnas** (cobertura comuna 91,8% / SMP 79,6%) |
| Código Urbanístico limpio | **318.126 parcelas** normalizadas |
| Panel urbanístico (SMP) | **335.569 parcelas · 44 columnas** (139.643 habilitaciones cruzadas) |
| Fichas catastrales EPOK | **19.608 fichas** (enriquecimiento incremental con reintentos) |
| Catálogo maestro (`dim_requisitos`) | **13 trámites únicos de CABA · 9 URLs oficiales vigentes** |
| Matriz normativa (`fact_reglas_habilitacion`) | **5.690 reglas · 882 rubros distintos · 176 condicionales** |
| Índice de oportunidad (`v1.0.0`) | **1.121 combinaciones · 15 comunas · 80 rubros** (pesos 40/40/20) |
| Calidad y CI/CD | **137 pruebas automatizadas (`pytest`)** + workflows semanales y de demo |

Arquitectura del Pipeline (`src/run_pipeline.py`)

El flujo se ejecuta en tres etapas atómicas con validación de calidad (`src/data_validation.py`):
1. **Build:** Normalización y deduplicación del padrón (2015–2026), geocodificación/asignación de comuna (`catastro`, `callejero`, `fuzzy`) y limpieza del Código Urbanístico.
2. **Validate:** Controles automáticos de cobertura, tipos, nulidad y reglas de compatibilidad urbanística (`v1.0.0`, 12 reglas versionadas).
3. **Load:** Exportación y carga `UPSERT` en PostgreSQL (`src/export_postgres.py`) hacia las tablas y vistas productivas (`habilitaciones`, `codigo_urbanistico`, `urbanismo_smp`, `dim_requisitos`, `fact_reglas_habilitacion`, `requisitos_por_smp` e `indice_oportunidad_actual`).

Inicio Rápido y Entorno de Demo

**Ejecución completa del pipeline:**
```bash
cd data_analytics/innovalab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Validar sin base de datos o cargar directo en PostgreSQL:
python -m src.run_pipeline --build-only
export DATABASE_URL="postgresql://usuario:clave@host:5432/innovalab"
python -m src.run_pipeline
