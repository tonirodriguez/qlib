"""Genera notebooks/cargar_ohlcv_desde_qlib.ipynb — carga OHLCV de todas las coins desde Qlib y muestra head/tail."""
from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3 (qlib)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
}

md_intro = """# Cargar OHLCV de todas las coins desde Qlib

Este notebook carga la serie de precios (Open/High/Low/Close/Volume) de **todas las coins** del universo crypto directamente desde el dataset **Qlib** (no desde CSV), usando `qlib.data.D.features()`.

- **Datos:** `data/qlib` (formato binario Qlib `.bin`)
- **Universo:** `data/qlib/instruments/crypto.txt`
- **Campo por defecto muestra:** OHLCV (`$open`, `$high`, `$low`, `$close`, `$volume`)

> Requiere el kernel Python del venv `qlib-venv` (donde está instalado `qlib`)."""

md_init = """## 1. Inicializar Qlib

Inicializamos Qlib contra el dataset `data/qlib` (mismo provider y región que usa `qlib_sfm_pipeline.v8.py`)."""

code_init = """from pathlib import Path

import qlib
from qlib.config import REG_US
from qlib.data import D

# --- Resuelve el repo raíz (/opt/data/qlib) aunque el notebook se abra
# desde el kernel en otra carpeta (p.ej. nbconvert, Jupyter Lab en otro dir)
PROJECT_ROOT = Path.cwd()
# Sube directorios si no estamos en la raíz del repo (presencia de data/qlib)
for _ in range(5):
    if (PROJECT_ROOT / "data" / "qlib" / "instruments").is_dir():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent

PROVIDER_URI = PROJECT_ROOT / "data" / "qlib"   # mismo provider/región que el pipeline SFM v8
FIELDS = ["$open", "$high", "$low", "$close", "$volume"]

qlib.init(provider_uri=str(PROVIDER_URI), region=REG_US, kernels=1)
print("Qlib inicializado OK →", PROVIDER_URI)"""

md_universe = """## 2. Universo de coins

Leemos el universo declarado desde `instruments/crypto.txt` (cada línea: `simbolo\\tfecha_inicio\\tfecha_fin`)."""

code_universe = """instruments_path = PROJECT_ROOT / "data" / "qlib" / "instruments" / "crypto.txt"
coins = []
for line in instruments_path.read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        coins.append(line.split("\\t")[0])

print(f"{len(coins)} coins en el universo:")
print("  " + ", ".join(sorted(coins)))"""

md_load = """## 3. Cargar cada coin en pandas y mostrar head/tail

Para **cada coin** cargamos su tabla OHLCV desde Qlib con `D.features()` y mostramos:
- **head(3)** → primeras 3 filas **reales** (desde la fecha de lanzamiento de la coin, no desde ceros de padding)
- **tail(3)** → últimas 3 filas
- rango de fechas, nº de filas y precio de apertura/cierre

> Nota: el dataset Qlib rellena con `0.0` los días previos al lanzamiento de cada coin (antes de su primera fecha en `crypto.txt`). Para que el `head` sea útil, cargamos cada coin desde su propia fecha de inicio."""

code_loop = """# Fecha real de inicio de cada coin (desde crypto.txt): simbolo, inicio, fin
start_by_coin = {}
for line in instruments_path.read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        parts = line.split("\\t")
        start_by_coin[parts[0]] = parts[1]

dataframes = {}

for coin in sorted(coins):
    start = start_by_coin[coin]
    df = D.features([coin], FIELDS, start_time=start, end_time="2026-12-31")
    # Suelta el nivel extra del MultiIndex por si solo hay un instrumento
    df = df.droplevel("instrument", axis=0) if "instrument" in df.index.names else df
    dataframes[coin] = df

    print("=" * 68)
    print(f"  {coin.upper()}")
    print("=" * 68)
    print(f"  Filas: {len(df)}  |  Rango: {df.index[0].date()} → {df.index[-1].date()}")
    display(df.head(3))
    print("  " + "·" * 60 + "  …")
    display(df.tail(3))
    print()

print(f"✅ Cargadas {len(dataframes)} coins en el dict `dataframes`.")"""

md_double = """## 4. (Opcional) Doble comprobación: head/tail de las 9 en una sola tabla

Si prefieres ver todas las coins de un vistazo, las cargamos desde su fecha de inicio real, concatenamos en un solo DataFrame (índice `instrument`/`datetime`) y mostramos `head(2)` y `tail(2)` combinados."""

code_double = """import pandas as pd

# Cargamos cada coin desde su fecha real de inicio (así no hay ceros de padding) y concatenamos
frames = [dataframes[c].copy() for c in coins]
for c, df in zip(coins, frames):
    df.index = pd.MultiIndex.from_product([[c.upper()], df.index], names=["instrument", "datetime"])
all_feats = pd.concat(frames)

print("SHAPE TOTAL:", all_feats.shape)
print("\\n── HEAD (primeros 2 días de cada coin) ──")
print(all_feats.groupby(level="instrument").head(2))
print("\\n── TAIL (últimos 2 días de cada coin) ──")
print(all_feats.groupby(level="instrument").tail(2))"""

cells = [
    nbf.v4.new_markdown_cell(md_intro),
    nbf.v4.new_markdown_cell(md_init),
    nbf.v4.new_code_cell(code_init),
    nbf.v4.new_markdown_cell(md_universe),
    nbf.v4.new_code_cell(code_universe),
    nbf.v4.new_markdown_cell(md_load),
    nbf.v4.new_code_cell(code_loop),
    nbf.v4.new_markdown_cell(md_double),
    nbf.v4.new_code_cell(code_double),
]
nb.cells = cells

out = Path("/opt/data/qlib/work/crypto/notebooks/cargar_ohlcv_desde_qlib.ipynb")
out.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, out)
print("Notebook creado:", out)