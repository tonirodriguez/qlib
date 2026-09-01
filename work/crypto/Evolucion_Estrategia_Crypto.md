# Evolucion de las Estrategias SFM Crypto

> **Documento:** Evolucion incremental de los pipelines SFM (Stochastic Factor Model)
> **Proposito:** Entender que cambio de una version a la siguiente y por que

---

## Indice

1. [v1 — Prototipo Inicial](#v1--prototipo-inicial)
2. [v2 — Wavelet Denoising + Split Temporal](#v2--wavelet-denoising--split-temporal)
3. [v3 — Optuna + Hiperparametros](#v3--optuna--hiperparametros)
4. [v4 — Walk-Forward + Top-K](#v4--walk-forward--top-k)
5. [v5 — SP500 (derivacion, no crypto)](#v5--sp500-derivacion-no-crypto)
6. [v6 — Split 60/20/20 + Lookback Ampliado + Maximo Historico](#v6--split-602020--lookback-ampliado--maximo-historico)
7. [v7 — Label 5d + Features Extendidos](#v7--label-5d--features-extendidos)

---

## v1 — Prototipo Inicial

**Archivo:** `qlib_sfm_pipeline.py`

### Descripcion
Primera implementacion del SFM (State-Frequency Memory). Usa una celda LSTM
modificada con frecuencias adaptativas (SFMCellRefined) para modelar series
temporales financieras.

### Caracteristicas
- **Modelo:** SFMCellRefined con `W_omega` para frecuencias adaptativas
- **Datos:** Carga desde Qlib usando `D.features()` con todas las criptos juntas
- **Features:** Solo `$close` (precio de cierre)
- **Label:** Retorno a 1 dia (`pct_change().shift(-1)`)
- **Split:** Manual 70/15/15
- **Optimizacion:** Ninguna (parametros fijos)
- **Denoising:** No
- **Visualizacion:** Grafica de equity final
- **Output:** Solo consola, sin persistencia

### Limitaciones
- Sin busqueda de hiperparametros
- Sin validacion walk-forward
- Sin top-k (un solo modelo)
- Sin persistencia de resultados
- Sin early stopping sistematico

---

## v2 — Wavelet Denoising + Split Temporal

**Archivo:** `qlib_sfm_pipeline.v2.py`

### Que cambia respecto a v1

| Aspecto | v1 | v2 |
|---|---|---|
| Preprocesado | Ninguno | **Wavelet denoising** (pywt) |
| Split | Manual 70/15/15 | **Split cronologico** 70/15/15 con funcion |
| Early stopping | No | **Si**, basado en validation loss |
| Reentreno final | No | **Si**, sobre train+val |
| Senal de trading | No | **Si**, prediccion direccional |
| Seed | No | **Si**, semilla fija 42 |
| Device | CPU | **Auto-detection** (cuda/cpu) |

### Descripcion
Anade preprocesado con Transformada Wavelet (db4) para eliminar ruido diario
de las series de precios. Implementa split cronologico, early stopping por
validation loss, y reentreno final sobre train+val antes de evaluar en test.

### Problema detectado
El denoising wavelet se aplica **sobre toda la serie** antes del split,
lo que introduce un leak temporal: informacion futura (del test) se usa
para filtrar el pasado (train). Esto invalida las metricas como evidencia
out-of-sample.

---

## v3 — Optuna + Hiperparametros

**Archivo:** `qlib_sfm_pipeline.v3.py`

### Que cambia respecto a v2

| Aspecto | v2 | v3 |
|---|---|---|
| Optimizacion | Parametros fijos | **Optuna** (TPE + MedianPruner) |
| Hiperparametros | hidden_dim, K fijos | **hidden_dim, K, lr, dropout, lookback, batch_size** |
| Objetivo | Validation MSE | **-Sharpe** (maximizar Sharpe en val) |
| Pruning | No | **Si**, MedianPruner |
| Importancia | No | **Si**, analisis de importancia |
| Output | Consola | **JSON + graficas + checkpoints** |
| Trials | 1 | **100** (configurable) |

### Descripcion
Introduce busqueda automatica de hiperparametros con Optuna. El objetivo
pasa de minimizar MSE a **maximizar el Sharpe en validacion** (via -Sharpe).
Anade pruning para descartar trials malos rapidamente, almacenamiento de
resultados en JSON, y visualizacion de la distribucion de Sharpe.

### Mejora clave
El cambio de objetivo (MSE -> Sharpe) alinea la optimizacion con la metrica
que realmente importa en trading: rentabilidad ajustada por riesgo, no
precision de prediccion.

---

## v4 — Walk-Forward + Top-K

**Archivo:** `qlib_sfm_pipeline.v4.py`

### Que cambia respecto a v3

| Aspecto | v3 | v4 |
|---|---|---|
| Validacion | Split fijo | **Walk-Forward** (3 ventanas) |
| Evaluacion | Un solo modelo | **Top-K** (5 mejores modelos) |
| Metricas | Sharpe, Equity | **Sharpe, Equity, Sortino, Calmar, VaR, CVaR, turnover** |
| Costes | No | **Si**, escenarios de costes |
| Semillas | Global | **Por trial** (reproducibilidad) |
| N_TRIALS | 100 | **100** (configurable) |
| DO_WALK_FORWARD | No | **False** (configurable, requiere nested tuning) |

### Descripcion
Anade walk-forward validation (3 ventanas de test secuenciales) para validar
la robustez temporal del modelo. Implementa evaluacion Top-K: entrena y evalua
los K mejores trials de Optuna, no solo el #1, para evitar p-hacking.
Incluye metricas adicionales (Sortino, Calmar, VaR, CVaR, turnover) y
escenarios de costes de transaccion.

### Leak conocido
A pesar de las mejoras, el wavelet denoising global sigue aplicandose antes
del split, manteniendo el leak temporal de v2. En la configuracion del
pipeline principal, `DENOISE = False` por defecto para evitarlo, pero el
codigo sigue soportando denoising global si se activa.

---

## v5 — SP500 (derivacion, no crypto)

**Archivo:** `qlib_sfm_pipeline.v5.py`

### Que cambia respecto a v4

| Aspecto | v4 | v5 |
|---|---|---|
| Universo | Crypto (BTC, ETH, ...) | **SP500 stocks** |
| Estrategia | Top-1 long | **Top-1 long/short** |
| Output dir | output/optuna_sfm_v4/ | **output/optuna_sfm_v5/** |
| Baseline | Media simple | **Media simple** (igual) |

### Descripcion
Es una **derivacion** del v4 adaptada para acciones del SP500 en lugar de
criptomonedas. No es una mejora del pipeline crypto, sino un experimento
paralelo. Comparte el mismo leak temporal (denoising global antes del split)
y la misma arquitectura base.

### Nota importante
Este pipeline esta en el directorio `work/crypto/` pero no es un modelo
crypto. Es un experimento sobre SP500 que se ubico aqui por razones
historicas. Sus outputs estan en `output/optuna_sfm_v5/`.

---

## v6 — Split 60/20/20 + Lookback Ampliado + Maximo Historico

**Archivo:** `qlib_sfm_pipeline.v6.py`

### Que cambia respecto a v4 (salta v5 por ser derivacion no crypto)

| Aspecto | v4 | v6 |
|---|---|---|
| Split | 70/15/15 | **60/20/20** |
| Lookback | 15-50 dias | **20-90 dias** |
| Denoising | OFF por defecto | **OFF por defecto** (igual) |
| Clipping | causal | **causal** (igual) |
| Provider Qlib | data/qlib | **data/qlib** (igual) |
| Start date | 2018-01-01 | **2015-01-01** |
| Lectura datos | Todas juntas | **Cada moneda por separado** |
| W_omega | freq_components | **hidden_dim** (correccion bug) |
| Descarga | since_days=1100 | **since_days=10000** (maximo historico) |

### Descripcion
Primera version que **respeta el maximo historico individual** de cada moneda.
En lugar de cargar todas las criptos juntas (lo que hace que Qlib alinee al
rango comun), lee instrumento por instrumento y combina manteniendo NaN donde
una moneda aun no existia.

El split pasa a 60/20/20 para absorber mas anos de historia sin saturar el
test set. El lookback se amplia a 20-90 dias para capturar dependencias
temporales mas largas.

### Correccion de bug
`W_omega` cambia de `nn.Parameter(torch.randn(hidden_dim, freq_components))`
a `nn.Parameter(torch.randn(hidden_dim, hidden_dim))` porque el calculo de
`freq_adapt` requiere que los tamanos de `c` y `freq_adapt` coincidan.

### Descarga de datos
Se crea `download_crypto_coingecko.py` para obtener datos desde el genesis
de cada moneda (CoinGecko), complementando a `download_crypto.py` (Binance).

---

## v7 — Label 5d + Features Extendidos

**Archivo:** `qlib_sfm_pipeline.v7.py`

### Que cambia respecto a v6

| Aspecto | v6 | v7 |
|---|---|---|
| Label | Retorno a 1 dia | **Retorno a 5 dias** |
| Features | close, pct, ratio_5d (3) | **close, pct, ratio_5d, vol_20d, ma20_ratio, rango (6)** |
| Total features (9 monedas) | 27 | **54** |
| Output dir | sfm_v6_full_history | **sfm_v7_label5d** |
| Variable nueva | - | **CRYPTO_FWD_DAYS** (default 5) |

### Descripcion
Incorporaba tres mejoras para intentar capturar mejor senal:

1. **Label a 5 dias**: El retorno a 1 dia es muy ruidoso en crypto. Con 5 dias
   se suaviza el ruido diario y se captura mejor la tendencia de corto plazo.

2. **Features adicionales** (6 por moneda en lugar de 3):
   - `close` — precio de cierre
   - `pct` — retorno diario
   - `ratio_5d` — media movil 5d / precio
   - `vol_20d` — volatilidad 20d (desviacion estandar de retornos)
   - `ma20_ratio` — media movil 20d / precio
   - `rango` — valor absoluto del retorno diario (proxy del rango)

3. **Configuracion flexible**: Nueva variable `CRYPTO_FWD_DAYS` para cambiar
   la label sin modificar el codigo. Tambien es facil reducir el numero de
   monedas via `CRYPTO_INSTRUMENTS`.

### Objetivo
Con mas features y una label menos ruidosa, se espera que el modelo SFM
encuentre patrones predictivos mas robustos y generalice mejor en el
periodo de test.

---

## Resumen visual de la evolucion

```
v1  Prototipo inicial SFM
 |   [Sin optimizacion, sin denoising, sin persistencia]
v2  + Wavelet denoising + split temporal + early stopping
 |   [PERO: leak temporal por denoising global]
v3  + Optuna (hiperparametros) + objetivo Sharpe + pruning
 |   [Mejora: alineacion con metrica de trading]
v4  + Walk-Forward + Top-K + metricas avanzadas + costes
 |   [Mejora: robustez y evaluacion multiple]
v5  (Derivacion a SP500, no es mejora de crypto)
 |
v6  + Split 60/20/20 + lookback 20-90 + maximo historico
 |   + Lectura individual por moneda + bugfix W_omega
 |   [Mejora: mas datos, mas historia, menos overfitting]
v7  + Label 5d + features extendidos (6 por moneda)
     [Mejora: menos ruido en label, mas senal en features]
```

## Tabla comparativa

| Version | Label | Features/moneda | Split | Lookback | Optuna | Walk-Forward | Top-K | Denoising | Max historico |
|:-------:|:-----:|:---------------:|:-----:|:--------:|:------:|:-------------:|:-----:|:----------:|:-------------:|
| v1 | 1d | 1 | 70/15/15 | fijo | No | No | No | No | No |
| v2 | 1d | 1 | 70/15/15 | fijo | No | No | No | Si (con leak) | No |
| v3 | 1d | 1 | 70/15/15 | variable | Si | No | No | Si (con leak) | No |
| v4 | 1d | 1 | 70/15/15 | 15-50 | Si | Si (3 vent) | Si (5) | OFF | No |
| v5 | 1d | 1 | 70/15/15 | 15-50 | Si | Si (3 vent) | Si (5) | OFF | No (SP500) |
| v6 | 1d | 3 | **60/20/20** | **20-90** | Si | Si (3 vent) | Si (5) | OFF | **Si** |
| v7 | **5d** | **6** | 60/20/20 | 20-90 | Si | Si (3 vent) | Si (5) | OFF | Si |

## Archivos asociados por version

| Version | Pipeline | Descarga datos | Datos desde |
|:-------:|----------|----------------|:-----------:|
| v1 | `qlib_sfm_pipeline.py` | - | Binance (~2017) |
| v2 | `qlib_sfm_pipeline.v2.py` | - | Binance (~2017) |
| v3 | `qlib_sfm_pipeline.v3.py` | - | Binance (~2017) |
| v4 | `qlib_sfm_pipeline.v4.py` | `download_crypto.py` | Binance (~2017) |
| v5 | `qlib_sfm_pipeline.v5.py` | - | SP500 (varios) |
| v6 | `qlib_sfm_pipeline.v6.py` | `download_crypto.py` + `download_crypto_coingecko.py` | CoinGecko (~2010) |
| v7 | `qlib_sfm_pipeline.v7.py` | `download_crypto.py` + `download_crypto_coingecko.py` | CoinGecko (~2010) |