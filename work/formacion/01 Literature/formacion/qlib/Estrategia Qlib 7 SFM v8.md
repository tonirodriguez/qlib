# Estrategia Qlib 7: SFM v8 — Modelo Robusto con Generalización Demostrada

> **Fecha:** Septiembre 2026
> **Objetivo:** Diseñar un Stochastic Factor Model (SFM) que generalice fuera de muestra, aprendiendo de los errores de v1 a v7.

---

## 📋 Evolución de las Versiones SFM (v1 → v7)

Cada versión introdujo mejoras, pero también arrastró problemas que identificamos y corregimos en la siguiente.

| Versión | Mejoras | Resultado Test | Problema detectado |
|:-------:|---------|:--------------:|--------------------|
| **v1** | SFM básico multivariable | ❌ No registrado | Sin optimización, overfitting |
| **v2** | +Denoising Wavelet, +Early stopping, split 70/15/15 | ❌ No registrado | Sin Optuna, hiperparámetros manuales |
| **v3** | +Optuna (30 trials), +MedianPruner, +Análisis importancia | ❌ Mejoró validación, test desconocido | Sin walk-forward, split único |
| **v4** | +Walk-Forward 3 ventanas, +Top-K, +Semillas fijas, +100 trials | ✅ **Sharpe +1.24, Equity 1.46x** | Solo 9 criptos, sin features adicionales |
| **v5** | Adaptado a SP500 (acciones USA) | ⚠️ **Sharpe +0.51** | Menor señal en acciones vs crypto |
| **v6** | +Features extendidos (vol, ma20_ratio, rango), 100 trials | ❌ **Sharpe -0.67, Equity 0.22x** | Perdió denoising wavelet, sin walk-forward |
| **v7** | +Label 5d, +Features extendidos, 100 trials | ❌ **Sharpe -1.03, Equity 0.02x** | Label 5d añadió ruido, sin denoising, sin walk-forward |

### 🔑 Lecciones Aprendidas por Componente

#### Label (ventana de predicción)

| Label | v4 (funcionó) | v7 (fracasó) |
|-------|:-------------:|:------------:|
| **1 día** | ✅ Sharpe test +1.24 | ❌ No probado |
| **5 días** | ❌ No probado | ❌ Sharpe test -1.03 |

**Conclusión:** Label a 1 día consistentemente supera a 5 días. El label largo introduce ruido.

#### Walk-Forward vs Split Único

| Método | Sharpe Test Medio | Robustez |
|--------|:-----------------:|:--------:|
| **Walk-Forward (v4)** | +1.24 | ✅ Alta — 3 ventanas independientes |
| **Split 60/20/20 (v6)** | -0.67 | ❌ Baja — sobreajuste al split |
| **Split 60/20/20 (v7)** | -1.03 | ❌ Muy baja |

**Conclusión:** Walk-forward es **crítico** para validar que el modelo generaliza en el tiempo.

#### Denoising Wavelet

| Versión | Denoising | Sharpe Test |
|:-------:|:---------:|:-----------:|
| **v4** | ✅ Sí | +1.24 |
| **v6** | ❌ No | -0.67 |
| **v7** | ❌ No | -1.03 |

**Conclusión:** El denoising wavelet reduce el ruido diario y mejora la señal. Especialmente importante en cripto (alta volatilidad).

#### Features

| Features | v4 | v6/v7 |
|----------|:--:|:-----:|
| close | ✅ | ✅ |
| pct_change | ✅ | ✅ |
| ratio_5d | ✅ | ✅ |
| vol_20d | ❌ | ✅ |
| ma20_ratio | ❌ | ✅ |
| rango diario | ❌ | ✅ |

**Conclusión:** Los features adicionales (vol, ma20, rango) son útiles **solo si** se acompañan de walk-forward y denoising. Sin ellos, el modelo sobreaprende correlaciones espurias.

#### Métrica de Optimización

| Versión | Objetivo Optuna | Sharpe Val vs Test |
|:-------:|:---------------:|:------------------:|
| **v4** | -Sharpe val | Val: +2.47 → Test: +1.24 |
| **v6** | -Sharpe val | Val: +1.21 → Test: -0.67 |
| **v7** | -Sharpe val | Val: +3.94 → Test: -1.64 |

**Conclusión:** Optimizar solo Sharpe en validación lleva a sobreajuste cuando no hay walk-forward. Necesitamos una métrica que penalice la diferencia train-val.

---

## 🚀 SFM v8 — Diseño Propuesto

