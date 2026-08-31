"""
qlib_sfm_pipeline.v6.py - SFM + Optuna + Top-K + Walk-Forward con TODO el historico

Mejoras respecto a v4:
  - Split 60/20/20 en lugar de 70/15/15 para absorber mas anos de historia
  - Lookback ampliado: se optimiza entre 20 y 90 dias (antes 15 a 50)
  - Semilla por trial para reproducibilidad exacta
  - Denoising global DESACTIVADO (leak conocido)
  - Clipping y scaling ajustados SOLO con train (causal)
  - Lee datos del provider Qlib generado con convert_crypto_qlib.py
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
from research_utils import (
    apply_clip_bounds,
    evaluate_cost_scenarios,
    fit_clip_bounds,
    performance_metrics,
    top1_long_returns,
)

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

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


class SFMCellRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, dropout_rate=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.K = freq_components
        self.W_i = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_f = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_o = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_z = nn.Linear(input_dim + hidden_dim, hidden_dim)
        self.W_omega = nn.Parameter(torch.randn(hidden_dim, hidden_dim))
        self.dropout = nn.Dropout(dropout_rate)

    def forward(self, x, states):
        h_prev, c_prev = states
        combined = torch.cat([x, h_prev], dim=-1)
        i = torch.sigmoid(self.W_i(combined))
        f = torch.sigmoid(self.W_f(combined))
        o = torch.sigmoid(self.W_o(combined))
        z = torch.tanh(self.W_z(combined))
        c = f * c_prev + i * z
        omega = torch.softmax(self.W_omega, dim=-1)
        freq_adapt = (omega * c.unsqueeze(-1)).sum(dim=1)
        h = o * torch.tanh(c + freq_adapt)
        h = self.dropout(h)
        return h, c


class SFMModelRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, output_dim, dropout_rate=0.2):
        super().__init__()
        self.cell = SFMCellRefined(input_dim, hidden_dim, freq_components, dropout_rate)
        self.fc_out = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        batch_size, seq_len, _ = x.shape
        h = torch.zeros(batch_size, self.cell.hidden_dim, device=x.device)
        c = torch.zeros(batch_size, self.cell.hidden_dim, device=x.device)
        for t in range(seq_len):
            h, c = self.cell(x[:, t, :], (h, c))
        return self.fc_out(h)


def load_and_process_crypto_data(cryptos, start_date, end_date):
    """Carga cada cripto por separado para respetar su maximo historico individual.

    A diferencia de la version anterior que cargaba todas juntas (y Qlib alineaba
    al rango comun), esta funcion lee instrumento por instrumento y combina
    manteniendo NaN donde una moneda aun no existia.
    """
    print(f"   Cargando {len(cryptos)} criptos desde {start_date} hasta {end_date}...")
    print(f"   (leyendo cada moneda por separado para respetar su historia maxima)")

    close_dict = {}
    for c in cryptos:
        df_c = D.features([c], ["$close"], start_time=start_date, end_time=end_date)
        if df_c is None or df_c.empty:
            print(f"     {c}: SIN DATOS")
            continue
        df_c = df_c.reset_index()
        series = df_c.pivot(index="datetime", columns="instrument", values="$close")[c]
        close_dict[c] = series
        n_vals = series.notna().sum()
        first = series.first_valid_index()
        last = series.last_valid_index()
        fstr = first.strftime('%Y-%m-%d') if first is not None else '---'
        lstr = last.strftime('%Y-%m-%d') if last is not None else '---'
        print(f"     {c:>5s}: {n_vals:>5d} valores [{fstr} -> {lstr}]")

    if not close_dict:
        raise ValueError("No se pudo cargar ninguna cripto")

    # Combinar respetando el rango individual de cada una
    df_close = pd.DataFrame(close_dict).sort_index()
    print(f"\n{'='*62}")
    print("DIAGNOSTICO DE DATOS (combinados)")
    print("=" * 62)
    print(f"   Rango total:          {df_close.index[0].strftime('%Y-%m-%d')} -> {df_close.index[-1].strftime('%Y-%m-%d')}")
    print(f"   Filas totales:        {len(df_close)}")
    anos = (df_close.index[-1] - df_close.index[0]).days / 365.25
    print(f"   Anos cubiertos:       {anos:.1f}")
    for c in cryptos:
        n_vals = df_close[c].notna().sum()
        n_nan = df_close[c].isna().sum()
        first = df_close[c].first_valid_index()
        last = df_close[c].last_valid_index()
        fstr = first.strftime('%Y-%m-%d') if first is not None else '---'
        lstr = last.strftime('%Y-%m-%d') if last is not None else '---'
        na_pct = 100 * n_nan / len(df_close)
        print(f"     {c:>5s}: {n_vals:>5d} valores, {n_nan:>5d} NaN ({na_pct:5.1f}%)  [{fstr} -> {lstr}]")

    if len(df_close) < 100:
        raise ValueError(f"Solo {len(df_close)} filas tras combinar.")

    # Features: precio, retorno diario, ratio media 5d / precio
    df_pct = df_close.pct_change().fillna(0)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_close_safe = df_close.replace(0, np.nan).ffill().bfill()
    df_ratio = (df_mean_5 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)

    market_matrix = np.hstack([df_close.values, df_pct.values, df_ratio.values])
    labels_matrix = df_pct.shift(-1).fillna(0).values

    n_bad = np.isnan(market_matrix).sum() + np.isinf(market_matrix).sum()
    if n_bad > 0:
        print(f"   Corrigiendo {n_bad} valores Inf/NaN residuales")
        market_matrix = np.nan_to_num(market_matrix, nan=0.0, posinf=1.0, neginf=-1.0)

    n_features = market_matrix.shape[1]
    print(f"\n   Matrix final: {market_matrix.shape[0]} filas x {n_features} columnas")
    print(f"   Anos cubiertos:    {anos:.1f}")
    print(f"{'='*62}")
    return market_matrix, labels_matrix, df_close.index


def make_sliding_windows(market_matrix, labels_matrix, lookback=30):
    X, y = [], []
    for i in range(len(market_matrix) - lookback - 1):
        X.append(market_matrix[i: i + lookback, :])
        y.append(labels_matrix[i + lookback, :])
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)


def train_trial(model, train_loader, val_loader, epochs, lr, weight_decay,
                device, trial=None, patience=8):
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    best_val_loss = float("inf")
    patience_counter = 0
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
    return best_val_loss, {"train": [], "val": []}


def train_final(model, combined_loader, test_loader, epochs, lr, weight_decay,
                device, patience=15, model_path="best.pth"):
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


def evaluate_trial(model, X_test, y_test, device, one_way_costs=None):
    model.eval()
    with torch.no_grad():
        preds = model(X_test.to(device)).cpu().numpy()
    real = y_test.numpy()
    test_loss = float(np.mean((preds - real) ** 2))
    cost_scenarios = evaluate_cost_scenarios(preds, real, periods_per_year=365)
    strategy_returns, positions = top1_long_returns(
        preds, real, transaction_cost=0.001, half_spread=0.0002, slippage=0.0003,
    )
    benchmark_returns = np.mean(real, axis=1)
    metrics = performance_metrics(strategy_returns, periods_per_year=365)
    equity_sfm = metrics["equity_final"]
    equity_bm = float(np.cumprod(1 + benchmark_returns)[-1])
    sharpe = metrics["sharpe"]
    direction_acc = float(np.mean((preds > 0) == (real > 0)))
    turnover = float(np.mean(positions[1:] != positions[:-1])) if len(positions) > 1 else 0.0
    calibrated_cost_metrics = None
    if one_way_costs is not None:
        calibrated_returns, _ = top1_long_returns(
            preds, real, one_way_costs=np.asarray(one_way_costs, dtype=float)
        )
        calibrated_cost_metrics = performance_metrics(calibrated_returns, periods_per_year=365)
    return {
        "test_loss": test_loss, "equity_final": equity_sfm, "benchmark_final": equity_bm,
        "sharpe": sharpe, "direction_acc": direction_acc, "max_drawdown": metrics["max_drawdown"],
        "turnover": turnover, "sortino": metrics["sortino"], "calmar": metrics["calmar"],
        "var_95": metrics["var_95"], "cvar_95": metrics["cvar_95"],
        "cost_scenarios": cost_scenarios, "calibrated_cost_metrics": calibrated_cost_metrics,
        "outperformance": equity_sfm - equity_bm,
        "strategy_returns": strategy_returns, "benchmark_returns": benchmark_returns,
    }


def objective(trial, cryptos, market_train_scaled, labels_train,
              market_val_scaled, labels_val, input_dim, output_dim, device):
    hidden_dim = trial.suggest_int("hidden_dim", 32, 128, step=16)
    freq_components = trial.suggest_int("freq_components", 4, 20)
    lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
    dropout_rate = trial.suggest_float("dropout_rate", 0.1, 0.5, step=0.05)
    batch_size = trial.suggest_categorical("batch_size", [16, 32])
    weight_decay = trial.suggest_float("weight_decay", 1e-5, 1e-3, log=True)
    lookback = trial.suggest_int("lookback", 20, 90, step=5)
    X_tr, y_tr = make_sliding_windows(market_train_scaled, labels_train, lookback=lookback)
    X_v, y_v = make_sliding_windows(market_val_scaled, labels_val, lookback=lookback)
    if len(X_tr) < 100 or len(X_v) < 20:
        raise optuna.TrialPruned()
    torch.manual_seed(SEED + trial.number)
    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=batch_size, shuffle=False)
    val_loader = DataLoader(TensorDataset(X_v, y_v), batch_size=batch_size, shuffle=False)
    model = SFMModelRefined(input_dim, hidden_dim, freq_components, output_dim,
                            dropout_rate=dropout_rate).to(device)
    train_trial(model, train_loader, val_loader,
                epochs=int(os.getenv("CRYPTO_TRIAL_EPOCHS", "60")), lr=lr,
                weight_decay=weight_decay, device=device, trial=trial, patience=8)
    model.eval()
    with torch.no_grad():
        preds = model(X_v.to(device)).cpu().numpy()
    real = y_v.numpy()
    strategy_returns, _ = top1_long_returns(
        preds, real, transaction_cost=0.001, half_spread=0.0002, slippage=0.0003,
    )
    val_sharpe = performance_metrics(strategy_returns, periods_per_year=365)["sharpe"]
    if val_sharpe < -3.0:
        raise optuna.TrialPruned()
    return -val_sharpe


def evaluate_top_k(study, k, cryptos, market_train_scaled, labels_train,
                   market_val_scaled, labels_val, market_test_scaled, labels_test,
                   input_dim, output_dim, device, output_dir):
    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    completed.sort(key=lambda t: t.value)
    top_k = completed[:k]
    print(f"\n   Evaluando Top-{k} trials (de {len(completed)} completados)...")
    all_results = []
    for i, trial in enumerate(top_k):
        params = trial.params
        lookback = params["lookback"]
        batch_size = params["batch_size"]
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
                            epochs=int(os.getenv("CRYPTO_FINAL_EPOCHS", "100")), lr=params["lr"],
                            weight_decay=params["weight_decay"],
                            device=device, patience=15, model_path=model_path)
        result = evaluate_trial(model, X_te, y_te, device)
        result["rank"] = i + 1
        result["sharpe_val"] = sharpe_val
        result["params"] = params
        all_results.append(result)
        print(f"     #{i+1}: Sharpe_val={sharpe_val:.2f}  "
              f"Sharpe_test={result['sharpe']:.2f}  Equity={result['equity_final']:.4f}x")
    sharpe_values = [r["sharpe"] for r in all_results]
    equity_values = [r["equity_final"] for r in all_results]
    stats = {
        "n_top": k,
        "sharpe": {"mean": float(np.mean(sharpe_values)), "std": float(np.std(sharpe_values)),
                   "min": float(np.min(sharpe_values)), "max": float(np.max(sharpe_values)),
                   "values": sharpe_values},
        "equity_final": {"mean": float(np.mean(equity_values)), "std": float(np.std(equity_values)),
                         "min": float(np.min(equity_values)), "max": float(np.max(equity_values)),
                         "values": equity_values},
        "trials": [{"rank": r["rank"], "sharpe": r["sharpe"], "equity_final": r["equity_final"],
                    "params": {k: float(v) if isinstance(v, (np.floating,)) else v
                               for k, v in r["params"].items()}}
                   for r in all_results],
    }
    print(f"\n   Top-{k}: Sharpe mu={stats['sharpe']['mean']:.2f} sigma={stats['sharpe']['std']:.2f}")
    return all_results, stats, top_k


def walk_forward_windows(n_total, n_windows=3, val_pct=0.10):
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
            "train_end": train_end, "val_start": train_end,
            "val_end": train_end + val_size,
            "test_start": train_end + val_size,
            "test_end": min(train_end + val_size + test_size, n_total),
        })
    return windows


def run_walk_forward(cryptos, market_data, labels_data, study, output_dir,
                     input_dim, output_dim, device, scaler):
    n_total = len(market_data)
    windows = walk_forward_windows(n_total, n_windows=3)
    print(f"\nWalk-Forward Validation ({len(windows)} ventanas):")
    wf_results = []
    for w, win in enumerate(windows):
        market_train_wf = market_data[:win["train_end"]]
        market_val_wf = market_data[win["val_start"]:win["val_end"]]
        market_test_wf = market_data[win["test_start"]:win["test_end"]]
        labels_train_wf = labels_data[:win["train_end"]]
        labels_val_wf = labels_data[win["val_start"]:win["val_end"]]
        labels_test_wf = labels_data[win["test_start"]:win["test_end"]]
        clip_bounds_wf = fit_clip_bounds(market_train_wf)
        market_train_wf = apply_clip_bounds(market_train_wf, clip_bounds_wf)
        market_val_wf = apply_clip_bounds(market_val_wf, clip_bounds_wf)
        market_test_wf = apply_clip_bounds(market_test_wf, clip_bounds_wf)
        scaler_wf = deepcopy(scaler)
        market_train_scaled = scaler_wf.fit_transform(market_train_wf)
        market_val_scaled = scaler_wf.transform(market_val_wf)
        market_test_scaled = scaler_wf.transform(market_test_wf)
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
            print(f"   Ventana {w+1}: pocas muestras ({len(X_te)}), omitiendo")
            continue
        combined_loader = DataLoader(TensorDataset(X_combined, y_combined),
                                     batch_size=batch_size, shuffle=False)
        model = SFMModelRefined(input_dim, params["hidden_dim"], params["freq_components"],
                                output_dim, dropout_rate=params["dropout_rate"]).to(device)
        model_path = os.path.join(output_dir, f"sfm_wf_w{w+1}.pth")
        model = train_final(model, combined_loader, None,
                            epochs=int(os.getenv("CRYPTO_FINAL_EPOCHS", "100")), lr=params["lr"],
                            weight_decay=params["weight_decay"],
                            device=device, patience=15, model_path=model_path)
        result = evaluate_trial(model, X_te, y_te, device)
        result["window"] = w + 1
        result["test_samples"] = len(X_te)
        result["sfm_equity_curve"] = np.cumprod(1 + result["strategy_returns"])
        result["bm_equity_curve"] = np.cumprod(1 + result["benchmark_returns"])
        wf_results.append(result)
        print(f"   Ventana {w+1}: Sharpe={result['sharpe']:.2f}  Equity={result['equity_final']:.4f}x")
    if wf_results:
        sharpe_wf = [r["sharpe"] for r in wf_results]
        print(f"\n   Walk-Forward: Sharpe mu={np.mean(sharpe_wf):.2f}")
    return wf_results


def _plot_distribution(study, output_dir):
    best = study.best_trial
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sharpe_vals = [-t.value for t in study.trials if t.value is not None]
    best_sharpe = -best.value
    axes[0].hist(sharpe_vals, bins=30, edgecolor="black", alpha=0.7, color="steelblue")
    axes[0].axvline(best_sharpe, color="red", linestyle="--", label=f"Mejor: {best_sharpe:.2f}")
    axes[0].axvline(0, color="gray", linestyle=":", alpha=0.7)
    axes[0].set_xlabel("Sharpe Ratio (validacion)")
    axes[0].set_ylabel("Frecuencia")
    axes[0].set_title("Distribucion de Sharpe en Validacion")
    axes[0].legend()
    n_complete = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE)
    n_pruned = sum(1 for t in study.trials if t.state == optuna.trial.TrialState.PRUNED)
    axes[1].bar(["Completados", "Pruned"], [n_complete, n_pruned],
                color=["green", "orange"], edgecolor="black")
    axes[1].set_ylabel("No. de trials")
    axes[1].set_title(f"Trials: {n_complete + n_pruned} totales")
    plt.suptitle(f"Optuna - Mejor Sharpe en Val: {best_sharpe:.2f}", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "optuna_distribution.png"), dpi=150)
    plt.close()


def plot_top_k_results(top_results, stats, output_dir):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
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
    plt.suptitle(f"Top-{len(top_results)} - Sharpe mu={stats['sharpe']['mean']:.2f}", fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "top_k_results.png"), dpi=150)
    plt.close()


def plot_walk_forward(wf_results, output_dir):
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
    plt.savefig(os.path.join(output_dir, "walk_forward.png"), dpi=150)
    plt.close()
    # Curvas de equity por ventana
    n_wf = len(wf_results)
    colors_sfm = ['#2196F3', '#4CAF50', '#FF9800']
    fig2, axes2 = plt.subplots(1, n_wf, figsize=(6 * n_wf, 4.5), sharey=False)
    if n_wf == 1:
        axes2 = [axes2]
    fig2.suptitle('Walk-Forward: SFM vs Baseline - Curvas de Equity por Ventana',
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
        sfm_sharpe = r['sharpe']
        bm_sharpe_val = float(np.mean(r['benchmark_returns']) /
                              (np.std(r['benchmark_returns']) + 1e-10) * np.sqrt(252))
        label = f'SFM Sharpe: {sfm_sharpe:.2f}  |  Equity: {r["equity_final"]:.2f}x'
        ax.text(0.97, 0.12, label, transform=ax.transAxes, fontsize=9,
                ha='right', va='bottom', color=colors_sfm[i % len(colors_sfm)],
                fontweight='bold',
                bbox=dict(facecolor='white', edgecolor=colors_sfm[i % len(colors_sfm)],
                          alpha=0.85, boxstyle='round,pad=0.4'))
        label_bm = f'Baseline Sharpe: {bm_sharpe_val:.2f}  |  Equity: {r["benchmark_final"]:.2f}x'
        ax.text(0.97, 0.02, label_bm, transform=ax.transAxes, fontsize=9,
                ha='right', va='bottom', color='#666666', fontweight='bold',
                bbox=dict(facecolor='white', edgecolor='#888888', alpha=0.85,
                          boxstyle='round,pad=0.4'))
        ax.set_title(f'Ventana {r["window"]}  ({r["test_samples"]} muestras)',
                     fontsize=12, fontweight='bold', pad=8)
        ax.set_xlabel('Dia de test', fontsize=9)
        ax.set_ylabel('Equidad acumulada', fontsize=9)
        ax.axhline(y=1.0, color='#cccccc', linewidth=0.8, linestyle=':')
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)
    fig2.legend([sfm_line, bm_line], ['SFM', 'Baseline'],
                loc='upper center', bbox_to_anchor=(0.5, -0.02),
                ncol=2, fontsize=11, frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "walk_forward_equity.png"), dpi=150)
    plt.close()


# =====================================================================
# PIPELINE PRINCIPAL
# =====================================================================
if __name__ == "__main__":
    # --- Configuracion ---
    CRYPTOS = [
        item.strip().lower()
        for item in os.getenv(
            "CRYPTO_INSTRUMENTS", "BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC"
        ).split(",")
        if item.strip()
    ]
    N_TRIALS = int(os.getenv("CRYPTO_OPTUNA_TRIALS", "100"))
    N_EPOCHS_FINAL = int(os.getenv("CRYPTO_FINAL_EPOCHS", "100"))
    TOP_K = int(os.getenv("CRYPTO_TOP_K", "5"))
    DO_WALK_FORWARD = False
    N_WALK_WINDOWS = 3
    OUTPUT_DIR = os.getenv(
        "CRYPTO_MODEL_OUTPUT_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "output/sfm_v6_full_history"),
    )
    PROVIDER_URI = os.getenv("CRYPTO_QLIB_OUTPUT_DIR", "data/qlib")
    START_DATE = os.getenv("CRYPTO_START_DATE", "2015-01-01")
    END_DATE = os.getenv("CRYPTO_END_DATE", pd.Timestamp.utcnow().strftime("%Y-%m-%d"))

    print("=" * 65)
    print("SFM v6 - Optuna + Top-K + Walk-Forward con TODO el historico")
    print("=" * 65)
    print(f"   Cryptos: {CRYPTOS}")
    print(f"   Split: 60/20/20 (train/val/test)")
    print(f"   Lookback: 20-90 dias (optimizado por Optuna)")
    print(f"   Denoising: OFF")
    print(f"   Trials Optuna: {N_TRIALS}  |  Top-K: {TOP_K}")
    print(f"   Seed: {SEED}")
    print(f"   Provider Qlib: {PROVIDER_URI}")
    print(f"   Rango: {START_DATE} -> {END_DATE}")
    if not HAS_OPTUNA:
        print("ERROR: Instala optuna: pip install optuna")
        exit(1)
    print("=" * 65)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- Qlib ---
    qlib.init(provider_uri=PROVIDER_URI, region=REG_US,
              kernels=int(os.getenv("QLIB_KERNELS", "1")))

    # --- Carga de datos ---
    print("\nCargando datos desde Qlib...")
    market_data, labels_data, dates_idx = load_and_process_crypto_data(
        CRYPTOS, START_DATE, END_DATE)

    input_dim = market_data.shape[1]
    output_dim = len(CRYPTOS)
    n_total = len(market_data)
    print(f"\n{'='*62}")

    # --- Split 60/20/20 ---
    train_end = int(n_total * 0.60)
    val_end = int(n_total * 0.80)

    market_train = market_data[:train_end]
    market_val = market_data[train_end:val_end]
    market_test = market_data[val_end:]

    labels_train = labels_data[:train_end]
    labels_val = labels_data[train_end:val_end]
    labels_test = labels_data[val_end:]

    print("SPLIT TEMPORAL 60/20/20")
    print("=" * 62)
    print(f"   {'Particion':<14} {'Muestras':<10} {'Rango':<20}   {'Ratio':<8}")
    print(f"   {'-'*14} {'-'*10} {'-'*20}   {'-'*8}")
    for name, ds, de, dlen in [
        ("TRAIN", 0, train_end, len(market_train)),
        ("VAL", train_end, val_end, len(market_val)),
        ("TEST", val_end, n_total, len(market_test)),
    ]:
        d_start = dates_idx[min(ds, len(dates_idx)-1)]
        d_end = dates_idx[min(max(0, de-1), len(dates_idx)-1)]
        pct = 100 * dlen / n_total
        print(f"   {name:<14} {dlen:<10} {d_start.strftime('%Y-%m-%d')} -> {d_end.strftime('%Y-%m-%d')}   {pct:.1f}%")
    print(f"{'='*62}")

    # Clipping y scaling con SOLO train
    clip_bounds = fit_clip_bounds(market_train)
    market_train = apply_clip_bounds(market_train, clip_bounds)
    market_val = apply_clip_bounds(market_val, clip_bounds)
    market_test = apply_clip_bounds(market_test, clip_bounds)

    scaler = MinMaxScaler(feature_range=(-1, 1))
    market_train_scaled = scaler.fit_transform(market_train)
    market_val_scaled = scaler.transform(market_val)
    market_test_scaled = scaler.transform(market_test)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"   Device: {device}")

    # =================================================================
    # FASE 1: OPTIMIZACION CON OPTUNA
    # =================================================================
    print("\n" + "=" * 65)
    print("FASE 1: BUSQUEDA DE HIPERPARAMETROS CON OPTUNA")
    print("=" * 65)
    print(f"   Trials: {N_TRIALS}  |  Sampler: TPESampler  |  Pruner: MedianPruner")

    study = optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=SEED),
        pruner=MedianPruner(n_startup_trials=10, n_warmup_steps=5, interval_steps=1),
        study_name="sfm_optuna_v6",
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
        print("\nInterrumpido")

    elapsed = time.time() - start_time
    print(f"\nTiempo: {elapsed/60:.1f} min")

    best_trial = study.best_trial
    best_sharpe_val = -best_trial.value
    print(f"\nMEJOR TRIAL (por Sharpe en validacion):")
    print(f"   Sharpe Val: {best_sharpe_val:.2f}")
    for key, val in best_trial.params.items():
        print(f"   {key}: {val}")

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
        "split": "60/20/20",
        "lookback_range": "20-90",
        "start_date": START_DATE,
        "end_date": END_DATE,
    }
    with open(os.path.join(OUTPUT_DIR, "study_results.json"), "w") as f:
        json.dump(study_results, f, indent=2)
    print(f"\nstudy_results.json guardado")

    print("\nGenerando visualizaciones...")
    try:
        _plot_distribution(study, OUTPUT_DIR)
    except Exception as e:
        print(f"   Distribucion: {e}")

    # =================================================================
    # FASE 2: TOP-K EVALUATION
    # =================================================================
    print("\n" + "=" * 65)
    print("FASE 2: TOP-K EVALUATION")
    print("=" * 65)

    top_results, stats, top_trials = evaluate_top_k(
        study, TOP_K, CRYPTOS,
        market_train_scaled, labels_train,
        market_val_scaled, labels_val,
        market_test_scaled, labels_test,
        input_dim, output_dim, device, OUTPUT_DIR
    )

    with open(os.path.join(OUTPUT_DIR, "top_k_results.json"), "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print(f"top_k_results.json guardado")

    try:
        plot_top_k_results(top_results, stats, OUTPUT_DIR)
    except Exception as e:
        print(f"   Top-K plot: {e}")

    # =================================================================
    # FASE 3: WALK-FORWARD VALIDATION
    # =================================================================
    if DO_WALK_FORWARD:
        print("\n" + "=" * 65)
        print("FASE 3: WALK-FORWARD VALIDATION")
        print("=" * 65)

        wf_results = run_walk_forward(
            CRYPTOS, market_data, labels_data, study, OUTPUT_DIR,
            input_dim, output_dim, device, scaler
        )

        if wf_results:
            wf_stats = {
                "n_windows": len(wf_results),
                "sharpe": {"mean": float(np.mean([r["sharpe"] for r in wf_results])),
                           "std": float(np.std([r["sharpe"] for r in wf_results])),
                           "values": [r["sharpe"] for r in wf_results]},
            }
            with open(os.path.join(OUTPUT_DIR, "walk_forward_results.json"), "w") as f:
                json.dump(wf_stats, f, indent=2, default=str)
            print(f"walk_forward_results.json guardado")
            try:
                plot_walk_forward(wf_results, OUTPUT_DIR)
            except Exception as e:
                print(f"   WF plot: {e}")

    # =================================================================
    # RESUMEN FINAL
    # =================================================================
    print("\n" + "=" * 65)
    print("RESUMEN SFM v6")
    print("=" * 65)
    print(f"\n   Optuna:")
    print(f"      Trials: {len(study.trials)} ({n_complete} OK, {n_pruned} pruned)")
    print(f"      Mejor Sharpe en val: {best_sharpe_val:.2f}")
    print(f"      Tiempo: {elapsed/60:.1f} min")
    print(f"\n   Top-{TOP_K} en test:")
    print(f"      Sharpe:  mu={stats['sharpe']['mean']:.2f}  sigma={stats['sharpe']['std']:.2f}")
    print(f"      Equity:  mu={stats['equity_final']['mean']:.4f}x  sigma={stats['equity_final']['std']:.4f}x")
    print(f"\n   {OUTPUT_DIR}/")
    print(f"   ├── study_results.json")
    print(f"   ├── top_k_results.json")
    print(f"   ├── top_k_results.png")
    print(f"   ├── optuna_distribution.png")
    print(f"   └── sfm_top*.pth (modelos)")

    print("\nPipeline v6 completado.")
