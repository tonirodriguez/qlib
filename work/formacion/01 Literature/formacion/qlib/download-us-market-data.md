# Descargar dataset US para Qlib

> Guía práctica para obtener datos del mercado estadounidense (NYSE/NASDAQ) en formato Qlib.

---

## Requisitos

- Python 3.8+ con Qlib instalado
- Conexión a internet
- Espacio en disco: ~3 GB para el dataset US completo

---

## Método 1: `get_data.py` (rápido, recomendado)

El script oficial de Qlib descarga un zip pre-empaquetado desde GitHub Releases.

```bash
# Activar entorno Qlib (si usas venv)
# source .venv/bin/activate

pip install fire

python vendor/microsoft-qlib/scripts/get_data.py qlib_data \
    --target_dir ~/.qlib/qlib_data/us_data \
    --region us \
    --interval 1d
```

**Flags útiles:**

| Flag | Descripción |
|------|-------------|
| `--region us` | Dataset US (NYSE/NASDAQ). Omitir para CN. |
| `--interval 1d` | Datos diarios. También disponible `1min`. |
| `--delete_old false` | No borrar datos existentes (por defecto true). |
| `--exists_skip true` | Saltar si ya existe (no descarga de nuevo). |

### Qué descarga

El zip contiene:

```
~/.qlib/qlib_data/us_data/
├── calendars/
│   └── day.txt          ← lista de fechas con datos (formato YYYYMMDD)
├── features/
│   ├── aapl/
│   │   ├── adjclose.day.bin
│   │   ├── close.day.bin
│   │   ├── high.day.bin
│   │   ├── low.day.bin
│   │   ├── open.day.bin
│   │   ├── volume.day.bin
│   │   ├── change.day.bin
│   │   ├── dividends.day.bin
│   │   ├── factor.day.bin
│   │   └── splits.day.bin
│   ├── msft/
│   ├── goog/
│   └── ... (~5000+ tickers)
└── instruments/
    ├── all.txt           ← ~8000 tickers con fechas de validez
    ├── sp500.txt         ← miembros S&P 500
    └── nasdaq100.txt     ← miembros NASDAQ-100
```

**Formato de `instruments/sp500.txt`:**
```
MMM	1999-01-01	2099-12-31
AOS	2017-07-26	2099-12-31
ABT	1999-01-01	2099-12-31
...
```

### Solución de problemas

**Error: `does not contain data for day`**

Causa más probable: falta `calendars/day.txt`. Qlib lo necesita para saber qué fechas están disponibles.

```bash
# Verificar si existe
ls ~/.qlib/qlib_data/us_data/calendars/

# Si no existe, regenerarlo desde los features:
python -c "
from pathlib import Path
import numpy as np
from qlib.data.storage.file_storage import FileFeatureStorage

data_dir = str(Path.home() / '.qlib/qlib_data/us_data')
cal_dir = Path(data_dir) / 'calendars'
cal_dir.mkdir(exist_ok=True)

# Leer el índice de un feature cualquiera para obtener el rango
fs = FileFeatureStorage('spy', 'adjclose', 'day', 
    provider_uri={'__DEFAULT_FREQ': data_dir})
start = fs.start_index
end = fs.end_index
print(f'Range: {start} to {end}')
# Las fechas se almacenan como un calendario independiente
# Si no hay calendar, Qlib no puede resolver índices a fechas
"
```

O simplemente **re-descargar** con `--delete_old true`:

```bash
python vendor/microsoft-qlib/scripts/get_data.py qlib_data \
    --target_dir ~/.qlib/qlib_data/us_data \
    --region us --interval 1d --delete_old true
```

---

## Método 2: Yahoo Collector (más control)

Útil si quieres controlar qué tickers descargar o necesitas datos más recientes que el zip pre-empaquetado.

```bash
# 1. Instalar dependencias
pip install -r vendor/microsoft-qlib/scripts/data_collector/yahoo/requirements.txt

# 2. Descargar raw data desde Yahoo Finance
python vendor/microsoft-qlib/scripts/data_collector/yahoo/collector.py download_data \
    --source_dir ~/.qlib/stock_data/source/us_data \
    --start 2000-01-01 \
    --end 2026-06-01 \
    --delay 0.5 \
    --interval 1d \
    --region US \
    --max_workers_skip 4

# 3. Convertir raw data a formato Qlib (normalize + dump_bin)
python vendor/microsoft-qlib/scripts/data_collector/yahoo/collector.py normalize_data \
    --source_dir ~/.qlib/stock_data/source/us_data \
    --normalize_dir ~/.qlib/stock_data/normalize/us_data \
    --region US \
    --interval 1d

# 4. Generar dataset Qlib final
python scripts/data_collector/yahoo/collector.py dump_bin \
    --normalize_dir ~/.qlib/stock_data/normalize/us_data \
    --qlib_dir ~/.qlib/qlib_data/us_data \
    --freq day \
    --exclude_fields_factor
```

**Ventajas:**
- Datos más actualizados (hasta ayer en vez de hasta la última release)
- Control granular sobre tickers y rango de fechas
- Actualizable incrementalmente

**Desventajas:**
- Mucho más lento (rate limiting de Yahoo)
- Dependencias adicionales
- Floración de `delay` para no ser baneado

---

## Método 3: Descarga directa del zip (para CI/scripts)

Si solo necesitas los datos para un pipeline headless:

```bash
# Usando curl / wget
VERSION="v2"
FILE="qlib_data_us_1d_latest.zip"
URL="https://github.com/SunsetWolf/qlib_dataset/releases/download/${VERSION}/${FILE}"

curl -L -o /tmp/us_data.zip "$URL"
unzip -o /tmp/us_data.zip -d ~/.qlib/qlib_data/us_data
rm /tmp/us_data.zip
```

---

## Verificar que los datos son válidos

```bash
python scripts/run_baseline_workflow.py \
    --config config/workflow_baseline_lightgbm_alpha158_sp500_us.yaml \
    --mode prepare
```

Si ves:

```
[INFO] - qlib successfully initialized
[INFO] - Dataset validation passed
```

→ los datos están listos. Si ves errores como `does not contain data for day`, falta el calendario (ver solución arriba).

---

## Estructura esperada (comprobado)

| Componente | CN data | US data |
|-----------|---------|---------|
| Tickers | ~8000 CSI | ~5000+ NYSE/NASDAQ |
| Calendario | `calendars/day.txt` | `calendars/day.txt` (obligatorio) |
| Features | 10 fields .bin | 10 fields .bin |
| Instrumentos | CSI índices | S&P 500, NASDAQ-100, all |
| Tamaño | ~1.5 GB | ~3 GB |

---

## Referencias

- [Qlib official US data download](https://qlib.readthedocs.io/en/latest/component/data.html#converting-csv-format-into-qlib-format)
- [Yahoo collector docs](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo)
- [qlib-dataset releases (GitHub)](https://github.com/SunsetWolf/qlib_dataset/releases)

---

> **Siguiente paso:** Una vez descargados los datos, ejecuta `--mode prepare` para validar y `--mode train` para el primer experimento US. Ver `experiments-quickstart.md`.
