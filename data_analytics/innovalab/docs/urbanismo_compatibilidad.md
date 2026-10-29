# Compatibilidad urbanística: Código Urbanístico + habilitaciones + EPOK

Este documento describe la integración del Código Urbanístico (CU) limpio con el
padrón de habilitaciones y las fichas catastrales EPOK. El resultado es un panel
por SMP, un reporte de cobertura y un conjunto de **reglas de compatibilidad
explícitas y versionadas**.

> **Advertencia:** la compatibilidad es orientativa. **No** constituye permiso de
> uso, habilitación comercial, aptitud legal ni asesoramiento profesional.
> `compatible` solo significa "no se detectaron señales de fricción en los campos
> disponibles". El Código Urbanístico no publica un campo de "uso permitido por
> rubro": `uso_1/2/3` son **mixtura de uso** y no deben leerse como autorización.

## 1. Entradas

| Fuente | Archivo / tabla | Filas | Rol |
|---|---|---|---|
| Código Urbanístico limpio | `data/processed/codigo_urbanistico_limpio.csv` | 318.126 | Atributos normativos por parcela (52 columnas) |
| Habilitaciones | `data/processed/habilitaciones_caba_clean.csv` | 216.991 | Demanda y antecedentes por SMP |
| Fichas EPOK | tabla `epok_fichas` | 19.608 | Perfil catastral (superficie, pisos, coordenadas) |
| Reglas | `db/seed/reglas_compatibilidad_urbanistica.json` | 12 reglas | Estados de compatibilidad, versión `1.0.0` |

La clave de cruce es `smp` (Sección-Manzana-Parcela). La normalización solo
recorta espacios, unifica mayúsculas y guiones tipográficos. **No completa
dígitos faltantes**: hacerlo generaría cruces falsos entre fuentes.

## 2. Validación de SMP

Cada SMP se clasifica en una de cinco categorías:

| Clasificación | Significado | CU (filas) | Habilitaciones (filas) |
|---|---|---|---|
| `estandar` | Sección-Manzana-Parcela numéricos, con letra opcional al final de manzana/parcela | 316.836 | 141.126 |
| `ampliado` | Manzana/parcela con longitudes no estándar o caracteres fuera de `A-Z` (p. ej. `Ñ`) | 110 | 4.267 |
| `placeholder` | Parcela en ceros (`...-000` / `...-0000`); no identifica una parcela real | 1.180 | 917 |
| `invalido` | Tiene contenido pero no cumple ningún formato catastral | 0 | 26.529 |
| `sin_dato` | Nulo o marcador de ausencia | 0 | 44.152 |

Solo `estandar` y `ampliado` se consideran SMP utilizables. Los `placeholder`
se toleran en el CU porque existen en la fuente oficial, pero se controla su
proporción (`max_placeholder=0.01` en `validar_codigo_urbanistico`). Un SMP
`invalido` en el CU siempre es un error de contrato.

## 3. Reglas de compatibilidad

### 3.1 Motor y precedencia

- Las reglas viven en `db/seed/reglas_compatibilidad_urbanistica.json`, con
  `version`, `fecha`, `advertencia`, `estados` y una lista `reglas`.
- Cada regla declara `id`, `prioridad`, `estado`, `cuando` y `motivo`.
- Se evalúan en orden ascendente de `prioridad`; el orden del archivo desempata.
- **La primera regla que coincide gana.** Si ninguna coincide, el estado es
  `no_verificable` (criterio conservador).
- El bloque `cuando` combina condiciones con AND. Formatos admitidos:
  - lista de valores: pertenencia (`in`);
  - booleano o escalar: igualdad;
  - objeto de operadores: `eq`, `ne`, `in`, `not_in`, `gte`, `lte`, `es_nulo`.

### 3.2 Estados

| Estado | Significado |
|---|---|
| `compatible` | Sin señales de fricción en los campos disponibles. **No implica que el rubro esté permitido.** |
| `requiere_revision` | Hay una señal que exige revisión humana o normativa adicional (patrimonio, riesgo, distrito especial, línea de edificación, datos faltantes). |
| `no_compatible` | La parcela está afectada por una condición urbanística declarada (espacio público, futura apertura o futuro ensanche). |
| `no_verificable` | No se puede identificar o verificar la parcela: SMP ausente/placeholder/inválido o SMP sin fila en el CU. |

### 3.3 Reglas versión 1.0.0 (2026-10-28)

