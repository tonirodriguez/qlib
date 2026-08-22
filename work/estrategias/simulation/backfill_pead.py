"""Reconstrucción retroactiva del paper-trading PEAD (momentum + filtro).

Simula la estrategia momentum 120d + filtro PEAD negativo desde el 14-ago-2026
(primer rebalanceo, cuando arrancó el momentum puro) hasta el último dato
disponible (21-ago), para ponerla en paralelo con el momentum 120 puro que ya
corre. El resultado es el state_pead.json con la cartera reconstruida,
para que simulate_pead.py continúe desde ahí.

No toca simulate.py (momentum puro). Genera UNICAMENTE state_pead.json.
"""
import os, json, datetime
import pandas as pd

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SIM_DIR, "state_pead.json")
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
UNIVERSE_FILE = os.path.join(QLIB_URI, "instruments/sp500_liquid.txt")
LIVE_CSV = os.path.join(SIM_DIR, "prices_live.csv")
EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_data_full.csv")
if not os.path.exists(EAR_FILE):
    EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_data.csv")

MOM_W = 120
TOPK = 30
START_CAPITAL_EUR = 20000.0
PEAD_NEG_THRESHOLD = -5.0
EURO_USD = 1.13


def get_universe():
    tk = []
    with open(UNIVERSE_FILE) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t: tk.append(t)
    return tk


def get_prices():
    df = pd.read_csv(LIVE_CSV, index_col=0, parse_dates=True).sort_index()
    return df


def load_last_surprise():
    if not os.path.exists(EAR_FILE):
        return {}
    ear = pd.read_csv(EAR_FILE)
    if "reported_ts" in ear.columns:
        max_ts = ear.groupby("ticker")["reported_ts"].transform("max")
        last = ear[ear["reported_ts"] == max_ts]
        return dict(zip(last["ticker"], last["surprise_pct"]))
    last = ear.groupby("ticker").last()
    return dict(zip(last.index, last["surprise_pct"]))


def ib_buy_cost(shares, price):
    return max(0.35, shares * 0.0035)


def ib_sell_cost(shares, price):
    commission = max(0.35, shares * 0.0035)
    sec = shares * price * (33.10 / 1_000_000.0)
    taf = shares * 0.00016
    return commission + sec + taf


def ib_trades_cost(buys, sells):
    return sum(ib_buy_cost(s, p) for s, p in buys) + sum(ib_sell_cost(s, p) for s, p in sells)


def momentum_at(prices, date):
    """Momentum 120d calculado en la fecha dada."""
    if date not in prices.index:
        # usar la fecha más próxima anterior
        valid = prices.index[prices.index <= date]
        if len(valid) == 0:
            return pd.Series(dtype=float)
        date = valid[-1]
    d = prices.loc[date]
    idx = prices.index.get_indexer([date])[0]
    if idx < MOM_W:
        return pd.Series(dtype=float)
    prev = prices.iloc[idx - MOM_W]
    mom = d / prev - 1
    return mom.dropna().sort_values(ascending=False)