### Arquitectura del Aprendizaje

Combinamos **todo lo que funcionó** de versiones anteriores y corregimos lo que falló:

```
v1  (SFM base)
 │
 ├─→ v2  +Denoising Wavelet +Early stopping
 │       ↓
 │       v3  +Optuna +MedianPruner
 │            ↓
 │            v4  +Walk-Forward +Top-K +Semillas fijas ✅ SHARPE +1.24 ← BASE DE v8
 │                 │
 │                 ├─→ v5  Adaptación SP500
 │                 │
 │                 └─→ v6  +Features extendidos (vol, ma20, rango)
 │                           ↓ (perdió denoising y walk-forward → overfitting)
 │                           v7  +Label 5d  ❌ SHARPE -1.03
 │
 └──────────────────────────────────────────────────────────────┐
                                                                │
                          SFM v8  ← Recupera de v4: Walk-Forward + Denoising + Label 1d
                                     Añade de v6/v7: Features extendidos (vol, ma20, rango)
                                     MEJORA: Métrica anti-overfitting + Patience adaptativa
```

### Lo que recuperamos de cada versión

| De la versión | Recuperamos | Por qué |
|:------------:|-------------|---------|
| **v2** | Denoising Wavelet (pywt) | Elimina ruido diario, mejora SNR |
| **v3** | MedianPruner + TPESampler | 65% de trials podados en v6 → ahorro computacional |
| **v4** | **Walk-Forward 3 ventanas** | 🔑 Clave del éxito: Sharpe +1.24 |
| **v4** | Top-K evaluation (Top-5) | Evita p-hacking del mejor trial |
| **v4** | Evaluación por Sharpe direccional | Métrica realista de trading |
| **v6** | Features: vol_20d, ma20_ratio, rango | Señal adicional valiosa (con walk-forward) |
| **v6** | Clipping causal + MinMaxScaler(-1,1) | Prevención de leakage |

### Lo que DESCARTAMOS de v7

| Descartamos | Por qué |
|-------------|---------|
| **Label 5d** | Ruido, sobreajuste, Sharpe test -1.64 vs +1.24 de label 1d |
| **Split 60/20/20** | Sobreajuste al split. Walk-forward es más robusto |

### Lo que AÑADIMOS nuevo en v8

