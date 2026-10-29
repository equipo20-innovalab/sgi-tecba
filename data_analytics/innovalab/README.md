# Innovalab — datos de habilitaciones comerciales de CABA

Pipeline reproducible para **integrar, limpiar, validar y publicar** datos de habilitaciones comerciales de la Ciudad de Buenos Aires. Combina el padrón histórico del GCBA, geografía oficial, el Código Urbanístico, fichas catastrales EPOK y un índice de oportunidad por comuna y rubro.

> **Alcance:** este directorio es la capa de datos. No incluye backend, frontend ni endpoints. Los resultados son descriptivos y orientativos: no constituyen permisos de uso, habilitaciones comerciales ni asesoramiento normativo.

## Estado actual

| Indicador | Valor |
|---|---|
| Padrón procesado | **216.991 registros · 22 columnas** |
| Cobertura de comuna / SMP / fecha | **91,8% / 79,6% / 71,2%** |
| Código Urbanístico limpio | **318.126 parcelas** |
| Panel urbanístico | **335.569 SMP · 44 columnas** |
| Habilitaciones cruzadas con CU | **139.643 (64,3%)** |
| Habilitaciones con ficha EPOK | **82.210 (37,9%)** |
| Índice de oportunidad | **1.121 filas · 15 comunas · 80 rubros** |
| Fórmula del índice | **`1.0.0`** · pesos 40/40/20 · `anio_ref=2025` |
| Reglas de compatibilidad | **`1.0.0`** · 12 reglas versionadas |
| Pruebas | **91** |

Detalle de la última corrida: [`data/processed/urbanismo_cobertura.json`](data/processed/urbanismo_cobertura.json) y [`data/processed/indice_oportunidad_meta.json`](data/processed/indice_oportunidad_meta.json).

## Inicio rápido

Desde la raíz del repositorio `sgi-tecba`:

