"""Paper-trading simulación 2: Estrategia momentum 120d + FILTRO PEAD NEGATIVO.

Comparativa con el momentum 120 puro (simulate.py):
- Mismo: momentum 120d, topk 30, rebalanceo semanal, costes IB tiered
- Diferencia: aplica filtro negativo por sorpresa de earnings.
  Sustituye del topk cualquier nombre cuya ÚLTIMA sorpresa sea fuertemente
  negativa (< PEAD_NEG_THRESHOLD %) por el siguiente del ranking.

Estado separado: state_pead.json (no mezcla con el momentum puro).
"""
import os, sys, json, datetime
import numpy as np
import pandas as pd

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SIM_DIR, "state_pead.json")
QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
UNIVERSE_FILE = os.path.join(QLIB_URI, "instruments/sp500_liquid.txt")
START = "2018-01-01"

MOM_W = 120
TOPK = 30
START_CAPITAL_EUR = 20000.0

# FILTRO PEAD NEGATIVO: umbral de sorpresa (%). Si la última sorpresa de un
# ticker es MENOR que esto, se excluye del topk (sustituido por el siguiente).
PEAD_NEG_THRESHOLD = -5.0
# MEJORA 1 — SUE: umbral en unidades de desviación estándar (σ). Filtra solo
# eventos catastróficos REALES del ticker, no % crudo que no es comparable.
SUE_THRESHOLD = -2.0
# MEJORA 2 — VENTANA DE FRESCURA: solo se filtra si la sorpresa es reciente.
# Pasados ~40 días hábiles, la sorpresa ya está en el precio (el drift se agota).
FRESHNESS_DAYS = 40
# Archivo de earnings (sorpresa por ticker): prioridad historial append-only
EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_appended.csv")
if not os.path.exists(EAR_FILE):
    EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_data_full.csv")
if not os.path.exists(EAR_FILE):
    EAR_FILE = os.path.join(SIM_DIR, "..", "pead_earnings_data.csv")

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
    """DataFrame de PRECIOS REALES (index fecha, columns tickers).

    Prioridad 1: prices_live.csv (del actualizador ligero update_data_light.py,
    que baja sp500_liquid desde Yahoo sin tocar el pipeline de Qlib).
    Prioridad 2: datos de Qlib (close / factor, deshaciendo el factor de splits).
    """
    # Prioridad 1: CSV fresco del actualizador ligero
    live_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices_live.csv")
    if os.path.exists(live_csv):
        import pandas as pd
        df = pd.read_csv(live_csv, index_col=0, parse_dates=True).sort_index()
        # Solo columnas que estén en el universo
        cols = [c for c in df.columns if c in tickers]
        if len(cols) > 0:
            print(f"   (usando datos frescos de {live_csv}, última fecha {df.index[-1].date()})")
            return df[cols]

    # Prioridad 2: datos Qlib (deshaciendo factor)
    close = D.features(tickers, ["$close", "$factor"], start_time=START, end_time="2100-12-31", freq="day")
    if close is None or close.empty:
        return None
    c = close["$close"].unstack(level=0).sort_index()
    f = close["$factor"].unstack(level=0).sort_index()
    real = c / f
    return real


