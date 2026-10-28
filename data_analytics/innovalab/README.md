# Innovalab: habilitaciones comerciales de CABA

Pipeline de datos para integrar, limpiar y analizar habilitaciones comerciales de la Ciudad de Buenos Aires. Combina datos abiertos del GCBA, geografía oficial y consultas catastrales de EPOK para notebooks, análisis y carga en PostgreSQL.

## Inicio rápido

Desde la raíz del repositorio `sgi-tecba`, entra al proyecto de Analytics:

```bash
cd data_analytics/innovalab
```

Luego ejecuta desde `data_analytics/innovalab`:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Ejecuta el flujo reproducible de preparación y validación:

```bash
python -m src.run_pipeline --build-only
```

Para construir, validar y actualizar PostgreSQL en un único comando, configura `DATABASE_URL` y ejecuta `python -m src.run_pipeline`. Los notebooks siguen disponibles para exploración, gráficos y modelado; no son necesarios para la carga programada.

Para correr las pruebas:

```bash
python -m pytest tests/ -v
```

## Qué incluye

- `src/data_loader.py`, `cleaning.py` y `geografia.py`: carga, normalización, deduplicación y asignación trazable de comuna.
- `src/estadistica.py`: distribuciones, outliers, Gini/Lorenz y asociación estadística.
- `src/modelado.py` y `src/oportunidad.py`: modelos de comuna, clustering e índice de oportunidad.
- `src/apis_gcba.py`, `limpiar_smp.py` y `enriquecer_epok.py`: clientes GCBA y enriquecimiento catastral.
- `src/export_postgres.py` y `db/`: esquema y carga de datos para PostgreSQL.
- `notebook/`: exploración, modelos, clustering y análisis del Código Urbanístico.

## Datos y resultados

El padrón procesado contiene **216.991 registros y 22 columnas**. Los CSV de origen y procesados, las capas geográficas y `db/innovalab_dump.sql` se almacenan con **Git LFS** para mantener liviano el historial normal de Git. Instala Git LFS antes de clonar o ejecuta `git lfs install` y `git lfs pull` después de clonar para descargar los archivos grandes.

Estructura local necesaria:

```text
data/
├── raw/        # CSV originales de habilitaciones y codigo-urbanistico.csv
├── processed/  # habilitaciones_caba_clean.csv y codigo_urbanistico_limpio.csv
└── geo/        # callejero.csv, comunas.geojson y manzanas_catastrales.csv
```

El padrón `data/processed/habilitaciones_caba_clean.csv` también puede generarse ejecutando el notebook 01.

- Comuna asignada al **91,8%** de los registros; el 8,2% restante no tiene información suficiente para georreferenciarse.
- **79,7%** de los registros tiene una clave catastral `smp` utilizable.
- **154.473** registros tienen fecha de habilitación. Los datos modernos de 2025/2026 pueden carecer de fecha y número de solicitud.
- El archivo 2022 disponible no tiene estructura tabular y se excluye.

El detalle de columnas, fuentes y reglas de limpieza está en `src/cleaning.py`, `src/geografia.py` y los notebooks.

## Notebooks y modelos

| Notebook | Propósito |
|---|---|
| `01_exploracion_y_limpieza.ipynb` | Pipeline, controles de calidad y EDA del padrón. |
| `02_modelos.ipynb` | Regresión de volumen y clasificación de comuna. |
| `03_clustering_oportunidad.ipynb` | Grupos de comunas e índice de oportunidad por comuna y rubro. |
| `04_exploracion_y_limpieza_de_codigo_urbanistico.ipynb` | Limpieza del Código Urbanístico, compatibilidad ilustrativa y análisis de fecha de habilitación. |

Los resultados son exploratorios, no pronósticos ni decisiones regulatorias. En el notebook 02, la clasificación de comuna alcanza **17,7%** de accuracy frente a un baseline de **15,3%**; el split temporal de la regresión obtiene R² negativo. El índice de oportunidad resume tendencias históricas y no mide demanda futura.

El notebook 04 predice si el padrón tiene una fecha de habilitación registrada. **La ausencia de fecha no significa que el trámite haya sido rechazado.** Su matriz de compatibilidad usa estados simulados y no representa una evaluación normativa real.

## Código Urbanístico

El notebook 04 procesa `data/raw/codigo-urbanistico.csv` y genera `data/processed/codigo_urbanistico_limpio.csv`. La clave `smp` permite cruces con habilitaciones y fichas EPOK. La limpieza normaliza marcadores nulos y tipos, valida la clave y conserva faltantes en campos opcionales o dispersos. Los valores FOT negativos y los candidatos a outlier se reportan para revisión; no se corrigen automáticamente.

