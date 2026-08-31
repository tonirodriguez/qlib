# Instrucciones de Ejecucion — SFM v6 con Todo el Historico

Pipeline SFM (Stochastic Factor Model) que entrena sobre criptomonedas usando
todo el historico disponible de cada una, respetando el maximo rango individual
(sin truncar al minimo comun denominador).

---

## Requisitos

- Entorno Python con: `qlib`, `torch`, `optuna`, `pandas`, `numpy`, `matplotlib`, `scikit-learn`, `ccxt`
- Conexion a Internet para la descarga de datos desde Binance
- GPU recomendada para 100 trials (CPU funciona pero es mas lento)

---

## Paso a paso (desde cero)

### 0. Ir al directorio del proyecto

```bash
cd /mnt/c/Users/trodriguez/src/qlib
```

Todos los comandos asumen que estas en WSL con el entorno conda `qlib`.

### 1. Descargar todo el historico de criptomonedas

Tienes dos fuentes disponibles:

#### Opcion A: Binance (via ccxt) — datos desde el listing del par

```bash
conda run -n qlib python work/crypto/download_crypto.py
```

| Moneda | Datos desde |
|--------|:-----------:|
| BTC, ETH | 2017-08-17 |
| LTC | 2017-12-13 |
| ADA | 2018-04-17 |
| XRP | 2018-05-04 |
| XLM | 2018-05-31 |
| LINK | 2019-01-16 |
| DOGE | 2019-07-05 |
| SOL | 2020-08-11 |

#### Opcion B: CoinGecko — datos desde el genesis de cada moneda (RECOMENDADA)

```bash
conda run -n qlib python work/crypto/download_crypto_coingecko.py
```

| Moneda | Datos desde (aprox) |
|--------|:-------------------:|
| BTC | ~2010 |
| LTC | ~2013 |
| XRP | ~2013 |
| XLM | ~2014 |
| ETH | ~2015 |
| ADA | ~2017 |
| LINK | ~2017 |
| DOGE | ~2019 (dato real mas antiguo disponible) |
| SOL | ~2020 |

La descarga itera en bloques de 365 dias hacia atras respetando el rate-limit
de la API publica (~2.5s entre llamadas). El volumen se marca como 0 porque
CoinGecko OHLC no incluye volumen en ese endpoint.

Los CSV se guardan en directorios separados segun la fuente:
- Binance: `scripts/crypto/csv_data/crypto/ohlcv/`
- CoinGecko: `scripts/crypto/csv_data/crypto_coingecko/ohlcv/`

Si quieres monedas distintas, usa la variable de entorno:
```bash
CRYPTO_INSTRUMENTS="BTC,ETH,SOL,ADA" conda run -n qlib python work/crypto/download_crypto_coingecko.py
```

### 2. Convertir los datos a formato Qlib

**Si usaste Binance:**
```bash
conda run -n qlib python work/crypto/convert_crypto_qlib.py
```

**Si usaste CoinGecko:**
```bash
CRYPTO_OHLCV_DIR="scripts/crypto/csv_data/crypto_coingecko/ohlcv" \
CRYPTO_INPUT_CSV="scripts/crypto/csv_data/crypto_coingecko/crypto_portfolio_daily.csv" \
conda run -n qlib python work/crypto/convert_crypto_qlib.py
```

En ambos casos se genera el provider Qlib en `data/qlib/`.

### 3. Verificar que los datos se cargan correctamente

```bash
conda run -n qlib python -c "
import qlib; from qlib.config import REG_US; from qlib.data import D
qlib.init(provider_uri='data/qlib', region=REG_US)
for c in ['btc','eth','sol','ada','xrp']:
    df = D.features([c], ['\$close'], start_time='2010-01-01', end_time='2026-12-31')
    dates = df.index.get_level_values('datetime')
    print(f'{c}: {len(df)} filas, {dates.min().date()} -> {dates.max().date()}')
"
```

Con CoinGecko deberias ver datos mucho mas antiguos (BTC ~2010, ETH ~2015, etc.)

### 3. Verificar que los datos se cargan correctamente

```bash
conda run -n qlib python -c "
import qlib; from qlib.config import REG_US; from qlib.data import D
qlib.init(provider_uri='data/qlib', region=REG_US)
for c in ['btc','eth','sol','ada','xrp']:
    df = D.features([c], ['\$close'], start_time='2017-01-01', end_time='2026-12-31')
    dates = df.index.get_level_values('datetime')
    print(f'{c}: {len(df)} filas, {dates.min().date()} -> {dates.max().date()}')
"
```

