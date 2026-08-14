"""Walk-Forward validation del experimento v5 (tech_giants + vol-targeting).

Barre varias ventanas temporales: entrena SOLO con datos pasados y predice el
siguiente periodo out-of-sample (OOS), luego avanza. Cada predicción OOS se
concatena, y se mide rendimiento agregado (IC, long-short spread). Si el alpha
se sostiene OOS, no era overfitting.
"""
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:////opt/data/qlib/work/qlib_work/mlflow.db"

import numpy as np
import pandas as pd
import yaml

import qlib
from qlib.utils import init_instance_by_config
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

# ------- Parámetros walk-forward -------
INSTRUMENTS = "tech_giants_universe"
TRAIN_YEARS = 4     # ventana de entrenamiento (años)
TEST_YEARS = 1      # periodo OOS a predecir por ventana
START = "2019-01-01"
END = "2026-08-01"
LABEL = ["Ref($close, -11) / Ref($close, -1) - 1"]

with open('work/estrategias/tech_experiment_v5.yml') as f:
    cfg = yaml.safe_load(f)
MODEL_KWARGS = cfg['task']['model']['kwargs']


def make_ds(train_start, train_end, valid_start, valid_end, test_start, test_end):
    handler_cfg = dict(cfg['task']['dataset']['kwargs']['handler']['kwargs'])
    handler_cfg['instruments'] = INSTRUMENTS
    handler_cfg['start_time'] = START
    handler_cfg['end_time'] = test_end
    handler_cfg['fit_start_time'] = train_start
    handler_cfg['fit_end_time'] = train_end
    handler_cfg['label'] = LABEL
    from qlib.contrib.data.handler import Alpha158
    handler = Alpha158(**handler_cfg)
    from qlib.data.dataset import DatasetH
    ds = DatasetH(handler, segments={
        "train": (train_start, train_end),
        "valid": (valid_start, valid_end),
        "test": (test_start, test_end),
    })
    return ds


def run():
    from qlib.data import D
    start_ts = pd.Timestamp(START)
    end_ts = pd.Timestamp(END)

    # Cortes de test cada TEST_YEARS años
    cuts = []
    t = start_ts + pd.Timedelta(days=TRAIN_YEARS*365)
    while t <= end_ts:
        cuts.append(t)
        t += pd.Timedelta(days=TEST_YEARS*365)
    if cuts[-1] < end_ts:
        cuts.append(end_ts)
    print(f"Ventanas propuestas (finales de test): {[c.date() for c in cuts]}")

    all_pred = []
    all_label = []

    for i, test_end in enumerate(cuts):
        # Entrenar ventana: de start_ts a test_end - TEST_YEARS, valid los últimos meses previos al test
        test_start = cuts[i-1] if i >= 1 else start_ts + pd.Timedelta(days=TRAIN_YEARS*365)
        # test_start debe ser el fin de la ventana anterior = corte anterior
        test_start = cuts[i-1] if i >= 1 else start_ts + pd.Timedelta(days=(TRAIN_YEARS-1)*365)
        train_end = test_start - pd.Timedelta(days=1)
        valid_start = train_end - pd.Timedelta(days=180)  # ~6 meses
        if valid_start < start_ts:
            valid_start = start_ts

        ts = test_start.date().isoformat()
        te = test_end.date().isoformat()
        print(f"\n=== Ventana {i+1}: test [{ts} → {te}] ===")
        print(f"    train [{START} → {train_end.date()}] | valid [{valid_start.date()} → {train_end.date()}]")

        try:
            ds = make_ds(START, train_end.date().isoformat(),
                         valid_start.date().isoformat(), train_end.date().isoformat(),
                         ts, te)
            model = init_instance_by_config({'class':'LGBModel','module_path':'qlib.contrib.model.gbdt','kwargs':MODEL_KWARGS})
            model.fit(ds)
            pred = model.predict(ds, segment='test')
            label = ds.prepare('test', col_set='label')
            label = pd.DataFrame(label)
            label.columns = ['label']
            merged = pd.DataFrame(pred).join(label, how='inner').dropna()
            ic = merged.iloc[:,0].corr(merged['label'])
            print(f"  Predicciones OOS: {len(merged)} | IC: {ic:.4f}")
            all_pred.append(merged)
        except Exception as e:
            print(f"  ERROR ventana {i+1}: {e}")

    if all_pred:
        full = pd.concat(all_pred)
        full.columns = ['pred', 'label']
        ic_all = full['pred'].corr(full['label'])
        full['date'] = full.index.get_level_values(1)
        full['rank'] = full.groupby('date')['pred'].rank(pct=True)
        top = full[full['rank'] >= 0.8]['label'].mean()
        bot = full[full['rank'] <= 0.2]['label'].mean()

        print("\n" + "="*52)
        print("RESULTADOS WALK-FORWARD (out-of-sample)")
        print("="*52)
        print(f"  Total muestras OOS: {len(full)}")
        print(f"  ** IC agregado OOS: {ic_all:.4f} **")
        print(f"  Retorno label TOP 20%: {top*100:+.2f}% (10d)")
        print(f"  Retorno label BOT 20%: {bot*100:+.2f}% (10d)")
        print(f"  Long-Short spread:    {(top-bot)*100:+.2f}% (10d)")
        if ic_all > 0.02:
            print("\n  ✅ Alpha se sostiene out-of-sample (IC>0). El resultado NO es mero overfitting.")
        elif ic_all > 0:
            print("\n  ⚠️  Alpha positivo pero débil OOS. El +24% de v5 está inflado por overfitting parcial.")
        else:
            print("\n  ❌ Sin alpha out-of-sample. El +24% era principalmente overfitting.")


if __name__ == '__main__':
    run()
