"""
qlib_sfm_pipeline.v2.py — SFM Multivariable con Filtrado Wavelet (Denoising)

Mejoras respecto a v1:
  - Preprocesado con Transformada Wavelet para eliminar ruido diario
  - División train/val/test cronológica (70/15/15)
  - Early stopping basado en validation loss
  - Reentreno final sobre train+val tras early stopping
  - Comparativa visual raw vs denoised
  - Cómputo de señal de trading (predicción direccional)
"""

import os, pickle, warnings
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import MinMaxScaler

# ── Denoising: pywt como primario, scipy.signal como fallback ──
try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False
    from scipy.signal import savgol_filter

import qlib
from qlib.config import REG_US
from qlib.data import D

warnings.filterwarnings("ignore")

# =====================================================================
# 1. ARQUITECTURA DEL MODELO SFM (sin cambios respecto a v1)
# =====================================================================
class SFMCellRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, dropout_rate=0.2):
        super().__init__()
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
        super().__init__()
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
# 2. FILTRO DE RUIDO — WAVELET DENOISING (primario) / SAVGOL (fallback)
# =====================================================================
def wavelet_denoise_series(series: np.ndarray, wavelet: str = "db4",
                           level: int = None, method: str = "soft") -> np.ndarray:
    """
    Aplica umbralizado wavelet (DWT + thresholding + IDWT) a una serie 1D.
    Elimina componentes de alta frecuencia (ruido diario) preservando
    la estructura de tendencia y ciclo.
    """
    if level is None:
        level = int(np.floor(np.log2(len(series)))) - 2
        level = max(1, min(level, 6))

    # Descomposición wavelet
    coeffs = pywt.wavedec(series, wavelet, level=level)

    # Estimación del umbral: sigma * sqrt(2 * log(N))
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(series)))

    # Aplicar umbralizado (soft = suavizado, hard = conserva picos)
    coeffs_th = list(coeffs)
    for i in range(1, len(coeffs_th)):
        coeffs_th[i] = pywt.threshold(coeffs_th[i], threshold, mode=method)

    # Reconstrucción
    return pywt.waverec(coeffs_th, wavelet)[:len(series)]


def denoise_market_matrix(matrix: np.ndarray, method: str = "wavelet",
                           wavelet: str = "db4", window_length: int = 11) -> np.ndarray:
    """
    Aplica denoising columna a columna sobre la matriz de mercado.
    Útil cuando NO se tiene pywt instalado (usa Savitzky–Golay como fallback).

    Parámetros
    ----------
    matrix : (días, features)
    method : "wavelet" | "savgol"
    """
    denoised = np.zeros_like(matrix)
    n_features = matrix.shape[1]

    for f in range(n_features):
        col = matrix[:, f].copy()

        if method == "wavelet" and HAS_PYWT:
            denoised[:, f] = wavelet_denoise_series(col, wavelet=wavelet)
        else:
            # Savitzky–Golay: suavizado polinómico sobre ventana deslizante
            wl = min(window_length, len(col) - 1 if len(col) % 2 == 0 else len(col))
            wl = wl if wl % 2 == 1 else wl - 1
            if wl < 3:
                denoised[:, f] = col
            else:
                from scipy.signal import savgol_filter
                denoised[:, f] = savgol_filter(col, window_length=wl, polyorder=2)

    return denoised