Debe mostrar el maximo historico de cada moneda (BTC ~3300 filas, SOL ~2200 filas, etc.)

### 4. Ejecutar el pipeline v6

**Smoke test rapido (10 trials, 20 epochs) para verificar que todo funciona:**

```bash
cd /mnt/c/Users/trodriguez/src/qlib
CRYPTO_OPTUNA_TRIALS=10 CRYPTO_FINAL_EPOCHS=20 conda run -n qlib python work/crypto/qlib_sfm_pipeline.v6.py
```

**Ejecucion completa (recomendada, ~100 trials):**

```bash
conda run -n qlib python work/crypto/qlib_sfm_pipeline.v6.py
```

**Ejecucion completa con walk-forward validation:**

```bash
DO_WALK_FORWARD=True conda run -n qlib python work/crypto/qlib_sfm_pipeline.v6.py
```

### 5. Outputs

Todo se guarda en `work/crypto/output/sfm_v6_full_history/`:

| Archivo | Contenido |
|---|---|
| `study_results.json` | Mejores hiperparametros y metrica de validacion |
| `top_k_results.json` | Resultados de los K mejores modelos en test |
| `top_k_results.png` | Grafica de Sharpe y Equity de los K mejores |
| `optuna_distribution.png` | Distribucion de Sharpe en validacion |
| `sfm_top1.pth` a `sfm_top5.pth` | Modelos entrenados (checkpoints) |
| `walk_forward_results.json` | Resultados walk-forward (si activado) |
| `walk_forward.png` / `walk_forward_equity.png` | Graficas walk-forward (si activado) |

---

## Flujo completo (comando unico)

Si quieres ejecutar todo de una vez (descarga, conversion y pipeline):

```bash
cd /mnt/c/Users/trodriguez/src/qlib
conda run -n qlib python work/crypto/download_crypto.py && \
conda run -n qlib python work/crypto/convert_crypto_qlib.py && \
conda run -n qlib python work/crypto/qlib_sfm_pipeline.v6.py
```

---

## Personalizacion via variables de entorno

| Variable | Default | Descripcion |
|---|---|---|
| `CRYPTO_INSTRUMENTS` | BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC | Monedas a incluir |
| `CRYPTO_START_DATE` | 2015-01-01 | Fecha inicio (usa esta aunque cada moneda tenga su maximo) |
| `CRYPTO_END_DATE` | hoy | Fecha fin de datos |
| `CRYPTO_OPTUNA_TRIALS` | 100 | Numero de trials de Optuna |
| `CRYPTO_FINAL_EPOCHS` | 100 | Epocas para reentreno final de los top-k |
| `CRYPTO_TRIAL_EPOCHS` | 60 | Epocas por trial durante la busqueda Optuna |
| `CRYPTO_TOP_K` | 5 | Modelos top a reentrenar y evaluar en test |
| `CRYPTO_QLIB_OUTPUT_DIR` | data/qlib | Ruta del provider Qlib |
| `CRYPTO_MODEL_OUTPUT_DIR` | work/crypto/output/sfm_v6_full_history | Directorio de salida de resultados |
| `CRYPTO_DOWNLOAD_SINCE_DAYS` | 10000 | Dias de historia a descargar (solo Binance, 10000 ~= 27 anos) |
| `CRYPTO_DOWNLOAD_DELAY` | 2.5 | Delay entre llamadas API en segundos (CoinGecko) |
| `DO_WALK_FORWARD` | False | Activar walk-forward validation (3 ventanas) |

---

## Notas importantes

1. **Cada moneda conserva su maximo historico**: el pipeline lee instrumento por instrumento,
   no todas juntas. Esto evita que SOL (2020) trunque a BTC (2017). Las monedas mas jovenes
   tienen NaN hasta su fecha de listing.

2. **Denoising desactivado**: el wavelet denoising global esta OFF porque filtra informacion
   futura hacia el pasado (leak temporal conocido de las versiones v2-v4).

3. **Clipping y scaling causales**: los bounds de clipping y el scaler se ajustan SOLO con
   los datos de entrenamiento de cada ventana, nunca con validacion o test.

4. **Lookback ampliado**: se optimiza entre 20 y 90 dias (frente a 15-50 de v4) para capturar
   dependencias temporales mas largas.

5. **El provider Qlib esta en `data/qlib/`**, no en `data/qlib_crypto/`. Asegurate de que
   `CRYPTO_QLIB_OUTPUT_DIR` apunte a `data/qlib` si es necesario.