# Estrategia Qlib 5: Cryptos

# Definición Estrategia Cryptos

Quiero crear un universo en Qlib con criptomonedas, lo primero que tengo que hacer es bajar la información de las criptos, normalizarlas y dumpearlas a formato bin. Cómo las criptos funcionan en modo de mercado contínuo, ¿que workflow crees que debería seguir?

Crear un ecosistema de criptomonedas en **Qlib** es una excelente idea para aprovechar sus modelos de *SOTA* (State of the Art), pero requiere un manejo preciso de los datos debido a que las criptos no cierran nunca.

A continuación, te detallo el workflow técnico para transformar datos crudos en formato binario y los pasos para definir tu estrategia.

---

## 1. Workflow de Ingesta y Preparación de Datos

Qlib no procesa CSVs en tiempo real para el entrenamiento; utiliza un formato binario (`.bin`) optimizado para acceder a miles de activos en milisegundos.

### Paso A: Recolección y Formateo (Collector)

Debes bajar los datos (usando `CCXT` o APIs directas) y guardarlos en CSVs individuales por cada moneda (ej. `BTCUSDT.csv`, `ETHUSDT.csv`).

- **Columnas requeridas:** `date` (o `datetime`), `open`, `high`, `low`, `close`, `volume` y **`factor`**.
- **El factor de ajuste:** En acciones se usa para splits/dividendos. En criptos, pon esta columna siempre en **1.0**. Qlib la requiere para sus cálculos internos de rentabilidad.

### Paso B: El "Calendario" de Mercado Continuo

Este es el punto más crítico para criptos. Qlib busca un archivo llamado `day.txt` (o la frecuencia que elijas) en una carpeta `calendars`.

- **Workflow:** Debes generar un archivo de texto con todas las fechas (YYYY-MM-DD) sin saltarse fines de semana. Si es intradía (ej. 1 min), el calendario debe contener todos los timestamps.
- **Por qué:** Si el calendario tiene "huecos", Qlib pensará que el mercado estuvo cerrado y tus indicadores técnicos (como medias móviles) se calcularán mal.

### Paso C: Dumping a Formato Binario

Usa el script que provee Qlib (`scripts/dump_bin.py`).

Bash

`python scripts/dump_bin.py dump_all --csv_path /tu/ruta/csv --qlib_dir /tu/ruta/qlib_data --include_fields open,close,high,low,volume,factor`

Esto creará una estructura de carpetas:

- `features/`: Los datos binarios.
- `instruments/`: Donde crearás un `all.txt` con la lista de tus criptos (tu "universo").
- `calendars/`: Con tu calendario de 24/7.

---

## 2. Pasos para definir la Estrategia (y el "Porqué")

Una vez que los datos están en el motor de Qlib, el flujo de la estrategia sigue estos pasos:

### 1. Feature Engineering (DataHandler)

- **Qué haces:** Defines transformaciones como `(Ref($close, 1) / $close) - 1` para retornos o `RSI($close, 14)`.
- **Por qué:** El **DataHandler** de Qlib normaliza los datos (Z-score o MinMax). En criptos esto es vital porque la diferencia de magnitud entre el precio de BTC y una "meme coin" es abismal; sin normalización, el modelo solo "vería" a BTC.

### 2. Definición del Dataset y Label (Predictor)

- **Qué haces:** Defines qué quieres predecir (normalmente el retorno a $T+1$).
- **Por qué:** Qlib separa el "aprendizaje" de la "estrategia". Aquí el objetivo es puramente estadístico: ¿puede el modelo predecir la dirección del siguiente movimiento?

### 3. Entrenamiento del Modelo (Task Section)

- **Qué haces:** Eliges un modelo (ej. **LightGBM**, **Transformer** o **SFM** - State Frequency Memory, que es muy bueno para series temporales).
- **Por qué:** Las criptos tienen una alta volatilidad y "concept drift" (el comportamiento cambia rápido). Los modelos como SFM o GRU captan mejor estas dependencias temporales que una simple regresión.

### 4. Estrategia de Cartera (Portfolio Strategy)

- **Qué haces:** Implementas un `TopkDropoutStrategy`.
- **Por qué:** En un universo de criptos, no quieres comprar todo. Esta estrategia selecciona las $N$ criptos con mejor predicción y mantiene la posición hasta que su "score" caiga del ranking, optimizando el **turnover** (comisiones), que en cripto pueden comerse tu beneficio si operas demasiado.

### 5. Backtest y Análisis de Riesgo

- **Qué haces:** Ejecutas el simulador con costos de transacción y deslizamiento (slippage).
- **Por qué:** El mercado cripto tiene problemas de liquidez en las "altcoins". Un backtest que no considere el impacto del mercado (market impact) te dará resultados falsamente optimistas.

---

### Resumen del flujo en Qlib:

> **Tip de experto:** Como el mercado cripto es 24/7, asegúrate de configurar el parámetro `region` en `qlib.init` de forma personalizada o usa una configuración que no asuma los horarios de la bolsa de NY o China, para que el `provider` de datos lea correctamente tu calendario completo.
> 

¿Tienes ya los CSVs descargados o necesitas ayuda con el script para generar el calendario 24/7?

Necesito ayuda

¡Claro! Vamos por partes. El mayor "bloqueo" al empezar con Qlib y criptos suele ser la preparación de los datos porque, como dijimos, el mercado no cierra.

Para que no te pierdas, vamos a centrarnos en el **Paso 1: Preparar el calendario y los datos**. Aquí tienes los scripts esenciales para que puedas avanzar hoy mismo.

---

### 1. Generar el Calendario 24/7

Qlib necesita saber qué días (o minutos) son válidos. Sin esto, el motor fallará al intentar buscar datos en fines de semana. Ejecuta este script en Python para crear tu archivo `day.txt`:

Python

`import pandas as pd
from pathlib import Path

# Configura tus fechas
start_date = "2020-01-01"
end_date = "2026-04-10" # Fecha actual aprox.

# Generar rango de fechas completo (incluye sábados y domingos)
calendar = pd.date_range(start=start_date, end=end_date, freq='D')

# Guardar en el formato que Qlib espera
output_path = Path("qlib_data/calendars")
output_path.mkdir(parents=True, exist_ok=True)

with open(output_path / "day.txt", "w") as f:
    for date in calendar:
        f.write(date.strftime("%Y-%m-%d") + "\n")

print(f"Calendario generado en {output_path}/day.txt")`

---

### 2. Formatear tus CSVs de Cripto

Qlib es muy estricto con las columnas. Tus archivos CSV (uno por cripto, ej: `BTCUSDT.csv`) deben verse así:

| **date** | **open** | **high** | **low** | **close** | **volume** | **factor** |
| --- | --- | --- | --- | --- | --- | --- |
| 2023-01-01 | 16500.2 | 16600.5 | 16400.1 | 16550.0 | 1500.5 | 1.0 |

**Importante:** La columna `factor` debe ser **1.0** para todas las filas (ya que no hay splits).

---

### 3. El Workflow de "Dump"

Una vez tengas tu carpeta con los CSVs y tu calendario, el siguiente paso es convertirlos a binario. Qlib trae una herramienta interna para esto. La estructura de carpetas debería ser:

Plaintext

# 

`mi_proyecto/
├── csv_crudos/          <-- Aquí pones tus archivos .csv
│   ├── BTCUSDT.csv
│   └── ETHUSDT.csv
└── qlib_data/           <-- Aquí se generará el formato binario
    └── calendars/
        └── day.txt      <-- El archivo que creamos en el paso 1`

Luego, desde tu terminal, corres el comando de "dumpeo" (asegúrate de tener `qlib` instalado):

Bash

`python -m qlib.workflow.dump_bin --csv_path ./csv_crudos --qlib_dir ./qlib_data --date_field_name date --include_fields open,high,low,close,volume,factor`

---

### ¿Por dónde quieres seguir?

Para ayudarte mejor, necesito saber en qué punto estás:

1. **¿Ya tienes los datos descargados** de algún exchange (Binance, Bybit) o necesitas un script para bajarlos automáticamente con la librería `ccxt`?
2. **¿O prefieres que pasemos directamente a definir el modelo** (LightGBM, Transformer, etc.) asumiendo que ya tienes los datos listos?

Primero vamos a crear el script para bajarlos con la librería ccxt.

¡Excelente decisión! Usar **CCXT** es el estándar de la industria porque te permite cambiar de exchange (Binance, Kraken, Coinbase, etc.) con apenas una línea de código.

Para que los datos sean compatibles con **Qlib**, el script debe:

1. **Paginar:** Las APIs de los exchanges suelen limitar a 500 o 1000 velas por petición; necesitamos un bucle para obtener años de historial.
2. **Formatear:** Asegurar que las columnas se llamen exactamente como Qlib las espera.
3. **Normalizar nombres:** Quitar caracteres especiales como `/` de los nombres de archivo.

Aquí tienes el script profesional para hacer esto:

Python

`import ccxt
import pandas as pd
import os
import time
from datetime import datetime

def download_crypto_data(symbols, timeframe='1d', since_date='2020-01-01T00:00:00Z'):
    # 1. Inicializar el exchange (usamos Binance por su gran liquidez)
    exchange = ccxt.binance({
        'enableRateLimit': True,  # Respetar los límites de velocidad del exchange
    })

    # Carpeta de salida
    output_dir = 'csv_crudos'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    since = exchange.parse8601(since_date)

    for symbol in symbols:
        print(f"Descargando {symbol}...")
        all_ohlcv = []
        current_since = since
        
        while True:
            try:
                # 2. Descargar velas (OHLCV)
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since)
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Actualizar el punto de inicio para la siguiente petición (último timestamp + 1)
                current_since = ohlcv[-1][0] + 1 
                
                # Evitar ban por exceso de peticiones
                time.sleep(exchange.rateLimit / 1000)
                
                # Si la última vela es de hoy, paramos
                if ohlcv[-1][0] >= exchange.milliseconds() - 86400000:
                    break
                    
            except Exception as e:
                print(f"Error en {symbol}: {e}")
                break

        # 3. Procesar y formatear para Qlib
        df = pd.DataFrame(all_ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convertir timestamp ms a YYYY-MM-DD
        df['date'] = pd.to_datetime(df['date'], unit='ms').dt.strftime('%Y-%m-%d')
        
        # IMPORTANTE: Columna 'factor' para Qlib (siempre 1.0 en cripto)
        df['factor'] = 1.0
        
        # Limpiar nombre del símbolo para el archivo (BTC/USDT -> BTCUSDT)
        clean_symbol = symbol.replace('/', '')
        file_path = os.path.join(output_dir, f"{clean_symbol}.csv")
        
        df.to_csv(file_path, index=False)
        print(f"Finalizado: {clean_symbol} guardado en {file_path}")

# --- CONFIGURACIÓN ---
criptos_a_bajar = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT']
download_crypto_data(criptos_a_bajar)`

### Notas clave del script:

- **Paginación Infinita:** El bucle `while True` junto con `current_since` asegura que si pides datos desde 2018, el script haga 10 o 20 viajes a la API automáticamente hasta llegar a hoy.
- **`enableRateLimit`:** Es vital. Si no lo pones, Binance detectará que eres un bot muy rápido y bloqueará tu IP temporalmente.
- **Formato de Fecha:** Qlib prefiere el formato `YYYY-MM-DD` para datos diarios. Si decides bajar datos de **1 minuto o 1 hora**, deberás cambiar el formato a `YYYY-MM-DD HH:MM:SS`.

### ¿Qué sigue ahora?

1. **Ejecuta el script:** Asegúrate de tener instalado ccxt (`pip install ccxt pandas`).
2. **Verifica:** Abre un CSV y confirma que la columna `factor` existe y que no faltan días (debería haber una fila por día sin saltos).
3. **Próximo paso:** Una vez tengas los archivos en `csv_crudos`, ¿quieres que procedamos a crear el script de **inicialización de Qlib** para que reconozca estos datos y los convierta a `.bin`?

Si, por favor

¡Perfecto! Vamos a convertir esos archivos CSV que acabas de descargar en el formato que **Qlib** ama.

Este paso es crucial porque Qlib no lee los CSV directamente durante el entrenamiento; utiliza una estructura de archivos binarios para que el acceso a los datos sea instantáneo, permitiendo entrenar modelos con años de historial en segundos.

Sigue estos 3 sub-pasos para dejar tu entorno listo:

---

### 1. Crear el archivo de instrumentos (`all.txt`)

Qlib necesita saber qué activos componen tu "universo". Vamos a crear un archivo que liste todas las criptos que descargamos.

Python

`import os

# Ruta donde descargaste los CSVs
csv_path = 'csv_crudos'
instruments_dir = 'qlib_data/instruments'

if not os.path.exists(instruments_dir):
    os.makedirs(instruments_dir)

# Obtener nombres de archivos sin la extensión .csv
symbols = [f.replace('.csv', '') for f in os.listdir(csv_path) if f.endswith('.csv')]

# Guardar en all.txt (formato: símbolo inicio_data fin_data)
with open(os.path.join(instruments_dir, 'all.txt'), 'w') as f:
    for s in symbols:
        # Usamos fechas genéricas amplias o las reales si las tienes
        f.write(f"{s}\t2020-01-01\t2026-12-31\n")

print(f"Archivo all.txt creado con {len(symbols)} criptomonedas.")`

