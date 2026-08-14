import os
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import MinMaxScaler

import qlib
from qlib.config import REG_US
from qlib.data.dataset.handler import DataHandlerLP

# =====================================================================
# 1. ARQUITECTURA DEL MODELO SFM (STATE-FREQUENCY MEMORY) EN PYTORCH
# =====================================================================
class SFMCellRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, dropout_rate=0.2):
        super(SFMCellRefined, self).__init__()
        self.hidden_dim = hidden_dim
        self.K = freq_components
        
        # Puertas LSTM estándar
        self.W_i = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_f = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_o = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_z = nn.Linear(input_dim + hidden_dim, hidden_dim)
        
        # Parámetro de matriz de frecuencia (Estado-Frecuencia)
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
        
        # Descomposición de frecuencias
        W_w_expanded = self.W_omega.unsqueeze(0).expand(x.size(0), -1, -1)
        S_t = f.unsqueeze(-1) * S_prev + i.unsqueeze(-1) * torch.tanh(W_w_expanded)
        
        # Transformada Inversa de Fourier aproximada
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
# 2. CONFIGURACIÓN DEL DATAHANDLER DE QLIB
# =====================================================================
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
        # Dejamos que Qlib calcule las variables pero realizaremos el escalado manual 
        # para preservar la estructura tridimensional exacta requerida por el SFM
        "learn_processors": [], 
    }
    return DataHandlerLP(**handler_config)

# =====================================================================
# 3. PROCESAMIENTO Y TRANSFORMACIÓN DE TABLAS QLIB A SECUENCIAS 3D
# =====================================================================
def reshape_qlib_to_sequences(df_qlib, cryptos, lookback=30):
    """
    Convierte el formato MultiIndex [instrument, datetime] de Qlib a una matriz 
    multivariable tridimensional [Muestras, Pasos_de_Tiempo, Características]
    """
    df_reset = df_qlib.reset_index()
    
    # Pivotar los datos para alinear las criptos en columnas por cada feature
    features_list = []
    features_names = ['close', 'return_1d', 'mean_ratio_5']
    
    for f in features_names:
        df_pivot = df_reset.pivot(index='datetime', columns='instrument', values=f)
        # Garantizar orden correcto de las criptomonedas
        df_pivot = df_pivot[cryptos]
        features_list.append(df_pivot.values)
        
    # market_data forma: (Días, Criptos, Features) -> Reordenar a (Días, Criptos * Features)
    # Para este modelo multivariable consolidamos las características en un vector diario único
    market_data = np.hstack(features_list)
    
    # Ajustar con MinMaxScaler
    scaler = MinMaxScaler(feature_range=(-1, 1))
    market_data_scaled = scaler.fit_transform(market_data)
    
    # Crear ventanas deslizantes (Lookback)
    X, y = [], []
    for i in range(len(market_data_scaled) - lookback):
        X.append(market_data_scaled[i : (i + lookback), :])
        # Intentamos predecir todos los campos de cierre del día siguiente (las primeras 5 columnas son close)
        y.append(market_data_scaled[i + lookback, :len(cryptos)])
        
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32), scaler

# =====================================================================
# 4. PIPELINE PRINCIPAL DE EJECUCIÓN
# =====================================================================
if __name__ == "__main__":
    # Hiperparámetros
    LOOKBACK = 30
    HIDDEN_DIM = 64
    FREQ_COMPONENTS = 10
    EPOCHS = 20
    LR = 0.001
    CRYPTOS = ['btc', 'eth', 'sol', 'xlm', 'ada']
    
    # Paso 4.1: Inicializar Qlib apuntando a tu repositorio binario
    print("📁 Inicializando repositorio de datos binarios Qlib...")
    qlib.init(provider_uri='/mnt/c/Users/trodriguez/src/agent_qlib/data/qlib', region=REG_US)
    
    # Paso 4.2: Extraer datos mediante el Handler nativo
    print("📥 Cargando y calculando expresiones matemáticas desde Qlib...")
    handler = get_crypto_handler()
    
    # Extraemos el fragmento completo usando el selector
    df_raw = handler.fetch(
        selector=slice("2023-01-01 00:00:00", "2024-12-31 23:59:59"), 
        data_key=DataHandlerLP.DK_L)
    
    # Paso 4.3: Convertir datos a tensores 3D estructurados secuencialmente
    print("🔄 Dando forma tridimensional a los datos para la celda SFM...")
    X_train, y_train, scaler_system = reshape_qlib_to_sequences(df_raw, CRYPTOS, lookback=LOOKBACK)
    
    # Parámetros dinámicos de entrada: 5 criptos * 3 features calculadas = 15 dimensiones de entrada
    input_dimension = len(CRYPTOS) * 3 
    output_dimension = len(CRYPTOS) # Predice el precio de las 5 criptos a la vez
    
    print(f"🔹 Dimensiones del tensor X (Train): {X_train.shape} [Muestras, Secuencia, Features]")
    print(f"🔹 Dimensiones del tensor Y (Train): {y_train.shape} [Muestras, Target_Precios]")
    
    # Paso 4.4: Instanciar el modelo refinado con Regularización L2
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = SFMModelRefined(
        input_dim=input_dimension, 
        hidden_dim=HIDDEN_DIM, 
        freq_components=FREQ_COMPONENTS, 
        output_dim=output_dimension
    ).to(device)
    
    # Usamos AdamW para desacoplar el Weight Decay correctamente de los estados ocultos
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    criterion = nn.MSELoss()
    
    # Paso 4.5: Bucle de entrenamiento principal
    print(f"🏋️ Iniciando el entrenamiento del modelo SFM en {device}...")
    model.train()
    for epoch in range(EPOCHS):
        optimizer.zero_grad()
        
        # Enviar tensores al dispositivo correspondiente (CPU o GPU)
        inputs, targets = X_train.to(device), y_train.to(device)
        
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        
        loss.backward()
        optimizer.step()
        
        print(f"Época [{epoch+1:02d}/{EPOCHS}] ── Loss MSE: {loss.item():.6f}")
        
    print("🎉 ¡Entrenamiento completado exitosamente!")
    
    # Paso 4.6: Guardado persistente del sistema completo
    print("💾 Almacenando pesos de la red neuronales y parámetros del Scaler...")
    torch.save(model.state_dict(), "sfm_multivariable_qlib.pth")
    with open("sfm_scalers_qlib.pkl", "wb") as f:
        pickle.dump(scaler_system, f)
        
    print("\n✅ Pipeline ejecutado. Tu modelo SFM está guardado y listo para emitir señales diarias.")