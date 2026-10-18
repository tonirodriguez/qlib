"""momentum_kernel_bandwidth.py — ¿Aporta la ponderación por RECENCIA sobre la media simple?

Motivado por el artículo de Navnoor Bawa (2026): el modelo de AQR de 2024 (Kelly-Malamud-Zhou)
es en la práctica una regresión de kernel (Nadaraya-Watson) y, con su ventana de 12 meses, pone
~65 % del peso en los 3 últimos meses; el ÚNICO dial es el ANCHO DE BANDA, y ensancharlo lo
convierte en una media móvil simple ("¿cuántos meses estás promediando de verdad?").

Aquí se traslada el experimento al momentum del proyecto:
  señal = momentum ponderado por kernel gaussiano sobre el LAG (días), con el MISMO lookback
  máximo (120d) en todas las variantes, cambiando SOLO el ancho de banda h:
      w_i = exp(-(i-1)^2 / (2 h^2)),   i = 1..W
  h -> inf  =>  media simple (momentum 120d clásico, el ya validado)
  h pequeño =>  recencia extrema

Se mide, además, la "memoria efectiva": fracción del peso total que cae en los últimos 63 días
(~3 meses, la métrica del artículo).

Motor: el backtest de Qlib (TopkDropout, semanal, costes IB), MISMO setup que vol_gate_test.py
para que los números sean comparables con el momentum 120d ya documentado
(Sharpe 0.960, MaxDD −19.3 %, +18.5 % anual).

Uso: python work/estrategias/momentum_kernel_bandwidth.py
"""
from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd

import qlib
from qlib.data import D

qlib.init(provider_uri="~/.qlib/qlib_data/us_data", region="us")

UNIVERSE = "sp500_liquid"
MOM_W = 120          # lookback máximo (idéntico en todas las variantes)
TOPK = 30
START = "2018-01-01"
END = "2026-08-01"
BT_START = "2022-01-01"
BT_END = "2026-08-07"
BENCH = "^NDX"
RECENT_DAYS = 63     # "últimos 3 meses" para la memoria efectiva

IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")


def kernel_weights(h: float, w: int = MOM_W) -> np.ndarray:
    """Pesos gaussianos sobre el lag (i = 0..w-1, i=0 es el día más reciente)."""
    i = np.arange(w)
    if not np.isfinite(h):
        return np.ones(w)                      # h -> inf  == media simple
    wt = np.exp(-(i ** 2) / (2.0 * h * h))
    return wt


def weight_profile(h: float):
    w = kernel_weights(h)
    w = w / w.sum()
    return {
        "h": ("inf (media simple)" if not np.isfinite(h) else h),
        "peso_ultimos_63d": round(float(w[:RECENT_DAYS].sum()), 3),
        "peso_ultimos_21d": round(float(w[:21].sum()), 3),
        "peso_ultimos_5d": round(float(w[:5].sum()), 3),
        "n_dias_con_99%_del_peso": int(np.searchsorted(np.cumsum(w), 0.99) + 1),
    }


def kernel_momentum(close: pd.DataFrame, h: float) -> pd.DataFrame:
    """Momentum ponderado por kernel: suma ponderada de retornos diarios por lag.

    Implementación con UN solo acumulador (in-place) en vez de 120 DataFrames
    intermedios: mismo resultado con una fracción de la memoria (el proceso moría
    por OOM al acumular copias).
    """
    vals = close.pct_change().to_numpy(dtype=np.float64, copy=False)
    w = kernel_weights(h)
    w = w / w.sum()
    acc = np.zeros_like(vals)
    n = vals.shape[0]
    for i in range(MOM_W):
        wi = w[i]
        if wi == 0.0:
            continue
        if i == 0:
            acc += wi * vals
        else:
            acc[i:] += wi * vals[:n - i]
    return pd.DataFrame(acc, index=close.index, columns=close.columns)


def to_qlib_signal(sig_df: pd.DataFrame):
    s = sig_df.stack().dropna()
    s = s.reset_index()
    s.columns = ["datetime", "instrument", "signal"] if s.shape[1] == 3 else s.columns
    s["datetime"] = pd.to_datetime(s["datetime"])
    return s.set_index(["datetime", "instrument"])["signal"].sort_index()


def run_backtest(sig_series, name):
    from qlib.backtest import backtest
    strategy = {
        "class": "TopkDropoutStrategy",
        "module_path": "qlib.contrib.strategy",
        "kwargs": {"signal": sig_series, "topk": TOPK, "n_drop": 5,
                   "only_tradable": True, "hold_thresh": 20},
    }
    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
    }
    report, _ = backtest(start_time=BT_START, end_time=BT_END, strategy=strategy,
                         executor=executor, benchmark=BENCH, account=100000,
                         exchange_kwargs=IB)
    freq_key = list(report.keys())[0]
    df = report[freq_key][0]
    pv = df["account"].values
    port_ret = pd.Series(pv).pct_change().dropna().values
    mean_ann = float(np.mean(port_ret)) * 52
    vol = float(np.std(port_ret)) * np.sqrt(52)
    sharpe = mean_ann / vol if vol else np.nan
    cum = np.cumprod(1 + port_ret)
    dd = cum / np.maximum.accumulate(cum) - 1
    return {"name": name, "sharpe": sharpe, "maxdd": float(dd.min()), "anual": mean_ann}


