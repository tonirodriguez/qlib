"""ms_regime.py — Réplica de Markov-Switching (Vansteenberghe 2026, sección 53) sobre cripto.

Objetivo: sustituir la regla heurística de régimen (MA + drawdown + histéresis, ver
`regime_switch_v2.py`) por un ESTADO DE VOLATILIDAD estimado con un modelo de cambio de
régimen de varianza (paper §53.2 Hamilton 1989 / §53.3 Kim et al. 1998, Hamilton-Susmel 1994)
y contrastar ambos como gate LONG<->CASH sobre BTC.

Metodología (siguiendo los cuidados del propio autor del paper):
  * Ajuste Markov-switching de 2 estados con VARIANZA conmutada sobre retornos diarios de BTC.
  * Señal ESTRICTAMENTE CAUSAL: refit en ventana EXPANSIVA cada `--refit-days` días; en cada
    refit se estiman los parámetros SOLO con datos pasados y luego se filtran (Hamilton/Kim
    one-sided filter) los días nuevos con esos parámetros congelados. Nunca se usa el futuro.
  * Test BDS (§53.1) sobre los retornos crudos y sobre los retornos estandarizados r/sigma_t:
    si rechaza iid en crudos y NO lo rechaza en estandarizados, el modelo captura la estructura
    no lineal (validación que usa el propio paper).
  * Comparativa contra `regime_switch_v2.regime_signal_v2` en las MISMAS ventanas de
    selección/OOS que usa el proyecto cripto, con el MISMO simulador (costes, yield cash).

Uso:
    python work/crypto/ms_regime.py                        # comparativa completa
    python work/crypto/ms_regime.py --th-enter 0.6 --th-exit 0.3
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


@contextlib.contextmanager
def quiet():
    """Silencia el ruido de statsmodels (ValueWarning de frecuencia) dentro del bloque."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

OHLCV_DIR = PROJECT_ROOT / "scripts" / "crypto" / "csv_data" / "crypto_cryptocompare" / "ohlcv"
OUT_DIR = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8" / "regimenes"
INITIAL_USD = 11000.0
PROXY = "btc"

# Ventanas idénticas a calibra_switch.py / calibra_vitalidad.py
WINDOWS = {
    "sel_bull2021": ("2020-11-01", "2021-11-30"),
    "sel_giro2022": ("2021-06-01", "2022-12-31"),
    "oos_rally2024": ("2024-01-01", "2024-12-31"),
    "oos_base2025": ("2025-01-01", "2026-08-30"),
}
FULL_WINDOW = ("2020-11-01", "2026-08-30")


# ----------------------------------------------------------------------------- datos
def load_proxy(proxy=PROXY):
    df = pd.read_csv(OHLCV_DIR / f"{proxy}.csv", parse_dates=["date"]).set_index("date")
    return df["close"].dropna()


# ------------------------------------------------------------------- Markov-switching
def ms_filtered_highvol_prob(returns: pd.Series, fit_start: str, refit_days: int):
    """Probabilidad FILTRADA (causal) del estado de ALTA volatilidad.

    Refit en ventana expansiva cada `refit_days`: parámetros estimados sólo con el pasado,
    filtrado hacia delante con parámetros congelados hasta el siguiente refit.
    Devuelve (p_high, sigma_filtrada, n_refits, params_final).
    """
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    r = returns.copy()
    r = r[r.index >= pd.Timestamp(fit_start, tz="UTC")]
    idx = r.index
    n = len(r)

    p_high = pd.Series(np.nan, index=idx)
    sig_t = pd.Series(np.nan, index=idx)
    n_refits = 0
    last_params = None

    # Primera estimación necesita al menos ~500 días
    fit_positions = list(range(500, n, refit_days))
    if not fit_positions or fit_positions[-1] != n - 1:
        fit_positions.append(n - 1)

    prev = 500
    for pos in fit_positions:
        train = r.iloc[:pos]
        try:
            with quiet():
                mod = MarkovRegression(train, k_regimes=2, trend="c", switching_variance=True)
                res = mod.fit(disp=False, maxiter=300)
                params = res.params
                s2 = [params.get("sigma2[0]"), params.get("sigma2[1]")]
                hi = int(np.argmax(s2))  # estado de mayor varianza = alta vol
                # filtrar hacia delante con parámetros congelados (incluye el bloque nuevo)
                seg = r.iloc[: min(pos + refit_days, n)]
                mod_seg = MarkovRegression(seg, k_regimes=2, trend="c", switching_variance=True)
                res_seg = mod_seg.filter(params)
            fp = res_seg.filtered_marginal_probabilities[hi]
            p_high.iloc[prev: min(pos + refit_days, n)] = fp.iloc[prev: min(pos + refit_days, n)].values
            sig = np.sqrt(params.get(f"sigma2[{hi}]"))
            sig_t.iloc[prev: min(pos + refit_days, n)] = sig
            n_refits += 1
            last_params = {k: float(v) for k, v in params.items()}
            prev = min(pos + refit_days, n)
        except Exception as e:  # pragma: no cover
            print(f"  [warn] refit en {idx[pos].date()} falló: {e}", file=sys.stderr)

    return p_high, sig_t, n_refits, last_params


