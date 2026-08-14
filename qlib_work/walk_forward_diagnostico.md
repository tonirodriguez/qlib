# 🧪 Walk-Forward Validation — Resultado y Diagnóstico (2026-08-14)

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — validación de robustez del modelo v5
> **Contexto:** tras lograr +24.3% absoluto / Sharpe 1.10 en backtest (v5, universo tech_giants), necesitábamos verificar si ese resultado era *alpha real* o *overfitting* al periodo fijo de test.

---

## 1. Método

**Walk-forward (out-of-sample)** en lugar de una sola división train/valid/test:
- Entrenar SOLO con datos pasados, predecir el siguiente periodo de 1 año (OOS), avanzar la ventana
- Modelo: LightGBM + Alpha158 (misma config que v5)
- Universo: tech_giants · label retorno 10 días
- Se concatena todo lo OOS y se mide IC agregado + long-short spread

## 2. Resultados

**IC agregado out-of-sample: 0.0078** · **Long-short spread: +0.03% (10d)**

| Ventana | Periodo test (OOS) | Muestras | IC |
|---|---|---|---|
| 1 | 2022 | 3,922 | +0.0303 |
| 2 | 2023 | 4,000 | −0.0130 |
| 3 | 2024 | 4,016 | +0.0032 |
| 4 | 2025 | 4,016 | +0.0184 |
| 5 | 2026 (H1) | 2,304 | −0.0056 |
| **Total** | | **18,258** | **+0.0078** |

## 3. Veredicto

**⚠️ El modelo NO tiene alpha predictivo robusto fuera de muestra.**

- IC agregado **0.0078** ≈ estadísticamente cero (ruido); ICs por ventana oscilan entre −0.013 y +0.03 (inestables / alternando signo)
- **Long-short spread +0.03%** en 10 días: insignificante (una señal útil daría >0.5-1%)
- El alpha **no se sostiene OOS** → el +24% del backtest no era edge predictivo genuino.

## 4. Interpretación honesta

**Lo que realmente pasó:**
- El **+24.3% "absoluto"** del backtest v5 refleja en gran parte la **subida del sector tech (beta) en 2022-2026**, no alpha del modelo.
- El **exceso vs benchmark** (~7%) era modesto y **se degrada fuera de muestra** — no es un edge real.
- Las mejoras aplicadas (universo, rebalanceo semanal, vol-targeting, costes IB) optimizaron la **infraestructura de ejecución** correctamente, pero **no crean predicción**. Redujeron costes y rotación (logos ~5pp de gap), pero la fuente de señal (LightGBM + Alpha158) no aporta.

**Conclusión clave:** hemos construido bien el *marco* de ejecución, pero la **predicción en sí no tiene poder** en este universo/config. Ningún ajuste de topk/rebalanceo/número de posiciones puede arreglarlo — el problema es la fuente de alpha.

## 5. Lecciones y hoja de ruta

### Lo que SÍ hemos validado (positivo)
- Infraestructura Qlib funcionando de extremo a extremo (datos US, entrenamiento, backtest, costes reales IB)
- Impacto de cada palanca: universo (decisivo), rebalanceo semanal (redujo costes), vol-targeting (mejora riesgo)
- Manejo de costes realistas y metodología rigurosa (walk-forward para no autoengañarnos)

### El problema real a resolver
- **LightGBM + Alpha158 no produce señal robusta** en este universo
- Antes de añadir más complejidad, hay que encontrar una fuente de alpha con **base empírica** y que **pase walk-forward**

### Direcciones a explorar (con mayor base para alpha)
1. **Momentum puro** — el script `qlib_us_simple_signal.py` ya lo intuía; momentum tiene respaldo empírico extenso y suele pasar OOS.
2. **Factores estilo** (value, quality, low-vol) sobre el universo.
3. **Combinación de señales** (momentum + algo ortogonal).
4. **Aceptar beta/cartera de índice + gestión de riesgo** si no se encuentra alpha robusto — una cartera pasiva de calidad con buen riesgo puede ser más honesta que forzar un modelo que no predice.

### Criterio de aceptación para el próximo modelo
Un modelo solo se considerará listo si pasa walk-forward con **IC agregado > 0.02-0.03** sostenido y long-short spread real, además del backtest.

---

*Documento de referencia del proyecto Qlib Work. Se actualiza con cada experimento.*
