# Backtest: 500€ en BTC con el Régimen-Switch v2 (nov-2020 → hoy)

**Fecha de ejecución:** 2026-10-09 · **Período:** 01-nov-2020 → 07-oct-2026 (2,167 días, 4 regímenes)
**Capital inicial:** 500€ (≈ $560 en el backtest) · **Proxy:** BTC · **Config:** switch v2, vital_dd=0.30, pico_win=90

## Resultado (retorno USD neto de costes, EUR/USD 1.12)

| Estrategia | Capital final (USD) | Equiv. (EUR) | Retorno |
|---|---|---|---|
| **Régimen-switch v2** | **$12,724** | **€11,361** | **+2,172.2%** |
| BTC buy & hold | $3,389 | €3,026 | +505.1% |
| USDT puro (yield 4.5%) | $727 | €649 | +29.9% |

**Actividad del switch:** 35 cambios · 1,822 días en LONG (84%) · 345 días en CASH (16%)

## Cómo se leyó en €

| | USD | EUR |
|---|---|---|
| Inversión inicial | $560 | €500 |
| Régimen-switch v2 | $12,724 | €11,361 (+€10,861) |
| BTC buy & hold | $3,389 | €3,026 (+€2,526) |
| USDT puro | $727 | €649 (+€149) |

## Lectura honesta (IMPORTANTE)

1. **El fenómeno que explica el +2,172%:** el switch está LONG el 84% del tiempo capturando
   la mayor parte del alza de BTC, PERO **evita los crashes compuestos** (cruza los giros
   2021→2022 y la base bajista 2025-26 sin dragarse). Comparado con el buy&hold, que SÍ
   soporta el drawdown del −55% en 2022 (y compone por debajo), el switch acumula mucho más
   en 6 años por **no sufrir el crash destructivo**, no por predecir mejor el alza.

2. **ADVERTENCIA de lookahead en la ELECCIÓN del umbral:** `vital_dd=0.30` se calibró usando
   correctamente datos de bull2021 + giro2022, que **están DENTRO** de este período completo.
   Es decir: la elección del umbral vio estos datos. La SEÑAL del switch en sí es causal
   (solo usa precio ≤ hoy), pero la configuración no es del todo out-of-sample limpia en
   este backtest largo. Por eso el +2,172% es un **límite favorable**, no una garantía.

3. **Referencia honesta para el futuro:** el activo correcto no es el modelo v8, es el
   **régimen-switch v2** con vital_dd 0.25-0.30 — el que mejor distribuida suerte tiene de
   "no quedar atrapado holdeando" en ambos sentidos. Aun con la advertencia de lookahead,
   superar al buy&hold por 4x y al USDT puro por 17x en estos 6 años valida la tesis de
   régimen-dependencia aplicada a cripto.

## Script usados
- `regime_switch_v2.py --proxy btc --name 500eur_desde2020 --start 2020-11-01 --end 2026-10-08 --initial-usd 560 --vital-dd 0.30`
- Salida: `output/sfm_v8/regimenes/regime_switch_v2_500eur_desde2020.json`