def ms_fullsample(returns: pd.Series, fit_start: str, k_regimes: int = 2):
    """Ajuste en muestra completa (solo para caracterizar estados; NO se usa para el gate)."""
    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    r = returns[returns.index >= pd.Timestamp(fit_start, tz="UTC")]
    with quiet():
        mod = MarkovRegression(r, k_regimes=k_regimes, trend="c", switching_variance=True)
        res = mod.fit(disp=False, maxiter=500)
        params = res.params
    s2 = {i: float(params.get(f"sigma2[{i}]", np.nan)) for i in range(k_regimes)}
    hi = max(s2, key=lambda i: (s2[i] if s2[i] == s2[i] else -1))
    sm = res.smoothed_marginal_probabilities
    ann_sig = {i: float(np.sqrt(v * 365) * 100) for i, v in s2.items()}
    ann_mu = {i: float(params.get(f"const[{i}]", np.nan) * 365 * 100) for i in range(k_regimes)}
    # persistencia esperada (días) de cada estado.
    # OJO: statsmodels sólo reporta 'p[i->j]' con j el OTRO estado (no la diagonal para i>0),
    # así que p_ii = 1 - p[i->j] salvo para i=0, donde sí da 'p[0->0]'.
    pers = {}
    for i in range(k_regimes):
        key = f"p[{i}->{i}]"
        if key in params:
            p_ii = float(params[key])
        else:
            otros = [k for k in params.index if k.startswith(f"p[{i}->") and k != key]
            p_ii = 1.0 - float(params[otros[0]]) if otros else np.nan
        pers[i] = float(1.0 / (1.0 - p_ii)) if p_ii == p_ii and p_ii < 1 else np.inf
    return {
        "k": k_regimes, "high_vol_state": int(hi),
        "sigma_anual_pct": ann_sig, "media_anual_pct": ann_mu,
        "persistencia_dias": pers,
        "loglik": float(res.llf), "aic": float(res.aic),
        "smoothed_high": sm[hi].copy(),
        "params": {k: float(v) for k, v in params.items()},
    }


# ------------------------------------------------------------------ gate desde p_high
def gate_from_phigh(p_high: pd.Series, th_enter=0.5, th_exit=0.3, min_state_days=5):
    """Gate LONG/CASH causal con histéresis (mismo patrón que el proyecto).

    Estamos LONG por defecto. Pasamos a CASH si P(alta vol) > th_enter; volvemos a LONG
    cuando P(alta vol) < th_exit. Se mantiene el estado >= min_state_days.
    """
    state = np.ones(len(p_high), dtype=int)  # 1 = LONG
    cur = 1
    for i, p in enumerate(p_high.values):
        if p != p:  # NaN (warm-up) -> LONG neutro
            state[i] = cur
            continue
        if cur == 1 and p > th_enter:
            cur = 0
        elif cur == 0 and p < th_exit:
            cur = 1
        state[i] = cur
    # histéresis sobre las transiciones a CASH
    out = np.ones(len(state), dtype=int)
    i, n = 0, len(state)
    while i < n:
        if state[i] == 0:
            end = min(i + min_state_days, n)
            out[i:end] = 0
            i = end
        else:
            out[i] = 1
            i += 1
    return pd.Series(out.astype(bool), index=p_high.index)


