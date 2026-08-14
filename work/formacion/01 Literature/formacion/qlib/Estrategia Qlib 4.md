# Estrategia Qlib 4

# Lista de las 158 features de Alpha158 y tipos de features:

Sí — esto es justo lo que necesitas entender bien si estás usando `Alpha158`, porque ahí está gran parte del “edge” (o del ruido 😄).
`Alpha158` en Qlib es un conjunto de **features técnicas generadas automáticamente** a partir de OHLCV, organizadas en varias familias. No están documentadas como lista plana en la doc oficial, pero sí en el código del handler.
Te las agrupo por tipo (como realmente están estructuradas):
**🧠 1. Price-based features (precios básicos)
📊 Raw / normalizados**
• `close`
• `open`
• `high`
• `low`
• `vwap`
Normalizados típicamente como:
• `close / close.shift(1) - 1`
• ratios tipo `close / open`, `high / low`, etc.
👉 Capturan estructura básica de precios.
**📈 2. Returns (retornos)
🔁 Retornos en distintas ventanas**
• `RET_1`
• `RET_2`
• `RET_3`
• `RET_5`
• `RET_10`
• `RET_20`
• `RET_30`
• `RET_60`
👉 Forma típica:

`close / close.shift(n) - 1`

👉 Son el núcleo de casi todos los modelos.
**📉 3. Moving averages (tendencia)
📊 Medias móviles**
• `MA_5`
• `MA_10`
• `MA_20`
• `MA_30`
• `MA_60`
**📊 Relativas al precio**
• `close / MA_n - 1`
👉 Capturan tendencia / mean reversion.
**📊 4. Volatility (volatilidad)
📉 Desviación estándar de retornos**
• `STD_5`
• `STD_10`
• `STD_20`
• `STD_30`
• `STD_60`
👉 Miden riesgo / inestabilidad.
**📦 5. Volume-based features
🔊 Volumen**
• `volume`
• `MA(volume, n)`
• `volume / MA(volume, n)`
**💰 Dollar volume**
• `close * volume`
• medias móviles de eso
👉 Importante para liquidez + microestructura.
**⚖️ 6. Price range / intraday structure
📊 Rangos**
• `(high - low) / close`
• `(close - open) / open`
**📊 Posición dentro del rango**
• `(close - low) / (high - low)`
👉 Capturan comportamiento intradía.
**🔄 7. Momentum / reversal
📈 Momentum**
• rolling sums de returns
• diferencias de MA
Ejemplos:
• `MA_5 - MA_20`
• `RET_5 - RET_20`
👉 Señales de tendencia vs reversión.
**🧮 8. Rolling rank / percentile
📊 Ranking temporal**
• rank del precio en ventana
• rank del volumen
• rank de retornos
👉 Muy importante en modelos cross-sectional.
**📐 9. Correlation features
🔗 Correlaciones rolling**
• `corr(close, volume, n)`
• `corr(return, volume, n)`
👉 Señales tipo:
• price-volume relationship
• accumulation/distribution
**🔁 10. Autocorrelation / lag structure
📊 Dependencia temporal**
• correlación de retornos con lags
• persistencia de tendencia
**📉 11. Max / Min / Quantiles
📊 Estadísticos rolling**
• `max(close, n)`
• `min(close, n)`
• posición relativa en ventana
👉 Ejemplo:

`(close - min_n) / (max_n - min_n)`

**🧩 12. Derived combinations**
Aquí está lo potente:
• combinaciones de:
    ◦ returns
    ◦ volumen
    ◦ volatilidad
    ◦ ratios
Ejemplo típico:
• `(RET_5 / STD_20)`
• `(volume / MA(volume, 20)) * RET_5`
👉 Estas features son las más “alpha-like”.
**📦 Resumen mental (muy útil)**
Piensa Alpha158 como:

`OHLCV
↓
+ ventanas (5, 10, 20, 30, 60)
↓
+ operadores:
    - mean
    - std
    - rank
    - corr
    - delta
↓
+ ratios / normalizaciones`

