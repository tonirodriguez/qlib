"""
sfm_paper_trading.py — Paper Trading para SFM v8 con señales diarias.

Lee las señales generadas por sfm_daily_signal.py y simula operaciones
de compra/venta con capital ficticio, registrando resultados.

DISEÑO:
- Fuente de precios: datos locales de Qlib (data/qlib/) — sin límite de red
- Señal de entrada: signal_YYYY-MM-DD.json generado por sfm_daily_signal.py
- Estrategia: COMPRAR la cripto con mejor score si confianza ALTA
- Capital inicial: 10,000 USD ficticios
- Costes: 0.1% por operación (como en el backtest)
- Estado persistente en state_paper_trading.json

Uso:
  conda run -n qlib python work/crypto/sfm_paper_trading.py
  conda run -n qlib python work/crypto/sfm_paper_trading.py --reset   # Reiniciar desde cero
  conda run -n qlib python work/crypto/sfm_paper_trading.py --report  # Solo ver reporte

Variables de entorno:
  PAPER_START_CAPITAL: capital inicial en USD (default: 10000)
  PAPER_MAX_POSITIONS: máximas posiciones abiertas (default: 2)
  PAPER_MIN_CONFIDENCE: confianza mínima para entrar (default: ALTA)
"""

import os, sys, json, pickle
from pathlib import Path
from datetime import datetime, date, timedelta
import numpy as np
import pandas as pd

import risk_controls as rc

import warnings
warnings.filterwarnings("ignore")


# =====================================================================
# CONFIGURACIÓN
# =====================================================================

PROJECT_ROOT = Path(__file__).resolve().parent  # work/crypto/
OUTPUT_DIR = PROJECT_ROOT / "output" / "sfm_v8"
STATE_FILE = OUTPUT_DIR / "state_paper_trading.json"
HISTORY_FILE = OUTPUT_DIR / "history_paper_trading.csv"

# --- Fee de Binance real (punto 3) ---
# Por defecto la cuenta base de Binance spot: 0.1% taker. Si se provee el
# JSON del fee schedule real de Binance vía CRYPTO_FEE_SCHEDULE_JSON (con
# tiers por volumen), se carga y se usa el tier base (volumen 0).
def _load_binance_fee() -> float:
    """Devuelve la fee taker de la cuenta base de Binance (0.1%) o la del JSON si se da."""
    import importlib.util
    sched_path = os.getenv("CRYPTO_FEE_SCHEDULE_JSON")
    if sched_path and Path(sched_path).exists():
        try:
            import execution_costs_v2 as ec
            sched = ec.load_fee_schedule(sched_path)
            tier0 = ec.select_fee_tier(sched, 0.0)
            fee = ec.blended_fee(tier0, float(os.getenv("CRYPTO_TAKER_FRACTION", "1.0")))
            return fee
        except Exception as exc:  # noqa
            print(f"   ⚠️  No se pudo usar fee schedule ({exc}); se usa fee base 0.1%")
            return 0.0010
    return float(os.getenv("PAPER_TRANSACTION_COST", "0.0010"))


TRANSACTION_COST = _load_binance_fee()  # Binance base taker 0.1% (o la del schedule)
START_CAPITAL = float(os.getenv("PAPER_START_CAPITAL", "10000"))
MAX_POSITIONS = int(os.getenv("PAPER_MAX_POSITIONS", "2"))
MIN_CONFIDENCE = os.getenv("PAPER_MIN_CONFIDENCE", "ALTA")

# --- Risk controls (punto 1) ---
RISK_CONFIG = {
    "max_signal_age_days": int(os.getenv("RISK_MAX_SIGNAL_AGE_DAYS", "1")),
    "max_drawdown_pct": float(os.getenv("RISK_MAX_DRAWDOWN_PCT", "0.15")),
    "max_per_asset_exposure_pct": float(os.getenv("RISK_MAX_ASSET_EXPOSURE_PCT", "0.40")),
    "max_total_exposure_pct": float(os.getenv("RISK_MAX_TOTAL_EXPOSURE_PCT", "0.90")),
    "kill_switch_enabled": os.getenv("RISK_KILL_SWITCH", "1") == "1",
}
# Si este archivo existe, la operación queda bloqueada (kill-switch manual)
KILL_SWITCH_FILE = OUTPUT_DIR / "KILL_SWITCH"

