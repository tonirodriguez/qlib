"""Análisis del retorno ABSOLUTO (no solo exceso) para ver efecto del vol-targeting.

Usa la función interna normal_backtest de Qlib (la misma que usa qrun), que
construye exchange/executor/portfolio automáticamente. El reporte vuelve en el
primer elemento, con portfolio_value y benchmark_value por fecha.
"""
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:////opt/data/qlib/work/work/qlib_work/mlflow.db"

import numpy as np
import pandas as pd
import yaml

import qlib
from qlib.utils import init_instance_by_config
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')


def run_and_report(yml_path, tag):
    with open(yml_path) as f:
        cfg = yaml.safe_load(f)

    task_cfg = cfg['task']
    port_cfg = cfg['port_analysis_config']

    dataset = init_instance_by_config(task_cfg['dataset'])
    model = init_instance_by_config(task_cfg['model'])
    model.fit(dataset)

    pred = model.predict(dataset, segment='test')

    strat_cfg = port_cfg['strategy']
    strat_cfg['kwargs']['signal'] = pred
    strat = init_instance_by_config(strat_cfg)

    # backtest de alto nivel: pass strategy y executor config del yml
    from qlib.backtest import backtest
    ex_full = port_cfg.get('executor', {})
    report_normal, indicator_normal = backtest(
        start_time=port_cfg['backtest']['start_time'],
        end_time=port_cfg['backtest']['end_time'],
        strategy=strat,
        executor=ex_full,
        account=port_cfg['backtest']['account'],
        benchmark=port_cfg['backtest']['benchmark'],
        exchange_kwargs=port_cfg['backtest']['exchange_kwargs'],
    )

    # --- Calcular métricas del retorno ABSOLUTO ---
    # report_normal es dict {freq: (DataFrame, ...)}; el DataFrame tiene 'account' y 'bench'
    freq_key = list(report_normal.keys())[0]
    df_report = report_normal[freq_key][0]
    pv = df_report['account'].values
    bv = df_report['bench'].values

    port_ret = pd.Series(pv).pct_change().dropna().values
    bench_ret = pd.Series(bv).pct_change().dropna().values

    n_per_year = len(port_ret) / (len(pv) / 52)  # aproximado: ajustar según longitud
    if n_per_year < 40 or n_per_year > 300:
        n_per_year = 52

    mean_ann = float(np.mean(port_ret)) * n_per_year
    vol_ann = float(np.std(port_ret)) * np.sqrt(n_per_year)
    cum = np.cumprod(1 + port_ret)
    dd = cum / np.maximum.accumulate(cum) - 1
    max_dd = float(dd.min())
    sharpe = mean_ann / vol_ann if vol_ann else np.nan

    cum_b = np.cumprod(1 + bench_ret)
    dd_b = cum_b / np.maximum.accumulate(cum_b) - 1
    bench_dd = float(dd_b.min())

    excess = port_ret - bench_ret
    exc_ann = float(np.mean(excess)) * n_per_year
    exc_vol = float(np.std(excess)) * np.sqrt(n_per_year)
    ir = exc_ann / exc_vol if exc_vol else np.nan

    print(f"\n{'='*52}")
    print(f"📊 {tag}")
    print(f"{'='*52}")
    print(f"  Valor final: ${pv[-1]:,.0f} (inicial ${pv[0]:,.0f})")
    print(f"  Retorno anualizado ABSOLUTO: {mean_ann*100:+.2f}%")
    print(f"  Volatilidad anualizada:      {vol_ann*100:.2f}%")
    print(f"  ** Max drawdown ABSOLUTO:    {max_dd*100:.2f}% **")
    print(f"  Sharpe ABSOLUTO:             {sharpe:.3f}")
    print(f"  --- exceso vs benchmark ---")
    print(f"  Retorno anualizado exceso:   {exc_ann*100:+.2f}%")
    print(f"  Information Ratio:           {ir:.3f}")
    print(f"  Benchmark drawdown:          {bench_dd*100:.2f}%")
    return pv, bv


if __name__ == '__main__':
    print("### v4 (semanal, SIN vol-targeting) ###")
    pv4, _ = run_and_report('work/estrategias/tech_experiment_v4.yml', 'v4 (semanal, SIN vol-targeting)')
    print("\n### v5 (semanal, CON vol-targeting) ###")
    pv5, _ = run_and_report('work/estrategias/tech_experiment_v5.yml', 'v5 (semanal, CON vol-targeting)')

    print("\n\n" + "="*52)
    print("COMPARATIVA FINAL")
    print("="*52)
    print(f"  Valor final v4: ${pv4[-1]:,.0f}")
    print(f"  Valor final v5: ${pv5[-1]:,.0f}")
