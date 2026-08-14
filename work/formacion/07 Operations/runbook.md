# Runbook operativo

## Setup inicial

```bash
cd /home/trodriguez/.openclaw/workspace/qlib
./scripts/setup_venv.sh
source .venv/bin/activate
```

## Validaciones base

```bash
python scripts/check_qlib_setup.py
python scripts/validate_qlib_workflow.py
```

## Preparar dataset demo

```bash
./scripts/prepare_demo_dataset.sh
```

## Preparar pipeline baseline

```bash
python scripts/run_baseline_workflow.py --mode prepare
```

## Ejecutar baseline completo

```bash
python scripts/run_baseline_workflow.py --mode train
```

## Rutas y piezas clave

- dataset: `data/qlib/`
- runs locales: `mlruns/`
- baseline principal: `config/workflow_baseline_lightgbm_alpha158.yaml`
- notebook comparador: `notebooks/03_compare_runs.ipynb`

## Ciclo recomendado de experimentación

1. duplicar un workflow existente
2. cambiar una sola variable importante
3. ejecutar el run completo
4. comparar en el notebook
5. consolidar hallazgos en `docs/experimental-results.md`

## Regla práctica

Si una variante mejora `IC` pero empeora el portfolio neto, **no asumir mejora real**.

Primero revisar:

- concentración de cartera
- `topk` / `n_drop`
- drawdown
- coste total y retorno con costes
