# Índice de oportunidad comercial — fórmula, artefacto y changelog

**Versión vigente:** `1.0.0` · **Fecha:** 2026-10-28

El índice responde *dónde y qué conviene abrir* en la CABA. Es una herramienta de
**orientación**, no una predicción ni una evaluación normativa. Este documento es
la fuente narrativa de la fórmula; la versión legible por máquina vive en
`src/oportunidad.py` (`VERSION_FORMULA` y `VERSIONES_FORMULA`).

---

## 1. Fórmula

Para cada combinación `(comuna, rubro)` con al menos `min_licencias` registros:

```
score = 100 × ( p_c · C + p_s · (1 − S) + p_r · R )
```

| Símbolo | Componente | Definición | Peso por defecto |
|---|---|---|---|
| `C` | `crecimiento` | Crecimiento **anualizado de la cuota** del rubro dentro de su comuna, entre el primer y el último año disponibles. La cuota cancela el sesgo de cobertura de cada archivo. | 0,40 |
| `1 − S` | `baja_saturacion` | `S = n_licencias(rubro, comuna) / media(n_licencias de la comuna)`. `S > 1` indica sobrerrepresentación. | 0,40 |
| `R` | `subrepresentacion` | `(cuota_esperada − cuota_observada) / cuota_esperada`, con `cuota_esperada = licencias de la comuna / total` y `cuota_observada = licencias del rubro en la comuna / total del rubro`. | 0,20 |

### Normalización

Cada señal se escala con **min-max** a `[0, 1]` sobre todas las combinaciones:

- `NaN` → `0.5` (decisión neutra: no penaliza ni premia datos incompletos).
- Serie constante → `0.5` (evita división por cero).
- Los pesos se **normalizan para sumar 1**, así que se puede pasar cualquier
  combinación y el resto se ajusta.

### Invariantes

- `0 ≤ score ≤ 100`.
- La suma de los aportes (`componente × peso`) coincide con el score salvo
  redondeo (±0,2).
- El score es determinista para los mismos datos, pesos y `calculado_en`.

---

## 2. Artefacto reproducible

El cálculo no queda solo en el notebook: se materializa en dos archivos y en
tablas consultables.

### Archivos

| Archivo | Contenido |
|---|---|
| `data/processed/indice_oportunidad.csv` | Una fila por `(comuna, rubro)` con score, componentes, pesos, aportes, métricas crudas, `formula_version`, `calculado_en` y `explicacion`. |
| `data/processed/indice_oportunidad_meta.json` | Versión, fecha, pesos efectivos, parámetros, cantidad de filas/comunas/rubros y **SHA-256 del CSV de origen**. |

### PostgreSQL

| Objeto | Rol |
|---|---|
| `indice_oportunidad_meta` | Una fila por corrida (`calculo_id`): versión, fecha, pesos, parámetros, huella del origen. |
| `indice_oportunidad` | Filas del score con componentes, aportes y métricas. Append-only: conserva el historial por `calculo_id`. |
| `indice_oportunidad_actual` | Vista con la **última** corrida (mayor `calculo_id`). Es la que conviene consultar. |

### Comandos

```bash
# Calcula, escribe CSV + JSON y carga en Postgres (reproducible)
python src/export_postgres.py --oportunidad --min-licencias 5 --top-rubros 80

# Solo valida y muestra cuántas filas saldrían (no escribe nada)
python src/export_postgres.py --oportunidad --dry-run
```

La huella SHA-256 permite verificar que el artefacto se generó con el mismo
padrón. Si cambia el CSV de origen, cambia la huella y queda registrado en
`indice_oportunidad_meta`.

### Consulta

```sql
-- Top oportunidades de la última corrida
SELECT comuna, rubro, oportunidad, n_licencias, explicacion
FROM indice_oportunidad_actual
ORDER BY oportunidad DESC
LIMIT 10;

-- Historial de corridas
SELECT calculo_id, formula_version, calculado_en, n_filas, fuente_sha256
FROM indice_oportunidad_meta
ORDER BY calculo_id DESC;
```

### Explicación de un score

Cada fila guarda `explicacion`, por ejemplo:

```
Oportunidad 96.9 = crecimiento 100.0×0.40 (40.0) + baja_saturacion 90.0×0.40 (36.0) + subrepresentacion 100.0×0.20 (20.0) · n_licencias=42 · fórmula 1.0.0
```

En Python:

```python
from src.oportunidad import explicar_oportunidad

detalle = explicar_oportunidad(fila)   # dict con aportes, componentes y resumen
```

---

## 3. Backtest mínimo

`backtest_oportunidad` entrena el índice **solo con datos hasta `anio_corte`** y
lo contrasta con el crecimiento realizado entre `anio_corte` y
`anio_evaluacion`. No hay fuga de información: el año de evaluación nunca entra
en el cálculo del score.

Métricas:

- **Spearman**: correlación de rangos entre el score y el crecimiento realizado
  de la cuota. Cercano a 0 ⇒ el índice no anticipa el crecimiento relativo.
- **top-k hit rate**: proporción del top-k predicho que también está en el top-k
  realizado.

Se eligen por defecto los dos últimos años con al menos `min_registros_anio`
(default 100) registros, para evitar años con cobertura ínfima (2026 tiene 2
filas).

<!-- RESULTADO_BACKTEST -->
**Resultado de la corrida 2026-10-28** (fórmula `1.0.0`, `min_licencias=5`, top 80 rubros):

| Métrica | Valor |
|---|---|
| Año de corte | 2019 |
| Año de evaluación | 2025 |
| Filas de entrenamiento | 156.216 |
| Combinaciones comparables | 786 |
| Spearman | **−0,178** |
| top-10 hit rate | **0,00** |

El índice **no anticipa** el crecimiento relativo del período en esta ventana: la
correlación es levemente negativa y ninguna de las 10 mejores oportunidades
predichas quedó en el top-10 realizado. Se reporta explícitamente para evitar
sobreinterpretar el score. La causa principal es la cobertura despareja del
padrón: 2020, 2021, 2023 y 2024 no traen `descripcion_rubro` (solo
`codigo_rubro`), así que el índice solo puede usar 2015, 2019, 2025 y 2026.

**Limitaciones:** es un backtest descriptivo de una sola ventana, no una
validación causal ni un pronóstico. La cobertura del padrón varía fuerte entre
años y el campo `anio` identifica el archivo de origen; por eso se usa cuota
(share) y no conteo crudo.

---

## 4. Changelog de la fórmula

| Versión | Fecha | Cambios |
|---|---|---|
| `1.0.0` | 2026-10-28 | Primera versión versionada y persistida. Pesos 40/40/20. Crecimiento por cuota. Artefacto CSV + metadatos, tablas `indice_oportunidad` / `indice_oportunidad_meta`, vista `indice_oportunidad_actual`, explicación por fila y backtest mínimo. |

### Cómo versionar un cambio

1. Modificar la fórmula o los pesos en `src/oportunidad.py`.
2. Incrementar `VERSION_FORMULA` y agregar una entrada a `VERSIONES_FORMULA`.
3. Agregar la fila correspondiente a esta tabla.
4. Volver a correr `python src/export_postgres.py --oportunidad`.
   Las corridas anteriores se conservan por `calculo_id`.
