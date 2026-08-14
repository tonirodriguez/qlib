import qlib
from qlib.constant import REG_US
from qlib.data import D
import pandas as pd

qlib.init(provider_uri="~/.qlib/qlib_data/us_data", region=REG_US)

pool_cfg = D.instruments("all")
tickers = D.list_instruments(pool_cfg, as_list=True)[:30]  # 30 para que sea rápido

# Cargar close
close = D.features(tickers, ["$close"], freq="day")
close = close["$close"].unstack(level=0)  # columnas = tickers

# Señal momentum 20d: return 20d
mom20 = close.pct_change(20)

# Señal: top 5 long, bottom 5 short (dólar-neutral)
signal = mom20.apply(lambda s: s.rank(pct=True), axis=1)
long = (signal >= 0.9).astype(int)
short = (signal <= 0.1).astype(int) * -1
position = long + short

print("✅ Señal generada. Ejemplo posiciones:")
print(position.tail())