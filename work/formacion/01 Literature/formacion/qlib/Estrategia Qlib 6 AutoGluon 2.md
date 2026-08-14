# Estrategia Qlib 6: AutoGluon 2

# 📊 Guía para usar AutoGluon con Alpha154 (Qlib)

¡Perfecto! Alpha154 es un dataset de trading cuantitativo de la plataforma Qlib de Microsoft. Te proporciono una guía completa para trabajar con AutoGluon en este contexto.

## 🔍 ¿Qué es Alpha154?

Alpha154 es un dataset tabular de características financieras que incluye:

- 154 features derivadas de datos OHLCV (Open, High, Low, Close, Volume)
- Datos normalizados por el precio de cierre
- Incluye features como: ROC, MA, STD, BETA, RSV, etc.
- Usado para predecir retornos futuros de acciones

---

## 📋 Instalación

bash

```
# Instalar Qlib (para obtener el dataset Alpha154)
pipinstallpyqlib

# Instalar AutoGluon
pipinstallautogluon.tabular[all]
```

```
# Instalar Qlib (para obtener el dataset Alpha154)
pipinstallpyqlib

# Instalar AutoGluon
pipinstallautogluon.tabular[all]
```

---

## 🚀 Código Completo con AutoGluon

### Opción 1: Usando Qlib + AutoGluon

python

```
import qlib
import pandasas pd
from qlib.contrib.data.handlerimport Alpha158# Similar a Alpha154
from qlib.data.datasetimport DatasetH
from autogluon.tabularimport TabularPredictor

# 1. Inicializar Qlib
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data',region=qlib.constant.REG_CN)

# 2. Cargar dataset Alpha154/158
data_handler_config= {
"start_time":"2008-01-01",
"end_time":"2020-08-01",
"fit_start_time":"2008-01-01",
"fit_end_time":"2014-12-31",
"instruments":"csi300",
}

handler= Alpha158(**data_handler_config)

# 3. Obtener features y labels
features_df= handler.fetch(col_set="feature")
labels_df= handler.fetch(col_set="label")

# 4. Combinar en un solo DataFrame
data= pd.concat([features_df, labels_df],axis=1)
data= data.dropna()# Eliminar NaN

# 5. Preparar train/test split temporal (importante en finanzas!)
train_data= data[data.index<'2017-01-01']
test_data= data[data.index>='2017-01-01']

print(f"Train samples:{len(train_data)}, Test samples:{len(test_data)}")
print(f"Features:{features_df.shape[1]}")

# 6. Entrenar con AutoGluon
label_column='LABEL0'# Nombre típico de la columna objetivo en Qlib

predictor= TabularPredictor(
label=label_column,
path='qlib_autogluon_models/',
eval_metric='rmse'# o 'mae' para regresión
).fit(
train_data=train_data,
time_limit=3600,# 1 hora
presets='best_quality',
verbosity=2
)

# 7. Evaluar
test_features= test_data.drop(columns=[label_column])
test_labels= test_data[label_column]

predictions= predictor.predict(test_features)
performance= predictor.evaluate(test_data)

print(f"\n📈 Performance en Test:")
print(performance)

# 8. Leaderboard de modelos
predictor.leaderboard(test_data)
```

```
import qlib
import pandasas pd
from qlib.contrib.data.handlerimport Alpha158# Similar a Alpha154
from qlib.data.datasetimport DatasetH
from autogluon.tabularimport TabularPredictor

# 1. Inicializar Qlib
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data',region=qlib.constant.REG_CN)

# 2. Cargar dataset Alpha154/158
data_handler_config= {
"start_time":"2008-01-01",
"end_time":"2020-08-01",
"fit_start_time":"2008-01-01",
"fit_end_time":"2014-12-31",
"instruments":"csi300",
}

handler= Alpha158(**data_handler_config)

# 3. Obtener features y labels
features_df= handler.fetch(col_set="feature")
labels_df= handler.fetch(col_set="label")

# 4. Combinar en un solo DataFrame
data= pd.concat([features_df, labels_df],axis=1)
data= data.dropna()# Eliminar NaN

# 5. Preparar train/test split temporal (importante en finanzas!)
train_data= data[data.index<'2017-01-01']
test_data= data[data.index>='2017-01-01']

print(f"Train samples:{len(train_data)}, Test samples:{len(test_data)}")
print(f"Features:{features_df.shape[1]}")

# 6. Entrenar con AutoGluon
label_column='LABEL0'# Nombre típico de la columna objetivo en Qlib

predictor= TabularPredictor(
label=label_column,
path='qlib_autogluon_models/',
eval_metric='rmse'# o 'mae' para regresión
).fit(
train_data=train_data,
time_limit=3600,# 1 hora
presets='best_quality',
verbosity=2
)

# 7. Evaluar
test_features= test_data.drop(columns=[label_column])
test_labels= test_data[label_column]

predictions= predictor.predict(test_features)
performance= predictor.evaluate(test_data)

print(f"\n📈 Performance en Test:")
print(performance)

# 8. Leaderboard de modelos
predictor.leaderboard(test_data)
```

---

### Opción 2: Desde CSV (si ya tienes Alpha154 exportado)

python

```
import pandasas pd
from autogluon.tabularimport TabularPredictor

# Cargar datos
train_data= pd.read_csv('alpha154_train.csv')
test_data= pd.read_csv('alpha154_test.csv')

# Identificar columna objetivo (típicamente es el retorno futuro)
label='LABEL0'# o 'target', 'return', etc.

# Entrenamiento
predictor= TabularPredictor(
label=label,
path='alpha154_models/',
problem_type='regression'# Alpha154 es típicamente regresión
).fit(
    train_data,
presets='best_quality',
time_limit=7200,
num_bag_folds=5,
num_stack_levels=2
)

# Evaluación
results= predictor.evaluate(test_data)
print(results)
```

```
import pandasas pd
from autogluon.tabularimport TabularPredictor

# Cargar datos
train_data= pd.read_csv('alpha154_train.csv')
test_data= pd.read_csv('alpha154_test.csv')

# Identificar columna objetivo (típicamente es el retorno futuro)
label='LABEL0'# o 'target', 'return', etc.

# Entrenamiento
predictor= TabularPredictor(
label=label,
path='alpha154_models/',
problem_type='regression'# Alpha154 es típicamente regresión
).fit(
    train_data,
presets='best_quality',
time_limit=7200,
num_bag_folds=5,
num_stack_levels=2
)

# Evaluación
results= predictor.evaluate(test_data)
print(results)
```

---

## ⚙️ Configuraciones Recomendadas para Alpha154

### Para Máxima Precisión:

python

```
predictor= TabularPredictor(
label='LABEL0',
eval_metric='rmse',
path='alpha154_best/',
verbosity=3
).fit(
    train_data,
presets='best_quality',
time_limit=14400,# 4 horas
num_bag_folds=8,
num_stack_levels=3,
hyperparameter_tune_kwargs='auto'
)
```

```
predictor= TabularPredictor(
label='LABEL0',
eval_metric='rmse',
path='alpha154_best/',
verbosity=3
).fit(
    train_data,
presets='best_quality',
time_limit=14400,# 4 horas
num_bag_folds=8,
num_stack_levels=3,
hyperparameter_tune_kwargs='auto'
)
```

### Para Producción (más rápido):

python

```
predictor= TabularPredictor(
label='LABEL0',
eval_metric='mae',
path='alpha154_prod/',
).fit(
    train_data,
presets='high_quality',
time_limit=1800,# 30 minutos
num_bag_folds=3
)
```

```
predictor= TabularPredictor(
label='LABEL0',
eval_metric='mae',
path='alpha154_prod/',
).fit(
    train_data,
presets='high_quality',
time_limit=1800,# 30 minutos
num_bag_folds=3
)
```

---

## 📊 Métricas Financieras Específicas

python

```
from sklearn.metricsimport mean_squared_error, mean_absolute_error
import numpyas np

# Después de hacer predicciones
y_true= test_data[label_column].values
y_pred= predictions.values

# Métricas básicas
rmse= np.sqrt(mean_squared_error(y_true, y_pred))
mae= mean_absolute_error(y_true, y_pred)

# Métricas específicas para trading
# IC (Information Coefficient) - correlación entre predicción y retorno real
ic= np.corrcoef(y_pred, y_true)[0,1]

# Rank IC
rank_ic= np.corrcoef(
    pd.Series(y_pred).rank(),
    pd.Series(y_true).rank()
)[0,1]

print(f"RMSE:{rmse:.6f}")
print(f"MAE:{mae:.6f}")
print(f"IC:{ic:.4f}")
print(f"Rank IC:{rank_ic:.4f}")
```

```
from sklearn.metricsimport mean_squared_error, mean_absolute_error
import numpyas np

# Después de hacer predicciones
y_true= test_data[label_column].values
y_pred= predictions.values

# Métricas básicas
rmse= np.sqrt(mean_squared_error(y_true, y_pred))
mae= mean_absolute_error(y_true, y_pred)

# Métricas específicas para trading
# IC (Information Coefficient) - correlación entre predicción y retorno real
ic= np.corrcoef(y_pred, y_true)[0,1]

# Rank IC
rank_ic= np.corrcoef(
    pd.Series(y_pred).rank(),
    pd.Series(y_true).rank()
)[0,1]

print(f"RMSE:{rmse:.6f}")
print(f"MAE:{mae:.6f}")
print(f"IC:{ic:.4f}")
print(f"Rank IC:{rank_ic:.4f}")
```

---

## ⚠️ Consideraciones Importantes

### 1. Split Temporal (NO aleatorio)

python

```
# ❌ INCORRECTO para series temporales
from sklearn.model_selectionimport train_test_split
train, test= train_test_split(data,test_size=0.2)# ¡No hacer esto!

# ✅ CORRECTO - Split temporal
train= data[data.index<'2017-01-01']
test= data[data.index>='2017-01-01']
```

```
# ❌ INCORRECTO para series temporales
from sklearn.model_selectionimport train_test_split
train, test= train_test_split(data,test_size=0.2)# ¡No hacer esto!

# ✅ CORRECTO - Split temporal
train= data[data.index<'2017-01-01']
test= data[data.index>='2017-01-01']
```

### 2. Manejo de Look-ahead Bias

python

```
# Asegúrate que las features no usen información futura
# Qlib ya maneja esto, pero verifica:
print(train_data.columns.tolist())
# Features como Ref($close, -1) indican retorno futuro (label)
```

```
# Asegúrate que las features no usen información futura
# Qlib ya maneja esto, pero verifica:
print(train_data.columns.tolist())
# Features como Ref($close, -1) indican retorno futuro (label)
```

### 3. Normalización

python

```
# Alpha154 ya viene normalizado, pero si usas datos crudos:
from sklearn.preprocessingimport StandardScaler

scaler= StandardScaler()
train_features= train_data.drop(columns=[label])
train_scaled= scaler.fit_transform(train_features)
```

```
# Alpha154 ya viene normalizado, pero si usas datos crudos:
from sklearn.preprocessingimport StandardScaler

scaler= StandardScaler()
train_features= train_data.drop(columns=[label])
train_scaled= scaler.fit_transform(train_features)
```

---

## 📈 Comparativa de Modelos en Alpha158 (Referencia)

Según los benchmarks de Qlib:

| Modelo | IC | ICIR | Annualized Return |
| --- | --- | --- | --- |
| LightGBM | 0.0448 | 0.3660 | 9.01% |
| XGBoost | 0.0498 | 0.3779 | 7.80% |
| CatBoost | 0.0481 | 0.3366 | 7.65% |
| MLP | 0.0376 | 0.2846 | 8.95% |
| DoubleEnsemble | 0.0521 | 0.4223 | 11.58% |

AutoGluon combina múltiples modelos, potencialmente superando modelos individuales.

---

## 🔄 Workflow Completo de Producción

python

```
import qlib
import pandasas pd
from autogluon.tabularimport TabularPredictor
import joblib

classAlpha154AutoGluonPipeline:
def__init__(self,qlib_data_path,model_path='alpha154_ag_model/'):
self.qlib_data_path= qlib_data_path
self.model_path= model_path
self.predictor=None

defprepare_data(self,instruments='csi300',
train_end='2016-12-31',
test_start='2017-01-01'):
"""Preparar datos desde Qlib"""
        qlib.init(provider_uri=self.qlib_data_path,region=qlib.constant.REG_CN)

from qlib.contrib.data.handlerimport Alpha158
        handler= Alpha158(
start_time='2008-01-01',
end_time='2020-08-01',
fit_start_time='2008-01-01',
fit_end_time=train_end,
instruments=instruments,
        )

        features= handler.fetch(col_set='feature')
        labels= handler.fetch(col_set='label')

        data= pd.concat([features, labels],axis=1).dropna()

        train= data[data.index< train_end]
        test= data[data.index>= test_start]

return train, test

deftrain(self,train_data,time_limit=3600):
"""Entrenar modelo"""
self.predictor= TabularPredictor(
label='LABEL0',
path=self.model_path,
eval_metric='rmse'
        ).fit(
            train_data,
presets='best_quality',
time_limit=time_limit
        )
returnself.predictor

defevaluate(self,test_data):
"""Evaluar modelo"""
returnself.predictor.evaluate(test_data)

defpredict(self,data):
"""Hacer predicciones"""
returnself.predictor.predict(data.drop(columns=['LABEL0']))

defsave(self,path='pipeline.pkl'):
"""Guardar pipeline"""
        joblib.dump(self.predictor, path)

defload(self,path='pipeline.pkl'):
"""Cargar pipeline"""
self.predictor= joblib.load(path)

# Uso
pipeline= Alpha154AutoGluonPipeline('~/.qlib/qlib_data/cn_data')
train, test= pipeline.prepare_data()
pipeline.train(train,time_limit=7200)
results= pipeline.evaluate(test)
print(results)
```

```
import qlib
import pandasas pd
from autogluon.tabularimport TabularPredictor
import joblib

classAlpha154AutoGluonPipeline:
def__init__(self,qlib_data_path,model_path='alpha154_ag_model/'):
self.qlib_data_path= qlib_data_path
self.model_path= model_path
self.predictor=None

defprepare_data(self,instruments='csi300',
train_end='2016-12-31',
test_start='2017-01-01'):
"""Preparar datos desde Qlib"""
        qlib.init(provider_uri=self.qlib_data_path,region=qlib.constant.REG_CN)

from qlib.contrib.data.handlerimport Alpha158
        handler= Alpha158(
start_time='2008-01-01',
end_time='2020-08-01',
fit_start_time='2008-01-01',
fit_end_time=train_end,
instruments=instruments,
        )

        features= handler.fetch(col_set='feature')
        labels= handler.fetch(col_set='label')

        data= pd.concat([features, labels],axis=1).dropna()

        train= data[data.index< train_end]
        test= data[data.index>= test_start]

return train, test

deftrain(self,train_data,time_limit=3600):
"""Entrenar modelo"""
self.predictor= TabularPredictor(
label='LABEL0',
path=self.model_path,
eval_metric='rmse'
        ).fit(
            train_data,
presets='best_quality',
time_limit=time_limit
        )
returnself.predictor

defevaluate(self,test_data):
"""Evaluar modelo"""
returnself.predictor.evaluate(test_data)

defpredict(self,data):
"""Hacer predicciones"""
returnself.predictor.predict(data.drop(columns=['LABEL0']))

defsave(self,path='pipeline.pkl'):
"""Guardar pipeline"""
        joblib.dump(self.predictor, path)

defload(self,path='pipeline.pkl'):
"""Cargar pipeline"""
self.predictor= joblib.load(path)

# Uso
pipeline= Alpha154AutoGluonPipeline('~/.qlib/qlib_data/cn_data')
train, test= pipeline.prepare_data()
pipeline.train(train,time_limit=7200)
results= pipeline.evaluate(test)
print(results)
```

---

## 🎯 Tips para Mejorar Performance

1. Usar más datos históricos → Mejor generalización
2. Aumentar `time_limit` → AutoGluon explora más modelos
3. Habilitar feature engineering → `feature_generator='auto'`
4. Usar ensembles → `num_bag_folds=8`, `num_stack_levels=2`
5. Validación cruzada temporal → Evitar look-ahead bias

---

## 📚 Recursos Adicionales