Las columnas `dist_*` pueden tener nulos estructurales. La matriz de permisos que aparece en la demostración es simulada y no debe usarse para determinar si un rubro está permitido.

## APIs y datos catastrales

`src/apis_gcba.py` incluye clientes para:

- **EPOK:** ficha catastral por SMP; `enriquecer_epok.py` guarda los resultados en `epok_fichas`.
- **BA Data (CKAN):** búsqueda y consulta de datasets abiertos.
- **USIG:** normalización/geocodificación de direcciones; servicio intermitente y no requerido por el pipeline principal.

El enriquecimiento EPOK se puede ejecutar por lotes y reanudar:

```bash
python src/limpiar_smp.py --dry-run
python src/enriquecer_epok.py --probar
python src/enriquecer_epok.py --limite 500
python src/enriquecer_epok.py
```

## PostgreSQL

Configura `DATABASE_URL` en el entorno; no guardes credenciales en el repositorio. Crea el esquema una vez y ejecuta el flujo completo:

```bash
psql "$DATABASE_URL" -f db/schema.sql
python -m src.run_pipeline
```

El comando único `python -m src.run_pipeline` reconstruye los CSV de habilitaciones y del Código Urbanístico desde `data/raw/`, asigna comunas al padrón, aplica los contratos de calidad y solo entonces carga las tres fuentes en PostgreSQL. `--build-only` prepara y valida sin base de datos; `--dry-run` valida también el formato de exportación sin escribir en PostgreSQL. Cada CSV procesado se reemplaza atómicamente después de superar sus validaciones. El reporte por columna queda en `data/processed/reporte_calidad.json`; las expectativas de comuna, SMP y fecha son 90%, 75% y 70%, respectivamente.

El padrón registra `comuna_fuente`, `smp_fuente` y `fecha_fuente`. La API expone el resumen en `GET /api/v1/habilitaciones/cobertura` y lo incluye en las respuestas de consulta.

El workflow `.github/workflows/analytics-refresh.yml` permite ejecución manual, corre cada lunes a las 09:17 UTC y se activa cuando cambian los datos fuente o el código del pipeline en `main`. Para habilitar la carga programada, configura `DATABASE_URL` como un secret del repositorio GitHub. El esquema debe estar creado previamente con `psql "$DATABASE_URL" -f db/schema.sql`; el job no guarda credenciales ni crea infraestructura de base de datos.

El scheduler procesa las versiones de entrada almacenadas en Git (incluidos los archivos LFS); no consulta por sí solo si el GCBA publicó una versión nueva de los datasets. Para incorporar datos fuente nuevos hay que actualizar los archivos versionados; ese cambio dispara una nueva carga.

El exportador resuelve `data/processed/habilitaciones_caba_clean.csv` desde la raíz de este proyecto; `codigo_urbanistico_limpio.csv` se lee desde el mismo directorio. No requiere rutas locales específicas de una computadora.

El CSV `db/seed/rubros_requisitos.csv` contiene un checklist curado para requisitos generales y de cafetería. Se consulta por rubro junto con los requisitos `General`:

```sql
SELECT etapa, orden, tramite, obligatorio, documentacion_requerida, organismo, link_oficial
FROM rubros_requisitos
WHERE rubro IN ('General', 'Cafetería')
ORDER BY etapa, orden;
```

La cobertura del checklist es un piloto, no un catálogo completo de rubros de la ciudad.

## Pruebas

```bash
python -m pytest tests/ -v
```

La suite verifica contratos de datos, estadísticas, oportunidad y clientes de APIs. Ejecuta las pruebas desde `data_analytics/innovalab`.

Las pruebas de contrato en `tests/test_data.py` validan `data/processed/habilitaciones_caba_clean.csv`. Si el archivo no existe, pytest las marca como omitidas; una suite sin omisiones de contrato requiere que el CSV esté disponible localmente.

## Limitaciones

- Hay años faltantes en la cobertura histórica; el campo `anio` identifica el archivo de origen y no constituye una serie temporal completa.
- La cobertura geográfica depende de la calidad de direcciones y claves del padrón original.
- La superficie del padrón puede ser cero o faltar; EPOK aporta datos catastrales cuando la SMP se resuelve.
- Los estados del Código Urbanístico en la demostración y la etiqueta de fecha de habilitación no equivalen a permisos ni a resultados de rechazo.