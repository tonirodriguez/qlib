# Fragmentación de la Nota SFM Original

La nota original `Implantar Modelo SFM para series temporales Criptomonedas.md` (2.509 líneas) contenía teoría, código PyTorch, conversaciones Q&A, múltiples scripts y experimentos mezclados en un solo documento.

Se fragmentó en **7 documentos independientes**, eliminando el tono conversacional y los residuos de asistente:

| # | Documento | Ubicación | Contenido |
|---|-----------|-----------|-----------|
| 1 | **Fundamentos teóricos** | `obsidian/01 Literature/formacion/qlib/sfm-fundamentos.md` → `wiki/concepts/sfm-fundamentos.md` | Qué es SFM, motivación crypto, perfiles de activos, hiperparámetro K, referencias |
| 2 | **Arquitectura PyTorch** | `obsidian/01 Literature/formacion/qlib/sfm-architectura-pytorch.md` → `wiki/research/sfm-architectura-pytorch.md` | SFMCell, SFMCellRefined, SFMModelRefined, AdamW, archivos relacionados |
| 3 | **Wavelet Denoising** | `obsidian/01 Literature/formacion/qlib/sfm-wavelet-denoising.md` → `wiki/research/sfm-wavelet-denoising.md` | Algoritmo DWT+thresholding+IDWT, umbral Donoho-Johnstone, fallback Savgol, pipeline v2, efecto esperado |
| 4 | **Pipeline con Qlib** | `obsidian/01 Literature/formacion/qlib/sfm-pipeline-qlib.md` → `wiki/workflows/sfm-pipeline-qlib.md` | Extracción, ventanas deslizantes, split 70/15/15, normalización, early stopping, reentreno, clase Qlib Model |
| 5 | **Evaluación y Backtesting** | `obsidian/01 Literature/formacion/qlib/sfm-backtesting.md` → `wiki/experiments/sfm-backtesting.md` | Top-1, benchmark hold, curva de equity, precisión direccional, Sharpe, MAPE, SL/TP, backtesting Qlib nativo, interpretación |
| 6 | **Datos y conversión Qlib** | `obsidian/01 Literature/formacion/qlib/sfm-datos-crypto.md` → `wiki/docs/sfm-datos-crypto.md` | ccxt download, CSV→Qlib, dump_bin, estructura directorio, calendar/instruments, DataHandler |
| 7 | **Señal diaria y producción** | `obsidian/01 Literature/formacion/qlib/sfm-senal-diaria.md` → `wiki/workflows/sfm-senal-diaria.md` | Save/load, señal live ccxt, pipeline cron, flujo completo, archivos de modelo |

## Scripts relacionados

- `scripts/sync_obsidian_to_wiki.sh` — Actualizado con las líneas `cp` para cada documento
- `scripts/wiki-index-template.md` — Actualizado con sección SFM en el índice

## Nota original

La nota original de 2.509 líneas se conserva intacta en:
- `obsidian/01 Literature/formacion/qlib/Implantar Modelo SFM para series temporales Criptomonedas.md`
- `wiki/formacion/qlib/Implantar Modelo SFM para series temporales Criptomonedas.md`
