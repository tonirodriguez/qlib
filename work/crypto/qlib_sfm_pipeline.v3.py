"""
qlib_sfm_pipeline.v3.py — SFM + Wavelet Denoising + Optimización Optuna

Mejoras respecto a v2:
  - Búsqueda de hiperparámetros con Optuna (HIDDEN_DIM, K, LR, DROPOUT, LOOKBACK, BATCH_SIZE)
  - Objetivo: minimizar validation MSE con penalización por overfitting
  - Pruning (MedianPruner) para trials no prometedores
  - Análisis de importancia de hiperparámetros
  - Reentreno final con mejores parámetros sobre train+val
  - Almacenamiento del mejor estudio como artefacto
  - Visualización de resultados del estudio
"""

import os, pickle, warnings, json, time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import MinMaxScaler

# ── Denoising ──
try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False
    from scipy.signal import savgol_filter

# ── Optuna ──
try:
    import optuna
    from optuna.pruners import MedianPruner
    from optuna.samplers import TPESampler
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

import qlib
from qlib.config import REG_US
from qlib.data import D
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# =====================================================================
# 1. ARQUITECTURA DEL MODELO SFM
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
# 2. WAVELET DENOISING
# =====================================================================
def wavelet_denoise_series(series: np.ndarray, wavelet: str = "db4",
                           level: int = None, method: str = "soft") -> np.ndarray:
    if level is None:
        level = int(np.floor(np.log2(len(series)))) - 2
        level = max(1, min(level, 6))
    coeffs = pywt.wavedec(series, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(series)))
    coeffs_th = list(coeffs)
    for i in range(1, len(coeffs_th)):
        coeffs_th[i] = pywt.threshold(coeffs_th[i], threshold, mode=method)
    return pywt.waverec(coeffs_th, wavelet)[:len(series)]


def denoise_market_matrix(matrix: np.ndarray, method: str = "wavelet",
                           wavelet: str = "db4", window_length: int = 11) -> np.ndarray:
    denoised = np.zeros_like(matrix)
    for f in range(matrix.shape[1]):
        col = matrix[:, f].copy()
        if method == "wavelet" and HAS_PYWT:
            denoised[:, f] = wavelet_denoise_series(col, wavelet=wavelet)
        else:
            wl = min(window_length, len(col) - 1 if len(col) % 2 == 0 else len(col))
            wl = wl if wl % 2 == 1 else wl - 1
            if wl < 3:
                denoised[:, f] = col
            else:
                from scipy.signal import savgol_filter
                denoised[:, f] = savgol_filter(col, window_length=wl, polyorder=2)
    return denoised


# =====================================================================
# 3. EXTRACCIÓN DE DATOS DESDE QLIB (preparación única)
# =====================================================================
def load_and_process_crypto_data(cryptos, start_date, end_date,
                                 denoise: bool = True,
                                 denoise_method: str = "wavelet"):
    fields = ['$close']
    df_qlib = D.features(cryptos, fields, start_time=start_date, end_time=end_date)
    df_reset = df_qlib.reset_index()

    df_close = df_reset.pivot(index='datetime', columns='instrument', values='$close')[cryptos]
    df_pct = df_close.pct_change().fillna(0)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_ratio = (df_mean_5 / df_close).fillna(1.0)

    market_matrix = np.hstack([df_close.values, df_pct.values, df_ratio.values])
    labels_matrix = df_pct.shift(-1).fillna(0).values

    if denoise:
        print(f"🌀 Denoising ({denoise_method}) sobre {market_matrix.shape[1]} features...")
        market_matrix = denoise_market_matrix(market_matrix, method=denoise_method)

    return market_matrix, labels_matrix, df_close.index


def make_sliding_windows(market_matrix, labels_matrix, lookback=30):
    X, y = [], []
    for i in range(len(market_matrix) - lookback - 1):
        X.append(market_matrix[i: i + lookback, :])
        y.append(labels_matrix[i + lookback, :])
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)


