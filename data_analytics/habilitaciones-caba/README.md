# Inovalab — Habilitaciones de comercios de la CABA

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
├── src/
│   ├── data_loader.py        carga con pathlib (rutas relativas) + detección de separador
│   ├── cleaning.py           armonización de esquemas, filtros, imputaciones y dtypes
│   ├── geografia.py          asignación de comuna (catastro + callejero, join oficial)
│   ├── estadistica.py        cuartiles, outliers (IQR), Gini/Lorenz y χ²
│   └── modelado.py           datasets de modelos (regresión y clasificación)
├── notebook/
│   ├── 01_exploracion_y_limpieza.ipynb   orquestador: EDA + auditoría + gráficos + export
│   └── 02_modelos.ipynb                  regresión (volumen) y clasificación (comuna)
├── tests/
│   ├── test_data.py          data contract del CSV procesado
│   └── test_estadistica.py   tests unitarios de cuartiles/Gini (valores conocidos)
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

## Tests (data contract)

`tests/test_data.py` valida el CSV procesado antes de cualquier modelo:

```bash
python -m pytest tests/ -v
```

21 tests en total. **Data contract (12):** esquema completo, volumen mínimo
(≥ 200k filas), `comuna` ∈ 1..15 con cobertura ≥ 90%, `comuna_fuente` con valores
conocidos, `anio` ∈ 2015..2026, superficie no negativa, techos de nulos por
columna, sin duplicados exactos, fechas parseables ≥ 70% y ≥ 7 archivos de origen.
**Estadística (9):** Gini y Lorenz con valores conocidos, cuartiles y detección de
outliers, χ² y V de Cramér (independencia/asociación perfecta) y agrupación de la
cola. Si uno falla, el pipeline rompió una suposición que asumen el EDA, los
modelos y los exports para RAG.

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