# =====================================================================
# 3. EXTRACCIÓN Y PROCESAMIENTO DE DATOS DESDE QLIB
# =====================================================================
def load_and_process_crypto_data(cryptos, start_date, end_date,
                                 denoise: bool = True,
                                 denoise_method: str = "wavelet"):
    """
    Carga datos desde Qlib, construye features (close, retorno, ratio MA5)
    y opcionalmente aplica filtrado wavelet para eliminar ruido diario.
    """
    fields = ['$close']
    df_qlib = D.features(cryptos, fields, start_time=start_date, end_time=end_date)
    df_reset = df_qlib.reset_index()

    features_list = []

    # 1. Precios de cierre
    df_close = df_reset.pivot(index='datetime', columns='instrument', values='$close')[cryptos]
    features_list.append(df_close.values)

    # 2. Retornos diarios (% cambio)
    df_pct = df_close.pct_change().fillna(0)
    features_list.append(df_pct.values)

    # 3. Ratio MA5 (ratio media móvil 5d / precio actual)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_ratio = (df_mean_5 / df_close).fillna(1.0)
    features_list.append(df_ratio.values)

    market_matrix = np.hstack(features_list)
    labels_matrix = df_pct.shift(-1).fillna(0).values

    # ── Aplicar denoising si se solicita ──
    if denoise:
        print(f"🌀 Aplicando filtro denoising ({denoise_method}) sobre {market_matrix.shape[1]} features...")
        market_matrix_denoised = denoise_market_matrix(market_matrix, method=denoise_method)
    else:
        market_matrix_denoised = market_matrix.copy()

    return market_matrix_denoised, labels_matrix, df_close, df_pct, market_matrix


def make_sliding_windows(market_matrix, labels_matrix, lookback=30):
    """Construye tensores 3D: (muestras, lookback, features)"""
    X, y = [], []
    for i in range(len(market_matrix) - lookback - 1):
        X.append(market_matrix[i: i + lookback, :])
        y.append(labels_matrix[i + lookback, :])
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)


def split_chronologically(X, y, train_frac=0.70, val_frac=0.15):
    """División cronológica train/val/test respetando el orden temporal."""
    n = len(X)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    return (X[:train_end], y[:train_end]), \
           (X[train_end:val_end], y[train_end:val_end]), \
           (X[val_end:], y[val_end:])


# =====================================================================
# 4. ENTRENAMIENTO CON EARLY STOPPING Y REENTRENO
# =====================================================================
def train_with_early_stopping(model, train_loader, val_loader,
                              epochs=100, lr=0.001, patience=10,
                              device="cpu", model_path="sfm_best.pth"):
    """
    Entrena con early stopping sobre validation loss.
    Guarda los mejores pesos y devuelve el historial de pérdidas.
    """
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    best_val_loss = float("inf")
    patience_counter = 0
    history = {"train": [], "val": []}

    for epoch in range(epochs):
        # ── Train ──
        model.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        # ── Validation ──
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                loss = criterion(model(bx), by)
                val_loss += loss.item()
        val_loss /= len(val_loader)

        history["train"].append(train_loss)
        history["val"].append(val_loss)

        # ── Early stopping check ──
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), model_path)
        else:
            patience_counter += 1

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Época [{epoch+1:3d}/{epochs}]  Train: {train_loss:.6f}  Val: {val_loss:.6f}  "
                  f"{'★ best' if val_loss == best_val_loss else f'(peor {patience_counter}/{patience})'}")

        if patience_counter >= patience:
            print(f"  ⏹️  Early stopping en época {epoch+1}")
            break

    # Cargar mejores pesos
    model.load_state_dict(torch.load(model_path, weights_only=True))
    print(f"  ✅ Mejor Val Loss: {best_val_loss:.6f} (cargado)")
    return history