| Prioridad | `id` | Estado | Condición |
|---:|---|---|---|
| 10 | `SMP_NO_VERIFICABLE` | `no_verificable` | `smp_clasificacion` ∈ {`sin_dato`, `placeholder`, `invalido`} |
| 20 | `CU_AUSENTE` | `no_verificable` | `codigo_presente = false` |
| 30 | `ESPACIO_PUBLICO` | `no_compatible` | `familia_distrito = ESPACIO_PUBLICO` |
| 31 | `AFECTACION_APERTURA` | `no_compatible` | `apertura = true` |
| 32 | `AFECTACION_ENSANCHE` | `no_compatible` | `ensanche = true` |
| 40 | `PATRIMONIO_CATALOGADO` | `requiere_revision` | `catalogado = true` |
| 41 | `RIESGO_HIDRICO` | `requiere_revision` | `riesgo_hidrico = true` |
| 42 | `LINEA_EDIFICACION` | `requiere_revision` | `linea_edificacion_particularizada = true` |
| 43 | `CONO_AEROPARQUE` | `requiere_revision` | `cono_aeroparque = true` |
| 50 | `DISTRITO_ESPECIAL` | `requiere_revision` | `familia_distrito` ∈ {`APH`, `U`, `UP`, `UF`, `AE`, `RUA`, `EE`, `AREA_RENOVACION`, `otro`} |
| 51 | `DISTRITO_SIN_DATO` | `requiere_revision` | `familia_distrito = sin_dato` |
| 99 | `SIN_SENALES_DE_FRICCION` | `compatible` | sin condición (fallback) |

Las familias de distrito se derivan de `dist_1_grp`: `APH*` → `APH`, `UP*` → `UP`,
`U` → `U`, `UF*` → `UF`, `AE*` → `AE`, `RUA*` → `RUA`, `EE*` → `EE`,
`Espacio Publico*` → `ESPACIO_PUBLICO`, `Area de Renovacion*` →
`AREA_RENOVACION`, vacío/`Sin dato` → `sin_dato`, resto → `otro`.

### 3.4 Flags del Código Urbanístico

| Columna CU | Booleano del panel | Interpretación |
|---|---|---|
| `catalogado` | `catalogado` | Edificio catalogado (protección patrimonial) |
| `rh` | `riesgo_hidrico` | Riesgo hídrico |
| `lep` | `linea_edificacion_particularizada` | Línea de edificación particularizada |
| `ensanche` | `ensanche` | Afectación a futuro ensanche |
| `apertura` | `apertura` | Afectación a futura apertura |
| `anac` | `cono_aeroparque` | Cono de aproximación Aeroparque |
| `ci_digital` | `cinturon_digital` | Cinturón digital |
| `rivolta` | `altura_esquina_rivolta` | Altura especial de esquina (Rivolta) |

Los flags ausentes quedan como `NA`, no como `false`: interpretar un faltante
como "sin afectación" ocultaría datos faltantes.

`dist_cpu_1` pertenece al Código de Planeamiento Urbano **derogado**. Se conserva
como contexto y el panel lo marca explícitamente con `dist_cpu_1_vigente=false`.

## 4. Artefactos

`python src/export_postgres.py --codigo-urbanistico` escribe, antes de intentar
la carga en PostgreSQL:

| Artefacto | Contenido |
|---|---|
| `data/processed/urbanismo_smp.csv` | Panel de una fila por SMP (44 columnas), con clasificación, presencia CU/EPOK, agregados de habilitaciones, flags, estado, regla, motivo y versión |
| `data/processed/urbanismo_cobertura.json` | Resumen de cobertura, distribuciones, flags, fuentes con SHA-256, versión/huella de reglas y limitaciones |

El JSON incluye el SHA-256 del CSV recién escrito (`artefacto.sha256`) para
verificar que ambos artefactos corresponden a la misma corrida. La escritura es
atómica (archivo temporal + rename).

Corrida del **2026-10-29T00:37Z** (reglas `1.0.0`, sha256
`62fe266f94d87ed8da9a6a36865c36d50e35fd0593d0107e60b0c44b8ea92791`):

- Panel: **335.569 SMP** · CSV sha256
  `44095af23d054dbb04006789f5b9e8a90679e07dbc94176ca42407cdfeaaa6e3`.
- Cobertura de SMP de habilitaciones en el CU: **27.709 / 45.152 = 61,4%**.
- Uso del CU por parte de habilitaciones: **27.709 / 318.126 = 8,7%**.
- Habilitaciones con fila en CU: **139.643 / 216.991 = 64,3%**.
- Habilitaciones con ficha EPOK: **82.210 / 216.991 = 37,9%** (todas ellas también
  tienen fila en CU). El dashboard EPOK normaliza los SMP con relleno de ceros y
  reporta 100.269 (46,2%); esta tabla usa la clave sin relleno del panel. Ver
  [`epok_enriquecimiento.md`](epok_enriquecimiento.md).
- Habilitaciones sin SMP: **44.152 = 20,3%**.

Estados por SMP (335.569):

| Estado | SMP | % |
|---|---:|---:|
| `compatible` | 187.142 | 55,8% |
| `requiere_revision` | 128.124 | 38,2% |
| `no_compatible` | 1.680 | 0,5% |
| `no_verificable` | 18.623 | 5,5% |

