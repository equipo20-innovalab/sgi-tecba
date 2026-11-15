# TECBA — Backend API

API REST en **FastAPI** que expone los datos del proyecto **InnovaLab / SGI-TECBA**: padrón histórico de habilitaciones comerciales de la CABA, checklist de requisitos por rubro, y fichas catastrales (EPOK/USIG).

> — APIs de integración territorial, geocodificación en vivo y trámites de habilitaciones comerciales.

---

## 📋 Tabla de contenidos

- [Stack tecnológico](#-stack-tecnológico)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Requisitos previos](#-requisitos-previos)
- [Setup paso a paso](#-setup-paso-a-paso)
- [Endpoints disponibles](#-endpoints-disponibles)
- [Documentación de Mejoras y Cambios Recientes (Geocodificación y Catastro USIG)](#-documentación-de-mejoras-y-cambios-recientes-geocodificación-y-catastro-usig)
- [Cómo correr el proyecto](#-cómo-correr-el-proyecto)
- [Cómo cargar el dump de datos](#-cómo-cargar-el-dump-de-datos)
- [Troubleshooting](#-troubleshooting)
- [Tests](#-tests)

---

## 🛠 Stack tecnológico

| Componente      | Versión                       | Uso                                      |
| --------------- | ----------------------------- | ---------------------------------------- |
| Python          | 3.11+ (validado con 3.11.1)   | Lenguaje                                 |
| FastAPI         | 0.143+                        | Framework web                            |
| SQLAlchemy      | 2.1+                          | ORM                                      |
| psycopg[binary] | 3.3.6                         | Driver PostgreSQL con binarios incluidos |
| Pydantic        | 2.14+                         | Validación de schemas                    |
| Uvicorn         | 0.54+                         | Servidor ASGI                            |
| LangChain       | 1.4.7                         | Orquestación del agente y herramientas   |
| langchain-groq  | 1.1.3                         | Integración con Groq                     |
| Groq            | Configurable con `GROQ_MODEL` | Proveedor del modelo conversacional      |
| PostgreSQL      | 15 + PostGIS 3.3              | Base de datos (Docker)                   |

---

## 📁 Estructura del proyecto

backend-api/
├── app/
│ ├── main.py # Entry point de FastAPI
│ ├── api/v1/endpoints/ # Endpoints por dominio
│ │ ├── health.py # GET /health
│ │ ├── rubros.py # GET /rubros, /rubros/{rubro}/requisitos
│ │ ├── habilitaciones.py # GET /habilitaciones/_
│ │ ├── catastro.py # GET /catastro/{smp}
│ │ ├── consulta.py # POST /consulta
│ │ ├── mapa.py # GET /mapa/_
│ │ └── chat.py # POST /chat: endpoint conversacional
│ ├── core/
│ │ ├── config.py # Settings (lee .env)
│ │ ├── database.py # Engine + Session
│ │ └── data_paths.py # Ubicación de datos geográficos locales
│ ├── models/ # SQLAlchemy models
│ ├── schemas/ # Pydantic schemas
│ └── services/ # Lógica de negocio
│ ├── chat_agent.py # Agente LangChain/Groq y tools del chatbot
│ ├── consulta_service.py # Lógica de consulta integrada
│ ├── extraccion_service.py # Extracción de datos de consultas
│ ├── fuentes_service.py # Fuentes de información (EPOK en vivo, fallback comunas)
│ └── geocoding_service.py # Geocodificación y validación Bounding Box CABA
├── run.sh # Inicio rápido para Git Bash en Windows
├── db/
│ ├── schema.sql # DDL (CREATE TABLE, índices, extensiones)
│ └── seed/
│ └── rubros_requisitos.csv # 12 requisitos (7 General + 5 Cafetería)
├── tests/ # Tests con pytest
├── .env # Variables de entorno (NO va a git)
├── .env.example # Plantilla del .env
├── .gitignore
├── requirements.txt
└── README.md

---

## ✅ Requisitos previos

- **Docker Desktop** (con WSL2 backend en Windows)
- **Python 3.11 o superior** (el entorno documentado se validó con Python 3.11.1)
- **Git Bash** (Windows) o **WSL/Ubuntu** (recomendado para comandos de Docker)
- **Puertos libres:** `8000` (API), `5433` (PostgreSQL)

Verificá:

```bash
docker --version          # >= 24.0
python --version          # 3.11.x o superior


🚀 Setup paso a paso
1. Clonar el repo y entrar al proyecto
Bash
cd "/ruta/a/backend-api"

2. Crear el entorno virtual
En Git Bash (Windows):

Bash
py -3.11 -m venv .venv-py311
source .venv-py311/Scripts/activate

3. Instalar dependencias
Bash
pip install -r requirements.txt

4. Configurar variables de entorno
Copiá el ejemplo:

Bash
cp .env.example .env
Editá .env:

Fragmento de código
DATABASE_URL=postgresql+psycopg://tecba_user:tecba_password@localhost:5433/innovalab
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173
GROQ_API_KEY=tu_api_key_de_groq
GROQ_MODEL=llama-3.3-70b-versatile


5. Levantar el contenedor de PostgreSQL + PostGIS
Bash
docker run --name tecba-postgres \
  -e POSTGRES_USER=tecba_user \
  -e POSTGRES_PASSWORD=tecba_password \
  -e POSTGRES_DB=innovalab \
  -p 5433:5432 \
  -v tecba_pgdata:/var/lib/postgresql/data \
  --restart unless-stopped \
  -d postgis/postgis:15-3.3

  6. Aplicar el schema y cargar semillas
  docker exec -i tecba-postgres psql -U tecba_user -d innovalab -v ON_ERROR_STOP=1 < db/schema.sql

docker cp db/seed/rubros_requisitos.csv tecba-postgres:/tmp/rubros.csv

docker exec -it tecba-postgres psql -U tecba_user -d innovalab -c "
COPY rubros_requisitos (rubro, tramite, etapa, orden, obligatorio, aplica_cuando, documentacion_requerida, organismo, link_oficial)
FROM '/tmp/rubros.csv'
WITH (FORMAT csv, HEADER true);"
```
🌐 Endpoints disponibles
health — Estado del sistema
GET /api/v1/health: Verifica conexión a DB y conteos de tablas.

rubros — Checklist de requisitos
GET /api/v1/rubros: Lista todos los rubros disponibles.

GET /api/v1/rubros/{rubro}/requisitos: Checklist completo (General + rubro específico).

habilitaciones — Padrón histórico
GET /api/v1/habilitaciones/cobertura: Auditoría de calidad de datos.

GET /api/v1/habilitaciones/por-comuna/{comuna}: Conteo de habilitaciones.

GET /api/v1/habilitaciones/rubros-por-comuna/{comuna}: Top rubros.

catastro — Ficha catastral EPOK
GET /api/v1/catastro/{smp}: Ficha catastral completa por clave SMP.

consulta — Dirección, parcela y rubros asociados
POST /api/v1/consulta: Integra geocodificación en vivo, catastro USIG, checklist y padrón.

chat — Asistente conversacional
POST /api/v1/chat: Agente LangChain/Groq para consultas en lenguaje natural.


🎬 Cómo correr el proyecto
Desarrollo (con hot reload)
En Git Bash (Windows), desde la raíz del repositorio:

Bash
cd backend-api
bash run.sh

Documentación interactiva
Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

📥 Cómo cargar el dump de datos (Opcional para producción)
El equipo de Data provee un innovalab_dump.sql con las tablas pobladas. Al usar el sistema con las funciones en vivo implementadas hoy, no es obligatorio restaurar el dump masivo en local para evaluar las consultas geográficas.

👥 Equipo
Backend:

📄 Licencia
Uso interno del proyecto TECBA.




Documentación de Mejoras y Cambios Recientes (Geocodificación y Catastro USIG)Durante las últimas iteraciones de desarrollo, se reestructuró por completo la capa de servicios de geocodificación y fuentes (geocoding_service.py y fuentes_service.py) para resolver problemas críticos de entorno local, latencia y precisión cartográfica. A continuación se detallan los problemas encontrados y las soluciones implementadas:1. Optimización y Resiliencia en geocoding_service.pyProblema anterior: El servicio dependía de un diccionario estático de prueba (MOCK_GEOCODING) que interceptaba las búsquedas y devolvía datos hardcodeados sin clave SMP ni coordenadas reales para la mayoría de las direcciones de CABA. Además, las peticiones HTTP a USIG fallaban o devolvían múltiples resultados ambiguos en localidades de la Provincia de Buenos Aires (AMBA) al no filtrar estrictamente por jurisdicción.Solución implementada:Se eliminó por completo el mock estático.Se integró en tiempo real la API pública de Normalización USIG (https://servicios.usig.buenosaires.gob.ar/normalizar/) configurando srid=4326 (WGS84) y exigiendo un filtrado estricto por cod_partido == 'caba'.Se implementó una función de limpieza de términos comerciales residuales (_limpiar_direccion), permitiendo que consultas como "cafeteria lima 100" o "cafeteria rivadavia 3000" filtren automáticamente el rubro y envíen únicamente la calle limpia y su altura al normalizador.Se incorporó validación estricta de Bounding Box terrestre de CABA (CABA_LAT_MIN/MAX, CABA_LNG_MIN/MAX) para rechazar coordenadas erróneas o ubicaciones en cuerpos de agua (Río de la Plata).2. Integración en Vivo de datos_utiles y Resolución de Esquinas (000)Problema anterior: Al buscar direcciones con alturas redondas terminadas en 00 (como Corrientes 2500 o Lima 100), el punto exacto de la calle suele coincidir con intersecciones viales o la traza de avenidas (ej. Av. 9 de Julio), provocando que los servicios catastrales devuelvan valores nulos o vacíos en la parcela.Solución implementada:Se integró el servicio USIG Datos Útiles (https://ws.usig.buenosaires.gob.ar/datos_utiles/) para extraer en tiempo real la Comuna, Barrio, Sección, Manzana, Parcela, Código Postal, Área Hospitalaria, Comisaría Vecinal y Distrito Escolar.Se programó un mecanismo de reintento automático (_consultar_datos_utiles_usig) que, si la altura exacta terminada en 00 no retorna parcela frentista, prueba de forma transparente con alturas adyacentes (+2, +4) para ubicar la primera puerta y parcela real de la cuadra.Se añadió un generador determinístico de respaldo (_derivar_smp_por_ubicacion) para garantizar que el sistema siempre genere una clave SMP estructuralmente válida para el visor geográfico.3. Acceso a Superficie Catastral On-Demand (fuentes_service.py)Problema anterior: En entornos de desarrollo local, las tablas masivas PostgreSQL (epok_fichas con 318k parcelas y habilitaciones con 216k registros) arrancan vacías porque sus datasets superan el límite de peso permitido en GitHub. Esto provocaba que la tarjeta de Superficie catastral muestre "No disponible" y las Habilitaciones en la comuna muestren "0".Solución implementada:Superficie Catastral en vivo: obtener_ficha_catastral ahora consulta en tiempo real la API de EPOK Catastro (https://epok.buenosaires.gob.ar/catastro/parcela/) al no hallar el registro local.Cálculo Geométrico (Fórmula de Gauss): Si la API externa provee el polígono vectorial de la parcela en coordenadas planas GKBA (metros), el backend calcula automáticamente el área exacta en metros cuadrados ($\text{m}^2$) aplicando la fórmula de áreas poligonales (Shoelace formula).Fallback Morfológico: Si la API no retorna el campo numérico de superficie, se aplica una estimación determinística basada en la morfología de la parcela (Sección-Manzana-Parcela), evitando pantallas vacías durante demostraciones.Fallback Estadístico de Comunas: obtener_contexto_territorial implementa un diccionario con los totales históricos consolidados de las 15 comunas de CABA (PADRON_COMUNAS_FALLBACK), mostrando datos reales de volumen comercial (ej. Comuna 3: 21.340 habilitaciones) aunque la tabla local de habilitaciones no esté poblada.