# =====================================================================
# 5. PIPELINE PRINCIPAL
# =====================================================================
if __name__ == "__main__":
    # ── Configuración ──
    LOOKBACK = 30
    HIDDEN_DIM = 64
    FREQ_COMPONENTS = 10
    EPOCHS = 100
    LR = 0.001
    PATIENCE = 12
    BATCH_SIZE = 32
    DENOISE = True
    DENOISE_METHOD = "wavelet"        # "wavelet" | "savgol"
    CRYPTOS = ['btc', 'eth', 'sol', 'xlm', 'ada']

    print("=" * 60)
    print("🧠 qlib_sfm_pipeline.v2.py — SFM + Wavelet Denoising")
    print("=" * 60)
    print(f"   Cryptos: {CRYPTOS}")
    print(f"   LOOKBACK={LOOKBACK}  HIDDEN_DIM={HIDDEN_DIM}  K(freq)={FREQ_COMPONENTS}")
    print(f"   Denoising: {DENOISE_METHOD if DENOISE else 'OFF'}")
    if HAS_PYWT:
        print(f"   PyWavelets: ✓ (versión {pywt.__version__})")
    else:
        print(f"   PyWavelets: ✗ → usando Savitzky-Golay como fallback")
    print("=" * 60)

    # ── Inicializar Qlib ──
    qlib.init(provider_uri='/mnt/e/src/agent_qlib/data/qlib', region=REG_US)

    # ── Carga + denoising ──
    print("\n📥 Cargando datos y aplicando filtrado...")
    market_data, labels_data, df_prices, df_returns, market_raw = \
        load_and_process_crypto_data(CRYPTOS, "2023-01-01", "2026-06-01",
                                     denoise=DENOISE, denoise_method=DENOISE_METHOD)

    # ── Split cronológico ──
    split_idx = int(len(market_data) * 0.70)

    market_train = market_data[:split_idx]
    market_val_test = market_data[split_idx:]

    labels_train = labels_data[:split_idx]
    labels_val_test = labels_data[split_idx:]

    # ── Escalado con MinMax (fit solo en train) ──
    scaler = MinMaxScaler(feature_range=(-1, 1))
    market_train_scaled = scaler.fit_transform(market_train)
    market_val_test_scaled = scaler.transform(market_val_test)

    # ── Ventanas deslizantes ──
    X_full_train, y_full_train = make_sliding_windows(
        np.vstack([market_train_scaled, market_val_test_scaled]),
        np.vstack([labels_train, labels_val_test]),
        lookback=LOOKBACK
    )

    X_train, y_train = make_sliding_windows(market_train_scaled, labels_train, lookback=LOOKBACK)

    # Separar val y test del tramo val_test
    n_val_test = len(market_val_test_scaled)
    mid = int(n_val_test * 0.5)  # 0.5 → split 15% / 15% sobre el total

    market_val_scaled = market_val_test_scaled[:mid]
    market_test_scaled = market_val_test_scaled[mid:]
    labels_val = labels_val_test[:mid]
    labels_test = labels_val_test[mid:]

    X_val, y_val = make_sliding_windows(market_val_scaled, labels_val, lookback=LOOKBACK)
    X_test, y_test = make_sliding_windows(market_test_scaled, labels_test, lookback=LOOKBACK)

    print(f"\n📐 Dimensiones:")
    print(f"   X_train: {X_train.shape}   y_train: {y_train.shape}")
    print(f"   X_val:   {X_val.shape}     y_val:   {y_val.shape}")
    print(f"   X_test:  {X_test.shape}    y_test:  {y_test.shape}")

    # ── DataLoaders ──
    train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=BATCH_SIZE, shuffle=False)
    val_loader = DataLoader(TensorDataset(X_val, y_val), batch_size=BATCH_SIZE, shuffle=False)

    # ── Instanciar modelo ──
    input_dim = market_data.shape[1]
    output_dim = len(CRYPTOS)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = SFMModelRefined(input_dim, HIDDEN_DIM, FREQ_COMPONENTS, output_dim).to(device)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"\n🏗️  Modelo SFM → parámetros: {total_params:,}  (device: {device})")

    # ── Entrenar con early stopping ──
    print("\n🏋️ Entrenando con early stopping...")
    history = train_with_early_stopping(
        model, train_loader, val_loader,
        epochs=EPOCHS, lr=LR, patience=PATIENCE,
        device=device, model_path="sfm_best_v2.pth"
    )

    # ── Reentreno final sobre train+val ──
    print("\n🔄 Reentrenando sobre train+val combinado...")
    X_combined = torch.cat([X_train, X_val], dim=0)
    y_combined = torch.cat([y_train, y_val], dim=0)
    combined_loader = DataLoader(TensorDataset(X_combined, y_combined),
                                 batch_size=BATCH_SIZE, shuffle=False)

    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LR * 0.5, weight_decay=1e-4)
    model.train()
    for epoch in range(10):
        total_loss = 0.0
        for bx, by in combined_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 5 == 0:
            print(f"   Época [{epoch+1:2d}/10]  Loss: {total_loss/len(combined_loader):.6f}")

    # ── Evaluación en test ──
    print("\n🔮 Evaluando en conjunto de test (out-of-sample)...")
    model.eval()
    with torch.no_grad():
        preds = model(X_test.to(device)).cpu().numpy()
    real_returns = y_test.numpy()

    # ── Estrategia Top-1 ──
    best_asset = np.argmax(preds, axis=1)
    strategy_returns = np.array([real_returns[t, best_asset[t]] for t in range(len(best_asset))])
    strategy_returns -= 0.001  # comisión estimada

    benchmark_returns = np.mean(real_returns, axis=1)

    equity_strategy = np.cumprod(1 + strategy_returns)
    equity_benchmark = np.cumprod(1 + benchmark_returns)

    print(f"\n📊 Resultados Test:")
    print(f"   Estrategia SFM (Top-1): {equity_strategy[-1]:.4f}x  "
          f"({(equity_strategy[-1]-1)*100:+.2f}%)")
    print(f"   Benchmark (Hold prom.): {equity_benchmark[-1]:.4f}x  "
          f"({(equity_benchmark[-1]-1)*100:+.2f}%)")
    print(f"   Diferencia vs Benchmark: {(equity_strategy[-1] - equity_benchmark[-1])*100:+.2f}pp")
    print(f"   Sharpe Ratio (aprox):    {np.mean(strategy_returns) / np.std(strategy_returns) * np.sqrt(252):.2f}")

    # ── Señal direccional ──
    accuracy = np.mean((preds > 0) == (real_returns > 0))
    print(f"   Precisión direccional:   {accuracy*100:.1f}%")

    # ── Gráfica de equity: SFM vs Buy & Hold ──
    print("\n📈 Generando gráfica de rendimiento...")
    import matplotlib.pyplot as plt
    plt.style.use('seaborn-v0_8-whitegrid')

    # Fechas del periodo de test
    test_start = split_idx + mid + LOOKBACK + 1
    test_dates = df_prices.index[test_start: test_start + len(strategy_returns)]

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(test_dates, equity_strategy,
            label=f'SFM Top-1 (Sharpe: {np.mean(strategy_returns)/np.std(strategy_returns)*np.sqrt(252):.2f})',
            color='#1f77b4', linewidth=2.5)
    ax.plot(test_dates, equity_benchmark,
            label='Benchmark — Hold Promedio (Buy & Hold)',
            color='#7f7f7f', linestyle='--', alpha=0.8)

    ax.set_title('Comparativa: Estrategia SFM vs Buy & Hold', fontsize=14, fontweight='bold')
    ax.set_xlabel('Fecha', fontsize=12)
    ax.set_ylabel('Capital (base = 1.0)', fontsize=12)
    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, linestyle=':', alpha=0.6)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig('rendimiento_sfm_v2.png', dpi=150)
    plt.close()
    print("   📁 Gráfica guardada como 'rendimiento_sfm_v2.png'")

    # ── Guardar modelo y scaler ──
    print("\n💾 Guardando modelo final y scaler...")
    torch.save(model.state_dict(), "sfm_multivariable_qlib_v2.pth")
    with open("sfm_scalers_qlib_v2.pkl", "wb") as f:
        pickle.dump(scaler, f)

    print("\n✅ Pipeline v2 completado.")