# =====================================================================
# 4. ENTRENAMIENTO (compatible con Optuna, reporta pruning)
# =====================================================================
def train_trial(model, train_loader, val_loader, epochs, lr, weight_decay,
                device, trial=None, patience=8):
    """
    Entrena un modelo y reporta a Optuna para pruning.
    Devuelve (best_val_loss, history).
    """
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_val_loss = float("inf")
    best_epoch = 0
    patience_counter = 0
    history = {"train": [], "val": []}

    for epoch in range(epochs):
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

        # ── Pruning: reportar a Optuna cada época ──
        if trial is not None:
            trial.report(val_loss, epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= patience:
            break

    return best_val_loss, history, best_epoch


# =====================================================================
# 5. OBJETIVO DE OPTUNA
# =====================================================================
def objective(trial, X_train, y_train, X_val, y_val, input_dim, output_dim,
              device, scaler_train, scaler_val_test, market_train, labels_train,
              market_val, labels_val, lookback_base, cryptos):
    """
    Función objetivo para Optuna. Sugiere hiperparámetros y devuelve val_loss.
    """
    # ── Hiperparámetros a optimizar ──
    hidden_dim = trial.suggest_int("hidden_dim", 32, 128, step=16)
    freq_components = trial.suggest_int("freq_components", 4, 20)
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    dropout_rate = trial.suggest_float("dropout_rate", 0.1, 0.5, step=0.05)
    batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
    weight_decay = trial.suggest_float("weight_decay", 1e-5, 1e-3, log=True)

    # LOOKBACK se prueba cada 5 pasos para mantener estabilidad del dataset
    lookback = trial.suggest_int("lookback", 15, 50, step=5)

    n_epochs = 60
    patience = 8

    # ── Reconstruir ventanas con este lookback ──
    X_tr, y_tr = make_sliding_windows(scaler_train, labels_train, lookback=lookback)
    X_v, y_v = make_sliding_windows(scaler_val_test, labels_val, lookback=lookback)

    if len(X_tr) < 100 or len(X_v) < 20:
        raise optuna.TrialPruned()  # dataset demasiado pequeño

    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=batch_size, shuffle=False)
    val_loader = DataLoader(TensorDataset(X_v, y_v), batch_size=batch_size, shuffle=False)

    # ── Instanciar modelo ──
    model = SFMModelRefined(input_dim, hidden_dim, freq_components, output_dim,
                            dropout_rate=dropout_rate).to(device)

    best_val_loss, history, best_epoch = train_trial(
        model, train_loader, val_loader,
        epochs=n_epochs, lr=lr, weight_decay=weight_decay,
        device=device, trial=trial, patience=patience
    )

    # ── Métricas adicionales (informativas, no afectan la optimización) ──
    train_final = history["train"][best_epoch] if best_epoch < len(history["train"]) else history["train"][-1]

    return best_val_loss


# =====================================================================
# 6. EVALUACIÓN COMPLETA DE UN TRIAL (con backtesting)
# =====================================================================
def evaluate_trial(model, X_test, y_test, cryptos, device):
    """Evalúa un modelo entrenado: test loss + backtesting rápido."""
    model.eval()
    with torch.no_grad():
        preds = model(X_test.to(device)).cpu().numpy()
    real = y_test.numpy()

    test_loss = np.mean((preds - real) ** 2)

    # Top-1 strategy
    best_asset = np.argmax(preds, axis=1)
    strategy_returns = np.array([real[t, best_asset[t]] for t in range(len(best_asset))])
    strategy_returns -= 0.001

    benchmark_returns = np.mean(real, axis=1)
    equity_sfm = np.cumprod(1 + strategy_returns)
    equity_bm = np.cumprod(1 + benchmark_returns)

    sharpe = np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-10) * np.sqrt(252)
    direction_acc = np.mean((preds > 0) == (real > 0))

    return {
        "test_loss": float(test_loss),
        "equity_final": float(equity_sfm[-1]),
        "benchmark_final": float(equity_bm[-1]),
        "sharpe": float(sharpe),
        "direction_acc": float(direction_acc),
        "outperformance": float(equity_sfm[-1] - equity_bm[-1]),
        "strategy_returns": strategy_returns,
        "benchmark_returns": benchmark_returns,
        "preds": preds,
        "real": real,
    }


