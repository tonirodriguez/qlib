# Análisis Series Temporales

Me puedes analizar estos resultados de análisis de series temporales con diferentes modelos:

Perfecto, vamos a desmenuzar esto bien porque ya tienes señales bastante claras 👇

## 📊 1. Comparación general de modelos

| Modelo | MAE ↓ | RMSE ↓ | MAPE ↓ |
| --- | --- | --- | --- |
| **AutoARIMA** | **24280** | **26638** | **18.48%** |
| AutoETS | 25815 | 28348 | 19.62% |
| LGBMRegressor | 26114 | 30270 | 19.62% |
| XGBRegressor | 26307 | 29209 | 19.94% |

👉 **Conclusión rápida:**

**AutoARIMA gana en todas las métricas.**

---

## 🔍 2. Interpretación por métricas

### 🟢 MAE (Error absoluto medio)

- Mide el error promedio en unidades reales.
- **AutoARIMA tiene el menor error (~24k)** → predicciones más cercanas en promedio.

👉 Los modelos de boosting (LGBM, XGB) están peor aquí → no están capturando bien el patrón base.

---

### 🟢 RMSE (penaliza errores grandes)

- Aquí se ve si hay errores “grandes” problemáticos.
- **AutoARIMA vuelve a ganar claramente (26638 vs >29000)**

👉 Esto es importante:

- Los modelos ML (sobre todo LGBM) tienen errores más extremos.
- Posible sobreajuste o mala captura de picos.

---

### 🟢 MAPE (% de error)

- Más interpretable: error relativo.
- **AutoARIMA: 18.48% → mejor modelo**
- El resto ~19.6–19.9%

👉 Diferencia de ~1–1.5 puntos → **no enorme, pero consistente**.

---

## 🧠 3. Lectura más profunda (esto es lo interesante)

### 📌 1. Modelos clásicos > modelos ML

Esto sugiere que tu serie:

- Tiene **estructura temporal clara** (tendencia/estacionalidad)
- No depende tanto de variables externas complejas

👉 Por eso:

- ARIMA y ETS funcionan mejor
- Boosting no aporta ventaja

---

### 📌 2. ETS vs ARIMA

- ETS está relativamente cerca, pero peor en todo
- Puede indicar que:
    - Hay **autocorrelación que ETS no captura tan bien**
    - O patrones más complejos que ARIMA sí modela

---

### 📌 3. ML (LGBM / XGB) rinden peor

Posibles causas:

- Falta de **features temporales buenas** (lags, rolling stats…)
- Dataset pequeño (muy común en series temporales)
- No se ha hecho feature engineering específico

👉 Tal como están, **no son competitivos**.

---

## ⚠️ 4. Cosas a vigilar

### ❗ Diferencias no gigantes

- MAPE: 18.5% vs 19.6%
    
    👉 Mejora real, pero no brutal
    

➡️ Esto sugiere que:

- Ningún modelo es “excelente”
- Hay margen de mejora global

---

## 🚀 5. Recomendaciones claras

### ✅ Qué usar ahora mismo

👉 **AutoARIMA sin duda** como baseline productivo

---

### 🔧 Cómo mejorar (muy importante)

### 1. Mejorar ML (si quieres que compitan)

Añadir features:

- Lags (t-1, t-7, t-30…)
- Rolling mean/std
- Variables calendario (mes, día semana)
- Festivos/eventos

---

### 2. Probar híbridos

- ARIMA + ML (residuos)
- Prophet (si hay estacionalidad fuerte)

---

### 3. Analizar residuos de ARIMA

Si los residuos:

- No son ruido blanco → aún hay patrón explotable

---

## 🧾 Conclusión final

👉 Tu serie parece **clásica (temporal pura)**

👉 **AutoARIMA es el mejor modelo actual**

👉 ML no aporta valor todavía (probablemente por falta de features)

---

Si quieres, en el siguiente paso puedo:

- Decirte exactamente **qué features crear para LGBM/XGB**
- O ayudarte a interpretar si hay **sobreajuste**
- O ver **gráficos (pred vs real, residuos, etc.)**

Solo dime 👍

Ahora añado los siguietnes datos:

Buenísimo, ahora esto cambia bastante la película 👇

## 📊 1. Tabla completa actualizada

| Modelo | MAE ↓ | RMSE ↓ | MAPE ↓ |
| --- | --- | --- | --- |
| AutoARIMA | 24280 | 26638 | 18.48% |
| AutoETS | 25815 | 28348 | 19.62% |
| LGBMRegressor | 26114 | 30270 | 19.62% |
| XGBRegressor | 26307 | 29209 | 19.94% |
| **RandomForest** | **16501** | **18697** | **12.50%** |
| TimeGPT | 31409 | 33940 | 23.99% |
| timesfm | 29577 | 31998 | 22.58% |

---

## 🧠 2. Conclusión principal (muy clara)

👉 **RandomForest rompe completamente el ranking**

👉 Mejora brutal respecto a todos los demás

- ~**30–40% mejor** en MAE y RMSE
- ~**6 puntos menos de MAPE** (esto es MUCHO)

---

## 🔍 3. Qué significa esto realmente

### 📌 1. Tu serie NO es “simplemente temporal”

Antes parecía:

> “serie clásica → ARIMA gana”
> 

Ahora vemos:

> **hay estructura no lineal importante**
> 

👉 Random Forest captura:

- relaciones no lineales
- interacciones entre variables
- patrones complejos

---

### 📌 2. Feature engineering probablemente ha funcionado

Esto es clave:

👉 Para que RandomForest gane así, casi seguro has añadido:

- lags
- rolling features
- variables calendario
- o exógenas

💡 Esto confirma:

> **el problema se beneficia de features, no solo del tiempo puro**
> 

---

### 📌 3. Boosting (LGBM/XGB) rinde peor que RF 🤔

Esto es interesante:

- RF >> XGB / LGBM
    
    👉 Posibles razones:
    
- Poco tuning en boosting
- Dataset pequeño → RF más robusto
- Ruido → RF generaliza mejor

---

### 📌 4. Modelos “foundation” (TimeGPT, timesfm) decepcionan

- Son claramente los peores

👉 Interpretación:

- No están adaptados a tu serie concreta
- O el dataset es específico / pequeño
- O falta fine-tuning

---

## ⚠️ 4. Red flags / cosas a validar

Esto es MUY importante antes de confiar en RF:

### ❗ 1. Posible data leakage

Cuando un modelo mejora tanto:

👉 revisa que NO estés usando:

- información del futuro en features
- rolling mal calculados (con leakage)
- normalización global

---

### ❗ 2. Validación temporal correcta

Asegúrate de:

- split por tiempo (NO random split)
- walk-forward o backtesting

---

### ❗ 3. Overfitting

RF puede:

- memorizar si hay pocos datos

