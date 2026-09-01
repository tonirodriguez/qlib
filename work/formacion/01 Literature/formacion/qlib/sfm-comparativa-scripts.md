# Comparativa de Scripts: qlib_sfm_pipeline

Evolución de los scripts del pipeline SFM para criptomonedas, desde v1 hasta la propuesta v8.

## Tabla comparativa completa (v1 — v8)

| Aspecto | **v1** | **graf** | **v2** | **v3** | **v4** | **v5 (SP500)** | **v6** | **v7** | **v8 (propuesta)** |
|---------|:------:|:--------:|:------:|:------:|:------:|:--------------:|:------:|:------:|:------------------:|
| **Archivo** | `qlib_sfm_pipeline.py` | `..._grafica.py` | `...v2.py` | `...v3.py` | `...v4.py` | `...v5.py` | `...v6.py`* | `...v7.py` | `...v8.py` |
| **Líneas** | 213 | 229 | 437 | 671 | 899 | 1031 | No existe** | 662 | 960 |
| **Extracción** | `DataHandlerLP` | `D.features` | `D.features` | `D.features` | `D.features` | `D.features` | `D.features` | `D.features` | `D.features` |
| **Label** | 1d | 1d | 1d | 1d | 1d | 1d | 1d | **5d** ❌ | **1d** ✅ |
| **Features** | close, pct, ratio | close, pct, ratio | close, pct, ratio | close, pct, ratio | close, pct, ratio | close, pct, ratio | **+vol_20d, ma20_ratio, rango** | **+vol_20d, ma20_ratio, rango** | **+vol_20d, ma20_ratio, rango** |
| **Wavelet Denoising** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| **Split** | Train único | 75/25 | **70/15/15** | **70/15/15** | **70/15/15** | **70/15/15** | **60/20/20** | **60/20/20** | **Walk-Forward 3 ventanas** |
| **Early Stopping** | ❌ | ❌ | ✅ patience=12 | ✅ + pruning | ✅ + pruning | ✅ + pruning | ✅ | ✅ | **✅ Paciencia adaptativa** |
| **Reentreno final** | ❌ | ❌ | ✅ train+val | ✅ best params | ✅ Top-K | ✅ Top-K | ✅ Top-K | ✅ Top-K | ✅ Top-K |
| **Optuna** | ❌ | ❌ | ❌ | ✅ **30 trials** | ✅ **100 trials** | ✅ **100 trials** | ✅ 100 trials | ✅ 100 trials | ✅ **100 trials** |
| **Semillas fijas** | ❌ | ❌ | ❌ | parcial | ✅ **completas** | ✅ completas | ✅ completas | ✅ completas | ✅ completas |
| **Top-K** | ❌ | ❌ | ❌ | ❌ | ✅ **Top-5** | ✅ Top-5 | ✅ Top-5 | ✅ Top-5 | ✅ **Top-5** |
| **Walk-Forward** | ❌ | ❌ | ❌ | ❌ | ✅ **3 ventanas** | ❌ | ❌ | ❌ | ✅ **3 ventanas** |
| **Métrica Optuna** | — | — | — | −Sharpe | −Sharpe | −Sharpe | −Sharpe | −Sharpe | **−(Sharpe − 0.2×\|ΔSharpe\|)** |
| **Métricas extra** | MSE | Equity | Sharpe, DirAcc | Sharpe, DirAcc, importancia HPs | μ/σ Sharpe, μ/σ Equity | μ/σ Sharpe, μ/σ Equity | μ/σ Sharpe, μ/σ Equity | μ/σ Sharpe, μ/σ Equity | **+ Direction Accuracy** |
| **Resultados reales** | — | — | — | — | **Sharpe test +1.24** ✅ | **Sharpe test +0.51** ⚠️ | **Sharpe test −0.67** ❌ | **Sharpe test −1.03** ❌ | — (pendiente ejecutar) |
| **Mercado** | Crypto | Crypto | Crypto | Crypto | Crypto | **SP500** | Crypto | Crypto | Crypto |
| **Salida** | carpeta actual | carpeta actual | carpeta actual | `output/optuna_sfm/` | `output/optuna_sfm_v4/` | `output/optuna_sfm_v5/` | `output/sfm_v6_full_history/` | `output/sfm_v7_label5d/` | `output/sfm_v8/` |