SYMBOLS_ORDER = ["BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC"]


# =====================================================================
# ESTADO PERSISTENTE
# =====================================================================

def default_state():
    return {
        "capital_usd": START_CAPITAL,
        "cash_usd": START_CAPITAL,
        "positions": {},      # { "BTC": {"shares": 0.5, "entry_price": 50000, "entry_date": "2026-09-01"} }
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "total_fees_paid": 0.0,
        "peak_capital": START_CAPITAL,
        "last_updated": None,
        "created_at": datetime.utcnow().isoformat(),
    }


def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return default_state()


def save_state(state):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"   💾 Estado guardado: {STATE_FILE}")


# =====================================================================
# PRECIOS DESDE QLIB
# =====================================================================

def get_latest_prices(cryptos):
    """
    Obtiene el último precio disponible de cada cripto desde Qlib.
    Devuelve dict: { "BTC": 65000.0, ... }
    """
    import qlib
    from qlib.config import REG_US
    from qlib.data import D

    PROVIDER_URI = os.getenv("CRYPTO_QLIB_OUTPUT_DIR", "data/qlib")
    qlib.init(provider_uri=PROVIDER_URI, region=REG_US, kernels=1)

    prices = {}
    for c in cryptos:
        df_c = D.features([c.lower()], ["$close"],
                          start_time="2026-01-01",
                          end_time=pd.Timestamp.utcnow().tz_localize(None))
        if df_c is not None and not df_c.empty:
            df_c = df_c.reset_index()
            series = df_c.pivot(index="datetime", columns="instrument", values="$close")[c.lower()]
            last_price = float(series.dropna().iloc[-1])
            prices[c] = last_price
        else:
            prices[c] = None
    return prices


# =====================================================================
# VALORACIÓN DE CARTERA
# =====================================================================

def value_portfolio(state, prices):
    """
    Calcula el valor total actual de la cartera.
    state: estado actual
    prices: dict con precios actuales { "BTC": 65000 }
    Retorna: (total_value_usd, positions_value)
    """
    positions_value = 0.0
    position_details = []

    for symbol, pos in state.get("positions", {}).items():
        shares = pos["shares"]
        entry_price = pos["entry_price"]
        current_price = prices.get(symbol)

        if current_price is not None:
            current_value = shares * current_price
            pnl_pct = (current_price - entry_price) / entry_price
            positions_value += current_value
            position_details.append({
                "symbol": symbol,
                "shares": shares,
                "entry_price": entry_price,
                "current_price": current_price,
                "current_value": current_value,
                "pnl_pct": round(pnl_pct * 100, 2),
                "pnl_usd": round(current_value - shares * entry_price, 2),
                "entry_date": pos.get("entry_date", "?"),
            })

    total_value = state["cash_usd"] + positions_value
    return total_value, position_details


# =====================================================================
# EJECUCIÓN DE OPERACIONES
# =====================================================================