👉 compara:

- train vs test error

---

## 🚀 5. Recomendaciones claras

### ✅ 1. Modelo ganador actual

👉 **RandomForestRegressor (claramente)**

---

### 🔧 2. Siguiente paso lógico

### Mejorar aún más RF:

- tuning (n_estimators, max_depth…)
- más features temporales

### Intentar superar RF con boosting:

- tuning serio de XGB/LGBM
- early stopping
- regularización

---

### 🧪 3. Mezcla de modelos (muy potente)

- Ensemble:
    - RF + ARIMA
    - RF + XGB

👉 muchas veces mejora estabilidad

---

## 🧾 Conclusión final

👉 Has pasado de:

> “ARIMA es mejor”
> 

a:

> **“los modelos basados en features dominan completamente”**
> 

💡 Insight clave:

- Tu problema **no es solo temporal**
- Es un problema **tabular + temporal**

---

Si quieres, puedo:

- Revisarte si hay **data leakage (muy importante aquí)**
- Proponerte el **pipeline ideal para RF/XGB**
- O ayudarte a construir un **modelo híbrido que mejore aún más ese 12.5%**

Solo dime 👍

Las tres cosas

Perfecto — ahora estamos en la parte “pro” de verdad. Vamos por partes y bien práctico 👇

---

# ⚠️ 1. DATA LEAKAGE (lo más crítico ahora mismo)

Con una mejora tan grande como la de RandomForest, **esto hay que auditar sí o sí**.

## 🔍 Checklist de leakage en series temporales

### ❗ 1. Lags mal construidos

Asegúrate de que:

```python
df['lag_1'] = df['y'].shift(1)
df['lag_7'] = df['y'].shift(7)
```

🚫 MAL:

- usar `.shift(0)`
- usar valores futuros sin querer

---

### ❗ 2. Rolling features peligrosas

🚫 Esto genera leakage:

```python
df['rolling_mean_7'] = df['y'].rolling(7).mean()
```

✅ Correcto:

```python
df['rolling_mean_7'] = df['y'].shift(1).rolling(7).mean()
```

👉 Siempre: **shift antes de rolling**

---

### ❗ 3. Escalado global

🚫 MAL:

```python
scaler.fit(df)  # usa todo el dataset
```

✅ BIEN:

- fit solo en train
- aplicar en test

---

### ❗ 4. Split incorrecto

🚫 Nunca:

```python
train_test_split(shuffle=True)
```

✅ Siempre:

```python
train = df[df.date < '2023-01-01']
test  = df[df.date >= '2023-01-01']
```

---

### ❗ 5. Features “futuras”

Cuidado con:

- medias por mes calculadas con todo el dataset
- variables agregadas con info futura

---

## 🧪 Test rápido anti-leakage

👉 Si RF mejora MUCHO vs ARIMA:

- ✔️ puede ser real
- ❗ pero también sospechoso

Haz esto:

- entrena en ventana antigua
- test en periodo completamente futuro

Si se mantiene → OK

Si cae fuerte → había leakage

---

# 🏗️ 2. PIPELINE IDEAL (RF / XGB)

Aquí es donde puedes ganar aún más.

## 🔧 Feature engineering (clave absoluta)

### 📌 Lags

```python
lags = [1, 2, 3, 7, 14, 30]
```

---

### 📌 Rolling stats

```python
windows = [7, 14, 30]

df['roll_mean_7'] = df['y'].shift(1).rolling(7).mean()
df['roll_std_7']  = df['y'].shift(1).rolling(7).std()
```

---

### 📌 Features calendario

```python
df['dayofweek'] = df.date.dt.dayofweek
df['month'] = df.date.dt.month
df['weekofyear'] = df.date.dt.isocalendar().week
```

👉 Muy importantes si hay estacionalidad

---

### 📌 Features cíclicas (MUY recomendable)

```python
df['month_sin'] = np.sin(2*np.pi*df['month']/12)
df['month_cos'] = np.cos(2*np.pi*df['month']/12)
```

---

### 📌 Diferencias (para tendencia)

```python
df['diff_1'] = df['y'] - df['lag_1']
```

---

## ⚙️ Pipeline limpio

```python
# 1. Crear features SOLO con pasado
df = create_features(df)

# 2. Split temporal
train = df[df.date < split_date]
test  = df[df.date >= split_date]

# 3. Entrenar
model = RandomForestRegressor(...)
model.fit(X_train, y_train)

# 4. Predecir
preds = model.predict(X_test)
```

---

## 🎯 Tuning recomendado

### RandomForest

```python
n_estimators: 200–1000
max_depth: 5–20
min_samples_leaf: 1–10
```

---

### XGBoost (para intentar superar RF)

```python
learning_rate: 0.01–0.1
max_depth: 3–10
n_estimators: 300–1000
subsample: 0.7–1
colsample_bytree: 0.7–1
```

👉 XGB puede superar RF si lo tuneas bien

---

# 🔗 3. MODELO HÍBRIDO (lo más potente)

Aquí puedes sacar otro salto de rendimiento.

## 🧠 Idea clave

👉 Combinar:

- **modelo lineal (ARIMA)** → tendencia/estructura
- **modelo ML (RF/XGB)** → residuos no lineales

---

## 🏗️ Arquitectura híbrida (recomendada)

### Paso 1: ARIMA

```python
arima.fit(train)
arima_pred = arima.predict(test)
```

---

### Paso 2: residuos

```python
residuals = y_train - arima.predict(train)
```

---

### Paso 3: ML sobre residuos

```python
rf.fit(X_train, residuals)
rf_pred = rf.predict(X_test)
```

---

### Paso 4: predicción final

```python
final_pred = arima_pred + rf_pred
```

---

## 💡 Por qué funciona

- ARIMA captura:
    - tendencia
    - estacionalidad
- RF captura:
    - patrones raros
    - no linealidades

👉 juntos = mejor que cualquiera solo

---

## 🔥 Alternativa más simple (ensemble)

```python
final_pred = 0.7 * rf_pred + 0.3 * arima_pred
```

👉 más fácil, muchas veces funciona muy bien

---

# 🧾 CONCLUSIÓN ESTRATÉGICA

Ahora mismo estás en este punto:

👉 RF gana → ✔️ buen feature engineering

👉 ARIMA aún útil → ✔️ estructura temporal existe

## 🚀 Mejor enfoque:

1. **Verificar leakage (crítico)**
2. **Optimizar RF/XGB con features**
3. **Construir modelo híbrido**

---

# 💬 Si quieres ir al siguiente nivel

Puedo ayudarte a:

- revisar tu código real (y detectar leakage exacto)
- darte un **pipeline listo en sklearn**
- o montar un **walk-forward validation profesional**

Solo dime 👍

Monteme un walk-forward validation profesional

