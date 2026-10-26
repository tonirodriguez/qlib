#!/usr/bin/env python3
"""exp_causal_leak.py — ¿Sobrevive la estrategia SFM v8 sin el data leak?

Entrena UN modelo por variante de preprocesado y mide IC + backtest honestos.

Variantes:
  A  raw        — features sin denoising (causal por construcción)
  B  causal_wav — wavelet en ventana móvil, descartando el borde (causal)
  C  global_wav — wavelet sobre la serie completa (EL LEAK ORIGINAL, control)

Mide en el test (último 20%, nunca visto en entrenamiento):
  - IC medio diario (Pearson cross-sectional predicción vs retorno realizado)
  - backtest top1_long_returns con coste 0.1%
  - prueba mecánica de truncado: ¿cambian las features de t si trunco los datos en t?

Uso: python exp_causal_leak.py [A B C]
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import qlib
from qlib.config import REG_US
from qlib.data import D

from crypto.research_utils import fit_clip_bounds, apply_clip_bounds, top1_long_returns

CRYPTOS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
START_DATE = "2015-01-01"
END_DATE = "2026-10-25"
LOOKBACK = 20
HIDDEN = 96
FREQ_COMP = 20
DROPOUT = 0.30
EPOCHS = 40
BATCH = 32
LR = 1e-3
WD = 1e-4
SEED = 42

OUT = Path(__file__).resolve().parent / "output" / "sfm_v8"
OUT.mkdir(parents=True, exist_ok=True)


# ── MODELO (réplica exacta de v8) ──────────────────────────────────────
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
        return self.dropout(h), c


class SFMModelRefined(nn.Module):
    def __init__(self, input_dim, hidden_dim, freq_components, output_dim, dropout_rate=0.2):
        super().__init__()
        self.cell = SFMCellRefined(input_dim, hidden_dim, freq_components, dropout_rate)
        self.fc_out = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        b, seq, _ = x.shape
        h = torch.zeros(b, self.cell.hidden_dim, device=x.device)
        c = torch.zeros(b, self.cell.hidden_dim, device=x.device)
        for t in range(seq):
            h, c = self.cell(x[:, t, :], (h, c))
        return self.fc_out(h)


# ── DENOISING ──────────────────────────────────────────────────────────
def wavelet_denoise_1d(sig, wavelet="db2", level=2, mode="soft"):
    import pywt
    coeffs = pywt.wavedec(sig, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    if sigma < 1e-10:
        sigma = np.std(sig) * 0.1
    thr = sigma * np.sqrt(2 * np.log(len(sig)))
    ct = [coeffs[0]] + [pywt.threshold(c, thr, mode=mode) for c in coeffs[1:]]
    return pywt.waverec(ct, wavelet)[:len(sig)]


def denoise_global(mat):
    """LEAK: transformada global sobre toda la serie."""
    out = np.zeros_like(mat)
    for c in range(mat.shape[1]):
        out[:, c] = wavelet_denoise_1d(mat[:, c])
    return out


def denoise_causal(mat, window=80, margin=10):
    """Causal: ventana móvil [t-window+1, t], valor tomado con retardo `margin`.

    El último punto de cada reconstrucción wavelet está distorsionado por el
    borde, así que se toma el valor en la posición window-1-margin. Eso
    introduce un retardo de `margin` días (lag) pero garantiza causalidad.
    """
    n, m = mat.shape
    out = np.zeros_like(mat)
    for c in range(m):
        col = mat[:, c]
        for t in range(n):
            if t < window - 1:
                out[t, c] = col[t]          # sin historia suficiente: valor crudo
                continue
            seg = col[t - window + 1 : t + 1]
            rec = wavelet_denoise_1d(seg)
            out[t, c] = rec[window - 1 - margin]
    return out


# ── FEATURES ───────────────────────────────────────────────────────────
def load_raw(cryptos, start_date, end_date):
    qlib.init(provider_uri="data/qlib", region=REG_US, kernels=1)
    close = {}
    for c in cryptos:
        df = D.features([c], ["$close"], start_time="2014-10-01", end_time=end_date)
        if df is None or df.empty:
            continue
        s = df.reset_index().pivot(index="datetime", columns="instrument", values="$close")[c]
        close[c] = s
    df_close = pd.DataFrame(close).sort_index()
    df_close = df_close[df_close.index >= pd.Timestamp(start_date)]
    return df_close


def build_features(df_close, variant):
    """Construye la matriz de features con la variante pedida.

    Diferencias con el original:
      - sin .bfill() (leak #2: rellena NaN con el valor futuro)
      - denoising según variante
    """
    n_c = df_close.shape[1]
    df_pct = df_close.pct_change().fillna(0)
    mean5 = df_close.rolling(5).mean().fillna(df_close)
    safe = df_close.replace(0, np.nan).ffill()          # solo ffill (causal)
    ratio = (mean5 / safe).replace([np.inf, -np.inf], np.nan).ffill().fillna(1.0)
    vol = df_pct.rolling(20).std().fillna(0)
    ma20 = df_close.rolling(20).mean().fillna(df_close)
    ma20_ratio = (ma20 / safe).replace([np.inf, -np.inf], np.nan).ffill().fillna(1.0)
    rng = df_pct.abs()

    mat = np.hstack([df_close.values, df_pct.values, ratio.values,
                     vol.values, ma20_ratio.values, rng.values])
    mat = np.nan_to_num(mat, nan=0.0, posinf=1.0, neginf=-1.0)

    if variant == "A":
        pass
    elif variant == "B":
        mat = denoise_causal(mat)
    elif variant == "C":
        mat = denoise_global(mat)
    else:
        raise ValueError(variant)

    # Saneado posterior al denoising: la reconstrucción wavelet puede devolver
    # NaN/inf en segmentos degenerados (columnas constantes, colas sin historia).
    mat = np.nan_to_num(mat, nan=0.0, posinf=1.0, neginf=-1.0)

    labels = (df_close.shift(-1) / df_close - 1).values
    # Saneado: NaN/inf -> 0 y recorte de outliers extremos (precios 0 pre-listing)
    labels = np.nan_to_num(labels, nan=0.0, posinf=0.0, neginf=0.0)
    labels = np.clip(labels, -1.0, 1.0)
    return mat, labels, n_c


def make_windows(mat, labels, lookback):
    X, y = [], []
    for i in range(len(mat) - lookback - 1):
        X.append(mat[i : i + lookback])
        y.append(labels[i + lookback])
    return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.float32)


def ic_mean(pred, real):
    """IC medio diario: correlación cross-sectional por día."""
    ics = []
    for t in range(len(pred)):
        p, r = pred[t], real[t]
        m = np.isfinite(p) & np.isfinite(r)
        if m.sum() < 4:
            continue
        if np.std(p[m]) < 1e-12 or np.std(r[m]) < 1e-12:
            continue
        ics.append(np.corrcoef(p[m], r[m])[0, 1])
    return float(np.mean(ics)) if ics else float("nan"), len(ics)


def truncation_test(df_close, variant, t_index):
    """¿Cambia la fila t si trunco los datos en t? Si no cambia → causal."""
    full_mat, _, _ = build_features(df_close, variant)
    trunc_mat, _, _ = build_features(df_close.iloc[: t_index + 1], variant)
    a = full_mat[t_index]
    b = trunc_mat[t_index]
    diff = np.abs(a - b)
    return float(diff.max()), int((diff > 1e-8).sum()), a.size


def run_variant(df_close, variant):
    print(f"\n{'='*70}\nVARIANTE {variant}\n{'='*70}")
    t0 = time.time()
    mat, labels, n_c = build_features(df_close, variant)
    print(f"  matriz: {mat.shape}  ({time.time()-t0:.1f}s)")

    n = len(mat)
    tr, va = int(n * 0.60), int(n * 0.80)
    mtr, mva, mte = mat[:tr], mat[tr:va], mat[va:]
    ltr, lva, lte = labels[:tr], labels[tr:va], labels[va:]

    # Preprocesado causal: clipping y scaler ajustados SOLO con train
    cb = fit_clip_bounds(mtr)
    mtr = apply_clip_bounds(mtr, cb)
    mva = apply_clip_bounds(mva, cb)
    mte = apply_clip_bounds(mte, cb)
    sc = MinMaxScaler(feature_range=(-1, 1))
    mtr_s = sc.fit_transform(mtr)
    mva_s = sc.transform(mva)
    mte_s = sc.transform(mte)

    # Ventanas: cada ventana termina en t y predice labels[t]
    def win(mm, ll):
        X, y = [], []
        for i in range(len(mm) - LOOKBACK - 1):
            X.append(mm[i : i + LOOKBACK])
            y.append(ll[i + LOOKBACK])
        return np.asarray(X, np.float32), np.asarray(y, np.float32)

    Xtr, ytr = win(mtr_s, ltr)
    Xva, yva = win(mva_s, lva)
    Xte, yte = win(mte_s, lte)
    print(f"  ventanas: train {Xtr.shape[0]} | val {Xva.shape[0]} | test {Xte.shape[0]}")

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    model = SFMModelRefined(mat.shape[1], HIDDEN, FREQ_COMP, n_c, DROPOUT)
    crit = nn.MSELoss()
    opt = optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)

    dl_tr = DataLoader(TensorDataset(torch.tensor(Xtr), torch.tensor(ytr)), batch_size=BATCH, shuffle=False)
    dl_va = DataLoader(TensorDataset(torch.tensor(Xva), torch.tensor(yva)), batch_size=BATCH, shuffle=False)

    best_va, best_state, patience = float("inf"), None, 0
    for ep in range(EPOCHS):
        model.train()
        tl = 0.0
        for bx, by in dl_tr:
            opt.zero_grad()
            loss = crit(model(bx), by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tl += loss.item()
        tl /= len(dl_tr)
        model.eval()
        vl = 0.0
        with torch.no_grad():
            for bx, by in dl_va:
                vl += crit(model(bx), by).item()
        vl /= len(dl_va)
        if np.isfinite(vl) and vl < best_va:
            best_va, best_state, patience = vl, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 8:
                print(f"  early stop en epoch {ep+1} (val {vl:.6f})")
                break
        if (ep + 1) % 10 == 0:
            print(f"  epoch {ep+1:>2} | train {tl:.6f} | val {vl:.6f}")

    if best_state is None:
        print("  ⚠️  ningún epoch con val finito: el modelo no aprendió nada")
        return {"variant": variant, "ic_mean": float("nan"), "n_days_ic": 0,
                "equity": float("nan"), "sharpe": float("nan"), "max_dd_pct": float("nan"),
                "days_invested": 0, "n_test": 0, "score_mean": float("nan"),
                "days_score_gt_0025": 0, "trunc_max_diff": float("nan"),
                "trunc_changed": -1, "trunc_total": -1, "causal": None,
                "elapsed_s": round(time.time() - t0, 1), "note": "training_diverged"}
    model.load_state_dict(best_state)
    model.eval()

    preds = []
    with torch.no_grad():
        for i in range(0, len(Xte), 256):
            preds.append(model(torch.tensor(Xte[i : i + 256])).numpy())
    preds = np.vstack(preds)

    ic, n_ic = ic_mean(preds, yte)
    ret, pos = top1_long_returns(preds, yte, transaction_cost=0.001)
    eq = float(np.cumprod(1 + np.nan_to_num(ret))[-1])
    sharpe = float(np.nanmean(ret) / np.nanstd(ret) * np.sqrt(365)) if np.nanstd(ret) > 0 else float("nan")
    dd = float(np.min(np.cumprod(1 + np.nan_to_num(ret)) / np.maximum.accumulate(np.cumprod(1 + np.nan_to_num(ret))) - 1))

    print(f"\n  IC medio test:      {ic:+.4f}  ({n_ic} días)")
    print(f"  equity top1:        {eq:.2f}x")
    print(f"  Sharpe:             {sharpe:.2f}")
    print(f"  Max drawdown:       {dd*100:.1f}%")
    print(f"  días invertido:     {int((pos >= 0).sum())}/{len(pos)}")
    print(f"  score medio:        {preds.mean():+.4f}  (sesgo)")
    print(f"  días con score>0.025: {int((preds.max(axis=1) > 0.025).sum())}/{len(preds)}")

    mx, nchg, tot = truncation_test(df_close, variant, n - 5)
    print(f"\n  PRUEBA DE TRUNCADO: diff máx {mx:.2e} | {nchg}/{tot} valores cambian", end="")
    print("  → CAUSAL ✅" if nchg == 0 else "  → LEAK ❌")

    r = np.nan_to_num(ret)
    t_stat = float(r.mean() / r.std() * np.sqrt(len(r))) if r.std() > 0 else float("nan")
    print(f"  retorno diario medio {r.mean()*100:+.3f}% | std {r.std()*100:.2f}% | t-stat {t_stat:+.2f}")

    return {
        "variant": variant, "ic_mean": ic, "n_days_ic": n_ic,
        "equity": eq, "sharpe": sharpe, "max_dd_pct": dd * 100,
        "days_invested": int((pos >= 0).sum()), "n_test": len(preds),
        "score_mean": float(preds.mean()), "days_score_gt_0025": int((preds.max(axis=1) > 0.025).sum()),
        "trunc_max_diff": mx, "trunc_changed": nchg, "trunc_total": tot,
        "causal": nchg == 0, "elapsed_s": round(time.time() - t0, 1),
        "ret_mean_pct": float(r.mean() * 100), "ret_std_pct": float(r.std() * 100),
        "t_stat": t_stat,
    }


def main():
    variants = sys.argv[1:] or ["A", "C"]
    print("Cargando datos crudos desde Qlib...")
    df_close = load_raw(CRYPTOS, START_DATE, END_DATE)
    print(f"  {df_close.shape[0]} filas x {df_close.shape[1]} coins")
    print(f"  {df_close.index[0].date()} -> {df_close.index[-1].date()}")

    results = []
    for v in variants:
        results.append(run_variant(df_close, v))

    path = OUT / "exp_causal_leak_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n{'='*70}\nRESUMEN\n{'='*70}")
    print(f"{'var':<4} {'IC':>9} {'equity':>10} {'Sharpe':>8} {'DD%':>7} {'causal':>8} {'días>0.025':>11}")
    for r in results:
        print(f"{r['variant']:<4} {r['ic_mean']:>+9.4f} {r['equity']:>9.2f}x "
              f"{r['sharpe']:>8.2f} {r['max_dd_pct']:>7.1f} "
              f"{('sí' if r['causal'] else 'NO'):>8} {r['days_score_gt_0025']:>6}/{r['n_test']}")
    print(f"\nresultados en {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
