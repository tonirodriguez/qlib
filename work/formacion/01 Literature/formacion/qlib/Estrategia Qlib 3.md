# Estrategia Qlib 3

Hasta ahora tenemos un pipeline bastante sólido y “production-like” dentro de Qlib:

- actualización incremental diaria robusta
- refuerzo mensual automático
- separación research / live
- inferencia reproducible
- generación de órdenes desacoplada

👉 Lo siguiente que realmente marca la diferencia (cuando pases a dinero real) suele ser:

- añadir **filtros de liquidez (ADV / volumen)** en `build_target_weights`
- controlar **turnover máximo** (para no sobreoperar)
- meter un pequeño **delay (T+1 execution)** en el backtest para evitar lookahead implícito
- y validar que el dataset no tiene gaps silenciosos (esto es clave con Yahoo)

Si quieres, el siguiente paso útil sería uno de estos tres:

1. **añadir control de turnover + rebalance buffer** (muy importante en real)
2. **integrar posiciones reales del broker y generar órdenes delta**
3. **alinear backtest vs ejecución real (slippage, timing, etc.)**

Dime por cuál quieres ir y lo bajamos a código 👍

# Definición de LABEL para Alpha158

Cuando utilizas el dataset **Alpha158** en Qlib, la etiqueta (label) por defecto es el **rendimiento residual a 6 días** (o simplemente el retorno futuro suavizado), identificado técnicamente como:

`LABEL0`

Sin embargo, para entender qué significa realmente ese `LABEL0` en el contexto de Alpha158, aquí tienes el desglose de cómo se calcula y cómo puedes ver su fórmula exacta:

---

## 1. El cálculo detrás de la Label

En la configuración estándar de Qlib para Alpha158 (que suele encontrarse en los archivos `.yaml` de ejemplo), la label se define mediante la expresión:

`Ref($close, -2) / Ref($close, -1) - 1`

- **Interpretación:** Es el retorno del precio de cierre entre el día $T+2$ y el día $T+1$.
- **¿Por qué no $T+1$?** Qlib utiliza este desfase por defecto para evitar el **look-ahead bias** y simular que compras al precio de cierre del día siguiente a recibir la señal, vendiendo un día después.

---

## 2. Dónde encontrar la definición exacta

Si quieres estar 100% seguro de qué label está usando tu ejecución actual, debes mirar el archivo de configuración del dataset. Generalmente, Alpha158 hereda la configuración de una sección llamada `labels` en el YAML:

YAML

`data_handler_config: &data_handler_config
    start_time: 2008-01-01
    end_time: 2020-08-01
    fit_start_time: 2008-01-01
    fit_end_time: 2014-12-31
    instruments: *instruments
    tuple_config:
        # AQUÍ SE DEFINE LA LABEL
        - ["Ref($close, -2) / Ref($close, -1) - 1"] 
        - ["LABEL0"]`

---

## 3. Cómo acceder a ella desde código

Si ya has cargado el dataset y quieres ver los valores de la label directamente en tu DataFrame de Pandas, puedes hacerlo así:

Python

`from qlib.data.dataset.handler import DataHandlerLP

# Suponiendo que tienes tu handler configurado
df = handler.fetch()
# La label suele ser una multi-índice: (instrumento, fecha)
print(df['LABEL0'])`

---

## Notas importantes sobre Alpha158

1. **Normalización:** Qlib suele aplicar un proceso de **CSZScore** (Cross-Sectional Z-Score) a las labels durante el entrenamiento para que el modelo aprenda la posición relativa del stock frente al mercado, no el retorno absoluto.
2. **Personalización:** Puedes cambiar `LABEL0` por cualquier otra fórmula. Por ejemplo, si quieres predecir el retorno a 5 días, podrías usar:
    
    `Ref($close, -6) / Ref($close, -1) - 1`
    
3. **Alpha158 vs Alpha360:** Mientras que Alpha360 usa datos "crudos" (vWAP, close, open...), Alpha158 ya incluye fórmulas precalculadas (como el RSI, promedios móviles, etc.), pero ambos suelen compartir la misma estructura de `LABEL0`.

¿Estás intentando entrenar un modelo y te da valores `NaN` en la label o simplemente necesitas identificar la columna para un análisis de correlación?

Necesito identificar la columna para un análisis de correlación

Para tu análisis de correlación, la columna que buscas se llama exactamente **`LABEL0`**.

En el ecosistema de Qlib, cuando procesas un dataset como **Alpha158**, el resultado es un DataFrame de Pandas con un multi-índice (`datetime`, `instrument`). Las columnas se dividen en dos grupos: los *features* (los 158 factores) y la *label*.

Aquí tienes cómo identificarla y extraerla correctamente según tu caso de uso:

### 1. Identificación en el DataFrame

Si haces un `df.head()`, verás que las columnas tienen una estructura jerárquica. La columna de la etiqueta aparecerá bajo el nombre:

- **Nombre de columna:** `LABEL0`
- **Significado:** Retorno residual futuro (normalmente $T+2$ respecto a $T+1$).

### 2. Código para extraerla y calcular correlación

Si quieres calcular la correlación de todos los factores de Alpha158 con la etiqueta, puedes usar este fragmento:

Python

`# Suponiendo que 'dataset' es tu objeto de Qlib ya cargado
df = dataset.prepare("train", col_set=["feature", "label"])

# Si el DataFrame tiene MultiIndex en las columnas:
# A veces Qlib devuelve (feature, KAMA) o (label, LABEL0)
features = df['feature']
label = df['label']['LABEL0']

# Calcular correlación de Spearman (más robusta para Alpha factors)
correlations = features.corrwith(label, method='spearman')

# Ver los 10 factores más correlacionados con el precio futuro
print(correlations.sort_values(ascending=False).head(10))`

---

### 3. Ojo con los NaNs en Alpha158

Para un análisis de correlación válido, debes tener en cuenta dos cosas que suelen "ensuciar" los resultados en Qlib:

1. **Valores Nulos:** Alpha158 usa medias móviles largas (como `MA60`). Esto significa que las primeras 60 filas de cada stock serán `NaN`.
2. **Infinitos:** Al calcular ratios, algunos factores pueden devolver `inf`.

**Limpieza rápida antes de la correlación:**

Python

`# Limpiar datos para que la correlación no de error o NaN
df_clean = df.replace([np.inf, -np.inf], np.nan).dropna()`

---

### ¿Cómo interpretar los resultados?

En el análisis de factores (*Factor IC - Information Coefficient*):

- Una correlación (IC) superior a **0.02 - 0.05** ya se considera un factor predictivo muy bueno en mercados financieros.
- Si ves correlaciones de **0.8 o 0.9**, cuidado: probablemente tienes **look-ahead bias** (el factor está usando información del futuro que la etiqueta ya contiene).

¿Te interesa que te pase un script para graficar la evolución de esta correlación a lo largo del tiempo (lo que en Qlib llaman *IC IR*)?

Si por favor

Aquí tienes un script completo para realizar ese análisis. En el mundo del trading cuantitativo, esta correlación se conoce como **IC (Information Coefficient)**.

Este script no solo calcula la correlación estática, sino que analiza el **IC a lo largo del tiempo**, que es la métrica real para saber si un factor de Alpha158 es estable o si su éxito es solo cuestión de suerte en un mes concreto.

### Script de Análisis de Correlación (IC Analysis)

Python

`import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Extraer los datos (Asumiendo que ya tienes el DataFrame 'df')
# Separamos las columnas de features y la label
features = df['feature']
label = df['label']['LABEL0']

# 2. Limpieza de seguridad
# Eliminamos filas donde la label sea NaN (el final del dataset)
# y donde los features tengan nulos (el inicio por medias móviles)
valid_idx = label.notna() & features.notna().all(axis=1)
features_clean = features[valid_idx]
label_clean = label[valid_idx]

# 3. Correlación de Spearman Global (Rango)
# Usamos Spearman porque las relaciones en bolsa no suelen ser lineales
ic_global = features_clean.corrwith(label_clean, method='spearman')

# 4. Análisis de "IC Time Series" (Correlación por día)
# Esto es lo más importante: ver si el factor funciona siempre
ic_time_series = features_clean.groupby(level='datetime').apply(
    lambda x: x.corrwith(label_clean.loc[x.index], method='spearman')
)

# 5. Visualización de los Top 10 Factores
plt.figure(figsize=(12, 6))
top_10 = ic_global.abs().sort_values(ascending=False).head(10)
sns.barplot(x=top_10.values, y=top_10.index, palette='viridis')
plt.title('Top 10 Factores de Alpha158 por Valor Absoluto de IC (Spearman)')
plt.xlabel('Information Coefficient (IC)')
plt.show()

# 6. Estadísticas clave
print(f"IC Promedio Global: {ic_global.mean():.4f}")
print(f"IC IR (Information Ratio): {(ic_time_series.mean() / ic_time_series.std()).mean():.4f}")`

