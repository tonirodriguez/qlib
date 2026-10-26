"""vol_gate_e3_validacion.py — Valida el vol-gate EN LA ARQUITECTURA REAL (E3).

POR QUE ESTE SCRIPT Y NO LOS ANTERIORES
    Los intentos previos median mecanismos que NO son los que usa el proyecto:

      vol_gate_validacion_v3.py  -> gate sobre NUMERO DE POSICIONES, toda la
                                    cartera. Dio Sharpe -0.180 (empeora).
      jev_backtest_ab.py         -> gate sobre CAPITAL, toda la cartera.
                                    Dio Sharpe +0.13 (mejora).

    Ninguno de los dos es la arquitectura real. `simulate_pead_core.py` (E3)
    aplica el gate asi (lineas 204-205):

        core_cash = portfolio_value * NUCLEO_W          # 65%, NO lo toca el gate
        tact_cash = portfolio_value * TACTICO_W * gate  # 35% x gate

    Es decir: **reduce el capital desplegado, y SOLO del libro tactico (35%)**.
    El techo de impacto es por tanto mucho menor que en los dos tests previos.

QUE MIDE
    A) SIN gate : tact_cash = 35% siempre
    B) CON gate : tact_cash = 35% x gate, con el gate real (P75/P90 + histeresis)

    Misma arquitectura, mismos pesos, mismos costes. Solo cambia el gate.

LIMITACION IMPORTANTE
    El libro PEAD se aproxima con momentum ordenado (no con SUE real), porque
    los datos de earnings (`pead_earnings_appended.csv`) pueden no estar en esta
    maquina. Lo que se mide es el EFECTO DEL GATE sobre el libro tactico, que es
    lo que se quiere saber. El PEAD actua como un "fondo" estable en ambos casos.

Uso (en WSL):
    conda run -n qlib python work/estrategias/vol_gate_e3_validacion.py
    conda run -n qlib python work/estrategias/vol_gate_e3_validacion.py --quick
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vol_gate as vg  # noqa: E402

# --- Parametros COPIADOS de simulate_pead_core.py (no inventados) ---
NUCLEO_W = 0.65
TACTICO_W = 0.35
PEAD_TOPK = 22
MOM_TOPK = 12
MOM_W = 120
VOL_WIN = 20
VOL_P75 = 0.75
VOL_P90 = 0.90

# Costes estilo IB (los mismos de sim_utils.py)
IB_RATE_PER_SHARE = 0.0035
IB_MIN_PER_ORDER = 0.35
IB_SEC_RATE = 33.10 / 1_000_000.0
IB_TAF_PER_SHARE = 0.00016


def ib_cost(shares, price, is_sell=False):
    c = max(IB_MIN_PER_ORDER, shares * IB_RATE_PER_SHARE)
    if is_sell:
        c += shares * price * IB_SEC_RATE + shares * IB_TAF_PER_SHARE
    return c


def simular(prices: pd.DataFrame, bench: pd.Series, rebal_freq: int,
            gate_series: pd.Series | None, capital: float = 100000.0) -> pd.Series:
    """Simula la arquitectura E3 semana a semana. Devuelve la serie de valor.

    Estructura identica a simulate_pead_core.py:
      - libro nucleo  : PEAD_TOPK nombres, NUCLEO_W del capital
      - libro tactico : MOM_TOPK nombres, TACTICO_W * gate del capital
    """
    rets = prices.pct_change()
    dates = prices.index

    # rankings rodantes (momentum). El nucleo usa otro orden pero misma
    # mecanica de cartera; lo que importa es el efecto del gate.
    mom = prices / prices.shift(MOM_W) - 1

    value = capital
    equity = pd.Series(index=dates, dtype=float)
    pos = {}          # ticker -> accioness
    cash = capital

    g = None
    if gate_series is not None:
        g = gate_series.reindex(dates).ffill().fillna(1.0)

    for i in range(MOM_W + 1, len(dates)):
        d = dates[i]

        # marcar a mercado cada dia
        pv = cash
        for t, sh in pos.items():
            px = prices[t].iloc[i]
            if px == px:
                pv += sh * px
            else:
                pv += sh * prices[t].iloc[i - 1] if prices[t].iloc[i - 1] == prices[t].iloc[i - 1] else 0
        equity.iloc[i] = pv

        if (i - MOM_W - 1) % rebal_freq != 0:
            continue
        if pv <= 0:
            continue

        row = mom.iloc[i].dropna()
        if len(row) < PEAD_TOPK + MOM_TOPK:
            continue
        ranked = row.sort_values(ascending=False)
        nucleo = list(ranked.index[:PEAD_TOPK])
        tactico = list(ranked.index[PEAD_TOPK:PEAD_TOPK + MOM_TOPK])

        level = 1.0 if g is None else float(g.iloc[i])
        if level != level:
            level = 1.0

        core_cash = pv * NUCLEO_W
        tact_cash = pv * TACTICO_W * level

        # vender todo lo que sale
        target = set(nucleo) | set(tactico)
        sells = []
        for t in list(pos.keys()):
            if t not in target:
                px = prices[t].iloc[i]
                if px == px and px > 0:
                    sells.append((t, pos[t], px))
                del pos[t]
        cost = sum(ib_cost(sh, px, True) for _, sh, px in sells)
        cash -= cost

        # reconstruir
        per_core = core_cash / len(nucleo) if nucleo else 0
        per_tact = tact_cash / len(tactico) if tactico else 0

        held_value = 0.0
        buys_cost = 0.0
        new_pos = {}
        for lst, per in ((nucleo, per_core), (tactico, per_tact)):
            for t in lst:
                px = prices[t].iloc[i]
                if px != px or px <= 0:
                    continue
                sh = per / px
                new_pos[t] = new_pos.get(t, 0.0) + sh
                held_value += sh * px
        # coste de compra de las nuevas (aproximado: solo las que no teniamos)
        for t, sh in new_pos.items():
            old = pos.get(t, 0.0)
            if sh > old:
                px = prices[t].iloc[i]
                buys_cost += ib_cost(sh - old, px, False)

        cash = pv - held_value - buys_cost
        pos = new_pos

    equity = equity.ffill().fillna(capital)
    return equity


def metricas(eq: pd.Series, freq_por_ano: float) -> dict:
    r = eq.pct_change().dropna()
    if len(r) < 10 or r.std() == 0:
        return {"sharpe": float("nan"), "maxdd": float("nan"), "total": float("nan")}
    ann = float(r.mean()) * freq_por_ano
    vol = float(r.std()) * np.sqrt(freq_por_ano)
    dd = (eq / eq.cummax() - 1).min()
    return {
        "sharpe": float(ann / vol) if vol else float("nan"),
        "maxdd": float(dd),
        "total": float(eq.iloc[-1] / eq.iloc[0] - 1),
        "final": float(eq.iloc[-1]),
        "ann": ann,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-08-01")
    ap.add_argument("--freq", type=int, default=5, help="dias entre rebalanceos")
    ap.add_argument("--max-tickers", type=int, default=200)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(HERE / "vol_gate_e3_validacion.json"))
    args = ap.parse_args()

    import qlib
    from qlib.data import D

    print("=" * 78)
    print(" VALIDACION DEL VOL-GATE EN LA ARQUITECTURA REAL (E3)")
    print("=" * 78)
    print(f"  nucleo PEAD   : {PEAD_TOPK} nombres, {NUCLEO_W:.0%} del capital (gate NO aplica)")
    print(f"  tactico momen.: {MOM_TOPK} nombres, {TACTICO_W:.0%} x gate")
    print(f"  rebalanceo    : cada {args.freq} sesiones")

    uri = os.environ.get("QLIB_US_DATA") or os.path.expanduser("~/.qlib/qlib_data/us_data")
    qlib.init(provider_uri=uri, region="us")

    inst_dir = os.path.join(uri, "instruments")
    universe = next((nm for nm in ("sp500_liquid", "sp500")
                     if os.path.exists(os.path.join(inst_dir, nm + ".txt"))), None)
    tickers = D.list_instruments(D.instruments(universe), as_list=True)
    if len(tickers) > args.max_tickers:
        idx = np.linspace(0, len(tickers) - 1, args.max_tickers).astype(int)
        tickers = [tickers[i] for i in idx]
    print(f"  universo      : {universe} ({len(tickers)} tickers)")

    close = D.features(tickers, ["$close", "$factor"], start_time=args.start,
                       end_time=args.end, freq="day")
    c = close["$close"].unstack(level=0).sort_index()
    f = close["$factor"].unstack(level=0).sort_index()
    prices = (c / f).dropna(axis=0, thresh=int(0.6 * c.shape[1]))
    print(f"  precios       : {prices.shape[0]} x {prices.shape[1]}")

    # benchmark para el gate
    try:
        b = D.features(["^GSPC"], ["$close", "$factor"], start_time=args.start,
                       end_time=args.end, freq="day")
        bc = b["$close"].unstack(level=0)["^GSPC"]
        bf = b["$factor"].unstack(level=0)["^GSPC"]
        bench = (bc / bf).dropna().sort_index()
        print(f"  benchmark     : ^GSPC real")
    except Exception:
        bench = prices.mean(axis=1)
        print(f"  benchmark     : media del universo (sin ^GSPC)")

    # gate
    vol, pct = vg.vol_percentile(bench, vol_win=VOL_WIN, hist_win=252)
    raw = pct.apply(lambda x: vg.gate_level_from_pct(x, VOL_P75, VOL_P90)
                    if pd.notna(x) else 1.0)
    gate = vg._apply_hysteresis(raw.fillna(1.0), 5)
    print(f"\n  gate: {dict(gate.value_counts().sort_index())}")

    freq_ano = 252.0 / args.freq
    print(f"\n  [A] sin gate (tactico siempre al {TACTICO_W:.0%})...")
    eq_a = simular(prices, bench, args.freq, None)
    mA = metricas(eq_a, freq_ano)

    print(f"  [B] con gate (tactico al {TACTICO_W:.0%} x gate)...")
    eq_b = simular(prices, bench, args.freq, gate)
    mB = metricas(eq_b, freq_ano)

    print("\n" + "=" * 78)
    print(" RESULTADOS")
    print("=" * 78)
    print(f"  {'Estrategia':<26}{'Sharpe':>9}{'MaxDD':>10}{'Total':>11}{'Final':>13}")
    print("  " + "-" * 66)
    for nm, m in (("A) sin gate", mA), ("B) con gate (35% x gate)", mB)):
        print(f"  {nm:<26}{m['sharpe']:>9.3f}{m['maxdd']*100:>9.1f}%"
              f"{m['total']*100:>10.1f}%{m['final']:>13,.0f}")

    print("\n" + "=" * 78)
    print(" VEREDICTO")
    print("=" * 78)
    ds = mB["sharpe"] - mA["sharpe"]
    dd = (mB["maxdd"] - mA["maxdd"]) * 100
    print(f"  delta Sharpe : {ds:+.3f}")
    print(f"  delta MaxDD  : {dd:+.1f} pp  (positivo = menos drawdown)")
    print(f"  delta Final  : {mB['final'] - mA['final']:+,.0f}")

    if abs(mB["final"] - mA["final"]) < 1.0 and abs(ds) < 1e-6:
        print("\n  >> IDENTICOS: el gate no esta afectando. Revisar.")
    elif ds > 0 and dd > 0:
        print("\n  >> El gate MEJORA Sharpe y reduce drawdown en la arquitectura real.")
    elif dd > 0:
        print("\n  >> El gate reduce drawdown pero no mejora Sharpe.")
        print("     Puede valer como control de riesgo, no como mejora de retorno.")
    else:
        print("\n  >> El gate no aporta en la arquitectura real.")

    print("\n  NOTA: el libro PEAD se aproxima con momentum (no SUE real).")
    print("  Se mide el EFECTO DEL GATE sobre el tactico, que es el objetivo.")

    Path(args.out).write_text(json.dumps({
        "fecha": pd.Timestamp.now().isoformat(),
        "arquitectura": "E3 real: nucleo 65% fijo + tactico 35% x gate",
        "periodo": [args.start, args.end],
        "universe": universe, "n_tickers": len(tickers),
        "gate_dist": {str(k): int(v) for k, v in gate.value_counts().items()},
        "sin_gate": mA, "con_gate": mB,
    }, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
