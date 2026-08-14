"""
qlib_sfm_pipeline.v4.py — SFM + Wavelet + Optuna + Walk-Forward + Top-K

Mejoras respecto a v3:
  - Walk-forward validation: 3 ventanas de test secuenciales en lugar de una sola
  - Top-K evaluation: entrena y evalúa los K mejores trials, no solo el #1 (evita p-hacking)
  - Semillas fijas en todo el pipeline para reproducibilidad total
  - N_TRIALS aumentado a 100 para convergencia más estable
  - Reporte estadístico: media, desviación, mínimo y máximo de Sharpe/equity entre los K top
"""

import os, pickle, warnings, json, time, random, math
from copy import deepcopy
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.preprocessing import MinMaxScaler

# ── Semillas globales ──
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

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
matplotlib.use("Agg")
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
def wavelet_denoise_series(series, wavelet="db4", level=None, method="soft"):
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


def denoise_market_matrix(matrix, method="wavelet", wavelet="db4", window_length=11):
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
# 3. EXTRACCIÓN DE DATOS
# =====================================================================
def load_and_process_crypto_data(cryptos, start_date, end_date,
                                 denoise=True, denoise_method="wavelet"):
    fields = ['$close']
    print(f"   📡 Solicitando '{cryptos}' desde {start_date} hasta {end_date}...")
    df_qlib = D.features(cryptos, fields, start_time=start_date, end_time=end_date)
    df_reset = df_qlib.reset_index()

    df_close = df_reset.pivot(index='datetime', columns='instrument', values='$close')[cryptos]

    print(f"\n{'='*62}")
    print("📊 DIAGNÓSTICO DE DATOS")
    print("=" * 62)
    print(f"   Consulta original:    {start_date} → {end_date}")
    print(f"   Filas sin procesar:   {len(df_close)}")
    print(f"   Activos solicitados:  {cryptos}")
    for c in cryptos:
        n_nan_c = df_close[c].isna().sum()
        first_c = df_close[c].first_valid_index()
        last_c = df_close[c].last_valid_index()
        first_c_str = first_c.strftime('%Y-%m-%d') if first_c is not None else '—'
        last_c_str = last_c.strftime('%Y-%m-%d') if last_c is not None else '—'
        na_pct = 100 * n_nan_c / len(df_close)
        print(f"     {c:>5s}:  {n_nan_c:>5d} NaN ({na_pct:5.1f}%)  "
              f"  [{first_c_str} → {last_c_str}]")

    # 🟢 Eliminar filas con NaNs (activos que no existían en la fecha)
    n_before = len(df_close)
    df_close = df_close.dropna()
    n_after = len(df_close)
    n_lost = n_before - n_after
    if n_lost > 0:
        print(f"\n   🔻 Tras dropna(): perdidas {n_lost} filas ({100*n_lost/n_before:.1f}%)")
    print(f"   ✅ Filas útiles:       {n_after}")
    print(f"   Rango efectivo:       {df_close.index[0].strftime('%Y-%m-%d')} → {df_close.index[-1].strftime('%Y-%m-%d')}")
    print(f"   Años de datos:        {(df_close.index[-1] - df_close.index[0]).days / 365.25:.1f}")
    if n_after < 100:
        raise ValueError(f"Solo quedan {n_after} filas tras limpiar NaNs. Reduce el rango de fechas.")

    df_pct = df_close.pct_change().fillna(0)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    # Evitar división por cero o valores extremos
    df_close_safe = df_close.replace(0, np.nan).ffill().bfill()
    df_ratio = (df_mean_5 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)

    market_matrix = np.hstack([df_close.values, df_pct.values, df_ratio.values])
    labels_matrix = df_pct.shift(-1).fillna(0).values

    # 🟢 Verificar integridad numérica tras el denoising
    if denoise:
        print(f"🌀 Denoising ({denoise_method}) sobre {market_matrix.shape[1]} features...")
        market_matrix = denoise_market_matrix(market_matrix, method=denoise_method)

    # Reemplazar cualquier Inf/NaN residual
    n_bad = np.isnan(market_matrix).sum() + np.isinf(market_matrix).sum()
    if n_bad > 0:
        print(f"   ⚠️  Corrigiendo {n_bad} valores Inf/NaN residuales")
        market_matrix = np.nan_to_num(market_matrix, nan=0.0, posinf=1.0, neginf=-1.0)

    # Clip extreme values (99.9% percentile)
    upper = np.percentile(np.abs(market_matrix), 99.9)
    if upper > 0:
        n_clipped = (np.abs(market_matrix) > upper).sum()
        if n_clipped > 0:
            print(f"   ⚠️  Clippeando {n_clipped} valores extremos (>P99.9 = {upper:.2f})")
            market_matrix = np.clip(market_matrix, -upper, upper)

    # Resumen final de la matrix
    print(f"\n   📐 Matrix final:")
    print(f"      Dimensiones:       {market_matrix.shape[0]} filas × {market_matrix.shape[1]} columnas")
    print(f"      Features:          {market_matrix.shape[1]} (close={len(cryptos)}, pct={len(cryptos)}, ratio={len(cryptos)})")
    print(f"      Rango temporal:    {df_close.index[0].strftime('%Y-%m-%d')} → {df_close.index[-1].strftime('%Y-%m-%d')}")
    print(f"      Días totales:      {len(market_matrix)}")
    print(f"      Años cubiertos:    {(df_close.index[-1] - df_close.index[0]).days / 365.25:.1f}")
    n_nan_final = np.isnan(market_matrix).sum()
    n_inf_final = np.isinf(market_matrix).sum()
    print(f"      NaN restantes:     {n_nan_final}")
    print(f"      Inf restantes:     {n_inf_final}")
    print(f"      Valores extremos:  >P99.9 clipeados")
    print(f"      Stats rápidos:     μ={np.mean(market_matrix):.4f}  "
          f"σ={np.std(market_matrix):.4f}  "
          f"min={np.min(market_matrix):.4f}  max={np.max(market_matrix):.4f}")
    print(f"\n{'='*62}")

    return market_matrix, labels_matrix, df_close.index