\* v6 no tiene archivo propio; fue una modificación directa sobre v4 sin walk-forward.
\*\* v6 y v7 son versiones evolutivas a partir del código de v4, con cambios incrementales.

---

## v1 — Pipeline básico

- Primer script funcional extraído de la nota original de 2.509 líneas
- Usa `DataHandlerLP` (propenso a errores de configuración)
- 20 epochs fijas, sin validación separada, sin denoising
- Basado en la arquitectura `SFMCellRefined` + `SFMModelRefined`

## graf — Pipeline con gráfica

- Abandona `DataHandlerLP` por `D.features` directo (más robusto)
- Añade backtesting Top-1 con comisiones y gráfica de equity
- Split 75/25, sin early stopping, sin denoising
- Primer script que realmente permite ver rendimiento visual

## v2 — Pipeline con denoising y early stopping

- **Wavelet Denoising**: DWT + umbral Donoho-Johnstone + IDWT (limpieza de ruido diario)
- **Split 70/15/15 cronológico**: respeta el orden temporal (no shuffle)
- **Early stopping** (patience=12) sobre validation loss
- **Reentreno final** sobre train+val combinado con LR reducido
- **Métricas**: Sharpe Ratio, precisión direccional
- Guarda modelo y scaler de forma persistente

## v3 — Pipeline con Optuna

- Todo lo de v2 +
- **Optuna**: 30 trials con TPESampler + MedianPruner
- **7 hiperparámetros optimizados**: hidden_dim, K, lr, dropout, batch_size, weight_decay, lookback
- **Pruning automático**: trials no prometedores se cancelan antes de terminar
- **Visualizaciones**: 5 gráficas del estudio
- **JSON de resultados**: params, estudio, todo exportable
- **Salida organizada**: todo en `output/optuna_sfm/`

## v4 — Pipeline con Optuna 100 trials + Top-K + Walk-Forward ✅

**Mejor resultado histórico: Sharpe test +1.24, Equity 1.46x**

- Todo lo de v3 +
- **100 trials Optuna** en lugar de 30 (convergencia más estable)
- **Semillas globales**: random + numpy + torch + cudnn + seed individual por trial
- **Top-K Evaluation**: evalúa los Top-5 mejores trials y reporta μ, σ, min, max de Sharpe/equity
- **Walk-Forward Validation**: 3 ventanas secuenciales con train creciente (robustez temporal)
- **Métrica de Optuna**: Sharpe en validación (antes MSE). Prune directo si Sharpe < −3
- **Gráficas**: histograma, Top-K, walk-forward SFM vs benchmark

## v5 — Adaptación a SP500 (acciones USA) ⚠️

- Basado en v4 pero adaptado para acciones del SP500
- **Resultado:** Sharpe test +0.51 (funciona, pero menor señal que en crypto)
- Estrategia Top-1 long/short (long la mejor predicción, short la peor)
- Para más detalle, ver [comparativa-v4-v5.md](comparativa-v4-v5.md)

## v6 — Features extendidos + 100 trials ❌

- **Añade**: vol_20d (desviación estándar 20d), ma20_ratio (media 20d / close), rango diario
- **Problema**: Perdió el denoising wavelet y el walk-forward de v4
- **Resultado**: Sharpe test **−0.67** — sobreajuste al dividir en 60/20/20 sin walk-forward
- **Lección**: Los features adicionales son útiles SOLO si se acompañan de denoising y walk-forward

## v7 — Label 5d + Features ❌

- **Cambio principal**: Label a 5 días (retorno acumulado en 5 sesiones)
- **Problema**: El label largo introduce ruido y el modelo aprende patrones que no generalizan
- **Resultado**: Sharpe val +3.94 (excelente en papel), pero Sharpe test **−1.03** — sobreajuste severo
- **Top-5 en test**: todos pierden capital (equity 0.02x a 0.05x)
- **Lección**: Label 1d consistentemente supera a label 5d. Validación sin walk-forward da métricas engañosas.

## v8 — Propuesta: Denoising + Walk-Forward + Label 1d + Métrica Anti-Overfitting 🚀

**Diseñado para recuperar el rendimiento de v4 (Sharpe +1.24) y superarlo con features extendidos.**

