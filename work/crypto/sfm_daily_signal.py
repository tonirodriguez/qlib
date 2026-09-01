"""
sfm_daily_signal.py — Genera señal diaria de trading usando el mejor modelo SFM v8.

Flujo:
  1. Carga los datos más recientes desde el dataset Qlib (data/qlib/)
  2. Reconstruye los features (close, pct, ratio_5d, vol_20d, ma20_ratio, rango)
  3. Aplica denoising wavelet
  4. Escala con MinMaxScaler (-1, 1)
  5. Carga el modelo entrenado (sfm_top3.pth — Sharpe 2.74)
  6. Genera predicción para hoy
  7. Muestra ranking ordenado con señal de trading

Uso:
  conda run -n qlib python work/crypto/sfm_daily_signal.py
  conda run -n qlib python work/crypto/sfm_daily_signal.py --model=top1
"""

import os, sys, json, warnings, pickle
from pathlib import Path
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False

import qlib
from qlib.config import REG_US
from qlib.data import D
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

PROJECT_ROOT = Path(__file__).resolve().parent  # work/crypto/
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "sfm_v8"
DEFAULT_CRYPTOS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]


# =====================================================================
# ARQUITECTURA DEL MODELO
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


# =====================================================================
# PROCESAMIENTO
# =====================================================================

def wavelet_denoise_1d(signal, wavelet="db2", level=2, mode="soft"):
    if not HAS_PYWT:
        return signal
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    if sigma < 1e-10:
        sigma = np.std(signal) * 0.1
    threshold = sigma * np.sqrt(2 * np.log(len(signal)))
    coeffs_thresh = list(coeffs)
    for i in range(1, len(coeffs_thresh)):
        coeffs_thresh[i] = pywt.threshold(coeffs_thresh[i], threshold, mode=mode)
    return pywt.waverec(coeffs_thresh, wavelet)[:len(signal)]


def denoise_market_matrix(market_matrix):
    if not HAS_PYWT:
        return market_matrix
    print("   🌀 Denoising Wavelet...")
    denoised = np.zeros_like(market_matrix)
    for col in range(market_matrix.shape[1]):
        denoised[:, col] = wavelet_denoise_1d(market_matrix[:, col])
    return denoised


def load_and_build_features(cryptos, start_date="2015-01-01"):
    """Carga datos desde Qlib y construye la matriz de features."""
    print(f"\n📥 Cargando {len(cryptos)} criptos...")
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp.utcnow().tz_localize(None)
    data_start = start_ts - pd.DateOffset(days=90)

    close_dict = {}
    for c in cryptos:
        df_c = D.features([c], ["$close"], start_time=data_start, end_time=end_ts)
        if df_c is None or df_c.empty:
            print(f"     {c}: SIN DATOS")
            continue
        df_c = df_c.reset_index()
        series = df_c.pivot(index="datetime", columns="instrument", values="$close")[c]
        close_dict[c] = series
        last = series.last_valid_index()
        print(f"     {c:>5s}: hasta {last.strftime('%Y-%m-%d')}" if last else f"     {c}: sin datos")

    if not close_dict:
        raise ValueError("No se pudo cargar ninguna cripto")

    df_close = pd.DataFrame(close_dict).sort_index()
    df_close = df_close[df_close.index >= start_ts]
    if len(df_close) < 100:
        raise ValueError(f"Solo {len(df_close)} filas.")

    df_pct = df_close.pct_change().fillna(0)
    df_mean_5 = df_close.rolling(window=5).mean().fillna(df_close)
    df_close_safe = df_close.replace(0, np.nan).ffill().bfill()
    df_ratio = (df_mean_5 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)
    df_vol = df_pct.rolling(window=20).std().fillna(0)
    df_ma20 = df_close.rolling(window=20).mean().fillna(df_close)
    df_ma20_ratio = (df_ma20 / df_close_safe).replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(1.0)
    df_range = df_pct.abs()

    market_matrix = np.hstack([
        df_close.values, df_pct.values, df_ratio.values,
        df_vol.values, df_ma20_ratio.values, df_range.values,
    ])
    market_matrix = np.nan_to_num(market_matrix, nan=0.0, posinf=1.0, neginf=-1.0)
    market_matrix = denoise_market_matrix(market_matrix)

    print(f"   📊 Matrix: {len(df_close)} filas x {market_matrix.shape[1]} features")
    print(f"   📅 Última fecha: {df_close.index[-1].strftime('%Y-%m-%d')}")
    return market_matrix, [c for c in cryptos if c in close_dict]


# =====================================================================
# PARÁMETROS DE MODELOS
# =====================================================================

MODEL_PARAMS = {
    "sfm_top1.pth": {"hidden_dim": 112, "freq_components": 16, "dropout_rate": 0.45, "lookback": 30},
    "sfm_top2.pth": {"hidden_dim": 112, "freq_components": 20, "dropout_rate": 0.45, "lookback": 20},
    "sfm_top3.pth": {"hidden_dim": 96,  "freq_components": 20, "dropout_rate": 0.30, "lookback": 20},
    "sfm_top4.pth": {"hidden_dim": 112, "freq_components": 16, "dropout_rate": 0.25, "lookback": 20},
    "sfm_top5.pth": {"hidden_dim": 32,  "freq_components": 20, "dropout_rate": 0.40, "lookback": 20},
}


