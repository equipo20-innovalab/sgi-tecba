# 🧪 QA & Testing — SGI TECBA

Bienvenido al módulo oficial de **Aseguramiento de Calidad (QA)** del proyecto **SGI TECBA** (*Sistema de Gestión Inteligente de Habilitaciones Comerciales - CABA*).

Este directorio centraliza la estrategia de pruebas, la matriz de 14 casos funcionales y la suite completa de pruebas automatizadas (+100 tests) para la API, el visor territorial y el Asistente Inteligente.

---

## 📁 Estructura del Módulo de QA

```text
tester/
├── README.md                 # Documento maestro del plan de QA (este archivo)
├── manual/                   # Matriz y especificación de casos de prueba funcionales
│   └── casos_de_prueba.md    # Detalle de los 14 casos (CP-01 a CP-14)
├── api_automation/           # Suite automatizada de pruebas con Pytest (+100 tests)
│   ├── conftest.py           # Fixtures globales, cliente HTTP y carga de entorno
│   ├── test_health.py        # Salud de la API y verificación de tablas en DB
│   ├── test_rubros.py        # Checklist por rubro, validación de etapas y errores 404
│   ├── test_habilitaciones.py# Padrón de habilitaciones, comunas y paginación
│   ├── test_catastro.py      # Fichas catastrales EPOK por SMP y coordenadas
│   ├── test_consulta.py      # Orquestador /consulta (lenguaje natural y estructurado)
│   ├── test_mapa.py          # GeoJSON comunal, parcelas y validación de bbox
│   ├── test_extraccion.py    # PLN: Detección formal, informal, esquinas y SMP (CP-01 a CP-04)
│   └── test_chat.py          # Chatbot: Seguridad, guardrails, plazos y prompt injection (CP-07 a CP-09)
└── reports/                  # Reportes de ejecución, capturas y evidencias
```

---

## 🎯 Alcance de Pruebas Automatizadas

| Módulo | Archivo | Cantidad | Casos Cubiertos / Qué Valida |
| :--- | :--- | :---: | :--- |
| **Extracción y Lenguaje** | `test_extraccion.py` | 8 | **CP-01 a CP-04, CP-10:** Lenguaje formal, modismos (*café y medialunas*), regla de altura (no adivina coordenadas) y cruces. |
| **Chatbot & Guardrails** | `test_chat.py` | 19 | **CP-07 a CP-09, CP-13:** Anti-alucinación (NASA), preguntas fuera de tema (recetas), prompt injection (boliche), plazos y contexto activo. |
| **Consulta Inteligente** | `test_consulta.py` | 11 | **CP-05:** Endpoint central `/consulta` en modo natural y estructurado, schemas de ubicación y rechazo 422 de payloads vacíos. |
| **Resiliencia y Fuentes** | `test_health.py` | 5 | **CP-06:** HTTP 200, status `ok`/`error`, conteos no negativos y presencia de las 4 tablas en DB. |
| **Rubros y Requisitos** | `test_rubros.py` | 13 | Listado de rubros, checklist de Cafetería (12) y General (7), tildes y retorno 404 en rubros inexistentes. |
| **Habilitaciones** | `test_habilitaciones.py` | 22 | **CP-12:** Métricas de cobertura, totales por comuna (1 a 15), top rubros y validaciones 422 de límites. |
| **Catastro (EPOK)** | `test_catastro.py` | 6 | **CP-10:** Búsqueda por SMP, estructura de ficha catastral, coordenadas flotantes válidas y errores 404/422. |
| **Visor Geográfico** | `test_mapa.py` | 25 | **CP-11:** GeoJSON comunal, parcelas paginadas, filtros por rubro/comuna y límites geográficos de Bounding Box. |

---

## 📋 Matriz de Casos Funcionales (Manuales)
El detalle paso a paso, precondiciones y criterios de aceptación de los 14 casos de prueba se encuentra en:  
👉 [**`tester/manual/casos_de_prueba.md`**](manual/casos_de_prueba.md)

---

## 🚀 Cómo Ejecutar la Suite Automatizada

### 1. Requisitos Previos
* Tener la base de datos levantada en Docker:
  ```bash
  docker ps  # tecba-postgres en puerto 5433
  ```
* Contar con el entorno virtual de Python activo.

### 2. Comandos de Ejecución (desde la raíz del repositorio)

```bash
# Correr toda la suite de pruebas completa:
backend-api/.venv/bin/pytest tester/api_automation -v

# Correr solo las pruebas del Chatbot y Seguridad de IA:
backend-api/.venv/bin/pytest tester/api_automation/test_chat.py -v

# Correr solo las pruebas de Entendimiento de Lenguaje:
backend-api/.venv/bin/pytest tester/api_automation/test_extraccion.py -v

# Correr con reporte de cobertura de código:
backend-api/.venv/bin/pytest tester/api_automation -v --cov=app --cov-report=term-missing
```

### 3. Generar Reporte Visual en HTML
Para generar un reporte HTML interactivo con el porcentaje de cobertura y guardarlo en la carpeta de evidencias `tester/reports/`:

```bash
backend-api/.venv/bin/pytest tester/api_automation --cov=app --cov-report=html:tester/reports/htmlcov
```
*(Luego podés abrir `tester/reports/htmlcov/index.html` directamente en tu navegador para ver la cobertura línea por línea).*
