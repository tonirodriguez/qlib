# SFM — Datos: Descarga y Conversión a Formato Qlib

## Descarga desde Binance (ccxt)

```python
import ccxt, pandas as pd, time

def download_historical(symbol, timeframe='1d', since_days=1100):
    exchange = ccxt.binance({'enableRateLimit': True})
    since = exchange.milliseconds() - since_days * 24 * 60 * 60 * 1000
    all_ohlcv = []
    current_since = since

    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        last_ts = ohlcv[-1][0]
        if current_since == last_ts:
            break
        current_since = last_ts + 1
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)
    return df
```

## Conversión a CSV formato Qlib

```python
def convert_to_qlib_csv(input_csv, output_csv):
    df = pd.read_csv(input_csv, parse_dates=True)
    df_melted = df.melt(id_vars=['date'], var_name='symbol', value_name='close')
    df_melted['open'] = df_melted['close']
    df_melted['high'] = df_melted['close']
    df_melted['low'] = df_melted['close']
    df_melted['volume'] = 10000.0
    df_melted['factor'] = 1.0
    df_melted = df_melted[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume', 'factor']]
    df_melted.to_csv(output_csv, index=False)
```

## Compilación a binarios Qlib

### Opción A: dump_bin.py

```bash
python path/to/qlib/scripts/dump_bin.py dump_all \
    --csv_path ./csv_data/crypto \
    --qlib_dir ./qlib_data/crypto_bin \
    --date_field_name date \
    --include_fields open,high,low,close,volume,factor
```

### Opción B: Desde Python

```python
from qlib.utils.data import DumpDataAll

DumpDataAll(
    csv_path="./csv_data/crypto",
    qlib_dir="./qlib_data/crypto_bin",
    date_field_name="date",
    include_fields="open,high,low,close,volume,factor"
).dump()
```

## Estructura del directorio Qlib

```
qlib_data/crypto_bin/
├── calendars/
│   └── day.txt
├── instruments/
│   └── all.txt
└── features/
    ├── btc/
    │   ├── close.bin
    │   └── ...
    ├── eth/
    └── ...
```

### Generación manual del calendario

```python
fechas = sorted(pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d').unique())
with open("./qlib_data/crypto_bin/calendars/day.txt", "w") as f:
    for fecha in fechas:
        f.write(f"{fecha}\n")
```

### Generación manual de instruments

```python
with open("./qlib_data/crypto_bin/instruments/all.txt", "w") as f:
    for crypto in ['btc', 'eth', 'sol', 'xlm', 'ada']:
        f.write(f"{crypto}\t{first_date}\t{last_date}\n")
```

## Acceso a datos desde Qlib

```python
import qlib
from qlib.config import REG_US
from qlib.data import D

qlib.init(provider_uri='./qlib_data/crypto_bin', region=REG_US)

instruments = D.instruments(market='all')
df = D.features(instruments, ['$close', '$volume'],
                start_time='2023-01-01', end_time='2026-06-01')
```

## DataHandler de Qlib

```python
def get_crypto_handler():
    handler_config = {
        "start_time": "2023-01-01",
        "end_time": "2026-06-01",
        "instruments": "all",
        "data_loader": {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": (
                        ["$close", "Ref($close, 1)/$close - 1", "Mean($close, 5)/$close"],
                        ["close", "return_1d", "mean_ratio_5"]
                    ),
                    "label": (
                        ["Ref($close, -1)/$close - 1"],
                        ["label_next_return"]
                    )
                }
            }
        },
        "learn_processors": [],
    }
    return DataHandlerLP(**handler_config)
```

## Archivos relacionados

- `scripts/crypto/download_crypto.py`
- `scripts/crypto/convert_crypto_qlib.py`
- `scripts/crypto/generate_daily_signals.py`