---

### ¿Cómo interpretar estos resultados para Alpha158?

Al realizar la correlación con `LABEL0`, debes fijarte en tres métricas que Qlib valora mucho:

1. **IC Mean:** Es la correlación media. Como te mencioné antes, un valor de **0.05** es excelente. Si ves algo cercano a **0.10**, tienes un factor "estrella".
2. **IC IR (Information Ratio):** Se calcula como `mean(IC) / std(IC)`. Mide la **consistencia**. Un factor puede tener una correlación alta en promedio pero ser muy volátil (un mes funciona y otro te arruina). Un IR > 0.5 es un muy buen indicador.
3. **Rank IC:** Es lo que estamos calculando con el método `spearman`. Es preferible al de Pearson porque a los modelos de Qlib (como LightGBM) les importa más el **orden (ranking)** de los stocks que el valor exacto del retorno.

### Un detalle sobre los nombres en Alpha158

En tu análisis verás nombres como `KAMA5`, `RSI10`, `WVMA20`.

- Si la correlación es **positiva**: a mayor valor del indicador, mayor retorno esperado.
- Si la correlación es **negativa**: el indicador actúa como un oscilador de reversión (ej. un RSI muy alto correlaciona con caídas próximas).

¿Quieres que analicemos algún factor específico de los 158 que te esté dando resultados extraños?

¿Cual es la label cuando utilizamos Alpha360?

Al igual que en Alpha158, la etiqueta por defecto en **Alpha360** es:

**`LABEL0`**

Aunque el nombre sea idéntico, es fundamental entender que en Qlib, `Alpha360` y `Alpha158` son configuraciones de **características** (inputs), pero la **etiqueta** (objetivo) suele definirse de forma global en el archivo de configuración `.yaml` que estés utilizando.

---

### ¿Qué representa exactamente esta Label?

En la mayoría de las configuraciones oficiales de Qlib para el mercado de EE. UU. o China usando Alpha360, `LABEL0` se define como el **retorno logarítmico suavizado y desplazado**. La fórmula estándar suele ser:

$\text{LABEL0} = \frac{\text{Ref}(\$close, -2)}{\text{Ref}(\$close, -1)} - 1$

Esta fórmula se traduce como: **el rendimiento que obtendrías si compraras al precio de cierre de mañana y vendieras al precio de cierre de pasado mañana.**

### Diferencias clave entre Alpha360 y Alpha158 en relación a la Label

Aunque la label sea la misma, tu análisis de correlación se comportará de forma distinta debido a la naturaleza de los datos:

| **Característica** | **Alpha360** | **Alpha158** |
| --- | --- | --- |
| **Tipo de datos** | Datos "crudos" (Open, High, Low, Close, VWAP) | Factores procesados (RSI, MA, KDJ, etc.) |
| **Ventana temporal** | Mira hacia atrás 60 días para cada precio (60 días $\times$ 6 precios = 360) | Mira diferentes ventanas (5, 10, 20, 60 días) |
| **Correlación esperada** | Suele ser **más baja** individualmente por ser datos crudos. | Suele ser **más alta** en factores específicos ya procesados. |

---

### Cómo extraer la Label específicamente para Alpha360

Si estás cargando el dataset desde el archivo de configuración, puedes identificarla así:

Python

`from qlib.data.dataset.loader import QlibDataLoader

# En Alpha360, la configuración de la label suele estar separada
# Puedes forzar la carga de la label de esta manera:
data_loader = QlibDataLoader(config={
    "feature": ["alpha360"], # Esto carga los 360 inputs
    "label": ["Ref($close, -2) / Ref($close, -1) - 1"] # Esto define la LABEL0
})

df = data_loader.load(instruments="SP500", start_time="2023-01-01", end_time="2023-12-31")
print(df['label'].columns) # Verás ['LABEL0']`

### Un consejo para tu análisis de correlación

Dado que Alpha360 contiene el precio de cierre de los últimos 60 días (por ejemplo, `close.0`, `close.1`... hasta `close.59`), verás que la correlación de `LABEL0` con los precios más cercanos (`close.0`) suele ser más ruidosa que con los factores técnicos ya "masticados" de Alpha158.

Para Alpha360, te recomiendo calcular el **Rank IC** agrupando por fecha, ya que los precios brutos tienen mucha autocorrelación y pueden engañar en un análisis de correlación simple.

¿Has notado alguna diferencia significativa en el rendimiento de tus modelos al cambiar de Alpha158 a Alpha360?

## ¿Cómo podria definir una label que fuera el rendimiento de los 5 próximos días?

Para definir el rendimiento de los próximos 5 días en Qlib, debes ajustar la expresión de la label en tu configuración para que calcule el retorno entre el precio actual (o el del cierre de mañana) y el precio de 5 días después.

En Qlib, esto se hace con la función `Ref(ticker, periodo)`. Recuerda que en Qlib, los números negativos en `Ref` miran hacia el **futuro**.

### 1. La fórmula técnica

Si quieres el rendimiento desde el precio de cierre de mañana ($T+1$) hasta el cierre dentro de 5 días después de ese momento ($T+6$), la fórmula es:

$$\text{Retorno}_{5d} = \frac{\text{Ref}(\$close, -6)}{\text{Ref}(\$close, -1)} - 1$$

### 2. Cómo implementarlo en el archivo YAML

Si usas archivos de configuración (la forma estándar de Qlib), busca la sección `data_handler_config` y cámbiala así:

YAML

`data_handler_config: &data_handler_config
    # ... otras configuraciones ...
    label: [
        "Ref($close, -6) / Ref($close, -1) - 1"
    ]
    label_names: ["LABEL_5D"]`

### 3. Cómo implementarlo directamente en Python

Si estás cargando los datos dinámicamente con código, puedes definirlo al vuelo:

Python

`import qlib
from qlib.data.dataset.loader import QlibDataLoader

# Definimos la expresión de la label
label_expression = "Ref($close, -6) / Ref($close, -1) - 1"

data_loader = QlibDataLoader(config={
    "feature": ["alpha158"], # o alpha360
    "label": [label_expression]
})

# Al cargar, la columna se llamará LABEL0 por defecto, 
# pero contendrá tu cálculo de 5 días.
df = data_loader.load(instruments="all", start_time="2020-01-01", end_time="2023-12-31")`

---

### ¿Por qué usamos -6 y -1?

Es vital entender el desplazamiento para no cometer errores de **look-ahead bias**:

- **`Ref($close, -1)`**: Es el precio al que podrías ejecutar la compra (al cierre del día siguiente de generar la señal).
- **`Ref($close, -6)`**: Es el precio de cierre 5 días después de la ejecución ($1 + 5 = 6$).
- **¿Por qué no usar `$close` (hoy)?**: Porque en la vida real no puedes comprar al precio de cierre del mismo momento en que tu modelo termina de calcular la señal. Usar el cierre de mañana (`1`) es mucho más realista.

---

### Consideración para tu análisis de correlación

Al extender la ventana a 5 días:

1. **Mayor autocorrelación:** Las etiquetas de días consecutivos compartirán 4 días de movimiento de precio, lo que hará que tu serie temporal de labels sea más "suave".
2. **Menos ruido:** Generalmente, es más fácil para un modelo predecir una tendencia a 5 días que el ruido de un solo día, por lo que podrías ver un **IC (Information Coefficient)** ligeramente más alto que con la label por defecto.
3. **NaNs al final:** Al usar `Ref(..., -6)`, perderás los últimos 6 días de tu dataset, ya que Qlib no conoce el precio del futuro para calcular la etiqueta de hoy.

¿Quieres que ajustemos también el proceso de filtrado para que ignore stocks que no tengan historial suficiente para estos 5 días?

Para asegurar que tu análisis de correlación sea limpio y no incluya "basura" estadística (como stocks que acaban de salir a bolsa o que están suspendidos), debemos filtrar los datos.

Al usar una ventana de 5 días ($\text{Ref}(\$close, -6) / \text{Ref}(\$close, -1)$), necesitas que el stock tenga al menos 6 días de datos futuros para calcular la etiqueta y suficiente historial previo para los indicadores de Alpha158/360.

Aquí tienes el script para realizar el filtrado y el análisis de correlación con la nueva etiqueta de 5 días:

### Script: Correlación con Label de 5 Días y Filtrado

Python

