# Innovalab — Habilitaciones de comercios de la CABA

Pipeline de datos que **carga, limpia y georreferencia** el padrón de habilitaciones
comerciales de la Ciudad Autónoma de Buenos Aires (exports del portal
[data.buenosaires.gob.ar](https://data.buenosaires.gob.ar), 2015-2026), listo para
consumir desde un backend o un MVP de análisis.

## Estructura del proyecto

```
inovalab_2/
├── data/
│   ├── raw/                  9 CSV crudos del GCBA
│   ├── geo/                  capas oficiales: comunas.geojson, manzanas, callejero
│   └── processed/            salida del pipeline: habilitaciones_caba_clean.csv
├── db/
│   ├── seed/
│   │   └── rubros_requisitos.csv   checklist para abrir un local: requisitos por rubro/etapa
│   └── schema.sql                  DDL de PostgreSQL (rubros_requisitos, habilitaciones, epok_fichas)
├── src/
│   ├── data_loader.py        carga con pathlib (rutas relativas) + detección de separador
│   ├── cleaning.py           armonización de esquemas, filtros, imputaciones y dtypes
│   ├── geografia.py          asignación de comuna (catastro + callejero, join oficial)
│   ├── estadistica.py        cuartiles, outliers (IQR), Gini/Lorenz y χ²
│   ├── modelado.py           datasets de modelos (regresión y clasificación)
│   ├── oportunidad.py        clustering de comunas + índice de oportunidad 0-100
│   ├── apis_gcba.py          clientes de APIs públicas: EPOK, USIG, BA Data
│   ├── limpiar_smp.py        normaliza SMP malformados del padrón (rellena ceros)
│   ├── enriquecer_epok.py    enriquece el padrón con la ficha catastral de EPOK
│   └── export_postgres.py    carga datos hacia PostgreSQL (rubros_requisitos + habilitaciones)
├── notebook/
│   ├── 01_exploracion_y_limpieza.ipynb    orquestador: EDA + auditoría + gráficos + export
│   ├── 02_modelos.ipynb                   regresión (volumen) y clasificación (comuna)
│   ├── 03_clustering_oportunidad.ipynb    KMeans/DBSCAN + índice de oportunidad
│   └── 04_exploracion_y_limpieza_de_codigo_urbanistico.ipynb
│                                           EDA y limpieza del Código Urbanístico de CABA
├── tests/
│   ├── test_data.py           data contract del CSV procesado
│   ├── test_estadistica.py    tests unitarios de cuartiles/Gini (valores conocidos)
│   ├── test_oportunidad.py    clustering, índice y recomendaciones
│   └── test_apis_gcba.py      contratos de los clientes de APIs GCBA
├── requirements.txt
└── README.md
```

## Puesta en marcha

```bash
cd inovalab_2
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Ejecutar el pipeline completo (notebook como orquestador):

```bash
jupyter nbconvert --to notebook --execute --inplace notebook/01_exploracion_y_limpieza.ipynb
```

o bien abrirlo interactivo con `jupyter notebook notebook/01_exploracion_y_limpieza.ipynb`.
Las capas geográficas de `data/geo/` se descargan solas la primera vez (~16 MB).

## El pipeline

| Paso | Módulo | Qué hace |
|------|--------|----------|
| 1 | `src/data_loader.py` | Lee `data/raw/*.csv` (`;`/latin1 con fallback a `,`/utf-8-sig), excluye el archivo no tabular 2022 y agrega `origen`/`anio` |
| 2 | notebook (EDA) | Auditoría de shape, dtypes, nulos y muestras |
| 3 | `src/cleaning.py` | Normaliza nombres de columna, fusiona columnas repetidas (snake_case ↔ CamelCase), mapea el esquema moderno 2025/2026 al común, filtra, imputa, tipa y construye la clave catastral `smp` |
| 4 | `src/geografia.py` | Asigna `comuna` con capas oficiales del GCBA (estrategia híbrida abajo) |
| 5 | notebook | Métricas de control |
| 6 | notebook (gráfico) | EDA visual: series temporales, distribuciones, rubros, nulos y coropleta de comunas |
| 7 | `src/estadistica.py` + notebook | Cuartiles/IQR/outliers de `superficie` y concentración (Gini + Lorenz) por comuna, rubro y trámite |
| 8 | `src/estadistica.py` + notebook | Asociación χ² de independencia y V de Cramér (comuna × rubro, trámite, año) |
| 9 | notebook | Export a `data/processed/` |

## Modelos (notebook 02)

`notebook/02_modelos.ipynb` entrena sobre el CSV procesado (lógica en
`src/modelado.py`):

* **Regresión** del volumen por (comuna, año): R² **0,41** con split aleatorio.
  Con split temporal (entrenar ≤ 2023, probar 2024-2026) el R² es **negativo**:
  `anio` es el año del archivo fuente, no una serie temporal → no sirve para
  pronosticar.
* **Clasificación** de la comuna desde el perfil de actividad (superficie, año,
  trámite y rubro; sin `seccion`/`manzana`/`calles` para no filtrar la regla de
  geocodificación): el mejor modelo llega a **17,7%** de accuracy vs **15,3%** del
  baseline. Confirma la V de Cramér (~0,08): la actividad está repartida pareja
  entre comunas y el rubro no la predice.

## Clustering e índice de oportunidad (notebook 03)

`notebook/03_clustering_oportunidad.ipynb` (lógica en `src/oportunidad.py`)
responde "dónde y qué conviene abrir" sin usar `anio` como serie temporal:

* **Selección de k**: silhouette de KMeans para k=2..8 → **k=5 óptimo (0,38)**.
* **Clustering de comunas** (KMeans y DBSCAN) con features de perfil:
  `n_licencias`, `rubros_distintos`, `superficie_promedio`, `tasa_nuevas`,
  `diversidad_top10`.
* **Índice de oportunidad 0-100** por (comuna × rubro) con tres componentes
  ponderados: **crecimiento** (cuota relativa del rubro en el año, no conteo
  crudo — invariante al sesgo de cobertura de 2015), **baja saturación**
  (rubro vs. media de la comuna) y **subrepresentación** (rubro vs. media de
  la ciudad). Pesos por defecto: 40% / 40% / 20%.
* **Recomendaciones** ordenadas por nota, filtrables por comuna o rubro
  (búsqueda parcial case-insensitive). Ejemplo: comuna 4 / artículos
  personales con crecimiento +27% → nota 96,9.

Limitación: `anio` es el año del archivo fuente, no una serie temporal; el
crecimiento es **tendencia entre el primer y el último año disponible**, no un
pronóstico. Faltan 2016-2018 y 2022 en el padrón.

## Exploración y limpieza del Código Urbanístico (notebook 04)

`notebook/04_exploracion_y_limpieza_de_codigo_urbanistico.ipynb` analiza
`data/raw/codigo-urbanistico.csv` y exporta
`data/processed/codigo_urbanistico_limpio.csv`. La clave `smp` permite cruzar
las parcelas con `epok_fichas` y las habilitaciones.

El análisis revisa estructura y tipos, nulos, duplicados y formato de `smp`, y
explora usos permitidos (`uso_1`), edificabilidad (`uni_edif_1`), factores FOT,
y distribución por comuna. Incluye cuantiles, diagnóstico de valores atípicos
por IQR y gráficos de distribuciones, valores negativos, comunas y faltantes.

La limpieza recorta espacios, convierte marcadores textuales de ausencia en
nulos, normaliza `smp` a mayúsculas y convierte las variables clave a tipos
numéricos. Solo descarta filas sin datos utilizables en `smp`, `uso_1`,
`uni_edif_1`, `fot_em_1` o `comuna`; conserva nulos en columnas opcionales y
dispersas, y no elimina ni corrige automáticamente valores FOT negativos o
candidatos a atípicos. Antes de exportar, valida que `smp` sea completa y única.

Las columnas `dist_*` pueden tener nulos estructurales porque solo aplican a
parcelas en zonas de influencia. Los candidatos identificados por IQR son una
señal para revisar, no errores confirmados.

## APIs públicas del GCBA (`src/apis_gcba.py`)

Clientes de las APIs oficiales del GCBA, con **contratos verificados en vivo**
(oct-2026). Todos degradan con gracia (timeout + retry + `None`) para no tumbar
el pipeline si una API del Estado se cae.

| API | Uso | Estado real |
|-----|-----|-------------|
| **EPOK Catastro** (`/catastro/parcela/?smp=…`) | ficha del inmueble por SMP: **m²** totales/cubiertos, centroide, dirección, partida, puertas | ✅ funciona (JSON) |
| **BA Data** (CKAN `…/api/3/action/…`) | buscar/detalle de datasets (`package_search`, `package_show`); fuente de los CSV | ✅ funciona |
| **USIG normalizar** (`/normalizar/?direccion=…`) | normaliza/geocodifica direcciones | ⚠️ intermitente: a veces responde en <1s, a veces timeout >45s |

Uso rápido:

```python
from src.apis_gcba import consultar_epok_por_smp, metros_cuadrados, buscar_datasets_badata

ficha = consultar_epok_por_smp("01-001-001A")     # -> dict con la ficha catastral
metros_cuadrados(ficha)                             # -> {'total': 1088.0, 'cubierta': 6735.0}
buscar_datasets_badata("habilitaciones")            # -> lista de datasets de BA Data
```

> El pipeline sigue georreferenciando con callejero/catastro (91,8%) y **no
> depende de USIG en vivo**: si USIG no responde, se ignora. Ver `PRODUCTO.md`
> para el alcance por fases de la plataforma.

## Datos de referencia para el backend (`rubros_requisitos`)

Responde la pregunta **"¿qué necesito para abrir un local de X?"**: un
**checklist ordenado por etapa** con todos los requisitos (previos,
habilitación, propios del rubro, tributarios y operativos), la documentación de
cada uno, el organismo y el link oficial. Es una tabla **curada manualmente**
(fuente de verdad: el CSV en `db/seed/`), pensada para que el backend la
consulte con un lookup SQL simple.

| Columna | Descripción |
|---------|-------------|
| `rubro` | `Cafetería`, o `General` si el requisito aplica a cualquier local |
| `tramite` | Requisito/trámite (ej. `Registro de Bromatología`) |
| `etapa` | `previo` → `habilitacion` → `rubro` → `tributario` → `operativo` |
| `orden` | Posición dentro de la etapa (para presentarlo en orden) |
| `obligatorio` | `Obligatorio`, `Opcional` o `Condicional` |
| `aplica_cuando` | Condición si es `Condicional` (NULL si no) |
| `documentacion_requerida` | Documentos que lleva ese requisito |
| `organismo` | Organismo que lo otorga (ej. `AGC`) |
| `link_oficial` | URL del trámite oficial |

**Cobertura actual:** 12 requisitos (7 `General` + 5 de `Cafetería`), que cubren
el recorrido completo de abrir un local gastronómico. Se extiende agregando filas
al CSV (`db/seed/rubros_requisitos.csv`); el upsert evita duplicados.

### Cargar los datos en PostgreSQL

```bash
# 1. Crear las tablas
psql "$DATABASE_URL" -f db/schema.sql

# 2. Cargar el CSV (idempotente: usa UPSERT sobre rubro+tramite)
python src/export_postgres.py

# Opcional: validar sin escribir
python src/export_postgres.py --dry-run
```

Requiere `psycopg` (ya en `requirements.txt`) y la variable `DATABASE_URL`.

### Cómo se consulta (SQL)

El backend conecta con el driver `pg` y una única variable `DATABASE_URL`
(vive en `backend/.env`, que está en `.gitignore` — la clave no se commitea):

```bash
# backend/.env
DATABASE_URL=postgresql://usuario:clave@localhost:5432/innovalab
```

Consulta de ejemplo (el checklist de un rubro, sumando los requisitos `General`):

```sql
SELECT tramite, etapa, obligatorio, documentacion_requerida
  FROM rubros_requisitos
 WHERE rubro IN ('General', 'Cafetería')
 ORDER BY etapa, orden;
```

## Qué preguntas responde esta base de datos

Todo lo que sigue está **cargado y verificado en PostgreSQL**: son las preguntas
de producto que la base contesta hoy, con la consulta SQL que las resuelve.

> **📌 Handoff a Backend (ticket #11 — "API's de integración territorial y
> Trámites de habilitaciones comerciales"):** esta base quedó **lista para que
> el equipo de backend la conecte** y exponga las preguntas de abajo como
> endpoints. El trabajo del lado datos (integración de APIs GCBA + dataset
> histórico, limpieza de SMP, enriquecimiento catastral y checklist de
> requisitos) está completo. La `DATABASE_URL` se pasa por canal seguro (la
> clave **no** va en el repo). **Alcance piloto (MVP):** cubre el caso
> **cafetería / pizzería**; aún no es la totalidad de la ciudad.

### 1. ¿Qué necesito para abrir un local de X? (checklist)
**Tabla:** `rubros_requisitos` · **12 requisitos** (7 `General` + 5 de `Cafetería`),
ordenados por etapa, con documentación, organismo y link oficial.

```sql
SELECT etapa, orden, tramite, obligatorio, aplica_cuando,
       documentacion_requerida, organismo, link_oficial
  FROM rubros_requisitos
 WHERE rubro IN ('General', 'Cafetería')   -- 'Cafetería' = el rubro consultado
 ORDER BY etapa, orden;
```
*Ejemplo de salida:* `[previo] Documentación personal del titular (Obligatorio)`,
`[rubro] Registro de Bromatología (Obligatorio)`, `[rubro] R.I.F.C.I. (Condicional: si hay instalaciones contra incendios)`…

### 2. ¿Cuántas habilitaciones hay en la comuna X?
**Tabla:** `habilitaciones` · **216.991 filas** del padrón de la CABA.

```sql
SELECT count(*) FROM habilitaciones WHERE comuna = 3;
-- o el detalle, filtrando por rubro / año:
SELECT solicitud, descripcion_rubro, superficie, smp, calles, anio
  FROM habilitaciones
 WHERE comuna = 3
   AND unaccent(descripcion_rubro) ILIKE unaccent('%cafetería%')
 ORDER BY anio DESC
 LIMIT 50;
```

### 3. ¿Qué rubros se habilitan en una zona o año?
**Tabla:** `habilitaciones` · agrupaciones por comuna, rubro o año.

```sql
SELECT comuna, count(*) AS habilitaciones
  FROM habilitaciones
 GROUP BY comuna ORDER BY habilitaciones DESC;
```

### 4. ¿Cuántos m² tiene el local de la calle Y? (ficha catastral)
**Tablas:** `habilitaciones` + `epok_fichas` (JOIN por `smp`) · **datos oficiales
de EPOK**: m² reales, coordenadas, pisos. Rellena los casos en que el padrón trae
`superficie = 0`.

```sql
SELECT h.descripcion_rubro, h.calles,
       h.superficie     AS m2_en_padron,
       e.superficie_total AS m2_reales,
       e.lat, e.lng, e.pisos_sobre_rasante
  FROM habilitaciones h
  LEFT JOIN epok_fichas e ON h.smp = e.smp
 WHERE h.smp = '001-001-008A';
-- -> m2_en_padron = 0, pero m2_reales = 495 (dato de EPOK)
```

### 🗺️ Enriquecimiento catastral (EPOK → `epok_fichas`)

Complementa el padrón con la ficha catastral oficial del GCBA por SMP: **coordenadas
(mapa), superficies reales, pisos, unidades y frente/fondo**. Resuelve el caso en
que el dataset trae `superficie = 0` (sin dato) pero el SMP sí existe en catastro.

```bash
# 1. Limpiar SMP malformados (rellena ceros; conserva original en smp_original)
python src/limpiar_smp.py            # --dry-run para ver el alcance

# 2. Enriquecer con EPOK (reanudable; salta SMP ya cargados)
python src/enriquecer_epok.py --probar      # prueba con 3 SMP
python src/enriquecer_epok.py --limite 500  # lote de prueba
python src/enriquecer_epok.py               # todo lo pendiente (~37k SMP)
```

> La limpieza **recupera ~92%** de los SMP malformados del dataset origen. Aun así,
> una parte de los SMP (históricos) ya no existe en el catastro actual y EPOK no los
> resuelve: son filas sin ficha, no un error del proceso.

### 🌐 APIs públicas del GCBA (clientes Python en `src/apis_gcba.py`)

Clientes verificados en vivo (oct-2026), con timeout/retry y degradación a
`None` si una API del Estado se cae. Son del **lado Python** (pipeline):

| API | Qué responde | Uso en el proyecto |
|-----|--------------|--------------------|
| **EPOK Catastro** | ficha del inmueble por SMP: **m²** totales/cubiertos, centroide, dirección, pisos | ✅ materializada en `epok_fichas` (ver sección de enriquecimiento) |
| **BA Data (CKAN)** | catálogo de datasets del GCBA (incluye el padrón de habilitaciones) | metadatos / descargas de datos abiertos |
| **USIG normalizar** | normaliza/geocodifica direcciones (intermitente) | convertir una dirección a coordenadas |

> EPOK ya quedó **materializada en la BD** (`epok_fichas`, cargada por
> `enriquecer_epok.py`): el backend la consulta como una tabla común, sin llamar
> a la API del GCBA en vivo. BA Data y USIG siguen siendo clientes Python.

> El padrón de habilitaciones **no está en el repo** (pesa y `data/` está en
> `.gitignore`): se genera corriendo el pipeline y luego se carga a PostgreSQL
> con `python src/export_postgres.py --habilitaciones`.

### Cómo verificar que los datos están cargados

```bash
# Backend: crear tablas + cargar checklist y padrón
psql "$DATABASE_URL" -f db/schema.sql
python src/export_postgres.py            # rubros_requisitos
python src/export_postgres.py --habilitaciones

# Consultas de control (deben devolver filas)
psql "$DATABASE_URL" -c "SELECT count(*) FROM rubros_requisitos;"   # 12
psql "$DATABASE_URL" -c "SELECT count(*) FROM habilitaciones;"       # 216991
psql "$DATABASE_URL" -c "SELECT count(*) FROM epok_fichas;"          # crece
```

## Tests (data contract)

```bash
python -m pytest tests/ -v
```

54 tests en total. **Data contract (12):** esquema completo, volumen mínimo
(≥ 200k filas), `comuna` ∈ 1..15 con cobertura ≥ 90%, `comuna_fuente` con valores
conocidos, `anio` ∈ 2015..2026, superficie no negativa, techos de nulos por
columna, sin duplicados exactos, fechas parseables ≥ 70% y ≥ 7 archivos de origen.
**Estadística (9):** Gini y Lorenz con valores conocidos, cuartiles y detección de
outliers, χ² y V de Cramér (independencia/asociación perfecta) y agrupación de la
cola. **Oportunidad (22):** normalización, features comuna×rubro (saturación,
crecimiento por cuota), índice 0-100, clustering KMeans/DBSCAN y recomendaciones.
**APIs GCBA (11):** clientes de EPOK/USIG/BA Data con mocks (timeouts, parseo,
degradación). Si uno falla, el pipeline rompió una suposición que asumen el EDA,
los modelos, los exports para RAG y el asistente de oportunidades.

### Estrategia de `comuna` (híbrida, con trazabilidad)

La columna `comuna_fuente` indica qué regla aplicó en cada fila:

1. **`archivo`** — `comuna` ya informada en los exports modernos 2025/2026;
2. **`catastro`** — par `(sección, manzana)` contra `manzanas_catastrales.csv`
   (polígono → punto representativo → punto-en-polígono con `comunas.geojson`);
3. **`callejero`** — nombre oficial de la calle contra `callejero.csv`
   (usa el lado par/impar según la altura de la dirección cuando está disponible);
4. **`callejero_fuzzy`** — coincidencia aproximada (similitud ≥ 0.90 con `difflib`).

## Auditoría: ¿dónde se fueron las ~318.678 filas?

La versión anterior del notebook concatenaba **510.085 filas** y exportaba
**191.407**. La diferencia se explica al 100% así:

| Causa | Filas | % |
|-------|------:|---:|
| Archivos **2025 y 2026** eliminados por `dropna(subset=[solicitud, numero_expediente])`: traen un esquema distinto (`razon_social`, `domicilio`, `comuna`…) sin esas columnas clave | 290.932 | 91,3% |
| **Duplicados exactos** entre exports anuales (superposición con el maestro 2015-2018): 2019: 4.342 · 2020: 8.353 · 2021: 5.713 · 2023: 3.447 · 2024: 5.891 | 27.746 | 8,7% |
| **Total** | **318.678** | **100%** |

Dato irónico: los archivos 2025/2026 eran los **únicos que traían `comuna`**, por lo
que el CSV limpio anterior tenía el 100% de `comuna` vacío y dependía de un mapeo
manual de 8 calles.

**Qué cambia hoy** (contabilidad en vivo en el notebook):

| Archivo | Crudas | Limpias | Descartadas | % retenido |
|---------|-------:|--------:|------------:|-----------:|
| habilitaciones-2015-a-2018.csv | 137.463 | 137.463 | 0 | 100,0% |
| habilitaciones-2019.csv | 23.203 | 18.861 | 4.342 | 81,3% |
| habilitaciones-aprobadas2020.csv | 12.938 | 4.585 | 8.353 | 35,4% |
| habilitaciones-aprobadas2021.csv | 31.829 | 26.117 | 5.712 | 82,1% |
| habilitaciones-aprobadas2023.csv | 5.063 | 1.616 | 3.447 | 31,9% |
| habilitaciones-aprobadas2024.csv | 8.637 | 2.746 | 5.891 | 31,8% |
| habilitaciones-aprobadas2025.csv | 145.457 | 25.601 | 119.856 | 17,6% |
| habilitaciones-aprobadas2026.csv | 145.475 | 2 | 145.473 | 0,0% |
| **Total** | **510.065** | **216.991** | **293.074** | **42,5%** |

Notas:

* **2025/2026 ahora se integran** (antes se perdían enteros): son registros
  modernos sin `solicitud` ni `fecha_habilitacion`, con un renglón por
  observación/comentario. Como el esquema común no incluye `comentarios`, los
  renglones repetidos del mismo local colapsan (145k → ~25,6k únicos).
* Los archivos 2025 y 2026 son snapshots casi idénticos (solo 2 registros
  nuevos en 2026): el dedup entre ambos evita duplicar ~25 mil registros.
* `habilitaciones-aprobadas2022.csv` se excluye: export manual de 20 filas
  tipo `Solicitud;All`, sin estructura tabular.
* El resto de descartes es la superposición normal entre el maestro
  2015-2018 y los dumps anuales 2019-2024 (duplicados exactos).

## Resultados del pipeline

* **510.065 filas crudas** (8 archivos) → **216.991 filas × 20 columnas**.
* **Comuna asignada al 91,8%**: catastro 79,5% · archivo moderno 11,6% ·
  callejero 0,7% · sin dato 8,2% (17.728 filas con dirección/clave catastral
  corrupta en origen: calles numéricas tipo `"1"`, secciones inexistentes, etc.).
* **Clave catastral `smp`** (`seccion-manzana-parcela`) en el 79,7% de las filas,
  lista para cruzar con las APIs del Catastro del GCBA.
* **154.473 trámites con fecha de habilitación** (71,2% del total; los
  archivos modernos no traen fecha por diseño del export). El notebook expone
  ese subconjunto como **`df_habilitados`** para análisis de tiempos de gestión
  y evolución temporal.
* Duración del pipeline completo: **~20 segundos**.

## Esquema de salida (`data/processed/habilitaciones_caba_clean.csv`)

| Columna | Tipo | Observación |
|---------|------|-------------|
| `solicitud` | Int64 | NaN en registros modernos 2025/2026 |
| `tipo_tramite`, `tipo_expediente`, `subtipo_expediente` | str | imputado `"Sin Especificar"` si falta |
| `fecha_habilitacion` | datetime | NaN en registros modernos |
| `numero_expediente`, `partida_matriz` | str/object | |
| `codigo_rubro` | Float64 | el padrón trae ~7,5k códigos con decimales (ej: 1.4): se conservan |
| `descripcion_rubro` | str | en modernos viene del campo `rubro` |
| `superficie` | float | 0 = sin dato |
| `seccion`, `manzana`, `parcela` | str | clave catastral |
| `smp` | str | clave unificada `seccion-manzana-parcela` (79,7% válida; NA si algún componente es inválido) |
| `calles` | str | en modernos viene de `domicilio` |
| `comuna` | Int64 | ver estrategia híbrida |
| `comuna_fuente` | str | trazabilidad: archivo / catastro / callejero / callejero_fuzzy / sin_dato |
| `razon_social` | str | en clásicos viene de `titulares` |
| `origen` | str | archivo fuente |
| `anio` | int | año detectado en el nombre del archivo |

## Limitaciones conocidas

* 8,2% de las filas sin `comuna`: son registros con datos corruptos en origen
  (no hay con qué georreferenciarlos sin geocodificación externa).
* La calle `GRILL` (498 filas) no figura en el callejero oficial del GCBA.
* Los registros modernos 2025/2026 no traen `fecha_habilitacion` ni `solicitud`
  (el export solo indica que fueron aprobados).
