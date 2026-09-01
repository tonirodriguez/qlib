# ROADMAP TRABAJO — Estrategia Cuantitativa Rentable con Operativa Diaria

> **Fecha:** Septiembre 2026 (revisado)
> **Última actualización:** 1 Septiembre 2026
> **Objetivo:** Generar una estrategia de inversión cuantitativa rentable con señales diarias, basada en Microsoft Qlib.

---

## 📊 RESUMEN DE EXPERIMENTOS REALIZADOS

### 🇨🇳 Mercado Chino (CSI300) — LightGBM + alpha158

| Experimento | Label | TopK | Ann Return | Std | Rank IC | Rank ICIR |
|------------|:-----:|:----:|:----------:|:---:|:------:|:---------:|
| **Baseline** | 1d | 50 | 14.73% | 0.0055 | 0.0487 | 0.4057 |
| **Label 5d** | 5d | 50 | 20.52% | 0.0049 | 0.0793 | 0.6141 |
| **Tuned (default 50)** | 1d | 50 | 11.06% | 0.0059 | 0.0495 | 0.3897 |
| **Tuned Top20** | 1d | 20 | 17.25% | 0.0087 | 0.0495 | 0.3897 |
| **Tuned Top30** | 1d | 30 | 15.19% | 0.0073 | 0.0495 | 0.3897 |
| **Tuned SoftTopk20** | 1d | 20 | 31.40% | 0.0081 | 0.0495 | 0.3897 |

- **Periodo:** Train 2008-2014 / Valid 2015-2016 / Test 2017-2020
- **Features:** alpha158 (158 factores técnicos)
- **Modelo:** LightGBM
- **Estrategia:** TopkDropoutStrategy / SoftTopkStrategy
- **Simulador:** diario, con costes de transacción (limit_threshold 0.095)

### 🇨🇳 Mercado Chino (CSI500)

| Experimento | Label | TopK | Ann Return | Std | Rank IC | Rank ICIR |
|------------|:-----:|:----:|:----------:|:---:|:------:|:---------:|
| **CSI500 Baseline** | 1d | 50 | 13.33% | 0.0052 | 0.0459 | 0.4722 |

- Mismo periodo y modelo, sobre 500 valores chinos mid-cap

### 🇺🇸 Mercado USA (S&P 500)

| Experimento | Estado | Periodo |
|------------|:------:|:-------:|
| **SP500 Baseline alpha158** | ⏳ Config listo, no ejecutado | 2008-2025 |
| **SP500 Label 5d** | ⏳ Config listo, no ejecutado | 2008-2025 |

- **Región:** US
- **Benchmark:** ^GSPC
- **Features:** alpha158
- **Modelo:** LightGBM
- **TopK:** 30

### 🔮 Mercado Crypto (SFM — Stochastic Factor Model) ✅ COMPLETADO

| Versión | Estado | Sharpe Test | Equity Test |
|:-------:|:------:|:-----------:|:-----------:|
| **v4** | ✅ Walk-Forward + Denoising | +1.24 | 1.46x |
| **v5 (SP500)** | ⚠️ Señal más débil | +0.51 | 1.43x |
| **v6** | ❌ Sin denoising ni walk-forward | −0.67 | 0.22x |
| **v7** | ❌ Label 5d + sin denoising | −1.03 | 0.02x |
| **v8** | 🚀 **Modelo definitivo** | **+2.17** | **10.49x** |

### 🧪 Otras configs pendientes

| Config | Estado |
|--------|:------:|
| **alpha360** (CSI300, más features) | ⏳ Config lista, no ejecutada |
| **SP500 US label5d** | ⏳ Config lista, no ejecutado |

---

## 🎯 NUEVA HOJA DE RUTA — Hacia Producción (Septiembre 2026)

Con el éxito de **SFM v8** (Sharpe +2.17, Equity 10.49x), el objetivo cambia: **llevar el modelo crypto a señal diaria operativa**.

### ✅ Logros alcanzados

1. **SFM v8 validado** — Sharpe test +2.17, mejor equity 20.03x
2. **Modelo entrenado** — `sfm_top3.pth` con mejores parámetros
3. **Pipeline de datos** — `download_crypto_coingecko.py` funcional
4. **Documentación completa** — evolución v1→v8, resultados, comparativas

---

### 🔴 Fase 0 — Señal Diaria (Inmediata, esta semana)

| # | Tarea | Esfuerzo | Estado |
|:-:|-------|:--------:|:------:|
| 1 | 🔴 **Script de señal diaria** (`sfm_daily_signal.py`) — carga modelo v8, descarga datos, genera predicción para hoy | Bajo (2h) | ✅ **HECHO** |
| 2 | 🔴 **Script de actualización de datos** (`download_crypto_coingecko.py`) — fix del manifest.json aplicado | Bajo (30min) | ✅ **HECHO** |
| 3 | 🟡 **Configurar cronjob** que ejecute: descarga → predicción → señal → notificación | Bajo (30min) | ⏳ Pendiente |
| 4 | 🟡 **Notificación** de la señal diaria (email/Telegram/consola) | Bajo (1h) | ⏳ Pendiente |

#### 📋 Especificación de la señal diaria

