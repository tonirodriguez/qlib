import qlib
from qlib.constant import REG_US
from qlib.data import D

qlib.init(provider_uri="~/.qlib/qlib_data/us_data", region=REG_US)

# 1) stock pool “all” (si existe) — o ajusta al que tengas disponible
pool_cfg = D.instruments(market="all")
tickers = D.list_instruments(pool_cfg, as_list=True)[:5]

print("Sample tickers:", tickers)

df = D.features(
    tickers,
    fields=["$open", "$close", "$high", "$low", "$volume"],
    freq="day"
)
print(df.head())