def execute_trades(state, signal_data, prices):
    """
    Ejecuta las operaciones según la señal del día.
    1. Vende posiciones que ya no tienen señal COMPRA
    2. Compra nuevas posiciones si hay señal y cupo
    """
    today = date.today().isoformat()
    signals = signal_data.get("signals", [])
    trades_executed = []

    # --- 1. Procesar ventas ---
    symbols_to_sell = set()
    for s in signals:
        # Vender si la señal no es COMPRA (ESPERAR, NEUTRAL, VENTA)
        if "COMPRA" not in s["signal"] and s["crypto"] in state.get("positions", {}):
            symbols_to_sell.add(s["crypto"])

    for symbol in symbols_to_sell:
        pos = state["positions"].pop(symbol, None)
        if pos is None:
            continue
        shares = pos["shares"]
        entry_price = pos["entry_price"]
        exit_price = prices.get(symbol)

        if exit_price is None:
            continue  # no hay precio, posiciones congeladas

        gross_value = shares * exit_price
        fee = gross_value * TRANSACTION_COST
        net_value = gross_value - fee

        state["cash_usd"] += net_value
        state["total_fees_paid"] += fee
        state["total_trades"] += 1

        pnl_pct = (exit_price - entry_price) / entry_price
        if pnl_pct > 0:
            state["wins"] += 1
        else:
            state["losses"] += 1

        trades_executed.append({
            "date": today,
            "type": "SELL",
            "symbol": symbol,
            "shares": shares,
            "price": exit_price,
            "gross_value": round(gross_value, 2),
            "fee": round(fee, 2),
            "net_value": round(net_value, 2),
            "pnl_pct": round(pnl_pct * 100, 2),
            "reason": f"Señal: {next((s['signal'] for s in signals if s['crypto'] == symbol), '?')}",
        })

    # --- 2. Procesar compras ---
    current_positions = len(state["positions"])
    available_slots = MAX_POSITIONS - current_positions

    if available_slots > 0:
        # Buscar señales de COMPRA con confianza suficiente
        buy_candidates = [
            s for s in signals
            if "COMPRA" in s["signal"]
            and s["confidence"] == MIN_CONFIDENCE
            and s["crypto"] not in state["positions"]
        ]

        for s in buy_candidates[:available_slots]:
            symbol = s["crypto"]
            price = prices.get(symbol)
            if price is None or price <= 0:
                continue

            # Asignar capital equitativamente entre las nuevas posiciones
            capital_per_position = state["cash_usd"] / (available_slots + 1)
            capital_per_position = min(capital_per_position, state["cash_usd"])

            if capital_per_position < 10:
                continue  # no merece la pena

            shares_to_buy = capital_per_position / price
            fee = capital_per_position * TRANSACTION_COST
            cost = shares_to_buy * price + fee

            if cost > state["cash_usd"]:
                shares_to_buy = (state["cash_usd"] - fee) / price
                cost = shares_to_buy * price + fee

            state["positions"][symbol] = {
                "shares": shares_to_buy,
                "entry_price": price,
                "entry_date": today,
            }
            state["cash_usd"] -= cost
            state["total_fees_paid"] += fee
            state["total_trades"] += 1

            trades_executed.append({
                "date": today,
                "type": "BUY",
                "symbol": symbol,
                "shares": round(shares_to_buy, 6),
                "price": price,
                "cost": round(cost, 2),
                "fee": round(fee, 2),
                "cash_after": round(state["cash_usd"], 2),
                "reason": f"Score: {s['score']:+.4f}, Confianza: {s['confidence']}",
            })

    return trades_executed


# =====================================================================
# REPORTE
# =====================================================================

def print_portfolio_report(total_value, cash, position_details, trades, state):
    print(f"\n{'='*58}")
    print(f"📊 PAPER TRADING SFM v8 — {date.today().isoformat()}")
    print(f"{'='*58}")

    # Resumen capital
    total_gain_pct = ((total_value - START_CAPITAL) / START_CAPITAL) * 100
    print(f"\n💰 CAPITAL: ${total_value:,.2f}  (${cash:,.2f} cash + ${total_value-cash:,.2f} posiciones)")
    print(f"   Ganancia total: {total_gain_pct:+.2f}%  |  Pico: ${state.get('peak_capital', START_CAPITAL):,.2f}")
    print(f"   Operaciones: {state['total_trades']}  |  Wins: {state['wins']}  |  Losses: {state['losses']}")

    if state["total_trades"] > 0:
        win_rate = 100 * state["wins"] / state["total_trades"]
        print(f"   Win Rate: {win_rate:.1f}%")

    # Posiciones activas
    if position_details:
        print(f"\n📈 POSICIONES ACTIVAS ({len(position_details)}):")
        print(f"{'Symbol':<8} {'Shares':<12} {'Entry':<12} {'Current':<12} {'Value':<12} {'P&L':<10} {'P&L%':<10}")
        print(f"{'-'*66}")
        for p in position_details:
            print(f"{p['symbol']:<8} {p['shares']:<12.4f} ${p['entry_price']:<9,.2f} ${p['current_price']:<9,.2f} "
                  f"${p['current_value']:<9,.2f} ${p['pnl_usd']:<+7,.2f} {p['pnl_pct']:<+7.2f}%")

    # Operaciones del día
    if trades:
        print(f"\n🔄 OPERACIONES DE HOY ({len(trades)}):")
        for t in trades:
            if t["type"] == "BUY":
                print(f"   🟢 COMPRA {t['symbol']:5s}  {t['shares']:.4f} sh  @ ${t['price']:>8,.2f}  "
                      f"Coste: ${t['cost']:,.2f}  |  {t['reason']}")
            else:
                print(f"   🔻 VENTA {t['symbol']:5s}  {t['shares']:.4f} sh  @ ${t['price']:>8,.2f}  "
                      f"Neto: ${t['net_value']:,.2f}  P&L: {t['pnl_pct']:+7.2f}%  |  {t['reason']}")
    else:
        print(f"\n   ⏸️  Sin operaciones hoy")

    print(f"{'='*58}\n")