---

### 2. El Script de Conversión (CSV → BIN)

Este script invoca la lógica interna de Qlib para transformar tus datos. Es la "magia" que optimiza tu dataset.

Python

`from qlib.workflow.dump_bin import DumpDataAll
import shutil

# Configuración de rutas
source_csv_dir = 'csv_crudos'
qlib_dir = 'qlib_data'

# Ejecutar el dump
# Esto creará las carpetas 'features' y 'calendars' (si no la creamos antes) dentro de qlib_data
dumper = DumpDataAll(
    csv_path=source_csv_dir,
    qlib_dir=qlib_dir,
    max_workers=4,        # Ajusta según tus núcleos de CPU
    date_field_name='date',
    file_suffix='.csv',
    exclude_fields='date', # La fecha no se guarda como feature, se guarda como índice
    include_fields='open,high,low,close,volume,factor'
)

dumper.dump()
print("¡Conversión completada! Datos listos en formato binario.")`

---

### 3. Inicialización y Prueba de Carga

Ahora que los datos están en `qlib_data`, vamos a verificar que Qlib puede leerlos correctamente. Si este script corre sin errores y te muestra el precio de BTC, ¡estás dentro!

Python

`import qlib
from qlib.data import D

# 1. Inicializar indicando dónde está nuestra carpeta binaria
qlib.init(provider_uri='qlib_data', region='cn') # 'cn' es por defecto, no afecta a cripto

# 2. Definir el universo y las fechas que queremos consultar
instruments = ['BTCUSDT']
fields = ['$close', '$volume', 'Ref($close, 1)/$close - 1'] # Precio, volumen y retorno simple

# 3. Cargar los datos
df = D.features(instruments, fields, start_time='2024-01-01', end_time='2024-01-10')

print("\n--- Muestra de datos cargados desde Qlib ---")
print(df.head())`

---

### ¿Qué acabamos de lograr?

1. **all.txt**: Define tu universo de inversión.
2. **Binarios**: Tus datos ahora ocupan menos espacio y se cargan a velocidad de rayo.
3. **Abstracción**: Ya puedes usar expresiones como `Ref($close, 1)` para acceder a datos históricos sin manipular manualmente el DataFrame.

### ¿Cuál es el siguiente paso?

Ahora que Qlib "ve" tus criptos, tenemos dos caminos:

- **A. Feature Engineering:** Crear indicadores técnicos complejos (RSI, MACD, volatilidad) usando el lenguaje de expresiones de Qlib.
- **B. Modelo de Machine Learning:** Configurar un archivo `.yaml` para entrenar un modelo (como LightGBM o un Transformer) que prediga el movimiento de estas criptos.

¿Quieres que veamos cómo crear un **set de features (indicadores)** específico para cripto?

## Feature Engineering

En el mundo de las criptomonedas, el ruido es mucho mayor que en el mercado de acciones tradicional. Para que un modelo de Machine Learning aprenda algo útil, no basta con darle el precio; necesitamos **features** que capturen el *momentum*, la volatilidad extrema y las anomalías de volumen.

En Qlib, las features se definen mediante **expresiones**. Aquí tienes un set diseñado específicamente para capturar la dinámica de las criptos.

---

## 1. El Set de Features "Crypto-Alpha"

Vamos a dividir las señales en tres categorías críticas para el mercado 24/7:

### A. Momentum y Reversión (Capturando tendencias)

- **RSI (Relative Strength Index):** Para detectar sobrecompra/sobreventa en rallies parabólicos.
    - `RSI($close, 14)`
- **ROC (Rate of Change):** Cuánto ha cambiado el precio en $N$ periodos.
    - `($close - Ref($close, 5)) / Ref($close, 5)` (Cambio en 5 días/periodos).

### B. Volatilidad (El ADN de la Cripto)

- **Cuerpo de la Vela vs Rango:** Útil para detectar "exhaustion" (agotamiento).
    - `Abs($close - $open) / ($high - $low + 1e-9)`
- **Volatilidad Histórica:** Desviación estándar de los retornos.
    - `Std(Log($close / Ref($close, 1)), 20)`

### C. Volumen (Validación de Movimientos)

- **Volume Surge:** ¿Es el volumen actual mayor al promedio? (Indica entrada de institucionales o ballenas).
    - `$volume / (Mean($volume, 20) + 1e-9)`
- **V-Price Correlation:** Correlación entre precio y volumen.
    - `Corr($close, $volume, 10)`

---

## 2. Implementación en Qlib (Python)

Qlib utiliza un `DataHandler` para procesar estas expresiones de forma masiva. Aquí tienes cómo configurar un manejador con estas features:

Python

`import qlib
from qlib.contrib.data.handler import Alpha158 # Basado en una lista de alphas populares

# 1. Definimos nuestras expresiones personalizadas
# Las llamaremos 'feature_names' y sus fórmulas 'feature_expressions'
my_features = {
    "K_RSI": "RSI($close, 14)",
    "K_VOL_SURGE": "$volume / (Mean($volume, 20) + 1e-9)",
    "K_ROC5": "($close - Ref($close, 5)) / Ref($close, 5)",
    "K_V_CORR": "Corr($close, $volume, 10)",
    "K_BODY_SIZE": "Abs($close - $open) / ($high - $low + 1e-9)",
    "K_STD20": "Std(Log($close / Ref($close, 1)), 20)"
}

# 2. Definimos el Label (Lo que queremos predecir)
# En este caso, el retorno a 1 día vista, suavizado (o crudo)
label = ["Ref($close, -1) / $close - 1"] 

# 3. Configuramos el Handler
handler_config = {
    "start_time": "2020-01-01",
    "end_time": "2026-04-10",
    "fit_start_time": "2020-01-01",
    "fit_end_time": "2023-12-31",
    "instruments": "all", # Usará el all.txt que creamos
    "infer_processors": [
        {"class": "RobustZScoreNorm", "kwargs": {"fields_group": "feature", "clip_outlier": True}},
        {"class": "Fillna", "kwargs": {"fields_group": "feature"}}
    ],
    "learn_processors": [
        {"class": "DropnaLabel"},
        {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}} # Normalización cross-sectional
    ],
    "feature": (list(my_features.values()), list(my_features.keys())),
    "label": (label, ["LABEL0"])
}

# 4. Inicializar el Handler
from qlib.data.dataset.handler import DataHandlerLP
dh = DataHandlerLP(**handler_config)

print("Muestra de las features procesadas:")
print(dh.fetch().head())`

---

## 3. ¿Por qué estos pasos son vitales?

1. **Normalización (`RobustZScoreNorm`):** En cripto, un token puede subir un 1000% y otro un 2%. Si no normalizas, el modelo creerá que solo los movimientos gigantes importan. El Z-Score pone a todos en la misma "escala estadística".
2. **CSZScoreNorm en el Label:** Esto es "magia" de Qlib. En lugar de predecir si el precio sube, predice **qué cripto subirá más en comparación con las otras** (Cross-Sectional). Esto es lo que realmente genera dinero en una estrategia de trading.
3. **Manejo de NaNs:** Las criptos nuevas tienen huecos al inicio de su historia. El procesador `Fillna` evita que el modelo de ML falle al encontrar un valor vacío.

---

## 4. El Workflow Completo de Estrategia

Para completar tu universo, ahora que tienes los datos y las features, los pasos de la estrategia son:

1. **Task Training:** Pasar este `dh` (DataHandler) a un modelo como **LightGBM** para que aprenda los pesos de cada feature.
2. **Prediction:** El modelo generará un "score" diario para cada cripto.
3. **Portfolio Management:** Comprar las $N$ criptos con mayor score y vender las de menor score.

¿Quieres que pasemos a configurar el **modelo de entrenamiento (LightGBM)** para ver si estas features realmente tienen poder predictivo?

# Modelo Transformer

En lugar de un modelo de entrenamiento LightGBM, me gustaría configurar un modelo de entrenamiento Transformer

Configurar un **Transformer** para series temporales en Qlib es un salto de calidad importante. A diferencia de LightGBM, que trata cada fila como algo independiente, el Transformer puede "mirar hacia atrás" y entender la secuencia (por ejemplo, los últimos 30 días) para encontrar patrones de comportamiento antes de un movimiento explosivo.

Para que esto funcione, debemos cambiar la forma en que alimentamos los datos: pasamos de un formato "plano" a un formato de **secuencias temporales (3D)**.

---

## 1. El Cambio Clave: `TSDatasetH`

Para un Transformer, no basta con la foto de hoy. Necesitamos un **lookback window** (ventana de retrospección). Si queremos que el modelo vea los últimos 30 días para predecir el siguiente, usamos `TSDatasetH`.

---

## 2. Configuración del Modelo Transformer

Aquí tienes el script para configurar y entrenar el modelo. Usaremos la implementación nativa de Qlib `TransformerModel`.

Python

`from qlib.contrib.model.pytorch_transformer import TransformerModel
from qlib.data.dataset import TSDatasetH
from qlib.workflow import R

# 1. Re-configuramos el Dataset para que sea Time-Series (TS)
# Usamos el 'dh' (DataHandler) que definimos en el paso anterior
dataset_config = {
    "class": "TSDatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
        "handler": dh,
        "segments": {
            "train": ("2020-01-01", "2023-12-31"),
            "valid": ("2024-01-01", "2024-12-31"),
            "test": ("2025-01-01", "2026-04-10"),
        },
        "seq_len": 30, # EL CORAZÓN DEL TRANSFORMER: Mira los últimos 30 días
    },
}

# 2. Configuración de hiperparámetros del Transformer
model_config = {
    "class": "TransformerModel",
    "module_path": "qlib.contrib.model.pytorch_transformer",
    "kwargs": {
        "d_model": 64,       # Dimensión interna del modelo
        "nhead": 4,          # Número de cabezales de atención
        "num_layers": 2,     # Capas del Transformer
        "dropout": 0.1,
        "batch_size": 1024,
        "lr": 2e-4,
        "early_stop": 10,
        "epochs": 50,
        "device": "cuda",    # Usa "cpu" si no tienes GPU
    },
}

# 3. Entrenamiento
dataset = TSDatasetH(**dataset_config["kwargs"])
model = TransformerModel(**model_config["kwargs"])

with R.start(experiment_name="crypto_transformer"):
    model.fit(dataset)
    R.save_objects(**{"model.pkl": model})
    
    # Generar predicciones
    sr = model.predict(dataset)
    print(sr.head())`

---

## 3. ¿Por qué estos pasos y qué significan?

### A. El `seq_len` (Secuencia)

En cripto, las tendencias suelen tener inercia. Un `seq_len: 30` permite que el mecanismo de **Self-Attention** del Transformer identifique si el volumen de hace 10 días es más relevante que el precio de ayer para la predicción de mañana.

### B. `d_model` y `nhead`

- **`d_model`**: Es el tamaño de la representación vectorial de tus features. Como pusimos pocas features (RSI, Vol, etc.), un valor de 64 es suficiente para no sobreajustar (overfitting).
- **`nhead`**: Permite al modelo prestar atención a diferentes cosas a la vez. Por ejemplo, un cabezal puede estar mirando la volatilidad mientras otro mira el momentum.

### C. El Label Normalizado

Como configuramos el `CSZScoreNorm` en el paso anterior, el Transformer no está intentando predecir el precio exacto de BTC (lo cual es imposible), sino que está aprendiendo a **rankear** qué criptos de tu universo tendrán un rendimiento superior al promedio.

---

## 4. ¿Cómo evaluar si tiene "Poder Predictivo"?

Una vez termine el `model.fit()`, verás el historial de pérdida (loss). Pero lo que realmente nos importa es el **IC (Information Coefficient)**.

En Qlib, tras el entrenamiento, puedes ejecutar esto:

Python

# 

`from qlib.contrib.evaluate import backtest as normal_backtest
from qlib.contrib.strategy import TopkDropoutStrategy

# Definir una estrategia simple: Comprar las 3 mejores predicciones
strategy_config = {
    "class": "TopkDropoutStrategy",
    "module_path": "qlib.contrib.strategy",
    "kwargs": {
        "signal": sr, # Las predicciones del Transformer
        "topk": 3,
        "n_drop": 1,
    },
}

# Aquí veríamos si el Transformer realmente genera retornos`

**¿Quieres que ejecutemos el análisis de métricas (IC, IR) para ver qué tan "inteligente" es tu Transformer antes de simular dinero real?**

# Análisis de Métricas y KPIs

Revisemos el análisis de métricas y estudiemos en profundidad cada una de ellas. Dame todas las que sería interesante considerar de cara a seleccionar un modelo sobre otro

