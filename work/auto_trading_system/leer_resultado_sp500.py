"""leer_resultado_sp500.py — Extrae las metricas del baseline SP500.

Lee el experimento de MLflow guardado por qrun y muestra:
  - Metricas de senal (IC, Rank IC, ICIR)
  - Metricas de portfolio (retorno, Sharpe, drawdown, turnover)
  - Comparacion con el baseline CSI300

Ejecutar en WSL:
    conda run -n qlib python work/auto_trading_system/leer_resultado_sp500.py
    conda run -n qlib python work/auto_trading_system/leer_resultado_sp500.py <recorder_id>
"""
from __future__ import annotations

import sys
from pathlib import Path

import qlib
from qlib.workflow import R

REPO = Path(__file__).resolve().parents[2]
URI = "~/.qlib/qlib_data/us_data"

# Referencia: baseline mercado chino (mismo modelo, alpha158)
CSI300 = {"ann": 0.1473, "ic": 0.0487, "icir": 0.4057, "name": "CSI300 baseline (top50)"}


def fmt(v, pct=False, dec=4):
    if v is None:
        return "  n/a"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return f"  {v}"
    if f != f:  # NaN
        return "  n/a"
    return f"{f*100:+.2f}%" if pct else f"{f:.{dec}f}"


def main() -> int:
    qlib.init(provider_uri=URI, region="us")

    rec_id = sys.argv[1] if len(sys.argv) > 1 else None
    exp = R.get_exp(experiment_name="workflow")
    recorders = exp.list_recorders()

    if not recorders:
        print("No hay recorders en el experimento 'workflow'.")
        return 1

    if rec_id:
        rec = recorders.get(rec_id)
        if rec is None:
            print(f"No existe el recorder {rec_id}")
            print(f"Disponibles: {list(recorders.keys())}")
            return 1
    else:
        rec = list(recorders.values())[-1]
        rec_id = rec.id

    print("=" * 76)
    print(" RESULTADO DEL BASELINE SP500 US — LightGBM + Alpha158")
    print("=" * 76)
    print(f"  experimento : workflow")
    print(f"  recorder    : {rec_id}")

    metrics = rec.list_metrics()

    # --- Metricas de senal ---
    print("\n" + "-" * 76)
    print(" METRICAS DE SENAL (poder predictivo)")
    print("-" * 76)
    sig_keys = [k for k in metrics if k in ("IC", "ICIR", "Rank IC", "Rank ICIR")]
    for k in ("IC", "ICIR", "Rank IC", "Rank ICIR"):
        if k in metrics:
            print(f"  {k:<12} {fmt(metrics[k])}")

    ic = metrics.get("Rank IC") or metrics.get("IC")

    # --- Metricas de portfolio ---
    print("\n" + "-" * 76)
    print(" METRICAS DE PORTFOLIO")
    print("-" * 76)

    # Las claves llevan prefijo; buscamos por sufijo
    def find(suffix):
        for k, v in metrics.items():
            if k.endswith(suffix):
                return k, v
        return None, None

    interesting = [
        ("annualized_return", "Retorno anualizado", True),
        ("information_ratio", "Information Ratio", False),
        ("max_drawdown", "Max Drawdown", True),
        ("annualized_volatility", "Volatilidad anual", True),
    ]

    found = {}
    for suffix, label, pct in interesting:
        k, v = find(suffix)
        if k:
            found[suffix] = v
            print(f"  {label:<22} {fmt(v, pct=pct)}")
            print(f"  {'':<22} (clave: {k})")

    # Sharpe: qlib no lo da directo en algunos casos
    k_ret, v_ret = find("annualized_return")
    k_vol, v_vol = find("annualized_volatility")
    if v_ret is not None and v_vol not in (None, 0):
        try:
            sharpe = float(v_ret) / float(v_vol)
            print(f"\n  {'Sharpe (calculado)':<22} {sharpe:.4f}")
            print(f"  {'':<22} = retorno anual / volatilidad anual")
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    # --- Todas las metricas ---
    print("\n" + "-" * 76)
    print(" TODAS LAS METRICAS REGISTRADAS")
    print("-" * 76)
    for k in sorted(metrics):
        print(f"  {k:<52} {fmt(metrics[k])}")

    # --- Comparacion con CSI300 ---
    print("\n" + "=" * 76)
    print(" COMPARACION CON EL BASELINE CHINO")
    print("=" * 76)
    print(f"  {'Mercado':<34} {'Rank IC':>10} {'Ann Return':>12}")
    print(f"  {'-'*34} {'-'*10} {'-'*12}")
    print(f"  {'CSI300 (top50, label 1d)':<34} {CSI300['ic']:>10.4f} {CSI300['ann']*100:>11.2f}%")

    if ic is not None:
        ann = found.get("annualized_return")
        print(f"  {'SP500 US (top30, label 1d)':<34} {float(ic):>10.4f} "
              f"{float(ann)*100 if ann is not None else float('nan'):>11.2f}%")

    # --- Veredicto ---
    print("\n" + "=" * 76)
    print(" VEREDICTO")
    print("=" * 76)

    if ic is None:
        print("  No hay metrica de IC registrada; no se puede juzgar la senal.")
    else:
        icf = float(ic)
        if icf > 0.02:
            print(f"  Rank IC = {icf:.4f} > 0.02  ->  La senal SI tiene poder predictivo.")
        elif icf > 0:
            print(f"  Rank IC = {icf:.4f} (0 < IC < 0.02)  ->  Senal DEBIL pero positiva.")
        else:
            print(f"  Rank IC = {icf:.4f} <= 0  ->  La senal NO predice. Revisar datos/features.")

    ann = found.get("annualized_return")
    if ann is not None:
        a = float(ann)
        if a > 0.05:
            print(f"  Retorno anual {a*100:+.2f}%  ->  Bate a cash con holgura.")
        elif a > 0:
            print(f"  Retorno anual {a*100:+.2f}%  ->  Positivo pero modesto.")
        else:
            print(f"  Retorno anual {a*100:+.2f}%  ->  NEGATIVO. Revisar costes y config.")

    dd, _ = find("max_drawdown")
    if dd is not None:
        print(f"  Max drawdown {float(dd)*100:+.2f}%  ->  "
              f"{'moderado' if float(dd) > -0.3 else 'SEVERO'}")

    print("\n  Recordatorio: mercado US es mas eficiente que CN.")
    print("  Un IC de 0.02-0.04 es un resultado NORMAL, no un fracaso.")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
