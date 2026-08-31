import qlib
from qlib.config import REG_US
from qlib.data import D

qlib.init(provider_uri="data/qlib_crypto", region=REG_US)
df = D.features(["btc"], ["$close"])
print(f"BTC: {len(df)} filas")
print(f"Index type: {type(df.index)}")
print(f"Index names: {df.index.names}")
print(f"Primeras fechas: {df.index.get_level_values('datetime')[:3].tolist()}")
print(f"Ultimas fechas: {df.index.get_level_values('datetime')[-3:].tolist()}")
print(f"Rango: {df.index.get_level_values('datetime').min()} -> {df.index.get_level_values('datetime').max()}")