# ------------------------------------------------------------------------ métricas
def curve_metrics(vals):
    vals = np.asarray(vals, dtype=float)
    peak = np.maximum.accumulate(vals)
    dd = vals / peak - 1.0
    rets = np.diff(vals) / vals[:-1]
    return {
        "ret_pct": round((vals[-1] / vals[0] - 1) * 100, 1),
        "maxdd_pct": round(float(dd.min()) * 100, 1),
        "vol_anual_pct": round(float(np.std(rets) * np.sqrt(365) * 100), 1) if len(rets) else np.nan,
        "sharpe": round(float(np.mean(rets) / np.std(rets) * np.sqrt(365)), 2) if len(rets) and np.std(rets) else np.nan,
    }


def simulate(price, signal, initial_usd=INITIAL_USD, cash_apy=0.045, cost=0.0010):
    """Mismo simulador que regime_switch_v2 (long/cash sobre el proxy)."""
    daily = (1.0 + cash_apy) ** (1.0 / 365.0) - 1.0
    cash = initial_usd
    shares = 0.0
    trades = 0
    curve = []
    for day in price.index:
        long_now = bool(signal.get(day, True))
        px = float(price.loc[day])
        cash += cash * daily
        if long_now and shares == 0 and px > 0:
            trades += 1
            fee = cash * cost
            shares = (cash - fee) / px
            cash = 0.0
        elif not long_now and shares > 0:
            trades += 1
            cash += shares * px - shares * px * cost
            shares = 0.0
        curve.append(cash + (shares * px if shares > 0 else 0.0))
    return np.array(curve), trades


def buyhold_curve(price, initial_usd=INITIAL_USD):
    return initial_usd * (price / price.iloc[0]).values


def usdt_curve(price, initial_usd=INITIAL_USD, cash_apy=0.045):
    daily = (1.0 + cash_apy) ** (1.0 / 365.0) - 1.0
    return initial_usd * (1.0 + daily) ** np.arange(len(price))


# --------------------------------------------------------------------------- test BDS
def _correlation_integral(x, m, eps):
    """Integral de correlación BDS: C(m,eps) = P(sup-norma de dos m-histórias < eps)."""
    x = np.asarray(x, dtype=float)
    emb = np.lib.stride_tricks.sliding_window_view(x, m)   # (T-m+1, m)
    Tn = emb.shape[0]
    if Tn < 2:
        return np.nan
    # distancia sup (Chebyshev) por pares
    d = np.abs(emb[:, None, :] - emb[None, :, :]).max(axis=2)
    M = d < eps
    np.fill_diagonal(M, False)          # excluir i == j
    return float(M.sum() / (Tn * (Tn - 1)))


def bds_statistic(x, m=2, eps_mult=1.5):
    """Estadístico BDS sin el término de varianza asintótica: D_m = C(m,eps) - C(1,eps)^m.

    Bajo H0 (iid) D_m debe ser ~0; su magnitud y el p-valor por permutación (ver
    bds_permutation_pvalue) dan el contraste. Es la lógica del test de Broock et al. (1996)
    omitiendo la varianza asintótica (que aquí aproximamos por permutación, más honesto
    para muestras financieras).
    """
    x = np.asarray(x, dtype=float)
    if len(x) < 50:
        return np.nan
    eps = eps_mult * float(np.std(x))
    C1 = _correlation_integral(x, 1, eps)
    Cm = _correlation_integral(x, m, eps)
    return float(Cm - C1 ** m)


