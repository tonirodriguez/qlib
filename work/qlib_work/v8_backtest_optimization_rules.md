# Reglas de Optimización del Backtest — SFM v8

**Periodo evaluado:** 2025-01-01 → 2026-08-30 (out-of-sample del split 60/20/20)
**Costes:** Binance one-way 0,15% (fee 0,1% taker + half-spread 0,02% + slippage 0,03%)
**Yield cash USDT:** +4,5% APY sobre capital no invertido
**Capital inicial:** €10.000 (= $10.389 @ EUR/USD 1,0389)
**Fuente:** `work/crypto/sensibilidad_v8.py` → `output/sfm_v8/diagnostico_sensibilidad.json`

> ⚠️ **Advertencia honesta:** estos resultados se obtuvieron sobre el mismo periodo
> out-of-sample ya evaluado. Existe **riesgo de sobreajuste**. Antes de adoptar
> cualquier configuración, validar en un **mini-holdout** (periodo futuro no visto).

---

## Definición de parámetros de sensibilidad

| Parámetro | Significado |
|---|---|
| **buy_threshold** | Score mínimo del modelo para **COMPRAR** (entrada). Señales más fuertes. |
| **sell_threshold** | Score por debajo del cual se **VENDÉ**. Si `< buy_threshold` → **histéresis**: aguanta la posición entre entrada y salida. |
| **min_holding_days** | Días mínimos que una posición debe mantenerse antes de poder venderse. |
| **max_positions** | Máximo de posiciones simultáneas (diversificación). |

**Base de referencia (estrategia actual del paper):** buy=0.025, sell=0.015, hold=0, pos=2 → **+4,30% USD / -6,94% EUR, Sharpe 0,247**.

---

## Configuraciones ordenadas por retorno (USD) descendente

### 🥇 1. Histeresis + Umbral alto + Holding — **MEJOR** (+28,64% USD)
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| **+28,64%** | **+14,78%** | **0,595** | -32,3% | 443 |

```
buy_threshold     = 0.040   (comprar solo señales muy fuertes)
sell_threshold    = 0.000   (vender solo cuando el score se vuelve negativo)
min_holding_days  = 3
max_positions     = 3
```
Único resultado **positivo en EUR** y con el mejor Sharpe y menor drawdown. Combina las 3 palancas.

---

### 🥈 2. Umbral alto (0.04) — +24,41% USD
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +24,41% | +11,01% | 0,551 | -36,7% | 424 |

```
buy_threshold    = 0.040
sell_threshold   = 0.015
min_holding_days = 0
max_positions    = 2
```
Subir el umbral de entrada a 0.04 es la **palanca individual más potente**.

---

### 🥉 3. Más diversificación (3 posiciones) — +23,75% USD
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +23,75% | +10,42% | 0,537 | -34,8% | 741 |

```
buy_threshold    = 0.025
sell_threshold   = 0.015
min_holding_days = 0
max_positions    = 3
```
Subir a 3 posiciones reparte riesgo y mejora mucho. Ojo: 741 trades (más costes).

---

### 4. Max posiciones 4 — +15,65% USD
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +15,65% | +3,20% | 0,422 | -39,5% | 949 |

```
buy=0.025  sell=0.015  hold=0  pos=4
```
Mejor que 2, peor que 3 (sobrediversificación + más costes).

---

### 5. Holding 5d + histéresis — +14,04% USD
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +14,04% | +1,75% | 0,398 | -41,5% | 380 |

```
buy_threshold    = 0.035
sell_threshold   = 0.005
min_holding_days = 5
max_positions    = 3
```

---

### 6. Histéresis salida en 0.00 — +10,80% USD
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +10,80% | -1,13% | 0,352 | -35,8% | 412 |

```
buy=0.025  sell=0.000  hold=0  pos=2
```

---

### 7. Umbral alto (0.06) — +7,26% USD
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +7,26% | -4,29% | 0,294 | -36,7% | 357 |

```
buy_threshold    = 0.060
sell_threshold   = 0.015
min_holding_days = 0
max_positions    = 2
```
Umbral demasiado alto — pocas señales, pierde oportunidades.

---

### 8. **BASE (actual)** — +4,30% USD ← referencia
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +4,30% | -6,94% | 0,247 | -34,0% | 500 |

```
buy=0.025  sell=0.015  hold=0  pos=2   (estrategia actual del paper)
```

---

### 9. Histéresis débil (sell=0.01) — +3,90% USD
| Ret USD | Ret EUR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|
| +3,90% | -7,29% | 0,241 | -34,0% | 474 |