Estados por habilitación (216.991):

| Estado | Habilitaciones | % |
|---|---:|---:|
| `compatible` | 96.829 | 44,6% |
| `requiere_revision` | 40.624 | 18,7% |
| `no_compatible` | 1.844 | 0,8% |
| `no_verificable` | 33.542 | 15,5% |
| `sin_smp` | 44.152 | 20,3% |

Lectura honesta:

- El 55,8% de `compatible` **no** es una tasa de aprobación ni de aptitud: mide
  ausencia de señales en los campos disponibles.
- El 38,2% de `requiere_revision` está dominado por distritos especiales (AE,
  U, APH, RUA, etc.) y por riesgo hídrico/patrimonio; no implica rechazo.
- El 35,7% de las habilitaciones no tiene fila en el CU: sin CU el estado es
  `no_verificable`. La cobertura de claves es la principal limitación del cruce.

## 5. PostgreSQL

El esquema (`db/schema.sql`) agrega:

- `codigo_urbanistico`: fila completa del CU en JSONB (`datos`) más columnas
  aplanadas consultables (`smp`, `comuna`, `dist_1_grp`, `uso_1`, flags, FOT,
  edificabilidad, `dist_cpu_1`, etc.).
- `urbanismo_cobertura`: historial append-only de corridas (reglas, huellas,
  métricas y distribuciones).
- `urbanismo_smp`: panel vigente, una fila por SMP; se recarga en cada corrida.
- `urbanismo_smp_actual`: vista del panel vigente.
- `urbanismo_cobertura_actual`: vista de la última corrida.
- `urbanismo_habilitaciones`: vista por habilitación con el estado, el motivo y
  el perfil EPOK cuando existe.

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

La carga requiere privilegios de `CREATE` sobre el esquema `public`. Si el
usuario no los tiene, los artefactos quedan escritos en disco y la corrida
termina con un aviso (no se pierde el resultado).

Estado de la corrida local del **2026-10-29**: la escritura de artefactos fue
exitosa, pero la carga falló con `InsufficientPrivilege: permiso denegado al
esquema public` porque el usuario `matias17` no tiene `CREATE` en `public` ni en
la base (el dueño es `postgres`). Para habilitar la carga, un administrador debe
ejecutar una vez:

```sql
GRANT CREATE ON SCHEMA public TO matias17;
GRANT CREATE ON DATABASE innovalab TO matias17;
```

Después alcanza con repetir `python src/export_postgres.py --codigo-urbanistico`.

## 6. Reproducción

```bash
# Solo validar y calcular (no escribe artefactos ni BD)
python src/export_postgres.py --codigo-urbanistico --dry-run

# Generar artefactos y cargar en PostgreSQL (si hay permisos)
python src/export_postgres.py --codigo-urbanistico

# Generar artefactos sin consultar EPOK (base sin enriquecimiento)
python src/export_postgres.py --codigo-urbanistico --sin-epok

# Usar otra versión/archivo de reglas
python src/export_postgres.py --codigo-urbanistico --reglas db/seed/reglas_compatibilidad_urbanistica.json
```

Pruebas: `python -m pytest tests/test_urbanismo.py -v`.

## 7. Versionado de reglas

- Cambiar cualquier regla, prioridad o estado exige subir `version` y `fecha`
  en el JSON; la versión queda registrada en el panel, la cobertura y la BD.
- `cargar_reglas(..., version="1.0.0")` falla si el archivo declara otra versión,
  para que un pipeline no mezcle reglas silenciosamente.
- La huella SHA-256 del archivo de reglas se guarda en `urbanismo_cobertura` y en
  el JSON, de modo que un resultado siempre puede rastrearse a las reglas usadas.
- Próximas versiones deberían agregar reglas por rubro solo si existe una fuente
  normativa oficial que relacione rubro y uso; hoy no la hay en estos datos.

## 8. Limitaciones

- `compatible` no es permiso de uso ni habilitación; el uso admitido depende del
  rubro y de normativa que estos datasets no publican por parcela.
- `uso_1/2/3` son mixtura de uso, no autorización de rubro.
- `dist_cpu_1` corresponde al CPU derogado; se conserva como contexto.
- Un `placeholder` (parcela `000`) no identifica una parcela real.
- La ausencia de ficha EPOK no implica que la parcela no exista.
- La cobertura del cruce es parcial: 61,4% de los SMP del padrón tienen fila en
  el CU y solo 8,7% del CU se usa en habilitaciones. Los estados
  `no_verificable` reflejan esa limitación, no un rechazo.
- Las reglas describen señales de fricción observables con estos campos; no
  reemplazan la consulta al Código Urbanístico vigente, al catastro ni a la
  autoridad de aplicación.