def bds_permutation_pvalue(x, m=2, eps_mult=1.5, n_perm=150, seed=7):
    """p-valor por permutación del estadístico BDS (H0: iid)."""
    obs = bds_statistic(x, m, eps_mult)
    if obs != obs:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    null = np.empty(n_perm)
    for i in range(n_perm):
        null[i] = bds_statistic(rng.permutation(x), m, eps_mult)
    p = float(np.mean(np.abs(null) >= abs(obs)))
    return obs, p


# -------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", default=PROXY)
    ap.add_argument("--fit-start", default="2017-01-01")
    ap.add_argument("--refit-days", type=int, default=21)
    ap.add_argument("--th-enter", type=float, default=0.5)
    ap.add_argument("--th-exit", type=float, default=0.3)
    ap.add_argument("--min-state-days", type=int, default=5)
    ap.add_argument("--k-bds", type=int, default=2)
    args = ap.parse_args()

    price_all = load_proxy(args.proxy)
    ret_all = np.log(price_all).diff().dropna()

    print("=" * 78)
    print(f"MARKOV-SWITCHING (paper §53.2/53.3) sobre {args.proxy.upper()} — gate LONG/CASH")
    print(f"Refit expansivo cada {args.refit_days}d desde {args.fit_start} | "
          f"th_enter={args.th_enter} th_exit={args.th_exit} min_state={args.min_state_days}d")
    print("=" * 78)

    # ---------- 1) probabilidad filtrada CAUSAL ----------
    print("\n[1] Estimando probabilidad filtrada causal del estado de alta vol…")
    p_high, sig_t, n_refits, params_final = ms_filtered_highvol_prob(
        ret_all, args.fit_start, args.refit_days)
    print(f"    refits: {n_refits} | días con p_high: {int(p_high.notna().sum())}")
    print(f"    parámetros del último refit: {params_final}")

    # ---------- 2) caracterización en muestra completa ----------
    print("\n[2] Caracterizando estados (muestra completa, solo descriptivo)…")
    fs2 = ms_fullsample(ret_all, args.fit_start, k_regimes=2)
    print(f"    k=2: estado alta-vol = {fs2['high_vol_state']}")
    for i in range(2):
        print(f"      estado {i}: sigma anual {fs2['sigma_anual_pct'][i]:.1f}% | "
              f"media anual {fs2['media_anual_pct'][i]:+.1f}% | "
              f"persistencia {fs2['persistencia_dias'][i]:.0f}d")
    fs3 = None
    try:
        fs3 = ms_fullsample(ret_all, args.fit_start, k_regimes=3)
        print(f"    k=3 (sensibilidad): sigmas anuales " +
              ", ".join(f"{fs3['sigma_anual_pct'][i]:.1f}%" for i in range(3)) +
              f" | AIC {fs3['aic']:.0f} (k=2: {fs2['aic']:.0f})")
    except Exception as e:
        print(f"    k=3 falló: {e}")

    # ---------- 3) test BDS (§53.1) ----------
    print("\n[3] Test BDS (Broock et al. 1996) — validación de no-linealidad §53.1")
    r_fit = ret_all[ret_all.index >= pd.Timestamp(args.fit_start, tz="UTC")]
    z = (r_fit / sig_t.reindex(r_fit.index)).dropna()
    bds_out = {}
    for label, series in [("retornos crudos", r_fit), ("retornos estandarizados r/sigma_t", z)]:
        for m in (2, 3):
            stat, pval = bds_permutation_pvalue(series.values, m=m, n_perm=300)
            bds_out[f"{label}_m{m}"] = {"stat": stat, "p": pval}
            verdict = "RECHAZA iid" if (pval == pval and pval < 0.05) else "no rechaza iid"
            print(f"    {label:<34} m={m}: stat={stat:+.5f}  p={pval:.3f}  -> {verdict}")

    # ---------- 4) gate y comparativa ----------
    gate = gate_from_phigh(p_high, args.th_enter, args.th_exit, args.min_state_days)

    from regime_switch_v2 import regime_signal_v2  # noqa: E402

    results = {}
    print("\n[4] Comparativa en las ventanas del proyecto (mismo simulador, costes 0.10%, cash 4.5%):")
    hdr = f"{'ventana':<14}{'estrategia':<22}{'ret%':>9}{'maxDD%':>9}{'Sharpe':>8}{'vol%':>8}{'trades':>8}{'díasLONG':>10}"
    print("\n" + hdr)
    print("-" * len(hdr))

    for wname, (s, e) in {**WINDOWS, "full_2020_2026": FULL_WINDOW}.items():
        s_ts, e_ts = pd.Timestamp(s, tz="UTC"), pd.Timestamp(e, tz="UTC")
        px = price_all[(price_all.index >= s_ts) & (price_all.index <= e_ts)]
        if len(px) < 30:
            continue
        # señales
        g_w = gate.reindex(px.index).fillna(True)
        v2_w = regime_signal_v2(px, vital_dd=0.30, pico_win=90, exit_dd=0.30,
                                ma_win=75, under_ma_days=10)
        rows = {}
        for name, sig in [("MS-gate (paper §53.3)", g_w), ("regime_switch_v2", v2_w)]:
            vals, tr = simulate(px, sig)
            met = curve_metrics(vals)
            rows[name] = {**met, "trades": tr, "dias_long": int(sig.sum())}
            print(f"{wname:<14}{name:<22}{met['ret_pct']:>9.1f}{met['maxdd_pct']:>9.1f}"
                  f"{met['sharpe']:>8.2f}{met['vol_anual_pct']:>8.1f}{tr:>8}{int(sig.sum()):>10}")
        # benchmarks
        for name, vals in [("buy&hold BTC", buyhold_curve(px)), ("USDT puro", usdt_curve(px))]:
            met = curve_metrics(vals)
            rows[name] = {**met, "trades": 0, "dias_long": len(px) if "hold" in name else 0}
            print(f"{wname:<14}{name:<22}{met['ret_pct']:>9.1f}{met['maxdd_pct']:>9.1f}"
                  f"{met['sharpe']:>8.2f}{met['vol_anual_pct']:>8.1f}{'-':>8}{'-':>10}")
        # acuerdo entre clasificaciones
        both = pd.DataFrame({"ms": g_w, "v2": v2_w}).dropna()
        agree = float((both["ms"] == both["v2"]).mean()) if len(both) else np.nan
        cash_ms = int((~both["ms"]).sum()); cash_v2 = int((~both["v2"]).sum())
        both_cash = int(((~both["ms"]) & (~both["v2"])).sum())
        print(f"{'':<14}acuerdo MS/v2={agree:.1%} | días CASH: MS={cash_ms} v2={cash_v2} ambos={both_cash}")
        print("-" * len(hdr))
        results[wname] = {"rows": rows, "acuerdo_ms_v2": round(agree, 4),
                          "dias_cash_ms": cash_ms, "dias_cash_v2": cash_v2,
                          "dias_cash_ambos": both_cash}

    # ---------- 5) persistencia de resultados ----------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "proxy": args.proxy, "fit_start": args.fit_start, "refit_days": args.refit_days,
        "gate": {"th_enter": args.th_enter, "th_exit": args.th_exit,
                 "min_state_days": args.min_state_days},
        "n_refits": n_refits, "params_ultimo_refit": params_final,
        "fullsample_k2": {k: v for k, v in fs2.items() if k != "smoothed_high"},
        "fullsample_k3": {k: v for k, v in fs3.items() if k != "smoothed_high"} if fs3 else None,
        "bds": bds_out,
        "comparativa": results,
    }
    (OUT_DIR / "ms_regime_results.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

    # serie de señal diaria para inspección/plot
    df_daily = pd.DataFrame({
        "price": price_all, "p_high": p_high.reindex(price_all.index),
        "ms_gate": gate.reindex(price_all.index),
    })
    df_daily.to_csv(OUT_DIR / "ms_regime_daily.csv")
    print(f"\n✅ Guardado: {OUT_DIR/'ms_regime_results.json'}")
    print(f"✅ Serie diaria: {OUT_DIR/'ms_regime_daily.csv'}")


if __name__ == "__main__":
    main()
