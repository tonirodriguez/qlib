# 🧬 Purged CV aplicado al Momentum 120d — Resultado (2026-08-22)

## Qué se hizo
Re-validar el IC del momentum 120d sobre sp500_liquid con **Purged Cross-Validation** (igual que hicimos con el PEAD), dividiendo por tiempo en pliegues y midiendo el IC out-of-sample en cada uno.

**Script:** `momentum_purgedcv.py` · **Universo:** sp500_liquid (292 tickers) · **Señal:** momentum 120d · **Label:** retorno futuro 60d y 120d · **5 pliegues temporales**

## Resultados

### Retorno a 60 días
| Métrica | Global | Purged CV |
|---|---|---|
| IC Pearson | −0.006 | **−0.038** |
| IC Spearman | −0.036 | **−0.062** |

### Retorno a 120 días
| Métrica | Global | Purged CV |
|---|---|---|
| IC Pearson | +0.025 | **+0.001** |
| IC Spearman | −0.009 | **−0.036** |

### Desglose por pliegue (retorno 120d) — el dato clave
| Pliegue | Periodo | IC Spearman |
|---|---|---|
| 1 | 2018-2020 | −0.030 |
| 2 | 2020-2021 | **−0.132** |
| 3 | 2021-2023 | **−0.100** |
| 4 | 2023-2024 | +0.065 |
| 5 | 2024-2026 | +0.019 |

## Veredicto honesto

**El momentum 120d NO tiene un IC robusto y estable en el tiempo.** Con purged CV el IC medio es **ligeramente negativo**, muy por debajo del +0.066 que recordábamos de la validación inicial.

**El hallazgo más revelador es la inestabilidad por régimen:**
- **Negativo en 2020-2023** (crash COVID + corrección 2022): IC −0.10 a −0.13
- **Positivo en 2023-2026** (mercado alcista): IC +0.02 a +0.065

→ El alpha del momentum es **Dependiente del Régimen**: rentable en mercados alcistas, con reversión en periodos de crisis.

## Coherencia con la literatura

Coincide con los **Momentum Crashes** (Daniel & Moskowitz): el momentum es rentable a largo plazo pero tiene **caídas bruscas en correcciones** — exactamente por eso la estrategia usa **vol-targeting**.

## Implicaciones prácticas

1. **No es un alpha constante** — alterna periodos fuertes con reversiones. Su ventaja de largo plazo (Sharpe 1.0) viene de compensar regímenes, no de ganar siempre.
2. **El paper-trading en −2.45% encaja:** entramos en agosto 2026 y el momentum está en un tramo flojo (pliegue reciente solo +0.02).
3. **El vol-targeting es crucial** — para sobrevivir los pliegues negativos (2020, 2022) que este purged CV hace visibles.
4. **El purged CV es más honesto** que el walk-forward simple: muestra la variabilidad entre periodos que el promedio global escondía.

---

*Documento de referencia del proyecto Qlib Work. Complementa `guia_purged_cv.md` y contrasta con `pead_purgedcv_resultado.md`.*
