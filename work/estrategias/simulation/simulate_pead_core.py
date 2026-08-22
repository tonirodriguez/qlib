"""ESTRATEGIA 3 — PEAD-núcleo + momentum-táctico (simulate_pead_core.py)

Según el plan de Quinn (plan_E3_quinn_futuro.md), esta es la nueva arquitectura
que INVIERTE los pesos implícitos:
- LIBRO NÚCLEO (PEAD, 60-70%): ranking por SUE positivo y fresco (topk 20-25).
  Captura el drift post-anuncio de forma natural (la señal se renueva al reportar).
- LIBRO TÁCTICO (momentum, 30-40%, techo 50%): momentum 120d (topk 10-12)
  con VOL-GATING (si la vol del SP500 está alta, se reduce/pausa el capital
  desplegado del libro táctico).

Pesos FIJOS (no oráculo). Solo el vol-gating modula el libro táctico.
Los simuladores E1 (simulate.py) y E2 (simulate_pead.py) NO se tocan; quedan
como monitor. Este es el nuevo simulador con estado separado state_pead_core.json.

Uso: python work/estrategias/simulation/simulate_pead_core.py [--reset]
"""
import os, sys, json, datetime
import numpy as np
import pandas as pd

import sim_utils as su

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SIM_DIR, "state_pead_core.json")

# --- Parámetros de la arquitectura (pesos fijos según plan) ---
NUCLEO_W = 0.65          # peso del libro PEAD-núcleo
TACTICO_W = 0.35         # peso del libro momentum-táctico
TECTO_MOM_MAX = 0.50     # techo duro del momentum (nunca > 50%)
PEAD_TOPK = 22           # topk del libro núcleo (PEAD)
MOM_TOPK = 12            # topk del libro táctico (momentum)
MOM_W = 120              # ventana de momentum
SUE_POSITIVO_MIN = 1.0   # SUE mínimo para entrar en el libro PEAD (positivo)
START_CAPITAL_EUR = 19500.0  # capital equivalente al valor actual del paper (~€19.5k)

# --- Vol-gating (libro táctico) ---
VOL_WIN = 20             # ventana de vol realizada (días)
VOL_P75 = 0.75
VOL_P90 = 0.90
# nivel de gate resultante: dict por umbral
GATE = {
    (0, VOL_P75): 1.0,      # vol baja/normal -> momentum a pleno
    (VOL_P75, VOL_P90): 0.5,# vol alta -> momentum a la mitad
    (VOL_P90, 2.0): 0.0,    # vol muy alta -> momentum pausado (a cash)
}


def get_vol_gate(close_sp500):
    """Nivel de gate (0..1) basado en la vol realizada 20d del SP500 (percentiles)."""
    if close_sp500 is None or len(close_sp500) < VOL_WIN + 10:
        return 1.0
    s = close_sp500 / close_sp500.shift(1) - 1
    vol = s.rolling(VOL_WIN).std() * np.sqrt(252)
    vol = vol.dropna()
    if vol.empty:
        return 1.0
    # percentil actual vs su propia historia
    current = vol.iloc[-1]
    pct = (vol < current).mean()  # fracción de días con vol < actual
    for (lo, hi), gate in sorted(GATE.items()):
        if lo <= pct < hi:
            return gate
    return 1.0


def get_momentum_ranking(prices):
    """Ranking de momentum 120d sobre tickers del universo (descendente)."""
    mom = {}
    for t in prices.columns:
        s = prices[t].dropna()
        if len(s) > MOM_W:
            mom[t] = s.iloc[-1] / s.iloc[-1 - MOM_W] - 1
    return pd.Series(mom).dropna().sort_values(ascending=False)


def get_pead_ranking():
    """Ranking de PEAD: tickers con SUE positivo y fresco, ordenados por SUE desc."""
    fresh = su.surprise_fresca()
    if fresh.empty:
        return pd.Series(dtype=float)
    fresh = fresh[fresh["sue"] > SUE_POSITIVO_MIN].sort_values("sue", ascending=False)
    return fresh.set_index("ticker")["sue"]


def select_holdings(mom_ranking, pead_ranking, prices, n_core, n_tact):
    """Selecciona los tickers de cada libro (sin solaparse)."""
    # Libro núcleo: PEAD
    core_tickers = [t for t in pead_ranking.index if t in prices.columns][:n_core]
    # Libro táctico: momentum (excluyendo los ya en núcleo para evitar doble-posición)
    tact_candidates = [t for t in mom_ranking.index if t not in set(core_tickers)]
    tact_tickers = [t for t in tact_candidates if t in prices.columns][:n_tact]
    return core_tickers, tact_tickers