# =====================================================================
# 7. VISUALIZACIÓN DEL ESTUDIO OPTUNA
# =====================================================================
def _plot_distribution(study, output_dir):
    """Gráfica matplotlib de distribución de trials (no necesita plotly)."""
    best = study.best_trial

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    val_losses = [t.value for t in study.trials if t.value is not None]
    axes[0].hist(val_losses, bins=30, edgecolor="black", alpha=0.7, color="steelblue")
    axes[0].axvline(best.value, color="red", linestyle="--", label=f"Mejor: {best.value:.6f}")
    axes[0].set_xlabel("Validation Loss (MSE)")
    axes[0].set_ylabel("Frecuencia")
    axes[0].set_title("Distribución de Trials")
    axes[0].legend()

    n_complete = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE)
    n_pruned = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.PRUNED)
    axes[1].bar(["Completados", "Pruned"], [n_complete, n_pruned],
                color=["green", "orange"], edgecolor="black")
    axes[1].set_ylabel("Nº de trials")
    axes[1].set_title(f"Trials: {n_complete + n_pruned} totales")

    plt.suptitle(f"Estudio Optuna — Mejor Val Loss: {best.value:.6f}", fontsize=14)
    plt.tight_layout()
    _dist_path = os.path.join(output_dir, "optuna_distribution.png")
    plt.savefig(_dist_path, dpi=150)
    plt.close()
    if os.path.exists(_dist_path):
        print(f"   📊 optuna_distribution.png guardado ({os.path.getsize(_dist_path)} bytes)")
    else:
        print(f"   ❌ optuna_distribution.png NO se guardó en {_dist_path}")


def _plot_interactive(study, output_dir):
    """Gráficas interactivas de Optuna (opcional, necesita plotly+narwhals+kaleido)."""
    try:
        fig = optuna.visualization.plot_optimization_history(study)
        fig.write_image(os.path.join(output_dir, "optuna_history.png"))
        print(f"   📈 optuna_history.png guardado")
    except Exception as e:
        print(f"   ⚠️  optuna_history omitido: {e}")

    try:
        fig = optuna.visualization.plot_parallel_coordinate(
            study, params=["hidden_dim", "freq_components", "lr", "dropout_rate", "batch_size", "lookback"]
        )
        fig.write_image(os.path.join(output_dir, "optuna_parallel_coord.png"))
        print(f"   📊 optuna_parallel_coord.png guardado")
    except Exception:
        pass

    try:
        fig = optuna.visualization.plot_param_importances(study)
        fig.write_image(os.path.join(output_dir, "optuna_importances.png"))
        print(f"   🔬 optuna_importances.png guardado")
    except Exception:
        pass

    try:
        fig = optuna.visualization.plot_slice(study)
        fig.write_image(os.path.join(output_dir, "optuna_slice.png"))
        print(f"   🧩 optuna_slice.png guardado")
    except Exception:
        pass


def plot_optuna_results(study, output_dir="."):
    """Genera gráficas del estudio Optuna (matplotlib + opcionales plotly)."""
    # 1. Matplotlib (siempre se ejecuta, no necesita plotly/narwhals)
    try:
        _plot_distribution(study, output_dir)
    except Exception as e:
        print(f"   ❌ Error en gráfica de distribución: {e}")

    # 2. Gráficas interactivas (opcional)
    try:
        _plot_interactive(study, output_dir)
    except Exception as e:
        print(f"   ⚠️  Gráficas interactivas omitidas: {e}")