def make_sliding_windows(market_matrix, labels_matrix, lookback=30):
    X, y = [], []
    for i in range(len(market_matrix) - lookback - 1):
        X.append(market_matrix[i: i + lookback, :])
        y.append(labels_matrix[i + lookback, :])
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)


def split_chronologically(X, y, train_frac=0.70, val_frac=0.15):
    n = len(X)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))
    return (X[:train_end], y[:train_end]), \
           (X[train_end:val_end], y[train_end:val_end]), \
           (X[val_end:], y[val_end:])


# =====================================================================
# 4. ENTRENAMIENTO (compatible con Optuna)
# =====================================================================
def train_trial(model, train_loader, val_loader, epochs, lr, weight_decay,
                device, trial=None, patience=8):
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_val_loss = float("inf")
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
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
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

        # 🟢 Detectar NaN en val_loss → podar inmediatamente
        if math.isnan(val_loss) or math.isinf(val_loss):
            if trial is not None:
                raise optuna.TrialPruned()
            break

        if trial is not None:
            trial.report(val_loss, epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= patience:
            break

    return best_val_loss, history


def train_final(model, combined_loader, test_loader, epochs, lr, weight_decay,
                device, patience=15, model_path="best.pth"):
    """Reentreno completo con early stopping sobre el combinado."""
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_loss = float("inf")
    patience_counter = 0

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for bx, by in combined_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item()
        total_loss /= len(combined_loader)

        # 🟢 Detectar NaN → parar este reentreno
        if math.isnan(total_loss) or math.isinf(total_loss):
            break

        if total_loss < best_loss:
            best_loss = total_loss
            patience_counter = 0
            torch.save(model.state_dict(), model_path)
        else:
            patience_counter += 1

        if patience_counter >= patience:
            break

    model.load_state_dict(torch.load(model_path, weights_only=True))
    return model


# =====================================================================
# 5. EVALUACIÓN (backtesting completo)
# =====================================================================
def evaluate_trial(model, X_test, y_test, device):
    """Evalúa un modelo entrenado: test loss + backtesting + métricas."""
    model.eval()
    with torch.no_grad():
        preds = model(X_test.to(device)).cpu().numpy()
    real = y_test.numpy()

    test_loss = float(np.mean((preds - real) ** 2))

    # Top-1 Long: comprar el activo con mayor predicción, solo si es positiva
    best_asset = np.argmax(preds, axis=1)
    best_pred = np.max(preds, axis=1)
    strategy_returns = np.array([
        real[t, best_asset[t]] if best_pred[t] > 0 else 0.0
        for t in range(len(best_asset))
    ])
    strategy_returns -= 0.001
    benchmark_returns = np.mean(real, axis=1)

    equity_sfm = float(np.cumprod(1 + strategy_returns)[-1])
    equity_bm = float(np.cumprod(1 + benchmark_returns)[-1])

    sharpe = float(np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-10) * np.sqrt(252))
    direction_acc = float(np.mean((preds > 0) == (real > 0)))

    return {
        "test_loss": test_loss,
        "equity_final": equity_sfm,
        "benchmark_final": equity_bm,
        "sharpe": sharpe,
        "direction_acc": direction_acc,
        "outperformance": equity_sfm - equity_bm,
        "strategy_returns": strategy_returns,
        "benchmark_returns": benchmark_returns,
    }