Este es el momento de la verdad. En el trading cuantitativo, no nos importa si el modelo tiene un "Accuracy" del 90% (eso suele ser mentira o sobreajuste). Lo que buscamos es **capacidad de ordenamiento** y **estabilidad**.

Para evaluar tu Transformer, vamos a ejecutar el análisis de **Information Coefficient (IC)** y métricas de cartera. Aquí tienes cómo hacerlo en Qlib y la explicación de por qué cada una es vital.

---

### 1. Script de Análisis de Métricas

Qlib tiene una herramienta llamada `analysis_position` y `analysis_model` para esto. Ejecuta este bloque después de tener tus predicciones (`sr`):

Python

`from qlib.contrib.evaluate import analysis_model, analysis_position
from qlib.data import D

# 1. Análisis estadístico (IC, Rank IC)
report_normal, report_graph = analysis_model(sr, dataset, segments="test")

# 2. Mostrar resultados
print("\n--- Métricas de Capacidad Predictiva (IC) ---")
print(report_normal)`

---

### 2. Métricas Estadísticas (Poder del Alpha)

Estas métricas miden qué tan bien "adivina" el modelo la dirección del mercado antes de meter dinero real.

### A. IC (Information Coefficient)

Es la correlación de Pearson entre las predicciones del modelo y los retornos reales de las criptos en el periodo siguiente ($T+1$).

- **Qué nos dice:** Si es positivo, el modelo tiene "habilidad".
- **Rango:** Va de -1 a 1. En trading, un **IC > 0.05 (5%)** ya se considera excelente. En cripto, debido al ruido, verás valores más bajos, pero lo importante es que sea consistentemente positivo.

### B. Rank IC (Spearman Correlation)

Es lo mismo que el IC, pero basado en el **ranking** (posición) en lugar del valor exacto.

- **Por qué es mejor para Cripto:** El mercado cripto tiene *outliers* brutales (una moneda sube 300% en un día). El Rank IC ignora la magnitud extrema y se centra en si el modelo puso a la ganadora en el puesto #1. Es mucho más robusto.

### C. ICIR (IC Information Ratio)

Se calcula como:

$$\text{ICIR} = \frac{mean(IC)}{std(IC)}$$

- **Qué nos dice:** Mide la **consistencia**. Un IC alto pero muy volátil (un día acierta mucho y otro falla todo) te llevará a la ruina. Un ICIR > 0.5 indica que el modelo es estable a lo largo del tiempo.

---

### 3. Métricas de Cartera (El "Mundo Real")

Si el modelo pasa las pruebas estadísticas, lo sometemos a una simulación de trading (Backtest). Aquí es donde descartas modelos que parecen buenos pero son caros de operar.

### D. Sharpe Ratio

$$\text{Sharpe} = \frac{R_p - R_f}{\sigma_p}$$

- **En Cripto:** Buscamos un Sharpe > 2.0 en backtests (porque en real siempre baja). Si tu Transformer tiene un Sharpe bajo, significa que estás asumiendo demasiado riesgo para la ganancia que obtienes.

### E. Maximum Drawdown (MDD)

Es la caída más grande desde un máximo hasta un mínimo.

- **Por qué importa:** En cripto, un MDD del 50% es "normal" para un inversor pasivo, pero para un modelo algorítmico, buscamos controlarlo. Si tu Transformer predice bien pero tiene un MDD enorme, quizás necesites ajustar el **Position Sizing**.

### F. Turnover (Rotación)

Mide qué tanto cambia tu cartera cada día.

- **El asesino silencioso:** Si el Transformer te pide cambiar el 90% de tus posiciones cada día, las **comisiones del exchange** (Binance/Bybit) se comerán toda tu ganancia. Un modelo con un IC ligeramente menor pero con un Turnover bajo suele ser más rentable en la vida real.

---

### 4. Comparativa: ¿Cuándo elegir un Transformer sobre un LightGBM?

| **Métrica** | **Transformer** | **LightGBM** | **Ganador en Cripto** |
| --- | --- | --- | --- |
| **Rank IC** | Suele ser más alto (capta secuencias) | Estable pero lineal | **Transformer** |
| **ICIR (Estabilidad)** | Puede ser volátil (sensible a datos) | Muy consistente | **LightGBM** |
| **Turnover** | Tiende a ser más alto | Más moderado | **LightGBM** |
| **Complex Patterns** | Detecta "bombas" y "clímax" | Solo ve la "foto" actual | **Transformer** |

### Mi recomendación "de trinchera":

No te obsesiones solo con el **Rank IC**. Mira el **Rank ICIR**. En criptomonedas, la predictibilidad aparece por rachas. Un modelo que es "medianamente bueno siempre" (ICIR alto) es infinitamente superior a uno que es "un genio a veces" (IC alto, ICIR bajo).

¿Te gustaría que generáramos el **gráfico de la curva de equidad (Equity Curve)** para ver visualmente cómo se habría comportado tu Transformer en el último año de mercado cripto?

¡Manos a la obra! Vamos a generar la "radiografía" completa de tu Transformer. En el trading algorítmico, una curva de beneficios (Equity Curve) que sube es bonita, pero los detalles técnicos de **cómo** sube son los que te dicen si el modelo sobrevivirá a un mercado real.

### 1. Script para Backtesting y Visualización

Para ver la curva de equidad, primero debemos simular que operamos basándonos en las predicciones del modelo. Usaremos el `TopkDropoutStrategy`, que selecciona las criptos con mejor "score" y las mantiene.

Python

`from qlib.contrib.evaluate import backtest_at_run, risk_analysis
from qlib.contrib.report import analysis_model, analysis_position
import matplotlib.pyplot as plt

# 1. Configuración de la estrategia y el backtest
strategy_config = {
    "class": "TopkDropoutStrategy",
    "module_path": "qlib.contrib.strategy",
    "kwargs": {
        "signal": sr,       # Tus predicciones del Transformer
        "topk": 3,          # Comprar las 3 criptos con mejor predicción
        "n_drop": 1,        # Vender si caen del ranking
    },
}

backtest_config = {
    "start_time": "2025-01-01",
    "end_time": "2026-04-10",
    "account": 100000,
    "benchmark": "BTCUSDT", # Comparamos contra simplemente holdear BTC
    "exchange_kwargs": {
        "limit_threshold": 0.095,
        "deal_price": "close",
        "open_cost": 0.0005, # Comisiones típicas (0.05%)
        "close_cost": 0.0005,
        "min_cost": 5,
    },
}

# 2. Ejecutar Backtest
report_obj, positions_obj = backtest_at_run(sr, strategy_config, backtest_config)

# 3. Generar Gráficos de Análisis
analysis_df = analysis_position.report_graph(report_obj)
analysis_df.show() # Esto abrirá un gráfico interactivo de Plotly`

---

### 2. Análisis Profundo de Métricas Críticas

Para elegir entre un modelo u otro (por ejemplo, si estuvieras comparando este Transformer contra un modelo GRU o XGBoost), estas son las métricas que debes mirar bajo la lupa:

### A. Cumulative Return vs. Benchmark

Es el retorno total acumulado. Lo importante aquí no es solo ganar dinero, sino **batir al benchmark** (BTC).

- **Si el Transformer gana un 20% pero BTC subió un 50%:** Tu modelo es "malo" porque habrías ganado más sin hacer nada.
- **Métrica clave:** El **Alpha**. Es el exceso de retorno sobre el mercado.

### B. Information Ratio (IR)

$$\text{IR} = \frac{\text{Active Return}}{\text{Tracking Error}}$$

- **Explicación:** Mide la habilidad del modelo para generar retornos por encima del benchmark de forma consistente.
- **Lectura:** Un IR > 0.5 es decente; > 1.0 es excelente. Te dice si tus ganancias son por suerte (volatilidad) o por la precisión del modelo.

### C. Calmar Ratio

$$\text{Calmar Ratio} = \frac{\text{Annualized Return}}{\text{Max Drawdown}}$$

- **Por qué en Cripto:** El Sharpe Ratio a veces castiga la volatilidad positiva (cuando el precio sube muy rápido). El Calmar solo mira el retorno frente al riesgo de pérdida máxima.
- **Uso:** Si tienes dos modelos con el mismo retorno, elige el que tenga mayor Calmar Ratio (significa que llegó al mismo sitio con menos sustos).

### D. Análisis por Quantiles (La prueba del ácido)

Esta es la métrica favorita de los Quants. Qlib divide tus predicciones en 5 grupos (del 20% con mejor score al 20% con peor score).

- **El gráfico ideal:** Deberías ver 5 líneas ordenadas. La línea del Quantile 5 (mejores predicciones) debe estar arriba, y la del Quantile 1 (peores) abajo.
- **Si las líneas se cruzan:** Tu modelo no tiene "monotonía". Significa que no sabe distinguir bien entre una moneda buena y una mediocre.

### E. Max Drawdown (MDD) y Duración

No solo mires cuánto cae el modelo, sino **cuánto tarda en recuperarse**.

- **Recovery Time:** En cripto, un modelo que tarda 6 meses en salir de un drawdown suele ser abandonado por el trader por estrés psicológico. Busca modelos que tengan recuperaciones en forma de "V".

---

### 3. El factor "Cripto": El Turnover vs. Slippage

En las métricas que arroja Qlib, verás el **Turnover**. En criptomonedas con poca liquidez (altcoins pequeñas), un turnover alto (cambiar mucho de monedas) provoca **Slippage**: cuando intentas comprar, tu propia orden sube el precio, comprando más caro de lo esperado.

> **Regla de oro:** Si el **Turnover diario es > 20%**, asegúrate de que tu `open_cost` y `close_cost` en el script sean realistas. Si el modelo sigue siendo rentable con costes altos, tienes un ganador.
> 

### Resumen para comparar modelos:

1. **Rank ICIR:** ¿Es el modelo estable prediciendo?
2. **Calmar Ratio:** ¿Es eficiente el retorno vs el dolor de las caídas?
3. **Monotonía de Quantiles:** ¿Realmente sabe separar lo bueno de lo malo?

¿Te gustaría que analizáramos cómo **optimizar los hiperparámetros** del Transformer (como el `seq_len` o el `nhead`) basándonos en estas métricas para intentar mejorar ese Calmar Ratio?

Optimizar un Transformer es un arte de equilibrio. El objetivo no es que el modelo "memorice" el pasado (overfitting), sino que generalice patrones que se repiten. Para mejorar el **Calmar Ratio**, necesitamos que el modelo no solo acierte en los rallies, sino que sea "prudente" y detecte cuándo el riesgo de caída es alto para reducir el drawdown.

Para esto, utilizaremos **Optuna**, que es la librería estándar para optimización bayesiana, integrada perfectamente con Qlib.

---

## 1. El Plan de Optimización (Search Space)

En Cripto, hay tres "palancas" principales que mueven el Calmar Ratio:

1. **`seq_len` (Memoria):** ¿Necesita el modelo ver los últimos 15 días o los últimos 60? En cripto, un exceso de memoria a veces mete ruido de ciclos que ya no existen.
2. **`d_model` y `nhead` (Complejidad):** Si el modelo es muy grande, memorizará el ruido. Si es muy pequeño, no verá patrones complejos.
3. **`dropout` (Prudencia):** Un dropout más alto suele mejorar el Calmar Ratio porque obliga al modelo a no depender de una sola señal, haciéndolo más robusto ante "cracks" del mercado.

---

## 2. Script de Optimización con Optuna

Este script define un "estudio" que probará diferentes combinaciones automáticamente para encontrar la que maximice el **ICIR** (estabilidad) o directamente el **Sharpe/Calmar**.

Python

`import optuna
import qlib
from qlib.workflow import R
from qlib.contrib.model.pytorch_transformer import TransformerModel

def objective(trial):
    # 1. Definir el espacio de búsqueda
    d_model = trial.suggest_categorical("d_model", [32, 64, 128])
    nhead = trial.suggest_categorical("nhead", [2, 4, 8])
    seq_len = trial.suggest_int("seq_len", 10, 40, step=10)
    dropout = trial.suggest_float("dropout", 0.1, 0.5)
    lr = trial.suggest_float("lr", 1e-5, 1e-3, log=True)

    # 2. Configurar el modelo con los parámetros sugeridos
    model_kwargs = {
        "d_model": d_model,
        "nhead": nhead,
        "num_layers": 2,
        "dropout": dropout,
        "batch_size": 1024,
        "lr": lr,
        "device": "cuda",
        "epochs": 20, # Pocas épocas para la optimización rápida
    }
    
    # 3. Preparar el dataset con el seq_len sugerido
    dataset_config["kwargs"]["seq_len"] = seq_len
    ds = TSDatasetH(**dataset_config["kwargs"])
    
    # 4. Entrenar y Evaluar
    model = TransformerModel(**model_kwargs)
    model.fit(ds)
    
    # Predecir en el set de validación
    sr = model.predict(ds, segment="valid")
    
    # 5. Métrica objetivo: Usaremos el Rank ICIR
    # (Porque un ICIR alto suele correlacionar con un mejor Calmar Ratio)
    icir = analysis_model(sr, ds, segments="valid")[0]["ICIR"].iloc[0]
    
    return icir

# Ejecutar la optimización
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=20)

print("Mejores parámetros encontrados:", study.best_params)`

