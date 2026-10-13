"""monitor_combinado.py — DECISIÓN DIARIA combinando RÉGIMEN-SWITCH (gate) + v8 (confirmación).

Lógica de decisión en 2 capas (la que Toni pidió fijar para el cron de las 8:00):

  CAPA MACRO — régimen-switch v2 (BTC): decide si el mercado está en régimen ALCISTA (LONG,
    permiso para invertir) o DEFENSIVO (CASH, USDT/yield). Parámetros fijados:
      vital_dd=0.30 · exit_dd=0.30 (ATH global) · ma_win=75 · under_ma_days=10.

  CAPA SELECCIÓN — señal v8 (modelo SFM del día): decide si HAY cripto con edge de compra
    (score > +0.025 → COMPRA confianza ALTA). La v8 es el "termómetro short" y es CONSERVADORA.

  DECISIÓN = AND: ENTRAR solo si el régimen es LONG Y la v8 confirma ≥1 compra. Si el régimen
  dice LONG pero la v8 no valida ninguna (todas VENTA/ESPERAR), entonces NO compras (saltar).

Uso (desde /opt/data/qlib):
  /opt/data/qlib-venv/bin/python work/crypto/monitor_combinado.py [--vital-dd 0.30 ...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np  # noqa
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from regime_switch_v2 import load_proxy, regime_signal_v2  # noqa: E402

START_HIST = "2020-11-01"
# umbral de compra de la v8 (confianza ALTA del paper)
BUY_THRESHOLD = 0.025


def leer_senal_v8():
    """Lee la señal v8 MÁS RECIENTE de output/sfm_v8/signal_<fecha>.json."""
    out_dir = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8"
    signals = sorted(out_dir.glob("signal_*.json"))
    if not signals:
        return None, "sin señal v8 generada"
    latest = signals[-1]
    try:
        data = json.loads(latest.read_text())
        return data, latest.name
    except Exception as e:
        return None, f"error leyendo {latest.name}: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default="btc")
    ap.add_argument("--vital-dd", type=float, default=0.30)
    ap.add_argument("--pico-win", type=int, default=90)
    ap.add_argument("--exit-dd", type=float, default=0.30)
    ap.add_argument("--ma-win", type=int, default=75)
    ap.add_argument("--under-ma-days", type=int, default=10)
    args = ap.parse_args()

    # ---- CAPA MACRO: régimen-switch sobre BTC ----
    price = load_proxy(args.proxy)
    price = price[price.index >= pd.Timestamp(START_HIST, tz="UTC")]
    today = price.index[-1].date()
    sig = regime_signal_v2(price, args.vital_dd, args.pico_win, exit_dd=args.exit_dd,
                           ma_win=args.ma_win, under_ma_days=args.under_ma_days)
    regimen_long = bool(sig.iloc[-1])
    px_hoy = float(price.iloc[-1])

    # ---- CAPA SELECCIÓN: señal v8 ----
    v8, v8_file = leer_senal_v8()
    if v8 is None:
        print(f"⚠️ Régimen: {'LONG 🟢' if regimen_long else 'CASH 💵'} · v8: {v8_file}")
        print("💡 DECISIÓN: no operar — señal v8 no disponible")
        sys.exit(0)
    compras = [s for s in v8["signals"] if s["score"] > BUY_THRESHOLD]
    mejores = sorted(v8["signals"], key=lambda s: -s["score"])[:3] if v8["signals"] else []
    v8_signa_fecha = v8.get("date", "?")

    # ---- DECISIÓN COMBINADA (AND) ----
    if regimen_long and compras:
        decision = "COMPRAR 🟢"
        mejor = compras[0]
        razon = (f"régimen LONG (mercado alcista) + v8 confirma compra "
                 f"({mejor['crypto']} score {mejor['score']:+.3f}, ret esperado {mejor['expected_return_pct']:+.1f}%)")
    elif regimen_long and not compras:
        decision = "SALTAR ⚪ (no comprar)"
        razon = "régimen LONG pero la v8 NO confirma ninguna compra (todas VENTA/ESPERAR) → sin edge short"
    else:
        decision = "NO COMPRAR 🔻 (defensivo)"
        razon = "régimen CASH (mercado defensivo) → mantener cash/USDT"

    # ---- montar mensaje ----
    lines = [
        "🔮 DECISIÓN DIARIA — Régimen-switch (gate) + v8 (confirmación)",
        f"   📅 {today}  ·  BTC ${px_hoy:,.0f}",
        f"   🎯 Decisión: {decision}",
        f"   · {razon}",
        "",
        f"   Capa MACRO (régimen): {'LONG 🟢 inversión permitida' if regimen_long else 'CASH 💵 defensivo'}",
        f"   Capa v8 (selección, señal {v8_signa_fecha}): {len(compras)} compra(s) confirmada(s)",
    ]
    # top-3 scores
    if mejores:
        top = ", ".join(f"{s['crypto']}:{s['score']:+.2f}" for s in mejores)
        lines.append(f"   Top scores v8 -> {top}")
    if v8_signa_fecha and v8_signa_fecha != str(today):
        lines.append(f"   ⚠️ señal v8 de {v8_signa_fecha} (no exactamente hoy)")
    lines.append("")
    lines.append("(Lógica causal: régimen MA50/drawdown + conf. v8 >= 0.025. Sin consejo de trading.)")
    print("\n".join(lines))


if __name__ == "__main__":
    main()