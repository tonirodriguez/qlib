"""Utilidades compartidas para los simuladores de paper-trading (E1, E2, E3).

REFACTOR del código común para que cada simulador (simulate.py, simulate_pead.py,
simulate_pead_core.py) use las MISMAS funciones de precios, earnings y costes IB,
sin duplicar lógica. Los simuladores existentes NO se tocan; este módulo se usa
por los nuevos (E3) desde el plan de Quinn (plan_E3_quinn_futuro.md).
"""
import os, json, datetime
import numpy as np
import pandas as pd

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
QLIB_URI = os.environ.get("QLIB_US_DATA", "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data")
UNIVERSE_FILE = os.path.join(QLIB_URI, "instruments/sp500_liquid.txt")
START = "2018-01-01"

# Ear file: prioridad historial append-only
EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_appended.csv")
if not os.path.exists(EAR_FILE):
    EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_data_full.csv")
if not os.path.exists(EAR_FILE):
    EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_data.csv")

# ===================== UNIVERSO =====================
def get_universe():
    tickers = []
    with open(UNIVERSE_FILE) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t:
                tickers.append(t)
    return tickers


# ===================== PRECIOS =====================
def get_prices(tickers):
    """DataFrame de precios reales (index fecha, cols tickers).

    Prioridad 1: prices_live.csv (fresco, del actualizador ligero)
    Prioridad 2: datos Qlib (close/factor, deshaciendo splits)
    """
    import qlib
    from qlib.data import D
    # Prioridad 1
    live_csv = os.path.join(SIM_DIR, "prices_live.csv")
    if os.path.exists(live_csv):
        df = pd.read_csv(live_csv, index_col=0, parse_dates=True).sort_index()
        cols = [c for c in df.columns if c in tickers]
        if len(cols) > 0:
            # qlib init implícitamente arriba
            return df[cols]
    # Prioridad 2: Qlib
    qlib.init(provider_uri=QLIB_URI, region='us')
    close = D.features(tickers, ["$close", "$factor"], start_time=START,
                       end_time="2100-12-31", freq="day")
    if close is None or close.empty:
        return None
    c = close["$close"].unstack(level=0).sort_index()
    f = close["$factor"].unstack(level=0).sort_index()
    return c / f


# ===================== EARNINGS (PEAD) =====================
def load_last_surprise():
    """Última sorpresa de earnings por ticker CON metadatos.

    Devuelve DataFrame: ticker, surprise_pct (última), reported_ts (última), sue.
    sue = surprise_pct / σ_histórica(surprise_pct del ticker) — comparable entre tickers.
    """
    if not os.path.exists(EAR_FILE):
        return pd.DataFrame(columns=["ticker", "surprise_pct", "reported_ts", "sue"])
    ear = pd.read_csv(EAR_FILE)
    if "reported_ts" in ear.columns:
        max_ts = ear.groupby("ticker")["reported_ts"].transform("max")
        last = ear[ear["reported_ts"] == max_ts].copy()
        sigma = ear.groupby("ticker")["surprise_pct"].std().rename("sigma")
        last = last.merge(sigma, on="ticker", how="left")
        last["sue"] = last["surprise_pct"] / last["sigma"].replace(0, np.nan)
        last["sue"] = last["sue"].fillna(last["surprise_pct"] / 10.0)
        return last[["ticker", "surprise_pct", "reported_ts", "sue"]]
    last = ear.groupby("ticker").last().reset_index()
    last["sue"] = np.nan
    return last[["ticker", "surprise_pct", "reported_ts", "sue"]] if "reported_ts" in last.columns \
        else last[["ticker", "surprise_pct", "sue"]]


def surprise_fresca(freshness_days=40):
    """DataFrame de sorpresas FRESCAS (dentro de ventana) para usar como señal PEAD.

    Returns: DataFrame con ticker, surprise_pct, sue (solo las dentro de ventana).
    """
    df = load_last_surprise()
    if df.empty or "reported_ts" not in df.columns:
        return pd.DataFrame()
    now = datetime.datetime.now().timestamp()
    df["ts"] = df["reported_ts"].astype(float)
    df["days_old"] = (now - df["ts"]) / 86400.0
    fresh = df[(df["ts"] > 0) & (df["days_old"] <= freshness_days)]
    return fresh[["ticker", "surprise_pct", "sue"]]


# ===================== COSTES IB =====================
IB_RATE_PER_SHARE = 0.0035
IB_MIN_PER_ORDER = 0.35
IB_SEC_RATE = 33.10 / 1_000_000.0
IB_TAF_PER_SHARE = 0.00016


def ib_buy_cost(shares, price):
    return max(IB_MIN_PER_ORDER, shares * IB_RATE_PER_SHARE)


def ib_sell_cost(shares, price):
    commission = max(IB_MIN_PER_ORDER, shares * IB_RATE_PER_SHARE)
    sec_fee = shares * price * IB_SEC_RATE
    taf = shares * IB_TAF_PER_SHARE
    return commission + sec_fee + taf


def ib_trades_cost(buys, sells):
    total = 0.0
    for shares, price in buys:
        total += ib_buy_cost(shares, price)
    for shares, price in sells:
        total += ib_sell_cost(shares, price)
    return total


# ===================== ESTADO =====================
def load_state(state_file):
    if not os.path.exists(state_file):
        return None
    with open(state_file) as f:
        state = json.load(f)
    for k in ("cash_usd", "start_capital_eur", "start_capital_usd", "euro_usd"):
        if k in state and isinstance(state[k], str):
            state[k] = float(state[k])
    for t, pos in state.get("positions", {}).items():
        for k in ("shares", "cost_usd", "entry_price"):
            if k in pos and isinstance(pos[k], str):
                pos[k] = float(pos[k])
    return state


def save_state(state, state_file):
    positions = {}
    for t, pos in state.get("positions", {}).items():
        # Convertir solo los campos numéricos; mantener strings (p.ej. book)
        clean = {}
        for k, v in pos.items():
            try:
                clean[k] = float(v)
            except (TypeError, ValueError):
                clean[k] = v
        positions[t] = clean
    out = dict(state)
    out["positions"] = positions
    with open(state_file, "w") as f:
        json.dump(out, f, indent=2, default=float)