- [Qlib Documentation](https://qlib.readthedocs.io/)
- [Alpha158 Handler Code](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py)
- [AutoGluon Tabular](https://auto.gluon.ai/stable/tutorials/tabular/index.html)
- [Qlib Benchmarks](https://github.com/microsoft/qlib/tree/main/examples/benchmarks)

¿Necesitas ayuda con alguna parte específica del pipeline o configuración?

# 🎯 Respuesta Corta: AutoGluon Tabular

Para Alpha154, debes usar AutoGluon Tabular, NO Time Series.

---

## 📊 ¿Por qué Tabular y NO Time Series?

| Característica | Alpha154 | Time Series Típico |
| --- | --- | --- |
| Formato | Tabla con 154 features ya engineered | Secuencia temporal cruda |
| Cada fila | Stock en fecha específica | Timestamp consecutivo |
| Temporalidad | Ya codificada en features (ROC, MA, STD) | Explícita en la secuencia |
| Independencia | Filas tratadas como independientes | Dependencia temporal entre rows |
| Predicción | Retorno futuro (regresión) | Forecast de valores futuros |

---

## 🔍 Análisis Detallado

### Alpha158/154 es Tabular Disfrazado

python

```
# Estructura típica de Alpha158:
# Index: (datetime, instrument)
# Columns: 158 features engineered + label

              CLOSE0  CLOSE1  ...  ROC5  ROC10  ...  LABEL0
datetime   instrument
2008-01-02 SH6000001.00.98  ...0.020.03   ...0.015
           SH6000041.00.99  ...-0.010.02   ...-0.008
2008-01-03 SH6000001.01.00  ...0.010.02   ...0.012
```

```
# Estructura típica de Alpha158:
# Index: (datetime, instrument)
# Columns: 158 features engineered + label

              CLOSE0  CLOSE1  ...  ROC5  ROC10  ...  LABEL0
datetime   instrument
2008-01-02 SH6000001.00.98  ...0.020.03   ...0.015
           SH6000041.00.99  ...-0.010.02   ...-0.008
2008-01-03 SH6000001.01.00  ...0.010.02   ...0.012
```

Las features YA capturan información temporal:

- `ROC5` = Rate of Change últimos 5 días
- `MA10` = Media móvil 10 días
- `STD20` = Desviación estándar 20 días
- `Ref($close, 1)` = Precio de cierre con 1 día de lag

👉 No necesitas AutoGluon Time Series porque la temporalidad ya está ingenierizada en las features.

---

## ✅ Código Correcto: AutoGluon Tabular

python

```
from autogluon.tabularimport TabularPredictor
import pandasas pd

# Datos Alpha154 (ya preprocessados desde Qlib)
train_data= pd.read_csv('alpha154_train.csv',index_col=[0,1])
test_data= pd.read_csv('alpha154_test.csv',index_col=[0,1])

# ✅ AutoGluon TABULAR
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',# o 'quantile' para distribución
path='alpha154_tabular_models/',
eval_metric='rmse'
).fit(
    train_data,
presets='best_quality',
time_limit=7200,
num_bag_folds=5,
num_stack_levels=2
)

# Evaluación
results= predictor.evaluate(test_data)
```

```
from autogluon.tabularimport TabularPredictor
import pandasas pd

# Datos Alpha154 (ya preprocessados desde Qlib)
train_data= pd.read_csv('alpha154_train.csv',index_col=[0,1])
test_data= pd.read_csv('alpha154_test.csv',index_col=[0,1])

# ✅ AutoGluon TABULAR
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',# o 'quantile' para distribución
path='alpha154_tabular_models/',
eval_metric='rmse'
).fit(
    train_data,
presets='best_quality',
time_limit=7200,
num_bag_folds=5,
num_stack_levels=2
)

# Evaluación
results= predictor.evaluate(test_data)
```

---

## ❌ Cuándo Usarías AutoGluon Time Series

python

```
from autogluon.timeseriesimport TimeSeriesPredictor

# Usarías esto si tuvieras datos CRUDOS como:
# Fecha, Precio, Volumen (sin features engineered)

datos_crudos= pd.DataFrame({
'timestamp': pd.date_range('2020-01-01',periods=100),
'item_id':'AAPL',
'close': [100,102,101,103, ...],
'volume': [1000000,1200000, ...]
})

# ✅ Esto SÍ requiere TimeSeriesPredictor
predictor_ts= TimeSeriesPredictor(prediction_length=5)
predictor_ts.fit(datos_crudos)
```

```
from autogluon.timeseriesimport TimeSeriesPredictor

# Usarías esto si tuvieras datos CRUDOS como:
# Fecha, Precio, Volumen (sin features engineered)

datos_crudos= pd.DataFrame({
'timestamp': pd.date_range('2020-01-01',periods=100),
'item_id':'AAPL',
'close': [100,102,101,103, ...],
'volume': [1000000,1200000, ...]
})

# ✅ Esto SÍ requiere TimeSeriesPredictor
predictor_ts= TimeSeriesPredictor(prediction_length=5)
predictor_ts.fit(datos_crudos)
```

---

## 📋 Comparación Directa

| Aspecto | AutoGluon Tabular | AutoGluon Time Series |
| --- | --- | --- |
| Alpha154 | ✅ RECOMENDADO | ❌ No necesario |
| Datos OHLCV crudos | ❌ Requiere feature engineering | ✅ Nativo |
| Forecasting multi-step | ❌ Limitado | ✅ Nativo |
| Features ya engineered | ✅ Óptimo | ⚠️ Overkill |
| Cross-sectional (stocks × date) | ✅ Diseñado para esto | ⚠️ No óptimo |
| Training speed | ✅ Más rápido | ❌ Más lento |
| Modelos disponibles | XGBoost, LightGBM, CatBoost, NN | DeepAR, Transformer, ARIMA |

---

## 🔄 Workflow Recomendado para Alpha154

python

```
import qlib
import pandasas pd
from autogluon.tabularimport TabularPredictor

# 1. Obtener datos desde Qlib (Alpha158 ≈ Alpha154)
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data',region=qlib.constant.REG_CN)

from qlib.contrib.data.handlerimport Alpha158
from qlib.data.datasetimport DatasetH

handler= Alpha158(
start_time='2008-01-01',
end_time='2020-08-01',
fit_start_time='2008-01-01',
fit_end_time='2014-12-31',
instruments='csi300',
)

dataset= DatasetH(
handler=handler,
segments={'train': ('2008-01-01','2016-12-31'),
'test': ('2017-01-01','2020-08-01')}
)

# 2. Extraer datos como DataFrame tabular
train_df= dataset.prepare('train',col_set=['feature','label'])
test_df= dataset.prepare('test',col_set=['feature','label'])

# Flatten multi-index si existe
train_df= train_df.droplevel('instrument')
test_df= test_df.droplevel('instrument')

# 3. ✅ AutoGluon TABULAR (NO Time Series)
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
path='alpha154_ag_tabular/',
eval_metric='rmse'
).fit(
    train_df,
presets='best_quality',
time_limit=7200,
# Importante: no hacer shuffle aleatorio en series temporales
shuffle=False
)

# 4. Evaluar
test_features= test_df.drop(columns=['LABEL0'])
test_labels= test_df['LABEL0']

predictions= predictor.predict(test_features)

# Métricas financieras
from sklearn.metricsimport mean_squared_error
import numpyas np

rmse= np.sqrt(mean_squared_error(test_labels, predictions))
ic= np.corrcoef(predictions, test_labels)[0,1]

print(f"RMSE:{rmse:.6f}")
print(f"IC (Information Coefficient):{ic:.4f}")
```

```
import qlib
import pandasas pd
from autogluon.tabularimport TabularPredictor

# 1. Obtener datos desde Qlib (Alpha158 ≈ Alpha154)
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data',region=qlib.constant.REG_CN)

from qlib.contrib.data.handlerimport Alpha158
from qlib.data.datasetimport DatasetH

handler= Alpha158(
start_time='2008-01-01',
end_time='2020-08-01',
fit_start_time='2008-01-01',
fit_end_time='2014-12-31',
instruments='csi300',
)

dataset= DatasetH(
handler=handler,
segments={'train': ('2008-01-01','2016-12-31'),
'test': ('2017-01-01','2020-08-01')}
)

# 2. Extraer datos como DataFrame tabular
train_df= dataset.prepare('train',col_set=['feature','label'])
test_df= dataset.prepare('test',col_set=['feature','label'])

# Flatten multi-index si existe
train_df= train_df.droplevel('instrument')
test_df= test_df.droplevel('instrument')

# 3. ✅ AutoGluon TABULAR (NO Time Series)
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
path='alpha154_ag_tabular/',
eval_metric='rmse'
).fit(
    train_df,
presets='best_quality',
time_limit=7200,
# Importante: no hacer shuffle aleatorio en series temporales
shuffle=False
)

# 4. Evaluar
test_features= test_df.drop(columns=['LABEL0'])
test_labels= test_df['LABEL0']

predictions= predictor.predict(test_features)

# Métricas financieras
from sklearn.metricsimport mean_squared_error
import numpyas np

rmse= np.sqrt(mean_squared_error(test_labels, predictions))
ic= np.corrcoef(predictions, test_labels)[0,1]

print(f"RMSE:{rmse:.6f}")
print(f"IC (Information Coefficient):{ic:.4f}")
```

---

## ⚠️ Consideración Especial: Validación Temporal

Aunque uses Tabular, debes respetar la estructura temporal:

python

```
# ✅ CORRECTO - Split temporal
train= data[data.index.get_level_values('datetime')<'2017-01-01']
test= data[data.index.get_level_values('datetime')>='2017-01-01']

# ❌ INCORRECTO - Split aleatorio (look-ahead bias)
from sklearn.model_selectionimport train_test_split
train, test= train_test_split(data,test_size=0.2,shuffle=True)# ¡NO!
```

```
# ✅ CORRECTO - Split temporal
train= data[data.index.get_level_values('datetime')<'2017-01-01']
test= data[data.index.get_level_values('datetime')>='2017-01-01']

# ❌ INCORRECTO - Split aleatorio (look-ahead bias)
from sklearn.model_selectionimport train_test_split
train, test= train_test_split(data,test_size=0.2,shuffle=True)# ¡NO!
```

En AutoGluon Tabular:

python

```
predictor.fit(
    train_data,
shuffle=False,# Importante para series temporales
num_bag_folds=5,# Bagging respeta el orden temporal
)
```

```
predictor.fit(
    train_data,
shuffle=False,# Importante para series temporales
num_bag_folds=5,# Bagging respeta el orden temporal
)
```

---

## 📊 Resumen Final

| Decisión | Recomendación |
| --- | --- |
| Módulo AutoGluon | `autogluon.tabular` |
| Problem Type | `regression` (o `quantile`) |
| Eval Metric | `rmse` o `mae` |
| Presets | `best_quality` o `high_quality` |
| Time Series? | ❌ No necesario para Alpha154 |

---

## 🎯 ¿Cuándo Considerar Time Series?

Solo si:

1. Tienes datos OHLCV crudos sin features engineered
2. Quieres hacer forecasting multi-step directo
3. Necesitas modelar dependencia temporal explícita entre timestamps

Para Alpha154 con sus 154 features ya calculadas → Tabular es la elección correcta.

¿Quieres que profundice en alguna configuración específica?

# 📊 Benchmark de Alpha158 en Mercado USA - Estado Actual

## 🚨 Respuesta Corta: NO hay benchmarks oficiales completos

Según la documentación oficial de Qlib, no existen benchmarks publicados oficialmente para Alpha158 en el mercado USA. Los benchmarks oficiales solo cubren:

| Mercado | Índice | Alpha158 | Alpha360 |
| --- | --- | --- | --- |
| China | CSI300 | ✅ Completo | ✅ Completo |
| China | CSI500 | ⚠️ Parcial | ⚠️ Parcial |
| USA | S&P 500 | ❌ No disponible | ❌ No disponible |
| USA | NASDAQ | ❌ No disponible | ❌ No disponible |

---

## 📋 Lo que Dice la Documentación Oficial

markdown

```
## Results on CSI500
The results on CSI500 is not complete. PR's for models on csi500 are welcome!

Transfer previous models in CSI300 to CSI500 is quite easy. You can try models
with just a few commands below.
```

```
## Results on CSI500
The results on CSI500 is not complete. PR's for models on csi500 are welcome!

Transfer previous models in CSI300 to CSI500 is quite easy. You can try models
with just a few commands below.
```

Traducción: Los resultados en CSI500 no están completos. ¡Las contribuciones para modelos en CSI500 son bienvenidas!

Esto indica que incluso para mercados chinos secundarios los benchmarks están incompletos, y para USA no hay nada oficial.

---

## 🔍 ¿Por qué No Hay Benchmarks USA?

### 1. Disponibilidad de Datos

python

```
# Datos oficiales de Qlib
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data',region=qlib.constant.REG_CN)# ✅ Disponible
qlib.init(provider_uri='~/.qlib/qlib_data/us_data',region=qlib.constant.REG_US)# ⚠️ Limitado
```

```
# Datos oficiales de Qlib
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data',region=qlib.constant.REG_CN)# ✅ Disponible
qlib.init(provider_uri='~/.qlib/qlib_data/us_data',region=qlib.constant.REG_US)# ⚠️ Limitado
```

- Los datos de USA requieren scraping de Yahoo Finance
- Menos estable que los datos chinos oficiales
- Problemas de calidad y consistencia

### 2. Diferencias de Mercado

| Característica | China A-Share | USA |
| --- | --- | --- |
| Límite precio diario | ±10% | Sin límite |
| Unidad trading | 100 acciones | 1 acción |
| Settlement | T+1 | T+2 |
| Short selling | Restringido | Permitido |
| Volatilidad | Alta | Variable |

### 3. Focus del Desarrollo

- Qlib fue desarrollado inicialmente por Microsoft Research Asia
- Primary focus en mercado chino
- Contribuciones de comunidad USA limitadas

---

## 📈 Benchmarks Existentes (Solo China)

### Alpha158 - CSI300 (Referencia)

| Modelo | IC | ICIR | Annualized Return | IR | Max Drawdown |
| --- | --- | --- | --- | --- | --- |
| DoubleEnsemble | 0.0521 | 0.4223 | 11.58% | 1.34 | -0.0920 |
| LightGBM | 0.0448 | 0.3660 | 9.01% | 1.02 | -0.1038 |
| XGBoost | 0.0498 | 0.3779 | 7.80% | 0.91 | -0.1168 |
| CatBoost | 0.0481 | 0.3366 | 7.65% | 0.80 | -0.1092 |
| MLP | 0.0376 | 0.2846 | 8.95% | 1.14 | -0.1103 |
| TRA | 0.0440 | 0.3535 | 7.18% | 1.08 | -0.0760 |

*20 runs con diferentes random seeds, periodo 2017-2020*

---

## 🛠️ Cómo Crear Tu Propio Benchmark USA

### Paso 1: Descargar Datos USA

bash

```
# Descargar datos US Stock en formato Qlib
python-mqlib.cli.dataqlib_data\
--target_dir~/.qlib/qlib_data/us_data\
--regionus
```

```
# Descargar datos US Stock en formato Qlib
python-mqlib.cli.dataqlib_data\
--target_dir~/.qlib/qlib_data/us_data\
--regionus
```

### Paso 2: Configurar Workflow para USA

yaml

```
# workflow_config_lightgbm_Alpha158_us.yaml
qlib_init:
provider_uri:"~/.qlib/qlib_data/us_data"
region:us# ← Cambiar a US

market: &marketsp500# o nasdaq, dowjones
benchmark: &benchmarkSPX

data_handler_config: &data_handler_config
start_time: 2010-01-01
end_time: 2023-12-31
fit_start_time: 2010-01-01
fit_end_time: 2018-12-31
instruments: *market

port_analysis_config: &port_analysis_config
strategy:
class:TopkDropoutStrategy
module_path:qlib.contrib.strategy
kwargs:
signal:<PRED>
topk:50
n_drop:5
backtest:
start_time: 2019-01-01
end_time: 2023-12-31
account:1000000
benchmark: *benchmark
exchange_kwargs:
limit_threshold:null# Sin límite en USA
deal_price:close
open_cost:0.001
close_cost:0.001
min_cost:1
```

```
# workflow_config_lightgbm_Alpha158_us.yaml
qlib_init:
provider_uri:"~/.qlib/qlib_data/us_data"
region:us# ← Cambiar a US

market: &marketsp500# o nasdaq, dowjones
benchmark: &benchmarkSPX

data_handler_config: &data_handler_config
start_time: 2010-01-01
end_time: 2023-12-31
fit_start_time: 2010-01-01
fit_end_time: 2018-12-31
instruments: *market

port_analysis_config: &port_analysis_config
strategy:
class:TopkDropoutStrategy
module_path:qlib.contrib.strategy
kwargs:
signal:<PRED>
topk:50
n_drop:5
backtest:
start_time: 2019-01-01
end_time: 2023-12-31
account:1000000
benchmark: *benchmark
exchange_kwargs:
limit_threshold:null# Sin límite en USA
deal_price:close
open_cost:0.001
close_cost:0.001
min_cost:1
```

### Paso 3: Ejecutar Benchmark

bash

```
# Ejecutar con qrun
qrunworkflow_config_lightgbm_Alpha158_us.yaml

# O para múltiples runs (20 seeds)
cdexamples/
pythonrun_all_model.pyrun20lightgbmAlpha158sp500
```

```
# Ejecutar con qrun
qrunworkflow_config_lightgbm_Alpha158_us.yaml

# O para múltiples runs (20 seeds)
cdexamples/
pythonrun_all_model.pyrun20lightgbmAlpha158sp500
```

### Paso 4: Código Python Directo

python

```
import qlib
import pandasas pd
from qlib.contrib.data.handlerimport Alpha158
from qlib.data.datasetimport DatasetH
from autogluon.tabularimport TabularPredictor

# 1. Inicializar Qlib para USA
qlib.init(
provider_uri='~/.qlib/qlib_data/us_data',
region=qlib.constant.REG_US
)

# 2. Cargar Alpha158
handler= Alpha158(
instruments='sp500',
start_time='2010-01-01',
end_time='2023-12-31',
fit_start_time='2010-01-01',
fit_end_time='2018-12-31',
)

# 3. Preparar dataset
dataset= DatasetH(
handler=handler,
segments={
'train': ('2010-01-01','2018-12-31'),
'valid': ('2019-01-01','2020-12-31'),
'test': ('2021-01-01','2023-12-31')
    }
)

# 4. Extraer datos
train_df= dataset.prepare('train',col_set=['feature','label'])
test_df= dataset.prepare('test',col_set=['feature','label'])

# 5. Entrenar con AutoGluon
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
path='alpha158_us_models/',
eval_metric='rmse'
).fit(
    train_df,
presets='best_quality',
time_limit=7200
)

# 6. Evaluar
results= predictor.evaluate(test_df)
print(f"USA Benchmark Results:{results}")

# 7. Métricas financieras
from sklearn.metricsimport mean_squared_error
import numpyas np

y_true= test_df['LABEL0'].values
y_pred= predictor.predict(test_df.drop(columns=['LABEL0']))

ic= np.corrcoef(y_pred, y_true)[0,1]
rmse= np.sqrt(mean_squared_error(y_true, y_pred))

print(f"IC (Information Coefficient):{ic:.4f}")
print(f"RMSE:{rmse:.6f}")
```

```
import qlib
import pandasas pd
from qlib.contrib.data.handlerimport Alpha158
from qlib.data.datasetimport DatasetH
from autogluon.tabularimport TabularPredictor

# 1. Inicializar Qlib para USA
qlib.init(
provider_uri='~/.qlib/qlib_data/us_data',
region=qlib.constant.REG_US
)

# 2. Cargar Alpha158
handler= Alpha158(
instruments='sp500',
start_time='2010-01-01',
end_time='2023-12-31',
fit_start_time='2010-01-01',
fit_end_time='2018-12-31',
)

# 3. Preparar dataset
dataset= DatasetH(
handler=handler,
segments={
'train': ('2010-01-01','2018-12-31'),
'valid': ('2019-01-01','2020-12-31'),
'test': ('2021-01-01','2023-12-31')
    }
)

# 4. Extraer datos
train_df= dataset.prepare('train',col_set=['feature','label'])
test_df= dataset.prepare('test',col_set=['feature','label'])

# 5. Entrenar con AutoGluon
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
path='alpha158_us_models/',
eval_metric='rmse'
).fit(
    train_df,
presets='best_quality',
time_limit=7200
)

# 6. Evaluar
results= predictor.evaluate(test_df)
print(f"USA Benchmark Results:{results}")

# 7. Métricas financieras
from sklearn.metricsimport mean_squared_error
import numpyas np

y_true= test_df['LABEL0'].values
y_pred= predictor.predict(test_df.drop(columns=['LABEL0']))

ic= np.corrcoef(y_pred, y_true)[0,1]
rmse= np.sqrt(mean_squared_error(y_true, y_pred))

print(f"IC (Information Coefficient):{ic:.4f}")
print(f"RMSE:{rmse:.6f}")
```

---

## 📊 Expectativas Realistas para USA

Basado en literatura académica y diferencias de mercado:

| Métrica | China CSI300 | USA S&P 500 (Estimado) | Razón |
| --- | --- | --- | --- |
| IC | 0.045-0.052 | 0.025-0.035 | Mercado USA más eficiente |
| ICIR | 0.35-0.42 | 0.20-0.30 | Menos alpha disponible |
| Annual Return | 9-12% | 5-8% | Menos ineficiencias |
| Max Drawdown | -8% a -12% | -10% a -15% | Sin límites de precio |
| Sharpe Ratio | 1.0-1.3 | 0.7-1.0 | Mayor competencia |

---

## 🔬 Papers/Recursos Relacionados

### 1. Estudios Académicos con Datos USA

- *"Deep Learning in Asset Pricing"* (Gu, Kelly, Xiu, 2020) - USA market
- *"Machine Learning in Finance"* (Dixon, 2020) - Incluye benchmarks USA
- *"Alpha158: 158 Quantitative Factors"* - Solo China oficialmente

### 2. Repositorios de Comunidad

bash

```
# Algunos repositorios de comunidad con USA data:
gitclonehttps://github.com/your-username/qlib-usa-benchmark
gitclonehttps://github.com/quant-research/alpha158-sp500
```

```
# Algunos repositorios de comunidad con USA data:
gitclonehttps://github.com/your-username/qlib-usa-benchmark
gitclonehttps://github.com/quant-research/alpha158-sp500
```

### 3. Datasets Alternativos para USA

| Dataset | Provider | Costo | Calidad |
| --- | --- | --- | --- |
| Alpha158 | Qlib (Yahoo) | Gratis | ⚠️ Media |
| WRDS | Wharton | Pago | ✅ Alta |
| Quandl | NASDAQ | Freemium | ✅ Alta |
| Polygon.io | Polygon | Pago | ✅ Alta |
| Alpha Vantage | Alpha Vantage | Freemium | ⚠️ Media |

---

## 💡 Recomendaciones

### Si Quieres Benchmark USA:

1. Opción Rápida: Usa benchmarks de China como referencia, espera 30-50% menos performance en USA
2. Opción Intermedia: Crea tu propio benchmark con datos de Yahoo Finance vía Qlib
3. Opción Profesional: Usa datos premium (WRDS, Bloomberg) con Qlib customizado

### Para Publicación/Investigación:

python

```
# Documenta claramente:
benchmark_config= {
'market':'US_S&P500',
'data_source':'Yahoo Finance via Qlib',
'period':'2010-2023',
'train_end':'2018-12-31',
'test_start':'2021-01-01',
'rebalancing':'daily',
'transaction_costs':'0.1%',
'universe':'SP500 constituents (time-varying)'
}
```

```
# Documenta claramente:
benchmark_config= {
'market':'US_S&P500',
'data_source':'Yahoo Finance via Qlib',
'period':'2010-2023',
'train_end':'2018-12-31',
'test_start':'2021-01-01',
'rebalancing':'daily',
'transaction_costs':'0.1%',
'universe':'SP500 constituents (time-varying)'
}
```

---

## 📝 Conclusión

| Pregunta | Respuesta |
| --- | --- |
| ¿Hay benchmarks oficiales USA? | ❌ No |
| ¿Se puede crear uno propio? | ✅ Sí, con Qlib + datos USA |
| ¿Performance esperada? | ~50-70% de los benchmarks China |
| ¿Recomendado para producción? | ⚠️ Validar con datos premium |
| ¿Vale para investigación? | ✅ Sí, documentando limitaciones |

¿Quieres que te ayude a configurar un benchmark USA personalizado con AutoGluon? 🚀

# 🤖 Modelos que AutoGluon Probaría con Alpha154/158

Cuando usas AutoGluon Tabular, automáticamente entrena y compara múltiples modelos de diferentes familias. Aquí te detallo exactamente qué modelos probaría:

---

## 📋 Modelos Default (Configuración Estándar)

### Con `presets='medium'` (Default)

python

```
predictor= TabularPredictor(label='LABEL0').fit(train_data)
```

```
predictor= TabularPredictor(label='LABEL0').fit(train_data)
```

| Familia | Modelos Específicos | Cantidad |
| --- | --- | --- |
| Neural Networks | `NeuralNetFastAI`, `NeuralNetTorch` | 2 |
| Gradient Boosting | `LightGBM`, `LightGBMXT`, `LightGBMLarge` | 3 |
| Random Forest | `RandomForestGini`, `RandomForestEntr` | 2 |
| Extra Trees | `ExtraTreesGini`, `ExtraTreesEntr` | 2 |
| XGBoost | `XGBoost` | 1 |
| CatBoost | `CatBoost` | 1 |
| K-Nearest Neighbors | `KNeighborsUnif`, `KNeighborsDist` | 2 |
| Ensemble | `WeightedEnsemble_L2` | 1 |

Total: ~15 modelos (varía según versión de AutoGluon)

---

## 🚀 Con `presets='best_quality'` (Recomendado)

python

```
predictor= TabularPredictor(
label='LABEL0',
eval_metric='rmse'
).fit(
    train_data,
presets='best_quality',
time_limit=7200
)
```

```
predictor= TabularPredictor(
label='LABEL0',
eval_metric='rmse'
).fit(
    train_data,
presets='best_quality',
time_limit=7200
)
```

| Familia | Modelos | Características |
| --- | --- | --- |
| Neural Networks | `NeuralNetFastAI`, `NeuralNetTorch` | Con hyperparameter tuning |
| LightGBM | `LightGBM`, `LightGBMXT`, `LightGBMLarge` | Diferentes configuraciones |
| XGBoost | `XGBoost` | Con tuning automático |
| CatBoost | `CatBoost` | Manejo nativo de categóricas |
| Random Forest | 3 variantes | Gini, Entropy, MSE |
| Extra Trees | 3 variantes | Gini, Entropy, MSE |
| KNN | 2 variantes | Uniforme, Distance-weighted |
| TabPFN | `TabPFN` | ⭐ Foundation model (si está disponible) |
| Ensemble | `WeightedEnsemble_L2`, `WeightedEnsemble_L3` | Multi-level stacking |

Total: ~20-25 modelos + ensembles

---

## 🔥 Con `presets='extreme'` (Máxima Calidad)

python

```
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
presets='extreme',
time_limit=14400
)
```

```
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
presets='extreme',
time_limit=14400
)
```

Incluye todo lo anterior MÁS:

| Modelo Nuevo | Tipo | Requiere |
| --- | --- | --- |
| `TabPFNv2` | Foundation Model | GPU recomendada |
| `TabICL` | In-Context Learning | GPU |
| `Mitra` | Meta-learned | GPU |
| `TabM` | Ensemble eficiente | - |

Total: ~30+ modelos

---

## 📊 Detalle de Cada Familia para Alpha154

### 1. Gradient Boosting (Los Más Importantes)

python

```
# LightGBM variants que AutoGluon prueba:
LightGBM: {
'num_leaves': [31,128,256],
'learning_rate': [0.03,0.1,0.2],
'feature_fraction': [0.8,0.9,1.0],
'min_data_in_leaf': [3,10,20],
'max_depth': [8,15,-1]
}

# XGBoost
XGBoost: {
'max_depth': [3,6,9],
'learning_rate': [0.01,0.1,0.3],
'n_estimators': [100,500,1000],
'subsample': [0.8,1.0],
'colsample_bytree': [0.8,1.0]
}

# CatBoost
CatBoost: {
'depth': [4,6,8,10],
'learning_rate': [0.01,0.1,0.3],
'l2_leaf_reg': [1,3,5],
'border_count': [32,254]
}
```

```
# LightGBM variants que AutoGluon prueba:
LightGBM: {
'num_leaves': [31,128,256],
'learning_rate': [0.03,0.1,0.2],
'feature_fraction': [0.8,0.9,1.0],
'min_data_in_leaf': [3,10,20],
'max_depth': [8,15,-1]
}

# XGBoost
XGBoost: {
'max_depth': [3,6,9],
'learning_rate': [0.01,0.1,0.3],
'n_estimators': [100,500,1000],
'subsample': [0.8,1.0],
'colsample_bytree': [0.8,1.0]
}

# CatBoost
CatBoost: {
'depth': [4,6,8,10],
'learning_rate': [0.01,0.1,0.3],
'l2_leaf_reg': [1,3,5],
'border_count': [32,254]
}
```

Para Alpha154: Estos suelen ser los TOP performers 🏆

---

### 2. Neural Networks

python

```
NeuralNetTorch: {
'layers': [[256], [512], [256,128], [512,256,128]],
'activation': ['ReLU','Tanh','GELU'],
'dropout': [0.0,0.1,0.2,0.3],
'learning_rate': [0.001,0.01,0.1],
'weight_decay': [0.0,0.0001,0.001],
'batch_size': [256,512,1024],
'epochs': [50,100,200]
}

NeuralNetFastAI: {
'layers': [[200], [400], [200,100]],
'emb_drop': [0.0,0.04],
'drop_out': [0.0,0.1],
'batch_norm': [True,False]
}
```

```
NeuralNetTorch: {
'layers': [[256], [512], [256,128], [512,256,128]],
'activation': ['ReLU','Tanh','GELU'],
'dropout': [0.0,0.1,0.2,0.3],
'learning_rate': [0.001,0.01,0.1],
'weight_decay': [0.0,0.0001,0.001],
'batch_size': [256,512,1024],
'epochs': [50,100,200]
}

NeuralNetFastAI: {
'layers': [[200], [400], [200,100]],
'emb_drop': [0.0,0.04],
'drop_out': [0.0,0.1],
'batch_norm': [True,False]
}
```

Para Alpha154: Performance variable, dependen de normalización

---

### 3. Tree-Based Ensembles

python

```
RandomForest: {
'n_estimators': [100,300],
'max_depth': [15,20,None],
'min_samples_split': [2,5,10],
'min_samples_leaf': [1,2,4],
'criterion': ['gini','entropy','log_loss']
}

ExtraTrees: {
# Similar a RandomForest pero con más aleatoriedad
'bootstrap': [True,False],
'criterion': ['gini','entropy']
}
```

```
RandomForest: {
'n_estimators': [100,300],
'max_depth': [15,20,None],
'min_samples_split': [2,5,10],
'min_samples_leaf': [1,2,4],
'criterion': ['gini','entropy','log_loss']
}

ExtraTrees: {
# Similar a RandomForest pero con más aleatoriedad
'bootstrap': [True,False],
'criterion': ['gini','entropy']
}
```

Para Alpha154: Buenos baselines, rápidos de entrenar

---

### 4. K-Nearest Neighbors

python

```
KNeighbors: {
'n_neighbors': [3,5,10,20,50],
'weights': ['uniform','distance'],
'metric': ['euclidean','manhattan','cosine']
}
```

```
KNeighbors: {
'n_neighbors': [3,5,10,20,50],
'weights': ['uniform','distance'],
'metric': ['euclidean','manhattan','cosine']
}
```

Para Alpha154: Generalmente low performance pero AutoGluon los incluye como baseline

---

### 5. Foundation Models (AutoGluon v1.0+)

python

```
TabPFN: {
# No requiere tuning - usa modelo pre-entrenado
'inference_mode':'fast',# o 'accurate'
'batch_size':1024
}

TabICL: {
# In-Context Learning
'context_size':100,
'num_iterations':5
}
```

```
TabPFN: {
# No requiere tuning - usa modelo pre-entrenado
'inference_mode':'fast',# o 'accurate'
'batch_size':1024
}

TabICL: {
# In-Context Learning
'context_size':100,
'num_iterations':5
}
```

Para Alpha154: ⭐ Excelente para datasets pequeños (< 10K samples)

---

## 🏆 Leaderboard Típico para Alpha154

Basado en benchmarks similares, este sería el ranking esperado:

| Rank | Modelo | IC Esperado | Tiempo Train |
| --- | --- | --- | --- |
| 1 | WeightedEnsemble_L2 | 0.045-0.055 | 2-4 horas |
| 2 | LightGBM | 0.040-0.050 | 10-30 min |
| 3 | XGBoost | 0.038-0.048 | 15-45 min |
| 4 | CatBoost | 0.037-0.047 | 30-60 min |
| 5 | TabPFN | 0.035-0.045 | 1-5 min ⚡ |
| 6 | NeuralNetTorch | 0.030-0.040 | 30-90 min |
| 7 | RandomForest | 0.028-0.038 | 5-15 min |
| 8 | ExtraTrees | 0.027-0.037 | 5-15 min |
| 9 | KNN | 0.015-0.025 | 1-5 min |

---

## 🔧 Cómo Ver los Modelos que AutoGluon Entrena

python

```
from autogluon.tabularimport TabularPredictor

predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
presets='best_quality',
verbosity=3# ← Muestra detalle de cada modelo
)

# Ver todos los modelos entrenados
predictor.leaderboard()

# Ver detalle de un modelo específico
predictor.get_model_best()

# Ver feature importance por modelo
predictor.feature_importance(test_data,model='LightGBM')
```

```
from autogluon.tabularimport TabularPredictor

predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
presets='best_quality',
verbosity=3# ← Muestra detalle de cada modelo
)

# Ver todos los modelos entrenados
predictor.leaderboard()

# Ver detalle de un modelo específico
predictor.get_model_best()

# Ver feature importance por modelo
predictor.feature_importance(test_data,model='LightGBM')
```

---

## ⚙️ Configuración Personalizada de Modelos

Si quieres controlar exactamente qué modelos probar:

python

```
# Opción 1: Especificar modelos explícitamente
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
hyperparameters={
'LightGBM': [
            {},# default
            {'num_leaves':128,'max_depth':15}# custom
        ],
'XGBoost': {},
'CatBoost': {},
'NeuralNetTorch': {
'activation':'relu',
'dropout_prob':0.1
        },
'RandomForest': {
'n_estimators':300,
'max_depth':20
        }
    },
time_limit=3600
)

# Opción 2: Excluir modelos específicos
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
hyperparameters='default',
excluded_model_types=['KNN','NeuralNetFastAI']# ← Excluir estos
)

# Opción 3: Priorizar ciertos modelos
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
hyperparameters={
'LightGBM': {},# Primero (más tiempo)
'XGBoost': {},
'CatBoost': {},
    },
time_limit=7200
)
```

```
# Opción 1: Especificar modelos explícitamente
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
hyperparameters={
'LightGBM': [
            {},# default
            {'num_leaves':128,'max_depth':15}# custom
        ],
'XGBoost': {},
'CatBoost': {},
'NeuralNetTorch': {
'activation':'relu',
'dropout_prob':0.1
        },
'RandomForest': {
'n_estimators':300,
'max_depth':20
        }
    },
time_limit=3600
)

# Opción 2: Excluir modelos específicos
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
hyperparameters='default',
excluded_model_types=['KNN','NeuralNetFastAI']# ← Excluir estos
)

# Opción 3: Priorizar ciertos modelos
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
hyperparameters={
'LightGBM': {},# Primero (más tiempo)
'XGBoost': {},
'CatBoost': {},
    },
time_limit=7200
)
```

---

## 📈 Hyperparameter Tuning Automático

AutoGluon hace tuning automático si especificas:

python

```
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
presets='best_quality',
hyperparameter_tune_kwargs='auto',# ← Auto-tuning
num_bag_folds=5,# ← Bagging
num_stack_levels=2# ← Stacking
)
```

```
predictor= TabularPredictor(label='LABEL0').fit(
    train_data,
presets='best_quality',
hyperparameter_tune_kwargs='auto',# ← Auto-tuning
num_bag_folds=5,# ← Bagging
num_stack_levels=2# ← Stacking
)
```

Lo que hace AutoGluon:

1. Bayesian Optimization para hyperparameters
2. Early Stopping para modelos iterativos
3. Ensemble Selection para combinar mejores modelos
4. Stacking multi-nivel para mejorar predictions

---

## 💡 Recomendaciones para Alpha154

### Configuración Óptima:

python

```
from autogluon.tabularimport TabularPredictor

predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
path='alpha154_autogluon/',
eval_metric='rmse'
).fit(
    train_data,
presets='best_quality',
time_limit=7200,# 2 horas
num_bag_folds=5,
num_stack_levels=2,
excluded_model_types=['KNN'],# KNN no funciona bien con 154 features
verbosity=2
)
```

```
from autogluon.tabularimport TabularPredictor

predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
path='alpha154_autogluon/',
eval_metric='rmse'
).fit(
    train_data,
presets='best_quality',
time_limit=7200,# 2 horas
num_bag_folds=5,
num_stack_levels=2,
excluded_model_types=['KNN'],# KNN no funciona bien con 154 features
verbosity=2
)
```

### Si Tienes GPU:

python

```
predictor= TabularPredictor(
label='LABEL0',
path='alpha154_gpu/'
).fit(
    train_data,
presets='extreme',# ← Incluye TabPFNv2, TabICL
time_limit=14400,
num_gpus=1
)
```

```
predictor= TabularPredictor(
label='LABEL0',
path='alpha154_gpu/'
).fit(
    train_data,
presets='extreme',# ← Incluye TabPFNv2, TabICL
time_limit=14400,
num_gpus=1
)
```

### Si Tienes Poco Tiempo:

python

```
predictor= TabularPredictor(
label='LABEL0',
path='alpha154_fast/'
).fit(
    train_data,
presets='high_quality',# ← Más rápido que best_quality
time_limit=1800# 30 minutos
)
```

```
predictor= TabularPredictor(
label='LABEL0',
path='alpha154_fast/'
).fit(
    train_data,
presets='high_quality',# ← Más rápido que best_quality
time_limit=1800# 30 minutos
)
```

---

## 📊 Resumen Visual

```
┌─────────────────────────────────────────────────────────┐
│           AUTOGLUON MODEL ZOO PARA ALPHA154             │
├─────────────────────────────────────────────────────────┤
│  🏆 TOP TIER (Mejor Performance)                        │
│     • LightGBM (variants: XT, Large)                    │
│     • XGBoost                                           │
│     • CatBoost                                          │
│     • WeightedEnsemble (combina todos)                  │
├─────────────────────────────────────────────────────────┤
│  🥈 MID TIER (Buena Performance)                        │
│     • NeuralNetTorch                                    │
│     • TabPFN (si disponible)                            │
│     • RandomForest                                      │
│     • ExtraTrees                                        │
├─────────────────────────────────────────────────────────┤
│  🥉 BASELINE (Rápidos pero menor performance)           │
│     • NeuralNetFastAI                                   │
│     • KNN                                               │
└─────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────┐
│           AUTOGLUON MODEL ZOO PARA ALPHA154             │
├─────────────────────────────────────────────────────────┤
│  🏆 TOP TIER (Mejor Performance)                        │
│     • LightGBM (variants: XT, Large)                    │
│     • XGBoost                                           │
│     • CatBoost                                          │
│     • WeightedEnsemble (combina todos)                  │
├─────────────────────────────────────────────────────────┤
│  🥈 MID TIER (Buena Performance)                        │
│     • NeuralNetTorch                                    │
│     • TabPFN (si disponible)                            │
│     • RandomForest                                      │
│     • ExtraTrees                                        │
├─────────────────────────────────────────────────────────┤
│  🥉 BASELINE (Rápidos pero menor performance)           │
│     • NeuralNetFastAI                                   │
│     • KNN                                               │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Mi Recomendación Personal

Para Alpha154 con AutoGluon, usa esta configuración:

python

```
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
eval_metric='rmse',
path='alpha154_final/'
).fit(
    train_data,
presets='best_quality',
time_limit=7200,
num_bag_folds=5,
num_stack_levels=2,
excluded_model_types=['KNN'],
verbosity=2
)

# Después de entrenar:
print(f"Best model:{predictor.get_model_best()}")
predictor.leaderboard(silent=True)
```

```
predictor= TabularPredictor(
label='LABEL0',
problem_type='regression',
eval_metric='rmse',
path='alpha154_final/'
).fit(
    train_data,
presets='best_quality',
time_limit=7200,
num_bag_folds=5,
num_stack_levels=2,
excluded_model_types=['KNN'],
verbosity=2
)

# Después de entrenar:
print(f"Best model:{predictor.get_model_best()}")
predictor.leaderboard(silent=True)
```

¿Quieres que profundice en algún modelo específico o en cómo interpretar los resultados? 🚀

# 🚀 Guía Completa: Benchmark USA Personalizado con AutoGluon + Alpha158

Te ayudo a configurar un benchmark completo paso a paso. Esta guía incluye todo el código necesario.

---

## 📋 Estructura del Proyecto

```
alpha158_usa_benchmark/
├── data/
│   └── (datos descargados de Qlib)
├── configs/
│   ├── workflow_config.yaml
│   └── autogluon_config.py
├── scripts/
│   ├── 01_download_data.py
│   ├── 02_prepare_dataset.py
│   ├── 03_train_autogluon.py
│   ├── 04_evaluate.py
│   └── 05_generate_report.py
├── results/
│   ├── models/
│   ├── predictions/
│   └── reports/
├── utils/
│   ├── metrics.py
│   └── helpers.py
└── README.md
```

```
alpha158_usa_benchmark/
├── data/
│   └── (datos descargados de Qlib)
├── configs/
│   ├── workflow_config.yaml
│   └── autogluon_config.py
├── scripts/
│   ├── 01_download_data.py
│   ├── 02_prepare_dataset.py
│   ├── 03_train_autogluon.py
│   ├── 04_evaluate.py
│   └── 05_generate_report.py
├── results/
│   ├── models/
│   ├── predictions/
│   └── reports/
├── utils/
│   ├── metrics.py
│   └── helpers.py
└── README.md
```

---

## 📦 Paso 1: Instalación de Dependencias

bash

```
# Crear entorno virtual
python-mvenvqlib_autogluon
sourceqlib_autogluon/bin/activate# Linux/Mac
# o: qlib_autogluon\Scripts\activate  # Windows

# Instalar Qlib
pipinstallpyqlib

# Instalar AutoGluon
pipinstallautogluon.tabular[all]

# Instalar dependencias adicionales
pipinstallpandasnumpyscikit-learnmatplotlibseabornplotly
pipinstallyfinancetqdmjoblibipywidgets

# Verificar instalación
python-c"import qlib; import autogluon; print('✅ Todo instalado correctamente')"
```

```
# Crear entorno virtual
python-mvenvqlib_autogluon
sourceqlib_autogluon/bin/activate# Linux/Mac
# o: qlib_autogluon\Scripts\activate  # Windows

# Instalar Qlib
pipinstallpyqlib

# Instalar AutoGluon
pipinstallautogluon.tabular[all]

# Instalar dependencias adicionales
pipinstallpandasnumpyscikit-learnmatplotlibseabornplotly
pipinstallyfinancetqdmjoblibipywidgets

# Verificar instalación
python-c"import qlib; import autogluon; print('✅ Todo instalado correctamente')"
```

---

## 📥 Paso 2: Descargar Datos USA

### Script: `scripts/01_download_data.py`

python

```
#!/usr/bin/env python3
"""
Descargar datos de mercado USA para Qlib
"""

import os
import sys
from pathlibimport Path

defdownload_qlib_data_us(target_dir: str="~/.qlib/qlib_data/us_data"):
"""
    Descargar datos de mercado USA desde Yahoo Finance
"""
    target_dir= os.path.expanduser(target_dir)

print("="*60)
print("📥 Descargando datos de mercado USA para Qlib")
print("="*60)

# Crear directorio
    Path(target_dir).mkdir(parents=True,exist_ok=True)

# Método 1: Usando el script oficial de Qlib
print("\n🔄 Intentando descargar con script oficial de Qlib...")

try:
import qlib
from qlib.tests.dataimport GetData

# Descargar datos
        GetData().qlib_data(
target_dir=target_dir,
region='us',
exists_skip=True
        )
print("✅ Datos descargados exitosamente")
returnTrue

except Exceptionas e:
print(f"⚠️ Error con método oficial:{e}")
print("\n📝 Alternativa: Descargar manualmente desde:")
print("   https://github.com/chenditc/investment_data/releases")
print("\n   O usar datos de Yahoo Finance directamente:")
print("   python scripts/data_collector/yahoo/collector.py")
returnFalse

defverify_data(data_dir: str):
"""Verificar que los datos se descargaron correctamente"""
print("\n🔍 Verificando integridad de datos...")

    required_files= [
'calendars/day.txt',
'instruments/sp500.txt',
'features/sh600000/close.day.bin'# Ejemplo
    ]

forfilein required_files:
        path= os.path.join(data_dir,file)
if os.path.exists(path):
print(f"  ✅{file}")
else:
print(f"  ❌{file} (faltante)")

print("\n"+"="*60)

if__name__=="__main__":
    target= sys.argv[1]iflen(sys.argv)>1else"~/.qlib/qlib_data/us_data"
    success= download_qlib_data_us(target)
if success:
        verify_data(os.path.expanduser(target))
```

```
#!/usr/bin/env python3
"""
Descargar datos de mercado USA para Qlib
"""

import os
import sys
from pathlibimport Path

defdownload_qlib_data_us(target_dir: str="~/.qlib/qlib_data/us_data"):
"""
    Descargar datos de mercado USA desde Yahoo Finance
"""
    target_dir= os.path.expanduser(target_dir)

print("="*60)
print("📥 Descargando datos de mercado USA para Qlib")
print("="*60)

# Crear directorio
    Path(target_dir).mkdir(parents=True,exist_ok=True)

# Método 1: Usando el script oficial de Qlib
print("\n🔄 Intentando descargar con script oficial de Qlib...")

try:
import qlib
from qlib.tests.dataimport GetData

# Descargar datos
        GetData().qlib_data(
target_dir=target_dir,
region='us',
exists_skip=True
        )
print("✅ Datos descargados exitosamente")
returnTrue

except Exceptionas e:
print(f"⚠️ Error con método oficial:{e}")
print("\n📝 Alternativa: Descargar manualmente desde:")
print("   https://github.com/chenditc/investment_data/releases")
print("\n   O usar datos de Yahoo Finance directamente:")
print("   python scripts/data_collector/yahoo/collector.py")
returnFalse

defverify_data(data_dir: str):
"""Verificar que los datos se descargaron correctamente"""
print("\n🔍 Verificando integridad de datos...")

    required_files= [
'calendars/day.txt',
'instruments/sp500.txt',
'features/sh600000/close.day.bin'# Ejemplo
    ]

forfilein required_files:
        path= os.path.join(data_dir,file)
if os.path.exists(path):
print(f"  ✅{file}")
else:
print(f"  ❌{file} (faltante)")

print("\n"+"="*60)

if__name__=="__main__":
    target= sys.argv[1]iflen(sys.argv)>1else"~/.qlib/qlib_data/us_data"
    success= download_qlib_data_us(target)
if success:
        verify_data(os.path.expanduser(target))
```

### Ejecutar:

bash

```
pythonscripts/01_download_data.py
```

```
pythonscripts/01_download_data.py
```

---

## 📊 Paso 3: Preparar Dataset Alpha158 para USA

### Script: `scripts/02_prepare_dataset.py`

python

```
#!/usr/bin/env python3
"""
Preparar dataset Alpha158 para mercado USA
"""

import os
import sys
import pandasas pd
import numpyas np
from datetimeimport datetime
import qlib
from qlib.contrib.data.handlerimport Alpha158
from qlib.data.datasetimport DatasetH
from qlib.constantimport REG_US

classAlpha158USAPreparator:
def__init__(
self,
data_dir: str="~/.qlib/qlib_data/us_data",
instruments: str="sp500",
start_time: str="2010-01-01",
end_time: str="2023-12-31",
train_end: str="2018-12-31",
test_start: str="2019-01-01"
    ):
self.data_dir= os.path.expanduser(data_dir)
self.instruments= instruments
self.start_time= start_time
self.end_time= end_time
self.train_end= train_end
self.test_start= test_start

definitialize_qlib(self):
"""Inicializar Qlib con datos USA"""
print("🔧 Inicializando Qlib para mercado USA...")
        qlib.init(
provider_uri=self.data_dir,
region=REG_US
        )
print("✅ Qlib inicializado correctamente")

defload_alpha158(self):
"""Cargar dataset Alpha158"""
print("\n📊 Cargando dataset Alpha158...")

self.handler= Alpha158(
instruments=self.instruments,
start_time=self.start_time,
end_time=self.end_time,
fit_start_time=self.start_time,
fit_end_time=self.train_end,
freq="day",
        )

print(f"  📈 Instrumentos:{self.instruments}")
print(f"  📅 Periodo:{self.start_time} a{self.end_time}")

defprepare_dataset(self):
"""Preparar train/test split"""
print("\n🔪 Preparando splits de train/test...")

self.dataset= DatasetH(
handler=self.handler,
segments={
"train": (self.start_time,self.train_end),
"valid": (self.train_end,self.test_start),
"test": (self.test_start,self.end_time)
            }
        )

# Extraer datos
print("  📥 Extrayendo datos de entrenamiento...")
self.train_df=self.dataset.prepare("train",col_set=["feature","label"])

print("  📥 Extrayendo datos de test...")
self.test_df=self.dataset.prepare("test",col_set=["feature","label"])

# Procesar multi-index
self.train_df=self._process_multiindex(self.train_df)
self.test_df=self._process_multiindex(self.test_df)

# Eliminar NaN
self.train_df=self.train_df.dropna()
self.test_df=self.test_df.dropna()

print(f"\n  ✅ Train samples:{len(self.train_df):,}")
print(f"  ✅ Test samples:{len(self.test_df):,}")
print(f"  ✅ Features:{self.train_df.shape[1]-1}")

def_process_multiindex(self,df: pd.DataFrame) -> pd.DataFrame:
"""Procesar multi-index de Qlib"""
ifisinstance(df.index, pd.MultiIndex):
            df= df.reset_index()
            df= df.set_index('datetime')
            df= df.drop(columns=['instrument'])
return df

defsave_dataset(self,output_dir: str="data/processed"):
"""Guardar dataset procesado"""
print("\n💾 Guardando dataset procesado...")

        os.makedirs(output_dir,exist_ok=True)

# Guardar como CSV
self.train_df.to_csv(f"{output_dir}/alpha158_usa_train.csv")
self.test_df.to_csv(f"{output_dir}/alpha158_usa_test.csv")

# Guardar metadata
        metadata= {
'instruments':self.instruments,
'start_time':self.start_time,
'end_time':self.end_time,
'train_end':self.train_end,
'test_start':self.test_start,
'n_features':self.train_df.shape[1]-1,
'n_train_samples':len(self.train_df),
'n_test_samples':len(self.test_df),
'feature_columns': list(self.train_df.columns.drop('LABEL0')),
'created_at': datetime.now().isoformat()
        }

import json
withopen(f"{output_dir}/metadata.json",'w')as f:
            json.dump(metadata, f,indent=2)

print(f"  ✅ Datos guardados en:{output_dir}/")

defrun(self):
"""Ejecutar todo el pipeline"""
print("="*60)
print("🚀 Preparando Dataset Alpha158 USA")
print("="*60)

self.initialize_qlib()
self.load_alpha158()
self.prepare_dataset()
self.save_dataset()

print("\n"+"="*60)
print("✅ Dataset preparado exitosamente!")
print("="*60)

returnself.train_df,self.test_df

if__name__=="__main__":
    preparator= Alpha158USAPreparator(
data_dir="~/.qlib/qlib_data/us_data",
instruments="sp500",
start_time="2010-01-01",
end_time="2023-12-31",
train_end="2018-12-31",
test_start="2019-01-01"
    )

    train_df, test_df= preparator.run()
```

```
#!/usr/bin/env python3
"""
Preparar dataset Alpha158 para mercado USA
"""

import os
import sys
import pandasas pd
import numpyas np
from datetimeimport datetime
import qlib
from qlib.contrib.data.handlerimport Alpha158
from qlib.data.datasetimport DatasetH
from qlib.constantimport REG_US

classAlpha158USAPreparator:
def__init__(
self,
data_dir: str="~/.qlib/qlib_data/us_data",
instruments: str="sp500",
start_time: str="2010-01-01",
end_time: str="2023-12-31",
train_end: str="2018-12-31",
test_start: str="2019-01-01"
    ):
self.data_dir= os.path.expanduser(data_dir)
self.instruments= instruments
self.start_time= start_time
self.end_time= end_time
self.train_end= train_end
self.test_start= test_start

definitialize_qlib(self):
"""Inicializar Qlib con datos USA"""
print("🔧 Inicializando Qlib para mercado USA...")
        qlib.init(
provider_uri=self.data_dir,
region=REG_US
        )
print("✅ Qlib inicializado correctamente")

defload_alpha158(self):
"""Cargar dataset Alpha158"""
print("\n📊 Cargando dataset Alpha158...")

self.handler= Alpha158(
instruments=self.instruments,
start_time=self.start_time,
end_time=self.end_time,
fit_start_time=self.start_time,
fit_end_time=self.train_end,
freq="day",
        )

print(f"  📈 Instrumentos:{self.instruments}")
print(f"  📅 Periodo:{self.start_time} a{self.end_time}")

defprepare_dataset(self):
"""Preparar train/test split"""
print("\n🔪 Preparando splits de train/test...")

self.dataset= DatasetH(
handler=self.handler,
segments={
"train": (self.start_time,self.train_end),
"valid": (self.train_end,self.test_start),
"test": (self.test_start,self.end_time)
            }
        )

# Extraer datos
print("  📥 Extrayendo datos de entrenamiento...")
self.train_df=self.dataset.prepare("train",col_set=["feature","label"])

print("  📥 Extrayendo datos de test...")
self.test_df=self.dataset.prepare("test",col_set=["feature","label"])

# Procesar multi-index
self.train_df=self._process_multiindex(self.train_df)
self.test_df=self._process_multiindex(self.test_df)

# Eliminar NaN
self.train_df=self.train_df.dropna()
self.test_df=self.test_df.dropna()

print(f"\n  ✅ Train samples:{len(self.train_df):,}")
print(f"  ✅ Test samples:{len(self.test_df):,}")
print(f"  ✅ Features:{self.train_df.shape[1]-1}")

def_process_multiindex(self,df: pd.DataFrame) -> pd.DataFrame:
"""Procesar multi-index de Qlib"""
ifisinstance(df.index, pd.MultiIndex):
            df= df.reset_index()
            df= df.set_index('datetime')
            df= df.drop(columns=['instrument'])
return df

defsave_dataset(self,output_dir: str="data/processed"):
"""Guardar dataset procesado"""
print("\n💾 Guardando dataset procesado...")

        os.makedirs(output_dir,exist_ok=True)

# Guardar como CSV
self.train_df.to_csv(f"{output_dir}/alpha158_usa_train.csv")
self.test_df.to_csv(f"{output_dir}/alpha158_usa_test.csv")

# Guardar metadata
        metadata= {
'instruments':self.instruments,
'start_time':self.start_time,
'end_time':self.end_time,
'train_end':self.train_end,
'test_start':self.test_start,
'n_features':self.train_df.shape[1]-1,
'n_train_samples':len(self.train_df),
'n_test_samples':len(self.test_df),
'feature_columns': list(self.train_df.columns.drop('LABEL0')),
'created_at': datetime.now().isoformat()
        }

import json
withopen(f"{output_dir}/metadata.json",'w')as f:
            json.dump(metadata, f,indent=2)

print(f"  ✅ Datos guardados en:{output_dir}/")

defrun(self):
"""Ejecutar todo el pipeline"""
print("="*60)
print("🚀 Preparando Dataset Alpha158 USA")
print("="*60)

self.initialize_qlib()
self.load_alpha158()
self.prepare_dataset()
self.save_dataset()

print("\n"+"="*60)
print("✅ Dataset preparado exitosamente!")
print("="*60)

returnself.train_df,self.test_df

if__name__=="__main__":
    preparator= Alpha158USAPreparator(
data_dir="~/.qlib/qlib_data/us_data",
instruments="sp500",
start_time="2010-01-01",
end_time="2023-12-31",
train_end="2018-12-31",
test_start="2019-01-01"
    )

    train_df, test_df= preparator.run()
```

### Ejecutar:

bash

```
pythonscripts/02_prepare_dataset.py
```

```
pythonscripts/02_prepare_dataset.py
```

---

## 🤖 Paso 4: Entrenar con AutoGluon

### Script: `scripts/03_train_autogluon.py`

python

```
#!/usr/bin/env python3
"""
Entrenar modelo AutoGluon con Alpha158 USA
"""

import os
import pandasas pd
import numpyas np
from autogluon.tabularimport TabularPredictor
from datetimeimport datetime
import json

classAlpha158AutoGluonTrainer:
def__init__(
self,
train_path: str="data/processed/alpha158_usa_train.csv",
test_path: str="data/processed/alpha158_usa_test.csv",
model_path: str="results/models/autogluon_alpha158_usa",
label_column: str="LABEL0",
time_limit: int=7200,# 2 horas
presets: str="best_quality"
    ):
self.train_path= train_path
self.test_path= test_path
self.model_path= model_path
self.label_column= label_column
self.time_limit= time_limit
self.presets= presets
self.predictor=None

defload_data(self):
"""Cargar datos"""
print("📥 Cargando datos...")

self.train_data= pd.read_csv(self.train_path,index_col=0,parse_dates=True)
self.test_data= pd.read_csv(self.test_path,index_col=0,parse_dates=True)

print(f"  ✅ Train:{len(self.train_data):,} samples")
print(f"  ✅ Test:{len(self.test_data):,} samples")
print(f"  ✅ Features:{len(self.train_data.columns)-1}")

deftrain(self):
"""Entrenar modelo AutoGluon"""
print("\n"+"="*60)
print("🤖 Entrenando AutoGluon")
print("="*60)

print(f"\n⚙️ Configuración:")
print(f"  • Presets:{self.presets}")
print(f"  • Time limit:{self.time_limit/3600:.1f} horas")
print(f"  • Label:{self.label_column}")
print(f"  • Problem type: regression")

self.predictor= TabularPredictor(
label=self.label_column,
problem_type='regression',
path=self.model_path,
eval_metric='rmse',
verbosity=2
        ).fit(
train_data=self.train_data,
presets=self.presets,
time_limit=self.time_limit,
num_bag_folds=5,
num_stack_levels=2,
excluded_model_types=['KNN'],# KNN no funciona bien con muchas features
verbosity=2
        )

print("\n✅ Entrenamiento completado!")

defevaluate(self):
"""Evaluar modelo"""
print("\n"+"="*60)
print("📊 Evaluando Modelo")
print("="*60)

# Evaluación básica
        results=self.predictor.evaluate(self.test_data)

print("\n📈 Métricas de Regresión:")
for metric, valuein results.items():
print(f"  •{metric}:{value:.6f}")

# Leaderboard
print("\n🏆 Leaderboard de Modelos:")
        leaderboard=self.predictor.leaderboard(self.test_data,silent=True)
print(leaderboard.head(10).to_string())

# Guardar leaderboard
        leaderboard.to_csv("results/predictions/leaderboard.csv",index=False)

return results, leaderboard

defsave_results(self):
"""Guardar resultados y predicciones"""
print("\n💾 Guardando resultados...")

        os.makedirs("results/predictions",exist_ok=True)

# Predicciones
        predictions=self.predictor.predict(self.test_data.drop(columns=[self.label_column]))
        predictions_df= pd.DataFrame({
'datetime':self.test_data.index,
'actual':self.test_data[self.label_column].values,
'predicted': predictions.values
        })
        predictions_df.to_csv("results/predictions/predictions.csv",index=False)

# Feature importance
        feature_importance=self.predictor.feature_importance(self.test_data)
        feature_importance.to_csv("results/predictions/feature_importance.csv")

# Metadata del entrenamiento
        metadata= {
'model_path':self.model_path,
'presets':self.presets,
'time_limit':self.time_limit,
'n_train_samples':len(self.train_data),
'n_test_samples':len(self.test_data),
'n_features':len(self.train_data.columns)-1,
'best_model':self.predictor.get_model_best(),
'trained_at': datetime.now().isoformat()
        }

withopen("results/predictions/training_metadata.json",'w')as f:
            json.dump(metadata, f,indent=2)

print("  ✅ Resultados guardados en results/predictions/")

defrun(self):
"""Ejecutar todo el pipeline"""
self.load_data()
self.train()
        results, leaderboard=self.evaluate()
self.save_results()

print("\n"+"="*60)
print("✅ Entrenamiento y evaluación completados!")
print("="*60)

return results, leaderboard

if__name__=="__main__":
    trainer= Alpha158AutoGluonTrainer(
train_path="data/processed/alpha158_usa_train.csv",
test_path="data/processed/alpha158_usa_test.csv",
model_path="results/models/autogluon_alpha158_usa",
time_limit=7200,# 2 horas
presets="best_quality"
    )

    results, leaderboard= trainer.run()
```

```
#!/usr/bin/env python3
"""
Entrenar modelo AutoGluon con Alpha158 USA
"""

import os
import pandasas pd
import numpyas np
from autogluon.tabularimport TabularPredictor
from datetimeimport datetime
import json

classAlpha158AutoGluonTrainer:
def__init__(
self,
train_path: str="data/processed/alpha158_usa_train.csv",
test_path: str="data/processed/alpha158_usa_test.csv",
model_path: str="results/models/autogluon_alpha158_usa",
label_column: str="LABEL0",
time_limit: int=7200,# 2 horas
presets: str="best_quality"
    ):
self.train_path= train_path
self.test_path= test_path
self.model_path= model_path
self.label_column= label_column
self.time_limit= time_limit
self.presets= presets
self.predictor=None

defload_data(self):
"""Cargar datos"""
print("📥 Cargando datos...")

self.train_data= pd.read_csv(self.train_path,index_col=0,parse_dates=True)
self.test_data= pd.read_csv(self.test_path,index_col=0,parse_dates=True)

print(f"  ✅ Train:{len(self.train_data):,} samples")
print(f"  ✅ Test:{len(self.test_data):,} samples")
print(f"  ✅ Features:{len(self.train_data.columns)-1}")

deftrain(self):
"""Entrenar modelo AutoGluon"""
print("\n"+"="*60)
print("🤖 Entrenando AutoGluon")
print("="*60)

print(f"\n⚙️ Configuración:")
print(f"  • Presets:{self.presets}")
print(f"  • Time limit:{self.time_limit/3600:.1f} horas")
print(f"  • Label:{self.label_column}")
print(f"  • Problem type: regression")

self.predictor= TabularPredictor(
label=self.label_column,
problem_type='regression',
path=self.model_path,
eval_metric='rmse',
verbosity=2
        ).fit(
train_data=self.train_data,
presets=self.presets,
time_limit=self.time_limit,
num_bag_folds=5,
num_stack_levels=2,
excluded_model_types=['KNN'],# KNN no funciona bien con muchas features
verbosity=2
        )

print("\n✅ Entrenamiento completado!")

defevaluate(self):
"""Evaluar modelo"""
print("\n"+"="*60)
print("📊 Evaluando Modelo")
print("="*60)

# Evaluación básica
        results=self.predictor.evaluate(self.test_data)

print("\n📈 Métricas de Regresión:")
for metric, valuein results.items():
print(f"  •{metric}:{value:.6f}")

# Leaderboard
print("\n🏆 Leaderboard de Modelos:")
        leaderboard=self.predictor.leaderboard(self.test_data,silent=True)
print(leaderboard.head(10).to_string())

# Guardar leaderboard
        leaderboard.to_csv("results/predictions/leaderboard.csv",index=False)

return results, leaderboard

defsave_results(self):
"""Guardar resultados y predicciones"""
print("\n💾 Guardando resultados...")

        os.makedirs("results/predictions",exist_ok=True)

# Predicciones
        predictions=self.predictor.predict(self.test_data.drop(columns=[self.label_column]))
        predictions_df= pd.DataFrame({
'datetime':self.test_data.index,
'actual':self.test_data[self.label_column].values,
'predicted': predictions.values
        })
        predictions_df.to_csv("results/predictions/predictions.csv",index=False)

# Feature importance
        feature_importance=self.predictor.feature_importance(self.test_data)
        feature_importance.to_csv("results/predictions/feature_importance.csv")

# Metadata del entrenamiento
        metadata= {
'model_path':self.model_path,
'presets':self.presets,
'time_limit':self.time_limit,
'n_train_samples':len(self.train_data),
'n_test_samples':len(self.test_data),
'n_features':len(self.train_data.columns)-1,
'best_model':self.predictor.get_model_best(),
'trained_at': datetime.now().isoformat()
        }

withopen("results/predictions/training_metadata.json",'w')as f:
            json.dump(metadata, f,indent=2)

print("  ✅ Resultados guardados en results/predictions/")

defrun(self):
"""Ejecutar todo el pipeline"""
self.load_data()
self.train()
        results, leaderboard=self.evaluate()
self.save_results()

print("\n"+"="*60)
print("✅ Entrenamiento y evaluación completados!")
print("="*60)

return results, leaderboard

if__name__=="__main__":
    trainer= Alpha158AutoGluonTrainer(
train_path="data/processed/alpha158_usa_train.csv",
test_path="data/processed/alpha158_usa_test.csv",
model_path="results/models/autogluon_alpha158_usa",
time_limit=7200,# 2 horas
presets="best_quality"
    )

    results, leaderboard= trainer.run()
```

### Ejecutar:

bash

```
pythonscripts/03_train_autogluon.py
```

```
pythonscripts/03_train_autogluon.py
```

---

## 📈 Paso 5: Evaluar con Métricas Financieras

### Script: `scripts/04_evaluate.py`

python

```
#!/usr/bin/env python3
"""
Evaluar con métricas financieras específicas para trading
"""

import pandasas pd
import numpyas np
from sklearn.metricsimport mean_squared_error, mean_absolute_error, r2_score
import json

classFinancialMetricsEvaluator:
def__init__(self,predictions_path: str="results/predictions/predictions.csv"):
self.predictions_df= pd.read_csv(predictions_path,parse_dates=['datetime'])
self.results= {}

defcalculate_regression_metrics(self):
"""Métricas de regresión básicas"""
        y_true=self.predictions_df['actual'].values
        y_pred=self.predictions_df['predicted'].values

self.results['regression']= {
'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
'mae': mean_absolute_error(y_true, y_pred),
'r2': r2_score(y_true, y_pred),
'mape': np.mean(np.abs((y_true- y_pred)/ (y_true+1e-8)))*100
        }

returnself.results['regression']

defcalculate_trading_metrics(self):
"""Métricas específicas para trading"""
        y_true=self.predictions_df['actual'].values
        y_pred=self.predictions_df['predicted'].values

# Information Coefficient (IC)
        ic= np.corrcoef(y_pred, y_true)[0,1]

# Rank IC
        rank_ic= np.corrcoef(
            pd.Series(y_pred).rank(),
            pd.Series(y_true).rank()
        )[0,1]

# ICIR (Information Coefficient Information Ratio)
# Calcular IC rolling
        window=20
        ic_rolling= []
for iinrange(window,len(y_pred)):
            ic_window= np.corrcoef(
                y_pred[i-window:i],
                y_true[i-window:i]
            )[0,1]
            ic_rolling.append(ic_window)

        ic_mean= np.mean(ic_rolling)
        ic_std= np.std(ic_rolling)
        icir= ic_mean/ (ic_std+1e-8)

# Directional Accuracy
        actual_direction= np.sign(y_true)
        predicted_direction= np.sign(y_pred)
        directional_accuracy= np.mean(actual_direction== predicted_direction)

# Hit Rate (predicciones correctas en magnitud y dirección)
        hit_rate= np.mean((np.sign(y_true)== np.sign(y_pred))&
                          (np.abs(y_pred)> np.median(np.abs(y_pred))))

self.results['trading']= {
'ic': ic,
'rank_ic': rank_ic,
'icir': icir,
'ic_mean': ic_mean,
'ic_std': ic_std,
'directional_accuracy': directional_accuracy,
'hit_rate': hit_rate
        }

returnself.results['trading']

defcalculate_portfolio_metrics(self,top_k: int=50,bottom_k: int=50):
"""Métricas basadas en portfolio"""
        df=self.predictions_df.copy()

# Ordenar por predicción
        df['pred_rank']= df['predicted'].rank(ascending=False)

# Top K (long positions)
        top_portfolio= df[df['pred_rank']<= top_k]
        top_return= top_portfolio['actual'].mean()

# Bottom K (short positions)
        bottom_portfolio= df[df['pred_rank']> (len(df)- bottom_k)]
        bottom_return= bottom_portfolio['actual'].mean()

# Long-Short portfolio
        long_short_return= top_return- bottom_return

# Annualized (asumiendo 252 trading days)
        annualized_return= long_short_return*252

# Volatility
        volatility= df['actual'].std()* np.sqrt(252)

# Sharpe Ratio (simplificado)
        sharpe= annualized_return/ (volatility+1e-8)

self.results['portfolio']= {
'top_k_return': top_return,
'bottom_k_return': bottom_return,
'long_short_return': long_short_return,
'annualized_return': annualized_return,
'volatility': volatility,
'sharpe_ratio': sharpe,
'top_k': top_k,
'bottom_k': bottom_k
        }

returnself.results['portfolio']

defprint_report(self):
"""Imprimir reporte completo"""
print("="*60)
print("📊 REPORTE DE EVALUACIÓN - ALPHA158 USA")
print("="*60)

print("\n📈 MÉTRICAS DE REGRESIÓN:")
for metric, valueinself.results['regression'].items():
print(f"  •{metric.upper()}:{value:.6f}")

print("\n💹 MÉTRICAS DE TRADING:")
for metric, valueinself.results['trading'].items():
print(f"  •{metric.upper()}:{value:.6f}")

print("\n📊 MÉTRICAS DE PORTFOLIO:")
for metric, valueinself.results['portfolio'].items():
ifisinstance(value, float):
print(f"  •{metric.upper()}:{value:.6f}")
else:
print(f"  •{metric.upper()}:{value}")

print("\n"+"="*60)

defsave_report(self,output_path: str="results/reports/evaluation_report.json"):
"""Guardar reporte"""
import os
        os.makedirs(os.path.dirname(output_path),exist_ok=True)

withopen(output_path,'w')as f:
            json.dump(self.results, f,indent=2,default=float)

print(f"✅ Reporte guardado en:{output_path}")

defrun(self):
"""Ejecutar todas las evaluaciones"""
self.calculate_regression_metrics()
self.calculate_trading_metrics()
self.calculate_portfolio_metrics()
self.print_report()
self.save_report()

returnself.results

if__name__=="__main__":
    evaluator= FinancialMetricsEvaluator(
predictions_path="results/predictions/predictions.csv"
    )

    results= evaluator.run()
```

```
#!/usr/bin/env python3
"""
Evaluar con métricas financieras específicas para trading
"""

import pandasas pd
import numpyas np
from sklearn.metricsimport mean_squared_error, mean_absolute_error, r2_score
import json

classFinancialMetricsEvaluator:
def__init__(self,predictions_path: str="results/predictions/predictions.csv"):
self.predictions_df= pd.read_csv(predictions_path,parse_dates=['datetime'])
self.results= {}

defcalculate_regression_metrics(self):
"""Métricas de regresión básicas"""
        y_true=self.predictions_df['actual'].values
        y_pred=self.predictions_df['predicted'].values

self.results['regression']= {
'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
'mae': mean_absolute_error(y_true, y_pred),
'r2': r2_score(y_true, y_pred),
'mape': np.mean(np.abs((y_true- y_pred)/ (y_true+1e-8)))*100
        }

returnself.results['regression']

defcalculate_trading_metrics(self):
"""Métricas específicas para trading"""
        y_true=self.predictions_df['actual'].values
        y_pred=self.predictions_df['predicted'].values

# Information Coefficient (IC)
        ic= np.corrcoef(y_pred, y_true)[0,1]

# Rank IC
        rank_ic= np.corrcoef(
            pd.Series(y_pred).rank(),
            pd.Series(y_true).rank()
        )[0,1]

# ICIR (Information Coefficient Information Ratio)
# Calcular IC rolling
        window=20
        ic_rolling= []
for iinrange(window,len(y_pred)):
            ic_window= np.corrcoef(
                y_pred[i-window:i],
                y_true[i-window:i]
            )[0,1]
            ic_rolling.append(ic_window)

        ic_mean= np.mean(ic_rolling)
        ic_std= np.std(ic_rolling)
        icir= ic_mean/ (ic_std+1e-8)

# Directional Accuracy
        actual_direction= np.sign(y_true)
        predicted_direction= np.sign(y_pred)
        directional_accuracy= np.mean(actual_direction== predicted_direction)

# Hit Rate (predicciones correctas en magnitud y dirección)
        hit_rate= np.mean((np.sign(y_true)== np.sign(y_pred))&
                          (np.abs(y_pred)> np.median(np.abs(y_pred))))

self.results['trading']= {
'ic': ic,
'rank_ic': rank_ic,
'icir': icir,
'ic_mean': ic_mean,
'ic_std': ic_std,
'directional_accuracy': directional_accuracy,
'hit_rate': hit_rate
        }

returnself.results['trading']

defcalculate_portfolio_metrics(self,top_k: int=50,bottom_k: int=50):
"""Métricas basadas en portfolio"""
        df=self.predictions_df.copy()

# Ordenar por predicción
        df['pred_rank']= df['predicted'].rank(ascending=False)

# Top K (long positions)
        top_portfolio= df[df['pred_rank']<= top_k]
        top_return= top_portfolio['actual'].mean()

# Bottom K (short positions)
        bottom_portfolio= df[df['pred_rank']> (len(df)- bottom_k)]
        bottom_return= bottom_portfolio['actual'].mean()

# Long-Short portfolio
        long_short_return= top_return- bottom_return

# Annualized (asumiendo 252 trading days)
        annualized_return= long_short_return*252

# Volatility
        volatility= df['actual'].std()* np.sqrt(252)

# Sharpe Ratio (simplificado)
        sharpe= annualized_return/ (volatility+1e-8)

self.results['portfolio']= {
'top_k_return': top_return,
'bottom_k_return': bottom_return,
'long_short_return': long_short_return,
'annualized_return': annualized_return,
'volatility': volatility,
'sharpe_ratio': sharpe,
'top_k': top_k,
'bottom_k': bottom_k
        }

returnself.results['portfolio']

defprint_report(self):
"""Imprimir reporte completo"""
print("="*60)
print("📊 REPORTE DE EVALUACIÓN - ALPHA158 USA")
print("="*60)

print("\n📈 MÉTRICAS DE REGRESIÓN:")
for metric, valueinself.results['regression'].items():
print(f"  •{metric.upper()}:{value:.6f}")

print("\n💹 MÉTRICAS DE TRADING:")
for metric, valueinself.results['trading'].items():
print(f"  •{metric.upper()}:{value:.6f}")

print("\n📊 MÉTRICAS DE PORTFOLIO:")
for metric, valueinself.results['portfolio'].items():
ifisinstance(value, float):
print(f"  •{metric.upper()}:{value:.6f}")
else:
print(f"  •{metric.upper()}:{value}")

print("\n"+"="*60)

defsave_report(self,output_path: str="results/reports/evaluation_report.json"):
"""Guardar reporte"""
import os
        os.makedirs(os.path.dirname(output_path),exist_ok=True)

withopen(output_path,'w')as f:
            json.dump(self.results, f,indent=2,default=float)

print(f"✅ Reporte guardado en:{output_path}")

defrun(self):
"""Ejecutar todas las evaluaciones"""
self.calculate_regression_metrics()
self.calculate_trading_metrics()
self.calculate_portfolio_metrics()
self.print_report()
self.save_report()

returnself.results

if__name__=="__main__":
    evaluator= FinancialMetricsEvaluator(
predictions_path="results/predictions/predictions.csv"
    )

    results= evaluator.run()
```

### Ejecutar:

bash

```
pythonscripts/04_evaluate.py
```

```
pythonscripts/04_evaluate.py
```

---

## 📊 Paso 6: Generar Reporte Visual

### Script: `scripts/05_generate_report.py`

python

```
#!/usr/bin/env python3
"""
Generar reporte visual con gráficos
"""

import pandasas pd
import numpyas np
import matplotlib.pyplotas plt
import seabornas sns
from datetimeimport datetime
import os

classVisualReportGenerator:
def__init__(self):
        plt.style.use('seaborn-v0_8-darkgrid')
self.colors= ['#2E86AB','#A23B72','#F18F01','#C73E1D','#6A994E']

defload_data(self):
"""Cargar datos necesarios"""
self.predictions= pd.read_csv(
"results/predictions/predictions.csv",
parse_dates=['datetime']
        )
self.leaderboard= pd.read_csv("results/predictions/leaderboard.csv")
self.feature_importance= pd.read_csv(
"results/predictions/feature_importance.csv",
index_col=0
        )

defplot_predictions_vs_actual(self,save_path: str="results/reports/01_predictions_vs_actual.png"):
"""Gráfico: Predicciones vs Actual"""
        fig, axes= plt.subplots(2,2,figsize=(16,12))

# Scatter plot
        ax1= axes[0,0]
        ax1.scatter(
self.predictions['actual'],
self.predictions['predicted'],
alpha=0.3,
s=10,
color=self.colors[0]
        )
        ax1.plot(
            [self.predictions['actual'].min(),self.predictions['actual'].max()],
            [self.predictions['actual'].min(),self.predictions['actual'].max()],
'r--',
linewidth=2
        )
        ax1.set_xlabel('Actual Returns')
        ax1.set_ylabel('Predicted Returns')
        ax1.set_title('Predictions vs Actual')

# Time series
        ax2= axes[0,1]
self.predictions.set_index('datetime')['actual'].plot(
ax=ax2,
label='Actual',
color=self.colors[0],
alpha=0.7
        )
self.predictions.set_index('datetime')['predicted'].plot(
ax=ax2,
label='Predicted',
color=self.colors[1],
alpha=0.7
        )
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Returns')
        ax2.set_title('Time Series Comparison')
        ax2.legend()

# Residuals
        ax3= axes[1,0]
        residuals=self.predictions['predicted']-self.predictions['actual']
        ax3.hist(residuals,bins=50,color=self.colors[2],alpha=0.7,edgecolor='black')
        ax3.axvline(x=0,color='red',linestyle='--',linewidth=2)
        ax3.set_xlabel('Residuals')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Residual Distribution')

# Residuals over time
        ax4= axes[1,1]
self.predictions['residuals']= residuals
self.predictions.set_index('datetime')['residuals'].plot(
ax=ax4,
color=self.colors[3],
alpha=0.7
        )
        ax4.axhline(y=0,color='red',linestyle='--',linewidth=2)
        ax4.set_xlabel('Date')
        ax4.set_ylabel('Residuals')
        ax4.set_title('Residuals Over Time')

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defplot_leaderboard(self,save_path: str="results/reports/02_model_leaderboard.png"):
"""Gráfico: Leaderboard de modelos"""
        fig, ax= plt.subplots(figsize=(14,8))

        top_models=self.leaderboard.head(15)

        colors= plt.cm.viridis(np.linspace(0.2,0.8,len(top_models)))

        bars= ax.barh(
            top_models['model'],
            top_models['score_test'],
color=colors
        )

        ax.set_xlabel('Score (RMSE)')
        ax.set_title('Model Leaderboard - Top 15 Models')
        ax.invert_yaxis()

# Añadir valores en las barras
for i, (bar, score)inenumerate(zip(bars, top_models['score_test'])):
            ax.text(
                bar.get_width()+0.001,
                bar.get_y()+ bar.get_height()/2,
f'{score:.4f}',
va='center',
fontsize=9
            )

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defplot_feature_importance(self,save_path: str="results/reports/03_feature_importance.png"):
"""Gráfico: Feature Importance"""
        fig, ax= plt.subplots(figsize=(12,10))

        top_features=self.feature_importance.head(30)

        colors= plt.cm.plasma(np.linspace(0.2,0.8,len(top_features)))

        bars= ax.barh(
            top_features.index,
            top_features['importance'],
color=colors
        )

        ax.set_xlabel('Importance')
        ax.set_title('Top 30 Most Important Features')
        ax.invert_yaxis()

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defplot_ic_analysis(self,save_path: str="results/reports/04_ic_analysis.png"):
"""Gráfico: IC Analysis"""
        fig, axes= plt.subplots(2,2,figsize=(16,12))

# Calcular IC rolling
        y_true=self.predictions['actual'].values
        y_pred=self.predictions['predicted'].values

        window=20
        ic_rolling= []
        dates= []

for iinrange(window,len(y_pred)):
            ic_window= np.corrcoef(
                y_pred[i-window:i],
                y_true[i-window:i]
            )[0,1]
            ic_rolling.append(ic_window)
            dates.append(self.predictions['datetime'].iloc[i])

# IC Rolling
        ax1= axes[0,0]
        ax1.plot(dates, ic_rolling,color=self.colors[0],linewidth=2)
        ax1.axhline(y=0,color='gray',linestyle='--',alpha=0.5)
        ax1.axhline(y=np.mean(ic_rolling),color='red',linestyle='--',label=f'Mean IC:{np.mean(ic_rolling):.4f}')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('IC')
        ax1.set_title('Rolling IC (20-day window)')
        ax1.legend()
        plt.setp(ax1.xaxis.get_majorticklabels(),rotation=45,ha='right')

# IC Histogram
        ax2= axes[0,1]
        ax2.hist(ic_rolling,bins=30,color=self.colors[1],alpha=0.7,edgecolor='black')
        ax2.axvline(x=np.mean(ic_rolling),color='red',linestyle='--',linewidth=2,label=f'Mean:{np.mean(ic_rolling):.4f}')
        ax2.set_xlabel('IC')
        ax2.set_ylabel('Frequency')
        ax2.set_title('IC Distribution')
        ax2.legend()

# Cumulative Returns
        ax3= axes[1,0]
        cumulative_returns= np.cumsum(y_pred)
        cumulative_actual= np.cumsum(y_true)
        ax3.plot(self.predictions['datetime'], cumulative_returns,label='Predicted',color=self.colors[2],linewidth=2)
        ax3.plot(self.predictions['datetime'], cumulative_actual,label='Actual',color=self.colors[3],linewidth=2,alpha=0.7)
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Cumulative Returns')
        ax3.set_title('Cumulative Returns')
        ax3.legend()
        plt.setp(ax3.xaxis.get_majorticklabels(),rotation=45,ha='right')

# Quantile Returns
        ax4= axes[1,1]
self.predictions['pred_quantile']= pd.qcut(self.predictions['predicted'],q=10,labels=False,duplicates='drop')
        quantile_returns=self.predictions.groupby('pred_quantile')['actual'].mean()
        ax4.bar(quantile_returns.index, quantile_returns.values,color=self.colors[4],alpha=0.7,edgecolor='black')
        ax4.set_xlabel('Prediction Quantile')
        ax4.set_ylabel('Mean Actual Return')
        ax4.set_title('Returns by Prediction Quantile')

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defrun(self):
"""Generar todos los gráficos"""
print("="*60)
print("📊 Generando Reporte Visual")
print("="*60)

        os.makedirs("results/reports",exist_ok=True)

self.load_data()
self.plot_predictions_vs_actual()
self.plot_leaderboard()
self.plot_feature_importance()
self.plot_ic_analysis()

print("\n✅ Todos los gráficos generados exitosamente!")
print("="*60)

if__name__=="__main__":
    generator= VisualReportGenerator()
    generator.run()
```

```
#!/usr/bin/env python3
"""
Generar reporte visual con gráficos
"""

import pandasas pd
import numpyas np
import matplotlib.pyplotas plt
import seabornas sns
from datetimeimport datetime
import os

classVisualReportGenerator:
def__init__(self):
        plt.style.use('seaborn-v0_8-darkgrid')
self.colors= ['#2E86AB','#A23B72','#F18F01','#C73E1D','#6A994E']

defload_data(self):
"""Cargar datos necesarios"""
self.predictions= pd.read_csv(
"results/predictions/predictions.csv",
parse_dates=['datetime']
        )
self.leaderboard= pd.read_csv("results/predictions/leaderboard.csv")
self.feature_importance= pd.read_csv(
"results/predictions/feature_importance.csv",
index_col=0
        )

defplot_predictions_vs_actual(self,save_path: str="results/reports/01_predictions_vs_actual.png"):
"""Gráfico: Predicciones vs Actual"""
        fig, axes= plt.subplots(2,2,figsize=(16,12))

# Scatter plot
        ax1= axes[0,0]
        ax1.scatter(
self.predictions['actual'],
self.predictions['predicted'],
alpha=0.3,
s=10,
color=self.colors[0]
        )
        ax1.plot(
            [self.predictions['actual'].min(),self.predictions['actual'].max()],
            [self.predictions['actual'].min(),self.predictions['actual'].max()],
'r--',
linewidth=2
        )
        ax1.set_xlabel('Actual Returns')
        ax1.set_ylabel('Predicted Returns')
        ax1.set_title('Predictions vs Actual')

# Time series
        ax2= axes[0,1]
self.predictions.set_index('datetime')['actual'].plot(
ax=ax2,
label='Actual',
color=self.colors[0],
alpha=0.7
        )
self.predictions.set_index('datetime')['predicted'].plot(
ax=ax2,
label='Predicted',
color=self.colors[1],
alpha=0.7
        )
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Returns')
        ax2.set_title('Time Series Comparison')
        ax2.legend()

# Residuals
        ax3= axes[1,0]
        residuals=self.predictions['predicted']-self.predictions['actual']
        ax3.hist(residuals,bins=50,color=self.colors[2],alpha=0.7,edgecolor='black')
        ax3.axvline(x=0,color='red',linestyle='--',linewidth=2)
        ax3.set_xlabel('Residuals')
        ax3.set_ylabel('Frequency')
        ax3.set_title('Residual Distribution')

# Residuals over time
        ax4= axes[1,1]
self.predictions['residuals']= residuals
self.predictions.set_index('datetime')['residuals'].plot(
ax=ax4,
color=self.colors[3],
alpha=0.7
        )
        ax4.axhline(y=0,color='red',linestyle='--',linewidth=2)
        ax4.set_xlabel('Date')
        ax4.set_ylabel('Residuals')
        ax4.set_title('Residuals Over Time')

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defplot_leaderboard(self,save_path: str="results/reports/02_model_leaderboard.png"):
"""Gráfico: Leaderboard de modelos"""
        fig, ax= plt.subplots(figsize=(14,8))

        top_models=self.leaderboard.head(15)

        colors= plt.cm.viridis(np.linspace(0.2,0.8,len(top_models)))

        bars= ax.barh(
            top_models['model'],
            top_models['score_test'],
color=colors
        )

        ax.set_xlabel('Score (RMSE)')
        ax.set_title('Model Leaderboard - Top 15 Models')
        ax.invert_yaxis()

# Añadir valores en las barras
for i, (bar, score)inenumerate(zip(bars, top_models['score_test'])):
            ax.text(
                bar.get_width()+0.001,
                bar.get_y()+ bar.get_height()/2,
f'{score:.4f}',
va='center',
fontsize=9
            )

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defplot_feature_importance(self,save_path: str="results/reports/03_feature_importance.png"):
"""Gráfico: Feature Importance"""
        fig, ax= plt.subplots(figsize=(12,10))

        top_features=self.feature_importance.head(30)

        colors= plt.cm.plasma(np.linspace(0.2,0.8,len(top_features)))

        bars= ax.barh(
            top_features.index,
            top_features['importance'],
color=colors
        )

        ax.set_xlabel('Importance')
        ax.set_title('Top 30 Most Important Features')
        ax.invert_yaxis()

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defplot_ic_analysis(self,save_path: str="results/reports/04_ic_analysis.png"):
"""Gráfico: IC Analysis"""
        fig, axes= plt.subplots(2,2,figsize=(16,12))

# Calcular IC rolling
        y_true=self.predictions['actual'].values
        y_pred=self.predictions['predicted'].values

        window=20
        ic_rolling= []
        dates= []

for iinrange(window,len(y_pred)):
            ic_window= np.corrcoef(
                y_pred[i-window:i],
                y_true[i-window:i]
            )[0,1]
            ic_rolling.append(ic_window)
            dates.append(self.predictions['datetime'].iloc[i])

# IC Rolling
        ax1= axes[0,0]
        ax1.plot(dates, ic_rolling,color=self.colors[0],linewidth=2)
        ax1.axhline(y=0,color='gray',linestyle='--',alpha=0.5)
        ax1.axhline(y=np.mean(ic_rolling),color='red',linestyle='--',label=f'Mean IC:{np.mean(ic_rolling):.4f}')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('IC')
        ax1.set_title('Rolling IC (20-day window)')
        ax1.legend()
        plt.setp(ax1.xaxis.get_majorticklabels(),rotation=45,ha='right')

# IC Histogram
        ax2= axes[0,1]
        ax2.hist(ic_rolling,bins=30,color=self.colors[1],alpha=0.7,edgecolor='black')
        ax2.axvline(x=np.mean(ic_rolling),color='red',linestyle='--',linewidth=2,label=f'Mean:{np.mean(ic_rolling):.4f}')
        ax2.set_xlabel('IC')
        ax2.set_ylabel('Frequency')
        ax2.set_title('IC Distribution')
        ax2.legend()

# Cumulative Returns
        ax3= axes[1,0]
        cumulative_returns= np.cumsum(y_pred)
        cumulative_actual= np.cumsum(y_true)
        ax3.plot(self.predictions['datetime'], cumulative_returns,label='Predicted',color=self.colors[2],linewidth=2)
        ax3.plot(self.predictions['datetime'], cumulative_actual,label='Actual',color=self.colors[3],linewidth=2,alpha=0.7)
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Cumulative Returns')
        ax3.set_title('Cumulative Returns')
        ax3.legend()
        plt.setp(ax3.xaxis.get_majorticklabels(),rotation=45,ha='right')

# Quantile Returns
        ax4= axes[1,1]
self.predictions['pred_quantile']= pd.qcut(self.predictions['predicted'],q=10,labels=False,duplicates='drop')
        quantile_returns=self.predictions.groupby('pred_quantile')['actual'].mean()
        ax4.bar(quantile_returns.index, quantile_returns.values,color=self.colors[4],alpha=0.7,edgecolor='black')
        ax4.set_xlabel('Prediction Quantile')
        ax4.set_ylabel('Mean Actual Return')
        ax4.set_title('Returns by Prediction Quantile')

        plt.tight_layout()
        plt.savefig(save_path,dpi=300,bbox_inches='tight')
        plt.close()
print(f"✅ Gráfico guardado:{save_path}")

defrun(self):
"""Generar todos los gráficos"""
print("="*60)
print("📊 Generando Reporte Visual")
print("="*60)

        os.makedirs("results/reports",exist_ok=True)

self.load_data()
self.plot_predictions_vs_actual()
self.plot_leaderboard()
self.plot_feature_importance()
self.plot_ic_analysis()

print("\n✅ Todos los gráficos generados exitosamente!")
print("="*60)

if__name__=="__main__":
    generator= VisualReportGenerator()
    generator.run()
```

### Ejecutar:

bash

```
pythonscripts/05_generate_report.py
```

```
pythonscripts/05_generate_report.py
```

---

## 🏃 Ejecutar Todo el Pipeline

### Script Principal: `run_benchmark.sh`

bash

```
#!/bin/bash

echo"============================================================"
echo"🚀 ALPHA158 USA BENCHMARK CON AUTOGLUON"
echo"============================================================"

# Crear directorios
mkdir-pdata/processedresults/modelsresults/predictionsresults/reports

# Paso 1: Descargar datos
echo""
echo"📥 PASO 1: Descargando datos..."
pythonscripts/01_download_data.py

# Paso 2: Preparar dataset
echo""
echo"📊 PASO 2: Preparando dataset..."
pythonscripts/02_prepare_dataset.py

# Paso 3: Entrenar AutoGluon
echo""
echo"🤖 PASO 3: Entrenando AutoGluon (esto puede tomar horas)..."
pythonscripts/03_train_autogluon.py

# Paso 4: Evaluar
echo""
echo"📈 PASO 4: Evaluando modelo..."
pythonscripts/04_evaluate.py

# Paso 5: Generar reporte
echo""
echo"📊 PASO 5: Generando reporte visual..."
pythonscripts/05_generate_report.py

echo""
echo"============================================================"
echo"✅ BENCHMARK COMPLETADO EXITOSAMENTE!"
echo"============================================================"
echo""
echo"📁 Resultados disponibles en:"
echo"   • Modelos: results/models/"
echo"   • Predicciones: results/predictions/"
echo"   • Reportes: results/reports/"
echo""
```

```
#!/bin/bash

echo"============================================================"
echo"🚀 ALPHA158 USA BENCHMARK CON AUTOGLUON"
echo"============================================================"

# Crear directorios
mkdir-pdata/processedresults/modelsresults/predictionsresults/reports

# Paso 1: Descargar datos
echo""
echo"📥 PASO 1: Descargando datos..."
pythonscripts/01_download_data.py

# Paso 2: Preparar dataset
echo""
echo"📊 PASO 2: Preparando dataset..."
pythonscripts/02_prepare_dataset.py

# Paso 3: Entrenar AutoGluon
echo""
echo"🤖 PASO 3: Entrenando AutoGluon (esto puede tomar horas)..."
pythonscripts/03_train_autogluon.py

# Paso 4: Evaluar
echo""
echo"📈 PASO 4: Evaluando modelo..."
pythonscripts/04_evaluate.py

# Paso 5: Generar reporte
echo""
echo"📊 PASO 5: Generando reporte visual..."
pythonscripts/05_generate_report.py

echo""
echo"============================================================"
echo"✅ BENCHMARK COMPLETADO EXITOSAMENTE!"
echo"============================================================"
echo""
echo"📁 Resultados disponibles en:"
echo"   • Modelos: results/models/"
echo"   • Predicciones: results/predictions/"
echo"   • Reportes: results/reports/"
echo""
```

### Ejecutar:

bash

```
chmod+xrun_benchmark.sh
./run_benchmark.sh
```

```
chmod+xrun_benchmark.sh
./run_benchmark.sh
```

---

## 📋 Configuraciones Alternativas

### Configuración Rápida (30 minutos)

python

```
# En scripts/03_train_autogluon.py
trainer= Alpha158AutoGluonTrainer(
time_limit=1800,# 30 minutos
presets='high_quality'
)
```

```
# En scripts/03_train_autogluon.py
trainer= Alpha158AutoGluonTrainer(
time_limit=1800,# 30 minutos
presets='high_quality'
)
```

### Configuración Máxima Calidad (8 horas)

python

```
trainer= Alpha158AutoGluonTrainer(
time_limit=28800,# 8 horas
presets='extreme',
num_bag_folds=8,
num_stack_levels=3
)
```

```
trainer= Alpha158AutoGluonTrainer(
time_limit=28800,# 8 horas
presets='extreme',
num_bag_folds=8,
num_stack_levels=3
)
```

### Configuración con GPU

python

```
trainer= Alpha158AutoGluonTrainer(
presets='extreme',
time_limit=14400
)

# En el fit:
predictor.fit(
    ...,
num_gpus=1# Habilitar GPU
)
```

```
trainer= Alpha158AutoGluonTrainer(
presets='extreme',
time_limit=14400
)

# En el fit:
predictor.fit(
    ...,
num_gpus=1# Habilitar GPU
)
```

---

## 📊 Resultados Esperados

| Métrica | Valor Esperado (USA) | China (Referencia) |
| --- | --- | --- |
| IC | 0.025 - 0.035 | 0.045 - 0.052 |
| Rank IC | 0.030 - 0.040 | 0.050 - 0.054 |
| ICIR | 0.20 - 0.30 | 0.35 - 0.42 |
| RMSE | 0.030 - 0.050 | 0.025 - 0.040 |
| Directional Accuracy | 52% - 56% | 55% - 60% |
| Annualized Return | 5% - 8% | 9% - 12% |

---

## ✅ Checklist Final

- [ ]  Datos USA descargados
- [ ]  Dataset Alpha158 preparado
- [ ]  AutoGluon entrenado
- [ ]  Métricas financieras calculadas
- [ ]  Reporte visual generado
- [ ]  Resultados comparados con benchmarks China

---

¿Necesitas ayuda con algún paso específico o quieres que profundice en alguna sección? 🚀

# 🧠 Configurar LSTM y GRU con Alpha158 USA

## ⚠️ Importante: AutoGluon Tabular NO Soporta LSTM/GRU

AutoGluon Tabular está diseñado para modelos tabulares tradicionales (LightGBM, XGBoost, CatBoost, etc.). LSTM y GRU son redes neuronales recurrentes que requieren un enfoque diferente.

Tienes 3 opciones:

| Opción | Herramienta | Dificultad | Recomendado |
| --- | --- | --- | --- |
| 1 | AutoGluon Time Series | ⭐ Fácil | ⚠️ No óptimo para Alpha158 |
| 2 | PyTorch/TensorFlow Custom | ⭐⭐⭐ Medio | ✅ RECOMENDADO |
| 3 | Qlib + Modelos Nativos | ⭐⭐ Fácil-Medio | ✅ MUY RECOMENDADO |

---

## 🎯 Opción 1: Qlib con LSTM/GRU (Más Fácil)

Qlib ya tiene implementaciones nativas de LSTM y GRU. Esta es la opción más recomendada.

### Paso 1: Configuración YAML para LSTM

Archivo: `configs/workflow_config_lstm_Alpha158_us.yaml`

yaml

```
qlib_init:
provider_uri:"~/.qlib/qlib_data/us_data"
region:us

market: &marketsp500
benchmark: &benchmarkSPX

data_handler_config: &data_handler_config
start_time: 2010-01-01
end_time: 2023-12-31
fit_start_time: 2010-01-01
fit_end_time: 2018-12-31
instruments: *market

port_analysis_config: &port_analysis_config
strategy:
class:TopkDropoutStrategy
module_path:qlib.contrib.strategy
kwargs:
signal:<PRED>
topk:50
n_drop:5
backtest:
start_time: 2019-01-01
end_time: 2023-12-31
account:1000000
benchmark: *benchmark
exchange_kwargs:
limit_threshold:null
deal_price:close
open_cost:0.001
close_cost:0.001
min_cost:1

task:
model:
class:LSTMModel
module_path:qlib.contrib.model.pytorch_lstm
kwargs:
input_size:158# Alpha158 features
hidden_size:256
num_layers:2
dropout:0.1
n_epochs:100
lr:0.001
early_stop:10
batch_size:2048
metric:loss
loss:mse
optimizer:adam
GPU:0# Cambiar a 0 si tienes GPU
dataset:
class:TSDatasetH
module_path:qlib.data.dataset
kwargs:
handler:
class:Alpha158
module_path:qlib.contrib.data.handler
kwargs: *data_handler_config
segments:
train: [2010-01-01, 2018-12-31]
valid: [2019-01-01, 2020-12-31]
test: [2021-01-01, 2023-12-31]
step_len:20# Window size para secuencias
record:
        -class:SignalRecord
module_path:qlib.workflow.record_temp
kwargs:
model:<MODEL>
dataset:<DATASET>
        -class:SigAnaRecord
module_path:qlib.workflow.record_temp
kwargs:
ana_long_short:False
ann_scaler:252
        -class:PortAnaRecord
module_path:qlib.workflow.record_temp
kwargs:
config: *port_analysis_config
```

```
qlib_init:
provider_uri:"~/.qlib/qlib_data/us_data"
region:us

market: &marketsp500
benchmark: &benchmarkSPX

data_handler_config: &data_handler_config
start_time: 2010-01-01
end_time: 2023-12-31
fit_start_time: 2010-01-01
fit_end_time: 2018-12-31
instruments: *market

port_analysis_config: &port_analysis_config
strategy:
class:TopkDropoutStrategy
module_path:qlib.contrib.strategy
kwargs:
signal:<PRED>
topk:50
n_drop:5
backtest:
start_time: 2019-01-01
end_time: 2023-12-31
account:1000000
benchmark: *benchmark
exchange_kwargs:
limit_threshold:null
deal_price:close
open_cost:0.001
close_cost:0.001
min_cost:1

task:
model:
class:LSTMModel
module_path:qlib.contrib.model.pytorch_lstm
kwargs:
input_size:158# Alpha158 features
hidden_size:256
num_layers:2
dropout:0.1
n_epochs:100
lr:0.001
early_stop:10
batch_size:2048
metric:loss
loss:mse
optimizer:adam
GPU:0# Cambiar a 0 si tienes GPU
dataset:
class:TSDatasetH
module_path:qlib.data.dataset
kwargs:
handler:
class:Alpha158
module_path:qlib.contrib.data.handler
kwargs: *data_handler_config
segments:
train: [2010-01-01, 2018-12-31]
valid: [2019-01-01, 2020-12-31]
test: [2021-01-01, 2023-12-31]
step_len:20# Window size para secuencias
record:
        -class:SignalRecord
module_path:qlib.workflow.record_temp
kwargs:
model:<MODEL>
dataset:<DATASET>
        -class:SigAnaRecord
module_path:qlib.workflow.record_temp
kwargs:
ana_long_short:False
ann_scaler:252
        -class:PortAnaRecord
module_path:qlib.workflow.record_temp
kwargs:
config: *port_analysis_config
```

### Paso 2: Configuración YAML para GRU

Archivo: `configs/workflow_config_gru_Alpha158_us.yaml`

yaml

```
# Similar a LSTM pero cambiar:
task:
model:
class:GRUModel
module_path:qlib.contrib.model.pytorch_gru
kwargs:
input_size:158
hidden_size:256
num_layers:2
dropout:0.1
n_epochs:100
lr:0.001
early_stop:10
batch_size:2048
metric:loss
loss:mse
optimizer:adam
GPU:0
```

```
# Similar a LSTM pero cambiar:
task:
model:
class:GRUModel
module_path:qlib.contrib.model.pytorch_gru
kwargs:
input_size:158
hidden_size:256
num_layers:2
dropout:0.1
n_epochs:100
lr:0.001
early_stop:10
batch_size:2048
metric:loss
loss:mse
optimizer:adam
GPU:0
```

### Paso 3: Ejecutar

bash

```
# LSTM
qrunconfigs/workflow_config_lstm_Alpha158_us.yaml

# GRU
qrunconfigs/workflow_config_gru_Alpha158_us.yaml
```

```
# LSTM
qrunconfigs/workflow_config_lstm_Alpha158_us.yaml

# GRU
qrunconfigs/workflow_config_gru_Alpha158_us.yaml
```

---

## 🎯 Opción 2: Implementación Custom con PyTorch + AutoGluon

Si quieres usar AutoGluon para otros modelos y LSTM/GRU custom, aquí está el código completo:

### Script: `scripts/06_train_lstm_gru.py`

python

```
#!/usr/bin/env python3
"""
Entrenar LSTM y GRU con Alpha158 USA
"""

import os
import pandasas pd
import numpyas np
import torch
import torch.nnas nn
from torch.utils.dataimport Dataset, DataLoader
from sklearn.preprocessingimport StandardScaler
from sklearn.metricsimport mean_squared_error, mean_absolute_error
import json
from datetimeimport datetime

# ==================== CONFIGURACIÓN ====================

classConfig:
    DATA_PATH="data/processed/alpha158_usa_train.csv"
    TEST_PATH="data/processed/alpha158_usa_test.csv"
    MODEL_DIR="results/models/lstm_gru"
    SEQUENCE_LENGTH=20# Ventana de tiempo
    HIDDEN_SIZE=256
    NUM_LAYERS=2
    DROPOUT=0.2
    BATCH_SIZE=512
    EPOCHS=100
    LEARNING_RATE=0.001
    EARLY_STOP_PATIENCE=10
    DEVICE= torch.device('cuda'if torch.cuda.is_available()else'cpu')

# ==================== DATASET CUSTOM ====================

classAlpha158Dataset(Dataset):
def__init__(self,data,sequence_length,is_train=True):
self.data= data
self.sequence_length= sequence_length
self.is_train= is_train

# Escalar features
self.feature_cols= [colfor colin data.columnsif col!='LABEL0']
self.scaler= StandardScaler()

# Escalar solo features (no label)
        features_scaled=self.scaler.fit_transform(data[self.feature_cols])
        labels= data['LABEL0'].values

# Crear secuencias
self.X,self.y=self._create_sequences(features_scaled, labels)

def_create_sequences(self,features,labels):
        X, y= [], []
for iinrange(self.sequence_length,len(features)):
            X.append(features[i-self.sequence_length:i])
            y.append(labels[i])
return np.array(X), np.array(y)

def__len__(self):
returnlen(self.X)

def__getitem__(self,idx):
return torch.FloatTensor(self.X[idx]), torch.FloatTensor([self.y[idx]])

# ==================== MODELOS ====================

classLSTMModel(nn.Module):
def__init__(self,input_size,hidden_size,num_layers,dropout):
        super(LSTMModel,self).__init__()
self.hidden_size= hidden_size
self.num_layers= num_layers

self.lstm= nn.LSTM(
input_size=input_size,
hidden_size=hidden_size,
num_layers=num_layers,
batch_first=True,
dropout=dropoutif num_layers>1else0
        )

self.fc= nn.Sequential(
            nn.Linear(hidden_size,128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128,1)
        )

defforward(self,x):
# x shape: (batch, seq_len, input_size)
        lstm_out, _=self.lstm(x)
# Tomar último time step
        out= lstm_out[:,-1, :]
        out=self.fc(out)
return out

classGRUModel(nn.Module):
def__init__(self,input_size,hidden_size,num_layers,dropout):
        super(GRUModel,self).__init__()
self.hidden_size= hidden_size
self.num_layers= num_layers

self.gru= nn.GRU(
input_size=input_size,
hidden_size=hidden_size,
num_layers=num_layers,
batch_first=True,
dropout=dropoutif num_layers>1else0
        )

self.fc= nn.Sequential(
            nn.Linear(hidden_size,128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128,1)
        )

defforward(self,x):
# x shape: (batch, seq_len, input_size)
        gru_out, _=self.gru(x)
# Tomar último time step
        out= gru_out[:,-1, :]
        out=self.fc(out)
return out

# ==================== TRAINER ====================

classLSTMGRUTrainer:
def__init__(self,model_type='lstm'):
self.model_type= model_type
self.device= Config.DEVICE
self.best_model=None

defprepare_data(self):
"""Preparar datos"""
print("📥 Cargando datos...")

self.train_df= pd.read_csv(Config.DATA_PATH,index_col=0,parse_dates=True)
self.test_df= pd.read_csv(Config.TEST_PATH,index_col=0,parse_dates=True)

# Crear datasets
self.train_dataset= Alpha158Dataset(
self.train_df,
            Config.SEQUENCE_LENGTH,
is_train=True
        )

self.test_dataset= Alpha158Dataset(
self.test_df,
            Config.SEQUENCE_LENGTH,
is_train=False
        )

# DataLoaders
self.train_loader= DataLoader(
self.train_dataset,
batch_size=Config.BATCH_SIZE,
shuffle=True,
num_workers=4
        )

self.test_loader= DataLoader(
self.test_dataset,
batch_size=Config.BATCH_SIZE,
shuffle=False,
num_workers=4
        )

print(f"  ✅ Train samples:{len(self.train_dataset):,}")
print(f"  ✅ Test samples:{len(self.test_dataset):,}")
print(f"  ✅ Sequence length:{Config.SEQUENCE_LENGTH}")

defcreate_model(self):
"""Crear modelo"""
        input_size=len(self.train_df.columns)-1# Features

ifself.model_type=='lstm':
self.model= LSTMModel(
input_size=input_size,
hidden_size=Config.HIDDEN_SIZE,
num_layers=Config.NUM_LAYERS,
dropout=Config.DROPOUT
            ).to(self.device)
else:
self.model= GRUModel(
input_size=input_size,
hidden_size=Config.HIDDEN_SIZE,
num_layers=Config.NUM_LAYERS,
dropout=Config.DROPOUT
            ).to(self.device)

self.criterion= nn.MSELoss()
self.optimizer= torch.optim.Adam(
self.model.parameters(),
lr=Config.LEARNING_RATE,
weight_decay=1e-5
        )

self.scheduler= torch.optim.lr_scheduler.ReduceLROnPlateau(
self.optimizer,
mode='min',
factor=0.5,
patience=5
        )

print(f"\n🤖 Modelo{self.model_type.upper()} creado:")
print(f"  • Input size:{input_size}")
print(f"  • Hidden size:{Config.HIDDEN_SIZE}")
print(f"  • Num layers:{Config.NUM_LAYERS}")
print(f"  • Device:{self.device}")

deftrain(self):
"""Entrenar modelo"""
print("\n"+"="*60)
print(f"🚀 Entrenando{self.model_type.upper()}")
print("="*60)

        best_loss= float('inf')
        patience_counter=0

for epochinrange(Config.EPOCHS):
# Training
self.model.train()
            train_loss=0.0

for batch_X, batch_yinself.train_loader:
                batch_X= batch_X.to(self.device)
                batch_y= batch_y.to(self.device)

self.optimizer.zero_grad()
                outputs=self.model(batch_X)
                loss=self.criterion(outputs, batch_y)
                loss.backward()

# Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.model.parameters(),max_norm=1.0)

self.optimizer.step()
                train_loss+= loss.item()

            train_loss/=len(self.train_loader)

# Validation
            val_loss=self._evaluate(self.test_loader)
self.scheduler.step(val_loss)

# Early stopping
if val_loss< best_loss:
                best_loss= val_loss
                patience_counter=0
self.best_model=self.model.state_dict().copy()
else:
                patience_counter+=1

if (epoch+1)%10==0:
print(f"Epoch [{epoch+1}/{Config.EPOCHS}] "
f"Train Loss:{train_loss:.6f} | "
f"Val Loss:{val_loss:.6f} | "
f"LR:{self.optimizer.param_groups[0]['lr']:.6f}")

if patience_counter>= Config.EARLY_STOP_PATIENCE:
print(f"\n⏹️ Early stopping en epoch{epoch+1}")
break

# Cargar mejor modelo
self.model.load_state_dict(self.best_model)
print("\n✅ Entrenamiento completado!")

def_evaluate(self,data_loader):
"""Evaluar modelo"""
self.model.eval()
        total_loss=0.0

with torch.no_grad():
for batch_X, batch_yin data_loader:
                batch_X= batch_X.to(self.device)
                batch_y= batch_y.to(self.device)

                outputs=self.model(batch_X)
                loss=self.criterion(outputs, batch_y)
                total_loss+= loss.item()

return total_loss/len(data_loader)

defpredict(self):
"""Hacer predicciones"""
print("\n📊 Generando predicciones...")

self.model.eval()
        predictions= []
        actuals= []

with torch.no_grad():
for batch_X, batch_yinself.test_loader:
                batch_X= batch_X.to(self.device)
                outputs=self.model(batch_X)
                predictions.extend(outputs.cpu().numpy().flatten())
                actuals.extend(batch_y.numpy().flatten())

self.predictions= np.array(predictions)
self.actuals= np.array(actuals)

print(f"  ✅ Predicciones generadas:{len(predictions):,}")

defevaluate_metrics(self):
"""Calcular métricas"""
print("\n"+"="*60)
print("📈 Métricas de Evaluación")
print("="*60)

# Métricas de regresión
        rmse= np.sqrt(mean_squared_error(self.actuals,self.predictions))
        mae= mean_absolute_error(self.actuals,self.predictions)
        r2= np.corrcoef(self.actuals,self.predictions)[0,1]**2

# IC (Information Coefficient)
        ic= np.corrcoef(self.actuals,self.predictions)[0,1]

# Rank IC
        rank_ic= np.corrcoef(
            pd.Series(self.actuals).rank(),
            pd.Series(self.predictions).rank()
        )[0,1]

# Directional Accuracy
        actual_direction= np.sign(self.actuals)
        predicted_direction= np.sign(self.predictions)
        directional_accuracy= np.mean(actual_direction== predicted_direction)

        metrics= {
'rmse': rmse,
'mae': mae,
'r2': r2,
'ic': ic,
'rank_ic': rank_ic,
'directional_accuracy': directional_accuracy
        }

for metric, valuein metrics.items():
print(f"  •{metric.upper()}:{value:.6f}")

return metrics

defsave_results(self):
"""Guardar resultados"""
print("\n💾 Guardando resultados...")

        os.makedirs(Config.MODEL_DIR,exist_ok=True)

# Guardar modelo
        torch.save(
self.model.state_dict(),
f"{Config.MODEL_DIR}/{self.model_type}_alpha158_usa.pth"
        )

# Guardar predicciones
        predictions_df= pd.DataFrame({
'actual':self.actuals,
'predicted':self.predictions
        })
        predictions_df.to_csv(
f"{Config.MODEL_DIR}/{self.model_type}_predictions.csv",
index=False
        )

# Guardar métricas
        metrics=self.evaluate_metrics()
withopen(f"{Config.MODEL_DIR}/{self.model_type}_metrics.json",'w')as f:
            json.dump(metrics, f,indent=2)

print(f"  ✅ Modelo guardado:{Config.MODEL_DIR}/{self.model_type}_alpha158_usa.pth")
print(f"  ✅ Predicciones:{Config.MODEL_DIR}/{self.model_type}_predictions.csv")

defrun(self):
"""Ejecutar todo el pipeline"""
self.prepare_data()
self.create_model()
self.train()
self.predict()
self.evaluate_metrics()
self.save_results()

print("\n"+"="*60)
print(f"✅{self.model_type.upper()} completado exitosamente!")
print("="*60)

if__name__=="__main__":
import sys

    model_type= sys.argv[1]iflen(sys.argv)>1else'lstm'

    trainer= LSTMGRUTrainer(model_type=model_type)
    trainer.run()
```

```
#!/usr/bin/env python3
"""
Entrenar LSTM y GRU con Alpha158 USA
"""

import os
import pandasas pd
import numpyas np
import torch
import torch.nnas nn
from torch.utils.dataimport Dataset, DataLoader
from sklearn.preprocessingimport StandardScaler
from sklearn.metricsimport mean_squared_error, mean_absolute_error
import json
from datetimeimport datetime

# ==================== CONFIGURACIÓN ====================

classConfig:
    DATA_PATH="data/processed/alpha158_usa_train.csv"
    TEST_PATH="data/processed/alpha158_usa_test.csv"
    MODEL_DIR="results/models/lstm_gru"
    SEQUENCE_LENGTH=20# Ventana de tiempo
    HIDDEN_SIZE=256
    NUM_LAYERS=2
    DROPOUT=0.2
    BATCH_SIZE=512
    EPOCHS=100
    LEARNING_RATE=0.001
    EARLY_STOP_PATIENCE=10
    DEVICE= torch.device('cuda'if torch.cuda.is_available()else'cpu')

# ==================== DATASET CUSTOM ====================

classAlpha158Dataset(Dataset):
def__init__(self,data,sequence_length,is_train=True):
self.data= data
self.sequence_length= sequence_length
self.is_train= is_train

# Escalar features
self.feature_cols= [colfor colin data.columnsif col!='LABEL0']
self.scaler= StandardScaler()

# Escalar solo features (no label)
        features_scaled=self.scaler.fit_transform(data[self.feature_cols])
        labels= data['LABEL0'].values

# Crear secuencias
self.X,self.y=self._create_sequences(features_scaled, labels)

def_create_sequences(self,features,labels):
        X, y= [], []
for iinrange(self.sequence_length,len(features)):
            X.append(features[i-self.sequence_length:i])
            y.append(labels[i])
return np.array(X), np.array(y)

def__len__(self):
returnlen(self.X)

def__getitem__(self,idx):
return torch.FloatTensor(self.X[idx]), torch.FloatTensor([self.y[idx]])

# ==================== MODELOS ====================

classLSTMModel(nn.Module):
def__init__(self,input_size,hidden_size,num_layers,dropout):
        super(LSTMModel,self).__init__()
self.hidden_size= hidden_size
self.num_layers= num_layers

self.lstm= nn.LSTM(
input_size=input_size,
hidden_size=hidden_size,
num_layers=num_layers,
batch_first=True,
dropout=dropoutif num_layers>1else0
        )

self.fc= nn.Sequential(
            nn.Linear(hidden_size,128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128,1)
        )

defforward(self,x):
# x shape: (batch, seq_len, input_size)
        lstm_out, _=self.lstm(x)
# Tomar último time step
        out= lstm_out[:,-1, :]
        out=self.fc(out)
return out

classGRUModel(nn.Module):
def__init__(self,input_size,hidden_size,num_layers,dropout):
        super(GRUModel,self).__init__()
self.hidden_size= hidden_size
self.num_layers= num_layers

self.gru= nn.GRU(
input_size=input_size,
hidden_size=hidden_size,
num_layers=num_layers,
batch_first=True,
dropout=dropoutif num_layers>1else0
        )

self.fc= nn.Sequential(
            nn.Linear(hidden_size,128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128,1)
        )

defforward(self,x):
# x shape: (batch, seq_len, input_size)
        gru_out, _=self.gru(x)
# Tomar último time step
        out= gru_out[:,-1, :]
        out=self.fc(out)
return out

# ==================== TRAINER ====================

classLSTMGRUTrainer:
def__init__(self,model_type='lstm'):
self.model_type= model_type
self.device= Config.DEVICE
self.best_model=None

defprepare_data(self):
"""Preparar datos"""
print("📥 Cargando datos...")

self.train_df= pd.read_csv(Config.DATA_PATH,index_col=0,parse_dates=True)
self.test_df= pd.read_csv(Config.TEST_PATH,index_col=0,parse_dates=True)

# Crear datasets
self.train_dataset= Alpha158Dataset(
self.train_df,
            Config.SEQUENCE_LENGTH,
is_train=True
        )

self.test_dataset= Alpha158Dataset(
self.test_df,
            Config.SEQUENCE_LENGTH,
is_train=False
        )

# DataLoaders
self.train_loader= DataLoader(
self.train_dataset,
batch_size=Config.BATCH_SIZE,
shuffle=True,
num_workers=4
        )

self.test_loader= DataLoader(
self.test_dataset,
batch_size=Config.BATCH_SIZE,
shuffle=False,
num_workers=4
        )

print(f"  ✅ Train samples:{len(self.train_dataset):,}")
print(f"  ✅ Test samples:{len(self.test_dataset):,}")
print(f"  ✅ Sequence length:{Config.SEQUENCE_LENGTH}")

defcreate_model(self):
"""Crear modelo"""
        input_size=len(self.train_df.columns)-1# Features

ifself.model_type=='lstm':
self.model= LSTMModel(
input_size=input_size,
hidden_size=Config.HIDDEN_SIZE,
num_layers=Config.NUM_LAYERS,
dropout=Config.DROPOUT
            ).to(self.device)
else:
self.model= GRUModel(
input_size=input_size,
hidden_size=Config.HIDDEN_SIZE,
num_layers=Config.NUM_LAYERS,
dropout=Config.DROPOUT
            ).to(self.device)

self.criterion= nn.MSELoss()
self.optimizer= torch.optim.Adam(
self.model.parameters(),
lr=Config.LEARNING_RATE,
weight_decay=1e-5
        )

self.scheduler= torch.optim.lr_scheduler.ReduceLROnPlateau(
self.optimizer,
mode='min',
factor=0.5,
patience=5
        )

print(f"\n🤖 Modelo{self.model_type.upper()} creado:")
print(f"  • Input size:{input_size}")
print(f"  • Hidden size:{Config.HIDDEN_SIZE}")
print(f"  • Num layers:{Config.NUM_LAYERS}")
print(f"  • Device:{self.device}")

deftrain(self):
"""Entrenar modelo"""
print("\n"+"="*60)
print(f"🚀 Entrenando{self.model_type.upper()}")
print("="*60)

        best_loss= float('inf')
        patience_counter=0

for epochinrange(Config.EPOCHS):
# Training
self.model.train()
            train_loss=0.0

for batch_X, batch_yinself.train_loader:
                batch_X= batch_X.to(self.device)
                batch_y= batch_y.to(self.device)

self.optimizer.zero_grad()
                outputs=self.model(batch_X)
                loss=self.criterion(outputs, batch_y)
                loss.backward()

# Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.model.parameters(),max_norm=1.0)

self.optimizer.step()
                train_loss+= loss.item()

            train_loss/=len(self.train_loader)

# Validation
            val_loss=self._evaluate(self.test_loader)
self.scheduler.step(val_loss)

# Early stopping
if val_loss< best_loss:
                best_loss= val_loss
                patience_counter=0
self.best_model=self.model.state_dict().copy()
else:
                patience_counter+=1

if (epoch+1)%10==0:
print(f"Epoch [{epoch+1}/{Config.EPOCHS}] "
f"Train Loss:{train_loss:.6f} | "
f"Val Loss:{val_loss:.6f} | "
f"LR:{self.optimizer.param_groups[0]['lr']:.6f}")

if patience_counter>= Config.EARLY_STOP_PATIENCE:
print(f"\n⏹️ Early stopping en epoch{epoch+1}")
break

# Cargar mejor modelo
self.model.load_state_dict(self.best_model)
print("\n✅ Entrenamiento completado!")

def_evaluate(self,data_loader):
"""Evaluar modelo"""
self.model.eval()
        total_loss=0.0

with torch.no_grad():
for batch_X, batch_yin data_loader:
                batch_X= batch_X.to(self.device)
                batch_y= batch_y.to(self.device)

                outputs=self.model(batch_X)
                loss=self.criterion(outputs, batch_y)
                total_loss+= loss.item()

return total_loss/len(data_loader)

defpredict(self):
"""Hacer predicciones"""
print("\n📊 Generando predicciones...")

self.model.eval()
        predictions= []
        actuals= []

with torch.no_grad():
for batch_X, batch_yinself.test_loader:
                batch_X= batch_X.to(self.device)
                outputs=self.model(batch_X)
                predictions.extend(outputs.cpu().numpy().flatten())
                actuals.extend(batch_y.numpy().flatten())

self.predictions= np.array(predictions)
self.actuals= np.array(actuals)

print(f"  ✅ Predicciones generadas:{len(predictions):,}")

defevaluate_metrics(self):
"""Calcular métricas"""
print("\n"+"="*60)
print("📈 Métricas de Evaluación")
print("="*60)

# Métricas de regresión
        rmse= np.sqrt(mean_squared_error(self.actuals,self.predictions))
        mae= mean_absolute_error(self.actuals,self.predictions)
        r2= np.corrcoef(self.actuals,self.predictions)[0,1]**2

# IC (Information Coefficient)
        ic= np.corrcoef(self.actuals,self.predictions)[0,1]

# Rank IC
        rank_ic= np.corrcoef(
            pd.Series(self.actuals).rank(),
            pd.Series(self.predictions).rank()
        )[0,1]

# Directional Accuracy
        actual_direction= np.sign(self.actuals)
        predicted_direction= np.sign(self.predictions)
        directional_accuracy= np.mean(actual_direction== predicted_direction)

        metrics= {
'rmse': rmse,
'mae': mae,
'r2': r2,
'ic': ic,
'rank_ic': rank_ic,
'directional_accuracy': directional_accuracy
        }

for metric, valuein metrics.items():
print(f"  •{metric.upper()}:{value:.6f}")

return metrics

defsave_results(self):
"""Guardar resultados"""
print("\n💾 Guardando resultados...")

        os.makedirs(Config.MODEL_DIR,exist_ok=True)

# Guardar modelo
        torch.save(
self.model.state_dict(),
f"{Config.MODEL_DIR}/{self.model_type}_alpha158_usa.pth"
        )

# Guardar predicciones
        predictions_df= pd.DataFrame({
'actual':self.actuals,
'predicted':self.predictions
        })
        predictions_df.to_csv(
f"{Config.MODEL_DIR}/{self.model_type}_predictions.csv",
index=False
        )

# Guardar métricas
        metrics=self.evaluate_metrics()
withopen(f"{Config.MODEL_DIR}/{self.model_type}_metrics.json",'w')as f:
            json.dump(metrics, f,indent=2)

print(f"  ✅ Modelo guardado:{Config.MODEL_DIR}/{self.model_type}_alpha158_usa.pth")
print(f"  ✅ Predicciones:{Config.MODEL_DIR}/{self.model_type}_predictions.csv")

defrun(self):
"""Ejecutar todo el pipeline"""
self.prepare_data()
self.create_model()
self.train()
self.predict()
self.evaluate_metrics()
self.save_results()

print("\n"+"="*60)
print(f"✅{self.model_type.upper()} completado exitosamente!")
print("="*60)

if__name__=="__main__":
import sys

    model_type= sys.argv[1]iflen(sys.argv)>1else'lstm'

    trainer= LSTMGRUTrainer(model_type=model_type)
    trainer.run()
```

### Ejecutar:

bash

```
#
```

```
#
```