# Enriquecimiento EPOK: cobertura, refresh incremental y alertas

El enriquecimiento EPOK completa el padrón con la ficha catastral oficial de
cada SMP: coordenadas, superficies, frente/fondo, pisos, unidades funcionales y
puertas. Este documento describe el estado operativo, la política incremental,
el dashboard de cobertura y las alertas.

**Última corrida registrada:** 2026-10-28 · reglas de datos sin cambios.

## 1. Estado actual

| Indicador | Valor |
|---|---:|
| Fichas EPOK almacenadas | **19.608** |
| SMP distintos en el padrón | **37.794** |
| Cobertura de SMP resueltos | **51,9%** |
| Habilitaciones con ficha | **100.269 / 216.991 (46,2%)** |
| SMP pendientes | **18.186** |
| Fichas fallidas | **0** |
| Última actualización | **2026-10-14** |
| Antigüedad al 2026-10-28 | **14 días** |

La cobertura es despareja: las comunas 8, 9, 10, 11 y 12 no tienen fichas y
2025 no tiene cobertura. Esas brechas generan alertas y explican por qué el
promedio global está lejos del objetivo del 80%.

## 2. Modelo de datos

`epok_fichas` guarda una fila por SMP:

| Columna | Rol |
|---|---|
| `smp` | Clave primaria en formato `SSS-MMM-PPP[L]` |
| `ficha` | Respuesta completa de EPOK en JSONB |
| `lng`, `lat` | Centroide para mapas |
| `direccion`, `superficie_total`, `superficie_cubierta`, `frente`, `fondo` | Campos consultables |
| `pisos_sobre_rasante`, `unidades_funcionales`, `propiedad_horizontal`, `puertas` | Perfil del inmueble |
| `actualizado_en` | Última ficha **válida** |
| `estado` | `ok` o `fallido` |
| `intentos` | Cantidad de intentos acumulados |
| `ultimo_error` | Motivo del último fallo |
| `ultimo_intento_en` | Fecha del último intento, exitoso o no |

Un fallo posterior a una ficha válida **no borra** `ficha` ni `actualizado_en`:
solo actualiza `estado`, `intentos`, `ultimo_error` y `ultimo_intento_en`. Así
se conserva el último dato bueno y se puede distinguir “sin ficha” de “ficha
vieja con refresh fallido”.

## 3. Política incremental

El enriquecedor lee los SMP distintos de
`data/processed/habilitaciones_caba_clean.csv` y los normaliza con
`limpiar_smp` (`SSS-MMM-PPP[L]`). Luego decide qué consultar:

| Situación | Comportamiento |
|---|---|
| SMP sin fila en `epok_fichas` | Se consulta siempre |
| SMP con `ficha = NULL` y `intentos < --max-intentos` | Se reintenta |
| SMP con `ficha = NULL` e intentos agotados | Se saltea, salvo `--reintentar` |
| SMP resuelto con `actualizado_en` más viejo que `--max-edad-dias` | Se refresca |
| SMP resuelto y fresco | Se saltea |
| `--solo-pendientes` | Solo faltantes y fallidos; no refresca vencidos |
| `--todo` | Fuerza la consulta de todos los SMP del padrón |

Comandos:

```bash
# Dashboard y reporte, sin llamar a EPOK
python src/enriquecer_epok.py --solo-reporte

# Incremental: faltantes + fallidos + fichas vencidas (30 días)
python src/enriquecer_epok.py

# Solo faltantes/fallidos, sin refrescar fichas vencidas
python src/enriquecer_epok.py --solo-pendientes

# Reintentar fallidos que agotaron los intentos
python src/enriquecer_epok.py --reintentar

# Recarga completa
python src/enriquecer_epok.py --todo

# Lote acotado para probar
python src/enriquecer_epok.py --probar
python src/enriquecer_epok.py --limite 500
```

Los lotes se confirman cada 50 SMP, por lo que una interrupción no pierde lo ya
escrito. El proceso es reanudable: la próxima corrida retoma desde el estado
persistido.

## 4. Reintentos y backoff

Cada SMP usa `--reintentos` (default 2) con espera exponencial desde
`--backoff` (default 1,5 s): 1,5 s, 3 s, 6 s… Solo se reintentan timeouts y
errores de red/servidor; un `404` no se reintenta. La API conserva además una
caché en memoria para no repetir consultas dentro del mismo proceso.

```bash
python src/enriquecer_epok.py --reintentos 3 --backoff 2 --limite 100
```

## 5. Reporte y dashboard

Al terminar (o con `--solo-reporte`) se generan:

| Archivo | Contenido |
|---|---|
| `data/processed/epok_cobertura.json` | Cobertura, fichas, cortes por año/comuna, umbrales y alertas |
| `data/processed/epok_dashboard.html` | Dashboard autocontenido, sin JavaScript ni CDN |