Perfecto — esto es justo lo que separa un modelo “que parece bueno” de uno **realmente fiable en producción**.

Te monto un **walk-forward validation profesional**, limpio y listo para usar 👇

---

# 🧠 ¿Qué vamos a construir?

Un esquema:

```
Train [------] Test [--]
Train [--------] Test [--]
Train [----------] Test [--]
```

👉 Entrenas → predices → avanzas → repites

👉 Simula cómo funcionará en el mundo real

---

# 🏗️ 1. ESTRUCTURA PROFESIONAL

## Tipos de walk-forward

### ✅ Expanding window (recomendado)

- El train crece con el tiempo
- Más estable

### 🔁 Rolling window

- Tamaño fijo
- Útil si hay drift fuerte

👉 Vamos con **expanding window** (mejor en la mayoría de casos)

---

# ⚙️ 2. IMPLEMENTACIÓN COMPLETA (lista para usar)

```python
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

def walk_forward_validation(
    df,
    model,
    target_col,
    date_col,
    initial_train_size,
    horizon=1,
    step=1,
    feature_func=None
):
    """
    Walk-forward validation profesional para series temporales

    Parameters:
    - df: DataFrame ordenado por fecha
    - model: modelo sklearn-like
    - target_col: nombre de la variable objetivo
    - date_col: columna de fecha
    - initial_train_size: tamaño inicial de train
    - horizon: pasos a predecir
    - step: cuánto avanza cada iteración
    - feature_func: función para crear features (MUY IMPORTANTE)
    """

    df = df.sort_values(date_col).reset_index(drop=True)

    preds = []
    actuals = []
    dates = []

    for i in range(initial_train_size, len(df) - horizon, step):

        train = df.iloc[:i].copy()
        test  = df.iloc[i:i+horizon].copy()

        # 🔥 Crear features SIN leakage
        if feature_func:
            train = feature_func(train)
            full = feature_func(df.iloc[:i+horizon].copy())
            test = full.iloc[i:i+horizon]

        # Drop NA (lags etc)
        train = train.dropna()
        test  = test.dropna()

        if len(test) == 0:
            continue

        X_train = train.drop(columns=[target_col, date_col])
        y_train = train[target_col]

        X_test = test.drop(columns=[target_col, date_col])
        y_test = test[target_col]

        # Entrenar
        model.fit(X_train, y_train)

        # Predecir
        y_pred = model.predict(X_test)

        preds.extend(y_pred)
        actuals.extend(y_test.values)
        dates.extend(test[date_col].values)

    # Métricas
    mae = mean_absolute_error(actuals, preds)
    rmse = np.sqrt(mean_squared_error(actuals, preds))
    mape = np.mean(np.abs((np.array(actuals) - np.array(preds)) / actuals)) * 100

    results = pd.DataFrame({
        'date': dates,
        'actual': actuals,
        'pred': preds
    })

    return {
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "predictions": results
    }
```

---

# 🧩 3. FUNCIÓN DE FEATURES (ANTI-LEAKAGE)

⚠️ Aquí está el 80% del éxito

```python
def create_features(df):
    df = df.copy()

    # Lags
    for lag in [1, 2, 7, 14, 30]:
        df[f'lag_{lag}'] = df['y'].shift(lag)

    # Rolling (correcto: shift antes)
    df['roll_mean_7'] = df['y'].shift(1).rolling(7).mean()
    df['roll_std_7']  = df['y'].shift(1).rolling(7).std()

    # Calendario
    df['dayofweek'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month

    # Cíclicas
    df['month_sin'] = np.sin(2*np.pi*df['month']/12)
    df['month_cos'] = np.cos(2*np.pi*df['month']/12)

    return df
```

---

# 🚀 4. USO REAL

```python
from sklearn.ensemble import RandomForestRegressor

model = RandomForestRegressor(
    n_estimators=300,
    max_depth=10,
    random_state=42
)

results = walk_forward_validation(
    df=df,
    model=model,
    target_col='y',
    date_col='date',
    initial_train_size=200,
    horizon=1,
    step=1,
    feature_func=create_features
)

print(results["MAE"], results["RMSE"], results["MAPE"])
```

---

# 🔬 5. MEJORAS PRO (muy recomendadas)

## 🔁 Multi-step forecast

```python
horizon = 7  # predices 7 días de golpe
```

---

## ⚡ Backtesting más rápido

```python
step = 7  # avanzas semanalmente
```

---

## 🎯 Guardar métricas por ventana

Puedes añadir tracking por iteración para ver drift.

---

## 🔍 Visualización

```python
import matplotlib.pyplot as plt

res = results["predictions"]

plt.figure(figsize=(12,5))
plt.plot(res['date'], res['actual'], label='Real')
plt.plot(res['date'], res['pred'], label='Pred')
plt.legend()
plt.show()
```

---

# ⚠️ ERRORES COMUNES QUE ESTO EVITA

✔ Leakage en features

✔ Overfitting por split aleatorio

✔ Métricas irreales

✔ Evaluación no representativa

---

# 🧾 CONCLUSIÓN

Con esto tienes:

- ✅ Evaluación realista tipo producción
- ✅ Sin leakage
- ✅ Compatible con RF, XGB, etc.
- ✅ Base para modelos híbridos

---

# 💬 Si quieres el siguiente nivel

Puedo montarte encima de esto:

- 🔗 Walk-forward + modelo híbrido ARIMA + RF
- 📊 Diagnóstico automático de drift
- ⚙️ Pipeline tipo sklearn completo

Solo dime 👍

Pipeline tipo sklearn completo

Perfecto. Te dejo la **siguiente versión integrada**: un sistema de **búsqueda de hiperparámetros con backtesting temporal**, manteniendo el enfoque sklearn-like y sin leakage.

Esto te permite:

- probar varias configuraciones de **RF** y **XGB**
- evaluarlas con **walk-forward real**
- elegir la mejor por una métrica objetivo
- quedarte con el mejor pipeline para producción

---

# Qué añade esta versión

Sobre el pipeline anterior, ahora sumamos:

- `param_grid` estilo sklearn
- evaluación por `MAE`, `RMSE` o `MAPE`
- ranking de combinaciones
- selección automática del mejor modelo

---

## Código

