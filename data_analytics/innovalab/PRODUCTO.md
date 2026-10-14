# Qué responde la plataforma — Alcance por fases

> Documento de producto para alinear a Data, Backend, Frontend y PM.
> Define **qué preguntas** responde la plataforma en cada fase y **con qué fuente**.

---

## PARTE 1 — MVP (dataset histórico + APIs integradas)

Fuentes activas: **habilitaciones (dataset histórico + ML)**, **EPOK Catastro**,
**BA Data (CKAN)**. *USIG queda como mejora (ver nota al pie).*

| # | Pregunta del usuario | Fuente | Estado |
|---|----------------------|--------|--------|
| 1 | **¿Dónde conviene abrir mi rubro?** | Índice de oportunidad (ML) | ✅ listo |
| 2 | **¿Cómo es este inmueble? ¿Cuántos m² tiene?** | EPOK Catastro (`superficie_total`, `superficie_cubierta`) | ✅ API verificada |
| 3 | **¿Dónde queda exactamente? ¿Comuna/barrio?** | EPOK (`centroide`) + capas de comuna · USIG (cuando funcione) | ⚠️ parcial |
| 4 | **¿Cuántos competidores de mi rubro hay en la comuna?** | Habilitaciones (`descripcion_rubro` + `comuna`) | ✅ listo |
| 5 | **¿Qué tipo de trámite se hizo para este rubro?** | Habilitaciones (`tipo_tramite`) | ✅ listo |
| 6 | **¿Cuánto tardó / cómo vino evolucionando?** | Habilitaciones (`fecha_habilitacion`, 71%) ⚠️ no usar `anio` como serie temporal | ⚠️ parcial |
| 7 | **¿De dónde sale / cuándo se actualizó el dato?** | BA Data (CKAN: dataset `habilitaciones-aprobadas`, licencia, fecha) | ✅ API verificada |

### Ficha de viabilidad que el MVP ya puede mostrar

```
📍 CORRIENTES 2330 — Comuna 4 (Palermo)
├── Inmueble (EPOK):   120 m² totales · 80 m² cubiertos · destino: …
├── Coordenadas:        -58.378, -34.607  (mapa)
├── Mercado (ML):       Oportunidad "pizzería": 94/100 ★
├── Competencia:        12 pizzerías en comuna 4 (baja saturación)
└── Trámite histórico:  tipo "Habilitación" · X días promedio
```

### Nota sobre USIG
El normalizador de direcciones (`servicios.usig.../normalizar`) está **caído o muy
lento hoy** (timeout >45s). No se usa en vivo en el MVP: la geocodificación sigue
con la lógica actual (callejero + catastro, 91,8%). USIG queda como **mejora
opcional** con timeout corto + fallback, no como dependencia.

---

## PARTE 2 — Fases siguientes (no MVP)

Se suman **dos fuentes nuevas** y desbloquean las preguntas que el MVP no cubre.

### Fase 2 — Código Urbanístico (zonificación por parcela)

| # | Pregunta del usuario | Fuente | Requiere |
|---|----------------------|--------|----------|
| 8 | **¿Puedo abrir ESTE uso en esta parcela?** | Código Urbanístico (uso permitido por SMP) | dataset `Codigo Urbanístico – Parcelas` (BA Data) + cruce por SMP |
| 9 | **¿Qué FOT/densidad permite la zona?** | Código Urbanístico (`fot`, distritos especiales) | idem |

> Ojo: EPOK da el **destino actual** del inmueble; el Código Urbanístico da el
> **uso permitido**. Son cosas distintas y la pregunta "¿puedo acá?" se responde
> con este último.

### Fase 3 — RAG de normativa (Código de Habilitaciones)

| # | Pregunta del usuario | Fuente | Requiere |
|---|----------------------|--------|----------|
| 10 | **¿Qué documentos necesito?** | RAG sobre el Código de Habilitaciones (PDF) | PDF de la norma + capa RAG (embeddings + retrieval) |
| 11 | **¿Cuánto cuesta / cuánto tarda oficialmente?** | idem (tasas, plazos de la norma) | idem |
| 12 | **¿Qué pasos del trámite hay que seguir?** | idem (etapas) | idem |

> ⚠️ **Esta fase supera al MVP**: necesita cargar la norma en PDF y montar RAG
> (vector store + citas + disclaimer legal). No se resuelve conectando APIs.

---

## Resumen visual del alcance

```
MVP                 →  "¿Dónde conviene?" + "¿Cómo es el inmueble (m²)?" + "¿Cómo está mi rubro?"
Fase 2 (+ Código U.) →  "¿Puedo abrir este uso acá?"   (viabilidad legal)
Fase 3 (+ RAG)       →  "¿Qué documentos necesito?"    (requisitos normativos)
```

**Fuentes verificadas técnicamente:** EPOK (✅ JSON por SMP), BA Data CKAN (✅),
USIG (⚠️ caído hoy).
