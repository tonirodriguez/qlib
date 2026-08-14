# Cómo ejecutar un experimento en qlib

## Comando básico

```bash
cd qlib
source .venv/bin/activate
```

### Validar datos (pre-check)
```bash
python scripts/run_baseline_workflow.py \
  --config config/workflow_baseline_lightgbm_alpha158.yaml \
  --mode prepare
```

### Entrenar ciclo completo
```bash
python scripts/run_baseline_workflow.py \
  --config config/workflow_baseline_lightgbm_alpha158.yaml \
  --mode train
```

Puedes cambiar el `--config` por cualquiera de los disponibles en `config/`.

---

## Diferencia entre `prepare` y `train`

| Paso | `prepare` | `train` |
|---|---|---|
| Cargar dataset (train/valid/test) | ✅ | ✅ |
| Mostrar dimensiones y preview | ✅ | ✅ |
| Validar que los datos existen | ✅ | ✅ |
| Entrenar modelo LightGBM | ❌ | ✅ |
| Generar señales (predicciones) | ❌ | ✅ |
| Backtest de portfolio | ❌ | ✅ |
| Calcular métricas (retorno, IR, drawdown) | ❌ | ✅ |
| Guardar run en `mlruns/` | ❌ | ✅ |
| Regenerar wiki automáticamente | ❌ | ✅ |
| Crear snapshot git | ❌ | ✅ |

- **`prepare`**: solo comprueba que el dataset se carga bien. Útil para confirmar que los datos están operativos antes de invertir tiempo en entrenar.
- **`train`**: ejecuta el ciclo completo: entrena, predice, backtestea, guarda resultados en `mlruns/`, regenera la wiki y crea un tag de git.

---

## Configs disponibles

| Config | Universo | Notas |
|---|---|---|
| `workflow_baseline_lightgbm_alpha158.yaml` | CSI300 | Baseline principal |
| `workflow_baseline_lightgbm_alpha158_csi300_label5d.yaml` | CSI300 | Label a 5 días |
| `workflow_baseline_lightgbm_alpha158_csi500.yaml` | CSI500 | Universo más amplio |
| `workflow_baseline_lightgbm_alpha158_csi300_tuned.yaml` | CSI300 | LightGBM tuneado |
| `workflow_baseline_lightgbm_alpha158_csi300_tuned_top20.yaml` | CSI300 | Top20 |
| `workflow_baseline_lightgbm_alpha158_csi300_tuned_top30.yaml` | CSI300 | Top30 |
| `workflow_baseline_lightgbm_alpha158_csi300_tuned_softtopk20.yaml` | CSI300 | Soft topk |
| `workflow_baseline_lightgbm_alpha158_sp500_us.yaml` | SP500 (US) | Mercado americano |
| `workflow_baseline_lightgbm_alpha158_sp500_us_label5d.yaml` | SP500 (US) | Label a 5 días |

---

## Provider URI

El `provider_uri` se define dentro de cada config YAML:

```yaml
qlib_init:
  provider_uri: ~/.qlib/qlib_data/us_data   # para US
  provider_uri: data/qlib                    # para CN
  region: us  # o cn
```

El script resuelve la ruta automáticamente:
- `~/.qlib/qlib_data/us_data` → expande el home del usuario y usa ruta absoluta
- `data/qlib` → resuelve relativo a la raíz del proyecto

---

## Tras entrenar

Cuando termina `--mode train`:

1. Los resultados quedan en `mlruns/` (accesibles por experimento y run ID)
2. La wiki se regenera automáticamente (dashboard, baselines, runs-index, project-state)
3. La wiki se valida (links rotos)
4. Se crea un tag de git: `wiki-snapshot-YYYYMMDDTHHMMSS`

Para ver los resultados en la wiki:

```bash
bash scripts/serve_llm_wiki.sh
# Abrir http://localhost:8016/
```

---

## Notas

- Los experimentos anteriores **no se borran**: cada run se acumula en `mlruns/`.
- La wiki muestra todos los runs ordenados por ranking compuesto.
- Si quieres empezar de cero, puedes limpiar `mlruns/`.
