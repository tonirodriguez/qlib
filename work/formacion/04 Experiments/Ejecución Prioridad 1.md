# Ejecución Prioridad 1 — SP500 US Baseline

> **Objetivo:** Ejecutar el baseline LightGBM + alpha158 sobre el mercado USA (S&P 500)
> **Fecha:** 30 Junio 2026
> **Config:** `config/workflow_baseline_lightgbm_alpha158_sp500_us.yaml`

---

## 📋 Detalles de la configuración

| Parámetro | Valor |
|-----------|:-----:|
| **Modelo** | LightGBM (LGBModel) |
| **Features** | alpha158 (158 factores técnicos) |
| **Train** | 2008-01-01 → 2018-12-31 |
| **Valid** | 2019-01-01 → 2021-12-31 |
| **Test** | 2022-01-01 → 2025-01-01 |
| **Estrategia** | TopkDropoutStrategy, topk=30, n_drop=3 |
| **Benchmark** | ^GSPC (S&P 500) |
| **Costes** | 0.05% open / 0.10% close / min $1 |
| **Account inicial** | $100,000,000 |

### Hyperparams del modelo

| Parámetro | Valor |
|-----------|:-----:|
| learning_rate | 0.0421 |
| max_depth | 8 |
| num_leaves | 210 |
| colsample_bytree | 0.8879 |
| subsample | 0.8789 |
| lambda_l1 | 205.6999 |
| lambda_l2 | 580.9768 |
| loss | mse |
| num_threads | 8 |

---

## 🚀 Instrucciones de ejecución

### Paso 1 — Preparar los datos USA

Los datos del mercado USA deben descargarse primero con la herramienta de Qlib:

```bash
cd qlib
.venv/bin/python -m qlib.tools.data.init.us_data
```

Esto descargará los datos a `~/.qlib/qlib_data/us_data/`.

### Paso 2 — Ejecutar el baseline

```bash
cd qlib
.venv/bin/python scripts/run_baseline_workflow.py \
  --config config/workflow_baseline_lightgbm_alpha158_sp500_us.yaml \
  --mode train
```

El flag `--mode train` ejecuta el workflow completo: entrena el modelo, genera predicciones, análisis de señal y backtest con costes de transacción.

---

## 📊 Output esperado

El experimento se registrará en MLflow con:
- **Métricas de señal:** IC, Rank IC, ICIR, Rank ICIR
- **Métricas de portfolio:** ann return, std, Sharpe, max drawdown, turnover
- **Parámetros** del modelo y configuración
- **Predicciones** para el periodo de test

El nombre del experimento en MLflow será: `qlib_baseline_lightgbm_alpha158_sp500_us`

---

## ⚠️ Dependencias

- El virtualenv debe estar activo: `qlib/.venv/`
- Qlib debe estar instalado desde el repo local en `vendor/microsoft-qlib/`
- Los datos USA deben descargarse antes de ejecutar
- La región configurada es `us` (REG_US)

---

## 🔗 Enlaces relacionados

- **Config:** `config/workflow_baseline_lightgbm_alpha158_sp500_us.yaml`
- **Script de ejecución:** `scripts/run_baseline_workflow.py`
- **Script para label5d:** `config/workflow_baseline_lightgbm_alpha158_sp500_us_label5d.yaml`
- **Roadmap general:** `04 Experiments/ROADMAP TRABAJO.md`

---

*Documento generado: 30 Junio 2026*
*Próximo paso tras ejecución: analizar resultados y comparar con CSI300*