```
Flujo:
  1. python download_crypto_coingecko.py   → Actualiza datos hasta ayer
  2. python sfm_daily_signal.py             → Genera predicción para hoy
  3. Salida: ranking de criptos con score, señal COMPRA/VENTA/ESPERAR

Formato de salida:
  📊 SEÑAL DIARIA SFM — 2026-09-02
  ========================================
  🥇 COMPRA:  BTC  | Score: +0.0351 | Confianza: ALTA
  🥈 COMPRA:  ETH  | Score: +0.0284 | Confianza: ALTA
  🥉 ESPERAR: SOL  | Score: +0.0082 | Confianza: BAJA
  ...
```

---

### 🟡 Fase 1 — Robustecimiento (1-2 semanas)

| # | Tarea | Esfuerzo | Impacto |
|:-:|-------|:--------:|:-------:|
| 5 | 🟡 **Ensemble de Top-3 modelos** — combinar predicciones de sfm_top1, sfm_top3, sfm_top4 | Medio (3-4h) | Reduce varianza, Sharpe esperado +2.0-2.5 |
| 6 | 🟡 **Paper trading automático** — ejecuta la señal y registra resultados en un archivo de historial | Medio (4-5h) | Validación en vivo sin riesgo |
| 7 | 🟢 **Dashboard Streamlit** — señal diaria, equity curve, métricas en tiempo real | Medio (3-4h) | Visibilidad del rendimiento |
| 8 | 🟢 **Alertas de decaimiento** — detectar si la señal empieza a fallar (Sharpe rodante < 1.0) | Bajo (2h) | Prevención de pérdidas |

---

### 🟠 Fase 2 — Diversificación (2-4 semanas)

| # | Tarea | Esfuerzo | Por qué |
|:-:|-------|:--------:|---------|
| 9 | 🟡 **Extender a más criptos** (BNB, DOT, AVAX, etc.) | Bajo (1h) | Más oportunidades, menor concentración |
| 10 | 🟡 **Reentrenamiento automático** — ejecutar v8 cada 2-4 semanas con datos nuevos | Medio (3-4h) | Evitar decaimiento de la señal |
| 11 | 🟢 **Probar SP500 US baseline** — config ya lista, datos ya existen | Bajo (1h) | Diversificación a acciones |

---

### 🔵 Fase 3 — Producción Real (1-2 meses)

| # | Tarea | Esfuerzo | Dependencias |
|:-:|-------|:--------:|:------------|
| 12 | 🔵 **Integración con broker** (Interactive Brokers) | Alto (1-2 semanas) | Fase 1, Fase 2 |
| 13 | 🔵 **Risk management automático** — stop-loss, VaR diario, posición máxima | Medio (1 semana) | #12 |
| 14 | 🔵 **Backup y recuperación** del sistema completo | Medio (3-4 días) | #12 |

---

### 🔮 Fase 4 — Modelos Avanzados (Largo plazo)

| # | Tarea | Esfuerzo |
|:-:|-------|:--------:|
| 15 | **Ensemble multimodelo:** LightGBM + GRU + Transformer | Alto |
| 16 | **Model routing:** ligero para diario, pesado para recalibración semanal | Medio |
| 17 | **Análisis fundamental + NLP** sobre noticias | Alto |

---

## 📋 PRIORIDADES INMEDIATAS ACTUALIZADAS

| # | Tarea | Esfuerzo | Impacto | Estado |
|:-:|-------|:--------:|:-------:|:------:|
| 1 | 🔴 Señal diaria SFM v8 | Bajo | **Crítico** — primer paso a producción | ✅ **HECHO** |
| 2 | 🔴 Descarga automática de datos | Bajo | **Crítico** — datos frescos cada día | ✅ **HECHO** |
| 3 | 🟡 Cronjob diario | Bajo | **Crítico** — automatización | ⏳ Pendiente |
| 4 | 🟡 Paper trading | Medio | Alto — validación en vivo | ⏳ Pendiente |
| 5 | 🟡 Ensemble Top-3 | Medio | Alto — mejora robustez | ⏳ Pendiente |
| 6 | 🟢 SP500 US baseline | Bajo | Medio — diversificación | ⏳ Pendiente |
| 7 | 🟢 Dashboard monitorización | Medio | Medio — visibilidad | ⏳ Pendiente |

---

## RECURSOS DISPONIBLES

- **QLib:** `qlib/` — framework principal (datos, modelos, backtesting)
- **Modelo SFM v8:** `work/crypto/output/sfm_v8/sfm_top3.pth` (mejor modelo, Sharpe 2.74)
- **Configs:** `qlib/config/` — 14 configs YAML para distintos universos y variantes
- **MLflow runs:** `qlib/mlruns/` — 9 experimentos con métricas almacenadas
- **Notebooks:** `qlib/notebooks/` — 3 notebooks de análisis
- **Documentación SFM:** `work/formacion/01 Literature/formacion/qlib/`
  - `sfm-comparativa-scripts.md` — evolución v1→v8
  - `sfm-v8-resultados.md` — resultados detallados de v8
  - `Estrategia Qlib 7 SFM v8.md` — diseño y pseudocódigo

---

*Documento generado: 30 Junio 2026*
*Última revisión: 1 Septiembre 2026 — actualizado con resultados SFM v8 y plan hacia producción*
*Próxima revisión sugerida: tras completar Fase 0 y Fase 1*