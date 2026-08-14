# SFM — Señal Diaria y Operativa en Producción

## Guardado Persistente del Modelo

```python
def save_trading_system(modelo_multi, modelos_individuales, scalers, path_prefix="sfm_"):
    torch.save(modelo_multi.state_dict(), f"{path_prefix}multivariable.pth")
    dict_pesos = {name: mod.state_dict() for name, mod in modelos_individuales.items()}
    torch.save(dict_pesos, f"{path_prefix}univariables.pth")
    with open(f"{path_prefix}scalers.pkl", "wb") as f:
        pickle.dump(scalers, f)
```

## Carga en Producción

```python
def load_trading_system(hidden_dim=64, freq_components=10, path_prefix="sfm_"):
    with open(f"{path_prefix}scalers.pkl", "rb") as f:
        scalers = pickle.load(f)

    modelo_multi = SFMModelRefined(input_dim=5, hidden_dim=hidden_dim,
                                    freq_components=freq_components, output_dim=5)
    modelo_multi.load_state_dict(torch.load(f"{path_prefix}multivariable.pth"))
    modelo_multi.eval()

    return modelo_multi, scalers
```

## Generación de Señal Diaria

```python
def generate_daily_signal(model_multi, scalers, lookback=30):
    exchange = ccxt.binance()
    tickers = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XLM/USDT', 'ADA/USDT']
    cryptos = ['BTC', 'ETH', 'SOL', 'XLM', 'ADA']

    live_data = {}
    for t, name in zip(tickers, cryptos):
        ohlcv = exchange.fetch_ohlcv(t, timeframe='1d', limit=lookback + 15)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        clean = wavelet_denoise_series(df['close'].values, wavelet='db4', level=1)
        clean_window = clean[-lookback:]
        scaled = scalers[name].transform(clean_window.reshape(-1, 1))
        live_data[name] = scaled

    matrix = np.hstack([live_data[n] for n in cryptos])
    input_tensor = torch.tensor(matrix, dtype=torch.float32).unsqueeze(0)

    model_multi.eval()
    with torch.no_grad():
        pred_scaled = model_multi(input_tensor).numpy()[0]

    for idx, name in enumerate(cryptos):
        last_price = scalers[name].inverse_transform([[matrix[-1, idx]]])[0][0]
        pred_price = scalers[name].inverse_transform([[pred_scaled[idx]]])[0][0]
        cambio = ((pred_price - last_price) / last_price) * 100
        accion = "COMPRA (LONG)" if pred_price > last_price else "VENTA (SHORT)"
        print(f"{name}: {last_price:.2f} → {pred_price:.2f} ({cambio:+.2f}%) → {accion}")
```

## Pipeline de Producción (cron diario)

```python
# cron_signals.py
if __name__ == "__main__":
    model, scalers = load_trading_system(HIDDEN_DIM, FREQ_COMPONENTS)
    generate_daily_signal(model, scalers, LOOKBACK)
```

## Flujo completo

```
[Datos Históricos] → [Wavelet Denoising] → [MinMaxScaler] →
[Modelo SFM (AdamW)] → [Backtesting SL/TP] → [Script CCXT Live]
```

## Archivos relacionados

- `scripts/crypto/use_crypto.py`
- `scripts/crypto/generate_daily_signals.py`
- `scripts/crypto/qlib_sfm_pipeline.v2.py`
- `scripts/crypto/sfm_multivariable_qlib.pth`
- `scripts/crypto/sfm_multivariable_qlib_v2.pth`
- `scripts/crypto/sfm_scalers_qlib.pkl`