def print_report_only(state, prices):
    """Solo muestra el reporte sin ejecutar operaciones."""
    total_value, position_details = value_portfolio(state, prices)
    print_portfolio_report(total_value, state["cash_usd"], position_details, [], state)


# =====================================================================
# HISTORIAL
# =====================================================================

def _save_metrics_from_history():
    """Guarda el JSON de metricas del paper desde el historial (Paso 6)."""
    try:
        from paper_metrics import returns_from_history, compute_metrics, save_metrics
        if HISTORY_FILE.exists():
            returns = returns_from_history(HISTORY_FILE, START_CAPITAL)
            metrics = compute_metrics(returns, START_CAPITAL)
            save_metrics(metrics)
    except Exception as exc:  # pragma: no cover
        print(f"   ⚠️  No se pudieron calcular metricas: {exc}")


def append_history(state, total_value, trades):
    """Añade una entrada al historial CSV."""
    today = date.today().isoformat()
    n_positions = len(state["positions"])
    total_gain_pct = ((total_value - START_CAPITAL) / START_CAPITAL) * 100

    record = {
        "date": today,
        "total_value": round(total_value, 2),
        "cash": round(state["cash_usd"], 2),
        "positions_value": round(total_value - state["cash_usd"], 2),
        "n_positions": n_positions,
        "total_gain_pct": round(total_gain_pct, 2),
        "peak_capital": round(state.get("peak_capital", START_CAPITAL), 2),
        "total_trades": state["total_trades"],
        "wins": state["wins"],
        "losses": state["losses"],
        "n_trades_today": len(trades),
    }

    df = pd.DataFrame([record])
    if HISTORY_FILE.exists():
        df_history = pd.read_csv(HISTORY_FILE)
        # Deduplicar por fecha: conservar solo un registro por dia (el actualizado)
        df = pd.concat([df_history, df], ignore_index=True)
        if "date" in df.columns:
            df = df.drop_duplicates(subset=["date"], keep="last")
    df = df.sort_values("date") if "date" in df.columns else df
    df.to_csv(HISTORY_FILE, index=False)
    print(f"   💾 Historial guardado: {HISTORY_FILE} ({len(df)} registros)")


# =====================================================================
# MAIN
# =====================================================================