def main():
    import argparse
    import gc

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="",
                    help="lista de anchos de banda a ejecutar, separada por comas "
                         "(ej. 'inf,60'); vacío = todas")
    args = ap.parse_args()

    tickers = D.list_instruments(D.instruments(UNIVERSE), as_list=True)
    close = D.features(tickers, ["$close"], start_time=START, end_time=END, freq="day")
    close = close["$close"].unstack(level=0).sort_index()
    print(f"Universo: {len(tickers)} tickers | precios: {close.shape}", flush=True)

    h_list = [np.inf, 60.0, 50.0, 40.0, 35.0, 25.0, 15.0]
    if args.only:
        wanted = {s.strip().lower() for s in args.only.split(",")}
        h_list = [h for h in h_list
                  if (("inf" in wanted) if not np.isfinite(h) else (f"{h:.0f}" in wanted))]

    # --- Memoria efectiva por ancho de banda ---
    # SIEMPRE los 5 perfiles completos (aunque se ejecute con --only), porque este
    # bloque es barato (aritmética de pesos) y el guardado incremental sobreescribe
    # el JSON: si sólo guardáramos el subconjunto, borraríamos los demás perfiles.
    all_h = [np.inf, 60.0, 50.0, 40.0, 35.0, 25.0, 15.0]
    print("\n" + "=" * 78, flush=True)
    print("MEMORIA EFECTIVA de cada ancho de banda (pesos renormalizados, lag 0 = hoy)", flush=True)
    print("=" * 78, flush=True)
    print(f"{'h (días)':<20}{'peso últ. 63d':>15}{'peso últ. 21d':>15}{'peso últ. 5d':>13}{'días p/ 99% peso':>18}", flush=True)
    print("-" * 78, flush=True)
    profiles = []
    for h in all_h:
        p = weight_profile(h)
        profiles.append(p)
        hs = p["h"] if isinstance(p["h"], str) else f"{p['h']:.0f}"
        print(f"{hs:<20}{p['peso_ultimos_63d']:>15.3f}{p['peso_ultimos_21d']:>15.3f}"
              f"{p['peso_ultimos_5d']:>13.3f}{p['n_dias_con_99%_del_peso']:>18d}", flush=True)

    # --- Backtests ---
    print("\n" + "=" * 78, flush=True)
    print("BACKTEST (motor Qlib, topk 30, semanal, costes IB) — mismo lookback 120d", flush=True)
    print("=" * 78, flush=True)

    import json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "momentum_kernel_bandwidth_results.json")
    # resultados previos (si se ejecuta por variantes en procesos separados)
    out = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                out = json.load(f)
        except Exception:
            out = {}
    results = out.get("resultados", [])
    done = {r["name"] for r in results}

    for h in h_list:
        label = "momentum 120d (media simple)" if not np.isfinite(h) else f"kernel h={h:.0f}d"
        if label in done:
            print(f"  {label:<32} (ya calculado, se omite)", flush=True)
            continue
        sig = kernel_momentum(close, h)
        r = run_backtest(to_qlib_signal(sig), label)
        del sig
        gc.collect()
        results.append(r)
        print(f"  {label:<32} Sharpe {r['sharpe']:>6.3f} | MaxDD {r['maxdd']:>7.1%} | Anual {r['anual']:>7.1%}", flush=True)
        # guardado incremental: si el proceso muere, no se pierde lo ya calculado
        out = {"universo": UNIVERSE, "lookback": MOM_W, "topk": TOPK,
               "bt_start": BT_START, "bt_end": BT_END,
               "memoria_efectiva": profiles, "resultados": results}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)

    if len(results) >= 2:
        base = results[0]
        print("\n" + "-" * 78, flush=True)
        print(f"Referencia (media simple): Sharpe {base['sharpe']:.3f}, DD {base['maxdd']:.1%}, anual {base['anual']:.1%}", flush=True)
        win = [r for r in results[1:] if r["sharpe"] > base["sharpe"]]
        print(f"Variantes con kernel que MEJORAN el Sharpe: {len(win)}/{len(results)-1}", flush=True)
        for r in results[1:]:
            print(f"  {r['name']:<32} ΔSharpe {r['sharpe']-base['sharpe']:+.3f} | "
                  f"ΔDD {r['maxdd']-base['maxdd']:+.1%} | Δanual {r['anual']-base['anual']:+.1%}", flush=True)

    print(f"\n✅ {path} ({len(results)} variantes)", flush=True)


if __name__ == "__main__":
    main()