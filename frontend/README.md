Sistema de Gestión Inteligente (SGI) | TECBA

¡Bienvenidos al repositorio oficial del Sistema de Gestión Inteligente (SGI) de TECBA! 🚀

Esta plataforma está diseñada para optimizar y gestionar la visualización geoespacial y la consulta inteligente de datos territoriales y comerciales mediante una interfaz moderna, modular y eficiente.

🛠️ Stack Tecnológico (¿Qué usamos y por qué?)

Para construir este MVP (Producto Mínimo Viable), hemos seleccionado herramientas modernas y ligeras, ideales para un desarrollo ágil y sin fricciones de costos o licencias:

React (v19): Librería principal de JavaScript para construir interfaces de usuario interactivas basadas en componentes.

Vite (v8.3.3): Nuestro empaquetador y servidor de desarrollo local. Lo preferimos por su velocidad extrema al compilar y actualizar cambios en tiempo real (Hot Module Replacement).

Tailwind CSS: Framework de estilos (utility-first) que nos permite diseñar interfaces limpias y adaptables rápidamente sin escribir CSS complejo desde cero.

MapLibre GL + Ciudad 3D (GCBA): MapLibre (fork open source de Mapbox GL) renderiza el satélite oficial de USIG, edificios 3D de contexto de CARTO y las capas vectoriales públicas del visor Ciudad 3D: parcelas catastrales, Código Urbanístico y volumen edificable por SMP (las capas temáticas de alturas, mixtura, incidencia/alícuota y barrios permanecen ocultas; el mapa se muestra "Sin capa"). La ficha urbanística de la parcela se consulta en vivo a la API de EPOK y a USIG, y se combina con las habilitaciones/rubros del backend propio. Se eligió MapLibre por encima de Google Maps para evitar restricciones de tarjetas de crédito, costos por visitas y licencias comerciales.

Fuentes oficiales integradas:

- Teselas vectoriales: `https://vectortiles.usig.buenosaires.gob.ar/cur3d/{parcela|codigo_urbanistico|volumen_edif}/{z}/{x}/{y}.pbf?optimize=true`
- Satélite USIG 2021 (esquema TMS): `https://servicios.usig.buenosaires.gob.ar/mapcache/tms/1.0.0/fotografias_aereas_2021_caba_3857@GoogleMapsCompatible/{z}/{x}/{y}.png`
- Ficha de parcela: `https://epok.buenosaires.gob.ar/catastro/parcela/?smp=...` y endpoints `/cur3d/*` del mismo host (superficie edificada, unidades funcionales, pisos sobre/bajo rasantes, superficie de parcela y planos)
- Barrio y Comuna: `https://ws.usig.buenosaires.gob.ar/datos_utiles?x=<lng>&y=<lat>` (usa el centroide devuelto por EPOK)
- Visor oficial (enlace profundo): `https://ciudad3d.buenosaires.gob.ar/?smp=...`
- Créditos: Gobierno de la Ciudad de Buenos Aires · USIG · EPOK · OpenStreetMap/CARTO · Esri (base alternativa)

📂 Estructura del Proyecto

El proyecto está organizado de forma modular dentro de la carpeta frontend/ para facilitar el trabajo en equipo:

sgi-tecba/
│
└── frontend/
    ├── public/             # Archivos estáticos públicos
    ├── src/
    │   ├── assets/         # Imágenes, iconos y recursos gráficos
    │   ├── components/     # Componentes reutilizables (ej. MapView.jsx)
    │   ├── services/       # Conexiones futuras con la API (Backend FastAPI)
    │   ├── App.jsx         # Componente principal de la interfaz
    │   ├── main.jsx        # Punto de entrada de React
    │   └── index.css       # Estilos globales y configuración de Tailwind
    ├── tailwind.config.js  # Configuración del motor de estilos
    └── package.json        # Dependencias y scripts del proyecto


🧭 Guía Paso a Paso para Principiantes

Si eres nuevo clonando repositorios o corriendo proyectos en tu computadora, sigue estos pasos detallados al pie de la letra:

Paso 1: Instalar las herramientas necesarias

Antes de tocar el código, asegúrate de tener instalado en tu computadora:

Node.js (Descarga la versión LTS recomendada desde nodejs.org). Esto incluye automáticamente a npm, que es nuestro gestor de paquetes.

Git (Descárgalo desde git-scm.com).

Visual Studio Code (VS Code) como editor de código.

Paso 2: Clonar el Repositorio en tu Computadora

Abre tu terminal (en Windows puedes usar Git Bash o la terminal integrada de VS Code).

Ubícate en la carpeta donde quieras descargar el proyecto (por ejemplo, tu Escritorio):

cd ~/Desktop


Clona el repositorio oficial ejecutando el siguiente comando:

git clone https://github.com/equipo20-innovalab/sgi-tecba.git


Entra a la carpeta del proyecto que acabas de descargar:

cd sgi-tecba/frontend


Paso 3: Instalar las dependencias del proyecto

Como el repositorio no incluye la carpeta pesada de librerías (node_modules), debes descargarla ejecutando:

npm install


(Espera unos segundos a que la terminal termine de descargar todos los paquetes necesarios).

Paso 4: Levantar el servidor local de desarrollo

Una vez instaladas las dependencias, arranca el servidor local con el siguiente comando:

npm run dev


La terminal te mostrará un enlace local (generalmente http://localhost:5173/).

Presiona la tecla Ctrl y haz clic en ese enlace (o cópialo y pégalo en tu navegador web de preferencia) para ver la aplicación corriendo en vivo. ¡Felicidades, ya tienes el entorno de desarrollo activo!

### Conectar con la API y los datos

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

🌿 ¿Cómo trabajar en equipo sin romper nada? (Git Flow básico)

Para evitar sobreescribir el trabajo de tus compañeros, sigue esta rutina cada vez que vayas a programar:

Actualiza tu rama principal antes de empezar:

git checkout main
git pull origin main


Crea tu propia rama de trabajo (reemplaza tu-nombre/nombre-de-la-tarea por algo descriptivo):

git checkout -b feature/mi-nueva-funcionalidad


Haz tus cambios, pruébalos y guárdalos:

git status
git add .
git commit -m "feat(frontend): breve descripción de lo que hiciste"


Sube tus cambios a GitHub:

git push origin feature/mi-nueva-funcionalidad


Por último, ve a GitHub y abre un Pull Request (PR) hacia la rama main para que el equipo revise tu código antes de integrarlo.



Solución de Problemas Frecuentes:
Si al ejecutar npm run dev por primera vez te aparece un error en la terminal diciendo que falta MapLibre o Cannot find module 'tailwindcss', significa que algunas dependencias no se descargaron automáticamente con el npm install inicial.

Además, es crucial asegurarnos de utilizar Tailwind CSS en su versión 3.x para mantener la compatibilidad con nuestros archivos de configuración actuales y evitar que se rompan los estilos.

Para solucionarlo, frena tu servidor (Ctrl + C) y ejecuta estos dos comandos dentro de la carpeta frontend:

1. Instalar la librería del mapa interactivo:

Bash
npm install maplibre-gl
2. Instalar el motor de estilos en la versión correcta (3.4.19):

Bash
npm install -D tailwindcss@3.4.19 postcss autoprefixer
Una vez que ambas descargas finalicen, vuelve a levantar el proyecto con npm run dev y la interfaz cargará sin problemas.