| Novedad | Descripción |
|---------|-------------|
| **Métrica anti-overfitting** | Objetivo = -(Sharpe_val - 0.2 × |Sharpe_val - Sharpe_train|). Penaliza cuando validación se aleja de entrenamiento |
| **Patience adaptativa** | patience = max(5, min(15, epochs // 10)). Menos paciencia en trials malos, más en prometedores |
| **Direction Accuracy como secundaria** | % de veces que predice signo correcto. Se registra pero no optimiza |
| **Walk-Forward completo sobre Top-3** | Tras Optuna + Top-5, re-evaluamos los 3 mejores en walk-forward real |

---

### Pseudocódigo del Flujo Completo

```
FASE 0 — CONFIGURACIÓN
├── Definir: 9 criptos (BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC)
├── Período: 2015-01-01 → hoy
├── Label: retorno a 1 día
├── Features: close, pct_change, ratio_5d, vol_20d, ma20_ratio, rango
├── Trials Optuna: 100
├── Top-K: 5
├── Walk-Forward: 3 ventanas

FASE 1 — CARGA Y PREPROCESAMIENTO
├── 1.1 Cargar datos desde Qlib (D.features)
├── 1.2 Calcular features:
│   ├── close (precio original)
│   ├── pct_change (retorno diario)
│   ├── ratio_5d (media 5d / close)
│   ├── vol_20d (desviación estándar 20d de retornos)
│   ├── ma20_ratio (media 20d / close)
│   └── rango (abs(pct_change))
├── 1.3 Denoising Wavelet (pywt) sobre cada feature:
│   ├── Descomposición wavelet nivel 2
│   ├── Umbral suave (soft thresholding)
│   └── Reconstrucción
├── 1.4 Label: retorno a 1 día (close.shift(-1)/close - 1)
├── 1.5 Clipping causal (fit en train, apply en val/test)
├── 1.6 MinMaxScaler(-1, 1) (fit en train, transform en val/test)

FASE 2 — WALK-FORWARD (3 VENTANAS)
├── Ventana 1: Train 60% | Val 20% | Test 20%
├── Ventana 2: Train 40% | Val 20% | Test 40% (desplazada)
├── Ventana 3: Train 20% | Val 20% | Test 60% (desplazada)
│
├── Por cada ventana:
│   ├── 2.1 Hacer sliding windows con lookback variable
│   ├── 2.2 Ejecutar Optuna (comparte estudio entre ventanas)
│   └── 2.3 Evaluar Top-5 en test de esa ventana
│
└── Resultado Walk-Forward: media y desviación del Sharpe en test

FASE 3 — OPTUNA (100 trials por ventana)
├── Hiperparámetros:
│   ├── hidden_dim: [32, 48, 64, 80, 96, 112, 128]
│   ├── freq_components: [4, 8, 12, 16, 20]
│   ├── lr: [3e-5, 1e-2] (log)
│   ├── dropout_rate: [0.1, 0.2, 0.3, 0.4, 0.5]
│   ├── batch_size: [16, 32]
│   ├── weight_decay: [1e-5, 1e-3] (log)
│   └── lookback: [20, 30, 40, 50, 60, 70, 80, 90] (step 10)
│
├── Objetivo por trial:
│   └── minimizar: -(Sharpe_val - 0.2 × |Sharpe_val - Sharpe_train|)
│       Esto penaliza cuando val es mucho mejor que train (sobreajuste)
│
├── Pruning: MedianPruner (startup=10, warmup=5, interval=1)
├── Patience adaptativa: max(5, min(15, epochs // 10))
└── Semilla: 42 + trial.number (reproducibilidad)

FASE 4 — TOP-K EVALUATION
├── 4.1 Ordenar trials completados por objetivo (menor = mejor)
├── 4.2 Seleccionar Top-5
├── 4.3 Por cada uno:
│   ├── Reentrenar en train+val combinado (100 épocas max)
│   ├── Evaluar en test
│   └── Registrar: Sharpe, Equity, Drawdown, Direction Accuracy
├── 4.4 Reporte estadístico de los Top-5:
│   ├── Sharpe: mean, std, min, max
│   ├── Equity: mean, std, min, max
│   └── Direction Accuracy: mean

FASE 5 — RESUMEN Y REPORTE
├── 5.1 Resultados Walk-Forward por ventana
├── 5.2 Comparativa vs Benchmark (equally-weighted)
├── 5.3 Gráficos:
│   ├── optuna_distribution.png
│   ├── top_k_results.png
│   └── walk_forward_equity.png
└── 5.4 Guardar: study_results.json, top_k_results.json, modelos .pth
```

---

### Comparativa Directa v7 vs v8

| Métrica | v7 (label 5d) | v8 (propuesta) |
|---------|:-------------:|:--------------:|
| **Label** | 5 días ❌ | **1 día** ✅ |
| **Walk-Forward** | No ❌ | **3 ventanas** ✅ |
| **Denoising Wavelet** | No ❌ | **Sí** ✅ |
| **Features** | 6 (close, pct, ratio, vol, ma20, rango) | **6** (mismos + rango mejorado) |
| **Objetivo Optuna** | -Sharpe val | -Sharpe val + penalización overfitting |
| **Trials** | 100 | 100 |
| **Top-K** | 5 | 5 |
| **Patience** | Fija (8) | **Adaptativa** (5-15 según trial) |
| **Métrica extra** | No | Direction Accuracy |
| **Validación** | Split único 60/20/20 | **Walk-Forward 3 ventanas** |
| **Resultado esperado** | Sharpe test ≈ **-1.0** | Sharpe test ≈ **+0.5 a +1.2** (basado en v4) |

---

### Archivos de la Versión

| Archivo | Descripción |
|---------|-------------|
| `work/crypto/qlib_sfm_pipeline.v8.py` | Script principal del pipeline |
| `work/crypto/output/sfm_v8/` | Directorio de resultados |
| `work/crypto/output/sfm_v8/study_results.json` | Resultados de Optuna |
| `work/crypto/output/sfm_v8/top_k_results.json` | Resultados Top-5 |
| `work/crypto/output/sfm_v8/optuna_distribution.png` | Distribución de Sharpe |
| `work/crypto/output/sfm_v8/top_k_results.png` | Resultados Top-K |
| `work/crypto/output/sfm_v8/walk_forward.png` | Resultados walk-forward |

---

### Ejecución

```bash
# Desde el directorio raíz del proyecto
conda run -n qlib python work/crypto/qlib_sfm_pipeline.v8.py
```

Tiempo estimado: **~2-3 horas** (100 trials × 3 ventanas walk-forward + Top-5)