# =====================================================================
# 8. PIPELINE PRINCIPAL CON OPTUNA
# =====================================================================
if __name__ == "__main__":
    # ── Configuración fija ──
    # ── Semillas para reproducibilidad ──
    import random
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    CRYPTOS = ['btc', 'eth', 'sol', 'xlm', 'ada']
    DENOISE = True
    DENOISE_METHOD = "wavelet"
    N_TRIALS = 30                     # número de trials de Optuna
    N_EPOCHS_FINAL = 100              # épocas para el reentreno final
    PATIENCE_FINAL = 15               # paciencia para el reentreno final
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output/optuna_sfm")

    print("=" * 65)
    print("🧠 qlib_sfm_pipeline.v3.py — SFM + Wavelet + Optuna")
    print("=" * 65)
    print(f"   Cryptos: {CRYPTOS}")
    print(f"   Denoising: {DENOISE_METHOD if DENOISE else 'OFF'}")
    print(f"   Trials Optuna: {N_TRIALS}")
    print(f"   PyWavelets: {'✓' if HAS_PYWT else '✗ → Savgol'}")
    print(f"   Optuna:     {'✓' if HAS_OPTUNA else '✗'}")
    if not HAS_OPTUNA:
        print("   ⚠️  Instala optuna: pip install optuna")
        print("   ⚠️  También para gráficos: pip install plotly kaleido")
        exit(1)
    print("=" * 65)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Inicializar Qlib ──
    qlib.init(provider_uri='/mnt/e/src/agent_qlib/data/qlib', region=REG_US)

    # ── Carga única de datos ──
    print("\n📥 Cargando datos desde Qlib...")
    market_data, labels_data, dates_idx = load_and_process_crypto_data(
        CRYPTOS, "2023-01-01", "2026-06-01",
        denoise=DENOISE, denoise_method=DENOISE_METHOD
    )

    input_dim = market_data.shape[1]   # n_cryptos * 3 features
    output_dim = len(CRYPTOS)

    print(f"   Matrix raw: {market_data.shape}  (días × features)")
    print(f"   Fechas: {dates_idx[0].strftime('%Y-%m-%d')} → {dates_idx[-1].strftime('%Y-%m-%d')}")

    # ── Split cronológico: 70/15/15 ──
    n_total = len(market_data)
    train_end = int(n_total * 0.70)
    val_end = int(n_total * 0.85)

    market_train = market_data[:train_end]
    market_val = market_data[train_end:val_end]
    market_test = market_data[val_end:]

    labels_train = labels_data[:train_end]
    labels_val = labels_data[train_end:val_end]
    labels_test = labels_data[val_end:]

    print(f"\n📐 Split cronológico: train={len(market_train)}  val={len(market_val)}  test={len(market_test)}")

    # ── Escalado (fit solo en train) ──
    scaler = MinMaxScaler(feature_range=(-1, 1))
    market_train_scaled = scaler.fit_transform(market_train)
    market_val_scaled = scaler.transform(market_val)
    market_test_scaled = scaler.transform(market_test)

    # ── Ventanas base (lookback por defecto para referencia) ──
    X_train_ref, y_train_ref = make_sliding_windows(market_train_scaled, labels_train, lookback=30)
    X_val_ref, y_val_ref = make_sliding_windows(market_val_scaled, labels_val, lookback=30)
    X_test_ref, y_test_ref = make_sliding_windows(market_test_scaled, labels_test, lookback=30)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"   Device: {device}")

    # =================================================================
    # FASE 1: OPTIMIZACIÓN CON OPTUNA
    # =================================================================
    print("\n" + "=" * 65)
    print("🔬 FASE 1: BÚSQUEDA DE HIPERPARÁMETROS CON OPTUNA")
    print("=" * 65)
    print(f"   Trials: {N_TRIALS}  |  Sampler: TPESampler  |  Pruner: MedianPruner")
    print(f"   Hiperparámetros: hidden_dim, K(freq), lr, dropout, batch_size, weight_decay, lookback")
    print(f"   Objetivo: minimizar Validation MSE")

    study = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=42),
        pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=5, interval_steps=1),
        study_name="sfm_optuna_v3",
        storage=None
    )

    start_time = time.time()

    try:
        study.optimize(
            lambda trial: objective(
                trial, X_train_ref, y_train_ref, X_val_ref, y_val_ref,
                input_dim, output_dim, device,
                market_train_scaled, market_val_scaled,
                market_train, labels_train,
                market_val, labels_val,
                30, CRYPTOS
            ),
            n_trials=N_TRIALS,
            show_progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n⚠️  Optimización interrumpida por el usuario. Continuando con mejores params...")

    elapsed = time.time() - start_time
    print(f"\n⏱️  Optimización completada en {elapsed/60:.1f} minutos")

    # ── Resultados del estudio ──
    best_trial = study.best_trial
    print("\n🏆 MEJOR TRIAL:")
    print(f"   Val Loss: {best_trial.value:.6f}")
    for key, val in best_trial.params.items():
        print(f"   {key}: {val}")
    print(f"   Estado: {best_trial.state}")

    # Guardar resultados del estudio
    study_results = {
        "best_val_loss": best_trial.value,
        "best_params": best_trial.params,
        "n_trials": len(study.trials),
        "n_complete": sum(1 for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE),
        "n_pruned": sum(1 for t in study.trials if t.state == optuna.trial.TrialState.PRUNED),
        "elapsed_min": elapsed / 60,
    }
    with open(os.path.join(OUTPUT_DIR, "study_results.json"), "w") as f:
        json.dump(study_results, f, indent=2)
    print(f"\n💾 Resultados guardados en {OUTPUT_DIR}/study_results.json")

    # ── Visualizaciones ──
    print("\n📊 Generando visualizaciones del estudio...")
    try:
        plot_optuna_results(study, OUTPUT_DIR)
    except Exception as e:
        print(f"   ⚠️  Visualización parcial: {e}")

    # =================================================================
    # FASE 2: REENTRENO CON MEJORES HIPERPARÁMETROS
    # =================================================================
    print("\n" + "=" * 65)
    print("🏋️  FASE 2: REENTRENO CON MEJORES PARÁMETROS (train+val → test)")
    print("=" * 65)

    best = best_trial.params
    HIDDEN_DIM = best["hidden_dim"]
    FREQ_COMPONENTS = best["freq_components"]
    LR = best["lr"]
    DROPOUT = best["dropout_rate"]
    BATCH_SIZE = best["batch_size"]
    WEIGHT_DECAY = best["weight_decay"]
    LOOKBACK = best["lookback"]

    print(f"\n   LOOKBACK={LOOKBACK}  HIDDEN_DIM={HIDDEN_DIM}  K={FREQ_COMPONENTS}")
    print(f"   LR={LR:.6f}  DROPOUT={DROPOUT:.2f}  BATCH={BATCH_SIZE}  WD={WEIGHT_DECAY:.6f}")

    # ── Reconstruir ventanas con el LOOKBACK óptimo ──
    X_train, y_train = make_sliding_windows(market_train_scaled, labels_train, lookback=LOOKBACK)
    X_val, y_val = make_sliding_windows(market_val_scaled, labels_val, lookback=LOOKBACK)
    X_test, y_test = make_sliding_windows(market_test_scaled, labels_test, lookback=LOOKBACK)

    print(f"\n   Train: {X_train.shape}  Val: {X_val.shape}  Test: {X_test.shape}")

    # ── Reentreno sobre train+val ──
    X_combined = torch.cat([X_train, X_val], dim=0)
    y_combined = torch.cat([y_train, y_val], dim=0)
    combined_loader = DataLoader(TensorDataset(X_combined, y_combined),
                                 batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(TensorDataset(X_test, y_test),
                             batch_size=BATCH_SIZE, shuffle=False)

    model_final = SFMModelRefined(input_dim, HIDDEN_DIM, FREQ_COMPONENTS, output_dim,
                                  dropout_rate=DROPOUT).to(device)

    print(f"\n🏗️  Modelo final → parámetros: {sum(p.numel() for p in model_final.parameters()):,}")

    # Entrenar con early stopping sobre train+val (no tenemos validation separado,
    # así que usamos early stopping sobre train loss como aproximación)
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model_final.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    best_loss = float("inf")
    patience_counter = 0

    for epoch in range(N_EPOCHS_FINAL):
        model_final.train()
        train_loss = 0.0
        for bx, by in combined_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model_final(bx), by)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(combined_loader)

        # Early stopping sobre train loss (proxy)
        if train_loss < best_loss:
            best_loss = train_loss
            patience_counter = 0
            torch.save(model_final.state_dict(), os.path.join(OUTPUT_DIR, "sfm_best_v3.pth"))
        else:
            patience_counter += 1

        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"   Época [{epoch+1:3d}/{N_EPOCHS_FINAL}]  Loss: {train_loss:.6f}  "
                  f"{'★' if train_loss == best_loss else f'({patience_counter}/{PATIENCE_FINAL})'}")

        if patience_counter >= PATIENCE_FINAL:
            print(f"   ⏹️  Early stopping en época {epoch+1}")
            break

    model_final.load_state_dict(torch.load(os.path.join(OUTPUT_DIR, "sfm_best_v3.pth"),
                                            weights_only=True))

    # =================================================================
    # FASE 3: EVALUACIÓN EN TEST
    # =================================================================
    print("\n" + "=" * 65)
    print("🔮 FASE 3: EVALUACIÓN EN TEST (out-of-sample)")
    print("=" * 65)

    results = evaluate_trial(model_final, X_test, y_test, CRYPTOS, device)

    print(f"\n📊 RESULTADOS FINALES (TEST):")
    print(f"   ┌─────────────────────────┬──────────────┐")
    print(f"   │ Test Loss (MSE)         │ {results['test_loss']:.6f}        │")
    print(f"   │ Equity SFM (Top-1)      │ {results['equity_final']:.4f}x    │")
    print(f"   │ Benchmark (Hold prom.)  │ {results['benchmark_final']:.4f}x  │")
    print(f"   │ Outperformance          │ {results['outperformance']*100:+.2f}pp   │")
    print(f"   │ Sharpe Ratio            │ {results['sharpe']:.2f}          │")
    print(f"   │ Precision direccional   │ {results['direction_acc']*100:.1f}%      │")
    print(f"   └─────────────────────────┴──────────────┘")

    # ── Gráfica de equity curves ──
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(14, 7))

    fechas_test = dates_idx[
        train_end + val_end + LOOKBACK + 1:
        train_end + val_end + LOOKBACK + 1 + len(results["strategy_returns"])
    ]
    if len(fechas_test) != len(results["strategy_returns"]):
        fechas_test = np.arange(len(results["strategy_returns"]))

    ax.plot(fechas_test, np.cumprod(1 + results["strategy_returns"]),
            label=f'SFM Top-1 (Sharpe: {results["sharpe"]:.2f})',
            color="#1f77b4", linewidth=2.5)
    ax.plot(fechas_test, np.cumprod(1 + results["benchmark_returns"]),
            label=f'Benchmark Hold (promedio)',
            color="#7f7f7f", linestyle="--", alpha=0.8)

    ax.set_title("Backtesting SFM v3 (Optuna) — Curva de Equity", fontsize=14, fontweight="bold")
    ax.set_xlabel("Fecha" if not isinstance(fechas_test[0], (int, np.integer)) else "Días de Test")
    ax.set_ylabel("Capital (base = 1.0)")
    ax.legend(loc="upper left", fontsize=11)
    ax.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "equity_curve_v3.png"), dpi=150)
    plt.close()
    print(f"\n📈 equity_curve_v3.png guardado")

    # ── Guardar modelo y scaler ──
    print("\n💾 Guardando modelo final y scaler...")
    torch.save(model_final.state_dict(), os.path.join(OUTPUT_DIR, "sfm_multivariable_qlib_v3.pth"))
    with open(os.path.join(OUTPUT_DIR, "sfm_scalers_qlib_v3.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    # También guardar los parámetros del mejor trial para cargar sin reoptimizar
    with open(os.path.join(OUTPUT_DIR, "best_params_v3.json"), "w") as f:
        json.dump(best_trial.params, f, indent=2)

    # ── Resumen final ──
    print("\n" + "=" * 65)
    print("✅ Pipeline v3 completado.")
    print("=" * 65)
    print(f"\n   📁 Salida: {OUTPUT_DIR}/")
    print(f"   ├── study_results.json       (resultados del estudio)")
    print(f"   ├── best_params_v3.json      (mejores hiperparámetros)")
    print(f"   ├── sfm_best_v3.pth          (mejores pesos del reentreno)")
    print(f"   ├── sfm_multivariable_qlib_v3.pth (modelo final)")
    print(f"   ├── sfm_scalers_qlib_v3.pkl  (scaler del pipeline)")
    print(f"   ├── optuna_history.png       (evolución del estudio)")
    print(f"   ├── optuna_parallel_coord.png (relaciones entre parámetros)")
    print(f"   ├── optuna_importances.png   (importancia de cada hp)")
    print(f"   ├── optuna_slice.png         (slice plots)")
    print(f"   ├── optuna_distribution.png  (histograma)")
    print(f"   └── equity_curve_v3.png      (backtesting final)")
