# Comparativa de Scripts: qlib_sfm_pipeline

Evolución de los scripts del pipeline SFM para criptomonedas.

| Aspecto | **v1** | **graf** | **v2** | **v3** | **v4** |
|---------|--------|----------|--------|--------|--------|
| **Archivo** | `qlib_sfm_pipeline.py` | `qlib_sfm_pipeline_grafica.py` | `qlib_sfm_pipeline.v2.py` | `qlib_sfm_pipeline.v3.py` | `qlib_sfm_pipeline.v4.py` |
| **Líneas** | 213 | 229 | 437 | 671 | 899 |
| **Extracción Qlib** | `DataHandlerLP` | `D.features` + Pandas | `D.features` + Pandas | `D.features` + Pandas | `D.features` + Pandas |
| **Wavelet Denoising** | ❌ | ❌ | ✅ DWT + thresholding + IDWT | ✅ DWT + thresholding + IDWT | ✅ DWT + thresholding + IDWT |
| **Fallback Savgol** | ❌ | ❌ | ✅ si no hay pywt | ✅ si no hay pywt | ✅ si no hay pywt |
| **Split** | Train único | 75/25 | **70/15/15** cronológico | **70/15/15** cronológico | **70/15/15** cronológico |
| **Early Stopping** | ❌ | ❌ | ✅ patience=12 | ✅ patience=15 (final) + pruning Optuna | ✅ patience=15 (final) + pruning Optuna |
| **Reentreno final** | ❌ | ❌ | ✅ train+val (10 épocas, LR/2) | ✅ train+val con best params | ✅ Top-K: reentrena top-5 con best params |
| **Optuna** | ❌ | ❌ | ❌ | ✅ 30 trials, 7 HPs, TPESampler, MedianPruner | ✅ **100 trials**, 7 HPs, TPESampler, MedianPruner |
| **Hiperparámetros optimizados** | — | — | — | hidden_dim, K, lr, dropout, batch_size, weight_decay, lookback | hidden_dim, K, lr, dropout, batch_size, weight_decay, lookback |
| **Semillas** | ❌ | ❌ | ❌ | solo TPESampler(seed=42) | ✅ random + numpy + torch + cudnn + seed por trial |
| **Top-K** | ❌ | ❌ | ❌ | ❌ | ✅ **Top-5**: μ, σ, min, max de Sharpe/equity |
| **Walk-Forward** | ❌ | ❌ | ❌ | ❌ | ✅ **3 ventanas** secuenciales con train creciente |
| **Estrategia** | — | Top-1 + comisión 0.1% | Top-1 + comisión 0.1% | Top-1 + comisión 0.1% | Top-1 + comisión 0.1% |
| **Métricas** | MSE por época | Equity curve | Equity, Sharpe, directional accuracy | Equity, Sharpe, directional accuracy + importancia de HPs | Equity, Sharpe, directional accuracy + μ/σ entre Top-K + walk-forward |
| **Resultados reales** | — | — | — | — | Sharpe μ=-1.07 (Top-K), μ=-1.29 (WF). Solo 1/5 trials positivo. Equity < 1.0 |
| **Visualización** | ❌ | `rendimiento_modelo_sfm.png` | ❌ | 5 gráficas Optuna + equity curve | `optuna_distribution.png`, `top_k_results.png`, `walk_forward.png` |
| **Guardado** | `.pth` + `.pkl` | ❌ | `sfm_multivariable_qlib_v2.pth` + `sfm_scalers_qlib_v2.pkl` | `sfm_multivariable_qlib_v3.pth` + scaler + JSON params | `sfm_top1.pth` a `sfm_top5.pth` + `study_results.json` + `top_k_results.json` + `walk_forward_results.json` |
| **Salida** | carpeta actual | carpeta actual | carpeta actual | `output/optuna_sfm/` | `output/optuna_sfm_v4/` |

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
- **Visualizaciones**: 5 gráficas del estudio (history, parallel coord, importances, slice, distribución)
- **JSON de resultados**: params, estudio, todo exportable
- **Salida organizada**: todo en `output/optuna_sfm/`

## v4 — Pipeline con Optuna 100 trials + Top-K + Walk-Forward

- Todo lo de v3 +
- **100 trials Optuna** en lugar de 30 (convergencia más estable)
- **Semillas globales**: random + numpy + torch + cudnn + seed individual por trial (`SEED + trial.number`)
- **Top-K Evaluation**: evalúa los Top-5 mejores trials y reporta μ, σ, min, max de Sharpe/equity
- **Walk-Forward Validation**: 3 ventanas secuenciales con train creciente (robustez temporal)
- **Métrica de Optuna**: **Sharpe en validación** (antes MSE). Devuelve `−Sharpe`, prune directo si Sharpe < −3
- **Top-K ordena por** Sharpe en validación (mejor correlación con rendimiento real que val_loss)
- **Gráficas**: histograma de Sharpe (con línea en 0), barras de Top-K, comparativa SFM vs benchmark por ventana
- **Salida organizada**: todo en `output/optuna_sfm_v4/`

## Resumen de la evolución

```
v1 (213L) ──→ graf (229L) ──→ v2 (437L) ──→ v3 (671L) ──→ v4 (899L)
  básico       +gráfica      +denoising      +Optuna 30      +Optuna 100
                              +early stop     +pruning        +reproducibilidad
                              +split 70/15/15 +5 gráficas     +Top-K
                              +métricas       +JSON export    +Walk-Forward
```

## Paquetes necesarios por versión

| Paquete | v1 | graf | v2 | v3 | v4 |
|---------|:--:|:----:|:--:|:--:|:--:|
| `torch` (PyTorch) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `numpy` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `pandas` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `scikit-learn` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `qlib` (Microsoft) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `ccxt` | — | — | — | — | — |
| `matplotlib` | — | ✅ | — | ✅ | ✅ |
| `PyWavelets` (`pywt`) | — | — | ✅ | ✅ | ✅ |
| `scipy` (savgol_filter) | — | — | ✅ (fallback) | ✅ (fallback) | ✅ (fallback) |
| `optuna` | — | — | — | ✅ | ✅ |
| `plotly` + `kaleido` | — | — | — | ✅ (gráficas estudio) | ✅ (gráficas estudio) |

### Instalación rápida

```bash
# v1 / graf
pip install torch numpy pandas scikit-learn matplotlib

# v2 — añadir
pip install PyWavelets scipy

# v3 / v4 — añadir
pip install optuna plotly kaleido
```

## Archivos

- `scripts/crypto/qlib_sfm_pipeline.py` — v1
- `scripts/crypto/qlib_sfm_pipeline_grafica.py` — versión con gráfica
- `scripts/crypto/qlib_sfm_pipeline.v2.py` — v2
- `scripts/crypto/qlib_sfm_pipeline.v3.py` — v3
- `scripts/crypto/qlib_sfm_pipeline.v4.py` — v4 (cripto)
- `scripts/crypto/qlib_sfm_pipeline.v5.py` — **v5 (SP500)**

> Para una comparativa detallada entre v4 y v5, ver [comparativa-v4-v5.md](comparativa-v4-v5.md).
