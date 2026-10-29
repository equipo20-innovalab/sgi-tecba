# Datos de demo y restauración

El proyecto completo depende de dos cosas que no siempre están disponibles: un
dump de **~89 MB** versionado con **Git LFS** y un servidor **PostgreSQL 18**.
Para demos, onboarding y CI hay un camino corto que no necesita ni LFS ni el
dump: un **fixture pequeño, reproducible y sanitizado**, servido por
`docker compose` con inicialización automática.

> **Importante:** el fixture es una muestra **pseudonimizada**, no un dataset
> anonimizado ni una fuente oficial. Sirve para probar el esquema, las cargas y
> las consultas; no para inferir negocios reales ni para calcular indicadores
> de producción.

## Ruta y versión

| Elemento | Ruta / versión |
|---|---|
| Directorio del fixture | `data_analytics/innovalab/db/demo/` |
| Versión del fixture | **`1.0.0`** (`FIXTURE.json`) |
| Versión de sanitización | **`1.0.0`** (`FIXTURE.json`) |
| Semilla | **`20261028`** |
| Generador | `scripts/generar_demo.py` |
| Dump de referencia | `db/innovalab_dump.sql` — **pg_dump 18.3**, 89.270.853 bytes |
| Servidor objetivo | **PostgreSQL 18** (probado con 18.6) |
| Script de restore | `scripts/restore_dump.sh` — **`1.1.0`** |
| Workflow | `.github/workflows/analytics-demo-restore.yml` |

Versiones que declara el dump real:

```text
-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3
```

## Contenido del fixture

| Archivo | Filas | Tamaño | SHA-256 (prefijo) |
|---|---:|---:|---|
| `db/demo/habilitaciones_demo.csv` | 150 | ~54 KB | `d0603201…` |
| `db/demo/epok_fichas_demo.csv` | 30 | ~84 KB | `d517f822…` |
| `db/demo/FIXTURE.json` | — | ~1,5 KB | — |

Cobertura de la muestra: **30 SMP**, **10 comunas**, **53 rubros** y los años
**2015 y 2019**. Los 30 SMP de las habilitaciones tienen ficha EPOK, así que el
cruce `habilitaciones ↔ epok_fichas` funciona sin huecos.

Los tres archivos se versionan en **Git normal**, no en LFS: la regla de
`.gitattributes` cubre `data/**/*.csv`, `data/**/*.geojson` y
`db/innovalab_dump.sql`, no `db/demo/`.

### Sanitización `1.0.0`

Se reemplazan los identificadores directos:

| Campo | Reemplazo |
|---|---|
| `solicitud` | `9000001`, `9000002`, … |
| `numero_expediente` | `EX-2026-DEMO-000001`, … |
| `razon_social` | `EMPRESA DEMO 0001`, … |
| `partida_matriz` | `DEMO-000001`, … |

Se conservan los campos necesarios para que los cruces y las consultas sigan
teniendo sentido: `smp`, `comuna`, `codigo_rubro`, `descripcion_rubro`,
`superficie`, `calles`, `seccion`/`manzana`/`parcela`, fechas, `origen` y
`anio`.

Una combinación de SMP, rubro y fecha puede seguir siendo singular: por eso el
fixture es **pseudonimizado**, no anonimizado. No se usa para inferir la
actividad de un local real.

### Regenerar el fixture

Los CSV son deterministas para la misma semilla y la misma fecha de corte:

```bash
cd data_analytics/innovalab

# Requiere el padrón procesado y, para EPOK, acceso a la base
python scripts/generar_demo.py --fecha 2026-10-28T00:00:00+00:00

# Sin base de datos (solo padrón; útil en CI y tests)
python scripts/generar_demo.py --sin-epok --fecha 2026-10-28T00:00:00+00:00
```

Opciones: `--filas` (default 150), `--smps` (default 30), `--semilla`
(default 20261028), `--entrada`, `--salida`.

El generador normaliza los SMP con `src/limpiar_smp.py`, elige la muestra de
forma estratificada por comuna priorizando parcelas con varias habilitaciones y
solo incluye filas con SMP, fecha, rubro y comuna. Al terminar escribe
`FIXTURE.json` con conteos y hashes, que es lo que valida la suite de tests.

## Base de demo con Docker Compose

```bash
cd data_analytics/innovalab
docker compose up -d --wait
```

Al primer arranque, la imagen `postgres:18` ejecuta en orden:

1. `db/schema.sql` → tablas, índices y vistas.
2. `db/demo/init_demo.sql` → carga `rubros_requisitos`, `habilitaciones` y
   `epok_fichas` desde los CSV.

Verificar:

```bash
psql "postgresql://innovalab:innovalab_demo@localhost:55432/innovalab" \
     -v ON_ERROR_STOP=1 -f db/demo/verificar_demo.sql
```

Resultado esperado:

```text
NOTICE:  Fixture OK: 150 habilitaciones, 30 fichas EPOK, 12 requisitos
     tabla       | count
-----------------+-------
 habilitaciones  |   150
 epok_fichas     |    30
 rubros_requisitos |  12
```

