# 📥 Datos Crypto — Carga inicial (CryptoCompare) + Operativa diaria (Binance)

> **Proyecto:** frente crypto de Qlib.
> **Objetivo:** histórico completo desde el **génesis** (CryptoCompare) en una carga
> inicial, y a partir de ahí **actualización diaria incremental** (Binance) sin
> re-descargar el histórico.

---

## 🧭 Flujo de trabajo (resumen)

```
[UNA VEZ] Carga inicial              ──►  [DIARIO] Actualización incremental
CryptoCompare (histórico génesis)         Binance (solo días nuevos)
        │                                        │
        ▼                                        ▼
   CSVs por coin (OHLCV, USD)          CSVs por coin (se agregan días nuevos)
        │                                        │
        └──────────────►  convert_crypto_qlib.py  ──►  dataset Qlib (data/qlib_cryptocompare)
```

- **Carga inicial:** `download_crypto_cryptocompare.py` (histórico completo, una vez o al regenerar).
- **Operativa diaria:** `update_crypto_daily_binance.py` (incremental, solo lo nuevo).
- **Convertir a Qlib:** `convert_crypto_qlib.py` (genera el dataset que usa el pipeline SFM).

---

## 💵 Moneda (GARANTIZADO en dólares)

| Fuente | Moneda cotización | Nota |
|---|---|---|
| **CryptoCompare** | **USD literal** (`tsym=USD`) | Cotización fija en el endpoint. |
| **Binance** | **USDT** (stablecoin anclada 1:1 al USD) | Equivalente práctico a dólar; el par USDT es el más líquido. |

**Protección automática:** ambos scripts tienen una **guarda de plausibilidad en USD**
por moneda (`_assert_usd_plausible`). Si el último precio de cierre cae por debajo del
umbral esperado para esa coin (ej. BTC < 1000, ETH < 100, SOL < 1), la descarga/escritura
**se aborta** en vez de escribir basura, para que nunca se corrompa el histórico con
una moneda equivocada (otra cotización, stablecoin despegada, satoshis).

> ⚠️ **Nota técnica:** en Binance no existe par `*USD`; si algún día prefirieras un par
> ligeramente distinto (USDC o FDUSD, ambas también 1:1 USD), basta cambiar la
> constante `QUOTE_CURRENCY = "USDT"` por `"USDC"` o `"FDUSD"` en
> `update_crypto_daily_binance.py`.

---

## ✅ Requisitos

- Python del venv Qlib: `$ /opt/data/qlib-venv/bin/python` (o `conda run -n qlib python` en la máquina local).
- `CRYPTOCOMPARE_API_KEY` en `/opt/data/qlib/.env` (¡no se commitea!).
- Acceso a internet (API pública de CryptoCompare con key, Binance sin key).

---

## 🚀 Paso 0 — Preparar (una vez)

```bash
cd /opt/data/qlib
# La key de CryptoCompare debe estar en .env:
cat .env    # debe incluir: CRYPTOCOMPARE_API_KEY=xxx
```

---

## 📅 Operativa diaria

### Actualización incremental (Binance) — lo que corre cada día

```bash
cd /opt/data/qlib
/opt/data/qlib-venv/bin/python work/crypto/update_crypto_daily_binance.py
```

- Descarga **solo los días nuevos** desde Binance (desde la última fecha de cada CSV hasta ayer).
- Reescribe los CSVs + `manifest.json` (con SHA-256, trazabilidad).
- No toca el histórico pasado; solo añade al final.

> Para correr una sola coin (p. ej. una prueba): `CRYPTO_INSTRUMENTS="BTC" <python> ...`

---

## 🔄 Regenerar el histórico completo (CryptoCompare)

Ejecuta **solo** cuando necesites regenerar el dataset desde génesis
(nuevas coins, corrupción, cambio de política de datos, migración):

```bash
cd /opt/data/qlib

# 1) Descarga histórico completo desde génesis (CryptoCompare) — consume rate-limit diario
/opt/data/qlib-venv/bin/python work/crypto/download_crypto_cryptocompare.py

# 2) Actualización diaria (Binance) si hay días nuevos tras lo descargado
/opt/data/qlib-venv/bin/python work/crypto/update_crypto_daily_binance.py

# 3) Convierte los CSVs a formato Qlib (dataset que usa el pipeline SFM v8)
CRYPTO_OHLCV_DIR="scripts/crypto/csv_data/crypto_cryptocompare/ohlcv" \
CRYPTO_OHLCV_FILE_PATTERN="{instrument_lower}.csv" \
CRYPTO_QLIB_OUTPUT_DIR="data/qlib_cryptocompare" \
/opt/data/qlib-venv/bin/python work/crypto/convert_crypto_qlib.py
```

**Salida:** dataset completo en `data/qlib_cryptocompare/` con cada coin desde su génesis real:

| Coin | Génesis (primer precio real) |
|---|---:|
| BTC | 2010-07 |
| LTC | 2013-09 |
| DOGE | 2014-02 |
| XLM | 2014-09 |
| ETH | 2015-08 |
| XRP | 2015-01 |
| ADA | 2017-10 |
| LINK | 2017-09 |
| SOL | 2020-04 |

> ⚠️ **Rate-limit CryptoCompare (plan gratuito):** `100 llamadas/día, 1/seg`.
> La regeneración de las 9 coins consume ~40 llamadas. Si falla a mitad por
> rate-limit, espera al día siguiente o sube el plan. El script ya reintenta y
> espera; no lo repitas entero el mismo día a menos que sea necesario.

---

## 🔍 Verificación

Tras descargar/actualizar, valida que el dataset carga con Qlib:

```bash
cd /opt/data/qlib && /opt/data/qlib-venv/bin/python -c "
import qlib
from qlib.config import REG_US
from qlib.data import D
qlib.init(provider_uri='data/qlib_cryptocompare', region=REG_US, kernels=1)
for c in ['btc','eth','sol','ada']:
    df = D.features([c], ['\$close'], start_time='2009-01-01', end_time='2026-12-31')
    s = df['\$close']; nz = s[s!=0]
    print(c, '|', nz.index[0][1].date(), '->', round(float(nz.iloc[-1]), 2))
"
```

---

## 📁 Scripts / archivos

| Archivo | Rol |
|---|---|
| `work/crypto/download_crypto_cryptocompare.py` | Carga inicial histórico génesis (CryptoCompare) |
| `work/crypto/update_crypto_daily_binance.py` | Actualización diaria incremental (Binance) |
| `work/crypto/convert_crypto_qlib.py` | Convierte CSVs → dataset Qlib |
| `scripts/crypto/csv_data/crypto_cryptocompare/ohlcv/*.csv` | CSVs por coin (OHLCV, USD) — **no se commitean** (`*.csv` ignorado) |
| `data/qlib_cryptocompare/` | Dataset Qlib generado (sí se commitea) |
| `.env` | API key CryptoCompare — **no se commitea** |