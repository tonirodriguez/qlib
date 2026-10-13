"""ms_regime_freq.py — Markov-switching de régimen a frecuencia SEMANAL y MENSUAL.

Motivación: en `ms_regime.py` (frecuencia diaria) el MS de varianza NO batió a `regime_switch_v2`
(whipsaw + la volatilidad realizada va por detrás del precio). Pero el paper (Vansteenberghe 2026,
§53.3, Kim et al. 1998) estima ese modelo sobre **retornos MENSUALES** de mercado de acciones, no
diarios: a frecuencia baja el ruido cae y la estructura de régimen es mucho más limpia.

Este script replica §53.3 a frecuencia semanal y mensual y compara contra:
  - MS-gate (probabilidad filtrada causal del estado de alta vol)
  - regime_switch_v2 ESCALADO a la misma frecuencia (ventanas en días ÷ días-por-periodo) — es el
    análogo honesto al cambio de frecuencia; el v2 diario NO se toca.
  - buy&hold BTC y USDT puro.

Causalidad: la decisión de exposición del periodo t+1 se toma con información hasta el cierre del
periodo t (señal desplazada 1 periodo). El MS se reajusta en ventana expansiva con parámetros
estimados SÓLO con el pasado y filtrado de Hamilton one-sided.

Uso:
    python work/crypto/ms_regime_freq.py                # semanal + mensual
    python work/crypto/ms_regime_freq.py --freq monthly
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from ms_regime import (  # noqa: E402
    INITIAL_USD, OUT_DIR, buyhold_curve, load_proxy, bds_permutation_pvalue,
)

CASH_APY = 0.045
COST = 0.0010

WINDOWS = {
    "sel_bull2021": ("2020-11-01", "2021-11-30"),
    "sel_giro2022": ("2021-06-01", "2022-12-31"),
    "oos_rally2024": ("2024-01-01", "2024-12-31"),
    "oos_base2025": ("2025-01-01", "2026-08-30"),
    "full_2020_2026": ("2020-11-01", "2026-08-30"),
}

FREQS = {                      # freq pandas, días por periodo, refit (periodos), min obs
    "weekly":  {"rule": "W-SUN", "days": 7, "refit": 13, "min_obs": 120},
    "monthly": {"rule": "ME",    "days": 30, "refit": 6,  "min_obs": 60},
}


@contextlib.contextmanager
def quiet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


# --------------------------------------------------------------------- frecuencia
def resample_periods(price: pd.Series, rule: str) -> pd.Series:
    try:
        return price.resample(rule).last().dropna()
    except ValueError:                     # pandas antiguo: 'ME' no existe
        return price.resample("M" if rule == "ME" else rule).last().dropna()


# ---------------------------------------------------- MS causal sobre retornos de periodo
def ms_filtered_highvol(returns: pd.Series, refit: int, min_obs: int):
    """Probabilidad FILTRADA causal del estado de alta varianza (parámetros sólo del pasado)."""
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    r = returns.dropna()
    idx = r.index
    n = len(r)
    p_high = pd.Series(np.nan, index=idx)
    sig_t = pd.Series(np.nan, index=idx)
    n_refits = 0
    last_params = None

    positions = list(range(min_obs, n, refit))
    if not positions or positions[-1] != n - 1:
        positions.append(n - 1)

    prev = min_obs
    for pos in positions:
        try:
            with quiet():
                mod = MarkovRegression(r.iloc[:pos], k_regimes=2, trend="c", switching_variance=True)
                res = mod.fit(disp=False, maxiter=300)
                params = res.params
                s2 = [params.get("sigma2[0]"), params.get("sigma2[1]")]
                hi = int(np.argmax(s2))
                end = min(pos + refit, n)
                mod_seg = MarkovRegression(r.iloc[:end], k_regimes=2, trend="c",
                                           switching_variance=True)
                fp = mod_seg.filter(params).filtered_marginal_probabilities[hi]
            p_high.iloc[prev:end] = fp.iloc[prev:end].values
            sig_t.iloc[prev:end] = float(np.sqrt(params.get(f"sigma2[{hi}]")))
            n_refits += 1
            last_params = {k: float(v) for k, v in params.items()}
            prev = end
        except Exception as e:  # pragma: no cover
            print(f"  [warn] refit {idx[pos].date()} falló: {e}", file=sys.stderr)
    return p_high, sig_t, n_refits, last_params


def gate_from_phigh(p_high: pd.Series, th_enter=0.5, th_exit=0.3, min_state=2):
    state = np.ones(len(p_high), dtype=int)
    cur = 1
    for i, p in enumerate(p_high.values):
        if p == p:
            if cur == 1 and p > th_enter:
                cur = 0
            elif cur == 0 and p < th_exit:
                cur = 1
        state[i] = cur
    out = np.ones(len(state), dtype=int)
    i, n = 0, len(state)
    while i < n:
        if state[i] == 0:
            end = min(i + min_state, n)
            out[i:end] = 0
            i = end
        else:
            out[i] = 1
            i += 1
    return pd.Series(out.astype(bool), index=p_high.index)


# ------------------------------------------- regime_switch_v2 escalado a la frecuencia
def v2_scaled_signal(price: pd.Series, days_per_period: int) -> pd.Series:
    """v2 con las ventanas en DÍAS convertidas a periodos (÷ días por periodo).

    base: MA(50d) + drawdown ATH ≥ −15 %; vitalidad: rebote del pico reciente (90d) dentro del 30 %;
    salida: cierre por debajo de MA(75d) N=10d consecutivos; histéresis 5d.
    """
    d = max(days_per_period, 1)
    ma_base = max(2, round(50 / d))
    pico_win = max(2, round(90 / d))
    ma_exit = max(2, round(75 / d))
    under_n = max(1, round(10 / d))
    minsd = max(1, round(5 / d))

    ma = price.rolling(ma_base, min_periods=max(2, ma_base // 2)).mean()
    dd = price / price.cummax() - 1.0
    base = ((price > ma) & (dd > -0.15)).fillna(True)

    pico = price.rolling(pico_win, min_periods=2).max().fillna(price.cummax())
    rebote = (price / pico - 1.0) > -0.30
    final = (base | rebote).astype(bool)

    ma_x = price.rolling(ma_exit, min_periods=ma_exit).mean()
    below = (price < ma_x).astype(int)
    streak = np.zeros(len(price), dtype=int)
    acc = 0
    for i in range(len(price)):
        acc = acc + 1 if below.iloc[i] else 0
        streak[i] = acc
    final = final & (streak < under_n)
    final = final & ~(price / price.cummax() - 1.0 < -0.30)   # salida por ATH (exit_dd=0.30)

    s = final.astype(int).values
    out = np.ones(len(s), dtype=int)
    i, n = 0, len(s)
    while i < n:
        if s[i] == 0:
            end = min(i + minsd, n)
            out[i:end] = 0
            i = end
        else:
            out[i] = 1
            i += 1
    return pd.Series(out.astype(bool), index=price.index)


# ------------------------------------------------------------------- simulador por periodo
def simulate_periods(price, signal, days_per_period, initial_usd=INITIAL_USD):
    yield_p = (1.0 + CASH_APY) ** (days_per_period / 365.0) - 1.0
    cash, sh, trades, curve = initial_usd, 0.0, 0, []
    for day in price.index:
        px = float(price.loc[day])
        cash += cash * yield_p
        long_now = bool(signal.get(day, True))
        if long_now and sh == 0 and px > 0:
            trades += 1
            fee = cash * COST
            sh = (cash - fee) / px
            cash = 0.0
        elif (not long_now) and sh > 0:
            trades += 1
            cash += sh * px - sh * px * COST
            sh = 0.0
        curve.append(cash + (sh * px if sh > 0 else 0.0))
    return np.array(curve), trades


def metrics(vals, periods_per_year):
    vals = np.asarray(vals, dtype=float)
    dd = vals / np.maximum.accumulate(vals) - 1.0
    rets = np.diff(vals) / vals[:-1]
    vol = float(np.std(rets) * np.sqrt(periods_per_year))
    return {
        "ret_pct": round((vals[-1] / vals[0] - 1) * 100, 1),
        "maxdd_pct": round(float(dd.min()) * 100, 1),
        "vol_anual_pct": round(vol * 100, 1),
        "sharpe": round(float(np.mean(rets) / np.std(rets) * np.sqrt(periods_per_year)), 2)
        if len(rets) and np.std(rets) else np.nan,
    }


def usdt_curve_periods(price, days_per_period, initial_usd=INITIAL_USD):
    y = (1.0 + CASH_APY) ** (days_per_period / 365.0) - 1.0
    return initial_usd * (1.0 + y) ** np.arange(len(price))


# ------------------------------------------------------------------------------- main
def run_freq(freq_name: str, price_all: pd.Series, args) -> dict:
    cfg = FREQS[freq_name]
    days = cfg["days"]
    periods_per_year = 365.0 / days
    px_all = resample_periods(price_all, cfg["rule"])
    ret_all = np.log(px_all).diff().dropna()

    print("\n" + "=" * 84)
    print(f"### FRECUENCIA {freq_name.upper()}  (regla {cfg['rule']}, ~{days}d/periodo, "
          f"{len(px_all)} periodos desde {px_all.index[0].date()})")
    print("=" * 84)

    p_high, sig_t, n_refits, params = ms_filtered_highvol(ret_all, cfg["refit"], cfg["min_obs"])
    if n_refits == 0:
        print("  (sin periodos suficientes para ajustar)")
        return {"error": "insufficient_data", "n_periods": int(len(px_all))}
    print(f"  refits: {n_refits} | periodos con p_high: {int(p_high.notna().sum())} | "
          f"media p_high={p_high.mean():.3f} | frac>0.5={float((p_high > 0.5).mean()):.1%}")
    print(f"  params último refit: {params}")

    gate = gate_from_phigh(p_high, args.th_enter, args.th_exit, max(1, round(5 / days)))
    gate_shift = gate.shift(1).fillna(True)          # causal: decisión para t+1

    # BDS a esta frecuencia (sólo si hay muestra suficiente)
    bds = {}
    if len(ret_all) >= 150:
        for m in (2, 3):
            st, pv = bds_permutation_pvalue(ret_all.values, m=m, n_perm=120)
            bds[f"raw_m{m}"] = {"stat": st, "p": pv}
        z = (ret_all / sig_t.reindex(ret_all.index)).dropna()
        if len(z) >= 150:
            for m in (2, 3):
                st, pv = bds_permutation_pvalue(z.values, m=m, n_perm=120)
                bds[f"std_m{m}"] = {"stat": st, "p": pv}
    print("  BDS: " + (", ".join(
        f"{k}: D={v['stat']:+.5f} p={v['p']:.3f} ({'RECHAZA' if v['p'] < 0.05 else 'no rechaza'})"
        for k, v in bds.items()) or "(muestra insuficiente)"))

    results = {}
    hdr = f"{'ventana':<16}{'estrategia':<30}{'ret%':>9}{'maxDD%':>9}{'Sharpe':>8}{'vol%':>8}{'trades':>8}{'periodos':>10}"
    print("\n" + hdr)
    print("-" * len(hdr))
    for wname, (s, e) in WINDOWS.items():
        s_ts, e_ts = pd.Timestamp(s, tz="UTC"), pd.Timestamp(e, tz="UTC")
        px = px_all[(px_all.index >= s_ts) & (px_all.index <= e_ts)]
        if len(px) < 8:
            continue
        g = gate_shift.reindex(px.index).fillna(True)
        v2 = v2_scaled_signal(px, days)
        rows = {}
        for name, sig in [(f"MS-gate §53.3 ({freq_name})", g), ("regime_switch_v2 escalado", v2)]:
            vals, tr = simulate_periods(px, sig, days)
            met = metrics(vals, periods_per_year)
            rows[name] = {**met, "trades": tr}
            print(f"{wname:<16}{name:<30}{met['ret_pct']:>9.1f}{met['maxdd_pct']:>9.1f}"
                  f"{met['sharpe']:>8.2f}{met['vol_anual_pct']:>8.1f}{tr:>8}{len(px):>10}")
        met = metrics(buyhold_curve(px), periods_per_year)
        rows["buy&hold BTC"] = {**met, "trades": 0}
        print(f"{wname:<16}{'buy&hold BTC':<30}{met['ret_pct']:>9.1f}{met['maxdd_pct']:>9.1f}"
              f"{met['sharpe']:>8.2f}{met['vol_anual_pct']:>8.1f}{'-':>8}{len(px):>10}")
        met = metrics(usdt_curve_periods(px, days), periods_per_year)
        rows["USDT puro"] = {**met, "trades": 0}
        print(f"{wname:<16}{'USDT puro':<30}{met['ret_pct']:>9.1f}{'-':>9}{'-':>8}{'-':>8}{'-':>8}{len(px):>10}")
        # acuerdo
        both = pd.DataFrame({"ms": g, "v2": v2}).dropna()
        agr = float((both["ms"] == both["v2"]).mean()) if len(both) else np.nan
        print(f"{'':<16}acuerdo MS/v2={agr:.1%} | periodos: CASH MS={int((~both['ms']).sum())} "
              f"v2={int((~both['v2']).sum())} ambos={int(((~both['ms']) & (~both['v2'])).sum())}")
        print("-" * len(hdr))
        results[wname] = {"rows": rows, "acuerdo_ms_v2": round(agr, 4), "n_periodos": int(len(px))}

    return {"freq": freq_name, "rule": cfg["rule"], "days_per_period": days,
            "n_periods_total": int(len(px_all)), "n_refits": n_refits,
            "params_ultimo_refit": params, "bds": bds,
            "th_enter": args.th_enter, "th_exit": args.th_exit, "resultados": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", choices=["weekly", "monthly", "both"], default="both")
    ap.add_argument("--th-enter", type=float, default=0.5)
    ap.add_argument("--th-exit", type=float, default=0.3)
    args = ap.parse_args()

    price_all = load_proxy()
    freqs = ["weekly", "monthly"] if args.freq == "both" else [args.freq]

    out = {}
    for f in freqs:
        out[f] = run_freq(f, price_all, args)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ms_regime_freq_results.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"\n✅ Guardado: {OUT_DIR/'ms_regime_freq_results.json'}")


if __name__ == "__main__":
    main()
