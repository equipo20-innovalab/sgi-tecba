import express from "express";

export const app = express();

app.disable("x-powered-by");
app.use(express.json());

app.get("/health", (_request, response) => {
  response.status(200).json({ status: "ok" });
});

app.use((_request, response) => {
  response.status(404).json({ error: "Not Found" });
});