def main():
    # Parsear argumentos
    do_reset = "--reset" in sys.argv
    do_report_only = "--report" in sys.argv

    if do_reset:
        state = default_state()
        save_state(state)
        print(f"✅ Cartera reiniciada con ${START_CAPITAL:,.2f}")
        return

    # Cargar estado
    state = load_state()

    # Buscar la señal más reciente
    signal_files = sorted(OUTPUT_DIR.glob("signal_*.json"), reverse=True)
    if not signal_files:
        print("❌ No hay señales diarias disponibles.")
        print(f"   Ejecuta primero: conda run -n qlib python work/crypto/sfm_daily_signal.py")
        return

    latest_signal = signal_files[0]
    with open(latest_signal) as f:
        signal_data = json.load(f)

    signal_date = signal_data["date"]
    print(f"📡 Señal del día: {signal_date} ({latest_signal.name})")

    # Obtener precios actuales
    print(f"📥 Obteniendo precios desde Qlib...")
    cryptos = [s["crypto"] for s in signal_data["signals"]]
    prices = get_latest_prices(cryptos)

    active_prices = {k: v for k, v in prices.items() if v is not None}
    print(f"   Precios obtenidos: {len(active_prices)}/{len(cryptos)} criptos")

    if do_report_only:
        print_report_only(state, active_prices)
        return

    # =================================================================
    # RISK CONTROLS (punto 1) — bloquean antes de operar
    # =================================================================
    # 0) Kill-switch manual: si existe el archivo KILL_SWITCH, parar.
    if KILL_SWITCH_FILE.exists():
        print("   🛑 KILL-SWITCH: archivo KILL_SWITCH presente. Operación bloqueada.")
        total_kill, _ = value_portfolio(state, active_prices)
        append_history(state, total_kill, [])
        _save_metrics_from_history()
        print_report_only(state, active_prices)
        return

    issues = rc.run_all_checks(
        state,
        active_prices,
        signal_date,
        config=RISK_CONFIG,
    )
    if issues:
        print("   ⛔ OPERACIÓN BLOQUEADA por controles de riesgo:")
        rc.emit_alerts(issues)
        # Notificar alertas de riesgo por Telegram (Paso 7)
        try:
            from notifications import send_message
            body = "\n".join(f"🚨 {m}" for m in issues)
            send_message(body, subject="⚠️ RIESGO v8 — operación bloqueada")
        except Exception:
            pass
        # Persistir el estado (pico) pero sin operar
        total_block, _ = value_portfolio(state, active_prices)
        if total_block > state["peak_capital"]:
            state["peak_capital"] = total_block
        state["last_updated"] = datetime.utcnow().isoformat()
        save_state(state)
        append_history(state, total_block, [])
        _save_metrics_from_history()
        print_report_only(state, active_prices)
        return

    # Ejecutar operaciones según la señal
    trades = execute_trades(state, signal_data, active_prices)

    # Valorar cartera
    total_value, position_details = value_portfolio(state, active_prices)

    # Actualizar pico de capital
    if total_value > state["peak_capital"]:
        state["peak_capital"] = total_value

    # Guardar estado
    state["last_updated"] = datetime.utcnow().isoformat()
    save_state(state)

    # Guardar historial
    append_history(state, total_value, trades)
    # Guardar metricas (Paso 6)
    _save_metrics_from_history()
    # Notificacion diaria por Telegram (Paso 7) — no bloquea la operacion
    try:
        from notifications import send_message
        total_gain_pct = ((total_value - START_CAPITAL) / START_CAPITAL) * 100
        summary = (
            f"📊 PAPER TRADING v8 — {date.today().isoformat()}\n"
            f"   Capital: ${START_CAPITAL:,.0f} → ${total_value:,.2f} ({total_gain_pct:+.2f}%)\n"
            f"   Posiciones: {len(state['positions'])} | Trades: {state['total_trades']}"
        )
        if trades:
            summary += f"\n   Operaciones hoy: {len(trades)}"
        send_message(summary, subject="🔔 Resumen diario v8")
    except Exception as _nexc:
        print(f"   ⚠️  No se pudo notificar: {_nexc}")

    # Mostrar reporte
    print_portfolio_report(total_value, state["cash_usd"], position_details, trades, state)

    # Resumen ejecutivo
    total_gain_pct = ((total_value - START_CAPITAL) / START_CAPITAL) * 100
    print(f"📋 RESUMEN PAPER TRADING — {date.today().isoformat()}")
    print(f"   Capital: ${START_CAPITAL:,.0f} → ${total_value:,.2f}  ({total_gain_pct:+.2f}%)")
    print(f"   Operaciones totales: {state['total_trades']}  |  Win Rate: {100*state['wins']/max(state['total_trades'],1):.1f}%")
    print(f"   Posiciones activas: {len(state['positions'])}")
    if trades:
        print(f"   Operaciones hoy: {len(trades)} ({sum(1 for t in trades if t['type']=='BUY')} compras, {sum(1 for t in trades if t['type']=='SELL')} ventas)")


if __name__ == "__main__":
    import warnings
    main()