Métricas principales:

- `cobertura_smp`: SMP del padrón con ficha / SMP distintos del padrón.
- `cobertura_habilitaciones`: habilitaciones cuyo SMP tiene ficha / total.
- `smp_pendientes`: SMP del padrón sin ficha.
- `fichas.fallidas`: filas con `ficha = NULL`.
- `fichas.desactualizadas`: fichas válidas con antigüedad mayor al SLA.
- `fichas.ultima_actualizacion` y `fichas.antiguedad_dias`.
- Cortes `por_anio` y `por_comuna` con habilitaciones, con SMP y con ficha.

```bash
# Abrir el dashboard localmente
xdg-open data/processed/epok_dashboard.html   # Linux
```

## 6. Alertas

El reporte incluye una lista `alertas` con `codigo`, `nivel`, `mensaje`,
`valor` y `umbral`. Niveles: `critica` y `advertencia`.

| Código | Nivel | Disparador |
|---|---|---|
| `SIN_PADRON` | crítica | El padrón no tiene SMP |
| `SIN_FICHAS` | crítica | No hay ninguna ficha resuelta |
| `SIN_ACTUALIZACION` | crítica | No hay fecha de última actualización |
| `SLA_VENCIDO` | crítica | La última ficha supera `--sla-dias` |
| `COBERTURA_SMP_BAJA` | advertencia | Cobertura SMP < `--alerta-min-cobertura-smp` |
| `COBERTURA_HABILITACIONES_BAJA` | advertencia | Cobertura de habilitaciones < `--alerta-min-cobertura-hab` |
| `FICHAS_DESACTUALIZADAS` | advertencia | Hay fichas válidas vencidas |
| `FICHAS_FALLIDAS` | advertencia | Fallidas > `--alerta-max-fallidas` |
| `COLA_PENDIENTE` | advertencia | Pendientes > `--alerta-max-pendientes` |
| `COMUNAS_SIN_COBERTURA` | advertencia | Comunas con ≥100 habilitaciones y 0% de cobertura |
| `ANIOS_SIN_COBERTURA` | advertencia | Años con ≥100 habilitaciones y 0% de cobertura |

Para usar el reporte como gate de CI:

```bash
python src/enriquecer_epok.py --solo-reporte --fallar-si-alerta
```

Ese comando devuelve código 1 si hay cualquier alerta. Sin el flag, siempre
devuelve 0 y las alertas quedan en el JSON/HTML y en la consola.

## 7. Permisos y migración

Las columnas nuevas se agregan con `db/schema.sql`, que es idempotente. El
usuario de carga necesita ser dueño de `epok_fichas` (o tener `ALTER`). Si la
base fue creada por otro usuario:

```sql
-- Ejecutar como administrador / dueño de la tabla
ALTER TABLE epok_fichas ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'ok';
ALTER TABLE epok_fichas ADD COLUMN IF NOT EXISTS intentos INTEGER NOT NULL DEFAULT 0;
ALTER TABLE epok_fichas ADD COLUMN IF NOT EXISTS ultimo_error TEXT;
ALTER TABLE epok_fichas ADD COLUMN IF NOT EXISTS ultimo_intento_en TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_epok_fichas_actualizado ON epok_fichas (actualizado_en);
CREATE INDEX IF NOT EXISTS idx_epok_fichas_estado ON epok_fichas (estado);
```

`--solo-reporte` funciona incluso sin las columnas nuevas: el reporte deduce
`estado` y `intentos` desde `ficha`. El enriquecimiento sí exige el esquema
actualizado y falla temprano con un mensaje claro si faltan columnas.

## 8. Limitaciones

- La cobertura se calcula contra `data/processed/habilitaciones_caba_clean.csv`,
  no contra una carga previa de `habilitaciones`. Es la fuente que publica el
  pipeline y evita reportar sobre datos viejos de PostgreSQL.
- El dashboard EPOK normaliza los SMP con `limpiar_smp` (relleno de ceros). El
  panel urbanístico usa `normalizar_smp` sin relleno, por eso su métrica de
  EPOK es menor. Unificar ambas normalizaciones queda como deuda técnica.
- `estado = 'fallido'` con `ficha` no nula significa “el último refresh falló,
  pero se conserva la última ficha buena”; no cuenta como ficha faltante.
- Las filas históricas migradas arrancan con `intentos = 0`; el promedio de
  intentos solo es representativo después de la primera corrida nueva.
- No hay SLA contractual con EPOK: el SLA del reporte es el objetivo operativo
  configurado con `--sla-dias`.
- La cobertura por comuna y año muestra brechas reales del operativo, no un
  error del cálculo: comunas 8–12 y 2025 no tienen fichas al 2026-10-28.