# =====================================================================
# 6. OBJETIVO DE OPTUNA
# =====================================================================
def objective(trial, cryptos, market_train_scaled, labels_train,
              market_val_scaled, labels_val, input_dim, output_dim, device):
    hidden_dim = trial.suggest_int("hidden_dim", 32, 128, step=16)
    freq_components = trial.suggest_int("freq_components", 4, 20)
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    dropout_rate = trial.suggest_float("dropout_rate", 0.1, 0.5, step=0.05)
    batch_size = trial.suggest_categorical("batch_size", [16, 32])
    weight_decay = trial.suggest_float("weight_decay", 1e-5, 1e-3, log=True)
    lookback = trial.suggest_int("lookback", 15, 50, step=5)

    X_tr, y_tr = make_sliding_windows(market_train_scaled, labels_train, lookback=lookback)
    X_v, y_v = make_sliding_windows(market_val_scaled, labels_val, lookback=lookback)

    if len(X_tr) < 100 or len(X_v) < 20:
        raise optuna.TrialPruned()

    # ── Semilla dentro del trial para que cada trial sea reproducible ──
    torch.manual_seed(SEED + trial.number)

    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=batch_size, shuffle=False)
    val_loader = DataLoader(TensorDataset(X_v, y_v), batch_size=batch_size, shuffle=False)

    model = SFMModelRefined(input_dim, hidden_dim, freq_components, output_dim,
                            dropout_rate=dropout_rate).to(device)

    # Entrenar con early stopping por val_loss (estabilidad)
    best_val_loss, _ = train_trial(
        model, train_loader, val_loader,
        epochs=60, lr=lr, weight_decay=weight_decay,
        device=device, trial=trial, patience=8
    )

    # ── Evaluar Sharpe en validación ──
    model.eval()
    with torch.no_grad():
        preds = model(X_v.to(device)).cpu().numpy()
    real = y_v.numpy()

    # Estrategia Top-1 Long con filtro: solo comprar si la mejor predicción es positiva
    best_asset = np.argmax(preds, axis=1)
    best_pred = np.max(preds, axis=1)  # valor de la mejor predicción
    strategy_returns = np.array([
        real[t, best_asset[t]] if best_pred[t] > 0 else 0.0
        for t in range(len(best_asset))
    ])
    strategy_returns -= 0.001  # costes

    val_sharpe = float(np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-10) * np.sqrt(252))

    # Si el Sharpe es muy negativo (< -3), podar el trial
    if val_sharpe < -3.0:
        raise optuna.TrialPruned()

    return -val_sharpe  # Optuna minimiza → maximizar Sharpe


# =====================================================================
# 7. TOP-K EVALUATION: entrena y evalúa los K mejores trials
# =====================================================================
def evaluate_top_k(study, k, cryptos,
                   market_train_scaled, labels_train,
                   market_val_scaled, labels_val,
                   market_test_scaled, labels_test,
                   input_dim, output_dim, device, output_dir):
    """
    Ordena los K mejores trials por Sharpe en validación, los re-entrena
    sobre train+val y los evalúa en test. Devuelve estadísticas agregadas.
    """
    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    completed.sort(key=lambda t: t.value)  # menor t.value = mejor Sharpe (minimiza -Sharpe)
    top_k = completed[:k]

    print(f"\n   Evaluando Top-{k} trials (de {len(completed)} completados)...")
    print(f"   (ordenados por Sharpe en validación)")

    all_results = []
    for i, trial in enumerate(top_k):
        params = trial.params
        lookback = params["lookback"]
        batch_size = params["batch_size"]

        # El valor almacenado es -Sharpe_val; darle la vuelta para mostrar
        sharpe_val = -trial.value

        torch.manual_seed(SEED + 999 + i)

        X_tr, y_tr = make_sliding_windows(market_train_scaled, labels_train, lookback=lookback)
        X_v, y_v = make_sliding_windows(market_val_scaled, labels_val, lookback=lookback)
        X_combined = torch.cat([X_tr, X_v], dim=0)
        y_combined = torch.cat([y_tr, y_v], dim=0)
        X_te, y_te = make_sliding_windows(market_test_scaled, labels_test, lookback=lookback)

        combined_loader = DataLoader(TensorDataset(X_combined, y_combined),
                                     batch_size=batch_size, shuffle=False)

        model = SFMModelRefined(input_dim, params["hidden_dim"], params["freq_components"],
                                output_dim, dropout_rate=params["dropout_rate"]).to(device)

        model_path = os.path.join(output_dir, f"sfm_top{i+1}.pth")
        model = train_final(model, combined_loader, None,
                            epochs=100, lr=params["lr"],
                            weight_decay=params["weight_decay"],
                            device=device, patience=15, model_path=model_path)

        result = evaluate_trial(model, X_te, y_te, device)
        result["rank"] = i + 1
        result["sharpe_val"] = sharpe_val  # Sharpe en validación
        result["params"] = params
        all_results.append(result)

        print(f"     #{i+1}: Sharpe_val={sharpe_val:.2f}  "
              f"Sharpe_test={result['sharpe']:.2f}  Equity={result['equity_final']:.4f}x")

    # ── Estadísticas agregadas ──
    sharpe_values = [r["sharpe"] for r in all_results]
    equity_values = [r["equity_final"] for r in all_results]
    outperf_values = [r["outperformance"] for r in all_results]

    stats = {
        "n_top": k,
        "sharpe": {
            "mean": float(np.mean(sharpe_values)),
            "std": float(np.std(sharpe_values)),
            "min": float(np.min(sharpe_values)),
            "max": float(np.max(sharpe_values)),
            "values": sharpe_values,
        },
        "equity_final": {
            "mean": float(np.mean(equity_values)),
            "std": float(np.std(equity_values)),
            "min": float(np.min(equity_values)),
            "max": float(np.max(equity_values)),
            "values": equity_values,
        },
        "outperformance": {
            "mean": float(np.mean(outperf_values)),
            "std": float(np.std(outperf_values)),
            "values": outperf_values,
        },
        "trials": [
            {
                "rank": r["rank"],
                "val_loss": r["test_loss"],
                "sharpe": r["sharpe"],
                "equity_final": r["equity_final"],
                "outperformance": r["outperformance"],
                "params": {k: float(v) if isinstance(v, (np.floating,)) else v
                           for k, v in r["params"].items()},
            }
            for r in all_results
        ],
    }

    print(f"\n   📊 Estadísticas agregadas Top-{k}:")
    print(f"      Sharpe:      μ={stats['sharpe']['mean']:.2f}  "
          f"σ={stats['sharpe']['std']:.2f}  "
          f"[{stats['sharpe']['min']:.2f}, {stats['sharpe']['max']:.2f}]")
    print(f"      Equity:      μ={stats['equity_final']['mean']:.4f}x  "
          f"σ={stats['equity_final']['std']:.4f}  "
          f"[{stats['equity_final']['min']:.4f}x, {stats['equity_final']['max']:.4f}x]")

    return all_results, stats, top_k