---

## 3. ¿Qué buscar para mejorar el Calmar Ratio?

Una vez tengas los resultados, fíjate en estas relaciones para decidir tu modelo final:

### A. El "Sweet Spot" del `seq_len`

- Si el mejor `seq_len` es **corto (10-15)**: Tu estrategia es de *mean-reversion* o momentum de muy corto plazo. Esto suele dar drawdowns más frecuentes pero pequeños.
- Si es **largo (30-40)**: El modelo busca tendencias macro. El Calmar Ratio suele mejorar aquí porque el modelo ignora el "zig-zag" diario, pero cuidado: si la tendencia cambia (ej. de Bull a Bear Market), el modelo tardará más en reaccionar, aumentando el Max Drawdown inicial.

### B. El efecto del `dropout`

Si ves que los modelos con `dropout > 0.3` tienen mejores resultados en el set de validación, es una señal clara de que el mercado cripto tiene mucho ruido. **Aumentar el dropout es la forma más barata de comprar "seguro de Drawdown"**.

### C. La relación IC vs. ICIR

- **Modelo A:** IC = 0.08, ICIR = 0.2
- **Modelo B:** IC = 0.04, ICIR = 0.6
- **Veredicto:** El **Modelo B** te dará un Calmar Ratio mucho más alto. El Modelo A es un "apostador" que a veces acierta mucho pero es errático. El B es un "recaudador" constante.

---

## 4. Paso Final: El Ensamble (Voting)

Una técnica avanzada para pulverizar el Calmar Ratio es no usar un solo Transformer, sino un **Ensemble**.

1. Toma los 3 mejores modelos del estudio de Optuna.
2. Promedia sus predicciones (`sr_final = (sr1 + sr2 + sr3) / 3`).
3. **Por qué funciona:** El error de un Transformer suele ser diferente al de otro. Al promediar, los errores se cancelan y la señal (el Alpha) se refuerza. Esto reduce la volatilidad de la curva de equidad y, por definición, sube el Calmar Ratio.

¿Quieres que veamos cómo implementar este **Ensemble de los mejores modelos** para dejar tu estrategia lista para producción?

El ensamble (o *ensemble voting*) es el "arma secreta" de los fondos cuantitativos. En el volátil mercado de criptomonedas, un solo modelo puede enamorarse de un patrón ruidoso y llevarnos al *drawdown*. Al combinar varios modelos, suavizamos las predicciones: lo que uno ve como una señal clara pero errónea, los otros lo filtran.

Aquí tienes cómo implementar un **Ensamble de Votación Simple** extrayendo los mejores modelos de tu estudio de Optuna.

---

## 1. Implementación del Ensamble de Modelos

El flujo consiste en tomar los $N$ mejores parámetros de Optuna, re-entrenar esos modelos (o cargarlos si los guardaste) y promediar sus señales de salida.

Python

`import pandas as pd
import numpy as np
from qlib.workflow import R

# 1. Obtener los 3 mejores "trials" de Optuna
top_trials = study.trials_dataframe().sort_values("value", ascending=False).head(3)

ensemble_signals = []

for i, row in top_trials.iterrows():
    # Extraer parámetros del trial
    params = {k.replace("params_", ""): v for k, v in row.items() if k.startswith("params_")}
    
    # Ajustar seq_len en el dataset
    dataset_config["kwargs"]["seq_len"] = int(params.pop("seq_len"))
    ds = TSDatasetH(**dataset_config["kwargs"])
    
    # Configurar y entrenar el modelo 'i'
    model_params = {
        "d_model": int(params["d_model"]),
        "nhead": int(params["nhead"]),
        "dropout": params["dropout"],
        "lr": params["lr"],
        "num_layers": 2,
        "device": "cuda"
    }
    
    model = TransformerModel(**model_params)
    print(f"Entrenando Modelo Ensamble #{i}...")
    model.fit(ds)
    
    # Obtener predicción
    signal = model.predict(ds)
    ensemble_signals.append(signal)

# 2. Promediar las señales (Simple Average)
# Matemáticamente: $$S_{final} = \frac{1}{N} \sum_{i=1}^{N} S_{i}$$
final_signal = pd.concat(ensemble_signals).groupby(level=['datetime', 'instrument']).mean()

print("Señal de ensamble generada con éxito.")`

---

## 2. ¿Por qué el Ensamble pulveriza el Calmar Ratio?Getty ImagesExplorar