Variables y ciclo de vida:

| Variable | Default |
|---|---|
| `INNOVALAB_PG_PORT` | `55432` |
| `INNOVALAB_DB` | `innovalab` |
| `INNOVALAB_USER` | `innovalab` |
| `INNOVALAB_PASSWORD` | `innovalab_demo` |

```bash
docker compose down      # conserva el volumen
docker compose down -v   # borra también los datos
```

El volumen se monta en `/var/lib/postgresql` (no en
`/var/lib/postgresql/data`) porque **PostgreSQL 18** movió `PGDATA` a
`/var/lib/postgresql/18/docker`. Montar el padre funciona también con imágenes
anteriores.

`init_demo.sql` usa `\cd` + `\copy` con rutas relativas: dentro de Docker toma
`/docker-entrypoint-initdb.d/demo` y `/docker-entrypoint-initdb.d/seed`, y
fuera de Docker acepta `-v demo_dir=... -v seed_dir=...`. Con
`-v demo_limpiar=1` vacía las tablas antes de cargar.

## Restaurar el dump real

El dump sigue fuera de Git normal. Antes de restaurar hay que tener el archivo
real, no el puntero LFS:

```bash
git lfs install
git lfs pull --include="data_analytics/innovalab/db/innovalab_dump.sql"
head -3 data_analytics/innovalab/db/innovalab_dump.sql   # debe empezar con "--"
```

Después:

```bash
cd data_analytics/innovalab
scripts/restore_dump.sh --info                     # versiones y compatibilidad
scripts/restore_dump.sh --dsn "$DATABASE_URL"      # restaurar + verificar conteos
```

Qué hace el script `1.1.0`:

1. Detecta si el archivo es un **puntero de Git LFS** y explica cómo bajarlo.
2. Compara la versión mayor del dump con la del servidor destino.
3. Elimina `\restrict` / `\unrestrict` (meta-comandos de `psql` 18).
4. Elimina `SET transaction_timeout` si el destino es anterior a PostgreSQL 17.
5. Reasigna `OWNER TO` al rol que restaura (evita `role "postgres" does not exist`).
6. Restaura con `--single-transaction`: si algo falla, no deja la base a medias.
7. Opcionalmente aplica `db/schema.sql` con `--con-esquema`.
8. Cuenta filas por tabla al final.

| Opción | Efecto |
|---|---|
| `--dsn DSN` | Cadena de conexión (default: `DATABASE_URL` o `dbname=innovalab`) |
| `--owner ROL` | Dueño de los objetos restaurados (default: usuario actual) |
| `--solo-filtrar` | Escribe el dump filtrado sin conectar |
| `--salida ARCHIVO` | Destino de `--solo-filtrar` |
| `--servidor-major N` | Fuerza la versión mayor del destino (pruebas) |
| `--con-esquema` | Aplica `db/schema.sql` después de restaurar |
| `--sin-transaccion` | Sin `--single-transaction` |
| `--sin-verificar` | Omite el conteo final |
| `--esperar SEGUNDOS` | Espera máxima al servidor (default 30) |
| `--info` | Muestra versiones y estado, sin restaurar |

Códigos de salida: `0` OK · `2` uso o archivo inválido · `3` puntero LFS o dump
ilegible · `4` error de `psql`.

Conteos de referencia del dump completo restaurado: **216.991**
habilitaciones, **19.608** `epok_fichas` y **12** `rubros_requisitos`.

## CI

`.github/workflows/analytics-demo-restore.yml` tiene cuatro jobs:

| Job | Cuándo | Qué prueba |
|---|---|---|
| `fixture` | push / PR | Tests del fixture y del script sin base ni Docker |
| `compose` | push / PR | `docker compose up` real y comparación con `FIXTURE.json` |
| `restore-demo` | push / PR | `pg_dump` 18 real → `restore_dump.sh` → verificación |
| `restore-full` | manual | Dump de 89 MB con LFS y conteos históricos |

`restore-full` se dispara a mano (`workflow_dispatch` con
`restaurar_dump_completo=true`) porque depende de que los objetos LFS estén
subidos al remoto. Si el checkout sigue trayendo el puntero, el job falla con un
mensaje que indica cómo subirlos:

```bash
git lfs install
git lfs push --all origin main
```

## Límites conocidos

- El fixture es una **muestra**, no el padrón: los indicadores que se calculen
  con él no son comparables con los de producción.
- La sanitización es **pseudonimización**. No hay garantía de resistencia a
  reidentificación por combinación de cuasi-identificadores.
- Las fichas EPOK del fixture están **compactadas**: la respuesta completa de
  la API puede pesar cientos de KB por parcela y no aporta a la demo.
- El dump real es **PostgreSQL 18.3**; restaurarlo en versiones anteriores
  funciona gracias al filtrado del script, pero no está garantizado para
  objetos que no existían antes (por ejemplo, cambios de catálogo).
- `restore-full` no crea infraestructura: usa el servicio PostgreSQL del
  runner.
- El proyecto no guarda credenciales. `docker compose` usa una clave de demo
  explícitamente insegura y solo para uso local.
