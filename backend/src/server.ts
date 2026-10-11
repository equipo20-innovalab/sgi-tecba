import { app } from "./app.js";
import { config } from "./config/env.js";

const server = app.listen(config.port, () => {
  console.log(`Backend escuchando en http://localhost:${config.port}`);
});

server.on("error", (error) => {
  console.error("No se pudo iniciar el servidor:", error);
  process.exitCode = 1;
});