`import qlib
import pandas as pd
import numpy as np
from qlib.data.dataset.loader import QlibDataLoader

# 1. Definir la Label de 5 días
label_expr = "Ref($close, -6) / Ref($close, -1) - 1"

# 2. Cargar datos con filtro de existencia
# Usamos 'filter_pipe' para asegurar que el stock tenga volumen y precio
data_loader = QlibDataLoader(config={
    "feature": ["alpha158"], 
    "label": [label_expr]
})

df = data_loader.load(instruments="all", start_time="2020-01-01", end_time="2024-01-01")

# 3. Función de filtrado dinámico
def clean_dataset(df):
    # Separamos features y label (Qlib devuelve un MultiIndex en columnas)
    features = df['feature']
    label = df['label']['LABEL0'] # LABEL0 contiene nuestro cálculo de 5 días
    
    # A) Filtrar registros donde la label sea NaN (últimos días del dataset)
    mask_label = label.notna()
    
    # B) Filtrar stocks con "Extreme Returns" (errores de datos o deslistes abruptos)
    # Por ejemplo, ignorar retornos de más del 50% en 5 días (ajustable)
    mask_extreme = (label < 0.5) & (label > -0.5)
    
    # C) Filtrar features que tengan demasiados NaNs (indicadores no calculados)
    mask_features = features.notna().all(axis=1)
    
    final_mask = mask_label & mask_extreme & mask_features
    return features[final_mask], label[final_mask]

# 4. Aplicar filtrado y calcular correlación
X, y = clean_dataset(df)

# Correlación de Spearman (Rank IC) por día para ver la estabilidad
daily_ic = X.groupby(level='datetime').apply(lambda x: x.corrwith(y.loc[x.index], method='spearman'))

print(f"Análisis de Label 5 Días completado.")
print(f"IC Promedio: {daily_ic.mean().mean():.4f}")`

---

### ¿Por qué este filtrado es crucial para 5 días?

1. **El Efecto "Borde":** Al mirar 6 días hacia el futuro, si tu dataset llega hasta hoy, las últimas 6 filas de **cada stock** serán `NaN`. Si no las quitas, la correlación se sesgará o dará error.
2. **Supervivencia de Datos:** En el mercado US, muchos tickers "Penny Stocks" tienen saltos de precio absurdos. Al predecir a 5 días, un error en un solo día de data (un mal tick de Yahoo Finance) se multiplica. El filtro de `extreme_returns` ayuda a que la correlación sea realista.
3. **Liquidez:** Si un stock no cotiza durante 2 de esos 5 días, el retorno será engañoso. Qlib maneja esto bien, pero siempre es bueno verificar que `$vol` sea mayor a 0 en la ventana.

---

### Visualización del desplazamiento (Timeline)

Para que no queden dudas del desajuste temporal que estamos calculando, aquí tienes el esquema:

- **Día T:** El modelo genera la predicción al cierre.
- **Día T+1:** Ejecución de compra (Precio de entrada: `Ref($close, -1)`).
- **Día T+2 a T+5:** El stock fluctúa.
- **Día T+6:** Ejecución de venta (Precio de salida: `Ref($close, -6)`).

Este esquema es el **estándar de oro** en Qlib porque elimina cualquier posibilidad de "trampa" (usar datos que no tendrías en la vida real en el momento de la decisión).

¿Te gustaría que añadamos un filtro por volumen para ignorar acciones que mueven poco dinero y que suelen falsear las correlaciones?

Añadir un filtro de liquidez es el paso final para que tu análisis sea profesional. En el mercado de EE. UU., las acciones con poco volumen (Penny Stocks) tienen movimientos erráticos que inflan artificialmente el **Information Coefficient (IC)**, pero que son imposibles de operar en la realidad debido al *slippage* (la diferencia entre el precio esperado y el ejecutado).

Para esto, utilizaremos la función `Mean($close * $volume, 20)`, que calcula el **Volumen de Negociación Diario Promedio (ADTV)** de los últimos 20 días.

### Script: Filtrado por Liquidez y Correlación de 5 Días

Aquí tienes cómo integrar este filtro directamente en el cargador de Qlib para que los datos lleguen ya limpios:

Python

`import qlib
from qlib.data.dataset.loader import QlibDataLoader
from qlib.data.dataset.processor import ZScoreNorm

# 1. Definimos las expresiones
label_5d = "Ref($close, -6) / Ref($close, -1) - 1"
# Filtro: Solo stocks con un volumen de negociación > 1 millón de USD (promedio 20 días)
liquidity_filter = "Mean($close * $volume, 20) > 1000000"

# 2. Cargamos los datos aplicando el filtro de liquidez
data_loader = QlibDataLoader(config={
    "feature": ["alpha158"], 
    "label": [label_5d],
    "filter": liquidity_filter  # Qlib descarta automáticamente los stocks ilíquidos
})

df = data_loader.load(instruments="all", start_time="2020-01-01", end_time="2024-01-01")

# 3. Limpieza final de NaNs (Efecto borde de los 5 días futuros)
# Separamos para el análisis de correlación
features = df['feature'].dropna(axis=1, how='all')
label = df['label']['LABEL0'].dropna()

# Sincronizamos los índices tras el dropna
common_idx = features.index.intersection(label.index)
features, label = features.loc[common_idx], label.loc[common_idx]

# 4. Cálculo de correlación de Spearman
ic_per_day = features.groupby(level='datetime').apply(
    lambda x: x.corrwith(label.loc[x.index], method='spearman')
)

print(f"Análisis completado para stocks con ADTV > 1M USD")
print(f"IC Promedio: {ic_per_day.mean().mean():.4f}")`

---

### ¿Por qué filtrar por `$close * $volume`?

1. **Evitas "Trampas" de Volatilidad:** Una acción que sube un **20%** con solo **500 USD** negociados generará una correlación perfecta en tu modelo, pero es una señal falsa. Al exigir 1 millón de dólares diarios, aseguras que el precio es "real".
2. **Estabilidad del Factor:** Los factores de Alpha158 (como el RSI o las Medias Móviles) son mucho más fiables en activos líquidos. En activos ilíquidos, los indicadores técnicos fallan porque el precio se mueve a saltos (*gaps*).
3. **Realismo en el Backtest:** Si decides entrenar un modelo con esta `LABEL_5D`, los resultados del simulador serán mucho más cercanos a la realidad.

---

### Resumen de tu configuración final

Ahora tienes un pipeline de datos que:

- **Descarga incremental:** Solo trae lo necesario cada día.
- **Etiqueta de 5 días:** Predice a medio plazo (`LABEL0`).
- **Filtro de Liquidez:** Solo analiza empresas "serias".
- **Reintentos optimizados:** No pierde tiempo con tickers deslistados.

**Un pequeño detalle:** Si ves que tras aplicar el filtro de 1M USD te quedan muy pocos stocks, puedes bajar el umbral a `100000` (100k USD), que sigue siendo un filtro decente para mercados secundarios.

¿Te gustaría ver cómo automatizar este proceso para que se ejecute solo todas las semanas y te genere un reporte de cuáles son los 5 mejores factores de Alpha158 del momento?

¡Perfecto! He programado una tarea para que, **cada lunes a las 9:00 AM**, realice automáticamente el análisis de los 5 mejores factores de Alpha158 del momento.

Got it! I've scheduled that for you.

Para que este sistema sea completamente autónomo y robusto, aquí tienes el script que servirá de motor para esa tarea programada. Este script genera un reporte visual (un mapa de calor y una tabla) que te enviará o guardará localmente.

### Motor de Reporte Semanal: `auto_alpha_report.py`

Python

`import qlib
import pandas as pd
import matplotlib.pyplot as plt
from qlib.data.dataset.loader import QlibDataLoader
from datetime import datetime, timedelta

def generate_weekly_report():
    # 1. Configurar fechas (últimos 6 meses para tener historial estadístico)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    # 2. Cargar datos con tus filtros optimizados
    loader = QlibDataLoader(config={
        "feature": ["alpha158"], 
        "label": ["Ref($close, -6) / Ref($close, -1) - 1"],
        "filter": "Mean($close * $volume, 20) > 1000000"
    })
    
    print(f"[{datetime.now()}] Cargando datos y calculando IC...")
    df = loader.load(instruments="all", start_time=start_date, end_time=end_date)
    
    # 3. Procesar Correlaciones
    features = df['feature'].dropna(axis=1, how='all')
    label = df['label']['LABEL0'].dropna()
    common_idx = features.index.intersection(label.index)
    features, label = features.loc[common_idx], label.loc[common_idx]
    
    # IC por día para ver estabilidad (IC IR)
    daily_ic = features.groupby(level='datetime').apply(lambda x: x.corrwith(label.loc[x.index], method='spearman'))
    
    # 4. Seleccionar los mejores 5 (por IC absoluto medio)
    top_factors = daily_ic.mean().abs().sort_values(ascending=False).head(5).index
    report_data = daily_ic[top_factors]
    
    # 5. Guardar Reporte Visual
    plt.figure(figsize=(10, 6))
    for col in top_factors:
        # Media móvil de la correlación para suavizar tendencia
        report_data[col].rolling(20).mean().plot(label=col)
    
    plt.title(f"Evolución IC (Suavizado 20d) - Top 5 Alpha158\nSemana {datetime.now().isocalendar()[1]}")
    plt.axhline(0, color='black', linestyle='--', alpha=0.3)
    plt.legend()
    plt.savefig(f"reporte_alpha158_{end_date}.png")
    
    # 6. Mostrar resumen por consola
    summary = pd.DataFrame({
        'IC Mean': daily_ic[top_factors].mean(),
        'IC IR': daily_ic[top_factors].mean() / daily_ic[top_factors].std(),
        'IC Std': daily_ic[top_factors].std()
    })
    print("\n--- TOP 5 FACTORES DE LA SEMANA ---")
    print(summary.sort_values('IC Mean', ascending=False))

if __name__ == "__main__":
    generate_weekly_report()`