# =====================================================================
# 8. WALK-FORWARD VALIDATION
# =====================================================================
def walk_forward_windows(n_total, n_windows=3, val_pct=0.10):
    """
    Genera ventanas de walk-forward secuenciales.
    Cada ventana: train=[0, train_end), val=[train_end, train_end+val_size),
                   test=[train_end+val_size, train_end+val_size+test_size)
    Las ventanas avanzan de forma que el rango de test sea contiguo y cubra
    la segunda mitad de los datos aproximadamente.
    """
    # Dejamos ~45% para la zona de test total, repartido en n_windows ventanas
    test_total_pct = 0.40
    test_size = int(n_total * test_total_pct / n_windows)
    val_size = int(n_total * val_pct)

    windows = []
    for w in range(n_windows):
        train_end = int(n_total * (0.15 + w * (test_total_pct / n_windows + val_pct)))
        if train_end + val_size + test_size > n_total:
            train_end = n_total - val_size - test_size
        if train_end < 100:
            continue
        windows.append({
            "train_end": train_end,
            "val_start": train_end,
            "val_end": train_end + val_size,
            "test_start": train_end + val_size,
            "test_end": min(train_end + val_size + test_size, n_total),
        })

    return windows


def run_walk_forward(cryptos, market_data, labels_data, study, output_dir,
                     input_dim, output_dim, device, scaler):
    """
    Ejecuta walk-forward validation usando los trials del estudio Optuna
    ya completado. Para cada ventana, evalúa el mejor trial en datos
    out-of-sample.
    """
    n_total = len(market_data)
    windows = walk_forward_windows(n_total, n_windows=3)

    print(f"\n🏃 Walk-Forward Validation ({len(windows)} ventanas):")

    wf_results = []
    for w, win in enumerate(windows):
        market_train_wf = market_data[:win["train_end"]]
        market_val_wf = market_data[win["val_start"]:win["val_end"]]
        market_test_wf = market_data[win["test_start"]:win["test_end"]]

        labels_train_wf = labels_data[:win["train_end"]]
        labels_val_wf = labels_data[win["val_start"]:win["val_end"]]
        labels_test_wf = labels_data[win["test_start"]:win["test_end"]]

        # Escalar (fit en train)
        scaler_wf = deepcopy(scaler)
        market_train_scaled = scaler_wf.fit_transform(market_train_wf)
        market_val_scaled = scaler_wf.transform(market_val_wf)
        market_test_scaled = scaler_wf.transform(market_test_wf)

        # Usar params del mejor trial de Optuna
        best_trial = study.best_trial
        params = best_trial.params
        lookback = params["lookback"]
        batch_size = params["batch_size"]

        torch.manual_seed(SEED + 1000 + w)

        X_tr, y_tr = make_sliding_windows(market_train_scaled, labels_train_wf, lookback=lookback)
        X_v, y_v = make_sliding_windows(market_val_scaled, labels_val_wf, lookback=lookback)
        X_combined = torch.cat([X_tr, X_v], dim=0)
        y_combined = torch.cat([y_tr, y_v], dim=0)
        X_te, y_te = make_sliding_windows(market_test_scaled, labels_test_wf, lookback=lookback)

        if len(X_te) < 10:
            print(f"   ⚠️  Ventana {w+1}: muy pocas muestras de test ({len(X_te)}), omitiendo")
            continue

        combined_loader = DataLoader(TensorDataset(X_combined, y_combined),
                                     batch_size=batch_size, shuffle=False)

        model = SFMModelRefined(input_dim, params["hidden_dim"], params["freq_components"],
                                output_dim, dropout_rate=params["dropout_rate"]).to(device)

        model_path = os.path.join(output_dir, f"sfm_wf_w{w+1}.pth")
        model = train_final(model, combined_loader, None,
                            epochs=100, lr=params["lr"],
                            weight_decay=params["weight_decay"],
                            device=device, patience=15, model_path=model_path)

        result = evaluate_trial(model, X_te, y_te, device)
        result["window"] = w + 1
        result["test_samples"] = len(X_te)
        result["test_range"] = f"{win['test_start']}:{win['test_end']}"
        # Almacenar curvas de equity para la gráfica
        result["sfm_equity_curve"] = np.cumprod(1 + result["strategy_returns"])
        result["bm_equity_curve"] = np.cumprod(1 + result["benchmark_returns"])
        wf_results.append(result)

        print(f"   Ventana {w+1}: test[{win['test_start']}:{win['test_end']}] "
              f"({len(X_te)} muestras)")
        print(f"      Sharpe={result['sharpe']:.2f}  "
              f"Equity={result['equity_final']:.4f}x  "
              f"Benchmark={result['benchmark_final']:.4f}x")

    # Estadísticas walk-forward
    if wf_results:
        sharpe_wf = [r["sharpe"] for r in wf_results]
        equity_wf = [r["equity_final"] for r in wf_results]
        print(f"\n   📊 Walk-Forward agregado:")
        print(f"      Sharpe:  μ={np.mean(sharpe_wf):.2f}  "
              f"σ={np.std(sharpe_wf):.2f}  "
              f"[{np.min(sharpe_wf):.2f}, {np.max(sharpe_wf):.2f}]")
        print(f"      Equity:  μ={np.mean(equity_wf):.4f}x  "
              f"σ={np.std(equity_wf):.4f}  "
              f"[{np.min(equity_wf):.4f}x, {np.max(equity_wf):.4f}x]")

    return wf_results