def print_report(signals, model_name, date_str, n_cryptos):
    print(f"\n{'='*58}")
    print(f"📊 SEÑAL DIARIA SFM v8 — {date_str}")
    print(f"   Modelo: {model_name}")
    print(f"{'='*58}")
    print(f"{'#':<4} {'Señal':<20} {'Cripto':<8} {'Score':<10} {'Retorno':<10} {'Confianza':<10}")
    print(f"{'-'*58}")
    for rank, s in enumerate(signals, 1):
        print(f"{rank:<3} {s['signal']:<20} {s['crypto']:<8} {s['score']:+7.4f}  {s['expected_return_pct']:+5.2f}%  {s['confidence']:<10}")
    buys = [s for s in signals if "COMPRA" in s["signal"]]
    sells = [s for s in signals if "VENTA" in s["signal"]]
    high_conf = [s for s in buys if s["confidence"] == "ALTA"]
    print(f"{'='*58}")
    print(f"   🟢 COMPRAS: {len(buys)}  🔻 VENTAS: {len(sells)}  🏆 Alta confianza: {len(high_conf)}")
    if buys:
        print(f"   🥇 Mejor: {buys[0]['crypto']} ({buys[0]['expected_return_pct']:+.2f}%)")
    print(f"{'='*58}\n")


# =====================================================================
# MAIN
# =====================================================================

def main():
    cryptos_env = os.getenv("CRYPTO_INSTRUMENTS", ",".join(DEFAULT_CRYPTOS))
    cryptos = [s.strip().lower() for s in cryptos_env.split(",") if s.strip()]

    model_choice = "top3"
    for arg in sys.argv[1:]:
        if arg.startswith("--model="):
            model_choice = arg.split("=", 1)[1]
    model_map = {"top1": "sfm_top1.pth", "top2": "sfm_top2.pth", "top3": "sfm_top3.pth",
                 "top4": "sfm_top4.pth", "top5": "sfm_top5.pth"}
    model_file = model_map.get(model_choice, model_choice)

    model_path = Path(os.getenv("SFM_MODEL_PATH", str(DEFAULT_OUTPUT / model_file)))
    if not model_path.exists():
        alt = DEFAULT_OUTPUT / model_file
        if alt.exists():
            model_path = alt
        else:
            print(f"❌ Modelo no encontrado: {model_path}")
            for f in sorted(DEFAULT_OUTPUT.glob("sfm_*.pth")):
                print(f"   {f.name}")
            return

    params = MODEL_PARAMS.get(model_path.name, MODEL_PARAMS["sfm_top3.pth"])
    scaler_path = Path(os.getenv("SFM_SCALER_PATH", str(DEFAULT_OUTPUT / "scaler.pkl")))
    start_date = os.getenv("CRYPTO_START_DATE", "2015-01-01")

    print(f"\n{'='*55}")
    print(f"🔮 SFM v8 — Señal Diaria ({model_path.name})")
    print(f"{'='*55}")
    print(f"   🪙 {', '.join(c.upper() for c in cryptos)}")

    qlib.init(provider_uri=os.getenv("CRYPTO_QLIB_OUTPUT_DIR", "data/qlib"), region=REG_US, kernels=1)

    market_matrix, active_cryptos = load_and_build_features(cryptos, start_date)
    n_cryptos = len(active_cryptos)
    n_features = market_matrix.shape[1]

    if scaler_path.exists():
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        market_scaled = scaler.transform(market_matrix)
        print(f"   📐 Scaler: cargado")
    else:
        scaler = MinMaxScaler(feature_range=(-1, 1))
        market_scaled = scaler.fit_transform(market_matrix)
        with open(DEFAULT_OUTPUT / "scaler.pkl", "wb") as f:
            pickle.dump(scaler, f)
        print(f"   ✅ Scaler guardado")

    device = torch.device("cpu")
    model = SFMModelRefined(
        input_dim=n_features, hidden_dim=params["hidden_dim"],
        freq_components=params["freq_components"], output_dim=n_cryptos,
        dropout_rate=params["dropout_rate"],
    )
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.eval()
    print(f"   🧠 Modelo: hidden={params['hidden_dim']}, freq={params['freq_components']}, lookback={params['lookback']}")

    lookback = params["lookback"]
    X_pred = torch.tensor(market_scaled[-(lookback + 1):][np.newaxis, :, :], dtype=torch.float32)
    with torch.no_grad():
        predictions = model(X_pred).numpy()[0]

    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    signals = []
    for i, crypto in enumerate(active_cryptos):
        score = float(predictions[i])
        if score > 0.015:
            signal, conf = "🟢 COMPRA", "ALTA" if score > 0.025 else "MEDIA"
        elif score > 0.0:
            signal, conf = "🟡 ESPERAR", "BAJA"
        elif score > -0.01:
            signal, conf = "⚪ NEUTRAL", "BAJA"
        else:
            signal, conf = "🔻 VENTA", "MEDIA"
        signals.append({"crypto": crypto.upper(), "score": score, "signal": signal,
                        "confidence": conf, "expected_return_pct": round(score * 100, 2)})
    signals.sort(key=lambda x: x["score"], reverse=True)

    print_report(signals, model_path.name, today, n_cryptos)

    signal_data = {"date": today, "model": model_path.name, "signals": signals}
    output_file = DEFAULT_OUTPUT / f"signal_{today}.json"
    with open(output_file, "w") as f:
        json.dump(signal_data, f, indent=2)
    print(f"   💾 Señal guardada: {output_file}")


if __name__ == "__main__":
    main()