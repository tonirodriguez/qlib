# 🧬 Regimen Test — Resultado (2026-08-22)

**Script:** `regimen_test.py` · **Hipótesis pre-registrada:** el momentum rinde MENOS en estados de estrés (vol/drawdown). **Criterio falsable:** si los CI de estrés y calma se solapan → no se distingue.

## IC del momentum 120d por estado (retorno fut. 60d, CI bootstrap 95%)

| Estado | n | IC Spearman | CI 95% |
|---|---|---|---|
| **CALMA** (vol<0.75) | 417,991 | **+0.024** | [+0.020, +0.027] |
| **ESTRÉS** (vol≥0.75) | 135,579 | **−0.184** | [−0.190, −0.180] |
| **ALZA** (dd120=0) | 409,292 | +0.035 | [+0.032, +0.039] |
| **DRAWDOWN** (dd120=1) | 144,278 | **−0.149** | [−0.154, −0.144] |

## Regresión de interacción (IC_m mensual ~ vol_alta + drawdown + tiempo)

| Coeficiente | Valor | t-stat | Significado |
|---|---|---|---|
| vol_alta | **−0.130** | **−3.06** | ⭐ Régimen (vol) significativo |
| drawdown | −0.016 | −0.33 | No significativo |
| tiempo | +0.070 | +1.32 | No (no es decaimiento) |

## VEREDICTO — CONFIRMADO

**El momentum 120d es DEPENDIENTE DEL RÉGIMEN, confirmado con rigor estadístico:**

1. **CI de estados NO se solapan** → el criterio falsable no se cumple → hipótesis CONSERVADA.
   - Calma IC +0.024 [0.020, 0.027] vs Estrés IC −0.184 [−0.190, −0.180]: separación enorme.

2. **`vol_alta` significativo (t=−3.06) y negativo** → en alta volatilidad el IC del momentum colapsa (de +0.02 a −0.18).

3. **Tiempo NO significativo (t=+1.32)** → **NO es decaimiento secular, es régimen.** Separa las dos hipótesis competidoras (como pedía Quinn).

## Implicaciones prácticas

- El momentum **funciona** (IC +0.02) en mercados calmos, y **se invierte** (IC −0.18) en estrés/alta vol.
- **Valida DOBLEMENTE el vol-gating** del plan (semana 5-6): reducir/pausar momentum cuando la vol es alta captura exactamente el régimen donde el momentum falla.
- Consistente con **Momentum Crashes** (Daniel-Moskowitz), ahora con evidencia estadística propia.

## Matiz honesto

- El `drawdown120` también muestra separación (alza +0.035 vs drawdown −0.149) pero su coeficiente no fue significativo en la regresión (por correlación con vol). La señal dominante es **la volatilidad**.
- n de periodos mensuales = 95 (~8 años), suficiente para la regresión.

---

*Documento de referencia del proyecto Qlib Work. Complementa `plan_E3_quinn_futuro.md` (Semana 3).`