def load_last_surprise():
    """Carga la ÚLTIMA sorpresa de earnings conocida por ticker CON metadatos.

    Devuelve un DataFrame con: ticker, surprise_pct (última), reported_ts (última),
    y sue (sorpresa normalizada por la σ histórica del ticker).

    SUE = (surprise_pct - 0) / σ_histórica(surprise_pct del ticker)
    Escala la sorpresa en unidades de desviación, comparable entre tickers.
    """
    if not os.path.exists(EAR_FILE):
        print(f"   ⚠️ No hay datos de earnings ({EAR_FILE}). Filtro PEAD inactivo.")
        return pd.DataFrame(columns=["ticker", "surprise_pct", "reported_ts", "sue"])
    ear = pd.read_csv(EAR_FILE)
    if "reported_ts" in ear.columns:
        # Última sorpresa por ticker
        max_ts = ear.groupby("ticker")["reported_ts"].transform("max")
        last = ear[ear["reported_ts"] == max_ts].copy()
        # SUE: normalizar por la desviación estándar histórica de las sorpresas del ticker
        sigma = ear.groupby("ticker")["surprise_pct"].std().rename("sigma")
        last = last.merge(sigma, on="ticker", how="left")
        last["sue"] = last["surprise_pct"] / last["sigma"].replace(0, np.nan)
        cols = ["ticker", "surprise_pct", "reported_ts", "sue"]
        # completar NaN de sigma (un solo dato) con un default conservador
        last["sue"] = last["sue"].fillna(last["surprise_pct"] / 10.0)
        return last[cols]
    # sin reported_ts -> última fila por ticker (sin SUE fiable)
    last = ear.groupby("ticker").last().reset_index()
    last["sue"] = np.nan
    return last[["ticker", "surprise_pct", "reported_ts", "sue"]] if "reported_ts" in last.columns else \
        last[["ticker", "surprise_pct", "sue"]]


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

    # --- FILTRO PEAD NEGATIVO (con SUE + ventana de frescura) ---
    surprise_df = load_last_surprise()
    today_ts = datetime.datetime.now().timestamp()
    n_filtered = 0
    excluded = []
    # Construir Set de tickers a excluir
    filter_set = set()
    if not surprise_df.empty:
        for _, row in surprise_df.iterrows():
            t = row["ticker"]
            # (1) VENTANA DE FRESCURA: si la sorpresa es vieja (> FRESHNESS_DAYS),
            #     no filtra (el drift ya se pagó). reported_ts en segundos.
            try:
                reported = float(row["reported_ts"])
            except (TypeError, ValueError):
                reported = 0.0
            if reported > 0:
                days_old = (today_ts - reported) / 86400.0
                if days_old > FRESHNESS_DAYS:
                    continue  # sorpresa vieja -> no filtrar
            # (2) SUE si está disponible, si no surprise% crudo (fallback)
            sue = row.get("sue")
            if pd.notna(sue):
                is_negative = sue < SUE_THRESHOLD
            else:
                is_negative = row["surprise_pct"] < PEAD_NEG_THRESHOLD
            if is_negative and t in mom_series.index:
                filter_set.add(t)
                excluded.append(t)
                n_filtered += 1

    # Seleccionar topk, excluyendo los filtrados (sustituir por el siguiente del ranking)
    candidate = [t for t in mom_series.index if t not in filter_set]
    if len(candidate) < TOPK:
        # si el filtro elimina demasiados, usar ranking puro (conservador)
        candidate = mom_series.index.tolist()
        print(f"   ⚠️ Filtro eliminó demasiados ({len(filter_set)}), usar ranking sin filtrar")
    new_holdings = candidate[:TOPK]
    print(f"Top {TOPK} seleccionado. Mejor: {new_holdings[0]} ({mom_series.iloc[0]*100:.1f}%)")
    if n_filtered > 0:
        print(f"   🔍 Filtro PEAD (SUE<-{SUE_THRESHOLD}σ o surprise<-{PEAD_NEG_THRESHOLD}% fresco): "
              f"excluidos {len(excluded)}: {excluded}")

    today = datetime.date.today().isoformat()
    data_date = close.index[-1].date().isoformat()

    if state is None:
        # PRIMERA EJECUCIÓN: construir cartera con capital ficticio
        cash_eur = START_CAPITAL_EUR
        euro_usd = 1.13
        cash_usd = cash_eur * euro_usd
        per_stock = cash_usd / TOPK
        positions = {}
        buys = []
        px0 = {}
        for t in new_holdings:
            s = close[t].dropna()
            price = float(s.iloc[-1])
            px0[t] = price
            shares = per_stock / price
            positions[t] = {"shares": shares, "cost_usd": shares * price, "entry_price": price}
            buys.append((shares, price))
        # Coste inicial de compra (IB tiered)
        entry_cost = ib_trades_cost(buys, [])
        cash_usd -= per_stock * TOPK  # invertido en acciones
        state = {
            "start_capital_eur": cash_eur,
            "start_capital_usd": cash_eur * euro_usd,
            "cash_usd": cash_usd - entry_cost,  # menos costes de entrada
            "entry_cost": entry_cost,
            "positions": positions,
            "euro_usd": euro_usd,
            "created": today,
            "date": today,
            "data_date": data_date,
        }
        save_state(state)
        print(f"\n🎯 PRIMERA EJECUCIÓN: compradas {len(positions)} acciones ficticias")
        print(f"   Capital inicial: €{cash_eur:,.0f} ≈ ${state['start_capital_usd']:,.0f} (EUR/USD {euro_usd})")
        print(f"   Costes IB de entrada: ${entry_cost:.2f} (30 órdenes de compra)")

    else:
        # VALORAR cartera anterior
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
        old_value = portfolio_value

        # Determinar operaciones de rebalanceo (comparar cartera actual vs nuevo topk)
        # Estrategia TopkDropout: mantenemos posiciones que siguen en el topk,
        # vendemos las que salen y compramos las que entran, con asignación igualitaria.
        # Precio de cada ticker hoy
        px = {}
        for t in set(list(positions.keys()) + new_holdings):
            if t in close.columns:
                s = close[t].dropna()
                px[t] = float(s.iloc[-1]) if len(s) > 0 else prices_get(t)
            else:
                # Ticker sin datos frescos (p.ej. salió del CSV live pero lo tenemos):
                # usar el precio de compra como fallback para no distorsionar la valoración.
                px[t] = float(positions.get(t, {}).get("entry_price", prices_get(t)))

        current = {t: float(pos["shares"]) for t, pos in positions.items()}

        # 1) VENDER posiciones que ya no están en el topk
        sells = []
        for t, sh in current.items():
            if t not in new_holdings:
                sells.append((sh, px[t]))

        # 2) COMPRAR posiciones nuevas que no teníamos, con asignación igualitaria
        #    y las que mantengamos se ajustan al nuevo peso.
        #    Presupuesto: valor total / TOPK por posición, ajustado por costes.
        buys = []
        remaining_cash_after_sells = cash_usd
        for sh, pr in sells:
            remaining_cash_after_sells += sh * pr  # efectivo liberado por ventas
        # Restar costes de las ventas
        sell_cost = ib_trades_cost([], sells)
        cash_for_buys = remaining_cash_after_sells - sell_cost

        per_stock = cash_for_buys / TOPK
        new_position_shares = {}
        for t in new_holdings:
            target_shares = per_stock / px[t]
            cur_sh = current.get(t, 0.0)
            if target_shares > cur_sh:
                buys.append(((target_shares - cur_sh), px[t]))
            elif target_shares < cur_sh:
                sells.append(((cur_sh - target_shares), px[t]))
            new_position_shares[t] = target_shares

        # 3) Calcular coste total de rebalanceo (ventas + compras)
        trades_cost = ib_trades_cost(buys, sells)

        # 4) Construir nueva cartera con asignación igualitaria, descontando costes
        new_cash = portfolio_value - trades_cost
        new_positions = {}
        remaining = new_cash
        for t in new_holdings:
            # reasignación igualitaria sobre el valor neto tras costes
            price = px[t]
            alloc = new_cash / TOPK
            shares = alloc / price
            new_positions[t] = {"shares": shares, "cost_usd": shares * price, "entry_price": price}
            remaining -= shares * price
        state["positions"] = new_positions
        state["cash_usd"] = remaining
        state["date"] = today
        state["data_date"] = data_date
        state["last_rebalance_cost"] = trades_cost
        save_state(state)

        print(f"\n📊 REBALANCEO: {len(positions)}→{len(new_holdings)} posiciones a topk {TOPK}")
        print(f"   Valor anterior: ${old_value:,.0f}")
        print(f"   Costes IB de rebalanceo: ${trades_cost:.2f} "
              f"(ventas {len(sells)} órdenes, compras {len(buys)} órd.)")
        print(f"   Valor tras costes: ${new_cash:,.0f} ({trades_cost/old_value*100:.2f}%)")

    # --- Resumen y P&L ---
    portfolio_value = state["cash_usd"]
    for t, pos in state["positions"].items():
        s = close[t].dropna() if t in close.columns else None
        if s is not None and len(s) > 0:
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

    # --- Tabla comparativa: opción FRACCIONARIA vs ENTERA, cada una con costes IB ---
    # Construir las dos variantes de cartera
    opt_frac = []   # (ticker, shares, price)
    opt_ent = []    # (ticker, shares_entera, price)
    for t, pos in state["positions"].items():
        sh = float(pos["shares"])
        pr = float(pos["entry_price"])
        ent = round(sh)
        opt_frac.append((t, sh, pr))
        if ent == 0:
            ent = 1  # mínimo 1 acción en la opción entera
        opt_ent.append((t, ent, pr))

    # Coste de COMPRA de cada opción (valor de las acciones + coste IB de las 30 órdenes)
    def _option_total(opt):
        value = sum(sh * pr for _, sh, pr in opt)
        buys = [(sh, pr) for _, sh, pr in opt]
        ib = ib_trades_cost(buys, [])
        return value, ib, value + ib

    val_f, ib_f, tot_f = _option_total(opt_frac)
    val_e, ib_e, tot_e = _option_total(opt_ent)

    print("\n" + "="*78)
    print("📊 POSICIONES — Comparativa FRACCIONARIA vs ENTERA")
    print("="*78)
    print(f"  {'Ticker':6}{'Fracc.':>8}{'Precio':>9}{'Entero':>7}{'Precio':>9}"
          f"{'CosteFr€':>9}{'CosteEn€':>9}")
    print("-"*78)
    for (t, sh, pr), (t2, ent, pr2) in zip(opt_frac, opt_ent):
        cf = sh * pr
        ce = ent * pr2
        print(f"  {t:6}{sh:>8.2f}{pr:>9.2f}{ent:>7}{pr2:>9.2f}"
              f"${cf:>8,.0f}${ce:>8,.0f}")
    print("-"*78)

    # Resumen comparativo de las DOS opciones con costes IB
    print("\n🔀 Comparación de costes de COMPRA (30 órdenes IB tiered):")
    print("  ┌───────────────────────┬─────────────┬───────────┬────────────────┐")
    print("  │ Opción                │ Acciones    │ Coste IB  │ Total (USD)    │")
    print("  ├───────────────────────┼─────────────┼───────────┼────────────────┤")
    print(f"  │ Fraccionaria (30)     │ {sum(sh for _,sh,_ in opt_frac):>11,.2f} │ ${ib_f:>9,.2f} │ ${tot_f:>14,.2f} │")
    print(f"  │ Entera (30)           │ {sum(sh for _,sh,_ in opt_ent):>11,.0f} │ ${ib_e:>9,.2f} │ ${tot_e:>14,.2f} │")
    print("  └───────────────────────┴─────────────┴───────────┴────────────────┘")

    dif = tot_e - tot_f
    print(f"\n  💡 Diferencia (entera vs fraccionaria): ${dif:+,.0f} "
          f"({'cuesta MÁS' if dif>0 else 'cuesta MENOS'})")
    print(f"  📌 Puedes replicar la fraccionaria casi exacta con acciones fraccionales de IB;")
    print(f"     con enteras necesitas {sum(sh for _,sh,_ in opt_ent):,.0f} acciones "
          f"(${val_e:,.0f} en acciones).")

    print(f"\n✅ Estado guardado en {STATE_FILE}")
    print("   (Próxima ejecución rebalanceará según nuevos datos)")


