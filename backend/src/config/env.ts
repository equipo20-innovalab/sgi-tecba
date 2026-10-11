const rawPort = process.env.PORT ?? "3000";
const port = Number(rawPort);

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error(`PORT debe ser un entero entre 1 y 65535; se recibió "${rawPort}".`);
}

export const config = {
  port,
};
