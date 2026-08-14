# Estrategia Qlib 6: AutoGluon 1

## Validación de los Datos y Alpha154 - Alpha360

> Eres un analista financiero quantitativo. Ayudame a configurar qlib con autogluon para crear un modelo para el mercado US. ¿como lo debo de hacer? ¿qué pasos he de seguir? ¿que factores debo de considerar?¿hay algún conjunto de factores preelaborados en qlib que pueda utilizar?
> 

Sí. La forma más limpia es usar **Qlib como capa de datos, workflow, backtest y evaluación**, y **AutoGluon Tabular como modelo supervisado custom** dentro de Qlib. Qlib trae el flujo completo de datos, entrenamiento, señal, backtest y análisis, y su herramienta `qrun` ejecuta el workflow completo desde un YAML. AutoGluon, por su parte, encaja bien porque `TabularPredictor` entrena modelos de regresión/clasificación sobre una tabla con una columna objetivo. ([PyPI](https://pypi.org/project/pyqlib/))

## 1. Arquitectura recomendada

Para mercado US, montaría esto así:

```
OHLCV US / Yahoo / vendor propio
        ↓
Qlib format: ~/.qlib/qlib_data/us_data
        ↓
Qlib DataHandler: Alpha158 o Alpha360
        ↓
DatasetH: train / valid / test cronológicos
        ↓
AutoGluonQlibModel custom
        ↓
SignalRecord + SigAnaRecord + PortAnaRecord
        ↓
IC, Rank IC, long-short, top-k portfolio, drawdown, costes
```

La idea importante es que **AutoGluon no sustituye a Qlib**; sustituye al modelo tipo LightGBM/MLP dentro del workflow de Qlib.

---

## 2. Entorno e instalación

Usaría Python 3.10 o 3.11 para evitar conflictos. Qlib declara soporte moderno desde Python 3.8 hasta 3.12 en PyPI, y AutoGluon declara soporte Python 3.10-3.13; Python 3.10/3.11 queda en la intersección cómoda. ([PyPI](https://pypi.org/project/pyqlib/))

```bash
conda create -n qlib-ag python=3.11 -y
conda activate qlib-ag

git clone https://github.com/microsoft/qlib.git
cd qlib

pip install -U pip
pip install -e .
pip install autogluon
```

También puedes instalar Qlib estable con:

```bash
pip install pyqlib
```

pero para datos, ejemplos y collectors suele ser más cómodo trabajar desde el repo clonado. ([PyPI](https://pypi.org/project/pyqlib/))

---

## 3. Preparar datos US

Primero prueba el dataset prehecho de Qlib:

```bash
python scripts/get_data.py qlib_data \
  --target_dir ~/.qlib/qlib_data/us_data \
  --region us \
  --interval 1d
```

Aquí hay una advertencia práctica: la documentación de Qlib no es totalmente consistente. La página de datos dice que Qlib incluye datasets off-the-shelf Alpha360 y Alpha158 para US y muestra el comando `--region us`; otra página de inicialización advierte que `get_data.py` puede proporcionar solo China y que para US quizá debas preparar tus propios datos. Por eso conviene probar el comando y, si no te sirve o no está actualizado, generar tu propio `us_data` desde Yahoo o un vendor. ([GitHub](https://raw.githubusercontent.com/microsoft/qlib/main/docs/component/data.rst))

Si quieres construirlo desde Yahoo Finance:

```bash
# 1) Descargar CSVs diarios US
python scripts/data_collector/yahoo/collector.py download_data \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --start 2000-01-01 \
  --end 2026-04-29 \
  --delay 1 \
  --interval 1d \
  --region US

# 2) Normalizar precios
python scripts/data_collector/yahoo/collector.py normalize_data \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --normalize_dir ~/.qlib/stock_data/source/us_1d_nor \
  --region US \
  --interval 1d

# 3) Convertir a formato Qlib
python scripts/dump_bin.py dump_all \
  --data_path ~/.qlib/stock_data/source/us_1d_nor \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --freq day \
  --exclude_fields date,symbol \
  --file_suffix .csv
```

Qlib avisa expresamente de que los datos Yahoo pueden no ser perfectos y recomienda usar datasets propios de alta calidad si los tienes. Para producción, usaría Norgate, CRSP/Compustat, Polygon, Tiingo, Refinitiv, FactSet o tu vendor interno, no Yahoo sin validación. ([GitHub](https://raw.githubusercontent.com/microsoft/qlib/main/scripts/data_collector/yahoo/README.md))

Para universo US, puedes crear listas de instrumentos tipo S&P 500, Nasdaq 100, DJIA o S&P 400 con el collector de índices:

```bash
cd scripts/data_collector/us_index

python collector.py \
  --index_name SP500 \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --method parse_instruments
```

El collector oficial lista soporte para `SP500`, `NASDAQ100`, `DJIA` y `SP400`. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/us_index/README.md))

---

## 4. Inicializar Qlib en modo US

En Python:

```python
import qlib
from qlib.constant import REG_US

qlib.init(
    provider_uri="~/.qlib/qlib_data/us_data",
    region=REG_US,
)
```

El modo `REG_US` cambia parámetros regionales como unidad mínima de trading y límites de precio; en la configuración base de Qlib, US usa `trade_unit=1` y `limit_threshold=None`, a diferencia de China. ([GitHub](https://raw.githubusercontent.com/microsoft/qlib/main/docs/start/initialization.rst))

---

## 5. Modelo custom: AutoGluon dentro de Qlib

Qlib permite integrar modelos custom heredando de `qlib.model.base.Model`, implementando `fit` y `predict`, y apuntando al modelo desde el campo `model` del YAML. Esa es justo la vía adecuada para AutoGluon. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/start/integration.rst))

Crea un archivo, por ejemplo:

```
my_models/autogluon_qlib_model.py
```

con este contenido:

```python
from pathlib import Path

import numpy as np
import pandas as pd
from autogluon.tabular import TabularPredictor

from qlib.model.base import Model
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP

class AutoGluonQlibModel(Model):
    """
    Wrapper Qlib -> AutoGluon Tabular.

    Cada fila es un par (instrument, datetime).
    Las columnas son factores de Qlib.
    La etiqueta es el retorno futuro definido por el DataHandler.
    """

    # Evita picklear todos los modelos internos de AutoGluon dentro del objeto Qlib.
    # AutoGluon ya guarda sus modelos en predictor_path.
    exclude_attr = ["predictor"]

    def __init__(
        self,
        label="LABEL0",
        problem_type="regression",
        eval_metric="root_mean_squared_error",
        path="./ag_models/qlib_autogluon",
        presets="medium_quality",
        time_limit=3600,
        num_cpus="auto",
        num_gpus=0,
        hyperparameters=None,
        verbosity=2,
        **fit_kwargs,
    ):
        self.label = label
        self.problem_type = problem_type
        self.eval_metric = eval_metric
        self.predictor_path = str(Path(path).expanduser())
        self.presets = presets
        self.time_limit = time_limit
        self.num_cpus = num_cpus
        self.num_gpus = num_gpus
        self.hyperparameters = hyperparameters
        self.verbosity = verbosity
        self.fit_kwargs = fit_kwargs
        self.predictor = None

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["__".join(map(str, c)).strip("_") for c in df.columns]
        else:
            df.columns = [str(c) for c in df.columns]
        return df

    def _to_autogluon_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        x = self._flatten_columns(df["feature"])
        y = df["label"]

        if isinstance(y, pd.DataFrame):
            if y.shape[1] != 1:
                raise ValueError("Este wrapper espera una sola etiqueta.")
            y = y.iloc[:, 0]

        out = x.copy()
        out[self.label] = y.astype(float).to_numpy()
        out = out.replace([np.inf, -np.inf], np.nan)

        # La etiqueta no puede faltar. Las features con NaN puede tratarlas AutoGluon.
        out = out.dropna(subset=[self.label])
        return out

    def _load_predictor_if_needed(self):
        if self.predictor is None:
            self.predictor = TabularPredictor.load(self.predictor_path)
        return self.predictor

    def fit(self, dataset: DatasetH, reweighter=None):
        df_train, df_valid = dataset.prepare(
            ["train", "valid"],
            col_set=["feature", "label"],
            data_key=DataHandlerLP.DK_L,
        )

        train_data = self._to_autogluon_frame(df_train)
        valid_data = self._to_autogluon_frame(df_valid)

        self.predictor = TabularPredictor(
            label=self.label,
            problem_type=self.problem_type,
            eval_metric=self.eval_metric,
            path=self.predictor_path,
            verbosity=self.verbosity,
        )

        self.predictor.fit(
            train_data=train_data,
            tuning_data=valid_data,
            presets=self.presets,
            time_limit=self.time_limit,
            num_cpus=self.num_cpus,
            num_gpus=self.num_gpus,
            hyperparameters=self.hyperparameters,
            **self.fit_kwargs,
        )

        return self

    def predict(self, dataset: DatasetH, segment="test"):
        predictor = self._load_predictor_if_needed()

        x = dataset.prepare(
            segment,
            col_set="feature",
            data_key=DataHandlerLP.DK_I,
        )

        x = self._flatten_columns(x)
        x = x.replace([np.inf, -np.inf], np.nan)

        pred = predictor.predict(x)
        return pd.Series(pred.to_numpy(), index=x.index, name="score")
```

He puesto `presets="medium_quality"` a propósito para empezar: evita parte de la complejidad de bagging/stacking y es más fácil de depurar. AutoGluon permite presets como `medium_quality`, `good_quality`, `high_quality` y `best_quality`, pero en finanzas conviene no empezar con el preset más agresivo porque puede mezclar validaciones internas de forma poco alineada con splits temporales. La propia documentación de AutoGluon advierte que `tuning_data` se usa para early stopping, selección y ensembling, y que no debe confundirse con un test realmente no visto. ([AutoGluon](https://auto.gluon.ai/stable/api/autogluon.tabular.TabularPredictor.fit.html))

---

## 6. YAML de Qlib para US + Alpha158 + AutoGluon

Crea, por ejemplo:

```
examples/benchmarks/AutoGluon/workflow_config_autogluon_Alpha158_us.yaml
```

```yaml
qlib_init:
  provider_uri: "~/.qlib/qlib_data/us_data"
  region: us

market: &market sp500
benchmark: &benchmark SPY

data_handler_config: &data_handler_config
  start_time: 2008-01-01
  end_time: 2025-12-31
  fit_start_time: 2008-01-01
  fit_end_time: 2017-12-31
  instruments: *market

port_analysis_config: &port_analysis_config
  strategy:
    class: TopkDropoutStrategy
    module_path: qlib.contrib.strategy
    kwargs:
      signal: <PRED>
      topk: 50
      n_drop: 5

  backtest:
    start_time: 2021-01-01
    end_time: 2025-12-31
    account: 100000000
    benchmark: *benchmark
    exchange_kwargs:
      limit_threshold:
      deal_price: close
      open_cost: 0.0002
      close_cost: 0.0002
      min_cost: 1

task:
  model:
    class: AutoGluonQlibModel
    module_path: my_models.autogluon_qlib_model
    kwargs:
      label: LABEL0
      problem_type: regression
      eval_metric: root_mean_squared_error
      path: "./ag_models/us_alpha158"
      presets: medium_quality
      time_limit: 7200
      num_cpus: 16
      num_gpus: 0
      hyperparameters:
        GBM: {}
        CAT: {}
        XGB: {}
        RF: {}
        XT: {}

  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: Alpha158
        module_path: qlib.contrib.data.handler
        kwargs: *data_handler_config

      segments:
        train: [2008-01-01, 2017-12-31]
        valid: [2018-01-01, 2020-12-31]
        test:  [2021-01-01, 2025-12-31]

  record:
    - class: SignalRecord
      module_path: qlib.workflow.record_temp
      kwargs:
        model: <MODEL>
        dataset: <DATASET>

    - class: SigAnaRecord
      module_path: qlib.workflow.record_temp
      kwargs:
        ana_long_short: False
        ann_scaler: 252

    - class: PortAnaRecord
      module_path: qlib.workflow.record_temp
      kwargs:
        config: *port_analysis_config
```

Ajusta `benchmark` según el símbolo que realmente exista en tu `us_data`. Puede ser `SPY`, `^GSPC` u otro benchmark que hayas cargado. Qlib no inventa el benchmark: debe estar en tu provider o tendrás errores de datos faltantes.

Ejecuta:

```bash
qrun examples/benchmarks/AutoGluon/workflow_config_autogluon_Alpha158_us.yaml
```

---

## 7. ¿Alpha158 o Alpha360?

Sí, Qlib trae conjuntos preelaborados. Los principales son:

| Dataset | Qué contiene | Cuándo usarlo |
| --- | --- | --- |
| `Alpha158` | Factores técnicos/cross-sectional sobre OHLCV: velas, precios normalizados, medias, volatilidad, momentum, ranks, correlaciones precio-volumen, etc. | Primera baseline tabular. Muy adecuado para AutoGluon, LightGBM, CatBoost, XGBoost. |
| `Alpha360` | Ventana de 60 días de OHLCV/VWAP/volumen normalizados, 360 features. | Más útil para modelos que explotan secuencia o historia cruda; también funciona con AutoGluon, pero puede ser más pesado. |

La documentación de Qlib lista `Alpha360` y `Alpha158` como datasets disponibles para US y China. En el código, `Alpha360` se construye con precios y volumen de los últimos 60 días normalizados por el precio/volumen más reciente; `Alpha158` genera familias de factores técnicos sobre OHLCV, rolling windows y operadores como ROC, MA, STD, slope, rank, cuantiles y correlaciones. ([GitHub](https://raw.githubusercontent.com/microsoft/qlib/main/docs/component/data.rst))

Para empezar con AutoGluon, usaría **Alpha158**. Después probaría Alpha360 y un set propio enriquecido.

---

## 8. Factores que deberías considerar

**1. Evitar leakage temporal.**

No mezcles fechas futuras en entrenamiento ni uses splits aleatorios. Usa siempre cortes cronológicos: train → valid → test. AutoGluon puede hacer validaciones internas; por eso recomiendo empezar con `medium_quality`, pasar explícitamente `tuning_data=valid` y dejar el periodo test completamente fuera.

**2. Survivorship bias del universo.**

Si usas “los miembros actuales del S&P 500” hacia atrás en el tiempo, el backtest estará sesgado. Usa constituyentes point-in-time cuando puedas. El collector de índices de Qlib ayuda a crear instrumentos históricos, pero aun así valida altas, bajas, mergers y cambios de ticker. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/us_index/README.md))

**3. Calidad de datos y corporate actions.**

Qlib usa precios ajustados; la documentación indica que los precios pueden diferir de los precios reales por ajustes, y que `$factor` permite recuperar precios originales como `$close / $factor`. Esto importa mucho para slippage, costes, stops y ejecución. ([GitHub](https://raw.githubusercontent.com/microsoft/qlib/main/docs/component/data.rst))

**4. Definición de label.**

El label por defecto en los handlers suele ser retorno futuro tipo:

```
Ref($close, -2) / Ref($close, -1) - 1
```

Eso no es accidental: intenta alinear predicción y ejecución evitando usar un precio que no podrías conocer al operar. Si vas a operar a apertura, cierre, VWAP o con delay, redefine el label.

**5. Métrica de entrenamiento vs métrica económica.**

AutoGluon optimiza métricas supervisadas como RMSE, MAE, R², etc. Qlib luego evalúa IC, Rank IC, long-short return y backtest. En alphas cross-sectionales, muchas veces te importa más el **ranking** que el error absoluto. Una evolución avanzada sería crear una métrica custom tipo Spearman/IC para AutoGluon, pero primero validaría con RMSE y luego miraría Rank IC en Qlib.

**6. Costes realistas.**

No uses los costes de los ejemplos China. Para US configura comisiones, spread, slippage, borrow si hay shorts, impacto de mercado y limitaciones de liquidez. En Qlib US, `limit_threshold` debería ser `null` o no imponerse como límite diario tipo China. ([GitHub](https://raw.githubusercontent.com/microsoft/qlib/main/qlib/config.py))

**7. Liquidez y tradability.**

Filtra por dollar volume, precio mínimo, ADV, días con volumen cero, acciones ilíquidas, ADRs si no los quieres, ETFs si no los quieres, y eventos corporativos raros.

**8. No estacionariedad.**

El mercado cambia. Qlib tiene componentes para rolling retraining y adaptación a dinámicas de mercado; para US, yo haría walk-forward: entrenar 2008-2017, validar 2018-2020, test 2021-2022; luego reentrenar y test 2023; etc. ([GitHub](https://github.com/microsoft/qlib))

**9. Capacidad y turnover.**

Un buen IC con turnover extremo puede no sobrevivir costes. Analiza turnover, holding period, decay de la señal, capacidad por ADV y sensibilidad a `topk`/`n_drop`.

**10. Comparar contra baselines.**

Antes de AutoGluon, corre LightGBM con el YAML oficial adaptado a US. Si AutoGluon no bate LightGBM en Rank IC o retorno neto, no lo compliques.

---

## 9. Configuración inicial que usaría

Para un primer experimento serio:

```
Datos:          US daily, 2008-2025
Universo:       sp500 point-in-time si es posible
Benchmark:      SPY o ^GSPC en provider_uri
Features:       Alpha158
Modelo:         AutoGluon Tabular, regression
Preset:         medium_quality
Train:          2008-2017
Valid:          2018-2020
Test:           2021-2025
Strategy:       TopKDropout, topk=50, n_drop=5
Costes:         2-10 bps por lado, según tu hipótesis
Métricas:       IC, Rank IC, ICIR, long-short, Sharpe/IR, MDD, turnover
```

Después probaría estas variantes:

```
A) Alpha158 + AutoGluon medium_quality
B) Alpha158 + AutoGluon good_quality
C) Alpha360 + AutoGluon medium_quality
D) Alpha158 + LightGBM Qlib baseline
E) Alpha158 + factores propios: liquidez, beta, sector, earnings, fundamentals
```

Mi recomendación práctica: **empieza con Alpha158 + AutoGluon `medium_quality` + validación cronológica**, confirma que el pipeline Qlib funciona de punta a punta, y solo después aumenta complejidad con `good_quality`, Alpha360, rolling retraining y factores propios.

> Veo que con Alpha158 debo de usar autogluon en modo tabular, con Alpha360 también o he de irme a time series?
> 

Para tu caso, **usaría AutoGluon en modo tabular tanto con `Alpha158` como con `Alpha360`**.

`Alpha360` suena “time series”, pero en Qlib no te llega como una serie temporal nativa para AutoGluon, sino como una fila por par:

```
(datetime, instrument) -> 360 columnas de features -> LABEL0
```

Qlib está planteando el problema como **predicción cross-sectional diaria de retornos futuros / scores por acción**, no como forecasting clásico de una serie por ticker. La propia descripción de los benchmarks de Qlib habla de modelos que generan predicciones para todas las acciones cada día y luego usan esos scores como alpha para construir carteras. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md))

## Decisión práctica

| Caso | AutoGluon recomendado | Motivo |
| --- | --- | --- |
| `Alpha158` + Qlib | `TabularPredictor` | Factores técnicos ya agregados por fecha/activo. |
| `Alpha360` + Qlib | `TabularPredictor` | Ventana de 60 días, pero aplanada en 360 columnas. |
| Forecasting de precio/retorno por ticker como serie | `TimeSeriesPredictor` | Otro problema: `item_id`, `timestamp`, `target`, horizonte de forecast. |
| RNN/LSTM/Transformer propio dentro de Qlib | No AutoGluon Tabular; usar PyTorch/Qlib sequence dataset | Necesitas preservar tensor `[samples, seq_len, features]`. |

## Por qué `Alpha360` sigue siendo tabular

`Alpha360` contiene los últimos 60 días de `close`, `open`, `high`, `low`, `vwap` y `volume`, normalizados por el precio o volumen actual. Eso produce 6 bloques × 60 días = **360 columnas**: `CLOSE59...CLOSE0`, `OPEN59...OPEN0`, etc. ([GitHub](https://raw.githubusercontent.com/microsoft/qlib/main/qlib/contrib/data/loader.py))

Es decir, para una acción en una fecha determinada tienes algo así:

```
AAPL, 2024-01-15:
  CLOSE59, CLOSE58, ..., CLOSE0,
  OPEN59,  OPEN58,  ..., OPEN0,
  HIGH59,  HIGH58,  ..., HIGH0,
  LOW59,   LOW58,   ..., LOW0,
  VWAP59,  VWAP58,  ..., VWAP0,
  VOLUME59,VOLUME58,...,VOLUME0,
  LABEL0
```

Eso **sí contiene historia temporal**, pero ya está transformada en una tabla de features. AutoGluon `TabularPredictor` está diseñado precisamente para predecir una columna objetivo a partir del resto de columnas de una tabla, en modo regresión o clasificación. ([AutoGluon](https://auto.gluon.ai/stable/api/autogluon.tabular.TabularPredictor.html))

Por eso, tu wrapper anterior de `AutoGluonQlibModel` te sirve también para `Alpha360`. Solo cambiarías el handler en el YAML:

```yaml
handler:
  class: Alpha360
  module_path: qlib.contrib.data.handler
  kwargs: *data_handler_config
```

y quizá el path del modelo:

```yaml
path: "./ag_models/us_alpha360"
```

## Cuándo tendría sentido usar `TimeSeriesPredictor`

Usaría `autogluon.timeseries.TimeSeriesPredictor` solo si replanteas el problema como forecasting de series temporales, por ejemplo:

```
item_id = AAPL
timestamp = fecha
target = retorno diario, precio, volatilidad realizada, etc.
prediction_length = 1, 5, 10...
```

AutoGluon Time Series espera datos en formato `TimeSeriesDataFrame`, donde cada fila está identificada por `(item_id, timestamp)`, y su objetivo es predecir valores futuros de una o varias series temporales relacionadas. ([AutoGluon](https://auto.gluon.ai/stable/api/autogluon.timeseries.TimeSeriesDataFrame.html))

El problema es que eso cambia bastante el enfoque. En Qlib, quieres generar **un score comparable entre acciones en la misma fecha** para hacer ranking, IC, Rank IC y backtest long-short/top-k. En AutoGluon TimeSeries estarías más cerca de “predecir la próxima observación de cada serie”, no de optimizar directamente el ranking cross-sectional diario.

Además, aunque AutoGluon TimeSeries soporta covariables temporales, distingue entre `known_covariates`, conocidas para todo el horizonte futuro, y `past_covariates`, conocidas solo hasta el inicio del forecast. ([AutoGluon](https://auto.gluon.ai/stable/tutorials/timeseries/forecasting-indepth.html)) Para factores tipo Alpha360, esto añade complejidad innecesaria si tu objetivo es predecir `LABEL0` desde features observables en `t`.

## Mi recomendación

Para tu pipeline Qlib + AutoGluon:

```
Alpha158  -> AutoGluon Tabular -> baseline principal
Alpha360  -> AutoGluon Tabular -> segunda prueba
TimeSeriesPredictor -> solo experimento separado, no primera opción
```

Yo empezaría así:

```yaml
task:
  model:
    class: AutoGluonQlibModel
    module_path: my_models.autogluon_qlib_model
    kwargs:
      label: LABEL0
      problem_type: regression
      eval_metric: root_mean_squared_error
      presets: medium_quality
      time_limit: 7200
      path: "./ag_models/us_alpha360"

  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: Alpha360
        module_path: qlib.contrib.data.handler
        kwargs: *data_handler_config
      segments:
        train: [2008-01-01, 2017-12-31]
        valid: [2018-01-01, 2020-12-31]
        test:  [2021-01-01, 2025-12-31]
```

## Factor importante: lo que pierdes con tabular

Con `TabularPredictor`, AutoGluon verá:

```
CLOSE59, CLOSE58, ..., CLOSE0
```

como columnas separadas. Puede aprender relaciones no lineales entre ellas, pero **no sabe explícitamente que forman una secuencia ordenada**, salvo por el patrón implícito de los nombres/valores. Para árboles tipo LightGBM, CatBoost, XGBoost o Random Forest, esto suele estar bien como baseline.

Si quieres que el modelo explote la estructura temporal de verdad, entonces no me iría a AutoGluon TimeSeries necesariamente; me iría a un modelo secuencial dentro de Qlib, por ejemplo LSTM, GRU, TCN, Transformer, ALSTM o similar, donde conviertes `Alpha360` a algo tipo:

```
[sample, 60 días, 6 variables]
```

Qlib ya compara muchos modelos de este tipo en sus benchmarks sobre `Alpha158` y `Alpha360`. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md))

## Conclusión

**No cambies a `TimeSeriesPredictor` solo por usar `Alpha360`.**

Para el workflow cuantitativo típico de Qlib —predecir `LABEL0`, generar scores diarios por acción, rankear y backtestear— usa:

```
AutoGluon Tabular + Alpha158
AutoGluon Tabular + Alpha360
```

Después, compara contra LightGBM de Qlib. Si `Alpha360 + AutoGluon Tabular` mejora Rank IC, ICIR o retorno neto, lo mantienes. Si no, el siguiente salto natural no es AutoGluon TimeSeries, sino un modelo secuencial Qlib/PyTorch que preserve la forma temporal de Alpha360.

> Propon un modelo secuencial de Qlib/Pytorch k preservf la forma temporal de Alpha360 o Alpha158?
> 

Sí. Te propongo **dos rutas**, una para `Alpha360` y otra para `Alpha158`, porque “preservar la forma temporal” significa algo distinto en cada caso.

Mi recomendación principal:

```
Alpha360 -> DatasetH + ALSTM / TCN / custom TCN-GRU-Attention
Alpha158 -> TSDatasetH + modelo *_ts: TCN_TS, GRU_TS, LSTM_TS, Transformer_TS
```

La razón es que `Alpha360` ya viene como una ventana temporal de 60 días embebida en las columnas, mientras que `Alpha158` es más tabular y necesita que Qlib cree ventanas con `TSDatasetH`. Qlib documenta en su benchmark que `Alpha158` es tabular y que `Alpha360` contiene datos precio-volumen con relaciones fuertes en la dimensión temporal; también indica que los modelos `*_ts.py` están pensados para `TSDatasetH`, que crea series temporales automáticamente desde datos tabulares. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md))

---

# 1. Para Alpha360: usaría ALSTM o TCN como baseline secuencial

Para `Alpha360`, empezaría con **ALSTM** de Qlib:

```
qlib.contrib.model.pytorch_alstm.ALSTM
```

o con **TCN**:

```
qlib.contrib.model.pytorch_tcn.TCN
```

`Alpha360` está construido con los últimos 60 días de `close`, `open`, `high`, `low`, `vwap` y `volume`, normalizados por el precio/volumen actual. En el código de Qlib, las columnas se generan como `CLOSE59...CLOSE0`, `OPEN59...OPEN0`, `HIGH59...HIGH0`, `LOW59...LOW0`, `VWAP59...VWAP0`, `VOLUME59...VOLUME0`. Eso te permite reinterpretar las 360 columnas como un tensor:

```
[batch, 360] -> [batch, 60 días, 6 variables]
```

Qlib ya usa esa lógica en sus modelos secuenciales sobre `Alpha360`; por ejemplo, su configuración ALSTM oficial para `Alpha360` usa `d_feat: 6`, `DatasetH` y el handler `Alpha360`. ([GitHub](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py))

## Modelo recomendado para Alpha360

Yo usaría este orden:

```
1. ALSTM Alpha360       baseline principal
2. TCN Alpha360         baseline robusto / rápido
3. TCN + GRU + Attention modelo custom
```

En los benchmarks públicos de Qlib sobre CSI300, `ALSTM` y `TCN` están entre los modelos secuenciales más competitivos en `Alpha360`; `ALSTM` muestra buen IC/Rank IC y `TCN` también aparece fuerte. Estos resultados son sobre China, no garantizan rendimiento en US, pero sí sirven como punto de partida técnico. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md))

---

# 2. YAML base para Alpha360 + ALSTM en mercado US

Adaptado a tu caso US:

```yaml
qlib_init:
  provider_uri: "~/.qlib/qlib_data/us_data"
  region: us

market: &market sp500
benchmark: &benchmark SPY

data_handler_config: &data_handler_config
  start_time: 2008-01-01
  end_time: 2025-12-31
  fit_start_time: 2008-01-01
  fit_end_time: 2017-12-31
  instruments: *market

  infer_processors:
    - class: RobustZScoreNorm
      kwargs:
        fields_group: feature
        clip_outlier: true
    - class: Fillna
      kwargs:
        fields_group: feature

  learn_processors:
    - class: DropnaLabel
    - class: CSRankNorm
      kwargs:
        fields_group: label

  label: ["Ref($close, -2) / Ref($close, -1) - 1"]

port_analysis_config: &port_analysis_config
  strategy:
    class: TopkDropoutStrategy
    module_path: qlib.contrib.strategy
    kwargs:
      signal: <PRED>
      topk: 50
      n_drop: 5

  backtest:
    start_time: 2021-01-01
    end_time: 2025-12-31
    account: 100000000
    benchmark: *benchmark
    exchange_kwargs:
      limit_threshold:
      deal_price: close
      open_cost: 0.0002
      close_cost: 0.0002
      min_cost: 1

task:
  model:
    class: ALSTM
    module_path: qlib.contrib.model.pytorch_alstm
    kwargs:
      d_feat: 6
      hidden_size: 64
      num_layers: 2
      dropout: 0.1
      n_epochs: 200
      lr: 1e-3
      early_stop: 20
      batch_size: 800
      metric: loss
      loss: mse
      optimizer: adam
      GPU: 0
      rnn_type: GRU

  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: Alpha360
        module_path: qlib.contrib.data.handler
        kwargs: *data_handler_config

      segments:
        train: [2008-01-01, 2017-12-31]
        valid: [2018-01-01, 2020-12-31]
        test:  [2021-01-01, 2025-12-31]

  record:
    - class: SignalRecord
      module_path: qlib.workflow.record_temp
      kwargs:
        model: <MODEL>
        dataset: <DATASET>

    - class: SigAnaRecord
      module_path: qlib.workflow.record_temp
      kwargs:
        ana_long_short: False
        ann_scaler: 252

    - class: PortAnaRecord
      module_path: qlib.workflow.record_temp
      kwargs:
        config: *port_analysis_config
```

Ejecutarías:

```bash
qrun workflow_config_alstm_Alpha360_us.yaml
```

---

# 3. Para Alpha158: usaría TSDatasetH + TCN_TS o GRU_TS

Para `Alpha158`, **no usaría `DatasetH` si tu objetivo es preservar temporalidad real**. Usaría:

```
TSDatasetH + qlib.contrib.model.pytorch_tcn_ts.TCN
```

o:

```
TSDatasetH + qlib.contrib.model.pytorch_gru_ts.GRU
TSDatasetH + qlib.contrib.model.pytorch_lstm_ts.LSTM
TSDatasetH + qlib.contrib.model.pytorch_transformer_ts.TransformerModel
```

En este caso, Qlib crea algo como:

```
[batch, step_len, n_features]
```

Por ejemplo, con:

```yaml
step_len: 20
```

cada muestra representa 20 días consecutivos de factores `Alpha158`.

En los ejemplos oficiales de Qlib para `Alpha158`, se suele filtrar a 20 features seleccionadas y luego usar `TSDatasetH` con `step_len: 20`; el propio benchmark indica que las “selected 20 features” se basan en la importancia de un modelo LightGBM. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/Transformer/workflow_config_transformer_Alpha158.yaml))

## YAML base para Alpha158 + TCN_TS en US

```yaml
qlib_init:
  provider_uri: "~/.qlib/qlib_data/us_data"
  region: us

market: &market sp500
benchmark: &benchmark SPY

data_handler_config: &data_handler_config
  start_time: 2008-01-01
  end_time: 2025-12-31
  fit_start_time: 2008-01-01
  fit_end_time: 2017-12-31
  instruments: *market

  infer_processors:
    - class: FilterCol
      kwargs:
        fields_group: feature
        col_list: [
          "RESI5", "WVMA5", "RSQR5", "KLEN", "RSQR10",
          "CORR5", "CORD5", "CORR10", "ROC60", "RESI10",
          "VSTD5", "RSQR60", "CORR60", "WVMA60", "STD5",
          "RSQR20", "CORD60", "CORD10", "CORR20", "KLOW"
        ]

    - class: RobustZScoreNorm
      kwargs:
        fields_group: feature
        clip_outlier: true

    - class: Fillna
      kwargs:
        fields_group: feature

  learn_processors:
    - class: DropnaLabel
    - class: CSRankNorm
      kwargs:
        fields_group: label

  label: ["Ref($close, -2) / Ref($close, -1) - 1"]

task:
  model:
    class: TCN
    module_path: qlib.contrib.model.pytorch_tcn_ts
    kwargs:
      d_feat: 20
      num_layers: 5
      n_chans: 32
      kernel_size: 7
      dropout: 0.5
      n_epochs: 200
      lr: 1e-4
      early_stop: 20
      batch_size: 2000
      metric: loss
      loss: mse
      optimizer: adam
      n_jobs: 20
      GPU: 0

  dataset:
    class: TSDatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: Alpha158
        module_path: qlib.contrib.data.handler
        kwargs: *data_handler_config

      segments:
        train: [2008-01-01, 2017-12-31]
        valid: [2018-01-01, 2020-12-31]
        test:  [2021-01-01, 2025-12-31]

      step_len: 20
```

Aquí `d_feat: 20` porque he filtrado a 20 factores. Si usas todo `Alpha158`, cambia a:

```yaml
d_feat: 158
```

pero no lo haría al principio: `20 días × 158 factores` puede sobreparametrizar rápido, especialmente en US si el universo no es muy grande o el histórico no está limpio.

---

# 4. Modelo custom que propondría: TCN + GRU + Attention

Si quieres algo mejor que el baseline de Qlib, propondría un modelo híbrido:

```
AlphaSeqNet
Input temporal
    ↓
Linear projection
    ↓
TCN causal/dilatado
    ↓
GRU
    ↓
Temporal attention
    ↓
Regression / ranking score
```

La intuición:

```
TCN       captura patrones locales: reversión, momentum corto, gaps, rangos.
GRU       captura dinámica secuencial suave.
Attention decide qué días de la ventana pesan más para la predicción.
Head      produce un score comparable cross-sectionally.
```

Para `Alpha360`, la entrada sería:

```
[batch, 360] -> [batch, 60, 6]
```

Para `Alpha158`, con `TSDatasetH`:

```
[batch, 20, 20]     si usas 20 factores seleccionados
[batch, 20, 158]    si usas Alpha158 completo
```

## Núcleo PyTorch del modelo

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

from qlib.contrib.model.tcn import TemporalConvNet

class AlphaSeqNet(nn.Module):
    """
    Modelo secuencial para Alpha360 o Alpha158.

    Alpha360:
        input: [batch, 360]
        reshape interno: [batch, 60, 6]

    Alpha158 con TSDatasetH:
        input: [batch, step_len, d_feat]
    """

    def __init__(
        self,
        d_feat: int = 6,
        hidden_size: int = 64,
        num_tcn_layers: int = 3,
        kernel_size: int = 5,
        dropout: float = 0.1,
        alpha360_mode: bool = True,
    ):
        super().__init__()

        self.d_feat = d_feat
        self.alpha360_mode = alpha360_mode

        self.input_proj = nn.Sequential(
            nn.Linear(d_feat, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        self.tcn = TemporalConvNet(
            num_inputs=hidden_size,
            num_channels=[hidden_size] * num_tcn_layers,
            kernel_size=kernel_size,
            dropout=dropout,
        )

        self.gru = nn.GRU(
            input_size=hidden_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
            dropout=0.0,
        )

        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1, bias=False),
        )

        self.head = nn.Sequential(
            nn.LayerNorm(hidden_size * 2),
            nn.Linear(hidden_size * 2, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1),
        )

    def _reshape_alpha360(self, x: torch.Tensor) -> torch.Tensor:
        """
        Qlib Alpha360 viene ordenado por bloques:
        CLOSE59..0, OPEN59..0, HIGH59..0, LOW59..0, VWAP59..0, VOLUME59..0

        Por eso:
            [B, 360] -> [B, 6, 60] -> [B, 60, 6]
        """
        batch_size = x.shape[0]
        x = x.view(batch_size, self.d_feat, -1)
        x = x.permute(0, 2, 1)
        return x

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.alpha360_mode and x.dim() == 2:
            x = self._reshape_alpha360(x)

        # x: [batch, seq_len, d_feat]
        h = self.input_proj(x)

        # TCN espera [batch, channels, seq_len]
        h_tcn = self.tcn(h.transpose(1, 2)).transpose(1, 2)

        h_gru, _ = self.gru(h_tcn)

        attn_score = self.attention(h_gru)
        attn_weight = F.softmax(attn_score, dim=1)
        context = torch.sum(attn_weight * h_gru, dim=1)

        last_state = h_gru[:, -1, :]
        out = self.head(torch.cat([last_state, context], dim=1))

        return out.squeeze(-1)
```

Este modelo preserva la temporalidad porque **no trata las 360 columnas como factores independientes**, sino como 60 pasos temporales de 6 variables.

---

# 5. Qué usaría en la práctica

Mi elección inicial sería esta:

```
Experimento 1:
Alpha360 + ALSTM oficial Qlib
DatasetH
d_feat = 6
loss = mse
label normalizado con CSRankNorm

Experimento 2:
Alpha360 + TCN oficial Qlib
DatasetH
d_feat = 6

Experimento 3:
Alpha158 + TCN_TS
TSDatasetH
step_len = 20
20 features seleccionadas

Experimento 4:
Alpha360 + custom AlphaSeqNet
reshape [360] -> [60, 6]
TCN + GRU + Attention
```

Para mercado US, empezaría con `Alpha360 + ALSTM`. Es el camino más limpio: preserva la ventana temporal, no requiere `TSDatasetH`, no necesitas rediseñar el handler y ya está alineado con los ejemplos de Qlib.

---

# 6. Alpha360 vs Alpha158: cuál elegir para modelo secuencial

| Dataset | Mejor uso secuencial | Forma recomendada |
| --- | --- | --- |
| `Alpha360` | Sí, muy natural | `[batch, 60, 6]` |
| `Alpha158` | Sí, pero con ventana creada | `[batch, step_len, n_features]` |
| `Alpha158` completo | Posible, más riesgo de overfit | `[batch, 20, 158]` |
| `Alpha158` filtrado | Mejor baseline | `[batch, 20, 20]` |

Mi preferencia:

```
Alpha360 para secuenciales puros.
Alpha158 para árboles, AutoGluon tabular o secuenciales con TSDatasetH.
```

---

# 7. Factores importantes al entrenarlo

Usaría `CSRankNorm` en la etiqueta, no solo retorno crudo. En un modelo de alpha equity normalmente te importa más ordenar acciones que predecir exactamente el retorno.

Mantendría validación temporal estricta:

```
train: 2008-2017
valid: 2018-2020
test:  2021-2025
```

No haría splits aleatorios.

Para Alpha360, empezaría con:

```yaml
d_feat: 6
hidden_size: 64
num_layers: 2
dropout: 0.1
batch_size: 800
lr: 1e-3
early_stop: 20
```

Para Alpha158 con TSDatasetH:

```yaml
step_len: 20
d_feat: 20
dropout: 0.3-0.5
lr: 1e-4 o 1e-3
```

Y siempre compararía contra:

```
LightGBM Alpha158
LightGBM Alpha360
AutoGluon Tabular Alpha158
AutoGluon Tabular Alpha360
```

Porque si el modelo secuencial no mejora Rank IC, ICIR, turnover-adjusted return o drawdown neto, no merece la complejidad.

---

# Conclusión

Para tu caso, propondría este modelo principal:

```
Alpha360 + ALSTM / TCN-GRU-Attention
```

con entrada real:

```
[batch, 60 días, 6 variables]
```

y este modelo alternativo:

```
Alpha158 + TSDatasetH + TCN_TS
```

con entrada:

```
[batch, 20 días, 20 factores seleccionados]
```

No empezaría con Transformer; primero validaría ALSTM y TCN. En datasets financieros diarios, con mucho ruido y señal débil, ALSTM/TCN suelen ser más fáciles de regularizar, más rápidos y más estables que un Transformer grande.

> Pero una vez entrenado el modelo, como harias la prevision a fecha de hoy?
> 

Para hacer una previsión “a fecha de hoy” con Qlib, no reentrenas necesariamente el modelo. Haces **inferencia** sobre el último segmento disponible del `DatasetH` o `TSDatasetH`, usando el modelo ya entrenado y los datos actualizados.

La idea es:

```
1. Actualizar datos OHLCV hasta la última barra disponible
2. Inicializar Qlib apuntando al provider_uri actualizado
3. Construir un dataset solo para inferencia
4. Cargar el modelo entrenado
5. Ejecutar model.predict(dataset, segment="today")
6. Ordenar acciones por score
7. Traducir scores a cartera / órdenes
```

---

# 1. Lo más importante: qué significa “hoy”

Con datos diarios US hay tres casos:

| Momento de ejecución | Datos disponibles | Predicción válida para |
| --- | --- | --- |
| Antes de apertura US | Hasta el cierre de ayer | Señal para operar hoy |
| Durante la sesión US | Datos incompletos de hoy | Mejor no usar Qlib diario estándar |
| Después del cierre US | Ya tienes OHLCV de hoy | Señal para operar mañana |

En Qlib daily, lo normal es hacer esto **después del cierre**, cuando ya tienes la barra diaria completa. Si hoy es `2026-05-01` y ya tienes el cierre de `2026-05-01`, entonces generas scores fechados en `2026-05-01` para decidir la cartera del próximo rebalanceo.

Qlib está pensado para generar **prediction scores** por activo, que luego se usan en análisis de señal o backtest; su workflow separa datos, entrenamiento/inferencia, evaluación y backtest. La documentación oficial muestra que `qrun` automatiza carga, procesamiento, slicing, entrenamiento, inferencia, análisis de señal y backtest. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/component/workflow.rst))

---

# 2. Pipeline manual de inferencia para hoy

Supón que ya entrenaste un modelo secuencial, por ejemplo:

```
Alpha360 + ALSTM
```

y lo guardaste con `R.save_objects` o desde el recorder de Qlib.

## Paso A — Actualizar datos

Antes de predecir, el provider de Qlib tiene que contener la última barra disponible.

Si usas Yahoo:

```bash
cd qlib

python scripts/data_collector/yahoo/collector.py download_data \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --start 2026-04-01 \
  --end 2026-05-01 \
  --delay 1 \
  --interval 1d \
  --region US

python scripts/data_collector/yahoo/collector.py normalize_data \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --normalize_dir ~/.qlib/stock_data/source/us_1d_nor \
  --region US \
  --interval 1d

python scripts/dump_bin.py dump_update \
  --data_path ~/.qlib/stock_data/source/us_1d_nor \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --freq day \
  --exclude_fields date,symbol \
  --file_suffix .csv
```

En producción, mejor usarías tu vendor de datos y un proceso propio de validación. Qlib también tiene módulo de **online serving**, pero su propia documentación recalca que el usuario debe mantener actualizada la fuente de datos para poder servir predicciones con datos recientes. ([Qlib Documentation](https://qlib-xiaoge.readthedocs.io/en/latest/component/online.html?utm_source=chatgpt.com))

---

# 3. Inferencia directa con `model.predict`

Este es el patrón más simple.

```python
import qlib
import pandas as pd

from qlib.constant import REG_US
from qlib.utils import init_instance_by_config
from qlib.workflow import R

qlib.init(
    provider_uri="~/.qlib/qlib_data/us_data",
    region=REG_US,
)
```

Ahora defines el dataset de inferencia. Para `Alpha360 + ALSTM`, usaría el mismo handler que entrenaste, pero con un segmento nuevo llamado `today`.

```python
asof_date = "2026-05-01"

market = "sp500"

data_handler_config = {
    "start_time": "2008-01-01",
    "end_time": asof_date,
    "fit_start_time": "2008-01-01",
    "fit_end_time": "2017-12-31",
    "instruments": market,
    "infer_processors": [
        {
            "class": "RobustZScoreNorm",
            "kwargs": {
                "fields_group": "feature",
                "clip_outlier": True,
            },
        },
        {
            "class": "Fillna",
            "kwargs": {
                "fields_group": "feature",
            },
        },
    ],
    "learn_processors": [
        {"class": "DropnaLabel"},
        {
            "class": "CSRankNorm",
            "kwargs": {
                "fields_group": "label",
            },
        },
    ],
    "label": ["Ref($close, -2) / Ref($close, -1) - 1"],
}

dataset_config = {
    "class": "DatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
        "handler": {
            "class": "Alpha360",
            "module_path": "qlib.contrib.data.handler",
            "kwargs": data_handler_config,
        },
        "segments": {
            "today": (asof_date, asof_date),
        },
    },
}

dataset = init_instance_by_config(dataset_config)
```

Cargas el modelo entrenado desde el recorder. Por ejemplo, si tienes el `recorder_id`:

```python
experiment_name = "workflow"
recorder_id = "TU_RECORDER_ID"

with R.start(experiment_name=experiment_name, recorder_id=recorder_id, resume=True):
    model = R.load_object("params.pkl")

pred = model.predict(dataset, segment="today")
```

Qlib documenta que los modelos custom o contrib deben implementar `predict(dataset, ...)`, preparar el segmento con `dataset.prepare(...)` y devolver un `pandas.Series` de scores con índice `(datetime, instrument)`. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/start/integration.rst))

Después limpias y ordenas:

```python
scores = (
    pred
    .dropna()
    .sort_values(ascending=False)
    .rename("score")
)

print(scores.head(30))
```

La salida será algo de este estilo:

```
datetime    instrument
2026-05-01  AAPL          0.8731
            MSFT          0.8124
            NVDA          0.7992
            ...
Name: score, dtype: float64
```

---

# 4. Convertir la previsión en cartera

Si quieres una cartera long-only top 50:

```python
topk = 50

today_scores = scores.xs(asof_date, level="datetime")
selected = today_scores.head(topk)

weights = selected / selected.abs().sum()
weights = weights.rename("target_weight")

print(weights)
```

Pero en la práctica, para long-only igual-weighted haría:

```python
topk = 50

today_scores = scores.xs(asof_date, level="datetime")
selected = today_scores.head(topk)

weights = pd.Series(
    1.0 / topk,
    index=selected.index,
    name="target_weight",
)

print(weights)
```

Para long-short market-neutral:

```python
n_long = 50
n_short = 50

today_scores = scores.xs(asof_date, level="datetime")

longs = today_scores.head(n_long)
shorts = today_scores.tail(n_short)

weights_long = pd.Series(0.5 / n_long, index=longs.index)
weights_short = pd.Series(-0.5 / n_short, index=shorts.index)

weights = pd.concat([weights_long, weights_short]).rename("target_weight")
print(weights)
```

---

# 5. Función completa de predicción diaria

Yo lo encapsularía así:

```python
import qlib
import pandas as pd

from qlib.constant import REG_US
from qlib.utils import init_instance_by_config
from qlib.workflow import R

def build_alpha360_inference_dataset(
    asof_date: str,
    market: str = "sp500",
    provider_uri: str = "~/.qlib/qlib_data/us_data",
):
    qlib.init(
        provider_uri=provider_uri,
        region=REG_US,
    )

    data_handler_config = {
        "start_time": "2008-01-01",
        "end_time": asof_date,
        "fit_start_time": "2008-01-01",
        "fit_end_time": "2017-12-31",
        "instruments": market,
        "infer_processors": [
            {
                "class": "RobustZScoreNorm",
                "kwargs": {
                    "fields_group": "feature",
                    "clip_outlier": True,
                },
            },
            {
                "class": "Fillna",
                "kwargs": {
                    "fields_group": "feature",
                },
            },
        ],
        "learn_processors": [
            {"class": "DropnaLabel"},
            {
                "class": "CSRankNorm",
                "kwargs": {
                    "fields_group": "label",
                },
            },
        ],
        "label": ["Ref($close, -2) / Ref($close, -1) - 1"],
    }

    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": "Alpha360",
                "module_path": "qlib.contrib.data.handler",
                "kwargs": data_handler_config,
            },
            "segments": {
                "today": (asof_date, asof_date),
            },
        },
    }

    return init_instance_by_config(dataset_config)

def predict_today_scores(
    asof_date: str,
    recorder_id: str,
    experiment_name: str = "workflow",
    market: str = "sp500",
    provider_uri: str = "~/.qlib/qlib_data/us_data",
):
    dataset = build_alpha360_inference_dataset(
        asof_date=asof_date,
        market=market,
        provider_uri=provider_uri,
    )

    with R.start(
        experiment_name=experiment_name,
        recorder_id=recorder_id,
        resume=True,
    ):
        model = R.load_object("params.pkl")

    pred = model.predict(dataset, segment="today")

    scores = (
        pred
        .dropna()
        .sort_values(ascending=False)
        .rename("score")
    )

    return scores

def scores_to_equal_weight_topk(scores: pd.Series, asof_date: str, topk: int = 50):
    today_scores = scores.xs(asof_date, level="datetime")
    selected = today_scores.head(topk)

    weights = pd.Series(
        1.0 / len(selected),
        index=selected.index,
        name="target_weight",
    )

    return weights

if __name__ == "__main__":
    asof_date = "2026-05-01"
    recorder_id = "TU_RECORDER_ID"

    scores = predict_today_scores(
        asof_date=asof_date,
        recorder_id=recorder_id,
        experiment_name="workflow",
        market="sp500",
    )

    print("Top scores")
    print(scores.head(30))

    weights = scores_to_equal_weight_topk(
        scores=scores,
        asof_date=asof_date,
        topk=50,
    )

    print("Target portfolio")
    print(weights)
```

---

# 6. Caso Alpha158 + TSDatasetH

Si entrenaste un modelo secuencial con `Alpha158 + TSDatasetH`, la lógica es casi igual, pero el dataset debe ser `TSDatasetH` y necesitas `step_len`.

Ejemplo:

```python
dataset_config = {
    "class": "TSDatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
        "handler": {
            "class": "Alpha158",
            "module_path": "qlib.contrib.data.handler",
            "kwargs": data_handler_config,
        },
        "segments": {
            "today": (asof_date, asof_date),
        },
        "step_len": 20,
    },
}
```

Importante: aunque el segmento sea solo `today`, el handler debe tener suficiente histórico antes de `today` para construir la ventana de 20 días. Por eso no pongas:

```python
start_time = asof_date
```

sino algo amplio:

```python
start_time = "2008-01-01"
end_time = asof_date
```

o como mínimo:

```python
start_time = "2025-01-01"
end_time = asof_date
```

Para `Alpha360`, también necesitas histórico suficiente porque los 360 factores incluyen una ventana de 60 días.

---

# 7. Cuidado con el label en inferencia

En inferencia real, el label futuro no existe. Pero puedes dejar la definición del label en el handler porque Qlib la necesita para consistencia del dataset. Lo relevante es que en `predict` se pide solo:

```python
col_set="feature"
```

Por tanto, el modelo no necesita conocer el retorno futuro para predecir.

En Qlib, el método `predict` típico prepara el segmento con:

```python
x_test = dataset.prepare("test", col_set="feature", data_key=DataHandlerLP.DK_I)
```

y devuelve la predicción como una serie indexada por fecha e instrumento. Ese es el mismo patrón que deberías usar para un segmento llamado `"today"`. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/start/integration.rst))

---

# 8. Flujo diario recomendado en producción

Yo lo haría así:

```
20:30-22:30 Madrid, según horario US y vendor:
    1. Descargar datos US del día
    2. Validar datos: missing, splits, volumen cero, outliers
    3. Actualizar qlib_data/us_data

Después:
    4. Cargar modelo vigente
    5. Crear dataset de inferencia para última fecha disponible
    6. Generar scores
    7. Aplicar filtros de liquidez/tradability
    8. Construir pesos objetivo
    9. Comparar contra cartera actual
   10. Generar órdenes para próximo mercado abierto
```

No usaría directamente los scores crudos para comprar. Entre el modelo y las órdenes pondría una capa de portfolio construction:

```
score
  -> filtro de universo
  -> filtro de liquidez
  -> neutralización sectorial / beta, si aplica
  -> top-k o optimizador
  -> límites por posición
  -> límites por turnover
  -> costes esperados
  -> órdenes
```

---

# 9. Ejemplo con `TopkDropoutStrategy` dentro de Qlib

Si quieres que Qlib use los scores para simular o construir cartera, puedes crear un segmento de backtest de un solo día o de los últimos días. Pero para producción yo prefiero separar:

```
model.predict(...) -> scores
scores -> pesos objetivo propios
```

El `TopkDropoutStrategy` es muy útil para research, pero para trading real normalmente necesitarás más controles: liquidez, exposición sectorial, max weight, borrow, cash buffer, eventos corporativos y restricciones del broker.

---

# 10. Qué guardaría como output diario

Cada día guardaría al menos:

```
predictions_2026-05-01.parquet
target_weights_2026-05-01.parquet
orders_2026-05-01.csv
data_quality_report_2026-05-01.json
model_metadata_2026-05-01.json
```

Con columnas tipo:

```
date
instrument
score
rank
target_weight
current_weight
trade_weight
expected_cost
adv_20d
price
sector
model_version
data_timestamp
```

Esto te permite auditar si el modelo predijo con datos correctos y si la cartera se construyó de forma reproducible.

---

# 11. Mi recomendación concreta

Para tu caso haría:

```
Research:
    Alpha360 + ALSTM o TCN
    train/valid/test histórico
    qrun para backtest

Serving diario:
    Script Python propio
    init Qlib
    cargar recorder/modelo
    construir DatasetH con segment "today"
    model.predict(dataset, segment="today")
    guardar scores
    construir cartera fuera de Qlib
```

La pieza clave es esta:

```python
segments = {
    "today": ("2026-05-01", "2026-05-01")
}

pred = model.predict(dataset, segment="today")
```

Y la regla operativa clave es:

```
Si tienes la barra completa de hoy, la señal sirve para el próximo rebalanceo.
Si no tienes la barra completa de hoy, usa la última fecha cerrada disponible.
```

> Funciona igual con tabular?
> 

Sí. **Con tabular funciona prácticamente igual**: actualizas datos, construyes un `DatasetH` con un segmento `"today"` o `"inference"`, cargas el modelo entrenado y llamas a:

```python
pred = model.predict(dataset, segment="today")
```

La diferencia es que, con AutoGluon tabular, el modelo no recibe tensores temporales tipo:

```
[batch, seq_len, features]
```

sino una tabla:

```
(datetime, instrument) -> feature_1, feature_2, ..., feature_n
```

Esto encaja con `TabularPredictor`, que está diseñado para predecir una columna objetivo a partir del resto de columnas de una tabla. Qlib, por su parte, espera que un modelo implemente `predict(dataset, segment=...)` y devuelva scores, normalmente como `pandas.Series`. ([AutoGluon](https://auto.gluon.ai/stable/api/autogluon.tabular.TabularPredictor.html))

---

## Flujo equivalente con AutoGluon tabular

Para `Alpha158`:

```
Alpha158 -> DatasetH -> AutoGluonQlibModel -> scores de hoy
```

Para `Alpha360` usado en modo tabular:

```
Alpha360 -> DatasetH -> AutoGluonQlibModel -> scores de hoy
```

En ambos casos, la predicción diaria sería:

```python
dataset = build_inference_dataset(
    handler_class="Alpha158",   # o "Alpha360"
    asof_date="2026-05-01",
)

model = load_trained_autogluon_qlib_model(...)
scores = model.predict(dataset, segment="today")
```

---

## Ejemplo completo para AutoGluon + Alpha158

```python
import qlib
import pandas as pd

from qlib.constant import REG_US
from qlib.utils import init_instance_by_config
from qlib.workflow import R

def build_tabular_inference_dataset(
    asof_date: str,
    handler_class: str = "Alpha158",
    market: str = "sp500",
    provider_uri: str = "~/.qlib/qlib_data/us_data",
):
    qlib.init(
        provider_uri=provider_uri,
        region=REG_US,
    )

    data_handler_config = {
        "start_time": "2008-01-01",
        "end_time": asof_date,
        "fit_start_time": "2008-01-01",
        "fit_end_time": "2017-12-31",
        "instruments": market,

        "infer_processors": [
            {
                "class": "RobustZScoreNorm",
                "kwargs": {
                    "fields_group": "feature",
                    "clip_outlier": True,
                },
            },
            {
                "class": "Fillna",
                "kwargs": {
                    "fields_group": "feature",
                },
            },
        ],

        "learn_processors": [
            {
                "class": "DropnaLabel",
            },
            {
                "class": "CSRankNorm",
                "kwargs": {
                    "fields_group": "label",
                },
            },
        ],

        "label": [
            "Ref($close, -2) / Ref($close, -1) - 1"
        ],
    }

    dataset_config = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": handler_class,
                "module_path": "qlib.contrib.data.handler",
                "kwargs": data_handler_config,
            },
            "segments": {
                "today": (asof_date, asof_date),
            },
        },
    }

    return init_instance_by_config(dataset_config)

def predict_today_with_autogluon(
    asof_date: str,
    recorder_id: str,
    experiment_name: str = "workflow",
    handler_class: str = "Alpha158",
    market: str = "sp500",
):
    dataset = build_tabular_inference_dataset(
        asof_date=asof_date,
        handler_class=handler_class,
        market=market,
    )

    with R.start(
        experiment_name=experiment_name,
        recorder_id=recorder_id,
        resume=True,
    ):
        model = R.load_object("params.pkl")

    pred = model.predict(dataset, segment="today")

    scores = (
        pred
        .dropna()
        .sort_values(ascending=False)
        .rename("score")
    )

    return scores

if __name__ == "__main__":
    scores = predict_today_with_autogluon(
        asof_date="2026-05-01",
        recorder_id="TU_RECORDER_ID",
        experiment_name="workflow",
        handler_class="Alpha158",   # o "Alpha360"
        market="sp500",
    )

    print(scores.head(30))
```

---

## La parte clave está dentro del wrapper

Tu wrapper de AutoGluon debería hacer algo así en `predict`:

```python
from autogluon.tabular import TabularPredictor
from qlib.data.dataset.handler import DataHandlerLP

def predict(self, dataset, segment="test"):
    if self.predictor is None:
        self.predictor = TabularPredictor.load(self.predictor_path)

    x = dataset.prepare(
        segment,
        col_set="feature",
        data_key=DataHandlerLP.DK_I,
    )

    x = self._flatten_columns(x)
    x = x.replace([float("inf"), float("-inf")], pd.NA)

    pred = self.predictor.predict(x)

    return pd.Series(
        pred.to_numpy(),
        index=x.index,
        name="score",
    )
```

Eso es lo importante:

```python
dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
```

En inferencia real no usas el label futuro. Solo generas las features disponibles hasta la fecha de corte. Qlib documenta este patrón: en `predict`, el modelo prepara el dataset del segmento correspondiente con `col_set="feature"` y devuelve los scores. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/start/integration.rst))

---

## Cargar AutoGluon directamente, sin Qlib recorder

También puedes saltarte el recorder de Qlib y cargar AutoGluon desde su carpeta:

```python
from my_models.autogluon_qlib_model import AutoGluonQlibModel

model = AutoGluonQlibModel(
    path="./ag_models/us_alpha158",
    label="LABEL0",
    problem_type="regression",
)

scores = model.predict(dataset, segment="today")
```

Internamente, el wrapper hará:

```python
TabularPredictor.load("./ag_models/us_alpha158")
```

AutoGluon recomienda cargar el predictor con la misma versión con la que fue entrenado; además, como usa pickle internamente, solo deberías cargar modelos desde rutas confiables. ([AutoGluon](https://auto.gluon.ai/stable/api/autogluon.tabular.TabularPredictor.load.html))

---

## Alpha158 tabular vs Alpha360 tabular

La inferencia es igual, pero cambia el handler:

```python
handler_class="Alpha158"
```

o:

```python
handler_class="Alpha360"
```

Con `Alpha158`, cada fila tendrá aproximadamente 158 factores técnicos.

Con `Alpha360`, cada fila tendrá 360 columnas que representan la ventana histórica ya aplanada:

```
CLOSE59, CLOSE58, ..., CLOSE0,
OPEN59,  OPEN58,  ..., OPEN0,
...
VOLUME59, ..., VOLUME0
```

Pero para AutoGluon sigue siendo una tabla. No necesitas `TSDatasetH`.

---

## Convertir scores en cartera

Después de obtener los scores:

```python
scores = predict_today_with_autogluon(...)
```

puedes hacer top-k long-only:

```python
asof_date = "2026-05-01"
topk = 50

today_scores = scores.xs(asof_date, level="datetime")
selected = today_scores.head(topk)

weights = pd.Series(
    1.0 / len(selected),
    index=selected.index,
    name="target_weight",
)

print(weights)
```

O long-short:

```python
n_long = 50
n_short = 50

today_scores = scores.xs(asof_date, level="datetime")

longs = today_scores.head(n_long)
shorts = today_scores.tail(n_short)

weights = pd.concat([
    pd.Series(0.5 / n_long, index=longs.index),
    pd.Series(-0.5 / n_short, index=shorts.index),
]).rename("target_weight")

print(weights)
```

---

## Diferencias prácticas frente al modelo secuencial

| Punto | AutoGluon tabular | Modelo secuencial Qlib/PyTorch |
| --- | --- | --- |
| Dataset | `DatasetH` | `DatasetH` o `TSDatasetH` |
| Input | Tabla 2D | Tensor temporal |
| Alpha158 | Natural | Necesita ventana con `TSDatasetH` |
| Alpha360 | Funciona como 360 columnas | Puede reinterpretarse como `[60, 6]` |
| Predicción diaria | `model.predict(dataset, "today")` | Igual |
| Output | Score por acción | Score por acción |

La llamada final es la misma:

```python
pred = model.predict(dataset, segment="today")
```

Lo que cambia es cómo el modelo interpreta las features por dentro.

---

## Regla operativa

Para daily US:

```
Si ya tienes el cierre completo de hoy:
    asof_date = hoy
    señal para el próximo rebalanceo

Si estás antes del cierre:
    asof_date = último día cerrado
    señal para la próxima apertura
```

Así que sí: **con AutoGluon tabular funciona igual a nivel de serving diario**. Usas `DatasetH`, segmento `"today"`, cargas el wrapper entrenado y obtienes scores ordenables por acción.

> Porque dices k los datos de yahoo son poco fiables o de baja calidad?
> 

No quería decir que Yahoo sea “inservible”. Para **prototipar Qlib, validar el pipeline, entrenar una baseline y hacer pruebas educativas**, Yahoo puede servir. Lo que quería decir es que **no lo trataría como fuente institucional para un backtest serio o para producción** sin una capa fuerte de validación.

Hay varias razones.

## 1. El propio Qlib lo advierte

La documentación del collector Yahoo de Qlib dice explícitamente que los datos vienen de Yahoo Finance, que “might not be perfect” y recomienda preparar datos propios si tienes un dataset de alta calidad. También menciona ejemplos de datos anómalos y dice que, aunque Qlib considera ajustes de precios, algunas series siguen pareciendo muy anormales. Además, para los datasets prehechos, Qlib indica que no se actualizan regularmente y que hay diferencias entre versiones por acceso histórico inestable a Yahoo Finance. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md))

Ese aviso es importante porque `Alpha158` y `Alpha360` son muy sensibles a errores puntuales. Un split mal ajustado, un cierre incorrecto o una vela con volumen raro puede contaminar momentum, volatilidad, correlaciones, medias móviles, ranks cross-sectionales y, en `Alpha360`, toda la ventana de 60 días.

## 2. Yahoo/yfinance no es una fuente institucional oficial para producción

`yfinance` deja claro en su documentación que no está afiliado, respaldado ni validado por Yahoo; es una herramienta open-source que usa APIs públicas de Yahoo y está pensada para investigación/educación. También recuerda que la API de Yahoo Finance es para uso personal. ([Rana Roussi](https://ranaroussi.github.io/yfinance/index.html))

Esto no significa que los precios estén siempre mal. Significa que no tienes las garantías típicas de un vendor profesional: SLA, soporte, trazabilidad de correcciones, documentación completa de corporate actions, identificadores permanentes, control point-in-time, licencia clara para producción, etc.

## 3. El mayor problema no es solo el precio: es el universo histórico

En un backtest equity US, uno de los errores más peligrosos es usar solo acciones que existen hoy. Eso introduce **survivorship bias**: el modelo aprende y se evalúa sobre supervivientes, excluyendo quiebras, fusiones, delistings y compañías que desaparecieron.

Para comparar, CRSP destaca precisamente que su base US incluye valores activos e inactivos, historia survivor-bias-free, corporate actions e identificadores permanentes como PERMNO/PERMCO. ([Center for Research in Security Prices](https://www.crsp.org/research/crsp-us-stock-databases/)) WRDS también lista como elementos de CRSP datos de delisting, corporate actions, identificadores, descriptores, volumen, market cap y retornos con/sin dividendos. ([WRDS](https://wrds-www.wharton.upenn.edu/pages/grid-items/crsp-stock-database-structure/))

Yahoo normalmente te da precios por ticker, pero no te resuelve de forma robusta todo esto:

```
AAPL de hoy ≠ universo invertible histórico completo
SP500 actual ≠ SP500 point-in-time de 2012
ticker histórico ≠ identificador permanente de compañía
retorno hasta delisting ≠ retorno observado si la acción desaparece
```

Para research cuantitativo, esto importa muchísimo.

## 4. Problemas concretos que he visto o que debes esperar

En Yahoo/Qlib/YFinance pueden aparecer problemas de este tipo:

| Problema | Efecto en el modelo |
| --- | --- |
| Splits o dividendos mal ajustados | Retornos falsos, momentum falso, volatilidad falsa |
| Tickers cambiados o reutilizados | Series históricas mal empalmadas |
| Delistings ausentes | Backtest demasiado optimista |
| Universo actual usado hacia atrás | Survivorship bias |
| Datos faltantes o velas anómalas | Factores extremos en `Alpha158` / `Alpha360` |
| Volumen no ajustado o inconsistente | Señales falsas en liquidez, turnover, volume-price correlation |
| Diferencias entre descarga vieja y descarga nueva | Resultados no reproducibles |
| Falta de datos point-in-time | Riesgo de mirar el futuro sin darte cuenta |
| API no oficial / uso personal | Riesgo operativo y legal para producción |

## 5. Por qué afecta especialmente a Qlib

Qlib no solo usa `close`. Los handlers como `Alpha158` calculan familias enteras de factores técnicos: retornos, medias, volatilidades, correlaciones precio-volumen, rankings, slopes, cuantiles, etc. Si un precio está mal ajustado por split, puedes crear un retorno artificial enorme; después ese error se propaga a muchas features.

En `Alpha360`, el problema es incluso más visual: el modelo ve una ventana de 60 días. Un dato malo dentro de esa ventana puede convertirse en un patrón temporal falso.

Ejemplo simple:

```
Día t-1: close = 100
Día t:   close = 50 por split 2:1 no ajustado

El modelo cree que hubo -50% de retorno.
```

Eso puede afectar:

```
ROC
STD
RSQR
corr precio-volumen
rank cross-sectional
label futuro
normalización
señal final
```

## 6. Cuándo sí usaría Yahoo

Yo sí lo usaría para:

```
probar instalación de Qlib
validar que qrun funciona
crear primera baseline
comparar Alpha158 vs Alpha360
probar AutoGluon tabular
probar ALSTM / TCN
desarrollar el pipeline de inferencia diaria
```

Pero marcaría los resultados como:

```
research preliminar, no concluyente
```

## 7. Cuándo no lo usaría sin más

No lo usaría directamente para:

```
decidir capital real
evaluar Sharpe final
hacer selección definitiva de modelo
estimar capacidad
validar una estrategia small-cap
hacer long-short con short book real
analizar eventos corporativos
hacer backtest multi-año con universo dinámico
```

Ahí preferiría un vendor con datos point-in-time, acciones delistadas, corporate actions auditables, histórico de constituyentes y licencias claras.

## 8. Qué haría si aun así quieres usar Yahoo

Lo usaría con una capa de validación:

```
1. Descargar todo desde cero, no mezclar dumps viejos con updates.
2. Comparar adjusted close contra close/splits/dividendos.
3. Detectar retornos diarios extremos, por ejemplo > ±40%.
4. Revisar splits alrededor de esos extremos.
5. Eliminar activos con demasiados missing values.
6. Filtrar acciones con volumen cero o precio demasiado bajo.
7. Crear universo líquido: ADV, precio mínimo, market cap si la tienes.
8. Guardar snapshot diario de datos para reproducibilidad.
9. Comparar algunos tickers contra otra fuente: Polygon, Tiingo, Nasdaq Data Link, Stooq, IBKR, etc.
10. No usar miembros actuales del S&P 500 hacia atrás como si fueran históricos.
```

Una regla práctica: si el modelo parece extraordinariamente bueno con Yahoo, sospecharía primero de los datos, del universo o del label antes de creer que has encontrado alpha.

## Conclusión

Yahoo no es “malo” para empezar. Es **suficiente para prototipar**. Pero para un modelo cuantitativo US en Qlib, los riesgos principales son:

```
corporate actions
delistings
survivorship bias
ticker history
datos anómalos
reproducibilidad
licencia / uso productivo
```

Por eso mi recomendación sería:

```
Fase 1: Yahoo + Qlib para pipeline y baseline.
Fase 2: Validación fuerte de datos.
Fase 3: Migrar a vendor profesional antes de confiar en métricas finales.
```

En otras palabras: Yahoo te sirve para saber si tu arquitectura funciona; no debería ser la única base para decidir si una estrategia tiene edge real.

> Como puedo hacer una validacion fuerte de los datos?
> 

Una **validación fuerte** no es una sola comprobación. Es un pipeline con varias capas:

```
Raw data validation
    ↓
Corporate actions / adjusted prices validation
    ↓
Universe validation
    ↓
Qlib provider validation
    ↓
Feature / label validation
    ↓
Backtest smoke tests
    ↓
Reporte + cuarentena de símbolos
```

La regla principal: **no corrijas silenciosamente**. Señala, aísla y deja trazabilidad.

---

# 1. Define qué significa “dato válido”

Yo clasificaría los controles en tres niveles.

## Errores bloqueantes

Estos deberían impedir entrenamiento o inferencia:

```
duplicados por symbol/date
fechas no ordenadas
precios negativos o cero
high < low
close fuera de [low, high]
open fuera de [low, high]
volumen negativo
missing close
missing volume
benchmark sin datos
menos de 60 barras para Alpha360
universo vacío en una fecha
retornos extremos no explicados por split/dividendo
```

## Alertas fuertes

No bloquean siempre, pero deberían revisarse:

```
retorno diario ajustado > ±30% o ±40%
volumen > 50x mediana móvil de 20 días
precio constante durante muchos días
volumen cero varios días seguidos
muchos missing por ticker
cambios bruscos en factor de ajuste
ticker con muy poca historia
ticker desaparece sin delisting/evento documentado
```

## Alertas de research

Sirven para evaluar calidad del backtest:

```
universo actual usado hacia atrás
ausencia de acciones delistadas
ausencia de delisting returns
cambios de ticker no trazados
ausencia de identificador permanente
benchmark inconsistente
diferencia contra otro vendor
cambios entre descarga de ayer y descarga de hoy
```

Este último bloque es muy importante en US equities. Por ejemplo, CRSP destaca precisamente identificadores permanentes, datos de corporate actions, delistings y securities activas e inactivas como piezas necesarias para research/backtesting limpio. ([crsp.org](https://www.crsp.org/research/crsp-us-stock-databases/), [wrds-www.wharton.upenn.edu](https://wrds-www.wharton.upenn.edu/pages/grid-items/crsp-stock-database-structure/))

---

# 2. Guarda snapshots inmutables

No deberías tener solo:

```
~/.qlib/qlib_data/us_data
```

Deberías guardar algo así:

```
data_lake/
  raw/
    yahoo/
      2026-05-01/
        AAPL.csv
        MSFT.csv
        ...
  normalized/
    yahoo/
      2026-05-01/
  qlib_bin/
    us_data_2026-05-01/
  reports/
    2026-05-01/
      raw_quality_report.parquet
      qlib_quality_report.parquet
      feature_quality_report.parquet
      rejected_symbols.csv
      metadata.json
```

Y en `metadata.json`:

```json
{
  "vendor": "yahoo",
  "download_timestamp_utc": "2026-05-01T23:30:00Z",
  "source_symbols": 503,
  "valid_symbols": 497,
  "rejected_symbols": 6,
  "start_date": "2008-01-01",
  "end_date": "2026-05-01",
  "qlib_region": "us",
  "data_version": "us_yahoo_20260501",
  "git_commit": "abc123",
  "script_version": "data_validation_v1.0"
}
```

Esto te permite reproducir un backtest aunque Yahoo, el collector o una fuente externa cambie datos históricos. Qlib advierte que los datos descargados desde Yahoo pueden no ser perfectos y recomienda usar datasets propios si tienes datos de mayor calidad. ([qlib-xiaoge.readthedocs.io](https://qlib-xiaoge.readthedocs.io/en/latest/start/initialization.html))

---

# 3. Valida los CSV brutos antes de convertir a Qlib

Primero valida la capa raw, antes de `normalize_data` y `dump_bin`.

Ejemplo de script base:

```python
from pathlib import Path
import json
import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume",
}

def load_price_csvs(source_dir: str) -> pd.DataFrame:
    frames = []

    for path in Path(source_dir).glob("*.csv"):
        df = pd.read_csv(path)
        df["source_file"] = path.name

        if "symbol" not in df.columns:
            df["symbol"] = path.stem.upper()

        frames.append(df)

    if not frames:
        raise ValueError(f"No CSV files found in {source_dir}")

    out = pd.concat(frames, ignore_index=True)
    out.columns = [c.lower() for c in out.columns]

    return out

def validate_raw_prices(
    df: pd.DataFrame,
    min_price: float = 0.5,
    max_abs_daily_return: float = 0.40,
    max_missing_ratio_per_symbol: float = 0.05,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    issues = []

    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.upper()

    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Duplicates
    dup_mask = df.duplicated(["symbol", "date"], keep=False)
    if dup_mask.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[dup_mask, "symbol"],
                "date": df.loc[dup_mask, "date"],
                "issue": "duplicate_symbol_date",
                "severity": "error",
                "value": np.nan,
            })
        )

    # Basic missingness
    for col in ["open", "high", "low", "close", "volume"]:
        mask = df[col].isna()
        if mask.any():
            issues.append(
                pd.DataFrame({
                    "symbol": df.loc[mask, "symbol"],
                    "date": df.loc[mask, "date"],
                    "issue": f"missing_{col}",
                    "severity": "error" if col in ["close", "volume"] else "warning",
                    "value": np.nan,
                })
            )

    # Price sanity
    checks = {
        "non_positive_open": df["open"] <= 0,
        "non_positive_high": df["high"] <= 0,
        "non_positive_low": df["low"] <= 0,
        "non_positive_close": df["close"] <= 0,
        "negative_volume": df["volume"] < 0,
        "high_less_than_low": df["high"] < df["low"],
        "open_outside_high_low": (df["open"] > df["high"]) | (df["open"] < df["low"]),
        "close_outside_high_low": (df["close"] > df["high"]) | (df["close"] < df["low"]),
        "very_low_price": df["close"] < min_price,
    }

    for issue_name, mask in checks.items():
        if mask.any():
            severity = "error" if issue_name not in ["very_low_price"] else "warning"
            issues.append(
                pd.DataFrame({
                    "symbol": df.loc[mask, "symbol"],
                    "date": df.loc[mask, "date"],
                    "issue": issue_name,
                    "severity": severity,
                    "value": df.loc[mask, "close"],
                })
            )

    # Returns
    df = df.sort_values(["symbol", "date"])
    df["ret_1d"] = df.groupby("symbol")["close"].pct_change()

    ret_mask = df["ret_1d"].abs() > max_abs_daily_return
    if ret_mask.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[ret_mask, "symbol"],
                "date": df.loc[ret_mask, "date"],
                "issue": "large_raw_return",
                "severity": "warning",
                "value": df.loc[ret_mask, "ret_1d"],
            })
        )

    # Volume anomalies
    df["volume_median_20"] = (
        df.groupby("symbol")["volume"]
        .transform(lambda s: s.rolling(20, min_periods=10).median())
    )

    vol_spike = (
        (df["volume_median_20"] > 0)
        & (df["volume"] > 50 * df["volume_median_20"])
    )

    if vol_spike.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[vol_spike, "symbol"],
                "date": df.loc[vol_spike, "date"],
                "issue": "volume_spike_gt_50x_20d_median",
                "severity": "warning",
                "value": df.loc[vol_spike, "volume"],
            })
        )

    zero_vol = df["volume"] == 0
    if zero_vol.any():
        issues.append(
            pd.DataFrame({
                "symbol": df.loc[zero_vol, "symbol"],
                "date": df.loc[zero_vol, "date"],
                "issue": "zero_volume",
                "severity": "warning",
                "value": 0,
            })
        )

    # Per-symbol missing ratio
    symbol_summary = (
        df.groupby("symbol")
        .agg(
            first_date=("date", "min"),
            last_date=("date", "max"),
            rows=("date", "size"),
            missing_close=("close", lambda s: s.isna().sum()),
            missing_volume=("volume", lambda s: s.isna().sum()),
            min_close=("close", "min"),
            max_abs_ret=("ret_1d", lambda s: s.abs().max()),
            zero_volume_days=("volume", lambda s: (s == 0).sum()),
        )
        .reset_index()
    )

    symbol_summary["missing_close_ratio"] = (
        symbol_summary["missing_close"] / symbol_summary["rows"]
    )

    bad_missing = symbol_summary[
        symbol_summary["missing_close_ratio"] > max_missing_ratio_per_symbol
    ]

    if not bad_missing.empty:
        issues.append(
            pd.DataFrame({
                "symbol": bad_missing["symbol"],
                "date": pd.NaT,
                "issue": "high_missing_close_ratio",
                "severity": "error",
                "value": bad_missing["missing_close_ratio"],
            })
        )

    issue_df = (
        pd.concat(issues, ignore_index=True)
        if issues
        else pd.DataFrame(columns=["symbol", "date", "issue", "severity", "value"])
    )

    return df, issue_df