```bash
cd data_analytics/innovalab
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Construir y validar sin base de datos:

```bash
python -m src.run_pipeline --build-only
```

Construir, validar y actualizar PostgreSQL en un solo comando:

```bash
export DATABASE_URL="postgresql://usuario:clave@host:5432/innovalab"
python -m src.run_pipeline
```

Comprobar todo el flujo sin escribir en disco ni en la base:

```bash
python -m src.run_pipeline --dry-run
```

Correr las pruebas:

```bash
python -m pytest tests/ -v
```

## Estructura

```text
data_analytics/innovalab/
├── src/
│   ├── data_loader.py          # Lectura de CSV crudos y rutas del proyecto
│   ├── cleaning.py             # Normalización, deduplicación y unificación de esquemas
│   ├── geografia.py            # Asignación trazable de comuna (catastro, callejero, fuzzy)
│   ├── codigo_urbanistico.py   # Limpieza del Código Urbanístico
│   ├── urbanismo.py            # SMP, reglas, panel y cobertura urbanística
│   ├── data_validation.py      # Contrato de calidad y reporte por columna
│   ├── oportunidad.py          # Índice, artefactos y backtest
│   ├── estadistica.py          # Distribuciones, Gini/Lorenz, asociación
│   ├── modelado.py             # Regresión y clasificación exploratorias
│   ├── apis_gcba.py            # Clientes EPOK, USIG y BA Data
│   ├── limpiar_smp.py          # Normalización de claves catastrales
│   ├── enriquecer_epok.py      # Enriquecimiento por lotes y reanudable
│   ├── export_postgres.py      # Artefactos + carga a PostgreSQL
│   └── run_pipeline.py         # Orquestación build → validate → load
├── data/
│   ├── raw/                    # CSV originales del GCBA + codigo-urbanistico.csv
│   ├── processed/              # Padrón, CU limpio y artefactos derivados
│   └── geo/                    # callejero.csv, comunas.geojson, manzanas_catastrales.csv
├── db/
│   ├── schema.sql              # Tablas, índices y vistas
│   ├── seed/                   # Requisitos de rubros y reglas de compatibilidad
│   └── innovalab_dump.sql      # Dump de referencia (Git LFS)
├── docs/                       # Fórmula del índice y detalle urbanístico
├── notebook/                   # Exploración, modelos, clustering y CU
└── tests/                      # 91 pruebas
```

Los archivos de `data/` y `db/innovalab_dump.sql` se versionan con **Git LFS**. Instala Git LFS antes de clonar o ejecuta `git lfs pull` después. Los artefactos derivados de índices y urbanismo se regeneran con los comandos de este README y no se versionan.

## Pipeline de datos

`python -m src.run_pipeline` ejecuta tres etapas y se detiene si alguna falla:

1. **Build** — carga los CSV crudos, normaliza y deduplica, asigna comuna y reconstruye el Código Urbanístico limpio.
2. **Validate** — aplica el contrato de calidad al padrón y al CU. Cada CSV se reemplaza de forma atómica solo después de superar las validaciones.
3. **Load** — ejecuta `src/export_postgres.py --all`: requisitos, habilitaciones, Código Urbanístico, panel urbanístico e índice de oportunidad.

| Comando | Construye | Valida | Escribe artefactos | Escribe en PostgreSQL |
|---|---:|---:|---:|---:|
| `python -m src.run_pipeline --build-only` | Sí | Sí | Sí | No |
| `python -m src.run_pipeline --dry-run` | Sí | Sí | Sí | No (prueba el formato) |
| `python -m src.run_pipeline` | Sí | Sí | Sí | Sí |

### Cargas selectivas

```bash
python src/export_postgres.py --rubros
python src/export_postgres.py --habilitaciones
python src/export_postgres.py --codigo-urbanistico
python src/export_postgres.py --oportunidad --min-licencias 5 --top-rubros 80
python src/export_postgres.py --all
```

Opciones útiles: `--reglas <ruta.json>` cambia el archivo de reglas, `--sin-epok` omite las fichas catastrales al construir el panel, `--dry-run` valida sin escribir.

## Fuentes y artefactos

### Entradas (`data/raw/`)

- `habilitaciones-2015-a-2018.csv`, `habilitaciones-2019.csv`, `habilitaciones-2020`, `2021`, `2023`, `2024`, `2025` y `2026` según la exportación vigente del GCBA.
- `habilitaciones-2022` existe pero **no tiene estructura tabular**: se excluye.
- `codigo-urbanistico.csv` (~50 MB).
- Geografía en `data/geo/`: `callejero.csv`, `comunas.geojson` y `manzanas_catastrales.csv`.

### Salidas (`data/processed/`)

| Archivo | Contenido |
|---|---|
| `habilitaciones_caba_clean.csv` | Padrón limpio, 216.991 × 22 |
| `codigo_urbanistico_limpio.csv` | Código Urbanístico normalizado, 318.126 parcelas |
| `reporte_calidad.json` | Cobertura por columna, fuentes y totales |
| `indice_oportunidad.csv` | Score por `(comuna, rubro)` con componentes y explicación |
| `indice_oportunidad_meta.json` | Versión, pesos, parámetros y SHA-256 del CSV de origen |
| `urbanismo_smp.csv` | Panel por SMP, 335.569 × 44 |
| `urbanismo_cobertura.json` | Métricas, distribuciones, huellas y limitaciones |

## Contrato de calidad

`src/data_validation.py` exige, entre otras condiciones:

| Control | Umbral |
|---|---|
| Filas mínimas | 200.000 |
| Comuna | ≥ 90%, valores 1..15 |
| SMP no nulo | ≥ 75% |
| Fecha de habilitación válida | ≥ 70% |
| Calles | ≥ 95% |
| `codigo_rubro` | ≥ 65% |
| `razon_social` | ≥ 10% |
| `origen`, `anio`, `smp_fuente`, `fecha_fuente`, `comuna_fuente` | 100% |
| Años | 2015..2026, sin nulos |
| Duplicados completos | 0 |
| Archivos fuente | ≥ 7 |

Cobertura medida en la última corrida: comuna **91,83%**, SMP **79,6%**, fecha **71,19%**, calles **99,12%**, `codigo_rubro` **69,6%**, `razon_social` **11,8%**, `partida_matriz` **99,23%** y `superficie` **21,9%**.

Fuentes de trazabilidad:

- `comuna_fuente`: `catastro` 172.527 · `archivo` 25.249 · `sin_dato` 17.728 · `callejero` 1.484 · `callejero_fuzzy` 3.
- `smp_fuente`: `seccion_manzana_parcela` 172.839 · `sin_dato` 44.152.
- `fecha_fuente`: `archivo` 154.473 · `sin_dato` 62.518.

## Código Urbanístico

`src/codigo_urbanistico.py` procesa `data/raw/codigo-urbanistico.csv` y genera `data/processed/codigo_urbanistico_limpio.csv`. La clave `smp` permite cruzar con habilitaciones y fichas EPOK. La limpieza normaliza marcadores nulos y tipos, valida la clave y conserva faltantes en campos opcionales o dispersos. Los FOT negativos y los candidatos a outlier se reportan para revisión; no se corrigen automáticamente.

- Las columnas `dist_*` pueden tener nulos estructurales; un faltante no se interpreta como “sin afectación”.
- `dist_cpu_1` pertenece al Código de Planeamiento Urbano **derogado**: se conserva como contexto y se marca `dist_cpu_1_vigente=false`.
- `uso_1/2/3` son **mixtura de uso**, no permisos de rubro.
- Los SMP se clasifican como `estandar`, `ampliado`, `placeholder`, `invalido` o `sin_dato`; el control de `placeholder` (parcela `000`) precede al de formato estándar.

### Compatibilidad urbanística

`src/urbanismo.py` construye un panel de una fila por SMP y evalúa reglas versionadas contra señales del CU, el padrón y EPOK.

```bash
python src/export_postgres.py --codigo-urbanistico --dry-run   # solo valida y calcula
python src/export_postgres.py --codigo-urbanistico             # artefactos + carga
python src/export_postgres.py --codigo-urbanistico --sin-epok  # sin fichas EPOK
python src/export_postgres.py --codigo-urbanistico --reglas db/seed/reglas_compatibilidad_urbanistica.json
```

Las reglas viven en [`db/seed/reglas_compatibilidad_urbanistica.json`](db/seed/reglas_compatibilidad_urbanistica.json) (versión `1.0.0`, 12 reglas, advertencia y SHA-256). Se evalúan por `prioridad` ascendente: gana la primera que coincide; si ninguna coincide, el estado es `no_verificable`.

| Estado | Significado |
|---|---|
| `compatible` | Sin señales de fricción en los campos disponibles. **No** implica que el uso esté permitido. |
| `requiere_revision` | Patrimonio, riesgo hídrico, línea de edificación, distrito especial o dato faltante. |
| `no_compatible` | Afectación declarada: espacio público, apertura o ensanche. |
| `no_verificable` | SMP ausente, placeholder, inválido o sin fila en el CU. |

Reglas `1.0.0`: `SMP_NO_VERIFICABLE` (10), `CU_AUSENTE` (20), `ESPACIO_PUBLICO` (30), `AFECTACION_APERTURA` (31), `AFECTACION_ENSANCHE` (32), `PATRIMONIO_CATALOGADO` (40), `RIESGO_HIDRICO` (41), `LINEA_EDIFICACION` (42), `CONO_AEROPARQUE` (43), `DISTRITO_ESPECIAL` (50), `DISTRITO_SIN_DATO` (51) y `SIN_SENALES_DE_FRICCION` (99).

### Cobertura medida

| Cruce | Valor |
|---|---|
| SMP del padrón con fila en CU | **27.709 / 45.152 = 61,4%** |
| Uso del CU por habilitaciones | **27.709 / 318.126 = 8,7%** |
| Habilitaciones con fila en CU | **139.643 / 216.991 = 64,3%** |
| Habilitaciones con EPOK | **82.210 / 216.991 = 37,9%** |
| Habilitaciones sin SMP | **44.152 / 216.991 = 20,3%** |

Estados por SMP: `compatible` 187.142 (55,8%) · `requiere_revision` 128.124 (38,2%) · `no_verificable` 18.623 (5,5%) · `no_compatible` 1.680 (0,5%).

Estados por habilitación: `compatible` 96.829 (44,6%) · `requiere_revision` 40.624 (18,7%) · `no_verificable` 33.542 (15,5%) · `sin_smp` 44.152 (20,3%) · `no_compatible` 1.844 (0,8%).

La lectura correcta es de **cobertura de datos**, no de aprobación: el 35,7% de las habilitaciones no tiene fila en el CU y el 20,3% no tiene SMP. Esas ausencias explican la mayor parte de los estados no verificables.

Documentación completa: [`docs/urbanismo_compatibilidad.md`](docs/urbanismo_compatibilidad.md).

## Índice de oportunidad

El índice responde *dónde y qué conviene abrir* con una fórmula versionada y auditable:

```text
score = 100 × (0,40 · crecimiento + 0,40 · (1 − saturación) + 0,20 · subrepresentación)
```

- **Crecimiento:** variación anualizada de la cuota del rubro dentro de su comuna.
- **Baja saturación:** `1 − n_licencias(rubro, comuna) / media(comuna)`.
- **Subrepresentación:** diferencia entre cuota esperada y observada del rubro.
- Cada señal se normaliza min-max; `NaN` y series constantes pasan a `0.5`.
- Los pesos se renormalizan para sumar 1; el score queda en `[0, 100]`.

```bash
python src/export_postgres.py --oportunidad --min-licencias 5 --top-rubros 80
```

Artefactos y objetos:

| Objeto | Rol |
|---|---|
| `data/processed/indice_oportunidad.csv` | 1.121 filas × 22 columnas: score, componentes, aportes, métricas, versión y explicación |
| `data/processed/indice_oportunidad_meta.json` | Versión, fecha, pesos, parámetros y SHA-256 del padrón de origen |
| `indice_oportunidad_meta` | Una fila por corrida (`calculo_id`) |
| `indice_oportunidad` | Historial append-only por `calculo_id` |
| `indice_oportunidad_actual` | Vista de la última corrida |

```sql
SELECT comuna, rubro, oportunidad, n_licencias, explicacion
FROM indice_oportunidad_actual
ORDER BY oportunidad DESC
LIMIT 10;
```

Última corrida: score entre **24,5 y 99,4**, `anio_ref=2025`, fuente SHA-256 `a402df64…9a343`.

### Backtest mínimo

`backtest_oportunidad` entrena solo con datos hasta `anio_corte` y evalúa el año siguiente, sin fuga de información. Resultado de la corrida documentada (corte 2019 → evaluación 2025):

| Métrica | Valor |
|---|---:|
| Filas de entrenamiento | 156.216 |
| Combinaciones comparables | 786 |
| Spearman | **−0,178** |
| top-10 hit rate | **0,00** |

El índice **no anticipa** el crecimiento relativo en esa ventana. La causa principal es la cobertura despareja: 2020, 2021, 2023 y 2024 no traen `descripcion_rubro`, por lo que el cálculo solo puede usar 2015, 2019, 2025 y 2026. Es un backtest descriptivo de una sola ventana, no una validación causal ni un pronóstico.

Fórmula, changelog y criterios de versionado: [`docs/indice_oportunidad_formula.md`](docs/indice_oportunidad_formula.md).

## PostgreSQL

Crear el esquema una vez (requiere permisos de `CREATE`):

```bash
psql "$DATABASE_URL" -f db/schema.sql
python -m src.run_pipeline
```

| Tabla / vista | Grano |
|---|---|
| `habilitaciones` | Una fila por registro del padrón |
| `rubros_requisitos` | Checklist curado por rubro, etapa y trámite |
| `epok_fichas` | Una ficha catastral por SMP enriquecido |
| `codigo_urbanistico` | Una fila por parcela: JSONB completo + columnas aplanadas |
| `urbanismo_smp` | Panel vigente, una fila por SMP |
| `urbanismo_cobertura` | Historial de corridas con reglas y huellas |
| `indice_oportunidad_meta` | Metadatos por corrida del índice |
| `indice_oportunidad` | Scores históricos por `calculo_id` |
| `urbanismo_smp_actual` | Vista del panel vigente |
| `urbanismo_cobertura_actual` | Vista de la última corrida urbanística |
| `urbanismo_habilitaciones` | Vista por habilitación con estado, motivo y perfil EPOK |
| `indice_oportunidad_actual` | Vista de la última corrida del índice |

Consultas de ejemplo:

```sql
-- Distribución de estados por distrito
SELECT familia_distrito, estado_compatibilidad, count(*) AS smp
FROM urbanismo_smp_actual
GROUP BY 1, 2
ORDER BY 1, 2;