def main(reset=False):
    tickers = su.get_universe()
    prices = su.get_prices(tickers)
    if prices is None or prices.empty:
        print("ERROR: no hay precios. Revisa QLIB_US_DATA / prices_live.csv.")
        return
    print(f"Precios: {prices.shape[0]} fechas, {prices.shape[1]} tickers")

    mom_ranking = get_momentum_ranking(prices)
    pead_ranking = get_pead_ranking()
    print(f"Señal momentum: {len(mom_ranking)} tickers")
    print(f"Señal PEAD fresca: {len(pead_ranking)} tickers")

    core_t, tact_t = select_holdings(mom_ranking, pead_ranking, prices, PEAD_TOPK, MOM_TOPK)
    print(f"Libro NÚCLEO (PEAD): {len(core_t)} posiciones")
    print(f"Libro TÁCTICO (momentum): {len(tact_t)} posiciones")

    # --- Vol-gating del libro táctico ---
    close_sp500 = prices.get("^GSPC") if "^GSPC" in prices.columns else None
    # si no hay índice en el CSV, usar promedio del mercado como proxy
    if close_sp500 is None:
        close_sp500 = prices.mean(axis=1)
    gate = get_vol_gate(close_sp500)
    print(f"Vol-gate del libro táctico: {gate:.2f}")

    # Estado
    state = None if reset else su.load_state(STATE_FILE)

    today = datetime.date.today().isoformat()
    last_price_date = prices.index[-1].date().isoformat()

    if state is None:
        # --- Primera ejecución (o reset): construir cartera ---
        euro_usd = 1.13
        cash_usd = START_CAPITAL_EUR * euro_usd
        core_cash = cash_usd * NUCLEO_W
        tact_cash = cash_usd * TACTICO_W * gate   # gate aplica al despliegue táctico
        positions = {}
        buys = []

        # Libro núcleo (PEAD) — captura solo la parte disponible
        per_core = core_cash / len(core_t) if core_t else 0
        for t in core_t:
            px = float(prices[t].dropna().iloc[-1])
            shares = per_core / px
            positions[t] = {"shares": shares, "cost_usd": shares * px,
                            "entry_price": px, "book": "nucleo"}
            buys.append((shares, px))

        # Libro táctico (momentum)
        per_tact = tact_cash / len(tact_t) if tact_t else 0
        for t in tact_t:
            px = float(prices[t].dropna().iloc[-1])
            shares = per_tact / px
            positions[t] = {"shares": shares, "cost_usd": shares * px,
                            "entry_price": px, "book": "tactico"}
            buys.append((shares, px))

        cash_invested = core_cash + (tact_cash if gate > 0 else 0)
        entry_cost = su.ib_trades_cost(buys, [])
        state = {
            "start_capital_eur": START_CAPITAL_EUR,
            "start_capital_usd": START_CAPITAL_EUR * euro_usd,
            "cash_usd": cash_usd - cash_invested - entry_cost,
            "euro_usd": euro_usd,
            "positions": positions,
            "nucleo_w": NUCLEO_W, "tactico_w": TACTICO_W,
            "gate": gate,
            "created": today, "date": today, "data_date": last_price_date,
        }
        su.save_state(state, STATE_FILE)
        print(f"\n🎯 E3 PRIMERA EJECUCIÓN: {len(core_t)} núcleo + {len(tact_t)} táctico")
        print(f"   Capital: €{START_CAPITAL_EUR:,.0f} | Costes entrada: ${entry_cost:.2f}")
        print(f"   Vol-gate: {gate:.2f}")
    else:
        print("(Modo rebalanceo — para reiniciar usa --reset)")
        print(f"Esta ejecución solo construye el estado inicial. "
              f"El rebalanceo semanal sobre state_pead_core.json se hará en una ejecución posterior.")
        # Para esta primera entrega de la semana 1, nos limitamos a crear el estado.

    # Resumen
    val = float(state["cash_usd"])
    p_row = prices.iloc[-1]
    for t, pos in state["positions"].items():
        if t in p_row.index:
            val += float(pos["shares"]) * float(p_row[t])
        else:
            val += float(pos["cost_usd"])
    start = float(state["start_capital_usd"])
    print(f"\n📊 E3 — PEAD-núcleo + momentum-táctico")
    print(f"   Fecha: {today} (datos {last_price_date})")
    print(f"   Posiciones: {len(state['positions'])} | Vol-gate: {gate:.2f}")
    print(f"   Valor: ${val:,.0f} = EUR {val/state['euro_usd']:,.0f}")
    print(f"   P&L: ${val-start:+,.0f} ({(val-start)/start*100:+.2f}%)")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