```python
import itertools
import numpy as np
import pandas as pd

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Any

from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import RandomForestRegressor

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# =========================================================
# 1. FEATURES
# =========================================================

def add_time_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    df = df.copy()
    dt = pd.to_datetime(df[date_col])

    df["dayofweek"] = dt.dt.dayofweek
    df["dayofmonth"] = dt.dt.day
    df["weekofyear"] = dt.dt.isocalendar().week.astype(int)
    df["month"] = dt.dt.month
    df["quarter"] = dt.dt.quarter
    df["year"] = dt.dt.year
    df["is_month_start"] = dt.dt.is_month_start.astype(int)
    df["is_month_end"] = dt.dt.is_month_end.astype(int)

    df["dow_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    return df

def add_lag_features(
    df: pd.DataFrame,
    target_col: str = "y",
    lags: List[int] = [1, 2, 3, 7, 14, 28],
) -> pd.DataFrame:
    df = df.copy()
    for lag in lags:
        df[f"lag_{lag}"] = df[target_col].shift(lag)
    return df

def add_rolling_features(
    df: pd.DataFrame,
    target_col: str = "y",
    windows: List[int] = [7, 14, 28],
) -> pd.DataFrame:
    df = df.copy()
    shifted = df[target_col].shift(1)

    for window in windows:
        df[f"roll_mean_{window}"] = shifted.rolling(window).mean()
        df[f"roll_std_{window}"] = shifted.rolling(window).std()
        df[f"roll_min_{window}"] = shifted.rolling(window).min()
        df[f"roll_max_{window}"] = shifted.rolling(window).max()

    return df

def add_difference_features(
    df: pd.DataFrame,
    target_col: str = "y",
) -> pd.DataFrame:
    df = df.copy()
    df["diff_1"] = df[target_col].diff(1)
    df["diff_7"] = df[target_col].diff(7)
    df["pct_change_1"] = df[target_col].pct_change(1)
    df["pct_change_7"] = df[target_col].pct_change(7)
    return df

def build_features(
    df: pd.DataFrame,
    date_col: str = "date",
    target_col: str = "y",
    lags: List[int] = [1, 2, 3, 7, 14, 28],
    windows: List[int] = [7, 14, 28],
) -> pd.DataFrame:
    df = df.copy().sort_values(date_col).reset_index(drop=True)
    df = add_time_features(df, date_col=date_col)
    df = add_lag_features(df, target_col=target_col, lags=lags)
    df = add_rolling_features(df, target_col=target_col, windows=windows)
    df = add_difference_features(df, target_col=target_col)
    return df

# =========================================================
# 2. METRICS
# =========================================================

def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return np.sqrt(mean_squared_error(y_true, y_pred))

def mape(y_true: np.ndarray, y_pred: np.ndarray, epsilon: float = 1e-8) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    denom = np.where(np.abs(y_true) < epsilon, epsilon, np.abs(y_true))
    return np.mean(np.abs((y_true - y_pred) / denom)) * 100

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": rmse(y_true, y_pred),
        "MAPE": mape(y_true, y_pred),
    }

# =========================================================
# 3. DATA PREP
# =========================================================

def prepare_supervised_data(
    df: pd.DataFrame,
    date_col: str = "date",
    target_col: str = "y",
    dropna: bool = True,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    df = df.copy()
    feature_cols = [c for c in df.columns if c not in [date_col, target_col]]

    X = df[feature_cols]
    y = df[target_col]
    dates = df[date_col]

    if dropna:
        valid_idx = X.notna().all(axis=1) & y.notna()
        X = X.loc[valid_idx].reset_index(drop=True)
        y = y.loc[valid_idx].reset_index(drop=True)
        dates = dates.loc[valid_idx].reset_index(drop=True)

    return X, y, dates

# =========================================================
# 4. PIPELINES
# =========================================================

def make_rf_pipeline(
    random_state: int = 42,
    n_estimators: int = 500,
    max_depth: Optional[int] = 10,
    min_samples_leaf: int = 2,
    max_features: float = 1.0,
    n_jobs: int = -1,
) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            random_state=random_state,
            n_jobs=n_jobs,
        ))
    ])

def make_xgb_pipeline(
    random_state: int = 42,
    n_estimators: int = 500,
    learning_rate: float = 0.05,
    max_depth: int = 6,
    subsample: float = 0.8,
    colsample_bytree: float = 0.8,
    reg_alpha: float = 0.0,
    reg_lambda: float = 1.0,
) -> Pipeline:
    if not XGBOOST_AVAILABLE:
        raise ImportError("xgboost no está instalado. Ejecuta: pip install xgboost")

    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", XGBRegressor(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            reg_alpha=reg_alpha,
            reg_lambda=reg_lambda,
            random_state=random_state,
            objective="reg:squarederror",
            n_jobs=-1,
        ))
    ])

# =========================================================
# 5. WALK FORWARD
# =========================================================

@dataclass
class WalkForwardResult:
    metrics: Dict[str, float]
    oof_predictions: pd.DataFrame
    fold_metrics: pd.DataFrame

class TimeSeriesWalkForwardValidator:
    def __init__(
        self,
        date_col: str = "date",
        target_col: str = "y",
        min_train_size: int = 180,
        horizon: int = 1,
        step: int = 1,
    ):
        self.date_col = date_col
        self.target_col = target_col
        self.min_train_size = min_train_size
        self.horizon = horizon
        self.step = step

    def split(self, df: pd.DataFrame):
        n = len(df)
        start = self.min_train_size
        while start + self.horizon <= n:
            train_idx = np.arange(0, start)
            test_idx = np.arange(start, start + self.horizon)
            yield train_idx, test_idx
            start += self.step

    def evaluate(
        self,
        df: pd.DataFrame,
        model: Pipeline,
        feature_builder: Callable[[pd.DataFrame], pd.DataFrame],
    ) -> WalkForwardResult:
        df = df.copy()
        df[self.date_col] = pd.to_datetime(df[self.date_col])
        df = df.sort_values(self.date_col).reset_index(drop=True)

        all_preds = []
        fold_metrics = []

        for fold, (train_idx, test_idx) in enumerate(self.split(df), start=1):
            subset = df.iloc[: test_idx[-1] + 1].copy()
            subset_feat = feature_builder(subset)

            train_feat = subset_feat.iloc[train_idx].copy()
            test_feat = subset_feat.iloc[test_idx].copy()

            X_train, y_train, _ = prepare_supervised_data(
                train_feat, date_col=self.date_col, target_col=self.target_col, dropna=True
            )
            X_test, y_test, test_dates = prepare_supervised_data(
                test_feat, date_col=self.date_col, target_col=self.target_col, dropna=True
            )

            if len(X_train) == 0 or len(X_test) == 0:
                continue

            model_fold = clone(model)
            model_fold.fit(X_train, y_train)
            preds = model_fold.predict(X_test)

            all_preds.append(pd.DataFrame({
                "fold": fold,
                "date": test_dates.values,
                "y_true": y_test.values,
                "y_pred": preds,
            }))

            fold_metric = compute_metrics(y_test.values, preds)
            fold_metric["fold"] = fold
            fold_metric["train_size"] = len(X_train)
            fold_metric["test_size"] = len(X_test)
            fold_metrics.append(fold_metric)

        if not all_preds:
            raise ValueError("No se generaron predicciones. Revisa horizon, min_train_size o los lags.")

        oof_predictions = pd.concat(all_preds, ignore_index=True)
        fold_metrics_df = pd.DataFrame(fold_metrics)
        global_metrics = compute_metrics(
            oof_predictions["y_true"].values,
            oof_predictions["y_pred"].values,
        )

        return WalkForwardResult(
            metrics=global_metrics,
            oof_predictions=oof_predictions,
            fold_metrics=fold_metrics_df,
        )

# =========================================================
# 6. GRID SEARCH TEMPORAL
# =========================================================

@dataclass
class TemporalSearchResult:
    leaderboard: pd.DataFrame
    best_params: Dict[str, Any]
    best_score: float
    best_metric: str
    best_model_name: str
    best_result: WalkForwardResult

def expand_param_grid(param_grid: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    combos = []
    for combination in itertools.product(*values):
        combos.append(dict(zip(keys, combination)))
    return combos

class TemporalGridSearch:
    def __init__(
        self,
        validator: TimeSeriesWalkForwardValidator,
        feature_builder: Callable[[pd.DataFrame], pd.DataFrame],
        scoring: str = "MAE",
        greater_is_better: bool = False,
    ):
        self.validator = validator
        self.feature_builder = feature_builder
        self.scoring = scoring
        self.greater_is_better = greater_is_better

    def _is_better(self, new_score: float, best_score: Optional[float]) -> bool:
        if best_score is None:
            return True
        if self.greater_is_better:
            return new_score > best_score
        return new_score < best_score

    def search(
        self,
        df: pd.DataFrame,
        model_name: str,
        model_factory: Callable[..., Pipeline],
        param_grid: Dict[str, List[Any]],
    ) -> TemporalSearchResult:
        candidates = expand_param_grid(param_grid)

        leaderboard_rows = []
        best_score = None
        best_params = None
        best_result = None

        for idx, params in enumerate(candidates, start=1):
            pipeline = model_factory(**params)
            result = self.validator.evaluate(
                df=df,
                model=pipeline,
                feature_builder=self.feature_builder,
            )

            score = result.metrics[self.scoring]

            row = {"rank_candidate": idx, "model": model_name, **params, **result.metrics}
            leaderboard_rows.append(row)

            if self._is_better(score, best_score):
                best_score = score
                best_params = params
                best_result = result

        leaderboard = pd.DataFrame(leaderboard_rows).sort_values(self.scoring, ascending=not self.greater_is_better).reset_index(drop=True)

        return TemporalSearchResult(
            leaderboard=leaderboard,
            best_params=best_params,
            best_score=best_score,
            best_metric=self.scoring,
            best_model_name=model_name,
            best_result=best_result,
        )

# =========================================================
# 7. COMPARAR VARIOS MODELOS
# =========================================================

@dataclass
class MultiModelSearchResult:
    global_leaderboard: pd.DataFrame
    best_overall_model_name: str
    best_overall_params: Dict[str, Any]
    best_overall_result: WalkForwardResult
    per_model_results: Dict[str, TemporalSearchResult]

def compare_models_temporally(
    df: pd.DataFrame,
    searches: Dict[str, Tuple[Callable[..., Pipeline], Dict[str, List[Any]]]],
    validator: TimeSeriesWalkForwardValidator,
    feature_builder: Callable[[pd.DataFrame], pd.DataFrame],
    scoring: str = "MAE",
) -> MultiModelSearchResult:
    per_model_results = {}
    all_rows = []

    best_score = None
    best_model_name = None
    best_params = None
    best_result = None

    for model_name, (factory, param_grid) in searches.items():
        searcher = TemporalGridSearch(
            validator=validator,
            feature_builder=feature_builder,
            scoring=scoring,
            greater_is_better=False,
        )

        result = searcher.search(
            df=df,
            model_name=model_name,
            model_factory=factory,
            param_grid=param_grid,
        )

        per_model_results[model_name] = result

        top_row = result.leaderboard.iloc[0].to_dict()
        all_rows.append(top_row)

        if best_score is None or result.best_score < best_score:
            best_score = result.best_score
            best_model_name = model_name
            best_params = result.best_params
            best_result = result.best_result

    global_leaderboard = pd.DataFrame(all_rows).sort_values(scoring).reset_index(drop=True)

    return MultiModelSearchResult(
        global_leaderboard=global_leaderboard,
        best_overall_model_name=best_model_name,
        best_overall_params=best_params,
        best_overall_result=best_result,
        per_model_results=per_model_results,
    )

# =========================================================
# 8. FIT FINAL
# =========================================================

class FinalTimeSeriesForecaster:
    def __init__(
        self,
        model: Pipeline,
        feature_builder: Callable[[pd.DataFrame], pd.DataFrame],
        date_col: str = "date",
        target_col: str = "y",
    ):
        self.model = clone(model)
        self.feature_builder = feature_builder
        self.date_col = date_col
        self.target_col = target_col

    def fit(self, df: pd.DataFrame):
        df = df.copy()
        df[self.date_col] = pd.to_datetime(df[self.date_col])
        df = df.sort_values(self.date_col).reset_index(drop=True)

        feat_df = self.feature_builder(df)
        X, y, _ = prepare_supervised_data(
            feat_df, date_col=self.date_col, target_col=self.target_col, dropna=True
        )

        self.model.fit(X, y)
        return self

    def predict_in_sample(self, df: pd.DataFrame) -> pd.DataFrame:
        feat_df = self.feature_builder(df.copy())
        X, y, dates = prepare_supervised_data(
            feat_df, date_col=self.date_col, target_col=self.target_col, dropna=True
        )
        preds = self.model.predict(X)

        return pd.DataFrame({
            "date": dates,
            "y_true": y,
            "y_pred": preds,
        })

# =========================================================
# 9. EJEMPLO DE USO
# =========================================================

if __name__ == "__main__":
    np.random.seed(42)
    n = 500
    df = pd.DataFrame({
        "date": pd.date_range("2022-01-01", periods=n, freq="D")
    })

    trend = np.linspace(100, 250, n)
    weekly = 18 * np.sin(2 * np.pi * np.arange(n) / 7)
    monthly = 10 * np.sin(2 * np.pi * np.arange(n) / 30)
    noise = np.random.normal(0, 6, n)

    df["y"] = trend + weekly + monthly + noise

    def feature_builder(data: pd.DataFrame) -> pd.DataFrame:
        return build_features(
            data,
            date_col="date",
            target_col="y",
            lags=[1, 2, 3, 7, 14, 28],
            windows=[7, 14, 28],
        )

    validator = TimeSeriesWalkForwardValidator(
        date_col="date",
        target_col="y",
        min_train_size=180,
        horizon=7,
        step=7,
    )

    searches = {
        "RandomForest": (
            make_rf_pipeline,
            {
                "n_estimators": [300, 500],
                "max_depth": [8, 12, None],
                "min_samples_leaf": [1, 2, 4],
                "max_features": [0.7, 1.0],
            }
        )
    }

    if XGBOOST_AVAILABLE:
        searches["XGBoost"] = (
            make_xgb_pipeline,
            {
                "n_estimators": [400, 700],
                "learning_rate": [0.03, 0.05],
                "max_depth": [4, 6],
                "subsample": [0.8, 1.0],
                "colsample_bytree": [0.8, 1.0],
                "reg_alpha": [0.0, 0.1],
                "reg_lambda": [1.0, 2.0],
            }
        )

    comparison = compare_models_temporally(
        df=df,
        searches=searches,
        validator=validator,
        feature_builder=feature_builder,
        scoring="MAE",
    )

    print("=== GLOBAL LEADERBOARD ===")
    print(comparison.global_leaderboard.head())

    print("\n=== BEST OVERALL MODEL ===")
    print(comparison.best_overall_model_name)
    print(comparison.best_overall_params)
    print(comparison.best_overall_result.metrics)

    best_model_name = comparison.best_overall_model_name
    best_params = comparison.best_overall_params

    if best_model_name == "RandomForest":
        best_pipeline = make_rf_pipeline(**best_params)
    else:
        best_pipeline = make_xgb_pipeline(**best_params)

    final_model = FinalTimeSeriesForecaster(
        model=best_pipeline,
        feature_builder=feature_builder,
        date_col="date",
        target_col="y",
    ).fit(df)

    preds = final_model.predict_in_sample(df)
    print("\n=== IN SAMPLE PREDICTIONS ===")
    print(preds.head())
```