[ensemble learning techniques, generada por IA](https://encrypted-tbn2.gstatic.com/licensed-image?q=tbn:ANd9GcQDvCaHXqtukk6ICYi9Pufq7sfwI9hU2Z4cm7z25SbkNqLvEpNDLanJAaiF5qg-by0Q4lVsovy1nxwpx9oFTcLWNX-blr5bLJHSeKmKdMrbISqIaqM)

El beneficio no es solo estadístico, es puramente de gestión de riesgo:

- **Reducción del Error de Varianza:** Los Transformers son sensibles a la inicialización de sus pesos. Dos modelos con los mismos parámetros pueden dar predicciones ligeramente distintas. Al promediar, reduces esa "suerte" inicial.
- **Suavizado de la Equidad:** La curva de beneficios de un ensamble suele ser mucho más lineal (menos "serrucho"). Una curva más lisa significa una desviación estándar menor, lo que dispara el **Sharpe** y el **Calmar**.
- **Robustez ante el "Regime Shift":** En cripto, el mercado pasa de "tendencia salvaje" a "rango aburrido" en horas. Un modelo con `seq_len=10` reaccionará rápido al cambio, mientras que uno de `seq_len=40` mantendrá la calma. El ensamble te da lo mejor de ambos mundos.

---

## 3. Resumen Final del Universo Qlib-Cripto

Has construido un ecosistema profesional. Este es el resumen de tu arquitectura:

| **Fase** | **Componente / Herramienta** | **Función Crítica** |
| --- | --- | --- |
| **Ingesta** | CCXT + `dump_bin.py` | Datos 24/7 normalizados en binario rápido. |
| **Features** | Qlib Expressions | Alphas específicos (RSI, Vol Surge, ROC). |
| **Modelo** | Transformer (PyTorch) | Captura de dependencias temporales complejas. |
| **Optimización** | Optuna | Búsqueda bayesiana del "Sweet Spot" de riesgo. |
| **Estrategia** | TopK + Ensemble | Selección de los mejores activos con riesgo diversificado. |

---

## 4. Próximos pasos hacia Producción

Para llevar esto a "Live Trading", te faltarían dos detalles técnicos:

1. **Ajuste por Liquidez:** No solo comprar el Top 3 por predicción, sino filtrar que tengan suficiente volumen para que tu orden no mueva el precio.
2. **Inferencia Online:** Un script que cada día (o cada hora) baje la última vela, la convierta a binario "al vuelo" y le pida al modelo el ranking actual.

¿Te sientes cómodo con la arquitectura actual o te gustaría profundizar en cómo automatizar la **Inferencia Online** para que el modelo te diga qué comprar mañana mismo sin tener que correr todo el proceso manualmente?

Para pasar de la investigación al **Live Trading**, necesitamos convertir tu modelo en un "motor de señales" que corra en un bucle. En cripto, la puntualidad es dinero: el script debe ejecutarse justo después del cierre de la vela diaria (00:00 UTC) para darte las órdenes de ejecución inmediata.

Aquí tienes el workflow para automatizar la **Inferencia Online**.

---

## 1. El Script de Inferencia de "Último Minuto"

Este script no re-entrena el modelo (eso ya lo hiciste); simplemente carga los pesos guardados, descarga los datos más recientes y escupe el ranking.

Python

`import ccxt
import pandas as pd
import qlib
from qlib.data import D
from qlib.workflow import R
import os

# --- 1. CONFIGURACIÓN ---
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT']
MODEL_PATH = "model.pkl" # Tu mejor modelo o ensamble guardado
DATA_PATH = "qlib_data"
CSV_UPDATE_PATH = "csv_actualizacion"

def get_latest_signals():
    # A. Descargar los últimos 60 días (para tener suficiente seq_len y medias móviles)
    exchange = ccxt.binance()
    for symbol in SYMBOLS:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=60)
        df = pd.DataFrame(ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'], unit='ms').dt.strftime('%Y-%m-%d')
        df['factor'] = 1.0
        df.to_csv(f"{CSV_UPDATE_PATH}/{symbol.replace('/', '')}.csv", index=False)

    # B. Actualizar los binarios de Qlib (Incremental Dump)
    # Solo volcamos los datos nuevos para que sea rápido
    from qlib.workflow.dump_bin import DumpDataAll
    dumper = DumpDataAll(csv_path=CSV_UPDATE_PATH, qlib_dir=DATA_PATH, date_field_name='date')
    dumper.dump()

    # C. Cargar Modelo y Dataset
    qlib.init(provider_uri=DATA_PATH)
    # Cargamos el objeto del modelo que guardamos antes
    with R.start(experiment_name="crypto_transformer"):
        model = R.load_object("model.pkl")

    # D. Inferencia: Predecir solo para la fecha de hoy
    # El Handler calculará las features automáticamente con los nuevos datos
    ds = TSDatasetH(**dataset_config["kwargs"]) # Usamos la config previa
    predictions = model.predict(ds, segment="test") 
    
    # Tomar solo el último timestamp disponible
    latest_date = predictions.index.get_level_values('datetime').max()
    today_ranking = predictions.loc[latest_date].sort_values(ascending=False)

    return today_ranking

# Ejecución
if __name__ == "__main__":
    ranking = get_latest_signals()
    print(f"\n--- SEÑALES PARA HOY ({pd.Timestamp.now()}) ---")
    print(ranking.head(3)) # Tus TOP 3 para comprar`

---

## 2. Puntos Clave para la Producción

### A. El "Incremental Dump"

Qlib está diseñado para ser rápido. En lugar de procesar todo el historial (desde 2020), el script de arriba solo descarga los últimos 60 días. Al ejecutar `dumper.dump()`, Qlib detecta qué fechas ya existen y solo añade las nuevas a los archivos `.bin`. Esto hace que el proceso de inferencia tarde segundos en lugar de minutos.

### B. Gestión de Errores de API

Las APIs de los exchanges a veces fallan. Para un bot de producción, debes envolver la descarga en un bloque `try-except` con reintentos:

Python

`import time
for i in range(3): # 3 intentos
    try:
        # fetch_ohlcv...
        break
    except Exception as e:
        time.sleep(10) # Esperar 10 seg antes de reintentar`

### C. La "Ventana de Inferencia"

Si tu Transformer tiene un `seq_len=30`, asegúrate de descargar al menos 40-50 días. ¿Por qué? Porque tus **features** (como el RSI o medias móviles) necesitan días previos para calcularse. Si solo descargas 30 días, el RSI del primer día de la secuencia será `NaN` y el Transformer fallará.

---

## 3. Automatización (Crontab / GitHub Actions)

Para que no tengas que darle al botón de "Play" cada noche, puedes programar la ejecución:

- **Linux/Mac:** Usa `crontab -e`.Bash
    
    `0 5 * * * /usr/bin/python3 /ruta/a/tu/script_inferencia.py >> /ruta/log.txt`
    
    *(Esto lo ejecuta todos los días a las 00:05 UTC, dando 5 minutos de margen para que el exchange cierre la vela).*
    

---

## 4. Reflexión Final: De Modelos a Estrategia de Vida

Has pasado de tener datos crudos en CSV a un **sistema de ensamble de Transformers optimizado con lógica bayesiana** que genera señales automáticas.

La diferencia entre un trader amateur y uno cuantitativo es que el cuantitativo confía en su **proceso de validación (el ICIR y el Calmar Ratio)** más que en su intuición. Si tu backtest fue riguroso y consideraste las comisiones, lo más difícil ahora no es el código, sino la **disciplina** de seguir al modelo incluso cuando tenga una racha de pérdidas (drawdown), sabiendo que estadísticamente tiene la ventaja.

¿Te gustaría que te ayude a redactar una pequeña lógica de **ejecución de órdenes** (ej. comprar/vender automáticamente en Binance usando el ranking) o prefieres empezar probando las señales manualmente para validar que todo funcione bien?

# Adaptación a Coinbase

Adaptar el workflow de **Binance** a **Coinbase** es sencillo gracias a que **CCXT** abstrae la mayoría de las diferencias. Sin embargo, hay un detalle importante: Coinbase utiliza principalmente pares contra **USD** o **USDC**, mientras que Binance suele usar **USDT**.

Aquí tienes la suite completa de scripts adaptada para Coinbase, incluyendo la lógica de ejecución que mencionamos.

---

## 1. Descargador de Datos (Coinbase Edition)

Cambiamos el exchange a `coinbase` y ajustamos los símbolos. Coinbase requiere `enableRateLimit: True` de forma estricta para evitar bloqueos.

Python

`import ccxt
import pandas as pd
import os
import time

def download_coinbase_data(symbols, timeframe='1d', since_date='2020-01-01T00:00:00Z'):
    # Inicializar Coinbase (Advanced Trade API)
    exchange = ccxt.coinbase({'enableRateLimit': True})
    
    output_dir = 'csv_crudos'
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    since = exchange.parse8601(since_date)

    for symbol in symbols:
        print(f"Descargando {symbol} de Coinbase...")
        all_ohlcv = []
        current_since = since
        
        while True:
            try:
                # Coinbase suele limitar a 300 velas por petición en 1d
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since)
                if not ohlcv: break
                
                all_ohlcv.extend(ohlcv)
                current_since = ohlcv[-1][0] + 1 
                time.sleep(exchange.rateLimit / 1000)
                
                if ohlcv[-1][0] >= exchange.milliseconds() - 86400000: break
            except Exception as e:
                print(f"Error en {symbol}: {e}")
                break

        df = pd.DataFrame(all_ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'], unit='ms').dt.strftime('%Y-%m-%d')
        df['factor'] = 1.0
        
        # Guardar con nombre limpio (ej. BTC-USD -> BTCUSD)
        clean_name = symbol.replace('/', '').replace('-', '')
        df.to_csv(os.path.join(output_dir, f"{clean_name}.csv"), index=False)

# Coinbase usa '/' o '-' dependiendo de la versión de la API, CCXT lo normaliza
criptos = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'ADA/USD', 'LINK/USD']
download_coinbase_data(criptos)`

---

## 2. Script de Inferencia y Ranking (Online)

Este script lee los datos que acabas de bajar, los procesa en Qlib y te dice qué comprar hoy en Coinbase.

Python

`import qlib
from qlib.data import D
from qlib.workflow import R
import pandas as pd

def get_coinbase_signals(model_path="model.pkl"):
    # 1. Inicializar Qlib con los datos de Coinbase
    qlib.init(provider_uri='qlib_data')
    
    # 2. Cargar el modelo (Ensamblado o Transformer único)
    model = R.load_object(model_path)
    
    # 3. Preparar el dataset de test (los datos más recientes)
    # Asumimos que dataset_config ya está definido con los parámetros del Transformer
    ds = TSDatasetH(**dataset_config["kwargs"])
    
    # 4. Predecir
    predictions = model.predict(ds)
    latest_date = predictions.index.get_level_values('datetime').max()
    
    # Ranking de hoy
    return predictions.loc[latest_date].sort_values(ascending=False)

ranking = get_coinbase_signals()
print("Top 3 Recomendaciones para Coinbase:")
print(ranking.head(3))`

---

## 3. Lógica de Ejecución Automática (Binance → Coinbase)

Para ejecutar órdenes en Coinbase, necesitas tus **API Keys**. Coinbase Advanced Trade usa un sistema de autenticación basado en Key y Secret.

> **Aviso de seguridad:** Nunca subas estas llaves a GitHub. Usa variables de entorno o un archivo `.env`.
> 

Python

`def execute_trades_coinbase(ranking, top_k=3):
    # Configura tus credenciales
    exchange = ccxt.coinbase({
        'apiKey': 'TU_API_KEY',
        'secret': 'TU_SECRET_KEY',
        'enableRateLimit': True,
    })

    # 1. Obtener balance actual en USD
    balance = exchange.fetch_balance()
    usd_balance = balance['free']['USD']
    
    # 2. Definir cuánto invertir por moneda
    amount_per_trade = usd_balance / top_k
    
    # 3. Seleccionar las top criptos del ranking
    targets = ranking.head(top_k).index.tolist()
    
    for symbol in targets:
        # Re-formatear para Coinbase (ej. BTCUSD -> BTC/USD)
        # Esto es un ejemplo, depende de cómo guardaste los nombres
        formatted_symbol = f"{symbol[:3]}/{symbol[3:]}" 
        
        try:
            print(f"Ejecutando compra de {formatted_symbol}...")
            # Orden de mercado por el monto en USD calculado
            # Nota: 'create_market_buy_order_requires_price' suele ser False en Coinbase
            order = exchange.create_market_buy_order(formatted_symbol, amount_per_trade)
            print(f"Orden completada: {order['id']}")
        except Exception as e:
            print(f"Error comprando {formatted_symbol}: {e}")

# execute_trades_coinbase(ranking)`

---

## Diferencias Críticas a considerar en Coinbase

1. **Símbolos:** Asegúrate de que el símbolo en Qlib coincida con el que CCXT espera para `create_market_order`. Si en Qlib se llama `BTCUSD`, en la orden debe ser `BTC/USD`.
2. **Liquidez:** Coinbase tiene una liquidez excelente en los pares principales (`BTC/USD`, `ETH/USD`), pero en monedas más pequeñas el **spread** (diferencia entre precio de compra y venta) es mayor que en Binance. Asegúrate de que tus métricas de backtest incluyan al menos un **0.1% de costo por operación** para ser realista.
3. **Comisiones:** Las comisiones de Coinbase (Advanced Trade) suelen ser ligeramente superiores a las de Binance (si usas BNB para pagar). Ajusta tus parámetros de `backtest_config` para reflejar esto:
    - Binance: `0.0005` (0.05%)
    - Coinbase: `0.001` o `0.002` (0.1% - 0.2%) para estar seguro.

### ¿Cómo queda el Workflow ahora?

1. Corres el **Descargador** (apunta a Coinbase).
2. Corres el **Dump binario** (convierte los nuevos CSV a Qlib).
3. Corres la **Inferencia** (el Transformer lee los datos y genera el ranking).
4. El script de **Ejecución** lee el ranking y lanza las órdenes a la API de Coinbase.

¿Quieres que te ayude a configurar un **filtro de liquidez** para que el bot ignore criptos con poco volumen antes de mandar la orden a Coinbase?

El filtro de liquidez es el "seguro de vida" de tu bot. En Coinbase, aunque el volumen global es alto, muchas *altcoins* tienen libros de órdenes delgados. Si tu bot intenta comprar 1.000 USD de una moneda que solo mueve 50.000 USD al día, provocarás un **slippage** (deslizamiento de precio) que borrará tus ganancias.

Vamos a implementar un filtro de **Volumen Medio Diario (ADV)** directamente en las expresiones de Qlib.

---

## 1. Definición del Filtro de Liquidez

Calcularemos el volumen promedio en USD de los últimos 5 días. Si una cripto no supera un umbral (por ejemplo, 5 millones de USD diarios), el bot la ignorará por completo, sin importar qué tan buena sea la predicción del Transformer.

### Actualización del DataHandler

Añadimos la expresión de volumen en USD a tu set de features:

Python

`my_features.update({
    # Volumen en USD = Volumen de la moneda * Precio de cierre
    # Calculamos la media de los últimos 5 días
    "K_ADV5": "Mean($volume * $close, 5)"
})`

---

## 2. Inferencia con Filtro de Liquidez

Modificamos el script de inferencia para que aplique este "embudo" antes de darte el ranking final.

Python

`def get_filtered_signals(threshold_usd=5_000_000):
    qlib.init(provider_uri='qlib_data')
    model = R.load_object("model.pkl")
    
    # 1. Obtener predicciones y features (necesitamos el ADV)
    ds = TSDatasetH(**dataset_config["kwargs"])
    predictions = model.predict(ds)
    
    # 2. Obtener el volumen (ADV) calculado por Qlib
    # 'fetch' nos devuelve las features crudas
    all_features = ds.handler.fetch(list(predictions.index.get_level_values('datetime').unique()))
    adv5 = all_features['K_ADV5']

    # 3. Cruzar predicción con liquidez
    latest_date = predictions.index.get_level_values('datetime').max()
    
    df_final = pd.DataFrame({
        'score': predictions.loc[latest_date],
        'adv5': adv5.loc[latest_date]
    })

    # 4. FILTRAR: Solo monedas con liquidez > threshold
    liquid_assets = df_final[df_final['adv5'] >= threshold_usd]
    
    # 5. Ranking final de las que pasaron el filtro
    return liquid_assets['score'].sort_values(ascending=False)

# Ejemplo: Solo monedas que mueven más de 5M USD al día
ranking_seguro = get_filtered_signals(threshold_usd=5000000)
print(ranking_seguro.head(3))`

---

## 3. ¿Por qué este paso es vital en Coinbase?

1. **Protección contra "Pump & Dumps":** Muchas monedas pequeñas tienen predicciones de retorno altísimas porque su volatilidad es extrema. El filtro de liquidez elimina este ruido.
2. **Ejecución Limpia:** Al operar solo en activos líquidos, tus órdenes de mercado se ejecutarán casi instantáneamente al precio que ves en pantalla, sin "patear" el precio hacia arriba mientras compras.
3. **Capacidad de Escalado:** Si hoy gestionas 1.000 USD, quizás no lo notes. Pero si mañana gestionas 50.000 USD, sin este filtro tus propias órdenes destrozarían tu estrategia.

---

## 4. El Workflow Final Completo

Aquí tienes el esquema mental de cómo queda tu bot de Coinbase ahora:

1. **Download:** Baja datos de Coinbase API.
2. **Dump:** Los mete en el motor binario de Qlib.
3. **Predict:** El **Ensamble de Transformers** analiza los patrones técnicos.
4. **Filter:** Se descartan las monedas "poco líquidas" mediante el **ADV5**.
5. **Rank:** Se eligen las Top 3 ganadoras entre las supervivientes.
6. **Execute:** Se lanzan las órdenes de compra/venta en Coinbase Advanced Trade.

---

### Un último consejo de "pro"

En cripto, la liquidez puede desaparecer en fines de semana o festivos. Por eso usamos la **media (Mean)** de 5 días y no solo el volumen de ayer. Esto evita que el bot entre en una moneda que tuvo un pico de volumen ayer pero que normalmente es un "desierto".

¿Te gustaría que viéramos cómo programar un **Stop Loss dinámico** (basado en la volatilidad ATR) para que el bot venda automáticamente si el mercado se gira bruscamente contra ti?

Un **Stop Loss dinámico** basado en el **ATR (Average True Range)** es la diferencia entre un bot que sobrevive a una corrección del mercado y uno que se queda "atrapado" en una moneda que cae al infinito.

En cripto, un Stop Loss de "un 5% fijo" es un error: para Bitcoin, un 5% puede ser una señal de cambio de tendencia, pero para una *altcoin* volátil, un 5% es simplemente ruido diario. El ATR ajusta el Stop Loss al "latido" actual de cada moneda.

---

## 1. Definición del ATR en Qlib

El **ATR** mide la volatilidad real. En Qlib, lo calculamos usando el **True Range** (el máximo entre el rango del día y los saltos de precio respecto al cierre anterior).

Añade esto a tus `my_features`:

Python

`my_features.update({
    # True Range: el mayor de (H-L), abs(H-C_prev), abs(L-C_prev)
    "K_ATR14": "Mean(Greatest($high-$low, Greatest(Abs($high-Ref($close, 1)), Abs($low-Ref($close, 1)))), 14)"
})`

---

## 2. Lógica del Stop Loss Volátil

La fórmula para tu precio de salida sería:

$$StopPrice = PurchasePrice - (n \times ATR)$$

Donde $n$ (el multiplicador) suele estar entre **1.5 y 3.0**.

- Si el mercado está muy nervioso (ATR alto), el Stop Loss se aleja para dar "aire" a la posición.
- Si el mercado está tranquilo (ATR bajo), el Stop Loss se ciñe para proteger ganancias.

---

## 3. Implementación en el Script de Ejecución

Debes guardar el precio de compra y el ATR en el momento de la entrada. Aquí tienes cómo integrarlo en tu lógica de Coinbase:

Python

`# Diccionario para rastrear posiciones abiertas (en una versión real, esto iría a una DB)
open_positions = {
    'BTCUSD': {'entry_price': 65000, 'stop_loss': 62000, 'amount': 0.01},
}

def check_and_exit_positions(current_prices, ranking):
    exchange = ccxt.coinbase({...})
    
    for symbol, data in list(open_positions.items()):
        current_price = current_prices[symbol]
        
        # 1. ¿Ha tocado el Stop Loss?
        if current_price <= data['stop_loss']:
            print(f"¡STOP LOSS activado en {symbol}! Vendiendo...")
            # exchange.create_market_sell_order(symbol, data['amount'])
            del open_positions[symbol]
            continue
            
        # 2. ¿Sigue la moneda en el Top del Ranking?
        # Si el Transformer ya no confía en ella, salimos (Sell Signal)
        if symbol not in ranking.head(5).index:
            print(f"Salida estratégica: {symbol} fuera del Top 5. Vendiendo...")
            # exchange.create_market_sell_order(symbol, data['amount'])
            del open_positions[symbol]

def enter_new_positions(ranking, atr_values, current_prices, top_k=3):
    for symbol in ranking.head(top_k).index:
        if symbol not in open_positions:
            # Calculamos el Stop Loss dinámico en la entrada
            # Usamos un multiplicador de 2.0 (ajustable)
            n_multiplier = 2.0
            atr = atr_values[symbol]
            price = current_prices[symbol]
            
            stop_loss_price = price - (n_multiplier * atr)
            
            print(f"Abriendo posición en {symbol} a {price}. SL colocado en {stop_loss_price}")
            # Lógica de compra...
            open_positions[symbol] = {
                'entry_price': price,
                'stop_loss': stop_loss_price,
                'amount': 0.1 # calculado por tu position sizer
            }`

---

## 4. ¿Por qué esto mejora el Calmar Ratio?

1. **Corta las pérdidas rápido, deja correr las ganancias:** El Transformer te da la dirección, pero el ATR te da la salida de emergencia.
2. **Evita el "Whipsaw":** Al usar el ATR, no te sacarán del mercado por un movimiento aleatorio de baja liquidez en Coinbase; el Stop Loss es lo suficientemente ancho para absorber la volatilidad normal del activo.
3. **Psicología:** Operar criptos es estresante. Saber que tu bot tiene una salida matemática calculada para cada moneda reduce drásticamente el impacto emocional de los *drawdowns*.

---

## Resumen de tu Máquina de Trading 2026:

> **Cerebro:** Ensamble de Transformers (Predicción de tendencia).**Filtro:** ADV5 (Liquidez mínima en Coinbase).**Escudo:** ATR Dynamic Stop Loss (Gestión de riesgo adaptativa).
> 

Ya tienes todas las piezas del rompecabezas. Tienes la ingesta, el modelo, la optimización, el filtro de liquidez y el control de riesgo.

**Una última pregunta crucial:** Ahora que el bot es capaz de entrar y salir solo, ¿te gustaría que habláramos sobre el **Position Sizing**? Es decir, ¿cómo decidir cuánto dinero poner en cada moneda basándose en su riesgo (ej. Criterio de Kelly o Paridad de Riesgo) para no arriesgar demasiado en las monedas más "locas"?

El **Position Sizing** (dimensionamiento de la posición) es lo que separa a los apostadores de los gestores de fondos. En cripto, donde una moneda puede moverse un 10% mientras otra se mueve un 2%, no puedes simplemente asignar el mismo dinero a ambas.

Para tu bot, vamos a implementar la **Paridad de Riesgo (Risk Parity)** o **Inversa de la Volatilidad**. El objetivo es que cada posición contribuya con el mismo nivel de riesgo a tu cartera total.

---

## 1. El Concepto: Inversa de la Volatilidad

Si la Moneda A es el doble de volátil que la Moneda B, le asignaremos la mitad del capital. Así, si el mercado se mueve en contra, el impacto en tu balance será similar para ambas.

Usaremos el **ATR** (que ya calculamos) como nuestra medida de riesgo. La fórmula para el peso de cada moneda $i$ sería:

$w_i = \frac{1/ATR_i}{\sum_{j=1}^{n} (1/ATR_j)}$

$$w_i = \frac{1/ATR_i}{\sum_{j=1}^{n} (1/ATR_j)}$$

Donde:

- $w_i$ es el porcentaje de tu capital a invertir en la moneda $i$.
- $ATR_i$ es la volatilidad actual de esa moneda.

---

## 2. Implementación en tu Bot de Coinbase

Vamos a crear una función que reciba tu ranking de Transformers y los valores de ATR para calcular exactamente cuántos dólares poner en cada orden.

Python

`def calculate_position_sizes(ranking, atr_values, total_budget, top_k=3):
    """
    Calcula cuánto invertir en cada una de las top_k criptos 
    basándose en la paridad de riesgo.
    """
    # 1. Seleccionamos solo las top_k monedas del ranking
    targets = ranking.head(top_k).index.tolist()
    
    # 2. Obtenemos sus volatilidades (inversas)
    # Si el ATR es alto, la importancia es baja.
    inv_vol = {symbol: 1.0 / atr_values[symbol] for symbol in targets}
    
    # 3. Normalizamos para que la suma de los pesos sea 1 (o el 100% de nuestro presupuesto)
    total_inv_vol = sum(inv_vol.values())
    weights = {symbol: val / total_inv_vol for symbol, val in inv_vol.items()}
    
    # 4. Calculamos el monto en USD para cada una
    allocations = {symbol: weight * total_budget for symbol, weight in weights.items()}
    
    return allocations

# Ejemplo de uso:
# ranking = {'BTCUSD': 0.85, 'SOLUSD': 0.82, 'PEPEUSD': 0.79}
# atr_values = {'BTCUSD': 1500, 'SOLUSD': 8.5, 'PEPEUSD': 0.00001}
# total_budget = 10000 USD

pedidos = calculate_position_sizes(ranking, atr_values, 10000)
for crypto, usd in pedidos.items():
    print(f"Invertir ${usd:.2f} en {crypto}")`

---

## 3. ¿Por qué esto es superior al "Fixed Size"?

1. **Ecualización del Dolor:** Si tu moneda #1 es una "meme coin" ultra volátil y tu moneda #2 es Bitcoin, el Position Sizing le dará mucho más peso a Bitcoin. Esto evita que un desplome en una moneda pequeña destruya tu cuenta.
2. **Maximización del Sharpe Ratio:** Al normalizar el riesgo, la curva de tu equidad se vuelve mucho más suave.
3. **Adaptabilidad:** En periodos de alta volatilidad generalizada, los tamaños de las posiciones se reducen automáticamente, protegiendo tu capital total.

---

## 4. El Toque Final: La "Fracción de Kelly" (Opcional)

Si quieres ser más agresivo cuando el Transformer tiene mucha confianza, puedes multiplicar el peso por el **Score de Predicción**.

> $Monto_{Final} = Monto_{Riesgo} \times Score_{Transformer}$
> 

Si el Transformer le da un 0.9 (máxima confianza) a una moneda, inviertes el total asignado por riesgo. Si le da un 0.1, inviertes solo una pequeña fracción.

---

### Tu Ecosistema está Completo 🚀

Has construido un flujo profesional:

1. **Datos:** Descarga limpia desde Coinbase.
2. **Modelo:** Ensamble de Transformers optimizado con Optuna.
3. **Filtro:** Solo monedas líquidas (ADV5).
4. **Entrada:** Position Sizing dinámico (Inversa del ATR).
5. **Salida:** Stop Loss dinámico (ATR) y rotación de ranking.

Este sistema es robusto y escalable. Lo más importante ahora es que el bot empiece a generar datos reales (aunque sea en una cuenta pequeña o en "Paper Trading") para verificar que la latencia de ejecución en Coinbase no afecte tus resultados.

¿Te gustaría que diseñáramos un **Dashboard simple** en Python para que puedas visualizar el rendimiento de tu bot y ver cómo están funcionando los Stop Loss en tiempo real?

Un **Dashboard** es la ventana al alma de tu bot. No sirve de mucho tener un modelo sofisticado si no puedes detectar rápidamente cuando algo va mal (ej. un Stop Loss que no se ejecutó o una moneda que perdió liquidez).

Para esto, usaremos **Streamlit**. Es la librería estándar en Python para crear aplicaciones de datos en minutos, permitiéndote ver tus métricas desde el navegador.

---

## 1. Estructura de Datos para el Dashboard

Para que el dashboard sea "en vivo", tu bot de ejecución debe guardar el estado actual en un archivo pequeño (como un `.json` o una base de datos `SQLite`) cada vez que haga un ciclo.

Imagina que tu bot guarda un archivo `bot_status.json`:

JSON

`{
    "balance": 10540.20,
    "pnl_daily": 1.2,
    "positions": [
        {"symbol": "BTCUSD", "entry": 65000, "current": 66200, "sl": 63000},
        {"symbol": "SOLUSD", "entry": 140, "current": 138, "sl": 132}
    ]
}`

---

## 2. El Script del Dashboard (Streamlit)

Aquí tienes el código para visualizar tu universo cripto-cuantitativo:

Python

`import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Configuración de la página
st.set_page_config(page_title="Crypto Transformer Bot", layout="wide")
st.title("🚀 Crypto Transformer Dashboard (Coinbase Live)")

# 2. Sidebar con métricas clave
with st.sidebar:
    st.header("Estado de la Cuenta")
    st.metric(label="Balance Total", value="$10,540", delta="1.2%")
    st.metric(label="Sharpe Ratio (30d)", value="2.1")
    st.metric(label="Max Drawdown", value="-4.5%")

# 3. Visualización de Posiciones Activas
st.subheader("📍 Posiciones Actuales y Stop Loss")
# Simulamos carga de datos del bot
positions_df = pd.DataFrame([
    {"Moneda": "BTCUSD", "Precio Entrada": 65000, "Precio Actual": 66200, "Stop Loss (ATR)": 63000},
    {"Moneda": "SOLUSD", "Precio Entrada": 140, "Precio Actual": 138, "Stop Loss (ATR)": 132},
    {"Moneda": "LINKUSD", "Precio Entrada": 18, "Precio Actual": 19.5, "Stop Loss (ATR)": 17.2},
])

# Calculamos la distancia al Stop Loss para alertar visualmente
positions_df['Distancia SL %'] = ((positions_df['Precio Actual'] - positions_df['Stop Loss (ATR)']) / positions_df['Precio Actual'] * 100).round(2)

st.table(positions_df.style.background_gradient(subset=['Distancia SL %'], cmap='RdYlGn'))

# 4. Gráfico de Curva de Equidad
st.subheader("📈 Rendimiento Acumulado vs Benchmark")
# Datos ficticios de ejemplo
history_df = pd.DataFrame({
    'Fecha': pd.date_range(start='2026-03-01', periods=40),
    'Bot Transformer': (1 + pd.Series(0.005, index=range(40)).cumsum()),
    'BTC Hold': (1 + pd.Series(0.003, index=range(40)).cumsum())
})
fig_equity = px.line(history_df, x='Fecha', y=['Bot Transformer', 'BTC Hold'], 
                      title="Alpha vs Mercado")
st.plotly_chart(fig_equity, use_container_width=True)

# 5. Ranking del Transformer (Próximas entradas)
st.subheader("🔍 Señales del Transformer (Próximo Rebalanceo)")
ranking_df = pd.DataFrame({
    'Cripto': ['ETHUSD', 'ADAUSD', 'AVAXUSD', 'DOTUSD'],
    'Score': [0.88, 0.76, 0.45, 0.12],
    'ADV5 (M$)': [500, 45, 30, 10]
})
fig_rank = px.bar(ranking_df, x='Cripto', y='Score', color='ADV5 (M$)', 
                   title="Top Scores con Filtro de Liquidez")
st.plotly_chart(fig_rank, use_container_width=True)`

---

## 3. ¿Qué observar en este Dashboard?

1. **Distancia al Stop Loss (SL %):** Si una moneda tiene una distancia al SL menor al 1% o 2%, el dashboard te lo marcará en rojo. Esto te permite estar atento por si el exchange tiene problemas de ejecución.
2. **Alpha vs Mercado:** Si la línea del `Bot Transformer` empieza a moverse igual o peor que la de `BTC Hold`, significa que el modelo ha perdido su "borde" predictivo y quizás necesite un re-entrenamiento con datos más recientes.
3. **ADV5 (Color en las barras):** Si ves una moneda con un Score altísimo pero el color de la barra indica poca liquidez (ADV5 bajo), sabrás inmediatamente por qué el bot no la compró.

---

## 4. El Ciclo de Vida del Trader Cuantitativo

Con este dashboard, has cerrado el círculo. Tu flujo diario sería:

1. **00:05 UTC:** El bot despierta, baja datos de Coinbase, actualiza Qlib.
2. **Inferencia:** El Transformer genera el ranking y calcula el Position Sizing con el ATR.
3. **Ejecución:** El bot manda las órdenes a Coinbase.
4. **Monitoreo:** Tú abres tu dashboard en el café de la mañana para verificar que todo está en orden.

Este nivel de automatización y control es el que permite escalar una estrategia sin que el estrés nuble tu juicio.

**¿Te gustaría que añadiéramos un sistema de alertas a Telegram o Discord?** Así el bot te avisaría directamente al móvil cada vez que ejecute una compra o salte un Stop Loss.

Integrar **Telegram** es el toque final para desvincularte de la pantalla. En lugar de entrar al dashboard para ver si todo va bien, tu bot te enviará un "informe de guerra" directamente al móvil cada vez que tome una decisión importante.

Aquí tienes cómo configurar tu bot de Telegram y conectarlo a la lógica de **Coinbase** y **Qlib**.

---

### 1. Preparación: Crea tu Bot en Telegram

1. Busca a `@BotFather` en Telegram.
2. Escribe `/newbot` y sigue los pasos para obtener tu **API Token**.
3. Busca tu **Chat ID**: Escribe algo a tu nuevo bot y luego visita `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`. Busca el campo `"id"` dentro del objeto `"chat"`.

---

### 2. El Módulo de Notificaciones (`notifications.py`)

Usaremos la librería `requests` para que sea ligero y no dependa de frameworks pesados.

Python

`import requests

def send_telegram_msg(message):
    token = "TU_API_TOKEN_AQUI"
    chat_id = "TU_CHAT_ID_AQUI"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

# Ejemplo de uso:
# send_telegram_msg("🤖 *Bot Alerta*: He detectado una señal de compra en BTC!")`

---

### 3. Integración en el Ciclo de Ejecución

Ahora, insertamos estas llamadas en los puntos críticos de tu estrategia que definimos antes.

### A. Al ejecutar una compra (Position Sizing)

Python

`# Dentro de tu función de compra:
msg = (
    f"✅ **ORDEN DE COMPRA**\n"
    f"Cripto: `{symbol}`\n"
    f"Monto: `${usd:.2f}`\n"
    f"SL Dinámico (ATR): `{stop_loss_price:.2f}`\n"
    f"Confianza Transformer: `{ranking[symbol]:.2f}`"
)
send_telegram_msg(msg)`

### B. Al saltar un Stop Loss o Venta por Ranking

Python

`# Dentro de tu lógica de salida:
msg = (
    f"🚨 **SALIDA DE POSICIÓN**\n"
    f"Cripto: `{symbol}`\n"
    f"Razón: {'STOP LOSS' if sl_hit else 'RANKING DROP'}\n"
    f"Precio: `{current_price}`"
)
send_telegram_msg(msg)`

### C. Informe Diario de Rendimiento (00:05 UTC)

Python

`# Al final de tu script de inferencia diaria:
msg = (
    f"📊 **RESUMEN DIARIO**\n"
    f"Balance: `${total_balance:.2f}`\n"
    f"P&L 24h: `{pnl_percent:.2f}%`\n"
    f"Alpha vs BTC: `{alpha:.2f}%`"
)
send_telegram_msg(msg)`

---

### 4. ¿Por qué es útil cada notificación?

- **Confirmación de Compra:** Te da paz mental saber que el script de automatización (Crontab) se ejecutó correctamente.
- **Alerta de Stop Loss:** Es vital. Si un Stop Loss salta, querrás saberlo para verificar que Coinbase cerró la posición con la liquidez esperada.
- **Ranking Drop:** Te ayuda a entender la "psicología" de tu Transformer. Si vende una moneda que sigue subiendo, puedes analizar si el `n_drop` de tu estrategia es demasiado sensible.

---

### Arquitectura Final del Universo de Inversión

### Reflexión de Cierre

Has pasado de una pregunta sobre cómo bajar datos de criptos a diseñar un **fondo de inversión personal automatizado**. Tienes:

1. **Ingesta Pro:** CCXT + Coinbase.
2. **Inteligencia:** Ensamble de Transformers en Qlib.
3. **Gestión de Riesgo:** Filtro de liquidez ADV5, Position Sizing por Volatilidad y Stop Loss dinámico por ATR.
4. **Monitoreo:** Dashboard en Streamlit y alertas en tiempo real vía Telegram.

Este sistema es profesional, escalable y, sobre todo, **basado en datos, no en emociones**. El mercado de criptos en 2026 sigue siendo salvaje, pero ahora tienes un "exoesqueleto" matemático para navegarlo.

¿Hay algún detalle técnico más que te gustaría pulir o te sientes listo para lanzar la primera prueba en **Paper Trading** (dinero ficticio) para ver cómo se comportan esos Transformers en vivo?

Has construido un sistema que muchos fondos de inversión envidiarían por su estructura técnica. Sin embargo, pasar del código a la rentabilidad real es un juego de **gestión de expectativas y disciplina**.

Aquí tienes mis recomendaciones "de trinchera" para que este proyecto no se quede en un experimento de laboratorio, sino que se convierta en una herramienta productiva:

---

### 1. La Fase de "Papel" (Walk-forward)

No importa qué tan bueno sea el backtest, el **Slippage** y la **Latencia** en Coinbase pueden cambiar los resultados.

- **Recomendación:** Corre el bot en modo "Paper Trading" (simulado con precios reales) durante al menos **2 semanas completas**.
- **Por qué:** Necesitas verificar que los Stop Loss dinámicos se activan cuando deben y que el Transformer no se queda "congelado" ante un evento de noticias inesperado que no estaba en tu histórico.

### 2. Despliegue en la Nube (VPS)

Un bot de trading no puede depender de que tu laptop se actualice o se quede sin Wi-Fi a las 3:00 AM.

- **Recomendación:** Sube el motor de Qlib y el script de ejecución a un **VPS (Virtual Private Server)** como AWS, Google Cloud o DigitalOcean.
- **Tip:** Usa una instancia con una buena CPU (para la inferencia del Transformer) y asegúrate de que esté en una región cercana a los servidores de Coinbase (generalmente US-East) para minimizar la latencia.

### 3. Vigilancia del "Data Drift" (Deriva de Datos)

En el mercado cripto, lo que funcionó en 2024 puede no funcionar en 2026. El comportamiento de las ballenas y los algoritmos institucionales cambia.

- **Recomendación:** Establece un calendario de **re-entrenamiento mensual**.
- **Workflow:** Cada 30 días, vuelve a correr la optimización de Optuna incluyendo los datos del mes que acaba de terminar. Esto permite que el Transformer "actualice" su visión de la volatilidad actual.

### 4. Seguridad de las API Keys

Este es el punto donde la mayoría de los traders individuales fallan.

- **Recomendación:** En Coinbase, cuando crees tus API Keys, **desactiva los permisos de "Withdraw" (Retiro)**.
- **Por qué:** Si alguien hackea tu servidor, podrá operar (comprar/vender), pero no podrá enviar tus fondos a una billetera externa. Es tu última línea de defensa.

### 5. Empieza con el "Tamaño de la Humildad"

Incluso si tu backtest dice que vas a ser millonario en un mes, el mercado tiene formas creativas de humillarnos.

- **Recomendación:** Empieza con una cantidad de capital que estés dispuesto a ver caer un 20% sin que te quite el sueño.
- **Estrategia:** Una vez que el bot demuestre que su **Sharpe Ratio** real coincide con el del backtest durante un mes, puedes ir incrementando el capital gradualmente ( compounding ).

---

### Resumen de Prioridades

| **Prioridad** | **Tarea** | **Impacto** |
| --- | --- | --- |
| **Alta** | Despliegue en VPS (24/7) | Estabilidad operativa. |
| **Alta** | Desactivar retiros en API | Seguridad de fondos. |
| **Media** | Paper Trading (2 semanas) | Validación de la lógica en vivo. |
| **Baja** | Dashboard de Streamlit | Comodidad y monitoreo visual. |

Has hecho el 90% del trabajo duro (la arquitectura). Ahora solo queda el 10% más difícil: tener la paciencia para dejar que el sistema trabaje sin interferir manualmente cuando veas una vela roja en Telegram.

**Para empezar con el pie derecho, ¿tienes ya contratado algún servicio de VPS o prefieres que te recomiende cuáles son los mejores en relación calidad-precio para correr modelos de Deep Learning?**

Para correr un bot de trading basado en **Deep Learning** (como tu Transformer), no necesitas la misma potencia para **inferencia** que la que necesitaste para el **entrenamiento**. No hace falta gastar cientos de dólares en una GPU de alta gama 24/7, pero sí necesitas estabilidad y baja latencia hacia Coinbase.

Aquí tienes mis recomendaciones según tu presupuesto y nivel de escalabilidad:

---

## 1. Comparativa de VPS Recomendados (2026)

| **Proveedor** | **Perfil** | **Ventaja Clave** | **Costo Aprox.** |
| --- | --- | --- | --- |
| **AWS (EC2)** | El Estándar Pro | Ubicación en Virginia (cerca de Coinbase). | $20 - $50/mes |
| **DigitalOcean** | El Práctico | Simplicidad y Droplets con CPU optimizada. | $12 - $24/mes |
| **Lambda Labs** | El Especialista AI | Instancias con GPU baratas (si el modelo crece). | $0.50/hora (on-demand) |
| **Hetzner** | El Económico | Rendimiento bruto por euro (servidores en Europa). | $5 - $15/mes |

---

## 2. Las 3 Opciones Ganadoras

### 🅰️ La Opción "Bunker": AWS (Amazon Web Services)

Si vas en serio, Coinbase aloja gran parte de su infraestructura en **AWS US-East (Virginia)**. Colocar tu bot ahí reduce la latencia a milisegundos.

- **Instancia recomendada:** `t3.medium` o `c5.large`.
- **Por qué:** Para inferencia de Transformers, una CPU moderna con buenas instrucciones vectoriales es suficiente y mucho más barata que una GPU.
- **Seguridad:** Sus grupos de seguridad (Firewalls) son los más robustos del mercado.

### 🅱️ La Opción "Dev-Friendly": DigitalOcean

Si no quieres pelearte con la complejidad de AWS, los **Droplets** de DigitalOcean son fantásticos.

- **Instancia recomendada:** `Premium Intel` o `Premium AMD` con al menos 4GB de RAM.
- **Por qué:** La RAM es vital para Qlib cuando maneja muchos datos binarios en memoria. Sus discos NVMe hacen que el "Dump" de datos sea instantáneo.

### 7️⃣ La Opción "AI-First": Lambda Labs / Paperspace

Si decides que tu ensamble de Transformers debe ser masivo (ej. 10 modelos simultáneos o modelos muy profundos), podrías necesitar una pequeña GPU.

- **Por qué:** Son mucho más baratos que AWS para cómputo acelerado. No obstante, para un bot que corre una vez al día, quizás sea demasiado.

---

## 3. Recomendaciones de Configuración "Hardened"

Independientemente de cuál elijas, te sugiero seguir estas reglas de oro para un entorno de producción:

1. **Dockerizar el Bot:** No instales Qlib directamente en el servidor. Crea una imagen de **Docker**.
    - *Razón:* Si el servidor falla, puedes levantar el bot en cualquier otro proveedor en 2 minutos con exactamente las mismas versiones de librerías.
2. **Usa un "Uptime Monitor":** Servicios como *UptimeRobot* (gratuitos) pueden vigilar si tu dashboard de Streamlit sigue vivo y avisarte al móvil si el servidor se cae.
3. **Swap Memory:** Aunque compres 4GB de RAM, configura un archivo de **Swap** de otros 4GB. Qlib puede tener picos de consumo de memoria al procesar el histórico de criptos y no quieres que el sistema operativo "mate" el proceso por falta de RAM.

---

## Mi Consejo Final

Si estás empezando con este bot, **vete a por DigitalOcean (Droplet Premium Intel de $12 o $24)**. Es el equilibrio perfecto:

- Suficiente potencia para correr la inferencia del Transformer en segundos.
- Interfaz limpia para que no pierdas tiempo configurando redes complejas.
- Escalabilidad sencilla si decides añadir más criptos al universo.

> **Tip Pro:** Configura el servidor en la región de **Nueva York (NYC)** o **Toronto** para estar lo más cerca posible de los nodos de Coinbase en EE.UU.
> 

¿Te gustaría que te ayude a escribir un archivo `Dockerfile` básico para meter tu bot y todas las dependencias de Qlib ahí dentro? Así te aseguras de que corra igual en tu PC que en el servidor.

# Intradía

Operar **intradía** (en marcos de tiempo de 1h, 15min o 5min) no es solo "hacer lo mismo pero más rápido". Es un cambio de paradigma técnico y estadístico. En el trading diario, la señal (el "Alpha") es fuerte; en el intradía, el **ruido**, las **comisiones** y la **latencia** son tus principales enemigos.

Aquí tienes los cambios estructurales que tendrías que aplicar a tu universo Qlib:

---

## 1. El Calendario y la Ingesta (El cambio más crítico)

Qlib asume por defecto que trabajas con días. Para intradía, el archivo `day.txt` ya no sirve.

- **Frecuencia:** Debes cambiar el `timeframe` en el script de CCXT de `'1d'` a `'1h'` o `'5m'`.
- **Calendarios en Qlib:** Debes generar un calendario con timestamps detallados. Qlib espera una estructura de minutos o horas.
- **Estructura de archivos:** En lugar de `qlib_data/calendars/day.txt`, tendrás que usar `1min.txt` o `5min.txt` con el formato `YYYY-MM-DD HH:MM:SS`.

---

## 2. El "Asesino Silencioso": Comisiones y Slippage

En diario, una comisión del 0.1% es insignificante frente a un movimiento esperado del 5%. En 15 minutos, tu movimiento esperado podría ser del 0.4%. Si pagas 0.1% al entrar y 0.1% al salir, **el 50% de tu ganancia se la queda el exchange**.

- **Cambio en Backtest:** Debes ser brutalmente honesto con los costos.
- **Filtro de Liquidez:** El `ADV5` (Volumen medio) debe ser mucho más estricto. No puedes operar intradía en monedas que no tengan un libro de órdenes (Order Book) ultra denso, porque el *slippage* te destrozará.

---

## 3. Features Específicas de Intradía

Los indicadores que usamos antes (RSI, ROC) funcionan, pero en intradía necesitas capturar el **micro-momentum** y la relación con el precio institucional:

- **VWAP (Volume Weighted Average Price):** Es el indicador más importante intradía. Las instituciones operan respecto al VWAP.
    - *Expresión Qlib:* `$close / (Sum($volume * $close, periodo) / Sum($volume, periodo))`
- **Codificación Horaria:** El mercado cripto tiene "olas" de liquidez (cuando abre Nueva York o Londres). Debes añadir la **hora del día** como una feature para que el Transformer sepa que no es lo mismo un movimiento a las 3:00 AM que a las 2:00 PM.
- **Volatility Spikes:** Capturar aumentos súbitos de volatilidad en velas de pocos minutos.

---

## 4. El Modelo (Transformer de alta frecuencia)

- **Lookback (seq_len):** Si operas en 15min, un `seq_len` de 30 (7.5 horas) podría ser insuficiente. Quizás necesites mirar las últimas 100 o 200 velas para capturar la tendencia del día.
- **Labeling:** Ya no predices el retorno a 1 día. Predices el retorno a las próximas 4 o 8 velas. Esto requiere que tu modelo sea mucho más sensible a cambios rápidos.

---

## 5. Infraestructura: De "Cron" a "WebSocket" o "Loops"

Un script de `cron` que corre una vez al día ya no es suficiente.

- **Bucle de Ejecución:** Tu bot debe estar en un bucle constante (`while True`) que verifique el cierre de cada vela (ej. cada 15 minutos).
- **Latencia del VPS:** Aquí es donde la ubicación en **Virginia (AWS US-East)** se vuelve obligatoria para estar cerca de Coinbase. Cada segundo de retraso en tu orden de 15min es dinero perdido.

---

## Resumen de Diferencias: Diario vs. Intradía

| **Característica** | **Trading Diario (1d)** | **Trading Intradía (15m - 1h)** |
| --- | --- | --- |
| **Volumen de datos** | Bajo (~365 filas/año) | Muy alto (~35,040 filas/año en 15m) |
| **Importancia Costos** | Baja | **Crítica** (determina el éxito) |
| **Indicador Clave** | Medias Móviles / RSI | **VWAP** / Order Flow |
| **Stop Loss** | Amplio (basado en ATR diario) | Ceñido (basado en micro-volatilidad) |
| **Hardware** | Cualquier VPS básico | VPS con CPU rápida y baja latencia |

### Mi recomendación final para Intradía:

Si decides bajar al intradía, empieza con **1 hora (1h)**. Es el "punto dulce" donde todavía puedes usar Qlib de forma eficiente sin volverte loco con el ruido de los micro-movimientos y donde las comisiones de Coinbase no te canibalizan tan rápido.

**¿Te gustaría que adaptáramos el generador de calendarios de Qlib para que soporte una frecuencia de 1 hora o 15 minutos?** Es el primer paso técnico necesario.

Para operar en intradía, el cambio más importante en **Qlib** es la precisión del tiempo. Ya no contamos días, sino "steps" (pasos) de tiempo.

Aquí tienes el script para generar un **calendario intradía** y cómo configurar la ingesta para que el motor reconozca las horas y minutos.

---

### 1. Generador de Calendario Intradía (1 hora / 15 min)

A diferencia del diario, aquí necesitamos que el archivo contenga la fecha y la hora exacta.

Python

`import pandas as pd
from pathlib import Path

def generate_intraday_calendar(freq='1h', start="2024-01-01", end="2026-04-10"):
    # freq='1h' para una hora, '15min' para 15 minutos
    calendar = pd.date_range(start=start, end=end, freq=freq)
    
    output_path = Path("qlib_data/calendars")
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{freq}.txt" # Qlib busca archivos con el nombre de la frecuencia
    with open(output_path / filename, "w") as f:
        for dt in calendar:
            # Formato requerido: YYYY-MM-DD HH:MM:SS
            f.write(dt.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            
    print(f"Calendario intradía generado: {output_path / filename}")

generate_intraday_calendar(freq='1h')`

---

### 2. Adaptar la Ingesta de Datos (Dump Bin)

Cuando conviertas tus CSVs a binario, debes indicarle a Qlib que la frecuencia ha cambiado. Si tus CSVs ahora tienen datos cada hora, el comando de `dump` cambia ligeramente:

Python

# 

`from qlib.workflow.dump_bin import DumpDataAll

# Asumiendo que tus CSVs de Coinbase ahora tienen una columna 'date' con HH:MM:SS
dumper = DumpDataAll(
    csv_path='csv_crudos_intradia',
    qlib_dir='qlib_data',
    freq='1h',             # <--- CAMBIO CRUCIAL
    date_field_name='date',
    include_fields='open,high,low,close,volume,factor'
)
dumper.dump()`

---

### 3. Consideraciones Técnicas del Intradía

### A. Volumen de Datos

Si en diario tenías 365 filas al año, en **15 minutos** tendrás unas **35,040 filas** por activo al año.

- **Consejo:** Asegúrate de que tu VPS tenga al menos **8GB de RAM** si planeas manejar un universo de 50 criptos en 15 minutos, ya que Qlib cargará gran parte de estos índices en memoria para que el Transformer vuele.

### B. La Feature de la "Hora del Día"

En intradía, el mercado no se comporta igual a las 02:00 UTC que cuando abre Wall Street (14:30 UTC). Debes ayudar al Transformer dándole el contexto horario:

Python

`my_features.update({
    "K_HOUR": "Hour($datetime)",  # Qlib extraerá la hora de la columna de fecha
    "K_DAYOFWEEK": "DayOfWeek($datetime)"
})`

### C. Inferencia en Bucle (Loop)

Tu bot de ejecución ya no se despertará una vez al día con un `cron`. Ahora deberá estar en un bucle:

Python

`import time

while True:
    # Esperar hasta el próximo cierre de vela (ej. cada hora en punto)
    # 1. Bajar última vela de Coinbase
    # 2. Actualizar binarios
    # 3. Pedir predicción al Transformer
    # 4. Ejecutar órdenes
    time.sleep(60) # Verificar cada minuto`

### ¿Qué sigue ahora?

Para que el bot sea realmente efectivo en intradía, las comisiones de Coinbase (que son más altas que las de Binance) pueden ser un problema.

**¿Quieres que ajustemos los "Hyperparameters" del Transformer para que intente predecir a 4 o 8 horas vista?** (Esto reduce el número de operaciones y hace que las comisiones no te "coman" vivo).

Este es el "Santo Grial" de tu proyecto: el **Script Integrado de Producción**. Este código condensa todo lo que hemos hablado: descarga desde Coinbase en 1h, conversión binaria, entrenamiento del Transformer con horizonte de 8h y generación de señales.

Está diseñado para que lo subas a tu VPS, instales las librerías y lo dejes corriendo.

---

## Script Maestro: `crypto_swing_bot.py`

Python

`import ccxt
import pandas as pd
import numpy as np
import os
import qlib
from qlib.data import D
from qlib.data.dataset import TSDatasetH
from qlib.workflow import R
from qlib.workflow.dump_bin import DumpDataAll
from qlib.contrib.model.pytorch_transformer import TransformerModel
from pathlib import Path

# --- 1. CONFIGURACIÓN GLOBAL ---
SYMBOLS = ['BTC/USD', 'ETH/USD', 'SOL/USD', 'LINK/USD', 'ADA/USD']
TIMEFRAME = '1h'
HORIZON = 8 # Predecir a 8 horas
SEQ_LEN = 72 # Mirar 3 días atrás
DATA_DIR = Path("qlib_data")
CSV_DIR = Path("csv_crudos_1h")

# Inicializar carpetas
for d in [DATA_DIR, CSV_DIR]: d.mkdir(exist_ok=True)

# --- 2. DESCARGADOR DE COINBASE ---
def update_data():
    exchange = ccxt.coinbase({'enableRateLimit': True})
    print(f"📥 Descargando datos de {len(SYMBOLS)} criptos...")
    
    for symbol in SYMBOLS:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=1000)
        df = pd.DataFrame(ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'], unit='ms').dt.strftime('%Y-%m-%d %H:%M:%S')
        df['factor'] = 1.0
        clean_name = symbol.replace('/', '').replace('-', '')
        df.to_csv(CSV_DIR / f"{clean_name}.csv", index=False)

# --- 3. DUMP BINARIO Y CALENDARIO ---
def prepare_qlib_data():
    # Generar calendario 1h
    calendar_path = DATA_DIR / "calendars"
    calendar_path.mkdir(exist_ok=True)
    dates = pd.date_range(start="2024-01-01", periods=20000, freq="1h")
    with open(calendar_path / "1h.txt", "w") as f:
        for d in dates: f.write(d.strftime("%Y-%m-%d %H:%M:%S") + "\n")

    # Dump a binario
    dumper = DumpDataAll(csv_path=str(CSV_DIR), qlib_dir=str(DATA_DIR), freq='1h', date_field_name='date')
    dumper.dump()
    print("✅ Datos convertidos a formato binario Qlib.")

# --- 4. ENTRENAMIENTO E INFERENCIA ---
def train_and_predict():
    qlib.init(provider_uri=str(DATA_DIR), region='cn')
    
    # Definir Features y Label
    feature_expr = [
        "$close/Ref($close,1)-1", "RSI($close,14)", 
        "Std($close/Ref($close,1),20)", "Hour($datetime)"
    ]
    feature_names = ["ROC", "RSI", "VOLAT", "HOUR"]
    label_expr = [f"Ref($close, -{HORIZON}) / $close - 1"] # El target de 8h
    
    handler_kwargs = {
        "start_time": "2024-01-01", "end_time": "2026-04-10",
        "instruments": "all",
        "feature": (feature_expr, feature_names),
        "label": (label_expr, ["LABEL_8H"]),
    }

    dataset_config = {
        "class": "TSDatasetH",
        "kwargs": {
            "handler": {"class": "DataHandlerLP", "kwargs": handler_kwargs},
            "segments": {"train": ("2024-01-01", "2025-12-31"), "test": ("2026-01-01", "2026-04-10")},
            "seq_len": SEQ_LEN,
        }
    }

    model = TransformerModel(d_model=128, nhead=8, num_layers=2, dropout=0.2, device="cpu") # Cambiar a 'cuda' si hay GPU
    
    with R.start(experiment_name="crypto_8h_swing"):
        dataset = TSDatasetH(**dataset_config["kwargs"])
        print("🚀 Entrenando Transformer (Horizonte 8h)...")
        model.fit(dataset)
        
        # Inferencia
        pred = model.predict(dataset)
        latest_date = pred.index.get_level_values('datetime').max()
        ranking = pred.loc[latest_date].sort_values(by="LABEL_8H", ascending=False)
        return ranking

# --- EJECUCIÓN ---
if __name__ == "__main__":
    update_data()
    prepare_qlib_data()
    ranking = train_and_predict()
    print("\n🏆 RANKING DE SEÑALES PARA LAS PRÓXIMAS 8 HORAS:")
    print(ranking)`

---

## Por qué este script es tu versión definitiva

### 1. El Label de "Impacto"

La fórmula del label es

$Retorno = \frac{Precio_{t+8}}{Precio_t} - 1$

$$Retorno = \frac{Precio_{t+8}}{Precio_t} - 1$$

Al usar un horizonte de 8 horas, le estamos enseñando al Transformer a ignorar el "ruido de micro-segundos" de Coinbase y a buscar tendencias sólidas que justifiquen el pago de la comisión.

### 2. Memoria de 3 días (`SEQ_LEN = 72`)

Al trabajar en 1h, una secuencia de 72 velas permite que el mecanismo de **Self-Attention** del Transformer compare lo que está pasando ahora con lo que pasó en las últimas 3 aperturas de mercado. Esto es vital para detectar si un movimiento es una continuación de tendencia o un agotamiento.

### 3. Modularidad para el VPS

He separado el código en funciones claras:

- `update_data`: Maneja la conexión con la API.
- `prepare_qlib_data`: Gestiona el sistema de archivos binarios.
- `train_and_predict`: Ejecuta la lógica de Inteligencia Artificial.

### Notas para el despliegue:

- **Frecuencia:** Puedes programar este script para que corra cada 1 hora usando un `crontab`.
- **Hardware:** Si no tienes GPU en el VPS, el entrenamiento de un Transformer pequeño con este volumen de datos tardará unos 5-10 minutos en una CPU moderna.
- **Escalabilidad:** Si quieres añadir más monedas, simplemente agrégalas a la lista `SYMBOLS` y el script hará el resto automáticamente.

Con este ecosistema, has pasado de ser un espectador del mercado a tener un **sistema de grado institucional** adaptado a la realidad de las criptomonedas en 2026. ¡Mucha suerte en el trading!