"""ms_regime_freq_sweep.py — ¿El gate MS degenera a buy&hold por el umbral o por el modelo?

En `ms_regime_freq.py` (semanal/mensual) el gate MS resultó casi idéntico a buy&hold. Aquí se
comprueba si es artefacto del umbral 0.5:

  1. Distribución de la probabilidad filtrada causal p_high (cuantiles, fracción > umbral).
  2. Barrido de umbrales (0.2–0.7) en las ventanas clave.
  3. Variante k=3 (probabilidad del estado de MÁXIMA varianza).

Reutiliza el ajuste de `ms_regime_freq.py` (mismos refits/ventanas). No toca scripts oficiales.

Uso: python work/crypto/ms_regime_freq_sweep.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

import contextlib
import warnings

from ms_regime import OUT_DIR, buyhold_curve, load_proxy  # noqa: E402
from ms_regime_freq import (  # noqa: E402
    FREQS, INITIAL_USD, WINDOWS, gate_from_phigh, metrics, resample_periods,
    simulate_periods, usdt_curve_periods, v2_scaled_signal,
)

warnings.filterwarnings("ignore")


@contextlib.contextmanager
def quiet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def ms_filtered_prob_k(returns: pd.Series, refit: int, min_obs: int, k: int):
    """Probabilidad filtrada causal del estado de MÁXIMA varianza, con k estados."""
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    r = returns.dropna()
    idx = r.index
    n = len(r)
    p_high = pd.Series(np.nan, index=idx)
    positions = list(range(min_obs, n, refit))
    if not positions or positions[-1] != n - 1:
        positions.append(n - 1)
    prev = min_obs
    for pos in positions:
        try:
            with quiet():
                mod = MarkovRegression(r.iloc[:pos], k_regimes=k, trend="c", switching_variance=True)
                params = mod.fit(disp=False, maxiter=300).params
                s2 = [params.get(f"sigma2[{i}]") for i in range(k)]
                hi = int(np.argmax([v if v == v else -1 for v in s2]))
                end = min(pos + refit, n)
                mod_seg = MarkovRegression(r.iloc[:end], k_regimes=k, trend="c",
                                           switching_variance=True)
                fp = mod_seg.filter(params).filtered_marginal_probabilities[hi]
            p_high.iloc[prev:end] = fp.iloc[prev:end].values
            prev = end
        except Exception as e:  # pragma: no cover
            print(f"  [warn] {idx[pos].date()} k={k}: {e}", file=sys.stderr)
    return p_high


def eval_window(px_all, p_high, gate_series, days, s, e, v2):
    s_ts, e_ts = pd.Timestamp(s, tz="UTC"), pd.Timestamp(e, tz="UTC")
    px = px_all[(px_all.index >= s_ts) & (px_all.index <= e_ts)]
    if len(px) < 8:
        return None
    g = gate_series.reindex(px.index).fillna(True)
    vals, tr = simulate_periods(px, g, days)
    met = metrics(vals, 365.0 / days)
    return {**met, "trades": tr}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit-start", default=None,
                    help="fecha desde la que se AJUSTA el modelo (None = toda la historia BTC, "
                         "que incluye la era extrema 2010-2017).")
    ap.add_argument("--min-obs-weekly", type=int, default=None)
    ap.add_argument("--min-obs-monthly", type=int, default=None)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()

    price_all = load_proxy()
    out = {}

    for freq_name in ("weekly", "monthly"):
        cfg = dict(FREQS[freq_name])
        days = cfg["days"]
        px_all = resample_periods(price_all, cfg["rule"])
        ret_full = np.log(px_all).diff().dropna()
        if a.fit_start:
            ret_all = ret_full[ret_full.index >= pd.Timestamp(a.fit_start, tz="UTC")]
            # con menos historia hay que bajar el mínimo de observaciones para poder ajustar
            mo = (a.min_obs_weekly if freq_name == "weekly" else a.min_obs_monthly)
            cfg["min_obs"] = mo or (100 if freq_name == "weekly" else 36)
        else:
            ret_all = ret_full
        print(f"\n[fit_start={a.fit_start or 'historia completa'}] {freq_name}: "
              f"{len(ret_all)} periodos de ajuste (desde {ret_all.index[0].date()}), "
              f"refit cada {cfg['refit']}, min_obs={cfg['min_obs']}")

        print("\n" + "#" * 88)
        print(f"# SWEEP {freq_name.upper()} — {len(px_all)} periodos, refit cada {cfg['refit']}")
        print("#" * 88)

        blk = {}
        for k in (2, 3):
            p = ms_filtered_prob_k(ret_all, cfg["refit"], cfg["min_obs"], k)
            p = p.dropna()
            if len(p) == 0:
                continue
            desc = {f"q{int(q*100)}": round(float(p.quantile(q)), 3) for q in (0.5, 0.75, 0.9, 0.95, 1.0)}
            frac = {f"frac>{t}": round(float((p > t).mean()), 3) for t in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)}
            print(f"\n  k={k}  p_high: media={p.mean():.3f} min={p.min():.3f} max={p.max():.3f}")
            print(f"        cuantiles {desc}")
            print(f"        {frac}")
            blk[f"k{k}_desc"] = {"media": round(float(p.mean()), 4), "max": round(float(p.max()), 4),
                                 "cuantiles": desc, "fracciones": frac}
            blk[f"k{k}_p_high"] = {str(i.date()): round(float(v), 4) for i, v in p.items()}

        # Barrido de umbrales (k=2) en las ventanas clave + full
        p2 = ms_filtered_prob_k(ret_all, cfg["refit"], cfg["min_obs"], 2)
        sweep = {}
        print(f"\n  --- barrido de umbrales (k=2), min_state=1 ---")
        hdr = f"    {'umbral':<8}{'ventana':<16}{'MS ret':>9}{'MS DD':>9}{'v2 ret':>9}{'v2 DD':>9}{'B&H ret':>9}{'B&H DD':>9}"
        print(hdr)
        for th in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7):
            gate = gate_from_phigh(p2, th, max(th - 0.2, 0.05), 1).shift(1).fillna(True)
            for wname in ("sel_giro2022", "full_2020_2026"):
                s, e = WINDOWS[wname]
                s_ts, e_ts = pd.Timestamp(s, tz="UTC"), pd.Timestamp(e, tz="UTC")
                px = px_all[(px_all.index >= s_ts) & (px_all.index <= e_ts)]
                if len(px) < 8:
                    continue
                ms = eval_window(px_all, p2, gate, days, s, e, None)
                v2v, _ = simulate_periods(px, v2_scaled_signal(px, days), days)
                v2m = metrics(v2v, 365.0 / days)
                bhm = metrics(buyhold_curve(px), 365.0 / days)
                sweep.setdefault(f"th{th}", {})[wname] = {"ms": ms, "v2": v2m, "bh": bhm}
                print(f"    {th:<8}{wname:<16}{ms['ret_pct']:>9.1f}{ms['maxdd_pct']:>9.1f}"
                      f"{v2m['ret_pct']:>9.1f}{v2m['maxdd_pct']:>9.1f}"
                      f"{bhm['ret_pct']:>9.1f}{bhm['maxdd_pct']:>9.1f}")
        blk["sweep"] = sweep
        out[freq_name] = blk

    name = f"ms_regime_freq_sweep{('_' + a.tag) if a.tag else ''}.json"
    (OUT_DIR / name).write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"\n✅ {OUT_DIR/name}")


if __name__ == "__main__":
    main()
