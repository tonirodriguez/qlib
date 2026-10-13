"""regime_switch_monitor.py — Monitor diario del régimen-switch v2 (para cron 08:00).

Ejecuta la señal de régimen del switch v2 sobre el histórico completo hasta HOY y emite un
mensaje legible (stdout = se entrega al cron no_agent) con:
  - Estado actual del día: LONG (invertir en BTC) o CASH (USDT con yield)
  - Precio BTC + contexto de drawdown
  - Actividad reciente (días en LONG/CASH y nº de cambios del último período)
  - Acción sugerida (sin consejo de trading)

Causal: la señal usa solo datos <= hoy. Parámetros iguales al backtest 500€ validado.

Uso (desde /opt/data/qlib):
  /opt/data/qlib-venv/bin/python work/crypto/regime_switch_monitor.py --vital-dd 0.30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from regime_switch_v2 import (  # noqa: E402
    CASH_YIELD_APY, INITIAL_USD, load_proxy, regime_signal_v2, simulate_switch,
)

START_HIST = "2020-11-01"   # mismo inicio que el backtest largo validado
LOOKBACK_CONTEXTO = 30      # días que se muestran de contexto reciente


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default="btc")
    ap.add_argument("--vital-dd", type=float, default=0.30)
    ap.add_argument("--pico-win", type=int, default=90)
    ap.add_argument("--exit-dd", type=float, default=0.30)  # salida mejorada por ATH global
    args = ap.parse_args()

    price = load_proxy(args.proxy)
    price = price[price.index >= pd.Timestamp(START_HIST, tz="UTC")]
    today = price.index[-1]

    sig = regime_signal_v2(price, args.vital_dd, args.pico_win, exit_dd=args.exit_dd)
    val, n_trades, ops = simulate_switch(price, sig)
    ret = (val / INITIAL_USD - 1) * 100

    estado_hoy = "LONG 🟢 (invertido en BTC)" if sig.iloc[-1] else "CASH 💵 (USDT con yield)"
    px_hoy = float(price.iloc[-1])
    px_antes = float(price.iloc[-LOOKBACK_CONTEXTO]) if len(price) >= LOOKBACK_CONTEXTO else float(price.iloc[0])
    chg_30 = (px_hoy / px_antes - 1) * 100

    # contexto reciente: últimos 60 días, estado y precio
    ult_60 = sig.iloc[-60:]
    dias_long_60 = int(ult_60.sum())
    dias_cash_60 = int((~ult_60).sum())

    bh = (price.iloc[-1] / price.iloc[0] - 1) * 100
    usdt = ((1 + CASH_YIELD_APY) ** (len(price) / 365.0) - 1) * 100

    # señales de alerta por régimen
    if estado_hoy.startswith("LONG"):
        accion = "Régimen al alza: mantén INVERTIDO. Vigila que el rebote no pierda fuerza."
    else:
        accion = "Régimen defensivo: mantén CASH (USDT). Espera un rebote claro del pico reciente antes de volver a LONG."

    # serie del estado para debug
    serie = "".join("L" if v else "-" for v in sig.iloc[-45:].astype(bool).values)

    lines = [
        "🔮 Régimen-Switch v2 — Monitor (BTC)",
        f"   📅 {today.date()}  |  vitäl_dd {args.vital_dd}",
        f"   📊 Precio BTC: ${px_hoy:,.0f}  ({chg_30:+.1f}% / 30d)",
        f"   🎯 Estado del día: {estado_hoy}",
        "",
        "   📈 Métricas del switch (desde 2020-11):",
        f"      retorno switch: {ret:+.1f}%  |  buy&hold BTC: {bh:+.1f}%  |  USDT puro: {usdt:+.1f}%",
        f"      cambios totales: {n_trades}  ·  días LONG (60d): {dias_long_60}  ·  días CASH (60d): {dias_cash_60}",
        f"      últimos 45d: {serie}",
        "",
        f"   💡 Acción sugerida: {accion}",
    ]
    print("\n".join(lines))
    print("")
    print("(Monitor causal: decisión con datos <= hoy. Sin consejo de trading.)")


if __name__ == "__main__":
    main()