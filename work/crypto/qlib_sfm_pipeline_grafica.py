import os
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler

import qlib
from qlib.config import REG_US
from qlib.data import D

# =====================================================================
# 1. ARQUITECTURA DEL MODELO SFM (STATE-FREQUENCY MEMORY) EN PYTORCH
# =====================================================================
class SFMCellRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, dropout_rate=0.2):
        super(SFMCellRefined, self).__init__()
        self.hidden_dim = hidden_dim
        self.K = freq_components
        
        self.W_i = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_f = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_o = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_z = nn.Linear(input_dim + hidden_dim, hidden_dim)
        
        self.W_omega = nn.Parameter(torch.randn(hidden_dim, self.K))
        self.dropout = nn.Dropout(dropout_rate)
        
    def forward(self, x, states):
        h_prev, c_prev, S_prev = states
        combined = torch.cat((x, h_prev), dim=1)
        combined_drop = self.dropout(combined)
        
        i = torch.sigmoid(self.W_i(combined_drop))
        f = torch.sigmoid(self.W_f(combined_drop))
        o = torch.sigmoid(self.W_o(combined_drop))
        z = torch.tanh(self.W_z(combined_drop))
        
        c_t = f * c_prev + i * z
        
        W_w_expanded = self.W_omega.unsqueeze(0).expand(x.size(0), -1, -1)
        S_t = f.unsqueeze(-1) * S_prev + i.unsqueeze(-1) * torch.tanh(W_w_expanded)
        
        h_freq = torch.mean(self.dropout(S_t) * torch.sin(W_w_expanded), dim=-1)
        h_t = o * torch.tanh(c_t + h_freq)
        
        return h_t, (h_t, c_t, S_t)

class SFMModelRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, output_dim, dropout_rate=0.2):
        super(SFMModelRefined, self).__init__()
        self.hidden_dim = hidden_dim
        self.K = freq_components
        self.cell = SFMCellRefined(input_dim, hidden_dim, freq_components, dropout_rate)
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        batch_size, seq_len, _ = x.size()
        h = torch.zeros(batch_size, self.hidden_dim).to(x.device)
        c = torch.zeros(batch_size, self.hidden_dim).to(x.device)
        S = torch.zeros(batch_size, self.hidden_dim, self.K).to(x.device)
        
        for t in range(seq_len):
            h, (h, c, S) = self.cell(x[:, t, :], (h, c, S))
            
        return self.fc(h)

# =====================================================================
# 2. EXTRACCIÓN DIRECTA Y CONSTRUCCIÓN DE CARACTERÍSTICAS (PANDAS/QLIB)
# =====================================================================
def load_and_process_crypto_data(cryptos, start_date, end_date):
    """
    Extrae los datos binarios directamente usando la API robusta D.features
    y calcula las expresiones técnicas calculadas en memoria.
    """
    fields = ['$close']
    # Cargar los datos crudos desde Qlib binario
    df_qlib = D.features(cryptos, fields, start_time=start_date, end_time=end_date)
    df_reset = df_qlib.reset_index()
    
    features_list = []
    # Generar características calculadas en formato matricial limpio
    # 1. Precios de Cierre
    df_close = df_reset.pivot(index='datetime', columns='instrument', values='$close')[cryptos]
    features_list.append(df_close.values)
    
    # 2. Retornos diarios: Cambio porcentual
    df_pct = df_close.pct_change().fillna(0)
    features_list.append(df_pct.values)
    
    # 3. Ratio de Media Móvil de 5 días
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_ratio = (df_mean_5 / df_close).fillna(1.0)
    features_list.append(df_ratio.values)
    
    # Unir todas las características de forma horizontal (Días, Características Totales)
    market_matrix = np.hstack(features_list)
    
    # La etiqueta o target a predecir será el retorno del día de mañana de las criptos
    labels_matrix = df_pct.shift(-1).fillna(0).values
    
    return market_matrix, labels_matrix, df_close, df_pct

def make_sliding_windows(market_matrix, labels_matrix, lookback=30):
    """Estructura las ventanas en tensores 3D para PyTorch"""
    X, y = [], []
    # Dejamos la última muestra fuera porque no tiene etiqueta futura válida debido al shift
    for i in range(len(market_matrix) - lookback - 1):
        X.append(market_matrix[i : (i + lookback), :])
        y.append(labels_matrix[i + lookback, :]) # Target: Retornos del día siguiente
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)

