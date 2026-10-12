# Backend

Backend inicial del MVP, implementado con TypeScript, Node.js y Express.

## Requisitos

- Node.js 22.9 o superior.
- npm.

## Desarrollo

Desde esta carpeta:

```bash
npm install
npm run dev
```

El servidor queda disponible en `http://localhost:3000`. `GET /health` devuelve
`{ "status": "ok" }` y sirve para comprobar que el proceso está activo; todavía
no hay endpoints de negocio ni integración con fuentes de datos.

Para compilar y ejecutar la versión compilada:

```bash
npm run build
npm start
```

La variable `PORT` permite cambiar el puerto. Para desarrollo local, se puede
copiar `.env.example` a `.env`; el servidor carga ese archivo si existe. No
guardar credenciales ni archivos `.env` en el repositorio.

## Estructura actual

- `src/server.ts`: configuración y arranque del servidor HTTP.
- `src/app.ts`: configuración de Express y ruta de salud.
- `src/config/env.ts`: lectura y validación de configuración.

La integración con Data, los contratos funcionales y las rutas de consulta se
incorporarán en incrementos posteriores, una vez confirmados los formatos y
requisitos del caso piloto.
