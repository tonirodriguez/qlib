# Ejecución Prioridad 1 — SP500 US Baseline

> **Objetivo:** ejecutar el baseline LightGBM + alpha158 sobre el mercado USA (S&P 500).
> **Tarea:** #6 del `ROADMAP TRABAJO.md` (pendiente desde agosto 2026).
> **Creado:** 30 Junio 2026 · **Reescrito:** 26 Octubre 2026 (las rutas anteriores no existían)
> **Config:** `work/auto_trading_system/conf/workflow_baseline_lightgbm_alpha158_sp500_us.yaml`

---

## ⚠️ Corrección respecto a la versión anterior

Esta guía apuntaba a rutas que **no existen en el repositorio**:

| Referencia antigua | Estado real (verificado 2026-10-26) |
|---|---|
| `config/workflow_baseline_..._sp500_us.yaml` | ❌ no existe `config/` |
| `scripts/run_baseline_workflow.py` | ❌ no existe |
| `qlib/.venv/` | ❌ no existe |
| `vendor/microsoft-qlib/` | ❌ no existe |

La config **se ha creado de nuevo** en `work/auto_trading_system/conf/`,
partiendo de la plantilla oficial `examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml`
y adaptándola a los datos realmente disponibles. Se ejecuta con `qrun` estándar,
sin scripts intermedios.

---

## 📋 Configuración

| Parámetro | Valor | Nota |
|-----------|:-----:|------|
| **Modelo** | LightGBM (LGBModel) | |
| **Features** | alpha158 | 158 factores técnicos |
| **Universo** | `sp500` | **1.180 tickers** con composición histórica |
| **Benchmark** | `^GSPC` | Verificado presente en `features/` |
| **Train** | 2008-01-01 → 2018-12-31 | |
| **Valid** | 2019-01-01 → 2021-12-31 | Incluye COVID-19 |
| **Test** | 2022-01-01 → 2026-10-16 | Incluye el bear de 2022. Ver nota de `end_time` |
| **Estrategia** | TopkDropoutStrategy | topk=30, n_drop=3 |
| **Costes** | 0.05% open / 0.10% close | min $5 |
| **Cuenta inicial** | $100,000 | |

### Hyperparams del modelo

`learning_rate 0.0421` · `max_depth 8` · `num_leaves 210` ·
`colsample_bytree 0.8879` · `subsample 0.8789` · `lambda_l1 205.6999` ·
`lambda_l2 580.9768` · `early_stopping_rounds 50` · `num_threads 8`

---

## 🚀 Ejecución

### Paso 1 — Verificar prerrequisitos (30 segundos)

```bash
cd /mnt/c/Users/trodriguez/src/qlib
conda run -n qlib python work/auto_trading_system/verificar_sp500_baseline.py
```

Comprueba que qlib importa, que los datos están en su sitio, que `sp500.txt` y
`^gspc` existen, que lightgbm/mlflow están instalados, y que las fechas de la
config no se salen del calendario. **No entrena nada.**

### Paso 2 — Ejecutar el baseline

```bash
conda run -n qlib qrun work/auto_trading_system/conf/workflow_baseline_lightgbm_alpha158_sp500_us.yaml
```

**Duración estimada:** 10–30 min (Alpha158 sobre ~1.180 tickers × 18 años).

---

## 📊 Salida esperada

Al terminar, `qrun` imprime:

1. **Métricas de señal:** IC, Rank IC, ICIR, Rank ICIR
2. **Métricas de portfolio:** annualized return, std, Sharpe, max drawdown, turnover
3. **ID del experimento** para MLflow

El experimento se registra en `./mlruns` (MLflow local).

Para consultarlo:

```bash
cd /mnt/c/Users/trodriguez/src/qlib
mlflow ui --backend-store-uri ./mlruns
# abrir http://localhost:5000
```

O por consola:

```bash
conda run -n qlib python -c "
import qlib
from qlib.workflow import R
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')
exp = R.get_exp(experiment_name='workflow')
for rec in exp.list_recorders().values():
    m = rec.list_metrics()
    print(rec.id, {k: round(v,4) for k,v in m.items() if k in ('IC','Rank IC','1day.excess_return_with_cost.annualized_return','1day.excess_return_with_cost.max_drawdown')})
"
```

---

## ✅ Criterio de éxito

Se considerará un baseline **válido** si:

