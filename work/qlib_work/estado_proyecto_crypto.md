# 🪙 Proyecto Crypto — Estado y lectura (2026-08-29)

> **Proyecto:** Qlib Work (frente crypto)
> **Fecha:** 2026-08-29
> **Fuente:** `work/formacion/Estado Crypto.md` (actualizado 2026-08-15) + salidas del piloto en `work/crypto/output/universe_comparison_pilot/`.
> **Objetivo de este doc:** resumen accesible del estado del frente crypto y de los próximos pasos, alineado con el resto de `qlib_work/`.

---

## 📌 Qué es

Sistema de **investigación cuantitativa sobre criptomonedas** con Qlib + SFM (State Fusion Model) + Optuna. Universo: **BTC, ETH, SOL, XLM, ADA, XRP, DOGE, LINK, LTC**.

**Fase:** exclusivamente **investigación** (sin paper-trading ni capital real). Todo el pipeline es **causal y trazable** (sin fuga temporal): provider atómico, datos cerrados con manifests/hashes, nested walk-forward, escenarios de costes.

---

## 🚦 Estado de los gates

| Gate | Estado | Evidencia |
|---|---|---|
| Contención de prototipos antiguos (con fuga) | ✅ Superado | salidas separadas, `research-only` |
| Causalidad del preprocessing | ✅ Superado | tests anti-leakage; clipping/scaler por train |
| Datos cerrados y trazables | ✅ Superado | 1.099 velas, manifests SHA-256 |
| Nested walk-forward | ✅ Técnicamente | smoke 2 folds; holdout no evaluado |
| Modelo de costes v2 | ✅ En módulo | `execution_costs_v2.py`; **falta alimentar datos reales** |
| **Comparación de universos** | ⚠️ **Piloto completo → gates RECHAZAN** | 6/6 combos; `holdout_may_be_opened: false` |
| **Holdout final** | 🔒 Bloqueado | 2026-03-02 → 2026-08-13, 165 fechas; `evaluated: false` |
| **Paper trading** | 🔒 Bloqueado | depende de todos los gates anteriores |

---

## 📊 Resultado del piloto (dato clave)

Sharpe neto medio por universo (6 folds, costes calibrados train-only, nocional $10k):

| Universo | Sharpe medio | Mediana | Desv. | Folds positivos | Peor DD |
|---|---:|---:|---:|---:|---:|
| Original 5 | **−0.379** | 0.040 | 1.65 | 3/6 | −51% |
| Completo 9 | −1.229 | −0.969 | 1.33 | 1/6 | −54% |
| Reducido 8 (sin XLM) | −0.904 | −0.567 | 1.40 | 2/6 | −59% |

**Lectura honesta:** el piloto **confirma inestabilidad, no rentabilidad**. Dispersión enorme (desv. 1.3-1.7) y el **fold 3 (2025-08 → 2026-03) es el peor en las 6 combinaciones** (−2 a −3.2). El original de 5 es el "menos malo" (única mediana ≥ 0), pero **ninguno supera los gates predeclarados**. Por tanto, **el holdout sigue correctamente cerrado**.

---

## 🔴 Próximos pasos (en orden, según el plan accionable)

1. **B2 — Alimentar el modelo de costes v2 con datos reales.** Implementado ✅; faltan: fee schedule del venue, bid/ask y profundidad (mientras no existan → degrada a proxy). La fontanería está lista (se activa con env vars, sin tocar código).
2. **B3 — Conectar baselines + DSR al experimento formal.** `baselines.py` implementado ✅ (bootstrap por bloques, PSR, DSR); falta conectarlo con `n_trials` = universos × seeds.
3. **D1 — Experimento formal (Fase 4).** 3 universos × 3 seeds (42,43,44), 30 trials/fold, 60 épocas. Empieza con **dry-run** (sin cómputo) para revisar la matriz. **Largo:** el piloto tardó ~3h/combo; el formal será mucho más.
   - Si ninguna variante supera los gates estables → **decisión correcta: no seleccionar y no abrir el holdout**.
4. **D2 — Holdout final** (solo si D1 pasa gates): definir umbrales antes de mirarlo, abrirlo una sola vez, informe inmutable.
5. **D3 — Paper trading** (solo si holdout aprueba): controles stale/drawdown/kill-switch + ≥30 días de simulación.

**Deuda no bloqueante:** lockfile multiplataforma + CI, mover `v5` (S&P) fuera de `work/crypto`, alertas freshness/gaps, universo point-in-time.

---

## 💡 Valoración (lectura de hoy)

- El frente crypto está **bien construido** (riguroso, sin fuga, gates declarados antes de ver resultados) — es un buen ejemplo de proceso de investigación disciplinado.
- **Está honestamente parado en investigación**: el piloto no dio rentabilidad estable, y el sistema correctamente **no avanza** hacia holdout/paper hasta que un experimento formal justifique abrirlo.
- No debe **contaminar** el plan principal de `qlib_work` (acción E1/E2/E3 en papel): frente separado, su prioridad es baja frente a la medición de las estrategias de acciones.

---

*Documento de referencia del frente crypto. Complementa `work/formacion/Estado Crypto.md` y `work/crypto/`.*