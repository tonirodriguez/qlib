# ROADMAP TRABAJO — Estrategia Cuantitativa Rentable con Operativa Diaria

> **Fecha:** Junio 2026
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

### 🔮 Mercado Crypto (SFM — Systematic Factor Model)

Documentado en el vault:
- **SFM v4:** Backtest 2018-2026 (múltiples runs, análisis, fixes)
- **SFM v5:** Sobre SP500
- Hipótesis, decisiones metodológicas y preguntas abiertas en `04 Experiments/`

### 🧪 Otras configs pendientes

| Config | Estado |
|--------|:------:|
| **alpha360** (CSI300, más features) | ⏳ Config lista, no ejecutada |
| **SP500 US label5d** | ⏳ Config lista, no ejecutado |

---

## 🎯 RECOMENDACIONES — HOJA DE RUTA

### ✅ Lo que funciona hasta ahora

1. **Label 5d > Label 1d.** La señal a 5 días da mejor Rank IC (0.079 vs 0.049) y mejor Sharpe
2. **SoftTopkStrategy > TopkDropoutStrategy.** SoftTopk20: 31.4% vs Topk20: 17.25% anual
3. **CSI300 > CSI500.** Más líquido, menos ruido
4. **LightGBM es sólido pero deja margen.** Rank IC 0.05-0.08 → espacio para modelos más expresivos

---

### Fase 1 — Mejorar el modelo actual 🟢 Corto plazo

- [ ] **Probar GRU y Transformer** de QLib — capturan no-linearidades que LightGBM no ve
- [ ] **Añadir features adicionales** (macro, sectores, momentum sectorial, volatilidad de mercado, rates)
- [ ] **Walk-forward validation** — evitar overfitting con ventanas temporales deslizantes

### Fase 2 — Expandir universos 🟡 Medio plazo

- [ ] **Ejecutar SP500 US baseline** — datos listos, config lista, bajo esfuerzo
- [ ] **Ejecutar alpha360** — más features, puede mejorar señal significativamente
- [ ] **Ejecutar SFM v5 sobre SP500** — ver si la señal de factores funciona fuera de crypto

### Fase 3 — Pipeline diario automatizado 🔴 Crítico para producción

- [ ] **Script diario automático:**
  1. Descarga datos del día anterior
  2. Genera predicciones con el modelo entrenado
  3. Calcula señales y ranking
  4. Genera órdenes según la estrategia (TopK, SoftTopK)
  5. Envía señales a broker (simulado o real)
- [ ] **Monitorización de decaimiento de señal:** reentrenar si Rank IC baja de threshold
- [ ] **Risk management:** stop-loss, VaR diario, límite drawdown, posición máxima por activo

### Fase 4 — Modelos avanzados 🔵 Largo plazo

- [ ] **Ensemble multimodelo:** LightGBM + GRU + Transformer con weighting dinámico
- [ ] **Model routing:** modelo ligero para predicciones rápidas, modelo pesado para recalibración semanal
- [ ] **Análisis fundamental + NLP** sobre noticias usando skills de análisis disponibles

---

## 📋 PRIORIDADES INMEDIATAS

| # | Tarea | Esfuerzo | Impacto estimado | Dependencias |
|:-:|-------|:--------:|:----------------:|:------------:|
| 1 | 🔴 Ejecutar SP500 US baseline | Bajo | Alto (nuevo universo) | Ninguna |
| 2 | 🔴 Ejecutar alpha360 | Bajo | Alto (más features) | Ninguna |
| 3 | 🟡 Construir pipeline diario | Medio | Crítico para vivo | #1, #2 |
| 4 | 🟡 Probar GRU/Transformer en CSI300 | Medio | Medio | Ninguna |
| 5 | 🟢 Walk-forward + feature engineering | Medio | Medio | #4 |
| 6 | 🟢 Ejecutar SFM v4/v5 | Bajo | Medio (validación) | Ninguna |

---

## RECURSOS DISPONIBLES

- **QLib:** `qlib/` — framework principal (datos, modelos, backtesting)
- **Configs:** `qlib/config/` — 14 configs YAML para distintos universos y variantes
- **MLflow runs:** `qlib/mlruns/` — 9 experimentos con métricas almacenadas
- **Notebooks:** `qlib/notebooks/` — 3 notebooks de análisis
- **Vault Obsidian:** `qlib/obsidian/` — documentación de conceptos, estrategias, experimentos
- **Wiki MkDocs:** `qlib/.site/llm-wiki/` — wiki navegable

---

*Documento generado: 30 Junio 2026*
*Próxima revisión sugerida: tras ejecutar fases 1-2*