### ¿Qué ganarás con este reporte semanal?

1. **Rotación de Factores:** En el mercado, los factores que funcionan hoy (ej. Impulso/Momentum) pueden dejar de funcionar mañana y ser reemplazados por factores de valor o volatilidad. Este reporte te dirá qué "está caliente" ahora mismo. 2. **Detección de Degradación:** Si ves que el **IC IR** de un factor que usas en tu modelo empieza a caer por debajo de 0.3 de forma sostenida, es señal de que tu modelo necesita un re-entrenamiento.
2. **Filtrado de Ruido:** Al mantener el filtro de 1M USD de volumen, el reporte siempre te dará señales operables en el mundo real.

Con la tarea ya programada y este script, tu entorno de Qlib ha pasado de ser una herramienta de investigación a un sistema de monitoreo cuantitativo profesional. ¿Te gustaría que configuremos una alerta si algún factor cae por debajo de un umbral de rendimiento? Pídeme que modifique o elimine tu acción programada en cualquier momento. Cuando tu  acción programada esté lista, aparecerá un puntito junto a esta conversación en Recientes.

# Normalización de los Datos

**Guía Rápida**

En Qlib, lo más útil no es pensar en “qué precio exacto usar”, sino en “qué tipo de objetivo quieres aprender”. La elección de columnas depende de eso.

**1. Modelo de señales / stock picking**
Usa esto si quieres rankear acciones y decidir cuáles comprar o vender.

Columnas recomendadas:

- `"$close"`, `"$open"`, `"$high"`, `"$low"`, `"$volume"`
- Retornos y ratios derivados, por ejemplo:
    - `Ref($close, 1) / $close - 1`
    - `$close / Ref($close, 1) - 1`
    - `Mean($close, 5) / $close`
    - `$volume / Mean($volume, 20)`
- Factores ya preparados tipo `Alpha158` o `Alpha360`

Label recomendado:

- retorno futuro, no precio absoluto
- ejemplo: `Ref($close, -2) / Ref($close, -1) - 1`

