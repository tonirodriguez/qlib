"""jev_backtest_ab.py — Backtest A/B: exposicion FIJA vs exposicion por JEV.

FASE 2 del plan Jev/OpenRouter. Compara tres estrategias de sizing sobre el
MISMO motor de momentum, para aislar el efecto de la capa de decision:

  A) FIXED     : exposicion = 1.0 siempre (comprado todo el tiempo).
  B) VOL_GATE  : exposicion segun el vol_gate.py existente (3 estados + histeresis).
  C) JEV       : exposicion = 1 - P(crisis) - 0.5*P(risk_off), via Jev/OpenRouter.

OBJETIVO: responder con datos si Jev aporta algo sobre el gate que ya tienes.
NO es un backtest de paper-trading: es un estudio de la CAPA DE DECISION.

COMO EJECUTARLO (en la maquina con qlib + datos):
    cd <repo>/work/estrategias
    python jev_backtest_ab.py

Salida: tabla comparativa + CSV con la serie de exposiciones y retornos.
Coste Jev: ~$0.000022 por fecha. Con 2.000 fechas ~ $0.044.

REQUISITOS
    - OPENROUTER_API_KEY en el entorno o en el .env del repo
    - qlib con datos en QLIB_US_DATA (o ~/.qlib/qlib_data/us_data)
    - numpy, pandas, requests, certifi
    - Certificado de Kaspersky SOLO si estas en la maquina con inspeccion TLS.

ADVERTENCIAS METODOLOGICAS (leer antes de interpretar)
    1. vol_pct, drawdown120 y mom_crash SON causales (verificado con
       demo_leak_vol_pct.py). El vol_gate tambien. No hay leak en las features.
    2. El leak posible esta en el CODIGO DE SIMULACION: no normalices los
       retornos sobre la muestra completa, no elijas umbrales mirando el
       resultado, no reutilices una clasificacion de 2026 para 2019.
    3. El benchmark es el propio universo, no el S&P500. Sharpe y drawdown son
       relativos a la estrategia de momentum, no al indice.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# --- import del clasificador Jev (mismo directorio) ---
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from jev_regime import JevRegimeClassifier, exposure_from_probabilities  # noqa: E402
from vol_gate import vol_percentile, gate_level_from_pct  # noqa: E402

REPO_ROOT = HERE.parents[1]
TRADING_DAYS = 252
MIN_HISTORY = 260  # dias minimos antes de empezar a operar


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def find_qlib_uri() -> str:
    """Localiza el directorio de datos qlib probando las rutas conocidas."""
    candidates = [
        os.environ.get("QLIB_US_DATA"),
        os.path.expanduser("~/.qlib/qlib_data/us_data"),
        "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data",
        str(REPO_ROOT / "qlib_data/us_data"),
    ]
    for c in candidates:
        if c and os.path.isdir(c) and os.path.isdir(os.path.join(c, "instruments")):
            return c
    raise FileNotFoundError(
        "No encuentro qlib_data. Define QLIB_US_DATA o coloca los datos en "
        "~/.qlib/qlib_data/us_data. Rutas probadas:\n  " + "\n  ".join(str(c) for c in candidates)
    )


def load_market_data(start: str = "2018-01-01", end: str = "2026-12-31",
                     max_tickers: int = 120) -> tuple[pd.Series, pd.DataFrame]:
    """Devuelve (bench_close, precios del universo) desde qlib."""
    import qlib
    from qlib.data import D

    uri = find_qlib_uri()
    print(f"  qlib_data: {uri}")
    qlib.init(provider_uri=uri, region="us")

    tickers: list[str] = []

    # 1) Universo: prioridad explicita. `sp500.txt` es el correcto para este
    #    proyecto (incluye composicion historica -> evita sesgo de supervivencia).
    #    NO se usa `all.txt` por defecto: son 15k tickers con micro-caps y
    #    liquidez muy desigual, lo que cambiaria por completo el backtest.
    inst_dir = os.path.join(uri, "instruments")
    inst_file = None
    for name in ("sp500_liquid.txt", "sp500.txt", "nasdaq100.txt"):
        p = os.path.join(inst_dir, name)
        if os.path.exists(p):
            inst_file = p
            break

    if inst_file is None and os.path.isdir(inst_dir):
        found = sorted(
            os.path.join(inst_dir, f) for f in os.listdir(inst_dir)
            if f.lower().endswith(".txt") and "all" not in f.lower()
        )
        if found:
            inst_file = found[0]
            print(f"  AVISO: sin sp500/sp500_liquid; uso {os.path.basename(inst_file)}")

    if inst_file and os.path.exists(inst_file):
        with open(inst_file) as f:
            for line in f:
                t = line.split("\t")[0].strip()
                if t:
                    tickers.append(t)
        print(f"  universo desde {os.path.basename(inst_file)}: {len(tickers)} tickers")

    # 2) Fallback: preguntar a qlib.
    if not tickers:
        for name in ("sp500", "csi300", "csi500"):
            try:
                tickers = D.list_instruments(D.instruments(name), as_list=True)
                if tickers:
                    print(f"  universo via qlib.instruments('{name}'): {len(tickers)} tickers")
                    break
            except Exception:
                continue
    if not tickers:
        raise ValueError(
            f"No encuentro universo en {inst_dir}. Contenido: "
            f"{os.listdir(inst_dir) if os.path.isdir(inst_dir) else 'no existe'}. "
            "Define QLIB_US_DATA o revisa los instrumentos."
        )

    # Truncar por orden alfabetico sesgaria la muestra (MMM, AOS, ABT...).
    # Se muestrea de forma determinista y REPARTIDA por todo el universo.
    if len(tickers) > max_tickers:
        total = len(tickers)
        idx = np.linspace(0, total - 1, max_tickers).astype(int)
        tickers = [tickers[i] for i in idx]
        print(f"  muestreo: {total} -> {len(tickers)} tickers (uniforme, no alfabetico)")
    else:
        tickers = [t for t in tickers if t]
    print(f"  universo final: {len(tickers)} tickers")

    close = D.features(tickers, ["$close", "$factor"], start_time=start,
                       end_time=end, freq="day")
    c = close["$close"].unstack(level=0).sort_index()
    f = close["$factor"].unstack(level=0).sort_index()
    prices = (c / f).dropna(axis=1, how="all")

    # Benchmark: ^GSPC si existe; si no, media del universo
    try:
        b = D.features(["^GSPC"], ["$close", "$factor"], start_time=start,
                       end_time=end, freq="day")
        bc = b["$close"].unstack(level=0)["^GSPC"]
        bf = b["$factor"].unstack(level=0)["^GSPC"]
        bench = (bc / bf).dropna().sort_index()
        print(f"  benchmark: ^GSPC ({len(bench)} fechas)")
    except Exception:
        bench = prices.mean(axis=1).dropna()
        print(f"  benchmark: media del universo ({len(bench)} fechas)")
    return bench, prices


# ---------------------------------------------------------------------------
# Features de estado (CAUSALES)
# ---------------------------------------------------------------------------

def build_states(bench: pd.Series, vol_win: int = 20, hist_win: int = 252) -> pd.DataFrame:
    """Indicadores de regimen por fecha. Todos CAUSALES (solo miran al pasado)."""
    ret = bench / bench.shift(1) - 1
    vol = ret.rolling(vol_win).std() * np.sqrt(TRADING_DAYS)

    # vol_percentile de vol_gate.py ya es causal y usa x.iloc[:-1]
    vol_s, pct = vol_percentile(bench, vol_win=vol_win, hist_win=hist_win)

    ret120 = bench / bench.shift(120) - 1
    dd120 = (ret120 < 0).astype(int)

    out = pd.DataFrame({
        "vol": vol_s,
        "vol_pct": pct,
        "drawdown120": dd120,
    })
    return out


# ---------------------------------------------------------------------------
# Motor de backtest
# ---------------------------------------------------------------------------

def run_strategy(prices: pd.DataFrame, exposure: pd.Series,
                 top_n: int = 20, lookback: int = 120,
                 rebalance_days: int = 5, cost_bps: float = 5.0) -> pd.Series:
    """Momentum simple con exposicion variable.

    - Senal: retorno de las ultimas `lookback` sesiones, top_n elegidos.
    - Rebalanceo cada `rebalance_days` sesiones.
    - `exposure` (0..1) escala la posicion bruta total.
    - Costes: `cost_bps` por unidad de turnover.
    """
    rets = prices.pct_change()
    mom = prices / prices.shift(lookback) - 1

    expo = exposure.reindex(rets.index).ffill().fillna(1.0).clip(0, 1)
    net = pd.Series(0.0, index=rets.index)

    current: set[str] = set()
    for i in range(lookback + 1, len(rets.index), rebalance_days):
        date = rets.index[i]
        row = mom.iloc[i].dropna()
        if len(row) < top_n:
            continue
        chosen = set(row.nlargest(top_n).index)
        w_new = 1.0 / top_n

        # turnover: fraccion de la cartera que cambia
        turnover = len(chosen.symmetric_difference(current)) / max(len(chosen), 1)
        cost = turnover * cost_bps / 10_000.0 * float(expo.iloc[i])

        # retorno del periodo siguiente con la cartera elegida
        horizon = min(rebalance_days, len(rets.index) - i - 1)
        if horizon <= 0:
            break
        sub = rets.iloc[i + 1 : i + 1 + horizon]
        # exposicion media del tramo (causal: se conoce al inicio)
        e = float(expo.iloc[i])
        port = sub[list(chosen)].mean(axis=1) * e
        net.iloc[i + 1 : i + 1 + horizon] = port.values
        if len(net) > i + 1:
            net.iloc[i + 1] -= cost  # coste en el primer dia del tramo
        current = chosen
    return net


def metrics(net: pd.Series, exposure: pd.Series | None = None) -> dict:
    """Metricas de la serie de retornos netos."""
    r = net.dropna()
    if len(r) < 20 or r.std() == 0:
        return {"n": len(r), "sharpe": np.nan, "cagr": np.nan,
                "max_dd": np.nan, "vol": np.nan, "turnover": np.nan}
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    years = len(r) / TRADING_DAYS
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    sharpe = r.mean() / r.std() * np.sqrt(TRADING_DAYS)
    return {
        "n": len(r),
        "sharpe": float(sharpe),
        "cagr": float(cagr),
        "max_dd": float(dd.min()),
        "vol": float(r.std() * np.sqrt(TRADING_DAYS)),
        "avg_exposure": float(exposure.reindex(r.index).mean()) if exposure is not None else 1.0,
    }


# ---------------------------------------------------------------------------
# Construccion de la exposicion JEV
# ---------------------------------------------------------------------------

def build_jev_exposure(states: pd.DataFrame, cache_file: Path,
                       sleep_s: float = 0.0, max_dates: int | None = None) -> pd.Series:
    """Clasifica cada fecha con Jev y devuelve la serie de exposicion.

    Usa cache en disco: repetir el backtest no vuelve a llamar a la API.
    """
    cache: dict = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
            print(f"  cache: {len(cache)} fechas ya clasificadas")
        except Exception:
            cache = {}

    # Compatibilidad: la cache antigua guardaba solo el escalar (float).
    # Detectamos si tiene probabilidades; si no, hay que reclasificar.
    n_float = sum(1 for v in cache.values() if isinstance(v, (int, float)))
    n_dict = sum(1 for v in cache.values() if isinstance(v, dict))
    if n_float and not n_dict:
        print(f"  AVISO: cache en formato antiguo ({n_float} escalares, sin "
              f"probabilidades). Se reclasificara para guardar el vector completo.")
        cache = {}

    clf = JevRegimeClassifier()
    dates = states.index
    if max_dates:
        dates = dates[-max_dates:]

    out: dict[str, float] = {}
    to_call = [d for d in dates if d.isoformat() not in cache]
    print(f"  fechas a clasificar con Jev: {len(to_call)} (de {len(dates)})")

    for i, d in enumerate(to_call):
        row = states.loc[d]
        feats = {
            "vol_pct": None if pd.isna(row.get("vol_pct")) else round(float(row["vol_pct"]), 4),
            "drawdown120": int(row.get("drawdown120", 0)),
            "vol_20d": None if pd.isna(row.get("vol")) else round(float(row["vol"]), 4),
        }
        dec = clf.classify(feats)
        expo = dec.exposure if not dec.error else 1.0
        # Guardar el VECTOR DE PROBABILIDADES, no solo el escalar: asi se pueden
        # probar formulas alternativas de sizing sin volver a llamar a la API.
        if dec.error:
            cache[d.isoformat()] = {"exposure": round(float(expo), 4),
                                    "probs": {}, "error": dec.error}
        else:
            cache[d.isoformat()] = {
                "exposure": round(float(expo), 4),
                "probs": {k: round(float(v), 4) for k, v in dec.probabilities.items()},
                "confidence": dec.confidence,
                "model": dec.model_returned,
            }
        out[d.isoformat()] = round(float(expo), 4)
        if (i + 1) % 25 == 0:
            print(f"    {i+1}/{len(to_call)} ... ({d.date()}) exp={expo:.3f}")
        if sleep_s:
            time.sleep(sleep_s)

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    s = pd.Series({
        pd.Timestamp(k): (v.get("exposure", 1.0) if isinstance(v, dict) else float(v))
        for k, v in cache.items()
    }).sort_index()
    return s


def load_probabilities(cache_file: Path) -> pd.DataFrame:
    """Carga los vectores de probabilidad de la cache como DataFrame.

    Columnas: una por etiqueta (risk_on, neutral, risk_off, crisis) + confidence.
    Permite recalcular formulas de sizing SIN volver a llamar a la API.
    """
    if not cache_file.exists():
        return pd.DataFrame()
    raw = json.loads(cache_file.read_text(encoding="utf-8"))
    rows = {}
    for k, v in raw.items():
        if isinstance(v, dict) and v.get("probs"):
            rows[pd.Timestamp(k)] = {**v["probs"], "confidence": v.get("confidence")}
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Backtest A/B de la capa de decision Jev.")
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-12-31")
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--lookback", type=int, default=120)
    ap.add_argument("--rebalance-days", type=int, default=5)
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--max-tickers", type=int, default=120)
    ap.add_argument("--jev-max-dates", type=int, default=None,
                    help="Limita el numero de fechas clasificadas con Jev (para pruebas)")
    ap.add_argument("--no-jev", action="store_true", help="Solo A y B (sin llamar a la API)")
    ap.add_argument("--out", default=str(HERE / "jev_backtest_ab_results.csv"))
    args = ap.parse_args()

    print("=" * 78)
    print("BACKTEST A/B - CAPA DE DECISION (FIXED vs VOL_GATE vs JEV)")
    print("=" * 78)

    # 1) Datos
    print("\n[1/4] Cargando datos...")
    bench, prices = load_market_data(args.start, args.end, args.max_tickers)
    prices = prices.dropna(axis=0, thresh=int(0.5 * prices.shape[1]))
    print(f"  precios: {prices.shape[0]} fechas x {prices.shape[1]} tickers")

    # 2) Estados
    print("\n[2/4] Construyendo estados de regimen (causales)...")
    states = build_states(bench)
    states = states.dropna(subset=["vol_pct"])
    print(f"  estados validos: {len(states)} fechas "
          f"({states.index.min().date()} -> {states.index.max().date()})")

    # 3) Exposiciones
    print("\n[3/4] Construyendo series de exposicion...")
    expo_fixed = pd.Series(1.0, index=states.index)
    expo_gate = states["vol_pct"].apply(
        lambda x: gate_level_from_pct(x) if pd.notna(x) else 1.0
    )
    print(f"  A) FIXED   : exposion media {expo_fixed.mean():.3f}")
    print(f"  B) VOL_GATE: exposion media {expo_gate.mean():.3f} "
          f"(dias a 0: {(expo_gate == 0).sum()}, a 0.5: {(expo_gate == 0.5).sum()})")

    expo_jev = None
    if not args.no_jev:
        cache_file = HERE / "jev_phase0_out" / "jev_exposure_cache.json"
        try:
            expo_jev = build_jev_exposure(states, cache_file, max_dates=args.jev_max_dates)
            print(f"  C) JEV     : exposion media {expo_jev.mean():.3f} "
                  f"(dias a 0: {(expo_jev <= 0.05).sum()})")
        except Exception as exc:  # noqa: BLE001
            print(f"  C) JEV     : FALLO ({exc})")

    # 4) Backtest
    print("\n[4/4] Ejecutando backtest...")
    results = {}

    net_a = run_strategy(prices, expo_fixed, args.top_n, args.lookback,
                         args.rebalance_days, args.cost_bps)
    results["A_FIXED"] = metrics(net_a, expo_fixed)

    net_b = run_strategy(prices, expo_gate, args.top_n, args.lookback,
                         args.rebalance_days, args.cost_bps)
    results["B_VOL_GATE"] = metrics(net_b, expo_gate)

    if expo_jev is not None:
        net_c = run_strategy(prices, expo_jev, args.top_n, args.lookback,
                             args.rebalance_days, args.cost_bps)
        results["C_JEV"] = metrics(net_c, expo_jev)

    # 5) Tabla
    print("\n" + "=" * 78)
    print("RESULTADOS")
    print("=" * 78)
    df = pd.DataFrame(results).T
    cols = ["n", "sharpe", "cagr", "max_dd", "vol", "avg_exposure"]
    df = df[[c for c in cols if c in df.columns]]
    for c in ["sharpe", "cagr", "max_dd", "vol", "avg_exposure"]:
        if c in df:
            df[c] = df[c].round(4)
    print(df.to_string())

    # Deltas vs baseline
    print("\n" + "-" * 78)
    print("DELTA vs A_FIXED (positivo = mejor)")
    print("-" * 78)
    base = results["A_FIXED"]
    for name, r in results.items():
        if name == "A_FIXED":
            continue
        ds = r["sharpe"] - base["sharpe"]
        dc = r["cagr"] - base["cagr"]
        dd = r["max_dd"] - base["max_dd"]  # menos negativo = mejor
        print(f"  {name:<12} dSharpe={ds:+.4f}  dCAGR={dc:+.2%}  "
              f"dMaxDD={dd:+.2%}  expo_media={r['avg_exposure']:.3f}")

    # 6) Guardar serie
    out_df = pd.DataFrame({
        "expo_fixed": expo_fixed,
        "expo_gate": expo_gate,
        "ret_fixed": net_a,
        "ret_gate": net_b,
    })
    if expo_jev is not None:
        out_df["expo_jev"] = expo_jev.reindex(out_df.index)
        out_df["ret_jev"] = net_c.reindex(out_df.index)
    out_df.to_csv(args.out)
    print(f"\nSerie guardada en: {args.out}")

    # 7) Veredicto
    print("\n" + "=" * 78)
    print("VEREDICTO")
    print("=" * 78)
    if "C_JEV" in results:
        d = results["C_JEV"]["sharpe"] - base["sharpe"]
        dg = results["B_VOL_GATE"]["sharpe"] - base["sharpe"]
        print(f"  Sharpe A(fixed)={base['sharpe']:.3f}  "
              f"B(vol_gate)={results['B_VOL_GATE']['sharpe']:.3f}  "
              f"C(jev)={results['C_JEV']['sharpe']:.3f}")
        if d <= 0:
            print("  >> Jev NO mejora el Sharpe frente a exposicion fija.")
            print("     Considera descartar la capa Jev o reformular la pregunta.")
        elif d > dg:
            print(f"  >> Jev mejora Sharpe ({d:+.3f}) MAS que el vol_gate ({dg:+.3f}).")
            print("     Merece investigacion adicional antes de adoptarlo.")
        else:
            print(f"  >> Jev mejora ({d:+.3f}) pero el vol_gate ya mejora mas ({dg:+.3f}).")
            print("     El vol_gate simple es suficiente; Jev no aporta valor anadido.")
    else:
        print("  Solo A y B ejecutados (sin Jev).")
    print("\n  RECORDATORIO: una sola muestra, sin out-of-sample. No adoptar")
    print("  ninguna conclusion como definitiva sin validacion fuera de muestra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