```
buy=0.025  sell=0.010  hold=0  pos=2
```

---

### ⬇️ Configuraciones NEGATIVAS (evitar)

| # | Config | Ret USD | Ret EUR | Sharpe | Trades |
|---|---|---|---|---|---|
| 10 | Holding min 3d | -5,06% | -15,29% | 0,100 | 366 |
| 11 | Histéresis sell=-0.01 | -6,21% | -16,31% | 0,080 | 330 |
| 12 | Holding min 5d | -10,76% | -20,37% | 0,016 | 282 |
| 13 | Holding min 7d | -13,58% | -22,88% | -0,016 | 234 |

> Todas usan `buy=0.025 sell=0.015` con un **holding mínimo > 0**: fuerzan aguantar
> posiciones que el modelo quiere vender → empeoran. El holding mínimo **solo ayuda
> combinado con umbral alto e histéresis** (config 1), no en solitario.

---

## 🎯 Conclusiones clave

1. **Subir el umbral de entrada (0.025 → 0.040)** es la palanca más efectiva: filtra
   señales ruidosas y concentra el capital en los movimientos con mayor convicción.
2. **Histéresis de salida** (vender solo con score más bajo) reduce rotación innecesaria
   y aguanta los ganadores.
3. **3 posiciones** es el óptimo de diversificación (2 demasiado concentrado, 4 demasiado
   costoso).
4. **Holding mínimo en solitario es perjudicial** (fuerza mantener perdedoras).
5. La **configuración ganadora** (0.04 / sell 0.00 / hold 3 / pos 3) **NO está validada
   fuera de este periodo** → es el **candidato a un mini-holdout** antes de adoptarla.

## 📋 Siguiente paso recomendado
Fijar la **config 1** como hipótesis y validarla en un **mini-holdout** sobre un periodo
futuro no usado (o el siguiente tramo de 2026) para descartar sobreajuste, antes de
cualquier cambio en producción.

---

## 🔬 Resultado del Mini-Holdout (validación)

**Script:** `work/crypto/mini_holdout_v8.py` → `output/sfm_v8/mini_holdout_result.json`

### Diseño (honesto, time-split)
- **Selección 2025** (2025-01-01 → 2025-12-31): se re-ejecuta la sensibilidad y se elige la mejor config.
- **Validación 2026** (2026-01-01 → 2026-08-30): holdout real, **nunca usado** para elegir.

### Fase 1 — Mejor config en 2025
| Config | Ret USD | Sharpe |
|---|---|---|
| **Histeresis+Umbral+Hold** (0.04/sell 0.00/hold3/pos3) | **+18,01%** | **0,603** |
| Max posiciones 3 | +8,65% | 0,407 |
| Umbral 0.04 | +7,65% | 0,385 |
| BASE (actual) | -4,84% | 0,078 |

→ La config "optimizada" (Histeresis+Umbral+Hold) domina en 2025. Elegida como desafiante.

### Fase 2 — Validación en 2026 (holdout real)
| Config | Ret USD | Sharpe | Trades |
|---|---|---|---|
| **BASE (actual)**: 0.025/0.015, 2 pos | **+9,60%** | **0,683** | 176 |
| **Mejor 2025**: 0.04/sell 0.00/hold3/pos3 | +9,01% | 0,619 | 135 |

### 🎯 Veredicto: **NO VALIDADO** — la config optimizada NO generaliza
En el holdout 2026, la config optimizada (que ganaba en 2025) **no supera a la BASE**:
- Retorno: +9,0% vs +9,6% (levemente peor)
- Sharpe: 0,619 vs 0,683 (peor)

**Conclusiones de la validación:**
1. El impresionante **+28,6% de la sensibilidad** (sobre todo el periodo) era en gran
   parte **sobreajuste a 2025**, donde la config optimizada destacaba.
2. En **datos realmente no vistos (2026)**, la **BASE actual** (0.025/0.015, 2 posiciones)
   es la **más robusta** — rinde mejor que la config "optimizada".
3. **Recomendación final:** **NO cambiar la configuración de producción.** La config
   actual del paper (comprar score>0.025, vender score<0.015, 2 posiciones) es la más
   robusta entre las probadas, y adoptar la "optimizada" sería sobreajustarse a 2025.

> 🟢 **Nota honesta:** esto no convierte a la BASE en una "estrategia ganadora absoluta".
> En el backtest completo 2025→ago-2026 dio +4,3% USD / -6,9% EUR; en 2026 aislado
> +9,6% USD. Simplemente es la **más estable** de las opciones evaluadas, y la validación
> evitó adoptar una mejora que era sobreajuste.