def main():
    tickers = get_universe()
    prices = get_prices()
    surprise = load_last_surprise()
    all_dates = [d for d in prices.index if d.weekday() < 5]

    # Fechas de rebalanceo: 14-ago (primer), 21-ago (segundo) - días con datos
    # usamos el viernes de cada semana con datos
    rebal_dates = []
    for d in all_dates:
        ds = d.strftime("%Y-%m-%d")
        if ds in ("2026-08-14", "2026-08-21"):
            rebal_dates.append(d)
    if len(rebal_dates) < 2:
        # fallback: últimos 2 viernes
        fridays = [d for d in all_dates if d.weekday() == 4][-2:]
        rebal_dates = fridays
    print(f"Fechas de rebalanceo reconstruidas: {[d.date() for d in rebal_dates]}")

    state = None
    for date in rebal_dates:
        date_str = date.strftime("%Y-%m-%d")
        mom = momentum_at(prices, date)
        if mom.empty:
            print(f"  {date_str}: sin momentum suficiente, skip")
            continue

        # Ranking momentum
        ranked = mom.index.tolist()
        # Aplicar FILTRO PEAD NEGATIVO: excluir del ranking los que tengan
        # sorpresa < umbral, pero mantener el flujo (sustituir por el siguiente)
        filtered = [t for t in ranked if not (t in surprise and surprise[t] < PEAD_NEG_THRESHOLD)]
        if len(filtered) < TOPK:
            filtered = ranked  # si el filtro elimina demasiados, no filtrar
            print(f"  {date_str}: filtro eliminó de más, usar ranking puro")
        new_holdings = filtered[:TOPK]

        # Precio en la fecha
        if date in prices.index:
            p_row = prices.loc[date]
        else:
            valid = prices.index[prices.index <= date]
            p_row = prices.loc[valid[-1]]

        if state is None:
            # PRIMERA cartera (14-ago)
            cash_usd = START_CAPITAL_EUR * EURO_USD
            per_stock = cash_usd / TOPK
            positions = {}
            buys = []
            for t in new_holdings:
                if t not in prices.columns:
                    continue
                price = float(p_row[t]) if t in p_row.index else per_stock / 100
                shares = per_stock / price
                positions[t] = {"shares": shares, "cost_usd": shares * price, "entry_price": price}
                buys.append((shares, price))
            entry_cost = ib_trades_cost(buys, [])
            cash_usd -= per_stock * TOPK
            state = {
                "start_capital_eur": START_CAPITAL_EUR,
                "start_capital_usd": START_CAPITAL_EUR * EURO_USD,
                "cash_usd": cash_usd - entry_cost,
                "entry_cost": entry_cost,
                "positions": positions,
                "euro_usd": EURO_USD,
                "created": date_str,
                "date": date_str,
                "data_date": date_str,
                "rebalances": [date_str],
            }
            print(f"  🎯 {date_str}: cartera inicial {len(positions)} posiciones (filtro PEAD)")
        else:
            # REBALANCEAR a la fecha siguiente
            old_positions = state["positions"]
            cash_usd = state["cash_usd"]
            # valorar
            portfolio_value = cash_usd
            for t, pos in old_positions.items():
                if t in prices.columns and date in prices.index and t in p_row.index:
                    portfolio_value += float(pos["shares"]) * float(p_row[t])
                else:
                    portfolio_value += float(pos["cost_usd"])
            # costes de rebalanceo (aprox): rotación de posiciones que salen/entran
            old_set = set(old_positions.keys())
            new_set = set(new_holdings)
            out = old_set - new_set
            inn = new_set - old_set
            sells = []
            buys = []
            for t in out:
                if t in old_positions and t in prices.columns and t in p_row.index:
                    sells.append((float(old_positions[t]["shares"]), float(p_row[t])))
            for t in inn:
                if t in prices.columns and t in p_row.index:
                    buys.append((portfolio_value / TOPK / float(p_row[t]), float(p_row[t])))
            cost = ib_trades_cost(buys, sells)
            # reconstruir con asignación igualitaria neta
            net = portfolio_value - cost
            new_positions = {}
            remaining = net
            for t in new_holdings:
                if t not in prices.columns or t not in p_row.index:
                    continue
                price = float(p_row[t])
                alloc = net / TOPK
                shares = alloc / price
                new_positions[t] = {"shares": shares, "cost_usd": shares * price, "entry_price": price}
                remaining -= shares * price
            state["positions"] = new_positions
            state["cash_usd"] = remaining
            state["date"] = date_str
            state["data_date"] = date_str
            state.setdefault("rebalances", []).append(date_str)
            state["last_rebalance_cost"] = cost
            print(f"  🔄 {date_str}: rebalanceo → {len(new_positions)} posiciones (coste IB ${cost:.2f})")

    if state is None:
        print("No se pudo reconstruir la estrategia.")
        return

    # Resumen final
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=float)
    print(f"\n✅ state_pead.json generado (reconstructción 14→21-ago)")
    print(f"   Fecha: {state['date']} | Posiciones: {len(state['positions'])}")
    # valor actual
    p_row = prices.iloc[-1]
    val = float(state["cash_usd"])
    for t, pos in state["positions"].items():
        if t in p_row.index:
            val += float(pos["shares"]) * float(p_row[t])
        else:
            val += float(pos["cost_usd"])
    start = float(state["start_capital_usd"])
    print(f"   Valor: ${val:,.0f} = EUR {val/state['euro_usd']:,.0f}")
    print(f"   P&L: ${val-start:+,.0f} ({(val-start)/start*100:+.2f}%)")
    print(f"   (para comparar, momentum puro estaba en -2.45%)")


if __name__ == "__main__":
    main()
