"""Test de dirección: ¿las señales del modelo v2 predicen en la dirección correcta?

Método robusto sin backtest completo:
1. IC (information coefficient) = correlación predicción vs label real en test
2. Comparar retorno medio del decil mejor-puntado vs peor-puntado (long-short spread)
Si IC<0 o el mejor decil rinde MENOS que el peor, la señal está invertida.

NOTA: model.fit de Qlib toca MLflow → fijar MLFLOW_ALLOW_FILE_STORE=true.
"""
import os
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:////opt/data/qlib/work/qlib_work/mlflow.db"

import qlib
from qlib.utils import init_instance_by_config
from qlib.data.dataset import DatasetH
import yaml, numpy as np, pandas as pd

qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')

with open('work/estrategias/tech_experiment_v2.yml') as f:
    cfg = yaml.safe_load(f)

task_cfg = cfg['task']
dataset_cfg = task_cfg['dataset']
model_cfg = task_cfg['model']

print("Construyendo dataset (Alpha158)...")
dataset = init_instance_by_config(dataset_cfg)

print("Entrenando LightGBM...")
model = init_instance_by_config(model_cfg)
model.fit(dataset)

print("Generando predicciones y cargando labels de test...")
pred = model.predict(dataset, segment='test')
# En Qlib, col_set="label" ya devuelve el label directamente
label = dataset.prepare("test", col_set="label")

# Unir por (instrumento, fecha)
pred_df = pred.copy()
pred_df.name = 'pred'
label_df = label.copy()
# el label no siempre se llama 'label'; usar nombre real de la columna
if isinstance(label_df, pd.Series):
    label_df.name = 'label'
elif 'label' not in label_df.columns:
    label_df.columns = ['label']
df = pred_df.to_frame().join(label_df, how='inner')
df.dropna(inplace=True)
print(f"Muestras (instrumento x fecha) en test: {len(df)}")
print("Columnas:", list(df.columns))

# --- 1. IC global: correlación pred -> label ---
ic = df['pred'].corr(df['label'])
print(f"\n{'='*50}")
print(f"IC global (correlación pred→label): {ic:.4f}")
print(f"{'='*50}")

# --- 2. Long-short spread por deciles (mejor vs peor) ---
# Por cada fecha, rankear las predicciones y comparar retorno del top vs bottom
df['date'] = df.index.get_level_values(1)
df['rank_pct'] = df.groupby('date')['pred'].rank(pct=True)

top = df[df['rank_pct'] >= 0.9]   # mejor 10% predicho
bottom = df[df['rank_pct'] <= 0.1] # peor 10% predicho

ret_top = top['label'].mean()
ret_bottom = bottom['label'].mean()
spread = ret_top - ret_bottom

print(f"\nRetorno medio label (10d) del TOP 10% predicho:  {ret_top:+.5f} ({ret_top*100:+.2f}%)")
print(f"Retorno medio label (10d) del BOTTOM 10%:         {ret_bottom:+.5f} ({ret_bottom*100:+.2f}%)")
print(f"Long-Short spread (top - bottom):                 {spread:+.5f} ({spread*100:+.2f}%)")

print(f"\n{'='*50}")
print("DIAGNÓSTICO:")
if ic < -0.01 or spread < -0.001:
    print("❌ SEÑAL INVERTIDA: las 'mejores' predicciones rinden peor que las 'peores'. \n   Multiplica la señal por -1 (o selecciona el bottom en vez del top) para corregir.")
elif abs(ic) < 0.02 and abs(spread) < 0.005:
    print("⚠️  SIN ALPHA CLARO: IC ~0 y spread ~0 → el modelo no distingue buenas de malas.\n   El problema NO es dirección, es que no hay señal predictiva útil.")
else:
    print("✅ Señal en DIRECCIÓN CORRECTA (IC positivo). El problema es de intensidad/fuerza,\n   no de dirección.")
print(f"{'='*50}")
