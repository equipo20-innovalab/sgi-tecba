# TECBA — Backend API

API REST en **FastAPI** que expone los datos del proyecto **InnovaLab / SGI-TECBA**: padrón histórico de habilitaciones comerciales de la CABA, checklist de requisitos por rubro, y fichas catastrales (EPOK).

> — APIs de integración territorial y trámites de habilitaciones comerciales.

---

## 📋 Tabla de contenidos

- [Stack tecnológico](#-stack-tecnológico)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Requisitos previos](#-requisitos-previos)
- [Setup paso a paso](#-setup-paso-a-paso)
- [Endpoints disponibles](#-endpoints-disponibles)
- [Cómo correr el proyecto](#-cómo-correr-el-proyecto)
- [Cómo cargar el dump de datos](#-cómo-cargar-el-dump-de-datos)
- [Troubleshooting](#-troubleshooting)
- [Tests](#-tests)

---

## 🛠 Stack tecnológico

| Componente | Versión | Uso |
|-----------|---------|-----|
| Python | 3.12+ | Lenguaje |
| FastAPI | 0.143+ | Framework web |
| SQLAlchemy | 2.1+ | ORM |
| psycopg | 3.3+ | Driver PostgreSQL |
| Pydantic | 2.14+ | Validación de schemas |
| Uvicorn | 0.54+ | Servidor ASGI |
| PostgreSQL | 15 + PostGIS 3.3 | Base de datos (Docker) |

---

## 📁 Estructura del proyecto

```
backend-api/
├── app/
│   ├── main.py                    # Entry point de FastAPI
│   ├── api/v1/endpoints/          # Endpoints por dominio
│   │   ├── health.py              # GET /health
│   │   ├── rubros.py              # GET /rubros, /rubros/{rubro}/requisitos
│   │   ├── habilitaciones.py      # GET /habilitaciones/*
│   │   └── catastro.py            # GET /catastro/{smp}
│   ├── core/
│   │   ├── config.py              # Settings (lee .env)
│   │   └── database.py            # Engine + Session
│   ├── models/                    # SQLAlchemy models
│   ├── schemas/                   # Pydantic schemas
│   └── services/                  # Lógica de negocio
├── db/
│   ├── schema.sql                 # DDL (CREATE TABLE, índices, extensiones)
│   └── seed/
│       └── rubros_requisitos.csv  # 12 requisitos (7 General + 5 Cafetería)
├── tests/                         # Tests con pytest
├── .env                           # Variables de entorno (NO va a git)
├── .env.example                   # Plantilla del .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ✅ Requisitos previos

- **Docker Desktop** (con WSL2 backend en Windows)
- **Python 3.12+**
- **Git Bash** (Windows) o **WSL/Ubuntu** (recomendado para comandos de Docker)
- **Puertos libres:** `8000` (API), `5433` (PostgreSQL)

Verificá:

```bash
docker --version          # >= 24.0
python --version          # >= 3.12
```

---

## 🚀 Setup paso a paso

### 1. Clonar el repo y entrar al proyecto

```bash
cd "/ruta/a/backend-api"
```

### 2. Crear el entorno virtual

**En Git Bash (Windows):**
```bash
python -m venv .venv
source .venv/Scripts/activate
```

**En WSL/Ubuntu:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Verificar que se activó:**
```bash
which python           # Debe apuntar a .venv/Scripts/python (o .venv/bin/python)
```

> 💡 **Tip:** si abrís una terminal nueva, **el venv NO está activado**. Volvé a correr `source .venv/Scripts/activate` (o `.venv/bin/activate`).

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copiá el ejemplo:
```bash
cp .env.example .env
```

Editá `.env`:
```env
DATABASE_URL=postgresql+psycopg://tecba_user:tecba_password@localhost:5433/innovalab
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173
```

> ⚠️ **Ojo con el driver `+psycopg`** (psycopg v3). Si ponés `+psycopg2` va a fallar.
> ⚠️ **Ojo con el puerto `5433`** (no `5432`). Usamos 5433 para no chocar con un Postgres nativo.

### 5. Levantar el contenedor de PostgreSQL + PostGIS

```bash
docker run --name tecba-postgres \
  -e POSTGRES_USER=tecba_user \
  -e POSTGRES_PASSWORD=tecba_password \
  -e POSTGRES_DB=innovalab \
  -p 5433:5432 \
  -v tecba_pgdata:/var/lib/postgresql/data \
  --restart unless-stopped \
  -d postgis/postgis:15-3.3
```

**Verificar que arrancó:**
```bash
docker ps
docker logs tecba-postgres | grep "ready to accept connections"
```

### 6. Aplicar el schema

```bash
docker exec -i tecba-postgres psql -U tecba_user -d innovalab -v ON_ERROR_STOP=1 < db/schema.sql
```

**Verificar las tablas:**
```bash
docker exec -it tecba-postgres psql -U tecba_user -d innovalab -c "\dt public.*"
```

Esperado:
```
 public | epok_fichas        | table | tecba_user
 public | habilitaciones     | table | tecba_user
 public | rubros_requisitos  | table | tecba_user
```

### 7. Cargar los rubros (CSV)

```bash
docker cp db/seed/rubros_requisitos.csv tecba-postgres:/tmp/rubros.csv

docker exec -it tecba-postgres psql -U tecba_user -d innovalab -c "
COPY rubros_requisitos (rubro, tramite, etapa, orden, obligatorio, aplica_cuando, documentacion_requerida, organismo, link_oficial)
FROM '/tmp/rubros.csv'
WITH (FORMAT csv, HEADER true);"
```

**Verificar:**
```bash
docker exec -it tecba-postgres psql -U tecba_user -d innovalab -c "
SELECT rubro, count(*) FROM rubros_requisitos GROUP BY rubro;"
```

Esperado:
```
   rubro    | count 
------------+-------
 Cafetería  |     5
 General    |     7
```

### 8. Levantar el backend

```bash
uvicorn app.main:app --reload --port 8000
```

**Salida esperada:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 9. Verificar que todo funciona

**En el navegador:**
- **Swagger UI:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/api/v1/health

**Esperado (health):**
```json
{
  "status": "ok",
  "database": "connected",
  "tablas": {
    "rubros_requisitos": 12,
    "habilitaciones": 0,
    "epok_fichas": 0
  }
}
```

> 📌 **Nota:** los `0` en `habilitaciones` y `epok_fichas` son esperados si todavía no cargaste el dump. Ver la sección [Cómo cargar el dump](#-cómo-cargar-el-dump-de-datos).

---

## 🌐 Endpoints disponibles

### `health` — Estado del sistema

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health` | Verifica conexión a DB + conteos de las 3 tablas |

### `rubros` — Checklist de requisitos

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/rubros` | Lista todos los rubros disponibles |
| GET | `/api/v1/rubros/{rubro}/requisitos` | Checklist completo (General + rubro específico) |

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/rubros/Cafetería/requisitos"
```

Devuelve 12 requisitos ordenados por etapa (`previo → habilitacion → rubro → tributario → operativo`).

### `habilitaciones` — Padrón histórico

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/habilitaciones/por-comuna/{comuna}` | Conteo total de habilitaciones en una comuna |
| GET | `/api/v1/habilitaciones/rubros-por-comuna/{comuna}` | Top rubros habilitados en la comuna |
| GET | `/api/v1/habilitaciones/buscar-cafeterias` | Busca cafeterías/pizzerías (con filtro opcional por comuna) |

**Ejemplos:**
```bash
curl "http://localhost:8000/api/v1/habilitaciones/por-comuna/3"
curl "http://localhost:8000/api/v1/habilitaciones/rubros-por-comuna/3?limit=10"
curl "http://localhost:8000/api/v1/habilitaciones/buscar-cafeterias?comuna=3&limit=50"
```

### `catastro` — Ficha catastral EPOK

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/catastro/{smp}` | Ficha catastral completa por SMP |

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/catastro/001-001-008A"
```

---

## 🎬 Cómo correr el proyecto

### Desarrollo (con hot reload)

```bash
source .venv/Scripts/activate      # Windows
# o
source .venv/bin/activate           # Linux/WSL

uvicorn app.main:app --reload --port 8000
```

### Producción (sin reload)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Documentación interactiva

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## 📥 Cómo cargar el dump de datos

El equipo de Data provee un `innovalab_dump.sql` con las 3 tablas pobladas (`habilitaciones`: 216.991 filas, `epok_fichas`: 19.608 filas).

### ⚠️ Importante: diferencias de versión

El dump viene de **pg_dump 18.3**, pero el contenedor usa **PostgreSQL 15**. Hay que filtrar **3 cosas** antes de restaurar:

1. `\restrict` / `\unrestrict` (meta-comandos nuevos de pg 18)
2. `SET transaction_timeout` (parámetro nuevo de pg 17+)
3. `OWNER TO postgres` (no existe ese rol en el contenedor)

### Procedimiento completo

**En WSL/host**, parado en la raíz del proyecto:

```bash
# 1. Normalizar y filtrar el dump
sed -e 's/\r$//' \
    -e '/^\\restrict /d' \
    -e '/^\\unrestrict /d' \
    -e '/transaction_timeout/d' \
    -e 's/OWNER TO postgres/OWNER TO tecba_user/g' \
    db/innovalab_dump.sql > db/innovalab_dump_clean.sql

# 2. Verificar que se filtró bien
grep -c "OWNER TO postgres" db/innovalab_dump_clean.sql    # debe dar 0
grep -c "restrict" db/innovalab_dump_clean.sql              # debe dar 0

# 3. Copiar al contenedor
docker cp db/innovalab_dump_clean.sql tecba-postgres:/tmp/dump_clean.sql

# 4. Backup preventivo del estado actual
docker exec -it tecba-postgres pg_dump -U tecba_user -d innovalab -F c -f /tmp/backup_pre_restore.backup
docker cp tecba-postgres:/tmp/backup_pre_restore.backup ./backup_pre_restore.backup

# 5. Restaurar
docker exec -it tecba-postgres psql -U tecba_user -d innovalab -v ON_ERROR_STOP=1 -f /tmp/dump_clean.sql

# 6. Verificar
docker exec -it tecba-postgres psql -U tecba_user -d innovalab -c "
SELECT 'rubros_requisitos' AS tabla, count(*) FROM rubros_requisitos
UNION ALL SELECT 'habilitaciones', count(*) FROM habilitaciones
UNION ALL SELECT 'epok_fichas', count(*) FROM epok_fichas;"
```

**Esperado:**
```
     tabla          | count  
--------------------+--------
 rubros_requisitos  |     12
 habilitaciones     | 216991
 epok_fichas        |  19608
```

> 💡 **Los dumps (86 MB c/u) NO van al repo** — están en `.gitignore`. Compartilos por Drive/S3 con el equipo.

---

## 🔧 Troubleshooting

### `psql: error: connection refused` al conectar a la DB

**Causa:** el contenedor no está corriendo o está en otro puerto.

**Solución:**
```bash
docker ps | grep tecba-postgres
# Si no aparece:
docker start tecba-postgres
# Si tenés otro Postgres en 5432, verificá que el contenedor esté en 5433:
docker port tecba-postgres
```

### `ModuleNotFoundError: No module named 'sqlalchemy'`

**Causa:** el venv no está activado.

**Solución:**
```bash
source .venv/Scripts/activate    # Windows
# o
source .venv/bin/activate         # Linux/WSL
which python                      # debe apuntar a .venv
```

### `psycopg.OperationalError: password authentication failed`

**Causa:** la `DATABASE_URL` del `.env` no coincide con las credenciales del contenedor.

**Solución:** verificá que las credenciales sean `tecba_user` / `tecba_password` y la DB `innovalab`.

### `sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgresql.psycopg2`

**Causa:** usaste `postgresql+psycopg2://` en la URL pero tenés `psycopg` v3 instalado.

**Solución:** cambiá a `postgresql+psycopg://` (sin el 2).

### `ERROR: unrecognized configuration parameter "transaction_timeout"`

**Causa:** el dump es de pg 18 y el contenedor es pg 15.

**Solución:** filtrar esa línea con `sed` (ver [Cómo cargar el dump](#-cómo-cargar-el-dump-de-datos)).

### `ERROR: role "postgres" does not exist`

**Causa:** el dump asume el owner `postgres`.

**Solución:** reemplazar `OWNER TO postgres` por `OWNER TO tecba_user` con `sed`.

### VS Code muestra `Import "sqlalchemy.orm" could not be resolved`

**Causa:** VS Code está usando otro intérprete de Python.

**Solución:**
1. `Ctrl + Shift + P` → **`Python: Select Interpreter`**
2. Elegir `./.venv/Scripts/python.exe`
3. Verificar en la barra inferior: `Python 3.14.x ('.venv': venv)`

### `port is already allocated` al levantar el contenedor

**Causa:** tenés otro Postgres corriendo en el puerto 5433.

**Solución:**
```bash
# Ver qué usa el 5433
docker ps --format '{{.Names}}\t{{.Ports}}' | grep 5433
# Detener el que molesta, o cambiar el puerto del contenedor:
docker run ... -p 5434:5432 ...
```

---

## 🧪 Tests

```bash
# Todos los tests
pytest tests/ -v

# Solo un archivo
pytest tests/test_requisitos.py -v

# Con cobertura
pytest tests/ --cov=app --cov-report=html
```

**Estructura esperada:**
```
tests/
├── test_health.py
├── test_requisitos.py
├── test_habilitaciones.py
└── test_catastro.py
```

---

## 👥 Equipo

- **Backend:** 

---

## 📄 Licencia

Uso interno del proyecto TECBA.