# =====================================================================
# 3. PIPELINE DE OPERACIÓN, ENTRENAMIENTO Y GRAFICACIÓN
# =====================================================================
if __name__ == "__main__":
    # Hiperparámetros
    LOOKBACK = 30
    HIDDEN_DIM = 64
    FREQ_COMPONENTS = 10
    EPOCHS = 20
    LR = 0.001
    # Asegúrate de colocar las criptos en el mismo caso (mayúsculas/minúsculas) de tus carpetas binarias
    CRYPTOS = ['btc', 'eth', 'sol', 'xlm', 'ada'] 
    
    print("📁 Inicializando repositorio de datos binarios Qlib...")
    qlib.init(provider_uri='/mnt/c/Users/trodriguez/src/agent_qlib/data/qlib', region=REG_US)
    
    print("📥 Cargando matrices desde el motor analítico...")
    # Extraemos todo el rango de datos disponibles
    market_data, labels_data, df_prices, df_returns = load_and_process_crypto_data(CRYPTOS, "2023-01-01", "2026-06-01")
    
    # Corte temporal cronológico estricto para simulación (75% Train, 25% Test)
    split_idx = int(len(market_data) * 0.50)
    
    market_train, market_test = market_data[:split_idx], market_data[split_idx:]
    labels_train, labels_test = labels_data[:split_idx], labels_data[split_idx:]
    
    # Escalar datos usando únicamente los parámetros del conjunto de Entrenamiento (Evita Data Leakage)
    scaler = MinMaxScaler(feature_range=(-1, 1))
    market_train_scaled = scaler.fit_transform(market_train)
    market_test_scaled = scaler.transform(market_test) # El test solo se transforma
    
    # Construcción de tensores de entrenamiento y prueba
    X_train, y_train = make_sliding_windows(market_train_scaled, labels_train, lookback=LOOKBACK)
    X_test, y_test = make_sliding_windows(market_test_scaled, labels_test, lookback=LOOKBACK)
    
    print(f"🔹 Dimensiones de Entrenamiento X: {X_train.shape} | Y: {y_train.shape}")
    print(f"🔹 Dimensiones de Prueba (Test)  X: {X_test.shape} | Y: {y_test.shape}")
    
    # Configuración de dimensiones de la Red Neuronal
    input_dimension = market_data.shape[1]  # 5 criptos * 3 features = 15
    output_dimension = len(CRYPTOS)         # Predice el retorno de los 5 activos a la vez
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SFMModelRefined(input_dimension, HIDDEN_DIM, FREQ_COMPONENTS, output_dimension).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    criterion = nn.MSELoss()
    
    # --- BUCLE DE ENTRENAMIENTO ---
    print(f"🏋️ Entrenando la celda SFM en {device}...")
    model.train()
    for epoch in range(EPOCHS):
        optimizer.zero_grad()
        inputs, targets = X_train.to(device), y_train.to(device)
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        print(f"Época [{epoch+1:02d}/{EPOCHS}] ── Pérdida del Modelo: {loss.item():.6f}")
        
    # --- EVALUACIÓN Y PREDICCIÓN EN EL CONJUNTO DE TEST ---
    print("\n🔮 Generando predicciones fuera de muestra (Out-of-Sample)...")
    model.eval()
    with torch.no_grad():
        test_inputs = X_test.to(device)
        # Predicciones obtenidas en forma de retornos esperados para el día siguiente
        predicted_returns = model(test_inputs).cpu().numpy() 
        
    # --- MOTOR DE BACKTESTING SIMPLIFICADO (ESTRATEGIA PORTAFOLIO TOP-1) ---
    # Tomamos el índice de retornos reales de la sección correspondiente al test
    real_test_returns = df_returns.iloc[split_idx + LOOKBACK + 1 : split_idx + LOOKBACK + 1 + len(predicted_returns)].values
    
    # Definición de estrategia: Cada día compramos únicamente el activo con la predicción de retorno más alta
    best_asset_idx = np.argmax(predicted_returns, axis=1)
    
    # Extraer los retornos que obtuvo nuestra estrategia día a día
    strategy_daily_returns = np.zeros(len(best_asset_idx))
    for t in range(len(best_asset_idx)):
        asset_elegido = best_asset_idx[t]
        strategy_daily_returns[t] = real_test_returns[t, asset_elegido]
        
    # Descontar comisiones de intercambio (0.1% por rebalanceo diario estimado)
    strategy_daily_returns -= 0.001 
    
    # Calcular el retorno promedio del mercado como Benchmark (Estrategia Equitativa Hold)
    market_benchmark_returns = np.mean(real_test_returns, axis=1)
    
    # Calcular crecimiento acumulado de capital (Base $1)
    equity_strategy = np.cumprod(1 + strategy_daily_returns)
    equity_benchmark = np.cumprod(1 + market_benchmark_returns)
    
    # --- CONTROL DE VISUALIZACIÓN GRÁFICA ---
    print("📊 Generando gráfica de rendimiento financiero...")
    fechas_test = df_prices.index[split_idx + LOOKBACK + 1 : split_idx + LOOKBACK + 1 + len(predicted_returns)]
    
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(14, 7))
    
    # Dibujar las líneas de rendimiento del dinero
    plt.plot(fechas_test, equity_strategy, label='Estrategia Portafolio SFM (Top-1 Activo)', color='#1f77b4', linewidth=2.5)


plt.plot(fechas_test, equity_benchmark, label='Benchmark Mercado General (Hold Promedio)', color='#7f7f7f', linestyle='--', alpha=0.8)

# Configuración de etiquetas profesionales  
plt.title('Simulación Financiera: Modelo SFM vs Mercado de Criptomonedas', fontsize=14, fontweight='bold')  
plt.xlabel('Fechas del Conjunto de Validación / Test', fontsize=12)  
plt.ylabel('Crecimiento del Capital (Multiplicador del Balance Inicial)', fontsize=12)  
plt.legend(loc='upper left', fontsize=11)  
plt.grid(True, linestyle=':', alpha=0.6)  
plt.gcf().autofmt_xdate() # Rota las fechas del eje X para que no se encimen

# Guardar gráfico localmente y mostrar en la pantalla  
plt.savefig("rendimiento_modelo_sfm.png", dpi=300)  
print("💾 Gráfica de rendimiento exportada y guardada como 'rendimiento_modelo_sfm.png'")  
plt.show()