-- Habilitaciones con señal de fricción
SELECT solicitud, smp, descripcion_rubro, estado_compatibilidad, regla_id, motivo
FROM urbanismo_habilitaciones
WHERE estado_compatibilidad <> 'compatible'
ORDER BY fecha_habilitacion DESC
LIMIT 20;
```

### Permisos

La carga de `codigo_urbanistico`, `urbanismo_*` e `indice_oportunidad*` requiere `CREATE` sobre el esquema `public` y sobre la base. Si el usuario no lo tiene, los artefactos se escriben igual en disco y la corrida termina con un aviso: no se pierde el resultado. Para habilitar la carga, un administrador debe ejecutar una vez:

```sql
GRANT CREATE ON SCHEMA public TO <usuario>;
GRANT CREATE ON DATABASE innovalab TO <usuario>;
```

Después alcanza con repetir la carga selectiva o el pipeline completo. El repositorio no crea infraestructura ni guarda credenciales.

### Requisitos de rubros

`db/seed/rubros_requisitos.csv` es un **piloto** con requisitos generales y de cafetería (12 filas, 2 rubros), no un catálogo completo:

```sql
SELECT etapa, orden, tramite, obligatorio, documentacion_requerida, organismo, link_oficial
FROM rubros_requisitos
WHERE rubro IN ('General', 'Cafetería')
ORDER BY etapa, orden;
```

## APIs y datos catastrales

`src/apis_gcba.py` incluye clientes para:

- **EPOK:** ficha catastral por SMP o por coordenadas; `enriquecer_epok.py` persiste los resultados en `epok_fichas`.
- **BA Data (CKAN):** búsqueda y consulta de datasets abiertos.
- **USIG:** normalización y geocodificación de direcciones; servicio intermitente y no requerido por el pipeline principal.

El enriquecimiento EPOK se puede ejecutar por lotes y reanudar:

```bash
python src/limpiar_smp.py --dry-run
python src/enriquecer_epok.py --probar
python src/enriquecer_epok.py --limite 500
python src/enriquecer_epok.py
```

## Automatización

El workflow [`.github/workflows/analytics-refresh.yml`](../../.github/workflows/analytics-refresh.yml) permite ejecución manual, corre los lunes a las **09:17 UTC** y se activa con cambios en `data/raw/`, `data/geo/`, `src/`, `db/schema.sql`, `db/seed/` o `requirements.txt` dentro de `data_analytics/innovalab`.

El job instala dependencias, corre `pytest` y ejecuta `python -m src.run_pipeline` con `DATABASE_URL` tomado de los secretos del repositorio. El esquema debe existir previamente y el job no crea infraestructura ni consulta si el GCBA publicó una versión nueva: procesa los archivos versionados en Git (incluidos los de LFS).

## Notebooks

| Notebook | Propósito |
|---|---|
| `01_exploracion_y_limpieza.ipynb` | Pipeline, controles de calidad y EDA del padrón. |
| `02_modelos.ipynb` | Regresión de volumen y clasificación de comuna. |
| `03_clustering_oportunidad.ipynb` | Grupos de comunas e índice de oportunidad. |
| `04_exploracion_y_limpieza_de_codigo_urbanistico.ipynb` | Limpieza del CU, cruce con habilitaciones/EPOK y reglas de compatibilidad reales. |

Resultados exploratorios: en el notebook 02 la clasificación de comuna alcanza **17,7%** de accuracy frente a un baseline de **15,3%**, y el split temporal de la regresión obtiene R² negativo. El notebook 04 predice si el padrón tiene fecha de habilitación registrada; **la ausencia de fecha no significa rechazo**. Los notebooks no son necesarios para la carga programada.

## Pruebas

```bash
python -m pytest tests/ -v
```

La suite cubre contratos de datos, estadística, oportunidad, urbanismo y clientes de APIs. Ejecútala desde `data_analytics/innovalab`. Las pruebas de contrato de `tests/test_data.py` validan `data/processed/habilitaciones_caba_clean.csv`: si el archivo no existe, se omiten; una suite sin omisiones requiere el CSV disponible localmente.

## Limitaciones

- Hay años faltantes en la cobertura histórica; `anio` identifica el archivo de origen y no forma una serie temporal completa.
- La cobertura geográfica depende de la calidad de direcciones y claves del padrón original.
- `superficie` falta o vale cero en la mayoría de los registros; EPOK aporta datos catastrales cuando la SMP se resuelve.
- `descripcion_rubro` falta en 2020, 2021, 2023 y 2024 (esos archivos solo traen `codigo_rubro`); el índice usa únicamente 2015, 2019, 2025 y 2026.
- El índice es orientativo: el backtest da Spearman −0,178 y top-10 hit rate 0,0.
- Los estados urbanísticos son señales de fricción, no permisos ni rechazos. La compatibilidad **no evalúa el rubro** y `compatible` no implica uso permitido.
- La cobertura del cruce urbanístico es parcial: 61,4% de los SMP del padrón tiene fila en el CU y 35,7% de las habilitaciones no puede cruzarse. `no_verificable` refleja esa limitación.
- `rubros_requisitos` cubre solo un piloto de 2 rubros.
- La carga local de las tablas urbanísticas e índice queda bloqueada hasta otorgar los permisos de `CREATE` indicados arriba.

## Documentación

- [`docs/urbanismo_compatibilidad.md`](docs/urbanismo_compatibilidad.md) — reglas, estados, panel, cobertura y versionado.
- [`docs/indice_oportunidad_formula.md`](docs/indice_oportunidad_formula.md) — fórmula, artefacto, backtest y changelog.
- [`db/schema.sql`](db/schema.sql) — esquema completo.
- [`db/seed/reglas_compatibilidad_urbanistica.json`](db/seed/reglas_compatibilidad_urbanistica.json) — reglas `1.0.0`.
