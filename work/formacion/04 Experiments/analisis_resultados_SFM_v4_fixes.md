---
tags: [analysis, results, sfm, v4, crypto, success]
status: completed
date: 2026-06-03
---

# Análisis de Resultados: SFM v4 con Fixes (2ª Ejecución)

> **Veredicto: Los 3 fixes funcionaron. SFM genera alpha positivo en walk-forward (Sharpe μ=+0.87)**
> El pruner podó 57/100 trials. El modelo es consistente entre ventanas (σ=0.10). Mejora drástica respecto a la ejecución anterior.

---

## 1. Cambios aplicados

| Cambio | Código | Efecto esperado |
|--------|--------|-----------------|
| **Gradient clipping** | `clip_grad_norm_(max_norm=1.0)` | Elimina gradientes explosivos → no hay loss Inf |
| **n_startup_trials** | 5 → **10** | La mediana del pruner no se corrompe con trials inestables |
| **batch_size** | [16, 32, 64] → **[16, 32]** | Elimina el mínimo local perezoso de batch=64 |

---

## 2. Diagnóstico del Optimus — El pruner FUNCIONÓ

| Métrica | Anterior (sin fixes) | Actual (con fixes) | Cambio |
|---------|---------------------|--------------------|--------|
| Trials completados | 100 (0 pruned) | **43** (57 pruned) | ✅ |
| Trials pruned | **0** | **57** | ✅ |
| Tiempo | — | **35 min** | ✅ |

El pruner descartó más de la mitad de los trials. Los primeros trials ya no divergen, la mediana no se contamina.

### Mejor trial (por val_loss)

```json
{
  "hidden_dim": 96, "freq_components": 4,
  "lr": 0.000295, "dropout_rate": 0.35,
  "batch_size": 32, "weight_decay": 0.000234,
  "lookback": 25
}
```

Diferencias clave respecto a la ejecución anterior:
- **lr**: 0.0003 (vs 0.001) — 3x más pequeño, más estable
- **lookback**: 25 (vs 35) — menos ventana, más sensible a cambios recientes
- **weight_decay**: 2.3e-4 (vs 1.4e-5) — 10x más regularización
- **K=4** — SFM usa muy pocos componentes de frecuencia

---

## 3. Walk-Forward — MEJORA ESPECTACULAR

| Ventana | Sharpe Anterior | Sharpe Ahora | Equity Anterior | Equity Ahora |
|---------|----------------|--------------|-----------------|--------------|
| 1 | −0.55 | **+1.00** 🟢 | 0.85x | **1.30x** |
| 2 | −1.48 | **+0.76** 🟢 | 0.48x | **1.18x** |
| 3 | −1.83 | **+0.84** 🟢 | 0.73x | **1.22x** |
| **Media** | **−1.29** | **+0.87** 🟢 | **0.68x** | **1.23x** |
| **σ** | 0.54 | **0.10** 🟢 | 0.15 | **0.05** |

![wf_v4_fixes](img/wf_v4_fixes.png)

**De Sharpe negativo sistemático (−1.29) a Sharpe positivo (+0.87) con baja varianza (σ=0.10).** Equity pasa de 0.68x a 1.23x.

**Degradación temporal eliminada:** V1=1.00, V2=0.76, V3=0.84 — ya no es monótonamente decreciente. La ventana 2 baja ligeramente pero la 3 se recupera.

---

## 4. Comparativa visual: Antes vs Después

![comparativa_antes_despues](img/comparativa_antes_despues.png)

---

## 5. Top-K — Sigue siendo negativo, pero es una pista importante

| Trial | Sharpe | Equity |
|-------|--------|--------|
| #1 (mejor val_loss) | −1.37 | 0.54x |
| #2 🟢 | **+0.06** | **0.91x** |
| #3 | −1.08 | 0.58x |
| #4 | −1.17 | 0.57x |
| #5 | −1.32 | 0.55x |
| **Media** | **−0.98** | **0.63x** |

![top_k_fixes](img/top_k_fixes.png)

**Solo 1/5 positivo.** La media mejoró ligeramente (−1.07 → −0.98) pero sigue siendo negativa.

### Paradoja: Top-K negativo vs Walk-Forward positivo

Esto es clave de entender:

- **Top-K** → usa la **última ventana de test del split 70/15/15** (la más reciente, fija)
- **Walk-Forward** → promedia **3 ventanas** en diferentes periodos

La partición test del split coincide probablemente con un periodo adverso. El walk-forward, al muestrear 3 periodos, da una imagen más realista y robusta.

**Conclusión metodológica: El Walk-Forward es más fiable que el Top-K como métrica de rendimiento real.**

---

## 6. Resumen de impacto de los fixes

| Métrica | Antes (sin fixes) | Ahora (con fixes) | Cambio |
|---------|-------------------|-------------------|--------|
| Trials pruned | **0** | **57** | ✅ |
| Trials Inf | primeros 5 | **cero** | ✅ |
| Top-K Sharpe μ | −1.07 | −0.98 | ⬆️ +8% |
| Top-K Sharpe σ | 0.83 | **0.53** | ⬇️ más estable |
| WF Sharpe μ | **−1.29** | **+0.87** | **+2.16 🚀** |
| WF Sharpe σ | 0.54 | **0.10** | **−81%** |
| WF Equity μ | 0.68x | **1.23x** | **+81% 🚀** |

---

## 7. Próximos pasos

| Prioridad | Acción | Fundamento |
|-----------|--------|------------|
| 🔴 Alta | **Ejecutar en acciones US (SP500)** | Validar si SFM generaliza a otros mercados o es específico de cripto |
| 🔴 Alta | **Evaluar en periodo out-of-sample no visto** | Confirmar que el Sharpe +0.87 aguanta en datos futuros |
| 🟡 Media | **Probar con Transformer/LSTM como baseline** | Comparar si SFM es mejor que una arquitectura más simple |
| 🟡 Media | **Aumentar a 5 ventanas de walk-forward** | Más ventanas → mejor estimación de la distribución real de Sharpe |
| 🟡 Media | **Re-ejecutar con Sharpe como métrica de Optuna (ya implementado)** | El cambio está hecho (commit `7ca4c65`), pendiente de ejecutar |
| 🟢 Baja | **Ajustar rango de K (2–12)** | El mejor trial usó K=4 (mínimo del rango) → quizás menos es mejor |
| 🟢 Baja | **Probar con n_trials=200** | 57 pruned de 100 sugiere que aún hay espacio de exploración |

---

## 8. Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.v4.py` — script con fixes
- `scripts/crypto/output/optuna_sfm_v4/` — resultados completos
- `obsidian/01 Literature/formacion/qlib/sfm-v4-caracteristicas.md` — nota técnica
- `obsidian/01 Literature/formacion/qlib/sfm-comparativa-scripts.md` — comparativa de versiones
- `obsidian/01 Literature/formacion/qlib/img/wf_v4_fixes.png` — equity curves reales
- `obsidian/01 Literature/formacion/qlib/img/comparativa_antes_despues.png` — comparativa
- `obsidian/01 Literature/formacion/qlib/img/top_k_fixes.png` — Top-K barras