**🧠 Qué es realmente Alpha158**
No son 158 features “handcrafted” tipo fórmula cerrada.
Es más bien:
👉 **un generador sistemático de features técnicas estándar**
Muy similar a:
• feature engineering clásico en quant
• pero empaquetado y consistente
**⚠️ Cosas importantes (muy importantes)
1. No todas las features aportan señal**
Muchas son:
• redundantes
• altamente correlacionadas
👉 LightGBM suele encargarse de esto bien.
**2. Escala importa**
Alpha158 funciona mejor con:
• normalización cross-sectional
• z-score por día
**3. Overfitting**
158 features → fácil sobreajustar si:
• dataset pequeño
• horizon corto
**4. Falta contexto fundamental**
Alpha158 es:
• puramente técnico
👉 No incluye:
• fundamentales
• news
• macro
**🚀 Si quieres mejorar Alpha158**
Te recomendaría añadir:
**🔹 Liquidity features**
• ADV
• bid/ask spread (si tienes)
**🔹 Risk features**
• beta vs SPY
• sector exposure
**🔹 Cross-sectional features**
• rank dentro del universo
• percentile
**🧩 Si quieres verlo exacto**
Puedo:
• sacarte la **lista completa exacta de las 158 features**
• o darte el código que las genera
• o ayudarte a reducirlas a las 20–30 más útiles
Solo dime 👍

Te voy a ser directo:
👉 darte la lista **exacta, completa y fiable de las 158 features** de `Alpha158` **de memoria no es seguro**, porque:
• se generan **programáticamente en el código**
• dependen de plantillas + ventanas + operadores
• cambian ligeramente entre versiones de Qlib
Si te doy una lista “a mano”, es muy fácil que:
• falten features
• haya nombres incorrectos
• o no coincidan exactamente con tu versión
**✅ La forma correcta (y 100% exacta)**
La mejor manera es **extraerlas directamente desde tu entorno Qlib**.
Te dejo el snippet exacto 👇
**🔧 Script para listar las 158 features reales**

`import qlib
from qlib.contrib.data.handler import Alpha158

qlib.init(provider_uri="~/.qlib/qlib_data/us_data")

handler = Alpha158(
    instruments="sp500",
    start_time="2020-01-01",
    end_time="2020-12-31",
)

features = handler.get_cols()

print(len(features))  # debería ser 158
for f in features:
    print(f)`

**🧾 Qué vas a ver**
Te devolverá algo tipo:

`$close
$open
$high
$low
$volume
$close_1
$close_2
...
$roc_5
$roc_10
...
$ma_5
$ma_10
...
$std_5
...
$rank_5
...
$corr_5
...`

👉 Esa es la lista **real, exacta y consistente con tu versión**.
**🧠 Por qué es así (importante)**
Alpha158 no está definido como:

`features = [f1, f2, f3, ... f158]`

Sino como algo tipo:

`for window in [5, 10, 20, 30, 60]:
    generate:
        - returns
        - mean
        - std
        - rank
        - corr
        ...`

👉 Es un **generador de features**, no una lista fija escrita a mano.
**⚠️ Detalle importante**
Dependiendo de:
• versión de Qlib
• parámetros del handler
• features habilitadas
👉 puedes tener:
• 158 exactas
• o alguna variación (raro, pero posible)
****

**🚀 Si quieres ir un paso más allá**

Puedo ayudarte a:

**1. Reducir las 158 → top 20–30 features**
(usando feature importance real)

**2. Agruparlas automáticamente por tipo**
(tendencia, volatilidad, volumen…)

**3. Visualizar correlaciones y redundancia**
(esto es MUY útil)

**4. Crear un Alpha158 “mejorado”**
(con liquidez + filtros reales)
****

**💡 Recomendación clave**
👉 No uses Alpha158 “tal cual” en producción sin:
• filtrar features redundantes
• validar estabilidad
• añadir liquidez

Si quieres, en el siguiente paso te saco:
👉 **las 158 features ya clasificadas automáticamente en grupos reales desde tu entorno** (mucho más útil que solo listarlas).