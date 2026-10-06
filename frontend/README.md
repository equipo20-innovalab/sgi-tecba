Sistema de Gestión Inteligente (SGI) | TECBA

¡Bienvenidos al repositorio oficial del Sistema de Gestión Inteligente (SGI) de TECBA! 🚀

Esta plataforma está diseñada para optimizar y gestionar la visualización geoespacial y la consulta inteligente de datos territoriales y comerciales mediante una interfaz moderna, modular y eficiente.

🛠️ Stack Tecnológico (¿Qué usamos y por qué?)

Para construir este MVP (Producto Mínimo Viable), hemos seleccionado herramientas modernas y ligeras, ideales para un desarrollo ágil y sin fricciones de costos o licencias:

React (v19): Librería principal de JavaScript para construir interfaces de usuario interactivas basadas en componentes.

Vite (v8.3.3): Nuestro empaquetador y servidor de desarrollo local. Lo preferimos por su velocidad extrema al compilar y actualizar cambios en tiempo real (Hot Module Replacement).

Tailwind CSS: Framework de estilos (utility-first) que nos permite diseñar interfaces limpias y adaptables rápidamente sin escribir CSS complejo desde cero.

Leaflet & OpenStreetMap: Librería de mapas interactivos de código abierto. Se eligió por encima de Google Maps para evitar restricciones de tarjetas de crédito, costos por número de visitas y licencias comerciales.

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