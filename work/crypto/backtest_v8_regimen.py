"""backtest_v8_regimen.py — Backtest SFM v8 sobre un RANGO de fechas dado (régimen concreto).

Replica fielmente la lógica de sfm_paper_trading.py (igual que backtest_v8_2025.py) pero
parametrizado por rango de fechas, para medir la RÉGIMEN-DEPENDENCIA de la estrategia v8.

Uso:
    python backtest_v8_regimen.py --name bull2021 --start 2020-11-01 --end 2021-11-30
    python backtest_v8_regimen.py --name rally2024 --start 2024-01-01 --end 2024-12-31

LIMITACIÓN METODOLÓGICA (declarada): el modelo sfm_top3.pth fue entrenado con datos hasta
~2026. Aplicarlo sobre 2020-21/2024 NO es un test out-of-sample limpio (el modelo "vio" esos
regímenes en training). Mide la robustez CUALITATIVA del CICLO de decisión + costes + capital
bajo regímenes distintos, no la capacidad predictiva pura. Se etiqueta como tal en el output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

import pywt  # noqa: E402
import qlib  # noqa: E402
from qlib.config import REG_US  # noqa: E402
from qlib.data import D  # noqa: E402

from research_utils import apply_clip_bounds, fit_clip_bounds, performance_metrics  # noqa: E402
from sklearn.preprocessing import MinMaxScaler  # noqa: E402

CRYPTOS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
MODEL_FILE = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "sfm_top3.pth"
MODEL_PARAMS = {"hidden_dim": 96, "freq_components": 20, "dropout_rate": 0.30, "lookback": 20}

INITIAL_CAPITAL_EUR = 10000.0
EURUSD_DEFAULT = 1.10  # fallback si no hay dato del rango

# Parametros del paper trading (identicos a backtest_v8_2025.py)
MAX_POSITIONS = 2
BUY_THRESHOLD = 0.015
HIGH_CONF_THRESHOLD = 0.025
TRANSACTION_COST = 0.0010
HALF_SPREAD = 0.0002
SLIPPAGE = 0.0003
COST = TRANSACTION_COST + HALF_SPREAD + SLIPPAGE
CASH_YIELD_APY = 0.045


class SFMCellRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, dropout_rate=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
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


def wavelet_denoise_1d(signal, wavelet="db2", level=2, mode="soft"):
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    if sigma < 1e-10:
        sigma = np.std(signal) * 0.1
    threshold = sigma * np.sqrt(2 * np.log(len(signal)))
    coeffs_thresh = list(coeffs)
    for i in range(1, len(coeffs_thresh)):
        coeffs_thresh[i] = pywt.threshold(coeffs_thresh[i], threshold, mode=mode)
    return pywt.waverec(coeffs_thresh, wavelet)[:len(signal)]


def denoise_matrix(matrix):
    denoised = np.zeros_like(matrix)
    for col in range(matrix.shape[1]):
        denoised[:, col] = wavelet_denoise_1d(matrix[:, col])
    return denoised


def build_features_matrix(df_close: pd.DataFrame) -> np.ndarray:
    df_pct = df_close.pct_change().fillna(0)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_close_safe = df_close.replace(0, np.nan).ffill().bfill()
    df_ratio = (df_mean_5 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)
    df_vol = df_pct.rolling(window=20).std().fillna(0)
    df_ma20 = df_close.rolling(window=20).mean().fillna(df_close)
    df_ma20_ratio = (df_ma20 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)
    df_range = df_pct.abs()
    matrix = np.hstack([df_close.values, df_pct.values, df_ratio.values,
                        df_vol.values, df_ma20_ratio.values, df_range.values])
    return np.nan_to_num(matrix, nan=0.0, posinf=1.0, neginf=-1.0)


def simulate_portfolio(pred_days, pred_list, df_close, cash_yield_apy=CASH_YIELD_APY,
                       buy_threshold=HIGH_CONF_THRESHOLD, max_positions=MAX_POSITIONS,
                       initial_capital_usd=INITIAL_CAPITAL_EUR * EURUSD_DEFAULT):
    sell_threshold = buy_threshold  # sin histeresis (comportamiento original del paper)
    cash = initial_capital_usd
    positions = {}
    curve, opers = [], []
    daily_rate = (1.0 + cash_yield_apy) ** (1.0 / 365.0) - 1.0 if cash_yield_apy > 0 else 0.0
    total_interest = 0.0
    idx_map = {c.upper(): i for i, c in enumerate(CRYPTOS)}

    for r, day in enumerate(pred_days):
        scores = pred_list[r]
        close_row = df_close.loc[day] if day in df_close.index else None
        if daily_rate > 0 and cash > 0:
            interest = cash * daily_rate
            cash += interest
            total_interest += interest
        # vender
        for s_lower in list(positions.keys()):
            ci = idx_map[s_lower.upper()]
            if scores[ci] < sell_threshold:
                if close_row is not None and s_lower.upper() in close_row.index:
                    px = float(close_row[s_lower.upper()])
                    if px and px == px:
                        shares = positions[s_lower]["shares"]
                        gross = shares * px
                        net = gross - gross * COST
                        cash += net
                        opers.append({"date": str(day.date()), "type": "SELL", "symbol": s_lower.upper(),
                                      "shares": shares, "price": px, "fee": round(gross*COST,2), "net": round(net,2)})
                        del positions[s_lower]
        # comprar
        current = len(positions)
        available = max_positions - current
        if available > 0 and close_row is not None:
            candidates = []
            for c in CRYPTOS:
                if c not in positions and scores[CRYPTOS.index(c)] > buy_threshold:
                    candidates.append((c, scores[CRYPTOS.index(c)]))
            candidates.sort(key=lambda kv: -kv[1])
            for c, _sc in candidates[:available]:
                if close_row is not None and c.upper() in close_row.index:
                    px = float(close_row[c.upper()])
                    if px and px == px:
                        capital_per = cash / (available + 1)
                        nav = max(capital_per - capital_per * COST, 0.0)
                        shares = nav / px
                        fee = capital_per * COST
                        cost = shares * px + fee
                        if cost <= cash:
                            positions[c] = {"shares": shares, "entry_day": r}
                            cash -= cost
                            opers.append({"date": str(day.date()), "type": "BUY", "symbol": c.upper(),
                                          "shares": shares, "price": px, "fee": round(fee,2), "cost": round(cost,2)})
        val = cash
        if close_row is not None:
            for c_shar in positions:
                if close_row is not None and c_shar.upper() in close_row.index:
                    val += positions[c_shar]["shares"] * float(close_row[c_shar.upper()])
        curve.append((day, val))
    return curve, opers, total_interest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Etiqueta del régimen (ej. bull2021)")
    ap.add_argument("--start", required=True, help="Fecha inicio YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="Fecha fin YYYY-MM-DD")
    ap.add_argument("--load-from", default="2020-01-01", help="Desde dónde cargar datos Qlib (pre-régimen)")
    args = ap.parse_args()

    start, end = pd.Timestamp(args.start), pd.Timestamp(args.end)
    qlib.init(provider_uri=str(PROJECT_ROOT / "data" / "qlib"), region=REG_US, kernels=1)

    close_dict = {}
    for c in CRYPTOS:
        df = D.features([c], ["$close"], start_time=args.load_from, end_time="2026-12-31")
        df = df.reset_index()
        s = df.pivot(index="datetime", columns="instrument", values="$close")[c]
        close_dict[c.upper()] = s
    df_close = pd.DataFrame(close_dict).sort_index()
    df_close = df_close[df_close.index <= pd.Timestamp("2026-10-31")]
    print(f"Datos cargados: {df_close.index[0].date()} -> {df_close.index[-1].date()} ({len(df_close)} filas)")

    model = SFMModelRefined(54, MODEL_PARAMS["hidden_dim"], MODEL_PARAMS["freq_components"], len(CRYPTOS), MODEL_PARAMS["dropout_rate"])
    model.load_state_dict(torch.load(MODEL_FILE, map_location="cpu", weights_only=True))
    model.eval()
    lookback = MODEL_PARAMS["lookback"]

    pred_days, pred_list = [], []
    all_days = list(df_close.index)
    for i in range(lookback + 25, len(all_days)):
        day = all_days[i]
        if day < start:
            continue
        if day > end:
            break
        window = df_close.loc[:day]
        if len(window) < lookback + 5:
            continue
        matrix = build_features_matrix(window)
        clip = fit_clip_bounds(matrix); matrix = apply_clip_bounds(matrix, clip)
        scale = MinMaxScaler(feature_range=(-1, 1)); scaled = scale.fit_transform(matrix)
        x = torch.tensor(scaled[-lookback:][np.newaxis, :, :], dtype=torch.float32)
        with torch.no_grad():
            pred = model(x).numpy()[0]
        pred_days.append(day); pred_list.append(pred)

    print(f"Dias evaluados en régimen: {len(pred_days)}")
    if not pred_days:
        print("Sin días — revisar rango.")
        return

    curve, opers, total_interest = simulate_portfolio(pred_days, pred_list, df_close)
    dates = [str(d.date()) for d, _ in curve]
    vals = np.array([v for _, v in curve])
    rets = np.diff(vals) / vals[:-1] if len(vals) > 1 else np.array([0.0])
    rets = np.insert(rets, 0, vals[0] / (INITIAL_CAPITAL_EUR * EURUSD_DEFAULT) - 1)
    metrics = performance_metrics(rets)
    final_usd = float(vals[-1]) if len(vals) else INITIAL_CAPITAL_EUR * EURUSD_DEFAULT
    initial_usd = INITIAL_CAPITAL_EUR * EURUSD_DEFAULT
    ret_pct_usd = (final_usd / initial_usd - 1) * 100

    result = {
        "nombre_regimen": args.name, "start_date": dates[0], "end_date": dates[-1],
        "n_dias": len(pred_days), "initial_usd": round(initial_usd, 2), "final_usd": round(final_usd, 2),
        "return_pct_usd": round(ret_pct_usd, 2),
        "sharpe": round(metrics["sharpe"], 3), "sortino": round(metrics["sortino"], 3),
        "max_drawdown_pct": round(metrics["max_drawdown"]*100, 2),
        "annualized_return_pct": round(metrics["annualized_return"]*100, 2),
        "calmar": round(metrics["calmar"], 3),
        "n_trades": len(opers), "total_interest_usd": round(total_interest, 2),
        "cash_yield_apy": CASH_YIELD_APY, "costs": {"txn": TRANSACTION_COST, "spread": HALF_SPREAD, "slippage": SLIPPAGE},
        "EURUSD_asumido": EURUSD_DEFAULT,
    }
    out_dir = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"backtest_regimen_{args.name}.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()