# =====================================================================
# 9. VISUALIZACIÓN
# =====================================================================
def _plot_distribution(study, output_dir):
    best = study.best_trial
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    # t.value = -Sharpe_val; dar la vuelta para mostrar Sharpe real
    sharpe_vals = [-t.value for t in study.trials if t.value is not None]
    best_sharpe = -best.value
    axes[0].hist(sharpe_vals, bins=30, edgecolor="black", alpha=0.7, color="steelblue")
    axes[0].axvline(best_sharpe, color="red", linestyle="--", label=f"Mejor: {best_sharpe:.2f}")
    axes[0].axvline(0, color="gray", linestyle=":", alpha=0.7)
    axes[0].set_xlabel("Sharpe Ratio (validación)")
    axes[0].set_ylabel("Frecuencia")
    axes[0].set_title("Distribución de Sharpe en Validación")
    axes[0].legend()

    n_complete = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE)
    n_pruned = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.PRUNED)
    axes[1].bar(["Completados", "Pruned"], [n_complete, n_pruned],
                color=["green", "orange"], edgecolor="black")
    axes[1].set_ylabel("Nº de trials")
    axes[1].set_title(f"Trials: {n_complete + n_pruned} totales")

    plt.suptitle(f"Optuna — Mejor Sharpe en Val: {best_sharpe:.2f}", fontsize=14)
    plt.tight_layout()
    path = os.path.join(output_dir, "optuna_distribution.png")
    plt.savefig(path, dpi=150)
    plt.close()
    if os.path.exists(path):
        print(f"   📊 optuna_distribution.png ({os.path.getsize(path)} bytes)")


