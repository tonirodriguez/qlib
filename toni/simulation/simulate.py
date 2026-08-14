"""Paper-trading simulación: Estrategia momentum 120d + topk30 sobre sp500_liquid.

DISEÑO ROBUSTO (evita rate-limit de fuentes externas):
- Fuente PRIMARIA de precios: datos locales de Qlib (~/.qlib/qlib_data/us_data),
  que ya tenemos hasta la fecha más reciente disponible. Sin límite de red.
- Cada ejecución (semanal vía cronjob):
  1. Calcula momentum 120d por ticker con los datos Qlib del universo
  2. Selecciona el topk 30 con mayor momentum
  3. Valora la cartera anterior (o crea la inicial con el capital ficticio)
  4. Rebalancea: reconstruye la cartera al nuevo topk (asignación igualitaria)
  5. Guarda estado en state.json para la siguiente semana

Uso: python toni/simulation/simulate.py [--reset]

NOTA: usa el ÚLTIMO precio disponible en Qlib para cada ticker. Si quieres precio
intradía/más fresco, se puede añadir una fuente externa puntual para el topk,
pero el diseño base es 100% con datos Qlib (reproducible y sin rate-limit).
"""
import os, sys, json, datetime
import pandas as pd

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SIM_DIR, "state.json")
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
UNIVERSE_FILE = os.path.join(QLIB_URI, "instruments/sp500_liquid.txt")
START = "2018-01-01"

MOM_W = 120
TOPK = 30
START_CAPITAL_EUR = 20000.0

import qlib
from qlib.data import D
qlib.init(provider_uri=QLIB_URI, region='us')


def get_universe():
    tickers = []
    with open(UNIVERSE_FILE) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t:
                tickers.append(t)
    return tickers


def get_prices(tickers):
    """DataFrame de PRECIOS REALES (index fecha, columns tickers) desde Qlib.

    Qlib guarda `$close` NORMALIZADO por un factor de splits. El precio real de
    mercado es `$close / $factor`. Este helper deshace el factor.
    """
    close = D.features(tickers, ["$close", "$factor"], start_time=START, end_time="2100-12-31", freq="day")
    if close is None or close.empty:
        return None
    c = close["$close"].unstack(level=0).sort_index()
    f = close["$factor"].unstack(level=0).sort_index()
    # Precio real = close / factor
    real = c / f
    return real


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        # Convertir valores numéricos que pudieron guardarse como str a float
        for k in ("cash_usd", "start_capital_eur", "start_capital_usd", "euro_usd"):
            if k in state and isinstance(state[k], str):
                state[k] = float(state[k])
        for t, pos in state.get("positions", {}).items():
            for k in ("shares", "cost_usd", "entry_price"):
                if k in pos and isinstance(pos[k], str):
                    pos[k] = float(pos[k])
        return state
    return None


def save_state(state):
    # Convertir a float nativo de Python para JSON (numpy.float no es serializable)
    positions = {}
    for t, pos in state.get("positions", {}).items():
        positions[t] = {
            "shares": float(pos["shares"]),
            "cost_usd": float(pos["cost_usd"]),
            "entry_price": float(pos["entry_price"]),
        }
    out = dict(state)
    out["positions"] = positions
    out["cash_usd"] = float(out["cash_usd"])
    with open(STATE_FILE, "w") as f:
        json.dump(out, f, indent=2)