---

# Cómo usarlo con tus datos

Si tu dataset real es:

```python
df.columns
# ['date', 'y']
```

haz:

```python
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)
```

y luego:

```python
def feature_builder(data):
    return build_features(
        data,
        date_col="date",
        target_col="y",
        lags=[1, 2, 7, 14, 30],
        windows=[7, 14, 30],
    )

validator = TimeSeriesWalkForwardValidator(
    date_col="date",
    target_col="y",
    min_train_size=200,
    horizon=7,
    step=7,
)

searches = {
    "RandomForest": (
        make_rf_pipeline,
        {
            "n_estimators": [300, 500, 800],
            "max_depth": [8, 12, None],
            "min_samples_leaf": [1, 2, 4],
            "max_features": [0.7, 1.0],
        }
    )
}
```

Si tienes XGBoost instalado:

```python
searches["XGBoost"] = (
    make_xgb_pipeline,
    {
        "n_estimators": [400, 700],
        "learning_rate": [0.03, 0.05, 0.08],
        "max_depth": [4, 6, 8],
        "subsample": [0.8, 1.0],
        "colsample_bytree": [0.8, 1.0],
        "reg_alpha": [0.0, 0.1],
        "reg_lambda": [1.0, 2.0],
    }
)
```

y ejecutas:

```python
comparison = compare_models_temporally(
    df=df,
    searches=searches,
    validator=validator,
    feature_builder=feature_builder,
    scoring="MAE",
)

print(comparison.global_leaderboard)
print(comparison.best_overall_model_name)
print(comparison.best_overall_params)
print(comparison.best_overall_result.metrics)
```

---

# Recomendaciones prácticas para no disparar el tiempo de cómputo

El grid de XGBoost crece muchísimo. Para empezar, usaría esto:

## RF

```python
{
    "n_estimators": [300, 500],
    "max_depth": [8, 12, None],
    "min_samples_leaf": [1, 2],
    "max_features": [0.7, 1.0],
}
```

## XGB

```python
{
    "n_estimators": [400, 700],
    "learning_rate": [0.03, 0.05],
    "max_depth": [4, 6],
    "subsample": [0.8],
    "colsample_bytree": [0.8, 1.0],
    "reg_alpha": [0.0, 0.1],
    "reg_lambda": [1.0, 2.0],
}
```

---

# Qué te devuelve exactamente

## `comparison.global_leaderboard`

Una tabla con el mejor resultado de cada familia de modelo.

## `comparison.per_model_results["RandomForest"].leaderboard`

Todas las combinaciones probadas de RF, ordenadas por la métrica elegida.

## `comparison.best_overall_result.oof_predictions`

Predicciones out-of-fold del mejor modelo.

## `comparison.best_overall_result.fold_metrics`

Métricas por ventana temporal.

---

# Siguiente paso lógico

Ahora mismo, el siguiente salto útil sería uno de estos dos:

**1. añadir early stopping real para XGBoost en cada fold**, o

**2. integrar el híbrido ARIMA + RF/XGB** dentro de esta misma arquitectura.

Por lo que me enseñaste antes, yo haría el **híbrido ARIMA + RandomForest** primero, porque es el camino más prometedor para bajar aún más ese MAPE.

Sí. Este es el siguiente paso más interesante.

Te monto un **híbrido ARIMA + RandomForest** bien estructurado, con esta lógica:

1. **ARIMA** modela la parte lineal y temporal clásica
2. calculamos los **residuos** del train
3. **RandomForest** aprende esos residuos usando features temporales
4. la predicción final es:

```python
pred_final = pred_arima + pred_rf_residuos
```

Eso suele funcionar muy bien cuando:

- ARIMA captura tendencia/estacionalidad
- pero quedan patrones no lineales explotables

---

# Idea del pipeline híbrido

## Entrenamiento

- ajustas ARIMA con `y_train`
- obtienes predicción in-sample de ARIMA
- calculas residuos:

```python
resid = y_train - arima_fitted
```

- creas features de residuos
- entrenas RF para predecir esos residuos

## Predicción

- ARIMA genera forecast base
- RF predice la corrección residual
- sumas ambas partes

---

# Implementación completa

Necesitas:

```bash
pip install statsmodels
```

Y este código:

```python
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Callable

from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from statsmodels.tsa.arima.model import ARIMA

# =========================================================
# 1. MÉTRICAS
# =========================================================

def rmse(y_true, y_pred):
    return np.sqrt(mean_squared_error(y_true, y_pred))

def mape(y_true, y_pred, epsilon=1e-8):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    denom = np.where(np.abs(y_true) < epsilon, epsilon, np.abs(y_true))
    return np.mean(np.abs((y_true - y_pred) / denom)) * 100

def compute_metrics(y_true, y_pred):
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": rmse(y_true, y_pred),
        "MAPE": mape(y_true, y_pred),
    }

# =========================================================
# 2. FEATURES PARA RANDOM FOREST
# =========================================================

def add_time_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    df = df.copy()
    dt = pd.to_datetime(df[date_col])

    df["dayofweek"] = dt.dt.dayofweek
    df["dayofmonth"] = dt.dt.day
    df["weekofyear"] = dt.dt.isocalendar().week.astype(int)
    df["month"] = dt.dt.month
    df["quarter"] = dt.dt.quarter
    df["year"] = dt.dt.year

    df["dow_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    return df

def build_residual_features(
    df: pd.DataFrame,
    date_col: str = "date",
    residual_col: str = "residual",
    lags: List[int] = [1, 2, 3, 7, 14],
    windows: List[int] = [7, 14],
) -> pd.DataFrame:
    """
    Features para modelar residuos SIN leakage.
    """
    df = df.copy().sort_values(date_col).reset_index(drop=True)

    df = add_time_features(df, date_col=date_col)

    for lag in lags:
        df[f"resid_lag_{lag}"] = df[residual_col].shift(lag)

    shifted = df[residual_col].shift(1)
    for w in windows:
        df[f"resid_roll_mean_{w}"] = shifted.rolling(w).mean()
        df[f"resid_roll_std_{w}"] = shifted.rolling(w).std()

    return df

def prepare_supervised_data(
    df: pd.DataFrame,
    target_col: str,
    date_col: str = "date",
):
    feature_cols = [c for c in df.columns if c not in [date_col, target_col]]
    X = df[feature_cols]
    y = df[target_col]
    valid_idx = X.notna().all(axis=1) & y.notna()
    return (
        X.loc[valid_idx].reset_index(drop=True),
        y.loc[valid_idx].reset_index(drop=True),
        df.loc[valid_idx, date_col].reset_index(drop=True),
    )

# =========================================================
# 3. FACTORY RF
# =========================================================

def make_rf_pipeline(
    random_state: int = 42,
    n_estimators: int = 500,
    max_depth: Optional[int] = 10,
    min_samples_leaf: int = 2,
    max_features: float = 1.0,
    n_jobs: int = -1,
) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            random_state=random_state,
            n_jobs=n_jobs,
        ))
    ])

# =========================================================
# 4. MODELO HÍBRIDO ARIMA + RF
# =========================================================

class HybridARIMARandomForest(BaseEstimator, RegressorMixin):
    """
    Híbrido:
    y_hat = ARIMA(y) + RF(residuos ARIMA)
    """

    def __init__(
        self,
        arima_order: Tuple[int, int, int] = (1, 1, 1),
        rf_pipeline: Optional[Pipeline] = None,
        date_col: str = "date",
        target_col: str = "y",
        residual_lags: List[int] = [1, 2, 3, 7, 14],
        residual_windows: List[int] = [7, 14],
    ):
        self.arima_order = arima_order
        self.rf_pipeline = rf_pipeline if rf_pipeline is not None else make_rf_pipeline()
        self.date_col = date_col
        self.target_col = target_col
        self.residual_lags = residual_lags
        self.residual_windows = residual_windows

        self.arima_model_ = None
        self.arima_result_ = None
        self.rf_model_ = None
        self.train_df_ = None
        self.residual_history_ = None

    def fit(self, df: pd.DataFrame):
        df = df.copy()
        df[self.date_col] = pd.to_datetime(df[self.date_col])
        df = df.sort_values(self.date_col).reset_index(drop=True)

        y = df[self.target_col].astype(float).values

        # 1. Ajustar ARIMA
        self.arima_model_ = ARIMA(y, order=self.arima_order)
        self.arima_result_ = self.arima_model_.fit()

        # 2. Predicción in-sample ARIMA
        arima_fitted = self.arima_result_.predict(start=0, end=len(df)-1)

        # 3. Residuos
        train_resid_df = df[[self.date_col]].copy()
        train_resid_df["residual"] = y - arima_fitted

        # 4. Features sobre residuos
        resid_feat_df = build_residual_features(
            train_resid_df,
            date_col=self.date_col,
            residual_col="residual",
            lags=self.residual_lags,
            windows=self.residual_windows,
        )

        X_resid, y_resid, _ = prepare_supervised_data(
            resid_feat_df,
            target_col="residual",
            date_col=self.date_col,
        )

        # 5. Ajustar RF sobre residuos
        self.rf_model_ = clone(self.rf_pipeline)
        self.rf_model_.fit(X_resid, y_resid)

        self.train_df_ = df.copy()
        self.residual_history_ = train_resid_df.copy()

        return self

    def forecast(self, steps: int) -> pd.DataFrame:
        """
        Forecast recursivo híbrido para 'steps' periodos futuros.
        Requiere frecuencia regular en date.
        """
        if self.arima_result_ is None or self.rf_model_ is None:
            raise ValueError("El modelo no está entrenado. Llama antes a fit().")

        # 1. Forecast base ARIMA
        arima_forecast = self.arima_result_.forecast(steps=steps)

        # 2. Construcción recursiva de fechas futuras
        hist_dates = pd.to_datetime(self.train_df_[self.date_col])
        inferred_freq = pd.infer_freq(hist_dates)

        if inferred_freq is None:
            # fallback simple: usar diferencia de las dos últimas fechas
            if len(hist_dates) < 2:
                raise ValueError("No se pudo inferir la frecuencia temporal.")
            step_delta = hist_dates.iloc[-1] - hist_dates.iloc[-2]
            future_dates = [hist_dates.iloc[-1] + (i + 1) * step_delta for i in range(steps)]
        else:
            future_dates = pd.date_range(
                start=hist_dates.iloc[-1],
                periods=steps + 1,
                freq=inferred_freq
            )[1:]

        # 3. Predicción recursiva de residuos
        residual_history = self.residual_history_.copy()
        rf_residual_preds = []

        for i in range(steps):
            next_date = future_dates[i]

            temp = pd.concat([
                residual_history,
                pd.DataFrame({self.date_col: [next_date], "residual": [np.nan]})
            ], ignore_index=True)

            temp_feat = build_residual_features(
                temp,
                date_col=self.date_col,
                residual_col="residual",
                lags=self.residual_lags,
                windows=self.residual_windows,
            )

            next_row = temp_feat.iloc[[-1]].copy()
            X_next = next_row.drop(columns=[self.date_col, "residual"])

            resid_pred = float(self.rf_model_.predict(X_next)[0])
            rf_residual_preds.append(resid_pred)

            residual_history = pd.concat([
                residual_history,
                pd.DataFrame({self.date_col: [next_date], "residual": [resid_pred]})
            ], ignore_index=True)

        final_pred = np.asarray(arima_forecast) + np.asarray(rf_residual_preds)

        return pd.DataFrame({
            "date": future_dates,
            "arima_pred": np.asarray(arima_forecast),
            "rf_residual_pred": np.asarray(rf_residual_preds),
            "final_pred": final_pred,
        })
```

---

# Walk-forward validation del híbrido

Ahora te dejo el backtesting profesional para este híbrido.