### Lo que recuperamos de versiones anteriores

| De la versión | Recuperamos | Por qué funcionó |
|:------------:|-------------|------------------|
| **v2** | Denoising Wavelet (pywt) | Elimina ruido diario — esencial en crypto de alta volatilidad |
| **v3** | MedianPruner + TPESampler | 65% pruning en v6 → ahorro computacional masivo |
| **v4** | **Walk-Forward 3 ventanas** | 🔑 Clave del éxito: Sharpe test +1.24 |
| **v4** | Top-K (Top-5) | Evita p-hacking del mejor trial |
| **v4** | Semillas fijas + reproducibilidad | Resultados consistentes entre ejecuciones |
| **v6/v7** | Features extendidos (vol, ma20, rango) | Señal adicional valiosa (con walk-forward) |
| **v6/v7** | Clipping causal + MinMaxScaler | Prevención de leakage |

### Lo que DESCARTAMOS de v7

| Descartamos | Por qué |
|-------------|---------|
| **Label 5d** | Ruido, sobreajuste severo, Sharpe test −1.64 vs +1.24 de label 1d |
| **Split 60/20/20** | Sobreajuste al split. Walk-forward es más robusto |

### Lo que AÑADIMOS nuevo en v8

| Novedad | Descripción |
|---------|-------------|
| **Métrica anti-overfitting** | Objetivo = −(Sharpe_val − 0.2 × \|Sharpe_val − Sharpe_train\|). Penaliza cuando val es mucho mejor que train |
| **Patience adaptativa** | patience = max(5, min(15, epochs ÷ 10)). Menos paciencia en trials malos |
| **Direction Accuracy** | % de acierto en predecir el signo (sube/baja). Se registra como métrica secundaria |
| **Walk-Forward completo** | Tras Optuna + Top-5, re-evaluamos Top-3 en walk-forward real |

### Pseudocódigo del flujo completo

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
│   ├── Descomposición wavelet nivel 2 (db2)
│   ├── Umbral suave Donoho-Johnstone
│   └── Reconstrucción
├── 1.4 Label: retorno a 1 día (close.shift(-1)/close - 1)
├── 1.5 Clipping causal (fit en train, apply en val/test)
├── 1.6 MinMaxScaler(-1, 1) (fit en train, transform en val/test)

FASE 2 — WALK-FORWARD (3 VENTANAS SECUENCIALES)
├── Ventana 1: Train 60% | Val 20% | Test 20%
├── Ventana 2: Train 40% | Val 20% | Test 40% (desplazada)
├── Ventana 3: Train 20% | Val 20% | Test 60% (desplazada)
│
├── Por cada ventana:
│   ├── 2.1 Hacer sliding windows con lookback variable
│   ├── 2.2 Clipping y scaling causales (fit en train de esa ventana)
│   ├── 2.3 Ejecutar Optuna
│   └── 2.4 Evaluar Top-5 en test de esa ventana
│
└── Resultado Walk-Forward: media y desviación del Sharpe, % ventanas con Sharpe > 0

FASE 3 — OPTUNA (100 trials por ventana principal)
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
│       (penaliza cuando val es mucho mejor que train = sobreajuste)
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

FASE 5 — WALK-FORWARD COMPLETO (sobre Top-3)
├── 5.1 Para cada Trial#1, #2, #3 del Top-K:
│   └── 5.1.1 Para cada ventana W1, W2, W3:
│       ├── Clipping + scaling causales
│       ├── Reentrenar desde cero en train de esa ventana
│       └── Evaluar en test de esa ventana
├── 5.2 Resultados:
│   ├── Sharpe medio entre todas las ventanas
│   ├── % de ventanas con Sharpe > 0
│   └── Desviación estándar entre ventanas (consistencia)

FASE 6 — RESUMEN Y REPORTE
├── 6.1 Resultados de todas las fases
├── 6.2 Comparativa vs Benchmark (equally-weighted)
├── 6.3 Gráficos:
│   ├── optuna_distribution.png (distribución del objetivo)
│   ├── top_k_results.png (Sharpe, Equity, DirAcc)
│   ├── walk_forward.png (métricas por ventana)
│   └── walk_forward_equity.png (curvas de equity)
└── 6.4 Guardar:
    ├── study_results.json
    ├── top_k_results.json
    ├── walk_forward_results.json
    └── modelos .pth (sfm_top1.pth ... sfm_top5.pth)