def prices_get(t):
    """Fallback: precio del ticker si no está en close."""
    return 100.0


# =====================================================================
# COSTES REALES DE INTERACTIVE BROKERS (estructura por niveles / tiered)
# Fuente: interactivebrokers.com — acciones US. No es tarifa plana:
#   - Compra: comisión = max($0.35, $0.0035 × nº acciones)
#   - Venta:  comisión = max($0.35, $0.0035 × nº acciones)
#             + SEC fee  (~$33.10 por $1M ≈ 0.00331% del valor)
#             + TAF      (~$0.00016/acción, FINRA Trading Activity Fee)
# Los cargos SEC/TAF solo aplican a VENTAS.
# =====================================================================
IB_RATE_PER_SHARE = 0.0035    # tiered ≤300k acciones/mes
IB_MIN_PER_ORDER = 0.35        # mínimo por orden (tiered)
IB_SEC_RATE = 33.10 / 1_000_000.0  # ~0.00331% del valor (ventas)
IB_TAF_PER_SHARE = 0.00016     # FINRA TAF ~$0.0001-0.0002/acción (ventas)


def ib_buy_cost(shares, price):
    """Coste total de una COMPRA de 'shares' a 'price' (USD)."""
    commission = max(IB_MIN_PER_ORDER, shares * IB_RATE_PER_SHARE)
    return commission


def ib_sell_cost(shares, price):
    """Coste total de una VENTA de 'shares' a 'price' (USD)."""
    commission = max(IB_MIN_PER_ORDER, shares * IB_RATE_PER_SHARE)
    sec_fee = shares * price * IB_SEC_RATE
    taf = shares * IB_TAF_PER_SHARE
    return commission + sec_fee + taf


def ib_trades_cost(buys, sells):
    """Coste total de una lista de operaciones.

    buys:  lista[(shares, price)] para compras
    sells: lista[(shares, price)] para ventas
    """
    total = 0.0
    for shares, price in buys:
        total += ib_buy_cost(shares, price)
    for shares, price in sells:
        total += ib_sell_cost(shares, price)
    return total



if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