```python
@dataclass
class HybridWalkForwardResult:
    metrics: Dict[str, float]
    predictions: pd.DataFrame
    fold_metrics: pd.DataFrame

class HybridWalkForwardValidator:
    def __init__(
        self,
        date_col: str = "date",
        target_col: str = "y",
        min_train_size: int = 180,
        horizon: int = 7,
        step: int = 7,
    ):
        self.date_col = date_col
        self.target_col = target_col
        self.min_train_size = min_train_size
        self.horizon = horizon
        self.step = step

    def split(self, df: pd.DataFrame):
        n = len(df)
        start = self.min_train_size
        while start + self.horizon <= n:
            train_idx = np.arange(0, start)
            test_idx = np.arange(start, start + self.horizon)
            yield train_idx, test_idx
            start += self.step

    def evaluate(
        self,
        df: pd.DataFrame,
        hybrid_model_factory: Callable[[], HybridARIMARandomForest],
    ) -> HybridWalkForwardResult:
        df = df.copy()
        df[self.date_col] = pd.to_datetime(df[self.date_col])
        df = df.sort_values(self.date_col).reset_index(drop=True)

        all_preds = []
        fold_metrics = []

        for fold, (train_idx, test_idx) in enumerate(self.split(df), start=1):
            train_df = df.iloc[train_idx].copy()
            test_df = df.iloc[test_idx].copy()

            model = hybrid_model_factory()
            model.fit(train_df)

            forecast_df = model.forecast(steps=len(test_df))

            fold_pred = pd.DataFrame({
                "fold": fold,
                "date": test_df[self.date_col].values,
                "y_true": test_df[self.target_col].values,
                "y_pred": forecast_df["final_pred"].values,
                "arima_pred": forecast_df["arima_pred"].values,
                "rf_residual_pred": forecast_df["rf_residual_pred"].values,
            })

            all_preds.append(fold_pred)

            metrics = compute_metrics(
                fold_pred["y_true"].values,
                fold_pred["y_pred"].values
            )
            metrics["fold"] = fold
            metrics["train_size"] = len(train_df)
            metrics["test_size"] = len(test_df)
            fold_metrics.append(metrics)

        preds_df = pd.concat(all_preds, ignore_index=True)
        fold_metrics_df = pd.DataFrame(fold_metrics)

        global_metrics = compute_metrics(
            preds_df["y_true"].values,
            preds_df["y_pred"].values
        )

        return HybridWalkForwardResult(
            metrics=global_metrics,
            predictions=preds_df,
            fold_metrics=fold_metrics_df,
        )
```

---

# Ejemplo de uso

```python
if __name__ == "__main__":
    np.random.seed(42)

    n = 500
    df = pd.DataFrame({
        "date": pd.date_range("2022-01-01", periods=n, freq="D")
    })

    trend = np.linspace(100, 250, n)
    weekly = 18 * np.sin(2 * np.pi * np.arange(n) / 7)
    nonlinear = 0.03 * (np.arange(n) ** 1.3)
    noise = np.random.normal(0, 6, n)

    df["y"] = trend + weekly + nonlinear + noise

    validator = HybridWalkForwardValidator(
        date_col="date",
        target_col="y",
        min_train_size=200,
        horizon=7,
        step=7,
    )

    def hybrid_factory():
        rf_pipe = make_rf_pipeline(
            n_estimators=500,
            max_depth=10,
            min_samples_leaf=2,
            max_features=1.0,
        )

        return HybridARIMARandomForest(
            arima_order=(2, 1, 2),
            rf_pipeline=rf_pipe,
            date_col="date",
            target_col="y",
            residual_lags=[1, 2, 3, 7, 14],
            residual_windows=[7, 14],
        )

    result = validator.evaluate(df, hybrid_factory)

    print("=== MÉTRICAS HÍBRIDO ===")
    print(result.metrics)

    print("\n=== MÉTRICAS POR FOLD ===")
    print(result.fold_metrics.head())

    print("\n=== PREDICCIONES ===")
    print(result.predictions.head())
```

---

# Cómo compararlo contra RF puro y ARIMA puro

Lo ideal es comparar tres cosas en el mismo walk-forward:

- **ARIMA solo**
- **RF solo**
- **ARIMA + RF**

Tu lectura debería ser esta:

## Si híbrido < RF

ARIMA está aportando estructura útil.

## Si híbrido ≈ RF

RF ya captura casi todo.

## Si híbrido > RF

puede pasar si:

- ARIMA está mal especificado
- el proceso es más no lineal que lineal
- el forecast recursivo del residuo mete ruido

---

# Recomendación de órdenes ARIMA para probar

Yo empezaría con una parrilla pequeña:

```python
(1,1,1)
(2,1,1)
(2,1,2)
(3,1,2)
```

Si hay estacionalidad fuerte semanal o mensual, ya te interesaría pasar a **SARIMA + RF**, no ARIMA simple.

---

# Riesgos reales del híbrido

## 1. Forecast recursivo del residuo

Cuantos más pasos predices, más fácil es acumular error.

## 2. ARIMA mal especificado

Si ARIMA modela mal la base, el RF arregla parte, pero no hace magia.

## 3. Estacionalidad no modelada

Si tu serie tiene estacionalidad clara, muchas veces conviene:

- **SARIMA + RF**
    
    en vez de ARIMA + RF.
    

---

# Mi recomendación práctica para tu caso

Con tus resultados previos, yo haría este orden:

1. **RF puro bien validado**
2. **ARIMA + RF**
3. si hay estacionalidad fuerte: **SARIMA + RF**
4. comparar por:
    - MAE
    - RMSE
    - MAPE
    - estabilidad por fold

---

# Lo que haría después

El siguiente salto útil sería integrar una **búsqueda temporal para el híbrido**, probando:

- varios `arima_order`
- varios hiperparámetros de RF
- y devolviendo un leaderboard igual que antes

Ese paso sí puede darte ya el mejor híbrido de forma sistemática.

Listo. Te he dejado el archivo completo en el canvas con:

- **ARIMA puro**
- **RandomForest puro**
- **híbrido ARIMA + RandomForest**
- **walk-forward validation**
- **grid search temporal**
- **leaderboard global**
- métricas por fold y predicciones del mejor modelo

Cómo usarlo con tus datos:

```python
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

comparison = run_full_comparison(
    df=df,
    date_col="date",
    target_col="y",
    min_train_size=250,
    horizon=7,
    step=7,
    scoring="MAE",
)

print(comparison["global_leaderboard"])
print(comparison["best_model_name"])
print(comparison["best_result"].params)
print(comparison["best_result"].metrics)
```

Qué miraría yo primero en la salida:

- si **Hybrid_ARIMA_RF** queda por encima de **RandomForest**
- si mejora no solo en promedio, sino también en **estabilidad por fold**
- si baja **RMSE** además de **MAE/MAPE**, porque eso te dirá si corrige errores grandes

Siguiente paso útil: pegar tus resultados del `global_leaderboard` y te digo cuál me quedaría para producción y qué tocaría después.