```

### Comparativa directa v7 vs v8

| Métrica | v7 (label 5d) | v8 (propuesta) |
|---------|:-------------:|:--------------:|
| **Label** | 5 días ❌ | **1 día** ✅ |
| **Walk-Forward** | No ❌ | **3 ventanas** ✅ |
| **Denoising Wavelet** | No ❌ | **Sí** ✅ |
| **Features** | 6 (close, pct, ratio, vol, ma20, rango) | **6** (mismos, con denoising) |
| **Objetivo Optuna** | −Sharpe val | **−(Sharpe_val − 0.2×\|ΔSharpe\|)** anti-overfitting |
| **Trials** | 100 | 100 |
| **Top-K** | 5 | 5 |
| **Patience** | Fija (8) | **Adaptativa** (5-15 según trial) |
| **Métrica extra** | No | **Direction Accuracy** |
| **Validación** | Split único 60/20/20 | **Walk-Forward 3 ventanas** + split |
| **Resultado esperado** | Sharpe test ≈ **−1.0** ❌ | Sharpe test ≈ **+0.5 a +1.2** (basado en v4) |

---

## Resumen de la evolución completa

```
v1 (213L) ──→ graf (229L) ──→ v2 (437L) ──→ v3 (671L) ──→ v4 (899L) ─╮
  básico       +gráfica      +denoising      +Optuna 30      +Optuna 100  │
                              +early stop     +pruning        +Top-K      │
                              +split          +gráficas       +Walk-Forw. │
                                                                          │
                                                                          │
                    v5 (1031L)  ←── SP500 (Sharpe +0.51) ⚠️              │
                    v6 (modif)  ←── +features, sin denoising ❌           │
                    v7 (662L)   ←── label 5d, +features ❌                │
                                                                          │
                    v8 (960L)   ←── ¡TODO lo que funcionó! 🚀            │
                                    Denoising + Walk-Forward + Label 1d  │
                                    + Features extendidos                 │
                                    + Métrica anti-overfitting            │
                                    + Patience adaptativa                 │
                                    + Direction Accuracy                   │
```

## Paquetes necesarios

| Paquete | v1 | graf | v2 | v3 | v4 | v5 | v6 | v7 | v8 |
|---------|:--:|:----:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `torch` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `numpy` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pandas` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `scikit-learn` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `qlib` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `matplotlib` | — | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `PyWavelets` | — | — | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `scipy` | — | — | ✅ (fb) | ✅ (fb) | ✅ (fb) | ✅ (fb) | — | — | — |
| `optuna` | — | — | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Instalación rápida

```bash
# v8 — completo
pip install torch numpy pandas scikit-learn matplotlib PyWavelets optuna

# Si falta qlib
pip install pyqlib
```

## Archivos

- `work/crypto/qlib_sfm_pipeline.py` — v1
- `work/crypto/qlib_sfm_pipeline_grafica.py` — versión con gráfica
- `work/crypto/qlib_sfm_pipeline.v2.py` — v2 (denoising + early stopping)
- `work/crypto/qlib_sfm_pipeline.v3.py` — v3 (Optuna 30 trials)
- `work/crypto/qlib_sfm_pipeline.v4.py` — v4 (Optuna 100 + Top-K + Walk-Forward) ✅
- `work/crypto/qlib_sfm_pipeline.v5.py` — v5 (SP500) ⚠️
- `work/crypto/qlib_sfm_pipeline.v7.py` — v7 (label 5d, features) ❌
- `work/crypto/qlib_sfm_pipeline.v8.py` — **v8 (propuesta)** 🚀

### Ejecutar v8

```bash
# Desde la raíz del proyecto
conda run -n qlib python work/crypto/qlib_sfm_pipeline.v8.py
```

Tiempo estimado: **~2-3 horas** (100 trials × 3 ventanas walk-forward + Top-5)

---

> Para una comparativa detallada entre v4 y v5, ver [comparativa-v4-v5.md](comparativa-v4-v5.md).
> Para la documentación completa de v8, ver [Estrategia Qlib 7 SFM v8](Estrategia%20Qlib%207%20SFM%20v8.md).