def plot_top_k_results(top_results, stats, output_dir):
    """Gráfica de barras con los Sharpe de los Top-K trials."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Sharpe por trial
    sharpe_vals = [r["sharpe"] for r in top_results]
    labels = [f"#{r['rank']}" for r in top_results]
    colors = ["green" if s > 0 else "red" for s in sharpe_vals]
    axes[0].bar(labels, sharpe_vals, color=colors, edgecolor="black", alpha=0.8)
    axes[0].axhline(stats["sharpe"]["mean"], color="blue", linestyle="--",
                    label=f'Media: {stats["sharpe"]["mean"]:.2f}')
    axes[0].set_ylabel("Sharpe Ratio")
    axes[0].set_title(f"Sharpe por Trial (Top-{len(top_results)})")
    axes[0].legend()
    axes[0].grid(True, axis="y", linestyle=":", alpha=0.6)

    # Equity final por trial
    equity_vals = [r["equity_final"] for r in top_results]
    colors2 = ["green" if e > 1.0 else "red" for e in equity_vals]
    axes[1].bar(labels, equity_vals, color=colors2, edgecolor="black", alpha=0.8)
    axes[1].axhline(stats["equity_final"]["mean"], color="blue", linestyle="--",
                    label=f'Media: {stats["equity_final"]["mean"]:.4f}x')
    axes[1].axhline(1.0, color="gray", linestyle=":", alpha=0.7, label="Punto muerto")
    axes[1].set_ylabel("Equity Final (x)")
    axes[1].set_title("Equity Final por Trial")
    axes[1].legend()
    axes[1].grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.suptitle(f"Top-{len(top_results)} — Sharpe μ={stats['sharpe']['mean']:.2f}  "
                 f"σ={stats['sharpe']['std']:.2f}", fontsize=14)
    plt.tight_layout()
    path = os.path.join(output_dir, "top_k_results.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"   📊 top_k_results.png ({os.path.getsize(path)} bytes)")


def plot_walk_forward(wf_results, output_dir):
    """Gráfica de walk-forward: Sharpe y equity por ventana."""
    if not wf_results:
        return
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    windows = [f"W{r['window']}" for r in wf_results]
    sharpe_wf = [r["sharpe"] for r in wf_results]
    equity_wf = [r["equity_final"] for r in wf_results]
    benchmark_wf = [r["benchmark_final"] for r in wf_results]

    colors_s = ["green" if s > 0 else "red" for s in sharpe_wf]
    axes[0].bar(windows, sharpe_wf, color=colors_s, edgecolor="black", alpha=0.8)
    axes[0].axhline(0, color="gray", linestyle="--")
    axes[0].set_ylabel("Sharpe Ratio")
    axes[0].set_title("Walk-Forward: Sharpe por Ventana")
    axes[0].grid(True, axis="y", linestyle=":", alpha=0.6)

    x = np.arange(len(windows))
    width = 0.35
    axes[1].bar(x - width/2, equity_wf, width, label="SFM", color="#1f77b4", alpha=0.8)
    axes[1].bar(x + width/2, benchmark_wf, width, label="Benchmark", color="#7f7f7f", alpha=0.6)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(windows)
    axes[1].axhline(1.0, color="gray", linestyle=":", alpha=0.7)
    axes[1].set_ylabel("Equity Final (x)")
    axes[1].set_title("Walk-Forward: SFM vs Benchmark")
    axes[1].legend()
    axes[1].grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.suptitle("Walk-Forward Validation", fontsize=14)
    plt.tight_layout()
    path = os.path.join(output_dir, "walk_forward.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"   📊 walk_forward.png ({os.path.getsize(path)} bytes)")

    # ── Gráfica de curvas de equity: SFM vs Baseline por ventana ──
    n_wf = len(wf_results)
    colors_sfm = ['#2196F3', '#4CAF50', '#FF9800']
    fig2, axes2 = plt.subplots(1, n_wf, figsize=(6 * n_wf, 4.5), sharey=False)
    if n_wf == 1:
        axes2 = [axes2]
    fig2.suptitle('Walk-Forward: SFM vs Baseline — Curvas de Equity por Ventana',
                  fontsize=14, fontweight='bold', y=1.02)

    for i, r in enumerate(wf_results):
        ax = axes2[i]
        sfm_curve = r["sfm_equity_curve"]
        bm_curve = r["bm_equity_curve"]
        x_days = np.arange(len(sfm_curve))

        sfm_line, = ax.plot(x_days, sfm_curve, color=colors_sfm[i % len(colors_sfm)],
                            linewidth=2.0, label='SFM')
        bm_line, = ax.plot(x_days, bm_curve, color='#888888', linestyle='--',
                           linewidth=1.5, alpha=0.7, label='Baseline')
        ax.fill_between(x_days, bm_curve, sfm_curve, alpha=0.08,
                        color=colors_sfm[i % len(colors_sfm)])

        # Anotaciones de Sharpe y equity final
        sfm_sharpe = r['sharpe']
        bm_sharpe_val = float(np.mean(r['benchmark_returns']) /
                              (np.std(r['benchmark_returns']) + 1e-10) * np.sqrt(252))
        label = (f'SFM Sharpe: {sfm_sharpe:.2f}   |   '
                 f'Equity: {r["equity_final"]:.2f}x')
        ax.text(0.97, 0.12, label, transform=ax.transAxes, fontsize=9,
                ha='right', va='bottom', color=colors_sfm[i % len(colors_sfm)],
                fontweight='bold',
                bbox=dict(facecolor='white', edgecolor=colors_sfm[i % len(colors_sfm)],
                          alpha=0.85, boxstyle='round,pad=0.4'))
        label_bm = (f'Baseline Sharpe: {bm_sharpe_val:.2f}   |   '
                    f'Equity: {r["benchmark_final"]:.2f}x')
        ax.text(0.97, 0.02, label_bm, transform=ax.transAxes, fontsize=9,
                ha='right', va='bottom', color='#666666', fontweight='bold',
                bbox=dict(facecolor='white', edgecolor='#888888', alpha=0.85,
                          boxstyle='round,pad=0.4'))

        ax.set_title(f'Ventana {r["window"]}  ({r["test_samples"]} muestras)',
                     fontsize=12, fontweight='bold', pad=8)
        ax.set_xlabel('Día de test', fontsize=9)
        ax.set_ylabel('Equidad acumulada', fontsize=9)
        ax.axhline(y=1.0, color='#cccccc', linewidth=0.8, linestyle=':')
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

    fig2.legend([sfm_line, bm_line], ['SFM', 'Baseline'],
                loc='upper center', bbox_to_anchor=(0.5, -0.02),
                ncol=2, fontsize=11, frameon=True)
    plt.tight_layout()
    path2 = os.path.join(output_dir, "walk_forward_equity.png")
    plt.savefig(path2, dpi=150)
    plt.close()
    print(f"   📊 walk_forward_equity.png ({os.path.getsize(path2)} bytes)")


# =====================================================================
# 10. PIPELINE PRINCIPAL
# =====================================================================
if __name__ == "__main__":
    # ── Configuración ──
    CRYPTOS = ['btc', 'eth', 'sol', 'xlm', 'ada']
    DENOISE = True
    DENOISE_METHOD = "wavelet"
    N_TRIALS = 100                    # más trials = convergencia más estable
    N_EPOCHS_FINAL = 100
    PATIENCE_FINAL = 15
    TOP_K = 5                         # cuántos mejores trials evaluar
    DO_WALK_FORWARD = True            # walk-forward validation
    N_WALK_WINDOWS = 3                # número de ventanas walk-forward
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output/optuna_sfm_v4")

    print("=" * 65)
    print("🧠 qlib_sfm_pipeline.v4.py — SFM + Wavelet + Optuna + Top-K + Walk-Forward")
    print("=" * 65)
    print(f"   Cryptos: {CRYPTOS}")
    print(f"   Denoising: {DENOISE_METHOD if DENOISE else 'OFF'}")
    print(f"   Trials Optuna: {N_TRIALS}  |  Top-K: {TOP_K}  |  Walk-Forward: {N_WALK_WINDOWS} ventanas")
    print(f"   Seed: {SEED} (reproducible)")
    print(f"   PyWavelets: {'✓' if HAS_PYWT else '✗ → Savgol'}")
    print(f"   Optuna:     {'✓' if HAS_OPTUNA else '✗'}")
    if not HAS_OPTUNA:
        print("   ⚠️  Instala optuna: pip install optuna")
        exit(1)
    print("=" * 65)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Qlib ──
    qlib.init(provider_uri='/mnt/e/src/agent_qlib/data/qlib', region=REG_US)

    # ── Carga de datos ──
    print("\n📥 Cargando datos desde Qlib...")
    market_data, labels_data, dates_idx = load_and_process_crypto_data(
        CRYPTOS, "2018-01-01", "2026-06-01",
        denoise=DENOISE, denoise_method=DENOISE_METHOD
    )

    input_dim = market_data.shape[1]
    output_dim = len(CRYPTOS)
    n_total = len(market_data)
    print(f"\n{'='*62}")

    # ── Split 70/15/15 ──
    train_end = int(n_total * 0.70)
    val_end = int(n_total * 0.85)

    market_train = market_data[:train_end]
    market_val = market_data[train_end:val_end]
    market_test = market_data[val_end:]

    labels_train = labels_data[:train_end]
    labels_val = labels_data[train_end:val_end]
    labels_test = labels_data[val_end:]

    # ── Diagnóstico del split ──
    print("📊 SPLIT TEMPORAL")
    print("=" * 62)
    print(f"   {'Partición':<14} {'Muestras':<10} {'Rango':<20}   {'Ratio':<8}")
    print(f"   {'─'*14} {'─'*10} {'─'*20}   {'─'*8}")
    for name, data_start, data_end, data_len in [
        ("TRAIN", 0, train_end, len(market_train)),
        ("VAL",   train_end, val_end, len(market_val)),
        ("TEST",  val_end, n_total, len(market_test)),
    ]:
        d_start = dates_idx[min(data_start, len(dates_idx)-1)]
        d_end   = dates_idx[min(max(0, data_end-1), len(dates_idx)-1)]
        pct = 100 * data_len / n_total
        print(f"   {name:<14} {data_len:<10} {d_start.strftime('%Y-%m-%d')} → {d_end.strftime('%Y-%m-%d')}   {pct:.1f}%")
    print(f"   {'─'*14} {'─'*10} {'─'*20}   {'─'*8}")
    print(f"   {'TOTAL':<14} {n_total:<10} {dates_idx[0].strftime('%Y-%m-%d')} → {dates_idx[-1].strftime('%Y-%m-%d')}   100.0%")
    print(f"{'='*62}")

    # ── Escalado ──

    # ── Escalado ──
    scaler = MinMaxScaler(feature_range=(-1, 1))
    market_train_scaled = scaler.fit_transform(market_train)
    market_val_scaled = scaler.transform(market_val)
    market_test_scaled = scaler.transform(market_test)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"   Device: {device}")

    # =================================================================
    # FASE 1: OPTIMIZACIÓN CON OPTUNA
    # =================================================================
    print("\n" + "=" * 65)
    print("🔬 FASE 1: BÚSQUEDA DE HIPERPARÁMETROS CON OPTUNA")
    print("=" * 65)
    print(f"   Trials: {N_TRIALS}  |  Sampler: TPESampler(seed={SEED})  |  Pruner: MedianPruner")

    study = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=SEED),
        pruner=MedianPruner(n_startup_trials=10, n_warmup_steps=5, interval_steps=1),
        study_name="sfm_optuna_v4",
        storage=None
    )

    start_time = time.time()

    try:
        study.optimize(
            lambda trial: objective(
                trial, CRYPTOS,
                market_train_scaled, labels_train,
                market_val_scaled, labels_val,
                input_dim, output_dim, device
            ),
            n_trials=N_TRIALS,
            show_progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n⚠️  Interrumpido")

    elapsed = time.time() - start_time
    print(f"\n⏱️  {elapsed/60:.1f} min")

    best_trial = study.best_trial
    best_sharpe_val = -best_trial.value
    print(f"\n🏆 MEJOR TRIAL (por Sharpe en validación):")
    print(f"   Sharpe Val: {best_sharpe_val:.2f}")
    for key, val in best_trial.params.items():
        print(f"   {key}: {val}")

    # Guardar estudio
    n_complete = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE)
    n_pruned = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.PRUNED)
    study_results = {
        "best_sharpe_val": best_sharpe_val,
        "best_params": best_trial.params,
        "n_trials": len(study.trials),
        "n_complete": n_complete,
        "n_pruned": n_pruned,
        "elapsed_min": elapsed / 60,
        "seed": SEED,
    }
    with open(os.path.join(OUTPUT_DIR, "study_results.json"), "w") as f:
        json.dump(study_results, f, indent=2)
    print(f"\n💾 study_results.json guardado")

    # ── Visualización estudio ──
    print("\n📊 Generando visualizaciones...")
    try:
        _plot_distribution(study, OUTPUT_DIR)
    except Exception as e:
        print(f"   ⚠️  Distribución: {e}")

    # =================================================================
    # FASE 2: TOP-K EVALUATION
    # =================================================================
    print("\n" + "=" * 65)
    print("🎯 FASE 2: TOP-K EVALUATION (entrenar + evaluar K mejores trials)")
    print("=" * 65)

    top_results, stats, top_trials = evaluate_top_k(
        study, TOP_K, CRYPTOS,
        market_train_scaled, labels_train,
        market_val_scaled, labels_val,
        market_test_scaled, labels_test,
        input_dim, output_dim, device, OUTPUT_DIR
    )

    # Guardar resultados top-k
    with open(os.path.join(OUTPUT_DIR, "top_k_results.json"), "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print(f"💾 top_k_results.json guardado")

    # Gráfica top-k
    try:
        plot_top_k_results(top_results, stats, OUTPUT_DIR)
    except Exception as e:
        print(f"   ⚠️  Top-K plot: {e}")

    # =================================================================
    # FASE 3: WALK-FORWARD VALIDATION
    # =================================================================
    if DO_WALK_FORWARD:
        print("\n" + "=" * 65)
        print("🏃 FASE 3: WALK-FORWARD VALIDATION")
        print("=" * 65)

        wf_results = run_walk_forward(
            CRYPTOS, market_data, labels_data, study, OUTPUT_DIR,
            input_dim, output_dim, device, scaler
        )

        if wf_results:
            wf_stats = {
                "n_windows": len(wf_results),
                "sharpe": {
                    "mean": float(np.mean([r["sharpe"] for r in wf_results])),
                    "std": float(np.std([r["sharpe"] for r in wf_results])),
                    "values": [r["sharpe"] for r in wf_results],
                },
                "equity_final": {
                    "mean": float(np.mean([r["equity_final"] for r in wf_results])),
                    "std": float(np.std([r["equity_final"] for r in wf_results])),
                    "values": [r["equity_final"] for r in wf_results],
                },
            }
            with open(os.path.join(OUTPUT_DIR, "walk_forward_results.json"), "w") as f:
                json.dump(wf_stats, f, indent=2, default=str)
            print(f"💾 walk_forward_results.json guardado")

            try:
                plot_walk_forward(wf_results, OUTPUT_DIR)
            except Exception as e:
                print(f"   ⚠️  WF plot: {e}")

    # =================================================================
    # RESUMEN FINAL
    # =================================================================
    print("\n" + "=" * 65)
    print("📋 RESUMEN V4")
    print("=" * 65)
    print(f"\n   🔬 Optuna:")
    print(f"      Trials: {len(study.trials)} ({n_complete} OK, {n_pruned} pruned)")
    print(f"      Mejor Sharpe en val: {best_sharpe_val:.2f}")
    print(f"      Tiempo: {elapsed/60:.1f} min")
    print(f"\n   🎯 Top-{TOP_K} en test:")
    print(f"      Sharpe:  μ={stats['sharpe']['mean']:.2f}  σ={stats['sharpe']['std']:.2f}")
    print(f"               min={stats['sharpe']['min']:.2f}  max={stats['sharpe']['max']:.2f}")
    print(f"      Equity:  μ={stats['equity_final']['mean']:.4f}x  σ={stats['equity_final']['std']:.4f}x")
    print(f"               min={stats['equity_final']['min']:.4f}x  max={stats['equity_final']['max']:.4f}x")

    if DO_WALK_FORWARD and wf_results:
        wf_sharpe_mean = np.mean([r["sharpe"] for r in wf_results])
        wf_equity_mean = np.mean([r["equity_final"] for r in wf_results])
        print(f"\n   🏃 Walk-Forward ({len(wf_results)} ventanas):")
        print(f"      Sharpe:  μ={wf_sharpe_mean:.2f}  σ={np.std([r['sharpe'] for r in wf_results]):.2f}")
        print(f"      Equity:  μ={wf_equity_mean:.4f}x  σ={np.std([r['equity_final'] for r in wf_results]):.4f}x")

    print(f"\n   📁 {OUTPUT_DIR}/")
    print(f"   ├── study_results.json")
    print(f"   ├── top_k_results.json")
    print(f"   ├── top_k_results.png")
    if DO_WALK_FORWARD:
        print(f"   ├── walk_forward_results.json")
        print(f"   ├── walk_forward.png")
        print(f"   ├── walk_forward_equity.png")
    print(f"   ├── optuna_distribution.png")
    print(f"   └── sfm_top*.pth (modelos)")

    print("\n✅ Pipeline v4 completado.")
