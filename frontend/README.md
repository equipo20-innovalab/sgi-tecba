# Sistema de Gestión Inteligente (SGI) | TECBA — Frontend

¡Bienvenidos al repositorio oficial del Sistema de Gestión Inteligente (SGI) de TECBA! 🚀

Esta plataforma está diseñada para optimizar y gestionar la visualización geoespacial y la consulta inteligente de datos territoriales, catastrales y comerciales de la Ciudad Autónoma de Buenos Aires (CABA) mediante una interfaz moderna, modular y eficiente.

---

## 📋 Tabla de contenidos

- [Stack tecnológico](#-stack-tecnológico)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Guía paso a paso para la puesta en marcha](#-guía-paso-a-paso-para-principiantes)
- [Conexión con la API y el Backend](#-conectar-con-la-api-y-los-datos)
- [Arquitectura y Mejoras Recientes (Frontend & USIG)](#-arquitectura-y-mejoras-recientes-frontend--usig)
- [Guía de trabajo en equipo (Git Flow)](#-cómo-trabajar-en-equipo-sin-romper-nada-git-flow-básico)
- [Solución de problemas frecuentes](#-solución-de-problemas-frecuentes)

---

## 🛠️ Stack Tecnológico (¿Qué usamos y por qué?)

Para construir este MVP (Producto Mínimo Viable), hemos seleccionado herramientas modernas y ligeras, ideales para un desarrollo ágil y sin fricciones de costos o licencias:

MapLibre GL + Ciudad 3D (GCBA): MapLibre (fork open source de Mapbox GL) renderiza el satélite oficial de USIG, edificios 3D de contexto de CARTO y las capas vectoriales públicas del visor Ciudad 3D: parcelas catastrales, Código Urbanístico y volumen edificable por SMP (las capas temáticas de alturas, mixtura, incidencia/alícuota y barrios permanecen ocultas; el mapa se muestra "Sin capa"). La ficha urbanística de la parcela se consulta en vivo a la API de EPOK y a USIG, y se combina con las habilitaciones/rubros del backend propio. Se eligió MapLibre por encima de Google Maps para evitar restricciones de tarjetas de crédito, costos por visitas y licencias comerciales.

Fuentes oficiales integradas:

- Teselas vectoriales: `https://vectortiles.usig.buenosaires.gob.ar/cur3d/{parcela|codigo_urbanistico|volumen_edif}/{z}/{x}/{y}.pbf?optimize=true`
- Satélite USIG 2021 (esquema TMS): `https://servicios.usig.buenosaires.gob.ar/mapcache/tms/1.0.0/fotografias_aereas_2021_caba_3857@GoogleMapsCompatible/{z}/{x}/{y}.png`
- Ficha de parcela: `https://epok.buenosaires.gob.ar/catastro/parcela/?smp=...` y endpoints `/cur3d/*` del mismo host (superficie edificada, unidades funcionales, pisos sobre/bajo rasantes, superficie de parcela y planos)
- Barrio y Comuna: `https://ws.usig.buenosaires.gob.ar/datos_utiles?x=<lng>&y=<lat>` (usa el centroide devuelto por EPOK)
- Visor oficial (enlace profundo): `https://ciudad3d.buenosaires.gob.ar/?smp=...`
- Créditos: Gobierno de la Ciudad de Buenos Aires · USIG · EPOK · OpenStreetMap/CARTO · Esri (base alternativa)

---

## 📂 Estructura del Proyecto

El proyecto está organizado de forma modular dentro de la carpeta `frontend/` para facilitar el trabajo en equipo:

sgi-tecba/
│
└── frontend/
├── public/             # Archivos estáticos públicos
├── src/
│   ├── assets/         # Imágenes, iconos y recursos gráficos
│   ├── components/     # Componentes reutilizables (MapView.jsx, ResultPanel.jsx, SearchBox.jsx, etc.)
│   ├── services/       # Conexiones con la API de FastAPI
│   ├── App.jsx         # Componente principal de la interfaz y enrutamiento de vistas
│   ├── main.jsx        # Punto de entrada de React
│   └── index.css       # Estilos globales y configuración de Tailwind
├── tailwind.config.js  # Configuración del motor de estilos y tokens GCBA
└── package.json        # Dependencias y scripts del proyecto


---

## 🧭 Guía Paso a Paso para Principiantes

Si eres nuevo clonando repositorios o corriendo proyectos en tu computadora, sigue estos pasos detallados al pie de la letra:

### Paso 1: Instalar las herramientas necesarias
Antes de tocar el código, asegúrate de tener instalado en tu computadora:
1. **Node.js** (Versión LTS recomendada desde [nodejs.org](https://nodejs.org/)). Esto incluye automáticamente a `npm`, nuestro gestor de paquetes.
2. **Git** (Descárgalo desde [git-scm.com](https://git-scm.com/)).
3. **Visual Studio Code (VS Code)** como editor de código recomendado.

### Paso 2: Clonar el Repositorio en tu Computadora
Abre tu terminal (en Windows puedes usar **Git Bash** o la terminal integrada de VS Code). Ubícate en la carpeta donde quieras descargar el proyecto (por ejemplo, tu Escritorio):

```bash
cd ~/Desktop

Clona el repositorio oficial ejecutando el siguiente comando:

git clone [https://github.com/equipo20-innovalab/sgi-tecba.git](https://github.com/equipo20-innovalab/sgi-tecba.git)

Entra a la carpeta del frontend que acabas de descargar:

cd sgi-tecba/frontend

Paso 3: Instalar las dependencias del proyecto
Como el repositorio no incluye la carpeta pesada de librerías (node_modules), debes descargarla ejecutando:

Bash
npm install
(Espera unos segundos a que la terminal termine de descargar todos los paquetes necesarios).

Paso 4: Levantar el servidor local de desarrollo
Una vez instaladas las dependencias, arranca el servidor local con el siguiente comando:

Bash
npm run dev

La terminal te mostrará un enlace local (generalmente http://localhost:5173/). Presiona la tecla Ctrl y haz clic en ese enlace (o cópialo y pégalo en tu navegador web) para ver la aplicación corriendo en vivo. ¡Felicidades, ya tienes el entorno de desarrollo activo!

🔌 Conectar con la API y los datosEl buscador principal envía el texto ingresado a POST /api/v1/consulta en el backend FastAPI. En desarrollo, Vite reenvía automáticamente las solicitudes /api hacia http://127.0.0.1:8000 mediante el proxy configurado.Antes de iniciar el frontend, configura y arranca el backend-api siguiendo su propia guía de puesta en marcha (../backend-api/README.md), incluyendo el contenedor PostgreSQL/PostGIS y las semillas de datos. Si la API no está disponible, la interfaz reportará el error de conexión sin simular resultados ficticios.   

🚀 Arquitectura y Mejoras Recientes 
(Frontend & USIG)Durante las últimas iteraciones de desarrollo, se implementaron optimizaciones clave en la interfaz de usuario y la visualización de datos:

1. Eliminación del Panel de Cobertura de Auditoría (ResultPanel.jsx)Se removió visualmente el bloque amarillo "Cobertura del padrón" de la interfaz principal de resultados, ya que correspondía a métricas de auditoría interna de la base de datos que resultaban confusas para el ciudadano común. El contrato JSON del backend se mantuvo intacto para no romper tests unitarios ni la navegación de soporte.

El buscador tiene dos campos en línea: **rubro** (lista obtenida de
`GET /api/v1/rubros`) y **lugar** (texto libre), y envía ambos a
`POST /api/v1/consulta` en modo
estructurado (`{ "rubro": "...", "direccion": "..." }`). En desarrollo, Vite
reenvía las solicitudes `/api` a `http://127.0.0.1:8000`.
La API relaciona las direcciones exactas del padrón de habilitaciones con su
SMP, ficha EPOK, historial completo de habilitaciones y atributos del Código
Urbanístico (cuando se cargue el CSV). El mapa usa el `smp` devuelto para
resaltar la parcela oficial y consultar en vivo su ficha urbanística en EPOK;
además llama a `GET /api/v1/mapa/parcelas` para mostrar habilitaciones y rubros
locales en el mismo popup. El mapa se muestra por defecto **Sin capa**: las
capas temáticas siguen definidas en el estilo pero no se dibujan.

El botón **Voz** llena esos dos campos con `Web Speech API` (`es-AR`). Un parser
local (`src/services/voz.js`) separa rubro y lugar usando el catálogo de
`/rubros` y sinónimos en español; el dictado nunca dispara la consulta solo:
siempre podés revisar y corregir antes de apretar **Buscar**. Si el navegador no
reconoce voz (o falla el permiso/servicio), se graba con `MediaRecorder` y se
envía a `POST /api/v1/voz/transcribir`, donde `faster-whisper` transcribe en
local con el modelo `base`. Se necesita `localhost` o HTTPS y permiso de
micrófono; Chrome/Edge tienen el mejor soporte.

Antes de iniciar el frontend, configura y arranca `backend-api` siguiendo su
[guía de puesta en marcha](../backend-api/README.md), incluida la base
PostgreSQL/PostGIS y la carga de datos del pipeline de Data Analytics. Si la API
no está disponible o la base no tiene datos, la interfaz muestra el error y no
reemplaza la respuesta por resultados simulados.

3. Validación de Coordenadas y Prevención del "Bug del Agua" (MapView.jsx)Se solucionó un error crítico donde, al recibir coordenadas nulas o vacías, la conversión en JavaScript evaluaba a 0, desplazando la cámara del mapa hacia las coordenadas [0, 0] (Null Island / Río de la Plata).Se incorporó una validación estricta de Bounding Box en el visor geográfico para garantizar que el mapa se posicione y renderice únicamente dentro de los límites terrestres de CABA.

🌿 ¿Cómo trabajar en equipo sin romper nada? (Git Flow Básico)Para evitar sobrescribir el trabajo de tus compañeros, sigue esta rutina cada vez que vayas a programar:

Para evitar sobrescribir el trabajo de tus compañeros, sigue esta rutina cada vez que vayas a programar:

1. Actualiza tu rama principal antes de empezar:

Bash
git checkout main
git pull origin main

2. Crea tu propia rama de trabajo (reemplaza con algo descriptivo):

Bash
git checkout -b feature/mi-nueva-funcionalidad

3.Haz tus cambios, pruébalos y guárdalos:

Bash
git status
git add .
git commit -m "feat(frontend): breve descripción de lo que hiciste"

4. Sube tus cambios a GitHub:

Bash
git push origin feature/mi-nueva-funcionalidad

5. Por último, ve a GitHub y abre un Pull Request (PR) hacia la rama main para que el equipo revise tu código antes de integrarlo.

🔧 Solución de Problemas Frecuentes

Error de dependencias o módulos faltantes (MapLibre o Tailwind)

Si al ejecutar npm run dev por primera vez aparece un error en la terminal diciendo que falta MapLibre o que no se encuentra Tailwind, significa que algunas dependencias requieren una sincronización manual. Asegúrate de utilizar Tailwind CSS v3.x para mantener la compatibilidad con los tokens institucionales del GCBA (gcba-primary, gcba-secondary, etc.).

Para solucionarlo, frena tu servidor (Ctrl + C) y ejecuta estos comandos dentro de la carpeta frontend:

1. Instalar la librería del mapa interactivo:

Bash
npm install maplibre-gl

2. Instalar el motor de estilos en la versión correcta (3.4.19):

Bash
npm install -D tailwindcss@3.4.19 postcss autoprefixer

Una vez finalizadas las descargas, vuelve a levantar el proyecto con npm run dev y la interfaz cargará sin problemas.

👥 Equipo
Frontend / UI-UX: Equipo Técnico SGI TECBA

📄 Licencia
Uso interno y académico del proyecto TECBA.