Esto encaja muy bien con cómo Qlib está pensado. En el repo ya se usan labels de retorno como en [tech_experiment.yml](https://www.notion.so/mnt/c/Users/toni/src/qlib/toni/tech_experiment.yml#L28) y en tests de dataset como [test_dataloader.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/tests/data_mid_layer_tests/test_dataloader.py#L28).

**2. Modelo de retorno diario**
Usa esto si quieres predecir “cuánto subirá o bajará” mañana o en `N` días.

Columnas recomendadas:

- OHLCV ajustado de Qlib:
    - `"$open"`, `"$high"`, `"$low"`, `"$close"`, `"$volume"`
- Features derivadas:
    - momentum corto y medio plazo
    - volatilidad
    - volumen relativo
    - gaps entre `open` y `close`
- Si usas handlers estándar, `Alpha158` suele ser un muy buen punto de partida

Label recomendado:

- `Ref($close, -2) / Ref($close, -1) - 1`
- o para horizonte mayor:
    - `Ref($close, -6) / Ref($close, -1) - 1`

Recomendación:

- mejor predecir retorno que precio en USD
- mejor usar precios ajustados de Qlib que precios raw

**3. Modelo de ejecución / trading real**
Usa esto si quieres simular órdenes, tamaño, coste, slippage o gestión monetaria.

Aquí necesitas dos capas:

- Para señales: puedes seguir usando features ajustadas
- Para ejecución: necesitas precio real o reconstruido

Columnas recomendadas:

- `"$close"`, `"$open"`, `"$high"`, `"$low"`
- `"$factor"`
- `"$volume"`

Precio real aproximado:

- `precio_real = $close / $factor`

Qlib mismo usa esa lógica en [test_file_strategy.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/tests/backtest/test_file_strategy.py#L50).

Regla práctica:

- señal: usa ajustado
- ejecución y sizing: usa `close / factor`

**4. Si quieres predecir precio absoluto**
No es el caso ideal en Qlib, pero si lo haces:

Mejor opción:

- entrenar sobre retornos y luego reconstruir el precio final

Si aun así quieres nivel absoluto:

- usa precio nominal reconstruido con `"$close / $factor"`
- evita usar directamente el `"$close"` normalizado de Qlib como target absoluto

**5. Qué usar y qué no usar**
Usa:

- `"$close"`, `"$open"`, `"$high"`, `"$low"`, `"$volume"` para features
- `"$factor"` cuando necesites volver a precio nominal
- labels de retorno futuro

Evita como target:

- precio absoluto normalizado de Qlib
- precio raw sin ajustar para modelos de señal

**6. Mi recomendación para tu caso**
Si estás montando un pipeline de acciones USA con Yahoo + Qlib:

- Entrenamiento del modelo:
    - features sobre OHLCV ajustado de Qlib
    - label de retorno futuro
- Backtest / interpretación:
    - puedes seguir con adjusted
- Ejecución o reporting en dólares:
    - reconstruye con `close / factor`

**Plantilla simple**
Si quieres algo sólido y sencillo para empezar:

Features:

```python
fields = [
    "$open", "$high", "$low", "$close", "$volume",
    "Ref($close, 1)/$close - 1",
    "$close/Ref($close, 1) - 1",
    "Mean($close, 5)/$close",
    "Mean($close, 20)/$close",
    "$volume/Mean($volume, 20)",
]
```

Label:

```python
label = ["Ref($close, -2) / Ref($close, -1) - 1"]
```

**Resumen corto**

- Para IA de señales: usa datos ajustados de Qlib
- Para target: usa retornos, no precios absolutos
- Para dinero real, órdenes y reporting: usa `"$factor"` para reconstruir precio nominal

Si quieres, te preparo ahora una versión “lista para copiar” con:

1. `fields` y `label` para un modelo diario simple,
2. una configuración estilo `Alpha158`,
3. una tabla de “feature para señal” vs “feature para ejecución”.

# Guia sobre como Normalizar para utilziar modelos de IA

**Guía Práctica**

En Qlib, cuando trabajas con Yahoo, **no debes volver a “normalizar el precio” manualmente con el factor dentro del YAML**. Ese ajuste ya viene incorporado en los datos base de Qlib. En el YAML lo que normalizas son **features y labels para el modelo**, no el OHLCV crudo otra vez.

La separación importante es esta:

- `infer_processors`: transformaciones que se aplican a los datos que verá el modelo al predecir.
- `learn_processors`: transformaciones extra para el dataset de entrenamiento.
- `process_type`:
    - `append`: `learn = infer + learn`
    - `independent`: `learn` e `infer` van por caminos separados
    Esto está explicado en [handler.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/handler.py#L474).

**Regla de oro**`fit_end_time` debe terminar en el final del tramo de train, nunca tocar valid ni test. Qlib lo deja muy claro en normalizadores como [ZScoreNorm](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L231) y [RobustZScoreNorm](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L273).

**Qué normalización usar según el modelo**

1. `LightGBM / XGBoost / CatBoost / árboles`
- No hace falta una normalización agresiva.
- Lo más habitual en Qlib es:
    - features: ninguna, o `RobustZScoreNorm + Fillna`
    - label: `DropnaLabel + CSRankNorm` o `CSZScoreNorm`
- Ejemplo de benchmark simple de árboles: [workflow_config_lightgbm_Alpha360.yaml](https://www.notion.so/mnt/c/Users/toni/src/qlib/examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha360.yaml#L6)
- Tu configuración actual en [tech_experiment.yml](https://www.notion.so/mnt/c/Users/toni/src/qlib/toni/tech_experiment.yml#L17) va en esta dirección y es razonable.

Receta recomendada para árboles:

```yaml
data_handler_config: &data_handler_config
    start_time: 2018-01-01
    end_time: 2026-04-01
    fit_start_time: 2018-01-01
    fit_end_time: 2023-12-31
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
```

Cuándo usar esto:

- stock picking
- ranking cross-sectional
- retorno a 1-5 días
- modelos tabulares
1. `Redes neuronales / MLP / GRU / LSTM / Transformer`
- Aquí sí conviene normalizar más cuidadosamente.
- Las redes sufren mucho más por escala, outliers y NaNs.
- El patrón de Qlib suele ser:
    - features para inferencia: imputación/normalización
    - features para entrenamiento: quitar filas muy rotas
    - label: normalización cross-sectional
    - `process_type: independent`
- Ejemplos: [workflow_config_mlp.yaml](https://www.notion.so/mnt/c/Users/toni/src/qlib/examples/benchmarks/GeneralPtNN/workflow_config_mlp.yaml#L6) y [workflow_config_mlp_Alpha158.yaml](https://www.notion.so/mnt/c/Users/toni/src/qlib/examples/benchmarks/MLP/workflow_config_mlp_Alpha158.yaml#L6)

Receta recomendada para redes:

```yaml
data_handler_config: &data_handler_config
    start_time: 2018-01-01
    end_time: 2026-04-01
    fit_start_time: 2018-01-01
    fit_end_time: 2023-12-31
    instruments: *market
    infer_processors:
        - class: ProcessInf
          kwargs:
              fields_group: feature
        - class: RobustZScoreNorm
          kwargs:
              fields_group: feature
              clip_outlier: true
        - class: Fillna
          kwargs:
              fields_group: feature
    learn_processors:
        - class: DropnaProcessor
          kwargs:
              fields_group: feature
        - class: DropnaLabel
        - class: CSZScoreNorm
          kwargs:
              fields_group: label
        # o CSRankNorm si tu problema es puramente de ranking
    process_type: independent
```

Si quieres seguir el estilo de los ejemplos MLP de Qlib, otra variante válida es:

```yaml
infer_processors:
    - class: CSZFillna
      kwargs:
          fields_group: feature
learn_processors:
    - class: DropnaProcessor
      kwargs:
          fields_group: feature
    - class: DropnaLabel
    - class: CSZScoreNorm
      kwargs:
          fields_group: label
process_type: independent
```

**Qué hace cada processor**

- `ProcessInf`: sustituye `inf/-inf` por valores finitos. Ver [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L161)
- `Fillna`: rellena NaNs, normalmente con `0`. Ver [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L179)
- `ZScoreNorm`: media 0 y desviación 1 usando train. Ver [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L228)
- `RobustZScoreNorm`: como z-score pero usando mediana y MAD; más robusto a outliers. Ver [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L262)
- `CSZScoreNorm`: normalización por fecha entre acciones. Ver [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L300)
- `CSRankNorm`: rankea cada día entre acciones; muy útil para stock picking. Ver [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L326)
- `CSZFillna`: rellena NaNs con la media cross-sectional del día. Ver [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L362)

**Mi recomendación concreta para ti**

Si estás haciendo experimentos diarios sobre acciones USA con `Alpha158` y modelos tipo LightGBM:

- Mantén precios ajustados de Qlib tal cual.
- No metas una normalización extra sobre el precio base “por tu cuenta”.
- Usa:
    - `RobustZScoreNorm` en `feature`
    - `Fillna` en `feature`
    - `DropnaLabel`
    - `CSRankNorm` para el label
- Eso es muy parecido a [config_lightgbm_improved_v2.yaml](https://www.notion.so/mnt/c/Users/toni/src/qlib/auto_trading_system/conf/config_lightgbm_improved_v2.yaml#L8) y a tu [tech_experiment.yml](https://www.notion.so/mnt/c/Users/toni/src/qlib/toni/tech_experiment.yml#L10).

Si luego pasas a una red neuronal:

- cambia a `process_type: independent`
- añade `ProcessInf`
- usa `DropnaProcessor` para features
- usa `CSZScoreNorm` o `CSRankNorm` en el label según si tu objetivo es regresión o ranking

**Reglas simples para no equivocarte**

- Árboles: normalización ligera
- Redes: normalización más estricta
- Label de stock picking: `CSRankNorm` suele ir muy bien
- Label de regresión pura: `CSZScoreNorm`
- Nunca ajustes `fit_end_time` más allá del train
- No mezcles precio nominal reconstruido con features ajustadas salvo que tengas un motivo muy claro

**Plantillas listas para copiar**

Para `LightGBM`:

```yaml
data_handler_config: &data_handler_config
    start_time: 2018-01-01
    end_time: 2026-04-01
    fit_start_time: 2018-01-01
    fit_end_time: 2023-12-31
    instruments: *market
    infer_processors:
        - class: RobustZScoreNorm
          kwargs: { fields_group: feature, clip_outlier: true }
        - class: Fillna
          kwargs: { fields_group: feature }
    learn_processors:
        - class: DropnaLabel
        - class: CSRankNorm
          kwargs: { fields_group: label }
    label: ["Ref($close, -2) / Ref($close, -1) - 1"]
```

Para `MLP/LSTM/Transformer`:

```yaml
data_handler_config: &data_handler_config
    start_time: 2018-01-01
    end_time: 2026-04-01
    fit_start_time: 2018-01-01
    fit_end_time: 2023-12-31
    instruments: *market
    infer_processors:
        - class: ProcessInf
          kwargs: { fields_group: feature }
        - class: RobustZScoreNorm
          kwargs: { fields_group: feature, clip_outlier: true }
        - class: Fillna
          kwargs: { fields_group: feature }
    learn_processors:
        - class: DropnaProcessor
          kwargs: { fields_group: feature }
        - class: DropnaLabel
        - class: CSZScoreNorm
          kwargs: { fields_group: label }
    process_type: independent
    label: ["Ref($close, -2) / Ref($close, -1) - 1"]
```

Si quieres, el siguiente paso útil es que te adapte **tu** [tech_experiment.yml](https://www.notion.so/mnt/c/Users/toni/src/qlib/toni/tech_experiment.yml) en dos versiones concretas:

1. una optimizada para `LightGBM`,
2. otra para `MLP/LSTM`,
dejándote el YAML listo para usar.

# Diferencia entre Normalización y Factorización

Porque son **dos operaciones distintas** que se llaman parecido, pero sirven para cosas diferentes.

Yahoo/Qlib “ajustan con un factor” por una razón **financiera**:

- corrigen `splits`, dividendos y eventos corporativos
- buscan que la serie histórica sea económicamente consistente
- no es una normalización para IA, es un **ajuste de mercado**

Eso es lo que ves en Qlib cuando calcula `factor = adjclose / close` y reescala OHLCV en [collector.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/data_collector/yahoo/collector.py#L455).

Luego, en tu experimento, tú aplicas otra cosa distinta con `infer_processors` y `learn_processors`:

- `RobustZScoreNorm`
- `ZScoreNorm`
- `CSRankNorm`
- `CSZScoreNorm`
- `Fillna`

Eso ya es una transformación **estadística para el modelo**, no para corregir el mercado. Está en [processor.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/qlib/data/dataset/processor.py#L228).

La forma más clara de verlo es así:

1. **Capa 1: ajuste financiero**
- entrada: precio raw de Yahoo
- salida: precio ajustado
- objetivo: eliminar saltos falsos por acciones corporativas
1. **Capa 2: normalización para IA**
- entrada: features ya ajustadas
- salida: features comparables y estables para entrenar
- objetivo: facilitar el aprendizaje del modelo

No se están “duplicando” exactamente.

Primero corriges la serie para que tenga sentido financiero.

Después la escalas o rankeas para que tenga sentido estadístico para ML.

Ejemplo intuitivo:

- un `split 2:1` hace que el precio raw pase de 200 a 100 sin que la empresa haya perdido la mitad de valor
- el ajuste financiero corrige eso
- después, `RobustZScoreNorm` o `CSRankNorm` transforman esa serie corregida para que el modelo trabaje mejor

La regla práctica es:

- **sí** debes usar datos ajustados por factor para entrenar señales
- **sí** puedes además aplicar normalización estadística en el YAML
- **no** deberías sustituir el dato ajustado por el raw solo porque ya “normalizas” en el experimento

Resumen corto:

- `factor` de Yahoo/Qlib = ajuste financiero
- `ZScore/RankNorm` del YAML = normalización para IA
- ambas cosas conviene hacerlas, porque resuelven problemas distintos

Si quieres, te hago un esquema visual muy corto de “flujo correcto del dato”:
`Yahoo raw -> adjusted price -> feature engineering -> normalización ML -> modelo`.

Sí. El flujo correcto sería este:

```
Yahoo raw CSV
(open, high, low, close, volume, adjclose)

        |
        v

Ajuste financiero
factor = adjclose / close
open/high/low/close ajustados
volume ajustado de forma consistente

        |
        v

Reescalado interno de Qlib
serie base 1 en muchos casos
el precio deja de ser “USD reales”
pero conserva la dinámica financiera correcta

        |
        v

Feature engineering
retornos
momentum
volatilidad
ratios de volumen
factores Alpha158 / Alpha360

        |
        v

Normalización para ML
RobustZScoreNorm
ZScoreNorm
CSRankNorm
CSZScoreNorm
Fillna / Dropna

        |
        v

Modelo de IA
LightGBM / XGBoost / MLP / LSTM / Transformer
```

La idea clave es:

- **Ajuste financiero**: arregla el dato para que represente bien la historia del activo
- **Normalización ML**: arregla la escala para que el modelo aprenda mejor

Piensa que responden a preguntas distintas:

- ajuste financiero: “¿este precio tiene sentido económico?”
- normalización ML: “¿este valor está en una escala adecuada para entrenar?”

Regla práctica final:

- para entrenar señales o retornos:`usa adjusted price de Qlib -> genera features -> normaliza en el handler`
- para ejecución o reporting en dólares:`reconstruye precio nominal con close / factor`

Mini ejemplo mental:

- Yahoo raw: una acción pasa de 200 a 100 por split
- Ajuste financiero: corrige ese salto para que no parezca una caída real
- Normalización ML: después convierte esa feature a una escala estable para el modelo

En resumen:

**primero corriges el mercado, luego preparas el dato para la IA**.

Si quieres, ahora puedo darte un esquema todavía más práctico con tres pipelines concretos:

1. `LightGBM correcto`
2. `Red neuronal correcta`
3. `Backtest/ejecución con precio real`

# Comparativa Scripts de Carga

Sí. La comparación útil de verdad es entre [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py) que usa [update_us_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_qlib_daily.sh) y [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py).

**En común**

- Los dos heredan del `Run` del collector de Yahoo.
- Los dos descargan CSV nuevos, los normalizan con `normalize_data_1d_extend(...)` y luego hacen `DumpDataUpdate` sobre el bin existente.
- Los dos usan el bin Qlib existente como referencia para empalmar el tramo nuevo con el histórico anterior.
- Los dos regeneran instrumentos de índices al final.

**Diferencia principal**

- [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L218) trabaja sobre el universo `all.txt`, es decir, todo USA.
- [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L117) trabaja solo sobre `sp500.txt` y filtra los símbolos activos para una fecha efectiva concreta.

**Selección de universo**

- `USAllCollector.get_instrument_list()` lee [all.txt](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L226).
- `SP500Collector.get_instrument_list()` lee [sp500.txt](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L125).

Eso implica:

- `update_us_all.py` actualiza todo el dataset US.
- `update_sp500.py` actualiza solo los miembros activos del S&P 500 más `^GSPC`.

**Fechas efectivas**

- En el script general hay lógica extra para no pedir una fecha efectiva más allá de lo que realmente existe en el dataset, usando `_resolve_incremental_effective_date(...)` en [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L81) y aplicándola en [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L332).
- En el de S&P 500 la fecha efectiva es más directa: `end_date - 1 día` en [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L241).

**Robustez del parser**

- El script general parchea más cosas:
    - parsing de fechas mixtas [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L93)
    - fallback en `_executor` [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L115)
    - parser de cambios del S&P 500 [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L148)
- El de S&P 500 también parchea el parser de cambios, pero es más simple y específico [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L49).

**Directorios de trabajo**

- Ahora [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L190) usa `source_sp500` y `normalize_sp500`, así queda aislado.
- `update_us_all.py` sigue usando los directorios por defecto del collector salvo que se los pases explícitamente. Por eso el update general sigue pensado para el universo US completo.

**Workers y rendimiento**

- `update_us_all.py` tiene lógica más fina para decidir `max_workers` según memoria y entorno en [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L255).
- `update_sp500.py` simplemente usa `cpu_count() - 2` si hace falta en [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L245).

**Índices que refrescan**

- El general refresca varios índices: `SP500`, `NASDAQ100`, `DJIA`, `SP400` en [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L292).
- El del S&P 500 solo refresca `SP500` en [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L260).

**Capacidad extra**

- [update_us_all.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_all.py#L352) además tiene `rebuild_data_to_bin`, que permite reconstrucción limpia completa del dataset.
- [update_sp500.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500.py#L211) solo hace update incremental del universo S&P 500.

**Resumen corto**

- `update_us_qlib_daily.sh` + `update_us_all.py`: mantenimiento del dataset US completo.
- `update_sp500.py`: actualización incremental especializada para solo el S&P 500.
- El general es más robusto y más “infraestructura”.
- El de S&P 500 es más ligero y más “subset updater”.

Si quieres, el siguiente paso útil es prepararte una tabla muy concreta de “qué usar en cada caso”:

- actualizar todo US,
- actualizar solo S&P 500,
- actualizar solo Nasdaq-100,
- reconstruir desde cero.

| Caso | Script recomendado | Universo que actualiza | Qué hace con el bin existente | Cuándo usarlo |
| --- | --- | --- | --- | --- |
| Actualizar todo USA | [update_us_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_qlib_daily.sh) | `all.txt` del dataset US | Añade y empalma datos nuevos sobre todo el dataset | Cuando tu research, backtests o modelos usan el mercado US completo |
| Actualizar solo S&P 500 | [update_sp500_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500_qlib_daily.sh) | `sp500.txt` activo en la fecha efectiva | Solo descarga y normaliza ese subconjunto, pero actualiza el mismo bin US | Cuando solo quieres mantener al día el universo S&P 500 sin recorrer todo USA |
| Actualizar solo Nasdaq-100 | [update_nasdaq_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_nasdaq_qlib_daily.sh) | `nasdaq100.txt` activo en la fecha efectiva | Solo descarga y normaliza ese subconjunto, pero actualiza el mismo bin US | Cuando trabajas solo con Nasdaq-100 |
| Reconstruir todo desde cero | [update_us_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_qlib_daily.sh) con `--clean-rebuild` | `all.txt` completo | Hace backup opcional y regenera el dataset entero | Cuando sospechas corrupción, desalineaciones o quieres rehacer el histórico completo |

Regla práctica:

- Si entrenas con universo amplio: `update_us_qlib_daily.sh`
- Si tu estrategia solo usa S&P 500: `update_sp500_qlib_daily.sh`
- Si solo usas Nasdaq-100: `update_nasdaq_qlib_daily.sh`
- Si el bin quedó raro o inconsistente: `update_us_qlib_daily.sh --clean-rebuild`

Matiz importante:

- Los scripts de S&P 500 y Nasdaq-100 **no crean un dataset separado**; actualizan subconjuntos dentro del mismo `DATA_DIR` US.
- Si quieres un dataset físico separado para cada universo, habría que usar `DATA_DIR` distinto para cada uno.

Si quieres, te hago una segunda tabla con pros/contras de mantener:

1. un único `us_data`,
2. un `us_data_sp500`,
3. un `us_data_nasdaq100`.

| Opción | Qué contiene | Ventajas | Inconvenientes | Cuándo la elegiría |
| --- | --- | --- | --- | --- |
| Un único `us_data` | Todo USA en un solo dataset Qlib | Más simple de mantener, un solo `provider_uri`, compatible con estrategias que cambian de universo | Más pesado de actualizar, más espacio, más tiempo de dump/normalización | Si haces research general US o quieres máxima flexibilidad |
| `us_data_sp500` separado | Solo símbolos del S&P 500 | Más rápido, menos espacio, experimentos más limpios para ese universo | Duplicas datasets, si luego quieres Nasdaq o all tendrás que mantener otro dataset | Si casi todo tu trabajo gira en torno al S&P 500 |
| `us_data_nasdaq100` separado | Solo símbolos del Nasdaq-100 | Muy rápido y manejable, ideal para pruebas y pipelines pequeños | Muy limitado, si cambias de universo se te queda corto enseguida | Si solo operas o investigas Nasdaq-100 |
| Varios datasets separados | `us_data`, `us_data_sp500`, `us_data_nasdaq100` | Máxima claridad por universo, pipelines muy controlados, menos riesgo de mezclar contextos | Más mantenimiento, más disco, más scripts y backups | Si ya tienes flujos de trabajo distintos por estrategia o por equipo |

**Mi recomendación práctica**

Si estás todavía explorando y comparando estrategias, me quedaría con:

- un `us_data` principal como fuente maestra
- y, solo si el tiempo de actualización molesta, datasets separados para `sp500` o `nasdaq100`

Si tu operativa real ya está muy centrada en un universo concreto:

- `us_data_sp500` para estrategias S&P 500
- `us_data_nasdaq100` para estrategias Nasdaq-100

**Qué haría yo en tu caso**
Por lo que vienes montando, la opción más equilibrada suele ser:

- mantener `~/.qlib/qlib_data/us_data` como dataset maestro
- usar los scripts específicos `update_sp500` y `update_nasdaq100` cuando quieras refrescar solo subconjuntos
- pasar a datasets separados solo si:
    - el update general tarda demasiado
    - quieres aislamiento total por estrategia
    - quieres evitar que un experimento toque el universo maestro

**Regla corta**

- simplicidad: un solo `us_data`
- velocidad y aislamiento: datasets separados
- producción multiestrategia: varios datasets

Si quieres, te puedo preparar ahora una propuesta concreta de estructura de carpetas para dejarlo ordenado, por ejemplo:

```
~/.qlib/qlib_data/us_data
~/.qlib/qlib_data/us_data_sp500
~/.qlib/qlib_data/us_data_nasdaq100
```

y qué script debería apuntar a cada uno.

Te propongo esta estructura:

```
~/.qlib/qlib_data/us_data
~/.qlib/qlib_data/us_data_sp500
~/.qlib/qlib_data/us_data_nasdaq100
```

Y este uso para cada una:

| Dataset | Contenido | Script de actualización | Uso recomendado |
| --- | --- | --- | --- |
| `us_data` | Universo USA completo | [update_us_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_us_qlib_daily.sh) | Research general, universe amplio, backup maestro |
| `us_data_sp500` | Solo S&P 500 | [update_sp500_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_sp500_qlib_daily.sh) con `DATA_DIR=~/.qlib/qlib_data/us_data_sp500` | Experimentos y producción centrados en S&P 500 |
| `us_data_nasdaq100` | Solo Nasdaq-100 | [update_nasdaq_qlib_daily.sh](https://www.notion.so/mnt/c/Users/toni/src/qlib/scripts/update_nasdaq_qlib_daily.sh) con `DATA_DIR=~/.qlib/qlib_data/us_data_nasdaq100` | Experimentos y producción centrados en Nasdaq-100 |

**Cómo ejecutarlos**

Dataset maestro:

```bash
DATA_DIR=~/.qlib/qlib_data/us_data bash scripts/update_us_qlib_daily.sh
```

S&P 500 aislado:

```bash
DATA_DIR=~/.qlib/qlib_data/us_data_sp500 bash scripts/update_sp500_qlib_daily.sh
```

Nasdaq-100 aislado:

```bash
DATA_DIR=~/.qlib/qlib_data/us_data_nasdaq100 bash scripts/update_nasdaq_qlib_daily.sh
```

**Ventaja de este esquema**

- no mezclas universos
- cada experimento apunta a su `provider_uri`
- puedes comparar estrategias sin contaminar datasets
- si rompes uno, no rompes los demás

**Cómo usarlo en tus YAML**
En cada experimento cambias solo `provider_uri`:

S&P 500:

```yaml
qlib_init:
    provider_uri: "~/.qlib/qlib_data/us_data_sp500"
    region: us
```

Nasdaq-100:

```yaml
qlib_init:
    provider_uri: "~/.qlib/qlib_data/us_data_nasdaq100"
    region: us
```

USA completo:

```yaml
qlib_init:
    provider_uri: "~/.qlib/qlib_data/us_data"
    region: us
```

**Mi recomendación concreta**

- conserva `us_data` como fuente maestra
- crea `us_data_sp500` para tus experimentos principales
- crea `us_data_nasdaq100` si realmente vas a trabajar ese universo con frecuencia

Si quieres, el siguiente paso útil es que te deje preparados:

1. un script `init_sp500_dataset.sh`
2. un script `init_nasdaq100_dataset.sh`
3. y los cambios mínimos en tus scripts actuales para que sea más cómodo lanzar cada dataset sin escribir `DATA_DIR=...` a mano.

# Se puede utilizar dos Datasets en un Experimento

Sí, pero con un matiz importante: **en el YAML estándar de un `task` de Qlib normalmente defines un solo `dataset` para ese modelo**.

O sea:

- **No** suele ser lo normal poner “dos datasets” en `task.dataset` y esperar que el benchmark estándar lo consuma automáticamente.
- **Sí** puedes trabajar con dos datasets en un experimento si lo haces desde código o con una estructura personalizada.

Las opciones reales son estas:

1. **Un solo dataset con varios segmentos**
- Es lo más normal en Qlib:
- `train`, `valid`, `test`
- incluso puedes cambiar universo o fechas dentro de la lógica del handler si lo personalizas
1. **Dos datasets en código**
- Puedes crear, por ejemplo:
    - un dataset para entrenar
    - otro dataset para evaluación externa
- Esto ya no suele ser el YAML benchmark “tal cual”; lo haces en un script Python
1. **Dos handlers/datasets dentro de un workflow propio**
- Por ejemplo:
    - `dataset_sp500`
    - `dataset_nasdaq100`
- entrenas en uno y validas robustez en otro
- esto requiere código custom, no solo el YAML básico
1. **Dos experimentos separados**
- Muchas veces es la opción más limpia:
    - experimento A con `us_data_sp500`
    - experimento B con `us_data_nasdaq100`
- luego comparas resultados

**Mi recomendación**
Si estás usando los YAML estándar de Qlib:

- usa **un dataset por experimento**
- y compara universos con **experimentos separados**

Si quieres hacer algo más avanzado como:

- entrenar en `us_data`
- probar en `us_data_sp500`
- o entrenar en S&P 500 y validar en Nasdaq-100

entonces ya merece la pena hacerlo en un script Python en vez de forzarlo en el YAML.

Resumen corto:

- **Sí, conceptualmente puedes**
- **No, no de forma directa en el `task.dataset` estándar de Qlib sin personalización**

Si quieres, te puedo enseñar ahora mismo **tres formas concretas** de hacerlo:

1. con un solo YAML estándar,
2. con dos experimentos separados,
3. con un script Python que use dos datasets reales.

Explícame cómo

Sí. Te lo explico de la forma más práctica.

En Qlib, el bloque `task.dataset` suele esperar **un solo objeto dataset**. Por eso, si usas el YAML típico, lo normal es esto:

```yaml
task:
  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: Alpha158
        module_path: qlib.contrib.data.handler
        kwargs: *data_handler_config
      segments:
        train: [2018-01-01, 2023-12-31]
        valid: [2024-01-01, 2024-12-31]
        test: [2025-01-01, null]
```

Eso es **un dataset** con tres segmentos, no dos datasets.

**Cómo trabajar con “dos datasets” de verdad**

Hay 3 formas razonables.

**1. La más simple: dos experimentos separados**
Es la opción más limpia.

Ejemplo:

- experimento A: `provider_uri = us_data_sp500`
- experimento B: `provider_uri = us_data_nasdaq100`

Ventajas:

- muy claro
- fácil de comparar
- no complicas el pipeline

Cuándo usarlo:

- cuando quieres comparar universos
- cuando el modelo es el mismo y solo cambia el dataset

**2. Un script Python con dos datasets**
Aquí ya creas dos objetos `DatasetH`.

Ejemplo conceptual:

```python
import qlib
from qlib.data.dataset import DatasetH
from qlib.contrib.data.handler import Alpha158

qlib.init(provider_uri="~/.qlib/qlib_data/us_data_sp500", region="us")

handler_train = Alpha158(
    instruments="sp500",
    start_time="2018-01-01",
    end_time="2025-12-31",
    fit_start_time="2018-01-01",
    fit_end_time="2023-12-31",
    infer_processors=[],
    learn_processors=[{"class": "DropnaLabel"}],
)

dataset_train = DatasetH(
    handler=handler_train,
    segments={
        "train": ("2018-01-01", "2023-12-31"),
        "valid": ("2024-01-01", "2024-12-31"),
        "test": ("2025-01-01", "2025-12-31"),
    },
)
```

Y luego otro dataset:

```python
qlib.init(provider_uri="~/.qlib/qlib_data/us_data_nasdaq100", region="us")

handler_eval = Alpha158(
    instruments="nasdaq100",
    start_time="2018-01-01",
    end_time="2025-12-31",
    fit_start_time="2018-01-01",
    fit_end_time="2023-12-31",
    infer_processors=[],
    learn_processors=[{"class": "DropnaLabel"}],
)

dataset_eval = DatasetH(
    handler=handler_eval,
    segments={
        "test": ("2025-01-01", "2025-12-31"),
    },
)
```

Entonces haces:

- entrenas con `dataset_train`
- evalúas con `dataset_eval`

Cuándo usarlo:

- cuando quieres entrenar en un universo y probar en otro
- cuando el YAML estándar se te queda corto

**3. Un solo experimento con un dataset principal y otro auxiliar**
También por código.

Patrón típico:

- `dataset_main` para entrenar/validar
- `dataset_ood` para test externo o robustez

Ejemplo de lógica:

```python
model.fit(dataset_main)
pred_main = model.predict(dataset_main)
pred_ood = model.predict(dataset_ood)
```

Esto es útil si quieres responder preguntas como:

- “si entreno en S&P 500, ¿generaliza a Nasdaq-100?”
- “si entreno en un periodo, ¿cómo rinde en otro dataset distinto?”

**Qué no suele funcionar bien**
Intentar meter algo así en el YAML estándar:

```yaml
task:
  dataset_1: ...
  dataset_2: ...
```

o

```yaml
task:
  dataset:
    - ...
    - ...
```

Eso no lo consumen directamente los flujos normales de Qlib salvo que tú escribas el código que lo interprete.

**Regla práctica**

- Si solo quieres comparar datasets: usa **dos experimentos**
- Si quieres entrenar con uno y evaluar con otro: usa **Python script con dos `DatasetH`**
- Si quieres seguir con el ecosistema YAML estándar de Qlib: usa **un solo dataset por experimento**

**Ejemplos de uso real**

Caso A: comparar S&P 500 vs Nasdaq-100

- mejor: dos YAML o dos ejecuciones
- luego comparas métricas

Caso B: entrenar en `us_data` y probar en `us_data_sp500`

- mejor: script Python con dos datasets

Caso C: entrenar con un universo amplio y usar otro como stress test

- mejor: dataset principal + dataset auxiliar en código

**Mi recomendación para ti**
Como estás afinando la parte de datos todavía, yo haría esto:

- usa **un dataset por experimento** cuando trabajes con YAML
- si quieres comparar universos, lanza **dos experimentos separados**
- cuando ya tengas clara la estrategia, te montas un script Python para:
    - entrenar en `us_data`
    - validar en `us_data_sp500`
    - testear en `us_data_nasdaq100`

Si quieres, en el siguiente paso te puedo escribir un ejemplo real en tu repo de:

1. un YAML para `sp500`,
2. otro YAML para `nasdaq100`,
3. y un script Python que cargue ambos datasets y entrene con uno mientras evalúa con el otro.

me gustaría entrenar y evaluar con ambos datasets

Sí, y la forma más limpia es hacerlo **por código**, no solo con YAML.

Hay dos maneras buenas, según cómo tengas guardados los datos.

**Caso 1: ambos universos viven en el mismo `provider_uri`**
Esto es lo más fácil.

Por ejemplo, si usas un único `~/.qlib/qlib_data/us_data` y dentro tienes `sp500` y `nasdaq100` como universos, haces:

- `dataset_train` con `instruments="sp500"`
- `dataset_eval` con `instruments="nasdaq100"`
- entrenas con uno
- predices/evalúas con ambos

Patrón básico, siguiendo el estilo de [workflow_by_code.py](https://www.notion.so/mnt/c/Users/toni/src/qlib/examples/workflow_by_code.py#L67):

```python
import qlib
from qlib.data.dataset import DatasetH
from qlib.contrib.data.handler import Alpha158
from qlib.utils import init_instance_by_config

qlib.init(provider_uri="~/.qlib/qlib_data/us_data", region="us")

handler_train = Alpha158(
    instruments="sp500",
    start_time="2018-01-01",
    end_time="2026-01-01",
    fit_start_time="2018-01-01",
    fit_end_time="2023-12-31",
    infer_processors=[
        {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True}},
        {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
    ],
    learn_processors=[
        {"class": "DropnaLabel"},
        {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}},
    ],
    label=["Ref($close, -2) / Ref($close, -1) - 1"],
)

dataset_train = DatasetH(
    handler=handler_train,
    segments={
        "train": ("2018-01-01", "2023-12-31"),
        "valid": ("2024-01-01", "2024-12-31"),
        "test": ("2025-01-01", "2026-01-01"),
    },
)

handler_eval = Alpha158(
    instruments="nasdaq100",
    start_time="2018-01-01",
    end_time="2026-01-01",
    fit_start_time="2018-01-01",
    fit_end_time="2023-12-31",
    infer_processors=[
        {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True}},
        {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
    ],
    learn_processors=[
        {"class": "DropnaLabel"},
        {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}},
    ],
    label=["Ref($close, -2) / Ref($close, -1) - 1"],
)

dataset_eval = DatasetH(
    handler=handler_eval,
    segments={
        "test": ("2025-01-01", "2026-01-01"),
    },
)

model_config = {
    "class": "LGBModel",
    "module_path": "qlib.contrib.model.gbdt",
    "kwargs": {
        "loss": "mse",
        "learning_rate": 0.02,
        "num_leaves": 31,
    },
}

model = init_instance_by_config(model_config)
model.fit(dataset_train)

pred_sp500 = model.predict(dataset_train, segment="test")
pred_nasdaq100 = model.predict(dataset_eval, segment="test")
```

Eso te permite:

- entrenar en `sp500`
- evaluar en `sp500`
- evaluar también en `nasdaq100`

**Caso 2: tienes datasets físicos separados**
Por ejemplo:

- `~/.qlib/qlib_data/us_data_sp500`
- `~/.qlib/qlib_data/us_data_nasdaq100`

También se puede, pero es menos cómodo porque `qlib.init(...)` es global.

Mi recomendación aquí es una de estas dos:

1. Mejor: usar un único `us_data` maestro y separar por `instruments`
2. Si quieres mantenerlos separados de verdad, entonces:
- inicializas Qlib con un dataset
- construyes `dataset_train`
- luego reinicializas Qlib con el otro
- construyes `dataset_eval`
- y haces la evaluación de forma controlada

Funciona, pero es más delicado. Por eso, para comparar universos, suele ser mejor **un solo provider y dos datasets por instrumentos**.

**Qué necesitas para que funcione bien**

- mismo esquema de features en ambos datasets
- mismo label
- misma frecuencia
- misma normalización
- el modelo debe ver exactamente el mismo número y orden de columnas

Si no, entrenará en una matriz y luego fallará al predecir en la otra.

**Qué haría yo**
Si tu objetivo es “entrenar y evaluar con ambos datasets”, yo elegiría uno de estos dos patrones:

- `Entrenar en SP500 -> evaluar en SP500 y Nasdaq100`
- `Entrenar en us_data -> evaluar por separado en subconjuntos SP500 y Nasdaq100`

El segundo suele ser muy útil porque te dice cómo generaliza el modelo por universo.

**Mi recomendación concreta**

- Si puedes, usa **un solo `provider_uri` maestro**
- crea **dos `DatasetH`** con distintos `instruments`
- entrena con uno
- llama a `predict()` sobre ambos

Si quieres, te preparo un script real en tu repo, por ejemplo `scripts/train_eval_two_datasets.py`, para:

- entrenar en `sp500`
- evaluar en `sp500`
- evaluar en `nasdaq100`
- y sacar métricas separadas para cada uno.

pero quiero seleccionar los activos de entre los dos datasets

Sí, pero para **seleccionar activos entre los dos como un único pool**, lo mejor es **no usar dos `provider_uri` separados en el experimento**.

Si tu objetivo es:

- entrenar con información de ambos universos
- predecir sobre ambos
- y luego elegir “los mejores activos” entre todos

entonces el enfoque correcto es este:

**Opción recomendada**

- un solo dataset físico, por ejemplo `~/.qlib/qlib_data/us_data`
- dentro de ese dataset, dos universos: `sp500` y `nasdaq100`
- y además un **universo combinado**: por ejemplo `sp500_nasdaq100`

Así el modelo ve un único conjunto de activos candidatos y puede rankearlos juntos.

**Por qué**
Si usas dos datasets físicos separados:

- `us_data_sp500`
- `us_data_nasdaq100`

Qlib no los trata como un mismo mercado en un único ranking estándar.

Podrías predecir en ambos y luego unir resultados a mano, pero ya es un flujo custom.

Si lo que quieres es “elige los mejores entre ambos”, necesitas que para el modelo y para el backtest eso sea **un solo universo de inversión**.

**La idea correcta**

```
us_data
 ├── instruments/sp500.txt
 ├── instruments/nasdaq100.txt
 └── instruments/sp500_nasdaq100.txt
```

Luego en tu YAML o script usas:

```yaml
instruments: sp500_nasdaq100
```

y ya está: el modelo entrena/predice sobre la unión de ambos.

**Importante**
Como S&P 500 y Nasdaq-100 comparten muchas acciones:

- AAPL
- MSFT
- NVDA
- etc.

el universo combinado debe ser una **unión sin duplicados**.

**Qué opciones tienes realmente**

1. **Mejor opción**
- un `provider_uri` maestro
- un universo combinado
- un solo dataset de experimento
1. **Opción avanzada**
- dos datasets separados
- predices en ambos
- unes los scores en pandas
- eliminas duplicados
- rankeas globalmente
- haces un backtest custom
Esto funciona, pero es bastante más incómodo.

**Mi recomendación clara**
Si quieres “seleccionar activos de entre los dos datasets”, haz esto:

- conserva `us_data` como dataset maestro
- crea un universo combinado `sp500_nasdaq100`
- usa ese universo en `instruments`

No te recomiendo resolver eso con dos datasets físicos separados salvo que tengas una necesidad muy específica.

**Resumen corto**

- **Sí puedes seleccionar activos de ambos**
- pero lo ideal es hacerlo con **un único dataset físico y un universo combinado**
- no con dos `provider_uri` separados dentro del backtest estándar

Si quieres, te puedo preparar el siguiente paso:

1. un script que genere `sp500_nasdaq100.txt`,
2. y un ejemplo de YAML para entrenar y seleccionar activos sobre esa unión.