| Criterio | Umbral | Razón |
|---|---|---|
| Rank IC | > 0.02 | Por debajo, la señal no tiene poder predictivo |
| Sharpe | > 0.5 | Un baseline debe batir a cash con holgura |
| Turnover | < 100%/día | Por encima, los costes se comen el retorno |

**Comparación de referencia (mercado chino, mismo modelo):**

| Mercado | Ann Return | Rank IC |
|---|---|---|
| CSI300 (baseline, top50) | 14.73% | 0.0487 |
| CSI500 (baseline, top50) | 13.33% | 0.0459 |
| **SP500 (este experimento)** | ? | ? |

El mercado US es más eficiente que el chino, así que **es razonable esperar un
IC menor**. Un resultado de 0.02–0.04 sería normal, no un fracaso.

---

## 🔧 Notas técnicas

### Sobre `limit_threshold: 0.095`

Se mantiene el valor de la plantilla china, pero **en US no existe el límite
diario del ±10%** que sí hay en China. Qlib lo usa para excluir días con saltos
anómalos al calcular si una orden se habría ejecutado.

**Implicación:** con 0.095 se están excluyendo movimientos >9.5%, que en US
ocurren de verdad (earnings, gaps). Esto puede hacer el backtest **ligeramente
conservador**. Si el resultado sorprende, probar con `limit_threshold: null`
(desactivado) para comparar.

### Sobre `sp500.txt` con 1.180 tickers

El S&P 500 tiene ~500 miembros, pero el archivo lista 1.180. Son los tickers que
**han pertenecido** al índice en algún momento del histórico — está bien así:

- ✅ **Evita el sesgo de supervivencia**: incluye empresas que quebraron o
  salieron del índice.
- ⚠️ **Más lento**: Alpha158 se calcula sobre 1.180 instrumentos.
- ⚠️ **Ruido**: incluye tickers con poca liquidez en ciertos periodos.

Si el tiempo de ejecución es un problema, se puede crear un subconjunto, pero
**no antes de tener el baseline completo** como referencia.

### Sobre `end_time` y el `IndexError` (corregido 2026-10-26)

Si `end_time` coincide con la **última fecha del calendario**, qlib falla con:

```
IndexError: index 6744 is out of bounds for axis 0 with size 6744
```

**Causa:** `qlib/backtest/utils.py:131` hace `_calendar[calendar_index + 1]` para
cerrar el último intervalo de trading. Si `end_time` es el último día, ese `+1`
se sale del array.

**Solución aplicada:** `END_DATE = 2026-10-16`, con **7 días de margen** sobre el
fin del calendario (`2026-10-23`). Está definido como ancla YAML y usado en los
3 sitios (`data_handler_config`, `backtest`, `segments.test`), así que **solo hay
que cambiar una línea** al actualizar datos.

```yaml
END_DATE: &end_date "2026-10-16"   # <-- unico sitio a tocar
```

**Si actualizas los datos**, mueve `END_DATE` a ~1 semana antes de la nueva
última fecha del calendario:

```bash
tail -1 ~/.qlib/qlib_data/us_data/calendars/day.txt   # nueva ultima fecha
```

El verificador comprueba este margen automáticamente y avisa con el arreglo.

> **Nota YAML:** el alias no puede ir dentro de una lista de flujo
> (`test: [2022-01-01, *end_date]` es **inválido**). Por eso `segments.test` usa
> lista en bloque. El verificador también detecta este caso.

### Ubicación del repo

Se ejecuta desde `/mnt/c/...` (unidad C de Windows vista desde WSL). Funciona,
pero el I/O es lento. Si el entrenamiento tarda demasiado, copiar el repo a
`~/src/qlib` dentro de WSL acelera notablemente la lectura de datos.

---

## 🔗 Enlaces relacionados

- **Config:** `work/auto_trading_system/conf/workflow_baseline_lightgbm_alpha158_sp500_us.yaml`
- **Verificador:** `work/auto_trading_system/verificar_sp500_baseline.py`
- **Inspección de datos:** `work/estrategias/inspeccionar_qlib_data.py`
- **Roadmap general:** `04 Experiments/ROADMAP TRABAJO.md`
- **Roadmap US:** `04 Experiments/us-market-roadmap.md`

---

*Documento generado: 30 Junio 2026*
*Reescrito: 26 Octubre 2026 — rutas corregidas, config creada, verificación añadida*
*Próximo paso tras ejecución: analizar resultados y comparar con CSI300*