def main(reset=False):
    tickers = get_universe()
    print(f"Universo: {len(tickers)} tickers (sp500_liquid)")

    state = None if reset else load_state()
    if state:
        print(f"Estado previo (última ejecución: {state.get('date','?')})")
    else:
        print("Sin estado previo → PRIMERA ejecución (construir cartera inicial)")

    # Cargar precios de Qlib (una sola lectura, sin red)
    print("Cargando precios desde Qlib (local)...")
    close = get_prices(tickers)
    if close is None or close.empty:
        print("ERROR: no se pudieron cargar datos de Qlib. Revisa QLIB_URI.")
        return
    print(f"Datos Qlib: {close.shape[0]} fechas, {close.shape[1]} tickers")
    print(f"Última fecha disponible: {close.index[-1].date()}")

    # Calcular momentum 120d por ticker con el último dato
    mom = {}
    for t in close.columns:
        s = close[t].dropna()
        if len(s) > MOM_W:
            mom[t] = s.iloc[-1] / s.iloc[-1 - MOM_W] - 1
    mom_series = pd.Series(mom).dropna().sort_values(ascending=False)
    print(f"Señal momentum calculada en {len(mom_series)} tickers")

    new_holdings = mom_series.head(TOPK).index.tolist()
    print(f"Top {TOPK} seleccionado. Mejor: {new_holdings[0]} ({mom_series.iloc[0]*100:.1f}%)")

    today = datetime.date.today().isoformat()
    data_date = close.index[-1].date().isoformat()

    if state is None:
        # PRIMERA EJECUCIÓN: construir cartera con capital ficticio
        cash_eur = START_CAPITAL_EUR
        # Conversión EUR->USD aproximada (constante base; se puede afinar)
        euro_usd = 1.13
        cash_usd = cash_eur * euro_usd
        per_stock = cash_usd / TOPK
        positions = {}
        for t in new_holdings:
            s = close[t].dropna()
            price = s.iloc[-1]
            shares = per_stock / price
            positions[t] = {"shares": shares, "cost_usd": shares * price, "entry_price": price}
            cash_usd -= shares * price
        state = {
            "start_capital_eur": cash_eur,
            "start_capital_usd": cash_eur * euro_usd,
            "cash_usd": cash_usd,
            "positions": positions,
            "euro_usd": euro_usd,
            "created": today,
            "date": today,
            "data_date": data_date,
        }
        save_state(state)
        print(f"\n🎯 PRIMERA EJECUCIÓN: compradas {len(positions)} acciones ficticias")
        print(f"   Capital inicial: €{cash_eur:,.0f} ≈ ${state['start_capital_usd']:,.0f} (EUR/USD {euro_usd})")

    else:
        # VALORAR cartera anterior (sin rebalancear del todo — simular TopkDropout básico)
        positions = state["positions"]
        cash_usd = state["cash_usd"]
        portfolio_value = cash_usd
        for t, pos in positions.items():
            s = close[t].dropna() if t in close.columns else None
            if s is not None and len(s) > 0:
                cur = float(s.iloc[-1])
                portfolio_value += float(pos["shares"]) * cur
            else:
                portfolio_value += float(pos["cost_usd"])

        # Simular TopkDropout simple: reasignar igualitariamente a los nuevos topk
        # (aproximación; en Qlib con n_drop este es el comportamiento habitual)
        new_cash = portfolio_value / TOPK
        new_positions = {}
        remaining = portfolio_value
        for t in new_holdings:
            s = close[t].dropna()
            price = s.iloc[-1] if len(s) > 0 else prices_get(t)
            shares = new_cash / price
            new_positions[t] = {"shares": shares, "cost_usd": shares * price, "entry_price": price}
            remaining -= shares * price
        state["positions"] = new_positions
        state["cash_usd"] = remaining
        state["date"] = today
        state["data_date"] = data_date
        save_state(state)

        print(f"\n📊 REBALANCEO: {len(positions)}→{len(new_holdings)} posiciones a topk {TOPK}")

    # --- Resumen y P&L ---
    portfolio_value = state["cash_usd"]
    for t, pos in state["positions"].items():
        s = close[t].dropna()
        if len(s) > 0:
            portfolio_value += pos["shares"] * s.iloc[-1]
        else:
            portfolio_value += pos["cost_usd"]
    start_usd = state["start_capital_usd"]
    euro_usd = state["euro_usd"]
    pnl_usd = portfolio_value - start_usd
    pnl_pct = pnl_usd / start_usd * 100

    print("\n" + "="*52)
    print("📈 ESTADO DE LA SIMULACIÓN (dinero ficticio)")
    print("="*52)
    print(f"  Capital inicial:      €{state['start_capital_eur']:,.0f} (${start_usd:,.0f})")
    print(f"  Valor cartera actual: ${portfolio_value:,.0f} = EUR {portfolio_value/euro_usd:,.0f}")
    print(f"  P&L ficticio:         {pnl_usd:+,.0f} USD = EUR {pnl_usd/euro_usd:+,.0f} ({pnl_pct:+.2f}%)")
    print(f"  Posiciones:           {len(state['positions'])}")
    print(f"  Fecha de simulación:  {today} (datos de {data_date})")

    # --- Tabla de posiciones: fraccionarias y redondeadas a entero ---
    print("\n" + "="*60)
    print("📊 POSICIONES DE LA SIMULACIÓN")
    print("="*60)
    print(f"{'Ticker':6}{'Fracc.':>8}{'Entero':>7}{'Precio':>9}{'CosteFr.$':>11}{'CosteEn$':>9}")
    print("-"*60)
    tf = 0.0; te = 0.0
    for t, pos in state["positions"].items():
        sh = float(pos["shares"])
        pr = float(pos["entry_price"])
        ent = round(sh)          # redondeo a entero
        cf = sh * pr             # coste fraccionario
        ce = ent * pr            # coste si se usa la versión entera
        tf += cf; te += ce
        print(f"{t:6}{sh:>8.2f}{ent:>7}{pr:>9.2f}${cf:>9,.0f}${ce:>8,.0f}")
    print("-"*60)
    print(f"{'TOTAL':6}{'':>8}{'':>7}{'':>9}${tf:>9,.0f}${te:>8,.0f}")
    print(f"\n  Coste versión fraccionaria: ${tf:,.0f} = EUR {tf/euro_usd:,.0f}")
    print(f"  Coste versión redondeada:   ${te:,.0f} = EUR {te/euro_usd:,.0f}")

    print(f"\n✅ Estado guardado en {STATE_FILE}")
    print("   (Próxima ejecución rebalanceará según nuevos datos)")


def prices_get(t):
    """Fallback: precio del ticker si no está en close."""
    return 100.0


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
