# 🧬 Purged CV aplicado al PEAD — Resultado (2026-08-22)

## Qué se hizo
Re-validar el IC de la sorpresa de earnings (PEAD) usando **Purged Cross-Validation**, para comprobar si el alpha (0.19-0.22 original) era real o estaba inflado por el solapamiento de etiquetas (retornos a 20-60 días).

**Script:** `pead_purgedcv.py` · **Datos:** 887-1,133 eventos de todo el universo (append-only) · **Método:** 5 pliegues temporales, IC solo en el pliegue test (out-of-sample).

## Resultados

### Retorno post-anuncio a 20 días
| Métrica | Global (sin purge) | **Purged CV** |
|---|---|---|
| IC Pearson | +0.104 | **+0.094** |
| IC Spearman | +0.084 | **+0.085** |

### Retorno post-anuncio a 60 días
| Métrica | Global (sin purge) | **Purged CV** |
|---|---|---|
| IC Pearson | +0.125 | **+0.121** |
| IC Spearman | +0.164 | **+0.130** |

## Veredicto

**✅ El alpha del PEAD se MANTIENE con purged CV.**

- A 20d: IC Spearman purgado +0.085 (≈ global +0.084)
- A 60d: IC Spearman purgado +0.130 (baja de +0.164 pero claramente positivo)
- **El solapamiento de etiquetas NO inflaba el resultado** — el alpha es genuino.

## Matices honestos

1. Los IC actuales (0.09-0.13) son **más bajos que las primeras mediciones** (0.19-0.22) porque ahora se usa **todo el universo** (887 eventos) y no solo 39 tickers — estimación más realista.
2. **0.09-0.13 sigue siendo alpha sólido** (umbral de Quinn: 0.02), confirmado con método riguroso.
3. **Variabilidad entre pliegues** (algunos negativos, otros muy positivos) — esperable en ventanas cortas (~177 eventos); el promedio es claramente positivo.

## Conclusión accionable

El **PEAD (earnings momentum) es un alpha real**, no un artefacto de data leakage. Esto **refuerza** su valor como filtro/refuerzo del momentum (estrategia 2), aunque el backtest de fusión no lo superara — el alpha de la señal en sí está validado.

---

*Documento de referencia del proyecto Qlib Work. Complementa `guia_purged_cv.md`.*