if __name__ == "__main__":
    source_dir = "~/.qlib/stock_data/source/us_data"
    report_dir = Path("data_lake/reports/latest")
    report_dir.mkdir(parents=True, exist_ok=True)

    df_raw = load_price_csvs(source_dir)
    clean_df, issues = validate_raw_prices(df_raw)

    issues.to_csv(report_dir / "raw_issues.csv", index=False)

    summary = {
        "rows": int(len(clean_df)),
        "symbols": int(clean_df["symbol"].nunique()),
        "errors": int((issues["severity"] == "error").sum()),
        "warnings": int((issues["severity"] == "warning").sum()),
    }

    with open(report_dir / "raw_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(summary)

    if summary["errors"] > 0:
        raise SystemExit("Blocking data errors found. Check raw_issues.csv")
```

Este script no resuelve todo, pero ya evita entrenar con errores obvios.

---

# 4. Valida precios ajustados y corporate actions

Para modelos de retornos, casi siempre quieres trabajar con precios ajustados. Qlib tiene su propia lógica: normaliza precios al primer día de trading del activo y permite usar `$factor` para recuperar precio original, por ejemplo `$close / $factor`. Esto importa porque distintas fuentes ajustan precios de manera diferente. ([qlib-xiaoge.readthedocs.io](https://qlib-xiaoge.readthedocs.io/en/latest/component/data.html))

Yo validaría tres cosas:

```
retorno raw
retorno ajustado
cambios en factor de ajuste
```

Ejemplo:

```python
def validate_adjustment_factor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Espera columnas:
        symbol, date, close, factor

    En Qlib, si tienes close ajustado y factor,
    puedes aproximar precio original como close / factor.
    """

    if "factor" not in df.columns:
        return pd.DataFrame(columns=["symbol", "date", "issue", "severity", "value"])

    out = df.copy()
    out = out.sort_values(["symbol", "date"])

    out["raw_close_est"] = out["close"] / out["factor"]
    out["adj_ret"] = out.groupby("symbol")["close"].pct_change()
    out["raw_ret_est"] = out.groupby("symbol")["raw_close_est"].pct_change()
    out["factor_chg"] = out.groupby("symbol")["factor"].pct_change()

    issues = []

    # Retorno ajustado extremo
    mask_adj = out["adj_ret"].abs() > 0.40
    if mask_adj.any():
        issues.append(pd.DataFrame({
            "symbol": out.loc[mask_adj, "symbol"],
            "date": out.loc[mask_adj, "date"],
            "issue": "large_adjusted_return",
            "severity": "warning",
            "value": out.loc[mask_adj, "adj_ret"],
        }))

    # Factor cambia mucho pero raw no se mueve: sospechoso
    mask_factor = out["factor_chg"].abs() > 0.25
    if mask_factor.any():
        issues.append(pd.DataFrame({
            "symbol": out.loc[mask_factor, "symbol"],
            "date": out.loc[mask_factor, "date"],
            "issue": "large_factor_change",
            "severity": "warning",
            "value": out.loc[mask_factor, "factor_chg"],
        }))

    # Raw se mueve muchísimo y factor no compensa
    mask_unexplained = (
        (out["raw_ret_est"].abs() > 0.40)
        & (out["factor_chg"].abs().fillna(0) < 0.05)
    )

    if mask_unexplained.any():
        issues.append(pd.DataFrame({
            "symbol": out.loc[mask_unexplained, "symbol"],
            "date": out.loc[mask_unexplained, "date"],
            "issue": "large_raw_move_not_explained_by_factor",
            "severity": "error",
            "value": out.loc[mask_unexplained, "raw_ret_est"],
        }))

    return pd.concat(issues, ignore_index=True) if issues else pd.DataFrame()
```

Esta validación es crítica para splits. Un split mal ajustado puede parecer una caída del 50%, contaminar los factores de momentum/volatilidad y alterar los ranks cross-sectionales.

---

# 5. Valida el universo, no solo los precios

En equity US, esta parte es tan importante como el precio.

## Lo mínimo

Para cada fecha de backtest deberías saber:

```
qué acciones eran invertibles en esa fecha
si estaban activas o delistadas
si pertenecían al índice en esa fecha
si tenían suficiente liquidez
si tenían precio mínimo aceptable
si eran common stocks, ADRs, ETFs, REITs, etc.
```

Si usas el S&P 500 actual hacia atrás, tienes survivorship bias.

Una validación fuerte debería producir una tabla así:

```
date        universe_size   missing_price   tradable   rejected   reason
2018-01-02  505             2               492        13         missing/illiquid
2018-01-03  505             1               494        10         missing/illiquid
...
```

## Filtros básicos para US

Para un modelo long-only líquido, yo empezaría con:

```
close >= 5 USD
ADV20 >= 5M o 10M USD
volume > 0
historia mínima >= 252 días
no penny stocks
no símbolos con demasiados missing
opcional: solo common stocks
opcional: excluir ETFs, ADRs, preferreds, warrants
```

Ejemplo:

```python
def build_tradable_universe(
    df: pd.DataFrame,
    min_price: float = 5.0,
    min_adv20: float = 5_000_000,
    min_history_days: int = 252,
) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(["symbol", "date"])

    df["dollar_volume"] = df["close"] * df["volume"]
    df["adv20"] = (
        df.groupby("symbol")["dollar_volume"]
        .transform(lambda s: s.rolling(20, min_periods=10).mean())
    )

    df["history_days"] = df.groupby("symbol").cumcount() + 1

    df["tradable"] = (
        (df["close"] >= min_price)
        & (df["adv20"] >= min_adv20)
        & (df["volume"] > 0)
        & (df["history_days"] >= min_history_days)
    )

    df["reject_reason"] = ""

    df.loc[df["close"] < min_price, "reject_reason"] += "low_price;"
    df.loc[df["adv20"] < min_adv20, "reject_reason"] += "low_adv20;"
    df.loc[df["volume"] <= 0, "reject_reason"] += "zero_volume;"
    df.loc[df["history_days"] < min_history_days, "reject_reason"] += "short_history;"

    return df
```

Para producción, el universo debería venir de una fuente point-in-time. Yahoo/yfinance no resuelve bien por sí solo delistings, cambios de ticker e identificadores permanentes. La documentación de yfinance indica que no está afiliado ni validado por Yahoo y que usa APIs públicas, orientadas a investigación/educación. ([ranaroussi.github.io](https://ranaroussi.github.io/yfinance/index.html))

---

# 6. Valida el provider de Qlib después de `dump_bin`

Después de convertir a formato Qlib, comprueba que Qlib realmente puede leer lo que crees que has cargado.

```python
import qlib
import pandas as pd
import numpy as np

from qlib.constant import REG_US
from qlib.data import D

def validate_qlib_provider(
    provider_uri: str,
    market: str,
    start_time: str,
    end_time: str,
):
    qlib.init(provider_uri=provider_uri, region=REG_US)

    instruments = D.list_instruments(
        instruments=market,
        start_time=start_time,
        end_time=end_time,
        as_list=True,
    )

    fields = [
        "$open",
        "$high",
        "$low",
        "$close",
        "$volume",
        "$factor",
    ]

    df = D.features(
        instruments=instruments,
        fields=fields,
        start_time=start_time,
        end_time=end_time,
        freq="day",
    )

    df.columns = ["open", "high", "low", "close", "volume", "factor"]
    df = df.reset_index()

    issues = []

    checks = {
        "missing_close": df["close"].isna(),
        "missing_volume": df["volume"].isna(),
        "non_positive_close": df["close"] <= 0,
        "negative_volume": df["volume"] < 0,
        "high_less_than_low": df["high"] < df["low"],
        "close_outside_high_low": (df["close"] > df["high"]) | (df["close"] < df["low"]),
    }

    for issue, mask in checks.items():
        if mask.any():
            issues.append(pd.DataFrame({
                "datetime": df.loc[mask, "datetime"],
                "instrument": df.loc[mask, "instrument"],
                "issue": issue,
                "severity": "error",
            }))

    df = df.sort_values(["instrument", "datetime"])
    df["ret_1d"] = df.groupby("instrument")["close"].pct_change()

    large_ret = df["ret_1d"].abs() > 0.40

    if large_ret.any():
        issues.append(pd.DataFrame({
            "datetime": df.loc[large_ret, "datetime"],
            "instrument": df.loc[large_ret, "instrument"],
            "issue": "large_qlib_adjusted_return",
            "severity": "warning",
            "value": df.loc[large_ret, "ret_1d"],
        }))

    issue_df = (
        pd.concat(issues, ignore_index=True)
        if issues
        else pd.DataFrame(columns=["datetime", "instrument", "issue", "severity"])
    )

    daily_coverage = (
        df.groupby("datetime")
        .agg(
            instruments=("instrument", "nunique"),
            missing_close=("close", lambda s: s.isna().sum()),
            missing_volume=("volume", lambda s: s.isna().sum()),
        )
        .reset_index()
    )

    symbol_coverage = (
        df.groupby("instrument")
        .agg(
            first_date=("datetime", "min"),
            last_date=("datetime", "max"),
            rows=("datetime", "size"),
            missing_close=("close", lambda s: s.isna().sum()),
            max_abs_ret=("ret_1d", lambda s: s.abs().max()),
            zero_volume=("volume", lambda s: (s == 0).sum()),
        )
        .reset_index()
    )

    return df, issue_df, daily_coverage, symbol_coverage

if __name__ == "__main__":
    df, issues, daily, symbol = validate_qlib_provider(
        provider_uri="~/.qlib/qlib_data/us_data",
        market="sp500",
        start_time="2008-01-01",
        end_time="2026-05-01",
    )

    issues.to_csv("qlib_provider_issues.csv", index=False)
    daily.to_csv("qlib_daily_coverage.csv", index=False)
    symbol.to_csv("qlib_symbol_coverage.csv", index=False)

    print(issues["severity"].value_counts(dropna=False))
```

Esto detecta errores introducidos por el proceso de normalización/conversión, no solo por el CSV original.

---

# 7. Valida Alpha158 / Alpha360 antes de entrenar

Una vez construyes el `DatasetH`, valida features y labels.

Para `Alpha158`:

```python
from qlib.utils import init_instance_by_config
from qlib.data.dataset.handler import DataHandlerLP
import numpy as np
import pandas as pd

def validate_dataset_features(dataset_config: dict, segment: str = "train"):
    dataset = init_instance_by_config(dataset_config)

    df = dataset.prepare(
        segment,
        col_set=["feature", "label"],
        data_key=DataHandlerLP.DK_L,
    )

    features = df["feature"]
    labels = df["label"]

    feature_report = pd.DataFrame({
        "missing_ratio": features.isna().mean(),
        "inf_ratio": np.isinf(features.replace([np.inf, -np.inf], np.nan)).mean(),
        "mean": features.mean(numeric_only=True),
        "std": features.std(numeric_only=True),
        "min": features.min(numeric_only=True),
        "max": features.max(numeric_only=True),
        "zero_std": features.std(numeric_only=True) == 0,
    })

    if isinstance(labels, pd.DataFrame):
        label_report = labels.describe().T
        label_missing = labels.isna().mean()
    else:
        label_report = labels.describe()
        label_missing = labels.isna().mean()

    daily_coverage = (
        features.reset_index()
        .groupby("datetime")
        .size()
        .rename("rows")
        .reset_index()
    )

    return feature_report, label_report, label_missing, daily_coverage
```

Qué miraría:

```
features con missing_ratio > 20%
features con std = 0
features con valores infinitos
features con outliers extremos
labels con muchos NaN
labels con distribución absurda
cambios fuertes de distribución entre train/valid/test
número de acciones por fecha
```

Para Alpha360, además revisaría que hay 360 columnas y que la ventana está completa. Para modelos secuenciales que reinterpretan Alpha360 como `[60, 6]`, valida que la forma sea coherente:

```python
def validate_alpha360_shape(features: pd.DataFrame):
    n_cols = features.shape[1]

    if n_cols != 360:
        raise ValueError(f"Alpha360 should have 360 features, got {n_cols}")

    groups = ["CLOSE", "OPEN", "HIGH", "LOW", "VWAP", "VOLUME"]

    missing_groups = []
    for g in groups:
        cols = [c for c in features.columns if str(c).upper().startswith(g)]
        if len(cols) != 60:
            missing_groups.append((g, len(cols)))

    if missing_groups:
        raise ValueError(f"Alpha360 column group mismatch: {missing_groups}")
```

---

# 8. Compara train, valid, test e inferencia

Una validación fuerte no solo mira errores absolutos. Mira **drift**.

Por ejemplo:

```python
def compare_feature_distributions(train_features, valid_features, test_features):
    rows = []

    for col in train_features.columns:
        tr = train_features[col].replace([np.inf, -np.inf], np.nan).dropna()
        va = valid_features[col].replace([np.inf, -np.inf], np.nan).dropna()
        te = test_features[col].replace([np.inf, -np.inf], np.nan).dropna()

        if len(tr) < 100 or len(va) < 100 or len(te) < 100:
            continue

        rows.append({
            "feature": col,
            "train_mean": tr.mean(),
            "valid_mean": va.mean(),
            "test_mean": te.mean(),
            "train_std": tr.std(),
            "valid_std": va.std(),
            "test_std": te.std(),
            "valid_mean_z_vs_train": abs(va.mean() - tr.mean()) / (tr.std() + 1e-12),
            "test_mean_z_vs_train": abs(te.mean() - tr.mean()) / (tr.std() + 1e-12),
        })

    return pd.DataFrame(rows).sort_values("test_mean_z_vs_train", ascending=False)
```

Si una feature tiene distribución normal en train y explota en test, puede ser:

```
problema de datos
cambio real de mercado
normalización mal configurada
ticker corrupto
corporate action mal tratado
```

---

# 9. Haz reconciliación contra otra fuente

Aunque uses Yahoo para prototipos, compara una muestra contra otra fuente:

```
Polygon
Tiingo
Stooq
Nasdaq Data Link
IBKR
Alpaca
Refinitiv
FactSet
CRSP
Norgate
```

No necesitas comparar todo cada día. Puedes comparar:

```
top 100 por capitalización
top 100 por ADV
todos los tickers del top-k del modelo
benchmark: SPY, QQQ, IWM, DIA
muestra aleatoria de 50 símbolos
símbolos con alertas
```

Reglas de reconciliación:

```
close difference > 1%              alerta
return difference > 20-50 bps      alerta
volumen difference > 20%           revisar
split date distinto                revisar
missing en una fuente              revisar
```

No esperes igualdad exacta en volumen y ajustes, pero sí coherencia en retornos ajustados.

---

# 10. Valida el calendario

Para US daily, cada símbolo debería estar alineado con el calendario de trading US. Comprueba:

```
no hay sábados/domingos
no hay fechas futuras
no hay festivos con datos falsos
no falta una sesión completa para todo el universo
el benchmark tiene barra en todas las sesiones esperadas
la última fecha disponible coincide con el último cierre real
```

Ejemplo básico:

```python
def validate_calendar(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])

    issues = []

    weekend = out["date"].dt.weekday >= 5
    if weekend.any():
        issues.append(pd.DataFrame({
            "symbol": out.loc[weekend, "symbol"],
            "date": out.loc[weekend, "date"],
            "issue": "weekend_date",
            "severity": "error",
        }))

    future = out["date"] > pd.Timestamp.today().normalize()
    if future.any():
        issues.append(pd.DataFrame({
            "symbol": out.loc[future, "symbol"],
            "date": out.loc[future, "date"],
            "issue": "future_date",
            "severity": "error",
        }))

    daily_count = (
        out.groupby("date")["symbol"]
        .nunique()
        .rename("symbols")
        .reset_index()
    )

    daily_count["pct_change_symbols"] = daily_count["symbols"].pct_change()

    universe_drop = daily_count["pct_change_symbols"] < -0.20
    if universe_drop.any():
        issues.append(pd.DataFrame({
            "symbol": "__ALL__",
            "date": daily_count.loc[universe_drop, "date"],
            "issue": "large_universe_count_drop",
            "severity": "error",
        }))

    return pd.concat(issues, ignore_index=True) if issues else pd.DataFrame()
```

---

# 11. Valida que no hay leakage

Para Qlib, esto es fundamental.

Tu label típico puede ser:

```
Ref($close, -2) / Ref($close, -1) - 1
```

Eso usa precios futuros respecto a la fecha de señal. Está bien para label, pero **nunca debe aparecer algo equivalente en features**.

Checklist:

```
features sin Ref(..., -1), Ref(..., -2), etc.
normalizadores fit solo en train
segmentos cronológicos
no random split
no usar membresía futura del índice
no usar fundamentals publicados después de la fecha
no usar close de hoy para operar al close de hoy
```

Pruebas útiles:

```
1. Entrenar con labels permutadas: IC debe ir cerca de cero.
2. Entrenar con señal aleatoria: Sharpe debe ir cerca de cero.
3. Retrasar señales un día: el resultado debe seguir siendo razonable si tu ejecución es next-day.
4. Aumentar costes: estrategia con turnover alto debe deteriorarse.
5. Cambiar train/valid/test: performance no debe depender de una única ventana.
```

Ejemplo de prueba con señal aleatoria:

```python
import numpy as np
import pandas as pd

def make_random_signal_like(pred: pd.Series, seed: int = 42) -> pd.Series:
    rng = np.random.default_rng(seed)
    random_values = rng.normal(size=len(pred))
    return pd.Series(random_values, index=pred.index, name="random_score")
```

Si una señal aleatoria da un backtest espectacular, tienes un problema en el backtest, universo o costes.

---

# 12. Valida las métricas del backtest como control de datos

Los datos corruptos muchas veces aparecen como resultados demasiado buenos.

Alertas:

```
Sharpe absurdamente alto
drawdown demasiado bajo
turnover irreal
operaciones en activos sin volumen
posiciones en activos con precio NaN
retornos enormes concentrados en pocos tickers
ganancia excesiva en acciones que luego desaparecen
diferencia enorme entre gross y net inexistente pese a alto turnover
```

Haz un reporte de atribución:

```
top 20 días por PnL
top 20 activos por PnL
top 20 operaciones por PnL
retorno medio por decil de score
IC diario
Rank IC diario
turnover diario
exposición sectorial
exposición beta
```

Si el 80% del PnL viene de 3 días o 2 acciones, revisa datos antes de celebrar.

---

# 13. Cuarentena de símbolos

No borres datos sin dejar rastro. Crea una tabla:

```
symbol   start_date   end_date     issue                         action
XYZ      2019-01-01   2020-03-04   large_unadjusted_split_move    quarantine
ABC      2015-07-01   2026-05-01   too_many_missing_days          exclude
DEF      2021-02-10   2021-02-10   bad_volume_spike               warning
```

Luego, antes de crear el universo Qlib:

```python
def apply_symbol_quarantine(df: pd.DataFrame, quarantine_path: str) -> pd.DataFrame:
    quarantine = pd.read_csv(quarantine_path)
    quarantine["start_date"] = pd.to_datetime(quarantine["start_date"])
    quarantine["end_date"] = pd.to_datetime(quarantine["end_date"])

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["symbol"] = out["symbol"].astype(str).str.upper()

    out["quarantined"] = False

    for row in quarantine.itertuples(index=False):
        mask = (
            (out["symbol"] == row.symbol)
            & (out["date"] >= row.start_date)
            & (out["date"] <= row.end_date)
            & (row.action == "quarantine")
        )
        out.loc[mask, "quarantined"] = True

    return out[~out["quarantined"]].drop(columns=["quarantined"])
```

---

# 14. Validación diaria antes de predecir

Para la inferencia “a fecha de hoy”, yo bloquearía la predicción si falla algo de esto:

```
última fecha del provider < fecha esperada
benchmark sin dato en última fecha
menos de X símbolos válidos
caída de universo > 20% contra día anterior
más de Y símbolos con close missing
más de Y símbolos con return > ±40%
menos de 60 barras recientes para Alpha360
features con NaN masivo
```

Ejemplo:

```python
def daily_inference_gate(
    qlib_df: pd.DataFrame,
    asof_date: str,
    min_symbols: int = 400,
    max_large_return_symbols: int = 10,
):
    asof_date = pd.Timestamp(asof_date)

    today = qlib_df[qlib_df["datetime"] == asof_date].copy()

    if today.empty:
        raise RuntimeError(f"No data for asof_date={asof_date.date()}")

    n_symbols = today["instrument"].nunique()

    if n_symbols < min_symbols:
        raise RuntimeError(
            f"Too few symbols on {asof_date.date()}: {n_symbols} < {min_symbols}"
        )

    today_missing_close = today["close"].isna().sum()

    if today_missing_close > 0:
        raise RuntimeError(
            f"Missing close values on {asof_date.date()}: {today_missing_close}"
        )

    latest_by_symbol = qlib_df.sort_values(["instrument", "datetime"]).copy()
    latest_by_symbol["ret_1d"] = latest_by_symbol.groupby("instrument")["close"].pct_change()

    today_ret = latest_by_symbol[latest_by_symbol["datetime"] == asof_date]
    large_ret_count = (today_ret["ret_1d"].abs() > 0.40).sum()

    if large_ret_count > max_large_return_symbols:
        raise RuntimeError(
            f"Too many large returns on {asof_date.date()}: {large_ret_count}"
        )

    return True
```

---

# 15. Orden recomendado en tu pipeline Qlib

Para tu caso concreto:

```
1. Descargar datos raw
2. Validar raw CSV
3. Guardar reporte raw
4. Normalizar datos
5. Validar precios ajustados/factor
6. Convertir a formato Qlib
7. Validar provider Qlib con D.features
8. Construir DatasetH / TSDatasetH
9. Validar features y labels
10. Entrenar modelo
11. Backtest con smoke tests
12. Guardar recorder + data snapshot
13. Para inferencia diaria: repetir pasos 1-8 y aplicar daily gate
```

En bash:

```bash
python validate_raw_prices.py \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --report_dir data_lake/reports/2026-05-01/raw

python scripts/data_collector/yahoo/collector.py normalize_data \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --normalize_dir ~/.qlib/stock_data/source/us_1d_nor \
  --region US \
  --interval 1d

python validate_normalized_prices.py \
  --source_dir ~/.qlib/stock_data/source/us_1d_nor \
  --report_dir data_lake/reports/2026-05-01/normalized

python scripts/dump_bin.py dump_all \
  --data_path ~/.qlib/stock_data/source/us_1d_nor \
  --qlib_dir ~/.qlib/qlib_data/us_data_2026_05_01 \
  --freq day \
  --exclude_fields date,symbol \
  --file_suffix .csv

python validate_qlib_provider.py \
  --provider_uri ~/.qlib/qlib_data/us_data_2026_05_01 \
  --market sp500 \
  --start_time 2008-01-01 \
  --end_time 2026-05-01

python validate_features.py \
  --provider_uri ~/.qlib/qlib_data/us_data_2026_05_01 \
  --handler Alpha158 \
  --market sp500
```

---

# 16. Umbrales iniciales que usaría

Para empezar:

```
close <= 0                         error
volume < 0                         error
high < low                         error
close fuera de [low, high]         error
duplicado symbol/date              error
missing close                      error
missing volume                     error
abs(adjusted return) > 40%         warning/error según ticker
abs(adjusted return) > 80%         error salvo evento documentado
zero volume > 5 días seguidos      warning
missing close ratio > 5%           error
ADV20 < 5M USD                     excluir de universo líquido
close < 5 USD                      excluir de universo líquido
historia < 252 días                excluir de entrenamiento inicial
Alpha360 history < 60 días         excluir de inferencia Alpha360
feature missing ratio > 20%        revisar/excluir feature
label missing ratio alto           revisar segmento
```

Estos umbrales no son universales. Para small caps tendrías que cambiarlos. Para S&P 500 / Nasdaq 100 son razonables como primera barrera.

---

# 17. Mi recomendación práctica

Para tu pipeline Qlib + AutoGluon / PyTorch, implementaría tres scripts obligatorios:

```
validate_raw_prices.py
validate_qlib_provider.py
validate_features_and_labels.py
```

Y haría que el entrenamiento falle si hay errores bloqueantes:

```python
if n_errors > 0:
    raise RuntimeError("Data validation failed. Do not train.")
```

Para producción diaria, haría lo mismo antes de predecir:

```python
if daily_data_gate_passed:
    scores = model.predict(dataset, segment="today")
else:
    no_trade_today()
```

El objetivo no es tener datos perfectos. El objetivo es que ningún modelo entrene o prediga sin que sepas exactamente:

```
qué datos entraron
qué datos fallaron
qué símbolos se excluyeron
qué versión del dataset usaste
qué riesgos quedan vivos
```

Esa es la diferencia entre un backtest bonito y un research pipeline serio.

> Que otras fuentes a parte de Yahoo recomendarias que utilizara. Dame precios aproximados para cada una de ellas.
> 

Sí. Para un pipeline **Qlib + US equities**, yo separaría las fuentes en cuatro grupos: **prototipo barato**, **research diario serio**, **API intradía/real-time**, e **institucional/academic gold standard**.

Mi recomendación directa sería:

```
Presupuesto bajo/medio y backtest diario serio:
    Norgate Data Platinum o Diamond

API sencilla para precios + fundamentals:
    Tiingo, FMP, EODHD, Polygon/Massive

Research académico/institucional:
    CRSP/Compustat vía WRDS, FactSet, LSEG, Bloomberg, QUODD/Xignite

Intradía/tick/real-time:
    Polygon/Massive, Databento, Intrinio, Alpaca
```

Los precios cambian y muchas licencias dependen de si eres **individual, profesional, empresa, display, non-display, redistribución o uso interno**. Te dejo rangos orientativos con precios públicos encontrados en las páginas actuales o, cuando no hay precio público, con presupuesto estimado.

---

## Tabla comparativa rápida

| Fuente | Precio aprox. | Mejor uso | ¿La usaría para Qlib US? |
| --- | --- | --- | --- |
| **Norgate Data** | US Platinum **$630/año**, Diamond **$787.50/año** | Backtesting EOD US survivor-bias-free | **Sí, mi primera opción calidad/precio** |
| **Tiingo** | Individual **$30/mes** o **$300/año**; comercial interno **$50/mes** o **$499/año** | API sencilla EOD/fundamentals/news | Sí, buena alternativa barata |
| **EODHD** | Desde **$19.99/mes**; planes indicados hasta aprox. **€79.99/mes** | API global barata, EOD/fundamentals | Sí para prototipo/mejora sobre Yahoo |
| **FMP** | Free; Starter **$22/mes**; Premium **$59/mes**; Ultimate **$149/mes**, facturación anual | Fundamentals + precios + APIs fáciles | Sí para factores fundamentales |
| **Alpha Vantage** | Free; premium **$49.99-$249.99/mes** personal; planes superiores enterprise | Prototipo, indicadores, API sencilla | Sí, pero no mi favorita para backtest US serio |
| **Twelve Data** | Free; Grow/Pro/Ultra desde aprox. **$29-$329/mes**, según créditos | Multi-mercado, real-time, indicadores | Útil, pero revisaría bien limits/cobertura |
| **Polygon / Massive** | Free; planes stock aprox. **$29-$199/mes** individual; Advanced visible **$199/mes** | Intradía, trades, quotes, real-time | Sí para intradía/real-time |
| **Alpaca Market Data** | Free; **$99/mes** Algo Trader Plus | Datos + broker + trading API | Útil para ejecución/inferencia, no tanto para backtest largo |
| **Intrinio** | EOD US **$3,100/año**; realtime equities desde **$1,250/mes**; Nasdaq Basic **$9,000/año** | API business, datos licenciados | Sí si presupuesto profesional |
| **Databento** | $125 créditos iniciales; uso por datos o subscripción; US Equities Basic históricamente citado **$825/mes** | Tick/intraday/direct feeds | Sí para intradía serio, no como primera fuente EOD larga |
| **Sharadar / Nasdaq Data Link** | Precio no visible sin login; estima **$1k-varios miles/año** | EOD + fundamentals + delisted + point-in-time | Muy interesante para quant equity |
| **CRSP vía WRDS** | No público; típicamente institucional, **decenas de miles/año** si no tienes acceso académico | Gold standard académico US equities | Sí, si tienes acceso |
| **QUODD / Xignite** | Quote-only | APIs profesionales con corporate actions/licencias | Sí para empresa |
| **FactSet / LSEG / Bloomberg** | Quote-only; terminales/feeds suelen ser **miles/mes** o más | Institucional completo | Solo si eres firma/profesional |

---

# 1. Norgate Data: mi opción preferida para Qlib US diario

Para **backtesting diario de acciones US**, Norgate es probablemente la mejor relación calidad/precio si no tienes CRSP. Sus paquetes US incluyen niveles Silver, Gold, Platinum y Diamond. Lo importante: **Platinum y Diamond incluyen delisted securities e historical index constituents**, justo lo que necesitas para reducir survivorship bias. En su tabla oficial, US Platinum cuesta **$346.50 por 6 meses** o **$630 por 12 meses**, y US Diamond cuesta **$433.13 por 6 meses** o **$787.50 por 12 meses**. ([Norgate Data](https://norgatedata.com/stockmarketpackages.php))

Yo elegiría:

```
Norgate US Platinum: suficiente para la mayoría de backtests desde 1990.
Norgate US Diamond: si quieres historia más larga, hasta 1950.
```

Ventajas:

```
delisted stocks
historical index constituents
EOD updates
daily history limpia
pensado para backtesting
muy barato frente a CRSP/FactSet
```

Limitaciones:

```
no es intradía
no es tick data
no es un API cloud estilo REST
históricamente más orientado a Windows/plugins, aunque también tiene paquete Python
```

Para tu caso Qlib:

```
Norgate -> CSV/parquet propio -> formato Qlib -> Alpha158/Alpha360
```

---

# 2. Tiingo: buena API barata para EOD y prototipos serios

Tiingo es una alternativa barata y cómoda si quieres API. Su página de pricing indica **$30/mes o $300/año para individuos**, y **$50/mes o $499/año para uso comercial interno**. ([tiingo.com](https://www.tiingo.com/about/pricing?utm_source=chatgpt.com))

Además, su producto EOD indica que ofrece campos como `open`, `high`, `low`, `close`, `volume`, dividendos y splits, tanto raw como adjusted, y actualizaciones EOD para equities/ETFs. ([tiingo.com](https://www.tiingo.com/products/end-of-day-stock-price-data?utm_source=chatgpt.com))

La usaría para:

```
pipeline diario barato
contrastar Yahoo
prototipos más robustos
factores técnicos diarios
actualizaciones automáticas
```

Pero no la pondría al mismo nivel que Norgate/CRSP para backtests libres de survivorship bias salvo que verifiques muy bien:

```
delisted coverage
ticker changes
corporate actions
constituyentes históricos
licencia para tu uso concreto
```

---

# 3. EODHD: barata, global y fácil de integrar

EODHD es otra opción barata. Su página indica planes desde **$19.99/mes**, free plan con **20 API calls/day**, cobertura de **60+ exchanges**, **150,000 tickers** y **30+ años** de datos históricos para grandes mercados. También menciona datos EOD ajustados por splits y dividendos, intradía en 1 y 5 minutos, fundamentals, options, forex y más. ([EODHD](https://eodhd.com/))

La usaría si quieres algo más “API-first” que Norgate y más económico que Intrinio/Polygon.

Buena para:

```
EOD global
fundamentals sencillos
indices / ETFs
actualizaciones automáticas
prototipo Qlib multi-mercado
```

Cuidado con:

```
calidad real de delisted data
point-in-time fundamentals
licencia comercial
diferencias de ajustes frente a CRSP/Norgate
```

Para Qlib, haría:

```
EODHD API -> guardar raw snapshot -> validar -> normalizar -> dump_bin Qlib
```

---

# 4. Financial Modeling Prep, FMP: buena para factores fundamentales

FMP es útil si además de OHLCV quieres construir factores de fundamentals, ratios, earnings, calendarios, 13F, ownership, etc. Su pricing público muestra plan Free, Starter **$22/mes**, Premium **$59/mes** y Ultimate **$149/mes**, facturados anualmente. El Starter tiene hasta 5 años de histórico, mientras Premium/Ultimate suben a **30+ años**. ([Modelado Financiero Prep](https://site.financialmodelingprep.com/developer/docs/pricing))

La usaría para:

```
factores fundamentales
market cap
ratios
earnings calendar
financial statements
shares float
13F / ownership si contratas plan alto
```

No la usaría como única fuente sin validar si tu prioridad es backtesting survivor-bias-free. Su propia página advierte que, aunque mantienen procesos de extracción y revisión, pueden existir errores u omisiones, y que display/redistribución requiere acuerdos específicos. ([Modelado Financiero Prep](https://site.financialmodelingprep.com/developer/docs/pricing))

Combinación interesante:

```
Norgate para precios + universo histórico
FMP para fundamentals adicionales
```

---

# 5. Alpha Vantage: buena para prototipo, menos para backtest institucional

Alpha Vantage es cómoda y barata. Su página premium indica que la mayoría de endpoints tienen acceso free, pero el límite estándar es **25 API requests/day**; sus planes premium personales visibles van desde **$49.99/mes** por 75 requests/min hasta **$249.99/mes** por 1200 requests/min. También aparecen planes más altos de **$499-$2499/mes**. ([Alpha Vantage](https://www.alphavantage.co/premium/))

La usaría para:

```
experimentos
indicadores técnicos
scripts sencillos
validaciones cruzadas de precios
```

No sería mi fuente principal para un backtest US multi-año con universo dinámico.

---

# 6. Twelve Data: buena si quieres multi-mercado y real-time

Twelve Data tiene un plan gratuito y planes de pago con créditos API/WS. En la página actual aparecen planes Individual como Basic Free, Grow, Pro y Ultra; también aparecen importes “from” desde **$29/mes**, **$99/mes** y **$329/mes**, según configuración, y precios más altos para configuraciones de más créditos como Grow **$79/mes**, Pro **$229/mes** y Ultra **$999/mes**. ([Twelve Data](https://twelvedata.com/pricing))

Tiene sentido si quieres:

```
acciones globales
forex
crypto
ETFs
indicadores técnicos API
WebSocket
datos real-time US
```

Para Qlib diario US, no sería mi primera opción frente a Norgate, pero sí puede servir como proveedor API alternativo.

---

# 7. Polygon / Massive: muy buena para intradía y real-time

Polygon aparece ahora bajo marca Massive en algunas páginas. Para acciones, los precios públicos encontrados están alrededor de:

```
Free
Starter aprox. $29/mes
Developer aprox. $79-$99/mes
Advanced aprox. $199/mes
```

La propia página de Massive muestra **Stocks Advanced a $199/mes** para uso individual, con real-time stock data, 20+ años de historia, websockets y financials/ratios incluidos. ([massive.com](https://massive.com/pricing?utm_source=chatgpt.com))

La usaría para:

```
intradía
trades/quotes
snapshots
websockets
real-time signals
validar ejecución
construir features intradía
```

Para **Alpha158/Alpha360 diarios**, no necesitas Polygon Advanced desde el día uno. Para eso, Norgate o Tiingo te dan mejor relación calidad/precio. Polygon empieza a tener sentido cuando quieras:

```
1-minute bars
second aggregates
quotes
trades
real-time inference
pre-market / after-hours
```

---

# 8. Alpaca Market Data: útil si también vas a ejecutar con Alpaca

Alpaca tiene plan Free y **Algo Trader Plus por $99/mes**. Su página indica **7+ años** de histórico, 100% market coverage, US stocks, US options, crypto, extended hours, corporate actions, aggregate bars, snapshots y WebSockets; el plan Free tiene 200 API calls/min y el Plus tiene llamadas ilimitadas. ([Alpaca](https://alpaca.markets/data))

La usaría para:

```
pipeline de trading/inferencia
validar señales diarias contra broker
paper trading
ejecución automática
datos de últimos años
```

No la elegiría como fuente maestra para un backtest de 20-30 años con delisted stocks. Es más útil como **capa de ejecución + market data reciente**.

---

# 9. Intrinio: profesional, más caro, buena licencia business

Intrinio es más caro, pero más “business-grade”. En su pricing público:

```
EOD Historical Stock Prices: $3,100/año
EquitiesEdge real-time: $1,250/mes
CBOE One delayed: $3,000/año
IEX real-time stock prices: $6,000/año
15-min delayed SIP: $6,000/año
Nasdaq Basic: $9,000/año
US fundamentals: $9,600/año
```

Su EOD Historical Stock Prices indica **50+ años**, precios ajustados y no ajustados, adjustment factors, volume y split ratios, con cobertura de todos los exchanges US. ([intrinio.com](https://intrinio.com/pricing))

La usaría si:

```
eres empresa
necesitas contrato/licencia clara
quieres API/S3/Snowflake/CSV
quieres soporte business
necesitas fundamentals + precios + opciones
```

No la elegiría si tu presupuesto es individual y solo necesitas EOD para research: Norgate te da mucho por bastante menos.

---

# 10. Databento: muy buena para tick/intraday, no primera para EOD largo

Databento es interesante si quieres datos de mercado más cercanos a microestructura: trades, quotes, book, direct feeds, PCAP, etc. Su página indica **$125 en créditos iniciales** para datos históricos y pricing por uso o suscripciones. ([Databento](https://databento.com/pricing?utm_source=chatgpt.com))

Para equities US, Databento tiene datasets como US Equities Mini y Summary; su página de equities menciona que el dataset Summary proporciona precios EOD oficiales y volumen retrasado al 100%, y que US Equities Mini ofrece trades/quotes/BBO derivados de feeds top-of-book. ([Databento](https://databento.com/equities?utm_source=chatgpt.com))

Históricamente, su US Equities Basic se publicó como bundle con cuatro exchanges y precio flat de **$825/mes** para uso ilimitado, aunque para precio definitivo actual conviene mirar el portal. ([Databento](https://databento.com/blog/dbeq-basic?utm_source=chatgpt.com))

La usaría para:

```
intraday serio
microestructura
slippage
fill simulation
book/quotes/trades
estrategias de menor horizonte
```

No sería mi primera opción para `Alpha158`/`Alpha360` daily con 20 años de historia.

---

# 11. Sharadar / Nasdaq Data Link: muy buena si quieres precios + fundamentals point-in-time

Sharadar es una de las fuentes más interesantes para quant equity US porque combina precios EOD, corporate actions, fundamentals, insiders, institutional investors y datos activos/delisted. Nasdaq Data Link indica que Sharadar Equity Prices ofrece adjusted/unadjusted EOD prices y corporate actions para más de **20,000 US public companies** desde 1998; también menciona delisted tickers y corporate actions como splits, dividends, spinoffs, acquisitions, delist reasons y ticker changes. ([data.nasdaq.com](https://data.nasdaq.com/publishers/SHARADAR?utm_source=chatgpt.com))

El problema: Nasdaq Data Link muestra estos datasets como **Premium** y pide login para ver precios. ([data.nasdaq.com](https://data.nasdaq.com/databases/SFA?utm_source=chatgpt.com))

Presupuesto orientativo:

```
Individual/research: probablemente desde ~1k/año, según dataset.
Profesional/comercial: varios miles/año o más.
```

No tomes ese rango como contrato. Hay que pedirlo/loguearse.

Para Qlib, Sharadar sería excelente para:

```
precios EOD
fundamentals point-in-time
acciones activas y delisted
S&P 500 constituents históricos
ticker changes
corporate actions
```

Muy buena combinación:

```
Sharadar prices + fundamentals -> Qlib custom factors
```

---

# 12. CRSP / Compustat vía WRDS: gold standard académico

Si tienes acceso universitario o institucional, CRSP es probablemente el estándar académico para US equities. Harvard describe CRSP como datos históricos de precios, retornos y volumen sobre más de **20,000 stocks**, incluyendo empresas activas e inactivas, con datos mensuales desde 1925 y diarios desde 1962. ([library.hbs.edu](https://www.library.hbs.edu/databases-cases-and-more/databases/center-for-research-in-security-prices?utm_source=chatgpt.com))

CRSP no está pensado para individuos. Su propia página de solicitud de suscripción indica que sus bases de datos están diseñadas para licenciatarios académicos, agencias gubernamentales e investment practitioners, no para inversores individuales. ([Center for Research in Security Prices](https://www.crsp.org/subscription-information/?utm_source=chatgpt.com))

Precio:

```
No público.
Si tienes acceso académico: puede estar incluido en la licencia de tu universidad.
Si eres empresa/institución: presupuestaría decenas de miles de USD/año, dependiendo de módulos.
```

Para un modelo Qlib serio, CRSP/Compustat sería ideal para:

```
survivorship-bias-free universe
PERMNO/PERMCO
delisting returns
share codes
exchange codes
corporate actions
Compustat fundamentals
point-in-time research
```

Si tienes acceso a WRDS, esta sería mi fuente “gold standard”.

---

# 13. QUODD / Xignite: APIs profesionales con licensing más claro

QUODD/Xignite están más en terreno profesional. QUODD indica que ofrece APIs para real-time, delayed e historical data, y su página de historical stock prices menciona ajustes automáticos por splits, dividendos ordinarios/extraordinarios, spinoffs, bonus shares, scrips y stock distributions. ([QUODD](https://www.quodd.com/historical-stock-prices-api-global-market-data?utm_source=chatgpt.com))

Xignite indica que sus APIs se venden con pricing por asset class, región y frecuencia, con **unlimited usage** en sus web services, pero pide contactar para quote. ([website.xignite.com](https://website.xignite.com/Pricing?utm_source=chatgpt.com))

Precio:

```
Quote-only.
Presupuesto típico: varios miles a decenas de miles USD/año, según uso/licencia.
```

Las consideraría si:

```
vas a redistribuir datos
eres fintech
necesitas display/non-display claro
necesitas compliance/licensing
quieres datos profesionales vía API
```

---

# 14. Interactive Brokers: útil para ejecución, no como dataset maestro

IBKR no es exactamente un vendor de research histórico, pero puede ser útil para inferencia y ejecución. Su página de market data indica que los clientes reciben streaming real-time gratuito para US-listed stocks y ETFs vía **Cboe One e IEX**, aunque no consolidado; también ofrece delayed data y snapshots gratuitos. ([Interactive Brokers](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php?utm_source=chatgpt.com))

La usaría para:

```
datos cercanos a ejecución
validar precios actuales
paper/live trading
comparar órdenes y fills
```

No la usaría como base principal para entrenar `Alpha158` o `Alpha360` con décadas de historia.

---

# 15. Bloomberg, FactSet, LSEG/Refinitiv: institucional completo

Estas fuentes son excelentes, pero caras y muchas veces innecesarias para empezar con Qlib. FactSet no publica precio estándar y pide contacto para una propuesta personalizada. ([factset.com](https://www.factset.com/factset-pricing?utm_source=chatgpt.com)) Bloomberg tampoco publica pricing simple en su página oficial; fuentes de benchmarking de compras sitúan una terminal en torno a **$2,360-$2,665/mes por usuario**, es decir, unos **$28k-$32k/año** por terminal. ([CostBench](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/?utm_source=chatgpt.com))

Las usaría si necesitas:

```
terminal profesional
cross-asset
news
estimates
ownership
corporate actions institucionales
Excel add-ins
compliance
datos de muchas clases de activo
```

No son la primera opción para un investigador individual montando Qlib.

---

# Mi recomendación concreta por presupuesto

## Presupuesto < $1,000/año

```
Norgate US Platinum: $630/año
+
Tiingo individual: $300/año, opcional
```

Esto te da una base muy fuerte para daily US equities.

Yo haría:

```
Norgate -> universo histórico + precios diarios + delisted
Tiingo -> API secundaria para contraste / daily updates / validación
```

## Presupuesto $1,000-$3,000/año

```
Norgate Diamond: $787.50/año
+
FMP Premium: $59/mes facturado anual
+
Tiingo o EODHD
```

Esto te permite añadir fundamentals, market cap, ratios y algunos datos alternativos sencillos.

## Presupuesto $3,000-$10,000/año

```
Intrinio EOD Historical Stock Prices: $3,100/año
o
Sharadar/Nasdaq Data Link
+
Norgate como validación alternativa
```

Aquí ya estás en terreno más profesional.

## Presupuesto institucional

```
CRSP + Compustat vía WRDS
o
FactSet / LSEG / Bloomberg / QUODD / Xignite
```

Si puedes acceder a CRSP/Compustat, lo pondría como fuente principal para research académico y usaría otra fuente para ejecución/serving.

---

# Para tu caso Qlib, elegiría así

Si estás empezando pero quieres evitar los problemas más graves de Yahoo:

```
Opción 1 — mejor calidad/precio:
    Norgate US Platinum
    $630/año
```

Si quieres API barata:

```
Opción 2:
    Tiingo + FMP
    ~$300-$700/año individual, según plan
```

Si quieres intradía/real-time:

```
Opción 3:
    Polygon/Massive Advanced
    ~$199/mes
```

Si quieres research institucional:

```
Opción 4:
    CRSP/Compustat vía WRDS
    precio institucional/custom
```

Mi elección práctica sería:

```
Backtest diario:
    Norgate US Platinum o Diamond

Factores fundamentales:
    FMP o Sharadar

Datos intradía/real-time:
    Polygon/Massive o Databento

Ejecución:
    IBKR o Alpaca
```

Y para Qlib:

```
1. Descargar datos raw del vendor.
2. Guardar snapshot inmutable.
3. Validar corporate actions, delisted, missing, outliers.
4. Convertir a formato Qlib.
5. Generar Alpha158/Alpha360.
6. Backtest con universe point-in-time.
7. Usar otro vendor como reconciliación.
```

La combinación que más me gusta para ti sería:

```
Norgate US Platinum + FMP Premium + Polygon/Massive si luego necesitas intradía.
```

Con eso cubrirías bien:

```
precios diarios
delisted stocks
historical constituents
fundamentals
corporate actions
API auxiliar
posible evolución a intradía
```

Sí. Para un pipeline **Qlib + US equities**, yo separaría las fuentes en cuatro grupos: **prototipo barato**, **research diario serio**, **API intradía/real-time**, e **institucional/academic gold standard**.

Mi recomendación directa sería:

```
Presupuesto bajo/medio y backtest diario serio:
    Norgate Data Platinum o Diamond

API sencilla para precios + fundamentals:
    Tiingo, FMP, EODHD, Polygon/Massive

Research académico/institucional:
    CRSP/Compustat vía WRDS, FactSet, LSEG, Bloomberg, QUODD/Xignite

Intradía/tick/real-time:
    Polygon/Massive, Databento, Intrinio, Alpaca
```

Los precios cambian y muchas licencias dependen de si eres **individual, profesional, empresa, display, non-display, redistribución o uso interno**. Te dejo rangos orientativos con precios públicos encontrados en las páginas actuales o, cuando no hay precio público, con presupuesto estimado.

---

## Tabla comparativa rápida

| Fuente | Precio aprox. | Mejor uso | ¿La usaría para Qlib US? |
| --- | --- | --- | --- |
| **Norgate Data** | US Platinum **$630/año**, Diamond **$787.50/año** | Backtesting EOD US survivor-bias-free | **Sí, mi primera opción calidad/precio** |
| **Tiingo** | Individual **$30/mes** o **$300/año**; comercial interno **$50/mes** o **$499/año** | API sencilla EOD/fundamentals/news | Sí, buena alternativa barata |
| **EODHD** | Desde **$19.99/mes**; planes indicados hasta aprox. **€79.99/mes** | API global barata, EOD/fundamentals | Sí para prototipo/mejora sobre Yahoo |
| **FMP** | Free; Starter **$22/mes**; Premium **$59/mes**; Ultimate **$149/mes**, facturación anual | Fundamentals + precios + APIs fáciles | Sí para factores fundamentales |
| **Alpha Vantage** | Free; premium **$49.99-$249.99/mes** personal; planes superiores enterprise | Prototipo, indicadores, API sencilla | Sí, pero no mi favorita para backtest US serio |
| **Twelve Data** | Free; Grow/Pro/Ultra desde aprox. **$29-$329/mes**, según créditos | Multi-mercado, real-time, indicadores | Útil, pero revisaría bien limits/cobertura |
| **Polygon / Massive** | Free; planes stock aprox. **$29-$199/mes** individual; Advanced visible **$199/mes** | Intradía, trades, quotes, real-time | Sí para intradía/real-time |
| **Alpaca Market Data** | Free; **$99/mes** Algo Trader Plus | Datos + broker + trading API | Útil para ejecución/inferencia, no tanto para backtest largo |
| **Intrinio** | EOD US **$3,100/año**; realtime equities desde **$1,250/mes**; Nasdaq Basic **$9,000/año** | API business, datos licenciados | Sí si presupuesto profesional |
| **Databento** | $125 créditos iniciales; uso por datos o subscripción; US Equities Basic históricamente citado **$825/mes** | Tick/intraday/direct feeds | Sí para intradía serio, no como primera fuente EOD larga |
| **Sharadar / Nasdaq Data Link** | Precio no visible sin login; estima **$1k-varios miles/año** | EOD + fundamentals + delisted + point-in-time | Muy interesante para quant equity |
| **CRSP vía WRDS** | No público; típicamente institucional, **decenas de miles/año** si no tienes acceso académico | Gold standard académico US equities | Sí, si tienes acceso |
| **QUODD / Xignite** | Quote-only | APIs profesionales con corporate actions/licencias | Sí para empresa |
| **FactSet / LSEG / Bloomberg** | Quote-only; terminales/feeds suelen ser **miles/mes** o más | Institucional completo | Solo si eres firma/profesional |

---

# 1. Norgate Data: mi opción preferida para Qlib US diario

Para **backtesting diario de acciones US**, Norgate es probablemente la mejor relación calidad/precio si no tienes CRSP. Sus paquetes US incluyen niveles Silver, Gold, Platinum y Diamond. Lo importante: **Platinum y Diamond incluyen delisted securities e historical index constituents**, justo lo que necesitas para reducir survivorship bias. En su tabla oficial, US Platinum cuesta **$346.50 por 6 meses** o **$630 por 12 meses**, y US Diamond cuesta **$433.13 por 6 meses** o **$787.50 por 12 meses**. ([Norgate Data](https://norgatedata.com/stockmarketpackages.php))

Yo elegiría:

```
Norgate US Platinum: suficiente para la mayoría de backtests desde 1990.
Norgate US Diamond: si quieres historia más larga, hasta 1950.
```

Ventajas:

```
delisted stocks
historical index constituents
EOD updates
daily history limpia
pensado para backtesting
muy barato frente a CRSP/FactSet
```

Limitaciones:

```
no es intradía
no es tick data
no es un API cloud estilo REST
históricamente más orientado a Windows/plugins, aunque también tiene paquete Python
```

Para tu caso Qlib:

```
Norgate -> CSV/parquet propio -> formato Qlib -> Alpha158/Alpha360
```

---

# 2. Tiingo: buena API barata para EOD y prototipos serios

Tiingo es una alternativa barata y cómoda si quieres API. Su página de pricing indica **$30/mes o $300/año para individuos**, y **$50/mes o $499/año para uso comercial interno**. ([tiingo.com](https://www.tiingo.com/about/pricing?utm_source=chatgpt.com))

Además, su producto EOD indica que ofrece campos como `open`, `high`, `low`, `close`, `volume`, dividendos y splits, tanto raw como adjusted, y actualizaciones EOD para equities/ETFs. ([tiingo.com](https://www.tiingo.com/products/end-of-day-stock-price-data?utm_source=chatgpt.com))

La usaría para:

```
pipeline diario barato
contrastar Yahoo
prototipos más robustos
factores técnicos diarios
actualizaciones automáticas
```

Pero no la pondría al mismo nivel que Norgate/CRSP para backtests libres de survivorship bias salvo que verifiques muy bien:

```
delisted coverage
ticker changes
corporate actions
constituyentes históricos
licencia para tu uso concreto
```

---

# 3. EODHD: barata, global y fácil de integrar

EODHD es otra opción barata. Su página indica planes desde **$19.99/mes**, free plan con **20 API calls/day**, cobertura de **60+ exchanges**, **150,000 tickers** y **30+ años** de datos históricos para grandes mercados. También menciona datos EOD ajustados por splits y dividendos, intradía en 1 y 5 minutos, fundamentals, options, forex y más. ([EODHD](https://eodhd.com/))

La usaría si quieres algo más “API-first” que Norgate y más económico que Intrinio/Polygon.

Buena para:

```
EOD global
fundamentals sencillos
indices / ETFs
actualizaciones automáticas
prototipo Qlib multi-mercado
```

Cuidado con:

```
calidad real de delisted data
point-in-time fundamentals
licencia comercial
diferencias de ajustes frente a CRSP/Norgate
```

Para Qlib, haría:

```
EODHD API -> guardar raw snapshot -> validar -> normalizar -> dump_bin Qlib
```

---

# 4. Financial Modeling Prep, FMP: buena para factores fundamentales

FMP es útil si además de OHLCV quieres construir factores de fundamentals, ratios, earnings, calendarios, 13F, ownership, etc. Su pricing público muestra plan Free, Starter **$22/mes**, Premium **$59/mes** y Ultimate **$149/mes**, facturados anualmente. El Starter tiene hasta 5 años de histórico, mientras Premium/Ultimate suben a **30+ años**. ([Modelado Financiero Prep](https://site.financialmodelingprep.com/developer/docs/pricing))

La usaría para:

```
factores fundamentales
market cap
ratios
earnings calendar
financial statements
shares float
13F / ownership si contratas plan alto
```

No la usaría como única fuente sin validar si tu prioridad es backtesting survivor-bias-free. Su propia página advierte que, aunque mantienen procesos de extracción y revisión, pueden existir errores u omisiones, y que display/redistribución requiere acuerdos específicos. ([Modelado Financiero Prep](https://site.financialmodelingprep.com/developer/docs/pricing))

Combinación interesante:

```
Norgate para precios + universo histórico
FMP para fundamentals adicionales
```

---

# 5. Alpha Vantage: buena para prototipo, menos para backtest institucional

Alpha Vantage es cómoda y barata. Su página premium indica que la mayoría de endpoints tienen acceso free, pero el límite estándar es **25 API requests/day**; sus planes premium personales visibles van desde **$49.99/mes** por 75 requests/min hasta **$249.99/mes** por 1200 requests/min. También aparecen planes más altos de **$499-$2499/mes**. ([Alpha Vantage](https://www.alphavantage.co/premium/))

La usaría para:

```
experimentos
indicadores técnicos
scripts sencillos
validaciones cruzadas de precios
```

No sería mi fuente principal para un backtest US multi-año con universo dinámico.

---

# 6. Twelve Data: buena si quieres multi-mercado y real-time

Twelve Data tiene un plan gratuito y planes de pago con créditos API/WS. En la página actual aparecen planes Individual como Basic Free, Grow, Pro y Ultra; también aparecen importes “from” desde **$29/mes**, **$99/mes** y **$329/mes**, según configuración, y precios más altos para configuraciones de más créditos como Grow **$79/mes**, Pro **$229/mes** y Ultra **$999/mes**. ([Twelve Data](https://twelvedata.com/pricing))

Tiene sentido si quieres:

```
acciones globales
forex
crypto
ETFs
indicadores técnicos API
WebSocket
datos real-time US
```

Para Qlib diario US, no sería mi primera opción frente a Norgate, pero sí puede servir como proveedor API alternativo.

---

# 7. Polygon / Massive: muy buena para intradía y real-time

Polygon aparece ahora bajo marca Massive en algunas páginas. Para acciones, los precios públicos encontrados están alrededor de:

```
Free
Starter aprox. $29/mes
Developer aprox. $79-$99/mes
Advanced aprox. $199/mes
```

La propia página de Massive muestra **Stocks Advanced a $199/mes** para uso individual, con real-time stock data, 20+ años de historia, websockets y financials/ratios incluidos. ([massive.com](https://massive.com/pricing?utm_source=chatgpt.com))

La usaría para:

```
intradía
trades/quotes
snapshots
websockets
real-time signals
validar ejecución
construir features intradía
```

Para **Alpha158/Alpha360 diarios**, no necesitas Polygon Advanced desde el día uno. Para eso, Norgate o Tiingo te dan mejor relación calidad/precio. Polygon empieza a tener sentido cuando quieras:

```
1-minute bars
second aggregates
quotes
trades
real-time inference
pre-market / after-hours
```

---

# 8. Alpaca Market Data: útil si también vas a ejecutar con Alpaca

Alpaca tiene plan Free y **Algo Trader Plus por $99/mes**. Su página indica **7+ años** de histórico, 100% market coverage, US stocks, US options, crypto, extended hours, corporate actions, aggregate bars, snapshots y WebSockets; el plan Free tiene 200 API calls/min y el Plus tiene llamadas ilimitadas. ([Alpaca](https://alpaca.markets/data))

La usaría para:

```
pipeline de trading/inferencia
validar señales diarias contra broker
paper trading
ejecución automática
datos de últimos años
```

No la elegiría como fuente maestra para un backtest de 20-30 años con delisted stocks. Es más útil como **capa de ejecución + market data reciente**.

---

# 9. Intrinio: profesional, más caro, buena licencia business

Intrinio es más caro, pero más “business-grade”. En su pricing público:

```
EOD Historical Stock Prices: $3,100/año
EquitiesEdge real-time: $1,250/mes
CBOE One delayed: $3,000/año
IEX real-time stock prices: $6,000/año
15-min delayed SIP: $6,000/año
Nasdaq Basic: $9,000/año
US fundamentals: $9,600/año
```

Su EOD Historical Stock Prices indica **50+ años**, precios ajustados y no ajustados, adjustment factors, volume y split ratios, con cobertura de todos los exchanges US. ([intrinio.com](https://intrinio.com/pricing))

La usaría si:

```
eres empresa
necesitas contrato/licencia clara
quieres API/S3/Snowflake/CSV
quieres soporte business
necesitas fundamentals + precios + opciones
```

No la elegiría si tu presupuesto es individual y solo necesitas EOD para research: Norgate te da mucho por bastante menos.

---

# 10. Databento: muy buena para tick/intraday, no primera para EOD largo

Databento es interesante si quieres datos de mercado más cercanos a microestructura: trades, quotes, book, direct feeds, PCAP, etc. Su página indica **$125 en créditos iniciales** para datos históricos y pricing por uso o suscripciones. ([Databento](https://databento.com/pricing?utm_source=chatgpt.com))

Para equities US, Databento tiene datasets como US Equities Mini y Summary; su página de equities menciona que el dataset Summary proporciona precios EOD oficiales y volumen retrasado al 100%, y que US Equities Mini ofrece trades/quotes/BBO derivados de feeds top-of-book. ([Databento](https://databento.com/equities?utm_source=chatgpt.com))

Históricamente, su US Equities Basic se publicó como bundle con cuatro exchanges y precio flat de **$825/mes** para uso ilimitado, aunque para precio definitivo actual conviene mirar el portal. ([Databento](https://databento.com/blog/dbeq-basic?utm_source=chatgpt.com))

La usaría para:

```
intraday serio
microestructura
slippage
fill simulation
book/quotes/trades
estrategias de menor horizonte
```

No sería mi primera opción para `Alpha158`/`Alpha360` daily con 20 años de historia.

---

# 11. Sharadar / Nasdaq Data Link: muy buena si quieres precios + fundamentals point-in-time

Sharadar es una de las fuentes más interesantes para quant equity US porque combina precios EOD, corporate actions, fundamentals, insiders, institutional investors y datos activos/delisted. Nasdaq Data Link indica que Sharadar Equity Prices ofrece adjusted/unadjusted EOD prices y corporate actions para más de **20,000 US public companies** desde 1998; también menciona delisted tickers y corporate actions como splits, dividends, spinoffs, acquisitions, delist reasons y ticker changes. ([data.nasdaq.com](https://data.nasdaq.com/publishers/SHARADAR?utm_source=chatgpt.com))

El problema: Nasdaq Data Link muestra estos datasets como **Premium** y pide login para ver precios. ([data.nasdaq.com](https://data.nasdaq.com/databases/SFA?utm_source=chatgpt.com))

Presupuesto orientativo:

```
Individual/research: probablemente desde ~1k/año, según dataset.
Profesional/comercial: varios miles/año o más.
```

No tomes ese rango como contrato. Hay que pedirlo/loguearse.

Para Qlib, Sharadar sería excelente para:

```
precios EOD
fundamentals point-in-time
acciones activas y delisted
S&P 500 constituents históricos
ticker changes
corporate actions
```

Muy buena combinación:

```
Sharadar prices + fundamentals -> Qlib custom factors
```

---

# 12. CRSP / Compustat vía WRDS: gold standard académico

Si tienes acceso universitario o institucional, CRSP es probablemente el estándar académico para US equities. Harvard describe CRSP como datos históricos de precios, retornos y volumen sobre más de **20,000 stocks**, incluyendo empresas activas e inactivas, con datos mensuales desde 1925 y diarios desde 1962. ([library.hbs.edu](https://www.library.hbs.edu/databases-cases-and-more/databases/center-for-research-in-security-prices?utm_source=chatgpt.com))

CRSP no está pensado para individuos. Su propia página de solicitud de suscripción indica que sus bases de datos están diseñadas para licenciatarios académicos, agencias gubernamentales e investment practitioners, no para inversores individuales. ([Center for Research in Security Prices](https://www.crsp.org/subscription-information/?utm_source=chatgpt.com))

Precio:

```
No público.
Si tienes acceso académico: puede estar incluido en la licencia de tu universidad.
Si eres empresa/institución: presupuestaría decenas de miles de USD/año, dependiendo de módulos.
```

Para un modelo Qlib serio, CRSP/Compustat sería ideal para:

```
survivorship-bias-free universe
PERMNO/PERMCO
delisting returns
share codes
exchange codes
corporate actions
Compustat fundamentals
point-in-time research
```

Si tienes acceso a WRDS, esta sería mi fuente “gold standard”.

---

# 13. QUODD / Xignite: APIs profesionales con licensing más claro

QUODD/Xignite están más en terreno profesional. QUODD indica que ofrece APIs para real-time, delayed e historical data, y su página de historical stock prices menciona ajustes automáticos por splits, dividendos ordinarios/extraordinarios, spinoffs, bonus shares, scrips y stock distributions. ([QUODD](https://www.quodd.com/historical-stock-prices-api-global-market-data?utm_source=chatgpt.com))

Xignite indica que sus APIs se venden con pricing por asset class, región y frecuencia, con **unlimited usage** en sus web services, pero pide contactar para quote. ([website.xignite.com](https://website.xignite.com/Pricing?utm_source=chatgpt.com))

Precio:

```
Quote-only.
Presupuesto típico: varios miles a decenas de miles USD/año, según uso/licencia.
```

Las consideraría si:

```
vas a redistribuir datos
eres fintech
necesitas display/non-display claro
necesitas compliance/licensing
quieres datos profesionales vía API
```

---

# 14. Interactive Brokers: útil para ejecución, no como dataset maestro

IBKR no es exactamente un vendor de research histórico, pero puede ser útil para inferencia y ejecución. Su página de market data indica que los clientes reciben streaming real-time gratuito para US-listed stocks y ETFs vía **Cboe One e IEX**, aunque no consolidado; también ofrece delayed data y snapshots gratuitos. ([Interactive Brokers](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php?utm_source=chatgpt.com))

La usaría para:

```
datos cercanos a ejecución
validar precios actuales
paper/live trading
comparar órdenes y fills
```

No la usaría como base principal para entrenar `Alpha158` o `Alpha360` con décadas de historia.

---

# 15. Bloomberg, FactSet, LSEG/Refinitiv: institucional completo

Estas fuentes son excelentes, pero caras y muchas veces innecesarias para empezar con Qlib. FactSet no publica precio estándar y pide contacto para una propuesta personalizada. ([factset.com](https://www.factset.com/factset-pricing?utm_source=chatgpt.com)) Bloomberg tampoco publica pricing simple en su página oficial; fuentes de benchmarking de compras sitúan una terminal en torno a **$2,360-$2,665/mes por usuario**, es decir, unos **$28k-$32k/año** por terminal. ([CostBench](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/?utm_source=chatgpt.com))

Las usaría si necesitas:

```
terminal profesional
cross-asset
news
estimates
ownership
corporate actions institucionales
Excel add-ins
compliance
datos de muchas clases de activo
```

No son la primera opción para un investigador individual montando Qlib.

---

# Mi recomendación concreta por presupuesto

## Presupuesto < $1,000/año

```
Norgate US Platinum: $630/año
+
Tiingo individual: $300/año, opcional
```

Esto te da una base muy fuerte para daily US equities.

Yo haría:

```
Norgate -> universo histórico + precios diarios + delisted
Tiingo -> API secundaria para contraste / daily updates / validación
```

## Presupuesto $1,000-$3,000/año

```
Norgate Diamond: $787.50/año
+
FMP Premium: $59/mes facturado anual
+
Tiingo o EODHD
```

Esto te permite añadir fundamentals, market cap, ratios y algunos datos alternativos sencillos.

## Presupuesto $3,000-$10,000/año

```
Intrinio EOD Historical Stock Prices: $3,100/año
o
Sharadar/Nasdaq Data Link
+
Norgate como validación alternativa
```

Aquí ya estás en terreno más profesional.

## Presupuesto institucional

```
CRSP + Compustat vía WRDS
o
FactSet / LSEG / Bloomberg / QUODD / Xignite
```

Si puedes acceder a CRSP/Compustat, lo pondría como fuente principal para research académico y usaría otra fuente para ejecución/serving.

---

# Para tu caso Qlib, elegiría así

Si estás empezando pero quieres evitar los problemas más graves de Yahoo:

```
Opción 1 — mejor calidad/precio:
    Norgate US Platinum
    $630/año
```

Si quieres API barata:

```
Opción 2:
    Tiingo + FMP
    ~$300-$700/año individual, según plan
```

Si quieres intradía/real-time:

```
Opción 3:
    Polygon/Massive Advanced
    ~$199/mes
```

Si quieres research institucional:

```
Opción 4:
    CRSP/Compustat vía WRDS
    precio institucional/custom
```

Mi elección práctica sería:

```
Backtest diario:
    Norgate US Platinum o Diamond

Factores fundamentales:
    FMP o Sharadar

Datos intradía/real-time:
    Polygon/Massive o Databento

Ejecución:
    IBKR o Alpaca
```

Y para Qlib:

```
1. Descargar datos raw del vendor.
2. Guardar snapshot inmutable.
3. Validar corporate actions, delisted, missing, outliers.
4. Convertir a formato Qlib.
5. Generar Alpha158/Alpha360.
6. Backtest con universe point-in-time.
7. Usar otro vendor como reconciliación.
```

La combinación que más me gusta para ti sería:

```
Norgate US Platinum + FMP Premium + Polygon/Massive si luego necesitas intradía.
```

Con eso cubrirías bien:

```
precios diarios
delisted stocks
historical constituents
fundamentals
corporate actions
API auxiliar
posible evolución a intradía
```

> Como reaccinamos ante los errores de duplicados? Solo cargo un resultado
> 

Sí: **yo lo marcaría como incidencia de calidad en el fichero raw**, aunque en el resultado final solo cargues una fila.

Pero no todos los duplicados tienen la misma gravedad. La clave es distinguir entre:

```
duplicado exacto        -> warning / incidencia menor
duplicado contradictorio -> error bloqueante
```

## 1. Duplicado exacto

Ejemplo:

```
date,symbol,open,high,low,close,volume
2024-01-02,AAPL,185,188,184,187,50000000
2024-01-02,AAPL,185,188,184,187,50000000
```

Aquí el dato final no cambia si cargas solo una fila. Aun así, yo lo registraría porque indica que algo en el proceso puede estar haciendo append dos veces, mezclando snapshots o reintentando descargas sin limpiar.

Mi política sería:

```
severidad: warning
acción: deduplicar determinísticamente
bloquea entrenamiento: no, si todos los campos son idénticos
bloquea inferencia diaria: normalmente no
```

## 2. Duplicado contradictorio

Ejemplo:

```
date,symbol,open,high,low,close,volume
2024-01-02,AAPL,185,188,184,187,50000000
2024-01-02,AAPL,185,188,184,186.5,51000000
```

Aquí sí lo trataría como **error bloqueante**. Aunque tu loader elija una fila, estás dejando que una decisión implícita cambie el dataset.

Mi política sería:

```
severidad: error
acción: no entrenar / no predecir hasta resolver
bloquea entrenamiento: sí
bloquea inferencia diaria: sí, salvo override documentado
```

Porque puede ocurrir que hoy tu pipeline se quede con la primera fila y mañana con la última. Eso rompe la reproducibilidad del backtest.

---

# 3. Regla práctica

Yo aplicaría esta regla:

```
Si hay duplicados symbol/date:
    si todas las columnas OHLCV/factor/adj son idénticas:
        registrar warning
        deduplicar
        continuar
    si alguna columna relevante difiere:
        registrar error
        bloquear
```

Columnas relevantes:

```
open
high
low
close
volume
adj_close
factor
split
dividend
vwap
```

No consideraría relevante, por ejemplo, una columna auxiliar como:

```
download_timestamp
source_file
row_number
```

Es normal que esas columnas difieran.

---

# 4. Cómo lo implementaría

```python
import pandas as pd
import numpy as np

KEY_COLS = ["symbol", "date"]

VALUE_COLS = [
    "open",
    "high",
    "low",
    "close",
    "volume",
    "factor",
    "adj_close",
    "vwap",
]

def classify_duplicates(df: pd.DataFrame):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.upper()

    value_cols = [c for c in VALUE_COLS if c in df.columns]

    dup_mask = df.duplicated(KEY_COLS, keep=False)
    dup_rows = df.loc[dup_mask].copy()

    if dup_rows.empty:
        return (
            df,
            pd.DataFrame(),
            pd.DataFrame(),
        )

    exact_duplicate_keys = []
    conflicting_duplicate_keys = []

    for key, group in dup_rows.groupby(KEY_COLS, dropna=False):
        # Comparamos solo columnas de mercado.
        values = group[value_cols].copy()

        # Normaliza NaN para que dos NaN cuenten como iguales.
        # nunique(dropna=False) permite detectar diferencias reales.
        nunique = values.nunique(dropna=False)

        if (nunique <= 1).all():
            exact_duplicate_keys.append(key)
        else:
            conflicting_duplicate_keys.append(key)

    exact_duplicates = (
        pd.DataFrame(exact_duplicate_keys, columns=KEY_COLS)
        if exact_duplicate_keys
        else pd.DataFrame(columns=KEY_COLS)
    )

    conflicting_duplicates = (
        pd.DataFrame(conflicting_duplicate_keys, columns=KEY_COLS)
        if conflicting_duplicate_keys
        else pd.DataFrame(columns=KEY_COLS)
    )

    # Deduplicación determinística para duplicados exactos.
    # Si son exactos, keep="last" o keep="first" da igual para datos de mercado,
    # pero conviene fijar siempre la misma regla.
    clean_df = df.drop_duplicates(KEY_COLS, keep="last")

    return clean_df, exact_duplicates, conflicting_duplicates
```

Uso:

```python
clean_df, exact_dups, conflict_dups = classify_duplicates(df)

print(f"Duplicados exactos: {len(exact_dups)}")
print(f"Duplicados conflictivos: {len(conflict_dups)}")

if len(conflict_dups) > 0:
    conflict_dups.to_csv("conflicting_duplicates.csv", index=False)
    raise RuntimeError("Hay duplicados conflictivos. No entrenar ni predecir.")

if len(exact_dups) > 0:
    exact_dups.to_csv("exact_duplicates_warning.csv", index=False)
```

---

# 5. No deduplicaría “a ciegas”

Evitaría hacer simplemente:

```python
df = df.drop_duplicates(["symbol", "date"])
```

sin antes clasificar los duplicados.

Ese código oculta problemas. Puede dejarte con una fila arbitraria dependiendo del orden del CSV.

Tampoco haría:

```python
df = df.groupby(["symbol", "date"]).mean()
```

para OHLCV. Promediar precios duplicados puede crear barras que nunca existieron.

---

# 6. Qué haría si hay conflicto parcial

Caso frecuente:

```
date,symbol,open,high,low,close,volume
2024-01-02,AAPL,185,188,184,187,
2024-01-02,AAPL,185,188,184,187,50000000
```

Aquí las dos filas son iguales salvo que una tiene `volume` vacío.

Mi política sería:

```
si una fila es estrictamente más completa y los valores comunes coinciden:
    quedarse con la fila más completa
    registrar warning fuerte
si los valores comunes no coinciden:
    error bloqueante
```

Puedes resolverlo así:

```python
def resolve_partial_duplicates(df: pd.DataFrame):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str).str.upper()

    value_cols = [c for c in VALUE_COLS if c in df.columns]

    resolved_rows = []
    unresolved_keys = []

    for key, group in df.groupby(KEY_COLS, dropna=False):
        if len(group) == 1:
            resolved_rows.append(group.iloc[0])
            continue

        values = group[value_cols]

        # Para cada columna, miramos valores no nulos distintos.
        non_null_nunique = values.apply(lambda s: s.dropna().nunique())

        if (non_null_nunique <= 1).all():
            # No hay contradicción entre valores observados.
            # Elegimos la fila con más campos no nulos.
            completeness = group[value_cols].notna().sum(axis=1)
            best_idx = completeness.idxmax()
            resolved_rows.append(group.loc[best_idx])
        else:
            unresolved_keys.append(key)

    resolved_df = pd.DataFrame(resolved_rows).reset_index(drop=True)

    unresolved = (
        pd.DataFrame(unresolved_keys, columns=KEY_COLS)
        if unresolved_keys
        else pd.DataFrame(columns=KEY_COLS)
    )

    return resolved_df, unresolved
```

---

# 7. En tu reporte de validación

Yo guardaría siempre esto:

```
n_duplicate_rows
n_duplicate_keys
n_exact_duplicate_keys
n_partial_duplicate_keys
n_conflicting_duplicate_keys
symbols_affected
dates_affected
source_files_affected
dedup_policy_applied
```

Ejemplo de `metadata.json`:

```json
{
  "duplicate_policy": "exact_duplicates_dropped_keep_last",
  "duplicate_keys": 12,
  "exact_duplicate_keys": 10,
  "conflicting_duplicate_keys": 2,
  "training_blocked": true
}
```

---

# 8. Para Qlib concretamente

Antes de ejecutar:

```bash
dump_bin.py dump_all
```

o:

```bash
dump_bin.py dump_update
```

yo dejaría el CSV ya limpio.

No delegaría la resolución de duplicados a Qlib. Qlib debería recibir una tabla ya canónica:

```
una fila por symbol/date
datos OHLCV coherentes
sin conflictos
sin duplicados
```

Porque si el CSV tiene duplicados y Qlib termina cargando uno, puede que no veas el problema en `D.features(...)`, pero el problema sigue existiendo en tu capa raw.

---

# Conclusión

Sí, es un error **en la fuente raw**. Pero su gravedad depende de si el duplicado es idéntico o contradictorio:

```
duplicado exacto:
    warning
    deduplicar
    continuar

duplicado con diferencias en OHLCV/factor/adj:
    error bloqueante
    revisar fuente
    no entrenar ni inferir
```

Mi regla sería: **el dataset final puede tener una sola fila, pero el pipeline debe demostrar por qué esa fila es la correcta**.