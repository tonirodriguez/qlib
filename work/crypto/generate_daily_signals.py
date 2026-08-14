import ccxt
import torch
import numpy as np
import pandas as pd

def generate_daily_signals(model_multi, scalers, lookback=30):
    """
    Descarga datos en tiempo real, procesa con Wavelet y predice la dirección de mañana.
    """
    exchange = ccxt.binance()
    tickers = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XLM/USDT', 'ADA/USDT']
    cryptos = ['BTC', 'ETH', 'SOL', 'XLM', 'ADA']
    
    live_data = {}
    print("📥 Descargando datos de mercado en tiempo real...")
    
    for t, name in zip(tickers, cryptos):
        # Descargamos lookback + 10 días para que el filtro Wavelet no tenga distorsión de borde
        ohlcv = exchange.fetch_ohlcv(t, timeframe='1d', limit=lookback + 15)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 1. Aplicar el mismo filtro Wavelet usado en el entrenamiento
        clean_series = wavelet_denoising(df['close'].values, wavelet='db4', level=1)
        
        # Tomar los últimos 'lookback' días requeridos por la ventana del SFM
        clean_series_window = clean_series[-lookback:]
        
        # 2. Transformar con su Scaler correspondiente
        scaled_series = scalers[name].transform(clean_series_window.reshape(-1, 1))
        live_data[name] = scaled_series
        
    # Estructurar matriz tridimensional para el modelo: (1, Lookback, 5 activos)
    market_matrix_live = np.hstack([live_data[name] for name in cryptos])
    input_tensor = torch.tensor(market_matrix_live, dtype=torch.float32).unsqueeze(0) # Añadir dimensión de batch
    
    # 3. Predicción del modelo
    model_multi.eval()
    with torch.no_grad():
        pred_scaled = model_multi(input_tensor).numpy()[0] # Forma: (5,)
        
    print("\n================ SEÑALES OPERATIVAS PARA MAÑANA ================")
    for idx, name in enumerate(cryptos):
        # Extraer último precio real y precio predicho des-normalizados
        last_real_price = scalers[name].inverse_transform([[market_matrix_live[-1, idx]]])[0][0]
        predicted_price = scalers[name].inverse_transform([[pred_scaled[idx]]])[0][0]
        
        # Lógica de decisión
        if predicted_price > last_real_price:
            action = "🟢 COMPRA (LONG)"
            cambio = ((predicted_price - last_real_price) / last_real_price) * 100
        else:
            action = "🔴 VENTA (SHORT)"
            cambio = ((predicted_price - last_real_price) / last_real_price) * 100
            
        print(f"Activo: {name:<5} | Último: {last_real_price:.4f} | Predicción: {predicted_price:.4f} ({cambio:+.2f}%) | Orden: {action}")
    print("================================================================")

# Para usarlo de forma diaria simplemente ejecutas:
# generate_daily_signals(modelo_multi, scalers)