# Estrategia Qlib 2

## Definir coste por transacción 0.35 € en fichero YAML

En **Qlib**, el coste de transacción se define dentro de la configuración del *backtest executor* o del *exchange*. Por defecto suele estar pensado como **ratio (porcentaje)**, pero puedes adaptarlo a un coste fijo como 0,35 € por operación.

### 🔧 Opción 1 — Usar `open_cost` / `close_cost` (aproximación porcentual)

Qlib espera normalmente costes proporcionales:

```python
exchange_kwargs = {
    "open_cost": 0.001,   # 0.1%
    "close_cost": 0.001,
    "min_cost": 0,
}
```

👉 Problema: esto no es fijo, sino proporcional al volumen.

---

### ✅ Opción 2 — Coste fijo por operación (lo que buscas)

Para un coste fijo como **0,35 € por trade**, tienes que usar `min_cost`:

```python
exchange_kwargs = {
    "open_cost": 0,       # sin coste proporcional
    "close_cost": 0,
    "min_cost": 0.35,     # coste mínimo por transacción
}
```

✔️ Así cada operación tendrá al menos 0,35€, que en la práctica actúa como coste fijo si no hay coste proporcional.

---

### ⚠️ Importante (detalle clave)

- `min_cost` se aplica **por orden (buy/sell)**
- Si haces compra + venta → pagarás **0,35 + 0,35 = 0,70 €** por round-trip

---

### 🧠 Si quieres EXACTAMENTE 0,35€ por round-trip

Entonces tienes dos opciones:

### A) Dividirlo:

```python
"min_cost": 0.175
```

### B) Customizar el exchange (más preciso)

Crear tu propia clase heredando de `Exchange` y sobrescribir el cálculo de costes.

---

### 📦 Ejemplo completo en backtest

```python
backtest_config = {
    "exchange_kwargs": {
        "freq": "day",
        "limit_threshold": 0.095,
        "deal_price": "close",
        "open_cost": 0,
        "close_cost": 0,
        "min_cost": 0.35,
    }
}
```

---

Si quieres, puedo ayudarte a:

- implementar un **coste fijo real por orden (sin hacks)**
- o ajustar el coste según broker real (IBKR, DeGiro, etc.) 👍

## Actualización diaria de los datos

En **Qlib**, no hay una única “mejor” forma universal, pero en la práctica hay **3 enfoques** y uno es claramente el recomendado para datos tipo `us_data`.

---

# ✅ ✅ Mejor opción (recomendada)

### 👉 Usar el script oficial de actualización incremental

Qlib incluye herramientas para **actualizar solo los datos nuevos** sin rehacer todo el dataset.

### 🔧 Flujo típico

```bash
python scripts/data_collector/yahoo/collector.py update_data \
    --region us \
    --start_date 2020-01-01 \
    --end_date 2026-04-07 \
    --interval 1d \
    --target_dir ~/.qlib/qlib_data/us_data
```

✔️ Ventajas:

- Solo descarga datos nuevos (incremental)
- Mantiene formato compatible con Qlib
- No rompe features existentes
- Es lo más cercano a “producción”

---

# ⚠️ Alternativa común (pero peor)

### 👉 Re-descargar todo el dataset

```bash
python scripts/get_data.py qlib_data --target_dir ~/.qlib/qlib_data/us_data --region us
```

❌ Problemas:

- Lento
- Sobrescribe todo
- No escalable para uso diario

---

# 🧠 Opción avanzada (mejor si vas en serio)

### 👉 Pipeline propio + dump incremental

Si ya estás en un entorno más serio:

1. Descargas datos diarios (Yahoo, Polygon, etc.)
2. Los conviertes a formato Qlib
3. Usas:

```python
from qlib.data.dataset import DataHandlerLP
```

o directamente:

```bash
dump_bin.py update
```

✔️ Ventajas:

- Control total
- Integrable con cron / Airflow
- Permite datos alternativos (fundamentales, etc.)

---

# 🔥 Recomendación práctica según uso

| Caso | Mejor opción |
| --- | --- |
| Experimentos / local | Script `collector.py update_data` |
| Uso diario automatizado | Script + cron |
| Producción / trading real | Pipeline propio + dump incremental |

---

# ⚠️ Detalles importantes (que suelen romper cosas)

- Asegúrate de mantener:
    - mismo `freq` (`1d`)
    - misma estructura de features
- Si cambias esquema → tendrás que regenerar dataset
- Yahoo a veces falla → considera retries o proveedor alternativo

---

# 🧩 Bonus (automatizar diario)

Ejemplo con cron:

```bash
0 22 * * 1-5 python update_qlib_data.py
```

---

Si quieres, dime cómo estás usando Qlib (research vs trading) y te digo **la arquitectura óptima exacta**, porque cambia bastante según el caso.

lo estoy usando para hacer research y esta research aplicarla a trading real

Sí: para **research que luego quieres llevar a trading real**, yo no usaría la misma solución “tal cual” en ambas capas.

## Recomendación práctica

La mejor arquitectura en tu caso es:

**1. Research en Qlib offline**

Mantén `us_data` en binario local y actualízalo **a diario de forma incremental** con el *Yahoo collector*. El propio repositorio de Qlib indica que el dataset listo para usar **no se actualiza regularmente**, y que si quieres datos recientes debes descargarlos tú; además, para actualización incremental recomienda usar el collector de Yahoo “from scratch” en vez de confiar en el paquete estático. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

**2. Preproducción / paper trading con Qlib online mode o Qlib-Server**

Si vas a ejecutar señales cada día y quieres una capa más estable para servir datos a varios procesos, Qlib soporta **Online mode** y existe **Qlib-Server** para centralizar datos, caché y actualización. Eso encaja mejor cuando pasas de notebooks a procesos diarios automatizados. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/advanced/server.rst?utm_source=chatgpt.com))

**3. Trading real: separar research engine de execution engine**

Usa Qlib para **investigación, generación de features, entrenamiento, scoring y backtests**, pero para ejecución real es mejor tener una capa aparte para:

- datos del broker / market data oficial,
- validación de órdenes,
- control de riesgo,
- slippage real,
- reconciliación de fills.

La razón es simple: el flujo de datos de Yahoo es útil para research, pero no es la base ideal para una ejecución real robusta. Además, el propio ecosistema de Qlib orienta el “online serving” a usar los datos más recientes y operar en condiciones de mercado, no a convertir Yahoo sin más en infraestructura de ejecución. ([qlib-xiaoge.readthedocs.io](https://qlib-xiaoge.readthedocs.io/en/latest/component/online.html?utm_source=chatgpt.com))

## Entonces, ¿qué haría yo exactamente?

### Fase 1: ahora mismo

Para tu `us_data`, usaría **actualización diaria incremental** con el collector de Yahoo y después regeneraría solo lo necesario para scoring diario. Qlib mantiene clases específicas para US en el collector de Yahoo (`YahooCollectorUS`, `YahooCollectorUS1d`), así que ese camino sigue siendo el oficial dentro del proyecto. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/collector.py?utm_source=chatgpt.com))

### Fase 2: cuando ya tengas estrategia estable

Montaría un proceso diario así:

1. **Descarga incremental** de datos US
2. **Validación** de huecos / símbolos fallidos
3. **Refresh de dataset/features**
4. **Predicción diaria**
5. **Generación de órdenes objetivo**
6. **Paper trading**
7. **Sólo después**, conexión a broker real

Eso te deja usar Qlib como motor cuantitativo sin acoplarlo demasiado a la ejecución.

## Mi recomendación clara

Para tu caso, la **mejor opción** es:

**Yahoo collector incremental para research + Qlib-Server/online mode para operación diaria + capa de ejecución separada para real trading.** ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

## Lo que no te recomiendo

No basaría todo el paso a real trading en:

- `scripts/get_data.py qlib_data` descargando el dataset entero cada vez, porque ese dataset preparado no se actualiza regularmente. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))
- una arquitectura donde Yahoo sea la fuente final de verdad para ejecución real, porque su collector está pensado para ingestión/research y ha tenido incidencias reportadas en el tiempo. ([GitHub](https://github.com/microsoft/qlib/issues/1981?utm_source=chatgpt.com))

## Regla simple

- **Si todavía estás afinando modelos:** Yahoo incremental + Qlib offline
- **Si ya ejecutas todos los días:** Qlib-Server / online mode
- **Si ya vas a meter dinero real:** broker/exchange data + execution layer separada

Si quieres, en el siguiente mensaje te dejo una **arquitectura concreta de carpetas, jobs diarios y comandos** para montar ese flujo con Qlib paso a paso.

Si

Perfecto. Para tu caso, montaría esto:

## Arquitectura recomendada

### 1) `research_data` separado de `live_data`

No mezcles el dataset con el que investigas meses o años de histórico con el que usas para generar señal diaria.

- **`research_data`**: histórico amplio, estable, reproducible
- **`live_data`**: copia operativa que actualizas cada día

Qlib deja claro que el `qlib_data` “ready-made” no se actualiza regularmente, y que **si quieres actualización incremental tienes que construir el dataset desde cero con el Yahoo collector y luego ir actualizándolo**. ([GitHub](https://github.com/microsoft/qlib?utm_source=chatgpt.com))

---

### 2) Flujo diario

Yo lo dejaría así:

**22:00–23:00 CET**

1. actualizar datos US
2. validar que no haya símbolos rotos o huecos
3. recalcular features necesarias
4. ejecutar scoring del modelo
5. generar pesos / órdenes objetivo
6. exportar órdenes a tu capa de ejecución

---

## Estructura de carpetas

```bash
~/qlib_workspace/
├── data/
│   ├── research_us/
│   │   ├── qlib_bin/
│   │   └── raw_yahoo/
│   └── live_us/
│       ├── qlib_bin/
│       └── raw_yahoo/
├── models/
│   ├── model_v1/
│   ├── model_v2/
│   └── registry.json
├── signals/
│   ├── predictions/
│   ├── target_positions/
│   └── orders/
├── logs/
├── scripts/
│   ├── update_us_data.sh
│   ├── validate_data.py
│   ├── run_inference.py
│   └── build_orders.py
└── configs/
    ├── qlib_research.yaml
    └── qlib_live.yaml
```

---

## Cómo lo montaría en Qlib

### A. Construcción inicial del dataset

Primero haz una **descarga completa** con el Yahoo collector, no con el dataset prehecho. El README del collector lo indica explícitamente para poder luego actualizar incrementalmente. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

### B. Actualización diaria incremental

Usa el collector de Yahoo para US. En el código siguen existiendo las clases específicas `YahooCollectorUS` y `YahooCollectorUS1d`, así que ese camino sigue siendo el soportado en el repo. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/collector.py?utm_source=chatgpt.com))

Un flujo tipo sería:

```bash
python scripts/data_collector/yahoo/collector.py update_data \
  --region us \
  --interval 1d \
  --target_dir ~/qlib_workspace/data/live_us/qlib_bin
```

Puede variar algo según la versión exacta de Qlib que tengas instalada, pero la idea correcta es esa: **actualización incremental sobre un dataset que tú mismo construiste con el collector**. El dataset preempaquetado no está pensado para eso. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

---

## Configuración recomendada por fase

### Fase 1: research reproducible

Usa siempre una foto congelada del dataset.

Ejemplo:

- entrenas con datos hasta `2025-12-31`
- validas y backtesteas sobre esa foto
- guardas:
    - commit del código
    - versión del modelo
    - fecha de corte de datos

Así, cuando algo cambie en Yahoo o en el universo de símbolos, tu research no se mueve.

---

### Fase 2: scoring diario

Aquí sí usas `live_us`.

Tu proceso diario sería:

1. `update_data`
2. cargar el modelo ya entrenado
3. generar predicciones del día
4. transformar score → pesos objetivo
5. aplicar filtros de ejecución

---

## Qué capa usar para “operación diaria”

### Opción simple

Si solo vas a correr **un proceso diario en una máquina**, puedes seguir en modo offline local.

### Opción mejor

Si vas a tener varios procesos, varios modelos, o quieres una capa más limpia, usa **Qlib-Server / online mode**. La documentación oficial dice que sirve para:

- centralizar datos,
- compartir caché,
- facilitar actualización de datos,
- y ejecutar Qlib en online mode. ([GitHub](https://github.com/microsoft/qlib-server/blob/main/docs/server.rst?utm_source=chatgpt.com))

Mi criterio sería:

- **1 máquina, 1 estrategia, research serio pero simple** → offline local
- **varios jobs diarios / varios modelos / varios consumidores** → Qlib-Server

---

## Lo que sí separaría para trading real

No dejaría a Qlib enviar órdenes directamente como única capa.

Haría esta separación:

### Qlib

- datos históricos
- features
- entrenamiento
- scoring
- backtest
- portfolio target

### Execution layer propia

- lectura de posiciones reales del broker
- comparación target vs actual
- cálculo de órdenes
- filtros de liquidez
- control de riesgo
- límites por símbolo
- horarios de mercado
- confirmación de fills
- reconciliación

Eso te evita acoplar demasiado la ejecución real al stack de research.

---

## Pipeline concreto que te recomiendo

### Job 1 — update

```bash
#!/bin/bash
set -e

python scripts/data_collector/yahoo/collector.py update_data \
  --region us \
  --interval 1d \
  --target_dir ~/qlib_workspace/data/live_us/qlib_bin
```

### Job 2 — validación

Comprueba al menos:

- que el último día existe para SPY / AAPL / MSFT / QQQ
- que no hay columnas clave vacías
- que no ha caído de golpe el número de símbolos

### Job 3 — inferencia

```bash
python ~/qlib_workspace/scripts/run_inference.py \
  --config ~/qlib_workspace/configs/qlib_live.yaml \
  --model ~/qlib_workspace/models/model_v2
```

### Job 4 — órdenes

```bash
python ~/qlib_workspace/scripts/build_orders.py \
  --predictions ~/qlib_workspace/signals/predictions/latest.parquet \
  --positions broker_positions.json \
  --cash 100000
```

---

## Reglas operativas que usaría

### Para research

- rebalance diario o semanal
- costes realistas
- slippage conservador
- universo estable

### Para real

- no operar todo el universo
- limitar a top N señales
- mínimo ADV / volumen
- tamaño máximo por nombre
- buffer de rebalance para no sobreoperar

---

## Riesgos que vigilaría con `us_data` de Yahoo

Esto es importante. Aunque el collector sigue siendo el camino oficial para construir y actualizar `us_data`, también ha habido incidencias recientes reportadas sobre el Yahoo collector y cambios en fuentes auxiliares para US. Hubo un fix para US data en 2025 y también issues por fallos del collector. ([GitHub](https://github.com/microsoft/qlib/pull/1954/files?utm_source=chatgpt.com))

Traducción práctica:

**para research sí; para ejecución real, no lo trataría como fuente definitiva de verdad.**

---

## Mi recomendación final, sin complicarte de más

Para empezar bien:

### Stack mínimo bueno

- **Qlib offline local**
- dataset US construido con Yahoo collector
- actualización incremental diaria
- modelo congelado por versión
- script separado de generación de órdenes
- ejecución real fuera de Qlib

### Cuándo pasar a Qlib-Server

- cuando tengas más de una estrategia,
- más de un proceso,
- o quieras servir los datos a varios jobs de forma centralizada. ([GitHub](https://github.com/microsoft/qlib-server/blob/main/docs/server.rst?utm_source=chatgpt.com))

---

## Qué haría yo en tu sitio hoy

1. crear `research_us` y `live_us`
2. reconstruir ambos desde collector Yahoo
3. entrenar siempre sobre `research_us`
4. actualizar cada noche `live_us`
5. generar señal diaria desde `live_us`
6. pasar target weights a un ejecutor propio

Si quieres, en el siguiente mensaje te dejo ya un **ejemplo real de `update_us_data.sh` + `validate_data.py` + `qlib_live.yaml`** listo para adaptar.

Adelante

Perfecto. Te dejo una versión **mínima pero seria** para montar el flujo.

La idea es esta:

- **`research_us`** = dataset congelado para entrenar y backtestear
- **`live_us`** = dataset que actualizas cada día para inferencia
- Qlib recomienda esto de forma implícita: el `qlib_data` “ready-made” no se actualiza regularmente, y para actualización incremental debes construir/actualizar con el **Yahoo collector**. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

---

## 1) `update_us_data.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

QLIB_DIR="${HOME}/qlib_workspace"
LIVE_DIR="${QLIB_DIR}/data/live_us/qlib_bin"
LOG_DIR="${QLIB_DIR}/logs"
mkdir -p "${LOG_DIR}"

TODAY=$(date +%F)
LOG_FILE="${LOG_DIR}/update_us_data_${TODAY}.log"

echo "[INFO] Updating Qlib US data at $(date)" | tee -a "${LOG_FILE}"

cd "${QLIB_DIR}"

python scripts/data_collector/yahoo/collector.py update_data \
  --region us \
  --interval 1d \
  --target_dir "${LIVE_DIR}" \
  2>&1 | tee -a "${LOG_FILE}"

echo "[INFO] Update finished at $(date)" | tee -a "${LOG_FILE}"
```

### Notas

- Este script asume que estás ejecutándolo **desde un clon del repo de Qlib**, porque `collector.py` vive ahí.
- En el código del collector siguen existiendo las clases `YahooCollectorUS` y `YahooCollectorUS1d`, así que ese camino sigue vigente para US daily data. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/collector.py?utm_source=chatgpt.com))
- El README del collector también deja claro que el dataset preparado no se actualiza regularmente. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

---

## 2) `validate_data.py`

Esto te evita lanzar inferencia sobre un dataset roto.

```python
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

REQUIRED_SYMBOLS = ["AAPL", "MSFT", "SPY", "QQQ"]

def load_calendar(calendars_dir: Path) -> pd.Timestamp:
    day_file = calendars_dir / "day.txt"
    if not day_file.exists():
        raise FileNotFoundError(f"Calendar file not found: {day_file}")

    cal = pd.read_csv(day_file, header=None)
    if cal.empty:
        raise ValueError("Calendar file is empty")

    last_date = pd.to_datetime(cal.iloc[-1, 0]).normalize()
    return last_date

def load_features_last_date(features_dir: Path, symbol: str) -> pd.Timestamp:
    symbol_lower = symbol.lower()
    candidates = list(features_dir.glob(f"{symbol_lower}.*.bin")) + list(features_dir.glob(f"{symbol}.*.bin"))
    if not candidates:
        raise FileNotFoundError(f"No feature bins found for {symbol} in {features_dir}")

    # Validación mínima: si existen bins del símbolo, asumimos que el dump llegó.
    # Para una validación más profunda puedes abrir los bins con Qlib.
    return pd.Timestamp.utcnow().normalize()

def check_instruments(instruments_dir: Path) -> None:
    if not instruments_dir.exists():
        raise FileNotFoundError(f"Instruments dir not found: {instruments_dir}")

    files = list(instruments_dir.glob("*.txt"))
    if not files:
        raise ValueError("No instrument files found")

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python validate_data.py /path/to/qlib_bin")
        return 2

    qlib_bin = Path(sys.argv[1]).expanduser().resolve()
    calendars_dir = qlib_bin / "calendars"
    features_dir = qlib_bin / "features"
    instruments_dir = qlib_bin / "instruments"

    try:
        last_calendar_date = load_calendar(calendars_dir)
        check_instruments(instruments_dir)

        print(f"[OK] Last trading date in calendar: {last_calendar_date.date()}")
        print(f"[OK] Instruments present")

        # Validación ligera
        for symbol in REQUIRED_SYMBOLS:
            try:
                load_features_last_date(features_dir, symbol)
                print(f"[OK] Feature files detected for {symbol}")
            except Exception as e:
                print(f"[WARN] {symbol}: {e}")

        return 0

    except Exception as e:
        print(f"[ERROR] Validation failed: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

### Qué comprobaría además

Yo añadiría luego estas 3 validaciones:

- que la **última fecha de calendario** sea la esperada,
- que sigan existiendo **instrumentos base**,
- que no haya una caída rara en el número de símbolos.

---

## 3) `qlib_live.yaml`

Un ejemplo sencillo para inferencia diaria.

```yaml
provider_uri: "~/.qlib_workspace/data/live_us/qlib_bin"
region: "us"

market: &market "sp500"
benchmark: &benchmark "^gspc"

data_handler_config:
  start_time: "2022-01-01"
  end_time: "2099-12-31"
  fit_start_time: "2022-01-01"
  fit_end_time: "2024-12-31"
  instruments: *market

task:
  model:
    class: LGBModel
    module_path: qlib.contrib.model.gbdt
    kwargs:
      loss: mse
      colsample_bytree: 0.8879
      learning_rate: 0.0421
      subsample: 0.8789
      lambda_l1: 205.6999
      lambda_l2: 580.9768
      max_depth: 8
      num_leaves: 210
      num_threads: 8

  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: Alpha158
        module_path: qlib.contrib.data.handler
        kwargs:
          start_time: "2022-01-01"
          end_time: "2099-12-31"
          fit_start_time: "2022-01-01"
          fit_end_time: "2024-12-31"
          instruments: *market

      segments:
        train: ["2022-01-01", "2024-12-31"]
        valid: ["2025-01-01", "2025-06-30"]
        test: ["2025-07-01", "2099-12-31"]

port_analysis_config:
  strategy:
    class: TopkDropoutStrategy
    module_path: qlib.contrib.strategy.signal_strategy
    kwargs:
      topk: 30
      n_drop: 5

  backtest:
    start_time: "2025-07-01"
    end_time: "2099-12-31"
    account: 100000
    benchmark: *benchmark
    exchange_kwargs:
      freq: day
      deal_price: close
      open_cost: 0
      close_cost: 0
      min_cost: 0.35
      limit_threshold: 0.095
```

### Importante con tu coste fijo

Si quieres modelar **0,35 € por transacción**, esta configuración con:

```yaml
open_cost: 0
close_cost: 0
min_cost: 0.35
```

es la forma práctica de hacerlo en Qlib.

---

## 4) `run_inference.py`

Ejemplo básico para cargar config, inicializar Qlib y generar predicciones.

```python
from __future__ import annotations

import argparse
from pathlib import Path
import yaml
import pandas as pd
import qlib
from qlib.utils import init_instance_by_config

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to qlib yaml config")
    parser.add_argument("--model-dir", required=True, help="Path to saved model artifacts")
    parser.add_argument("--output", required=True, help="Output parquet for predictions")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    model_dir = Path(args.model_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    provider_uri = str(Path(cfg["provider_uri"]).expanduser().resolve())
    region = cfg["region"]

    qlib.init(provider_uri=provider_uri, region=region)

    dataset = init_instance_by_config(cfg["task"]["dataset"])
    model = init_instance_by_config(cfg["task"]["model"])

    # Aquí asumo que tienes un método propio para cargar el modelo ya entrenado.
    # Adáptalo según cómo serialices tus artefactos.
    if hasattr(model, "load"):
        model.load(str(model_dir))

    preds = model.predict(dataset)
    if not isinstance(preds, pd.Series):
        preds = pd.Series(preds)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    preds.to_frame("score").to_parquet(output_path)

    print(f"[OK] Predictions saved to {output_path}")

if __name__ == "__main__":
    main()
```

---

## 5) `build_orders.py`

Convierte score a pesos objetivo de forma simple.

```python
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--topk", type=int, default=20)
    args = parser.parse_args()

    pred_path = Path(args.predictions).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()

    df = pd.read_parquet(pred_path).reset_index()

    # Espera columnas tipo: instrument, datetime, score
    latest_dt = df["datetime"].max()
    latest = df[df["datetime"] == latest_dt].copy()

    latest = latest.sort_values("score", ascending=False).head(args.topk).copy()
    latest["target_weight"] = 1.0 / len(latest)

    orders = latest[["datetime", "instrument", "score", "target_weight"]]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    orders.to_csv(out_path, index=False)

    print(f"[OK] Orders saved to {out_path}")

if __name__ == "__main__":
    main()
```

---

## 6) pipeline diario completo

Yo lo dejaría así:

```bash
#!/usr/bin/env bash
set -euo pipefail

QLIB_DIR="${HOME}/qlib_workspace"
LIVE_DIR="${QLIB_DIR}/data/live_us/qlib_bin"

bash "${QLIB_DIR}/scripts/update_us_data.sh"

python "${QLIB_DIR}/scripts/validate_data.py" "${LIVE_DIR}"

python "${QLIB_DIR}/scripts/run_inference.py" \
  --config "${QLIB_DIR}/configs/qlib_live.yaml" \
  --model-dir "${QLIB_DIR}/models/model_v2" \
  --output "${QLIB_DIR}/signals/predictions/latest.parquet"

python "${QLIB_DIR}/scripts/build_orders.py" \
  --predictions "${QLIB_DIR}/signals/predictions/latest.parquet" \
  --output "${QLIB_DIR}/signals/orders/orders_latest.csv" \
  --topk 20
```

---

## 7) cron diario

Por ejemplo, después del cierre US:

```bash
15 23 * * 1-5 /home/toni/qlib_workspace/scripts/daily_pipeline.sh >> /home/toni/qlib_workspace/logs/cron.log 2>&1
```

---

## 8) cuándo meter Qlib-Server

No lo necesitas el día 1.

Sí lo metería cuando tengas:

- varios modelos,
- varios procesos diarios,
- varios clientes/consumidores,
- o quieras centralizar datos y caché.

Ese es justo el caso de uso que describe la documentación de Qlib-Server y online mode: centralizar gestión de datos, compartir caché y acceso remoto. ([GitHub](https://github.com/microsoft/qlib-server/blob/main/README.md?utm_source=chatgpt.com))

---

## 9) advertencia importante con Yahoo

Para research está bien, pero yo pondría vigilancia porque:

- el propio collector ha tenido incidencias reportadas,
- y hubo fixes recientes para US data. ([GitHub](https://github.com/microsoft/qlib/issues/1981?utm_source=chatgpt.com))

Traducción práctica:

- **research / scoring diario**: sí
- **fuente definitiva para ejecución real**: mejor no

---

## 10) mi recomendación final para ti

Qué haría yo ya:

- entrenar sobre `research_us`
- inferir cada día con `live_us`
- guardar predicciones en parquet
- convertir a `target_weight`
- ejecutar órdenes desde una capa separada del broker

Así separas bien:

- **Qlib = research + señal**
- **ejecutor = órdenes reales**

En el siguiente paso te puedo dejar una versión más aterrizada de `run_inference.py` para tu caso concreto:

**LightGBM + Alpha158 + topk strategy**, ya con carga de modelo entrenado y export limpio de señales.

Adelante

Sí. Para **LightGBM + Alpha158 + scoring diario**, la forma más limpia en Qlib suele ser:

1. entrenar y guardar el modelo con el **workflow/recorder** (`R.save_objects(trained_model=model)`),
2. en inferencia cargar ese modelo con `recorder.load_object("trained_model")`,
3. reconstruir el `DatasetH` apuntando a tu `live_us`,
4. hacer `model.predict(dataset)`.

Ese patrón aparece en el ejemplo oficial `workflow_by_code.ipynb`, y Qlib también documenta `SignalRecord` como la pieza para generar predicciones dentro del workflow. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/workflow_by_code.ipynb?utm_source=chatgpt.com))

Te dejo una versión ya aterrizada para tu caso.

## `run_inference_lgb_alpha158.py`

```python
from __future__ import annotations

import argparse
from pathlib import Path
import yaml
import pandas as pd
import qlib

from qlib.utils import init_instance_by_config
from qlib.workflow import R

def load_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def init_qlib(cfg: dict) -> None:
    provider_uri = str(Path(cfg["provider_uri"]).expanduser().resolve())
    region = cfg["region"]
    qlib.init(provider_uri=provider_uri, region=region)

def build_dataset(cfg: dict):
    return init_instance_by_config(cfg["task"]["dataset"])

def load_trained_model(experiment_name: str, recorder_id: str):
    recorder = R.get_recorder(experiment_name=experiment_name, recorder_id=recorder_id)
    model = recorder.load_object("trained_model")
    return model

def normalize_pred_to_frame(pred) -> pd.DataFrame:
    if isinstance(pred, pd.Series):
        df = pred.to_frame("score")
    elif isinstance(pred, pd.DataFrame):
        if "score" not in pred.columns:
            if pred.shape[1] == 1:
                df = pred.copy()
                df.columns = ["score"]
            else:
                raise ValueError("Prediction DataFrame has multiple columns and none is named 'score'")
        else:
            df = pred.copy()
    else:
        raise TypeError(f"Unsupported prediction type: {type(pred)}")

    if not isinstance(df.index, pd.MultiIndex) or len(df.index.names) < 2:
        raise ValueError("Expected MultiIndex index like (datetime, instrument) or (instrument, datetime)")

    # Normalizar nombres del índice
    names = list(df.index.names)
    if "datetime" not in names or "instrument" not in names:
        # Intento razonable: renombrar las dos primeras dimensiones
        df.index = df.index.set_names(["datetime", "instrument"][: len(names)])
        names = list(df.index.names)

    # Reordenar a (datetime, instrument) si hiciera falta
    if names[0] != "datetime":
        df = df.reorder_levels(["datetime", "instrument"]).sort_index()

    return df.sort_index()

def export_latest_scores(pred_df: pd.DataFrame, parquet_path: Path, csv_path: Path | None, topk: int | None) -> None:
    latest_dt = pred_df.index.get_level_values("datetime").max()
    latest = pred_df.xs(latest_dt, level="datetime").reset_index()
    latest.insert(0, "datetime", latest_dt)
    latest = latest.sort_values("score", ascending=False)

    if topk is not None:
        latest = latest.head(topk).copy()

    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    latest.to_parquet(parquet_path, index=False)

    if csv_path is not None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        latest.to_csv(csv_path, index=False)

    print(f"[OK] Latest scoring date: {pd.Timestamp(latest_dt).date()}")
    print(f"[OK] Saved parquet: {parquet_path}")
    if csv_path is not None:
        print(f"[OK] Saved csv: {csv_path}")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to qlib_live.yaml")
    parser.add_argument("--experiment-name", required=True, help="Qlib experiment name where the model was saved")
    parser.add_argument("--recorder-id", required=True, help="Recorder id of the trained model")
    parser.add_argument("--output-parquet", required=True, help="Output parquet for latest daily scores")
    parser.add_argument("--output-csv", default=None, help="Optional csv export for latest daily scores")
    parser.add_argument("--topk", type=int, default=None, help="Optional top-k export")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    output_parquet = Path(args.output_parquet).expanduser().resolve()
    output_csv = Path(args.output_csv).expanduser().resolve() if args.output_csv else None

    cfg = load_config(config_path)
    init_qlib(cfg)

    dataset = build_dataset(cfg)
    model = load_trained_model(args.experiment_name, args.recorder_id)

    pred = model.predict(dataset)
    pred_df = normalize_pred_to_frame(pred)

    export_latest_scores(
        pred_df=pred_df,
        parquet_path=output_parquet,
        csv_path=output_csv,
        topk=args.topk,
    )

if __name__ == "__main__":
    main()
```

## Cómo lo usaría yo

```bash
python run_inference_lgb_alpha158.py \
  --config ~/qlib_workspace/configs/qlib_live.yaml \
  --experiment-name train_model \
  --recorder-id TU_RECORDER_ID \
  --output-parquet ~/qlib_workspace/signals/predictions/latest_scores.parquet \
  --output-csv ~/qlib_workspace/signals/predictions/latest_scores.csv \
  --topk 50
```

En el ejemplo oficial por código, Qlib guarda el modelo como `trained_model` dentro del recorder y luego lo recupera con `recorder.load_object("trained_model")`; además, ese mismo ejemplo usa `model.predict(...)` y `SignalRecord` para generar y almacenar predicciones. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/workflow_by_code.ipynb?utm_source=chatgpt.com))

## `qlib_live.yaml` ajustado para esto

```yaml
provider_uri: "~/qlib_workspace/data/live_us/qlib_bin"
region: us

market: &market sp500
benchmark: &benchmark ^gspc

data_handler_config: &data_handler_config
  start_time: "2022-01-01"
  end_time: "2099-12-31"
  fit_start_time: "2022-01-01"
  fit_end_time: "2024-12-31"
  instruments: *market

task:
  model:
    class: LGBModel
    module_path: qlib.contrib.model.gbdt
    kwargs:
      loss: mse
      colsample_bytree: 0.8879
      learning_rate: 0.0421
      subsample: 0.8789
      lambda_l1: 205.6999
      lambda_l2: 580.9768
      max_depth: 8
      num_leaves: 210
      num_threads: 8

  dataset:
    class: DatasetH
    module_path: qlib.data.dataset
    kwargs:
      handler:
        class: Alpha158
        module_path: qlib.contrib.data.handler
        kwargs: *data_handler_config
      segments:
        train: ["2022-01-01", "2024-12-31"]
        valid: ["2025-01-01", "2025-06-30"]
        test: ["2025-07-01", "2099-12-31"]
```

Qlib documenta `DatasetH` como la capa que prepara datos para entrenamiento e inferencia, y los ejemplos oficiales de benchmark para LightGBM + Alpha158 usan precisamente esa combinación de `LGBModel` + `DatasetH` + `Alpha158`. ([qlib.readthedocs.io](https://qlib.readthedocs.io/en/latest/component/data.html?utm_source=chatgpt.com))

## Si prefieres no pasar `recorder_id` a mano

Puedes guardar el `recorder_id` en un fichero al terminar el entrenamiento:

```python
from pathlib import Path
from qlib.workflow import R

with R.start(experiment_name="train_model"):
    model.fit(dataset)
    R.save_objects(trained_model=model)
    rid = R.get_recorder().id

Path("~/qlib_workspace/models/model_v2/recorder_id.txt").expanduser().write_text(rid, encoding="utf-8")
print(rid)
```

Esto encaja con el flujo oficial de Qlib basado en `R.start(...)`, `R.save_objects(...)` y posterior recuperación desde el recorder. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/workflow_by_code.ipynb?utm_source=chatgpt.com))

## Siguiente paso lógico: convertir score en pesos

Después de generar `latest_scores.parquet`, haría esto:

- ordenar por `score`,
- quedarme con `topk`,
- aplicar filtros de liquidez,
- convertir a `target_weight`,
- pasar eso a tu ejecutor.

Qlib incluye `TopkDropoutStrategy` para ese tipo de lógica de cartera, y su documentación describe exactamente ese enfoque top-k/drop para construir posiciones objetivo. ([qlib.readthedocs.io](https://qlib.readthedocs.io/en/latest/component/strategy.html?utm_source=chatgpt.com))

Te dejo también una versión mínima de `build_target_weights.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--topk", type=int, default=20)
    parser.add_argument("--max-weight", type=float, default=0.10)
    args = parser.parse_args()

    scores_path = Path(args.scores).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    df = pd.read_parquet(scores_path)
    df = df.sort_values("score", ascending=False).head(args.topk).copy()

    raw_w = 1.0 / len(df)
    capped_w = min(raw_w, args.max_weight)
    df["target_weight"] = capped_w

    total = df["target_weight"].sum()
    df["target_weight"] = df["target_weight"] / total

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df[["datetime", "instrument", "score", "target_weight"]].to_csv(output_path, index=False)

    print(f"[OK] Saved target weights to {output_path}")

if __name__ == "__main__":
    main()
```

Y el pipeline quedaría:

```bash
python run_inference_lgb_alpha158.py \
  --config ~/qlib_workspace/configs/qlib_live.yaml \
  --experiment-name train_model \
  --recorder-id $(cat ~/qlib_workspace/models/model_v2/recorder_id.txt) \
  --output-parquet ~/qlib_workspace/signals/predictions/latest_scores.parquet \
  --output-csv ~/qlib_workspace/signals/predictions/latest_scores.csv \
  --topk 100

python build_target_weights.py \
  --scores ~/qlib_workspace/signals/predictions/latest_scores.parquet \
  --output ~/qlib_workspace/signals/orders/target_weights.csv \
  --topk 20 \
  --max-weight 0.10
```

El punto delicado aquí no es Qlib sino **cómo guardaste el modelo al entrenar**. Si lo guardaste con `R.save_objects(trained_model=model)`, este script te encaja casi directo. Si lo guardaste como pickle/manual, habría que cambiar solo la parte de `load_trained_model()`. ([GitHub](https://github.com/microsoft/qlib/blob/main/examples/workflow_by_code.ipynb?utm_source=chatgpt.com))

Puedo dejarte ahora la pieza que falta: un `train_lgb_alpha158.py` simétrico a este, para que entrenamiento e inferencia queden cerrados y compatibles.

## Carga de los datos desde el día 1 del presente mes de forma incremental

Sí: en Qlib lo haría con **`update_data_to_bin`**, porque es el flujo que el propio repo documenta para **actualización incremental** sobre un dataset que **ya construiste tú desde Yahoo desde cero**. Qlib también aclara que **no** puedes hacer actualización incremental fiable partiendo del `us_data` offline/preempaquetado de Qlib. ([GitHub](https://github.com/microsoft/qlib))

Para cargar **desde el día 1 del mes actual**, la idea es:

- `trading_date` = **primer día del mes**
- `end_date` = **mañana** o la fecha límite que quieras, porque Qlib documenta `end_date` como **no incluida** en el rango. ([GitHub](https://github.com/microsoft/qlib))

Con la fecha de hoy (**7 de abril de 2026**), sería así:

```bash
python scripts/data_collector/yahoo/collector.py update_data_to_bin \
  --qlib_data_1d_dir ~/.qlib/qlib_data/us_data \
  --trading_date 2026-04-01 \
  --end_date 2026-04-08
```

Eso intenta actualizar desde **2026-04-01** hasta **2026-04-07 inclusive**, porque `end_date` no entra en el rango. ([GitHub](https://github.com/microsoft/qlib))

## Cómo lo haría de forma genérica cada mes

### Bash

```bash
FIRST_DAY=$(date +%Y-%m-01)
END_DAY=$(date -d "tomorrow" +%F)

python scripts/data_collector/yahoo/collector.py update_data_to_bin \
  --qlib_data_1d_dir ~/.qlib/qlib_data/us_data \
  --trading_date "$FIRST_DAY" \
  --end_date "$END_DAY"
```

## Cuándo usaría esto

Lo usaría si quieres **reconstruir/asegurar todo el tramo del mes en curso** cada vez que corra el job. Es útil para:

- rellenar días perdidos,
- corregir pequeños fallos del collector,
- evitar depender de “solo ayer”.

## Qué haría yo en producción ligera

Para tu caso, usaría dos modos:

- **diario normal**: actualizar solo desde el último día pendiente;
- **job de reparación**: desde el **día 1 del mes actual**.

Así, por ejemplo:

- cada noche: update corto;
- cada sábado o cada inicio de sesión importante: update desde `YYYY-MM-01`.

## Matiz importante

Esto asume que `~/.qlib/qlib_data/us_data` es un dataset generado con el **Yahoo collector**. Si lo creaste con `scripts/get_data.py qlib_data`, Qlib avisa que ese dataset offline no sirve como base ideal para incremental porque le faltan campos que el flujo incremental necesita. ([GitHub](https://github.com/microsoft/qlib))

## Mi versión recomendada para ti

Yo dejaría un script así:

```bash
#!/usr/bin/env bash
set -euo pipefail

QLIB_DATA_DIR="${HOME}/.qlib/qlib_data/us_data"
FIRST_DAY=$(date +%Y-%m-01)
END_DAY=$(date -d "tomorrow" +%F)

python scripts/data_collector/yahoo/collector.py update_data_to_bin \
  --qlib_data_1d_dir "${QLIB_DATA_DIR}" \
  --trading_date "${FIRST_DAY}" \
  --end_date "${END_DAY}"
```

Y después correría una validación de salud de datos, porque el propio repo también recomienda comprobar la salud del dataset tras actualizar. ([GitHub](https://github.com/microsoft/qlib))

Si quieres, te dejo ahora la versión equivalente en **Python**, para que no dependas de `date` de Linux y puedas integrarlo en tu pipeline de Qlib.

## Carga Diaria

Para la **carga diaria**, yo haría esto:

## La idea buena

Usar `update_data_to_bin` sobre un `us_data` que hayas **construido tú con el Yahoo collector**, no sobre el dataset offline prehecho. Qlib indica explícitamente que el dataset preempaquetado no es una base válida para actualización incremental, y que para actualizar de forma incremental hay que haber creado el dataset desde cero con el collector de Yahoo. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

## Estrategia diaria recomendada

### Opción normal

Cada día, actualizar **desde la última fecha pendiente** hasta hoy.

### Opción robusta

Cada día, actualizar **desde hace 3 a 5 días** hasta hoy para cubrir:

- pequeños fallos de Yahoo,
- huecos,
- correcciones tardías.

Yo, para research con paso a real trading, usaría la segunda.

## Ejemplo diario simple

Como hoy es **7 de abril de 2026**, una ejecución diaria podría ser:

```bash
python scripts/data_collector/yahoo/collector.py update_data_to_bin \
  --qlib_data_1d_dir ~/.qlib/qlib_data/us_data \
  --trading_date 2026-04-06 \
  --end_date 2026-04-08 \
  --region us
```

En Qlib, `end_date` es el límite superior **no incluido**, así que usando `2026-04-08` cubres hasta el **7 de abril de 2026**. Además, el propio repo recomienda hacer una actualización manual inicial y luego dejarla automatizada. ([GitHub](https://github.com/microsoft/qlib?utm_source=chatgpt.com))

## Cómo lo haría yo de verdad

No usaría “solo ayer”. Haría una **ventana deslizante corta**.

### Script diario robusto

```bash
#!/usr/bin/env bash
set -euo pipefail

QLIB_DATA_DIR="${HOME}/.qlib/qlib_data/us_data"
START_DAY=$(date -d "5 days ago" +%F)
END_DAY=$(date -d "tomorrow" +%F)

python scripts/data_collector/yahoo/collector.py update_data_to_bin \
  --qlib_data_1d_dir "${QLIB_DATA_DIR}" \
  --trading_date "${START_DAY}" \
  --end_date "${END_DAY}"
  --region us
```

Eso reescribe/revalida los últimos días y reduce bastante el riesgo de quedarte con un hueco silencioso. Esta recomendación es una inferencia práctica mía basada en que el collector de Yahoo ha tenido incidencias reportadas y en que Yahoo no es una fuente perfecta para producción. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

## La versión “inteligente”

Si quieres hacerlo fino, primero lees la **última fecha disponible** en tu calendario/binarios y luego lanzas el update desde ahí.

### Lógica

1. leer última fecha cargada en `day.txt`
2. restar 3–5 días de margen
3. ejecutar `update_data_to_bin`

### Pseudocódigo Python

```python
from datetime import timedelta
import pandas as pd
from pathlib import Path
import subprocess

qlib_dir = Path.home() / ".qlib/qlib_data/us_data"
day_txt = qlib_dir / "calendars" / "day.txt"

cal = pd.read_csv(day_txt, header=None)
last_dt = pd.to_datetime(cal.iloc[-1, 0]).normalize()

start_dt = (last_dt - timedelta(days=5)).strftime("%Y-%m-%d")
end_dt = (pd.Timestamp.today().normalize() + timedelta(days=1)).strftime("%Y-%m-%d")

subprocess.run([
    "python",
    "scripts/data_collector/yahoo/collector.py",
    "update_data_to_bin",
    "--qlib_data_1d_dir", str(qlib_dir),
    "--trading_date", start_dt,
    "--end_date", end_dt,
    "--region us"
], check=True)
```

## Mi recomendación clara para tu caso

### Para research serio con uso diario

Haz esto cada noche:

- `start = última_fecha - 5 días`
- `end = mañana`

### Para mantenimiento extra

Una vez por semana:

- recarga desde el **día 1 del mes actual**

Así combinas:

- rapidez diaria,
- robustez ante huecos,
- y poca complejidad.

## Pipeline diario que dejaría

```bash
#!/usr/bin/env bash
set -euo pipefail

python update_us_incremental.py
python validate_data.py ~/.qlib/qlib_data/us_data
python run_inference_lgb_alpha158.py ...
python build_target_weights.py ...
```

## Mi versión corta

- **cada día**: ventana deslizante de 5 días
- **cada semana o al inicio de mes**: recarga desde el día 1 del mes
- **siempre**: validación después del update

Eso es lo que haría yo con Qlib para `us_data`.

Puedo dejarte el `update_us_incremental.py` completo, listo para cron, con logging y lectura automática de la última fecha.

Sí. Yo lo haría con un script Python que:

1. lea la **última fecha cargada** del calendario de Qlib,
2. retroceda unos días de margen,
3. lance `update_data_to_bin`,
4. deje logs y código de salida.

Eso encaja con la recomendación de Qlib de usar el **Yahoo collector** para la actualización incremental sobre un dataset que hayas construido tú desde cero, no sobre el `us_data` offline prehecho. Qlib también documenta `update_data_to_bin` como el flujo para actualizar datos diarios y recomienda hacer primero una actualización manual y luego automatizarla. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

### Script: `update_us_incremental.py`

```python
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

def setup_logging(log_file: Path | None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
    )

def read_last_calendar_date(qlib_data_dir: Path) -> pd.Timestamp:
    day_file = qlib_data_dir / "calendars" / "day.txt"
    if not day_file.exists():
        raise FileNotFoundError(f"No existe el calendario: {day_file}")

    cal = pd.read_csv(day_file, header=None)
    if cal.empty:
        raise ValueError(f"El calendario está vacío: {day_file}")

    last_dt = pd.to_datetime(cal.iloc[-1, 0]).normalize()
    return last_dt

def build_update_window(
    last_dt: pd.Timestamp,
    lookback_days: int,
    end_offset_days: int,
) -> tuple[str, str]:
    start_dt = (last_dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    end_dt = (pd.Timestamp.today().normalize() + timedelta(days=end_offset_days)).strftime("%Y-%m-%d")
    return start_dt, end_dt

def run_update(
    qlib_repo_dir: Path,
    qlib_data_dir: Path,
    trading_date: str,
    end_date: str,
    python_bin: str = sys.executable,
) -> int:
    collector = qlib_repo_dir / "scripts" / "data_collector" / "yahoo" / "collector.py"
    if not collector.exists():
        raise FileNotFoundError(f"No encuentro collector.py en: {collector}")

    cmd = [
        python_bin,
        str(collector),
        "update_data_to_bin",
        "--qlib_data_1d_dir",
        str(qlib_data_dir),
        "--trading_date",
        trading_date,
        "--end_date",
        end_date,
    ]

    logging.info("Lanzando comando: %s", " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    return completed.returncode

def main() -> int:
    parser = argparse.ArgumentParser(description="Actualización incremental diaria de us_data en Qlib")
    parser.add_argument(
        "--qlib-data-dir",
        required=True,
        help="Ruta al dataset binario de Qlib, p.ej. ~/.qlib/qlib_data/us_data",
    )
    parser.add_argument(
        "--qlib-repo-dir",
        required=True,
        help="Ruta al repo clonado de Qlib",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=5,
        help="Días de margen hacia atrás para rehacer una ventana reciente",
    )
    parser.add_argument(
        "--end-offset-days",
        type=int,
        default=1,
        help="Desplazamiento del end_date respecto a hoy. 1 = mañana",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Fichero de log opcional",
    )
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Intérprete Python a usar para lanzar collector.py",
    )

    args = parser.parse_args()

    qlib_data_dir = Path(args.qlib_data_dir).expanduser().resolve()
    qlib_repo_dir = Path(args.qlib_repo_dir).expanduser().resolve()
    log_file = Path(args.log_file).expanduser().resolve() if args.log_file else None

    setup_logging(log_file)

    try:
        last_dt = read_last_calendar_date(qlib_data_dir)
        trading_date, end_date = build_update_window(
            last_dt=last_dt,
            lookback_days=args.lookback_days,
            end_offset_days=args.end_offset_days,
        )

        logging.info("Última fecha en calendario: %s", last_dt.date())
        logging.info("Ventana de actualización: [%s, %s)", trading_date, end_date)

        rc = run_update(
            qlib_repo_dir=qlib_repo_dir,
            qlib_data_dir=qlib_data_dir,
            trading_date=trading_date,
            end_date=end_date,
            python_bin=args.python_bin,
        )

        if rc != 0:
            logging.error("collector.py terminó con código %s", rc)
            return rc

        logging.info("Actualización completada correctamente")
        return 0

    except Exception as e:
        logging.exception("Fallo en la actualización: %s", e)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

### Cómo lo usaría

```bash
python update_us_incremental.py \
  --qlib-data-dir ~/.qlib/qlib_data/us_data \
  --qlib-repo-dir ~/src/qlib \
  --lookback-days 5 \
  --log-file ~/qlib_workspace/logs/update_us_incremental.log
```

### Por qué lo haría así

Qlib documenta que la actualización incremental diaria se hace con el collector de Yahoo, y que el dataset offline “ready-made” no sirve como base ideal para eso porque le faltan campos para reducir tamaño. Además, el collector para US daily sigue existiendo en `collector.py` como `YahooCollectorUS1d`. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

### Mi criterio práctico

Para diario usaría:

- `lookback_days=5` en días normales, para rehacer una ventana corta y cubrir huecos.
- `end_offset_days=1`, porque en la documentación de Qlib el `end_date` se trata como límite superior no incluido, así que “mañana” suele cubrir hasta hoy. ([qlib-xiaoge.readthedocs.io](https://qlib-xiaoge.readthedocs.io/en/latest/component/data.html?utm_source=chatgpt.com))

### Cron de ejemplo

```bash
15 23 * * 1-5 /usr/bin/python3 /home/toni/qlib_workspace/scripts/update_us_incremental.py --qlib-data-dir /home/toni/.qlib/qlib_data/us_data --qlib-repo-dir /home/toni/src/qlib --lookback-days 5 --log-file /home/toni/qlib_workspace/logs/update_us_incremental.log
```

### Recomendación extra

Después del update, yo correría siempre una validación mínima del dataset, porque Yahoo no es una fuente perfecta y ha habido incidencias reportadas con el collector. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

Te dejo también una versión que **calcula automáticamente el primer día del mes** y cambia entre modo diario y modo mensual con un flag si quieres.

si

Sí. Yo lo dejaría en un solo script con **dos modos**:

- `daily`: rehace una ventana corta hacia atrás, por ejemplo 5 días.
- `month`: rehace desde el **día 1 del mes actual**.

Eso encaja con lo que Qlib documenta: la actualización incremental debe hacerse con el **Yahoo collector** sobre un dataset que hayas construido tú desde cero, no sobre el `us_data` offline/preempaquetado. Además, Qlib recomienda hacer una actualización manual inicial y luego automatizar la actualización diaria. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

## `update_us_auto.py`

```python
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

def setup_logging(log_file: Path | None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
    )

def read_last_calendar_date(qlib_data_dir: Path) -> pd.Timestamp:
    day_file = qlib_data_dir / "calendars" / "day.txt"
    if not day_file.exists():
        raise FileNotFoundError(f"No existe el calendario: {day_file}")

    cal = pd.read_csv(day_file, header=None)
    if cal.empty:
        raise ValueError(f"El calendario está vacío: {day_file}")

    return pd.to_datetime(cal.iloc[-1, 0]).normalize()

def first_day_of_current_month() -> pd.Timestamp:
    today = pd.Timestamp.today().normalize()
    return today.replace(day=1)

def build_window(
    mode: str,
    last_dt: pd.Timestamp,
    lookback_days: int,
    end_offset_days: int,
) -> tuple[str, str]:
    today = pd.Timestamp.today().normalize()

    if mode == "daily":
        start_dt = last_dt - timedelta(days=lookback_days)
    elif mode == "month":
        start_dt = first_day_of_current_month()
    else:
        raise ValueError(f"Modo no soportado: {mode}")

    end_dt = today + timedelta(days=end_offset_days)

    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

def run_update(
    qlib_repo_dir: Path,
    qlib_data_dir: Path,
    trading_date: str,
    end_date: str,
    python_bin: str,
) -> int:
    collector = qlib_repo_dir / "scripts" / "data_collector" / "yahoo" / "collector.py"
    if not collector.exists():
        raise FileNotFoundError(f"No encuentro collector.py en: {collector}")

    cmd = [
        python_bin,
        str(collector),
        "update_data_to_bin",
        "--qlib_data_1d_dir",
        str(qlib_data_dir),
        "--trading_date",
        trading_date,
        "--end_date",
        end_date,
        "--region us",
    ]

    logging.info("Ejecutando: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode

def main() -> int:
    parser = argparse.ArgumentParser(description="Actualización automática de us_data en Qlib")
    parser.add_argument("--qlib-data-dir", required=True, help="Ruta a ~/.qlib/qlib_data/us_data")
    parser.add_argument("--qlib-repo-dir", required=True, help="Ruta al repo clonado de Qlib")
    parser.add_argument(
        "--mode",
        choices=["daily", "month"],
        default="daily",
        help="daily = ventana deslizante; month = desde el día 1 del mes actual",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=5,
        help="Solo para mode=daily. Días hacia atrás desde la última fecha",
    )
    parser.add_argument(
        "--end-offset-days",
        type=int,
        default=1,
        help="1 = usar mañana como end_date",
    )
    parser.add_argument("--python-bin", default=sys.executable, help="Python para lanzar collector.py")
    parser.add_argument("--log-file", default=None, help="Fichero de log opcional")
    args = parser.parse_args()

    qlib_data_dir = Path(args.qlib_data_dir).expanduser().resolve()
    qlib_repo_dir = Path(args.qlib_repo_dir).expanduser().resolve()
    log_file = Path(args.log_file).expanduser().resolve() if args.log_file else None

    setup_logging(log_file)

    try:
        last_dt = read_last_calendar_date(qlib_data_dir)
        trading_date, end_date = build_window(
            mode=args.mode,
            last_dt=last_dt,
            lookback_days=args.lookback_days,
            end_offset_days=args.end_offset_days,
        )

        logging.info("Última fecha en el calendario: %s", last_dt.date())
        logging.info("Modo: %s", args.mode)
        logging.info("Ventana a actualizar: [%s, %s)", trading_date, end_date)

        rc = run_update(
            qlib_repo_dir=qlib_repo_dir,
            qlib_data_dir=qlib_data_dir,
            trading_date=trading_date,
            end_date=end_date,
            python_bin=args.python_bin,
        )

        if rc != 0:
            logging.error("collector.py terminó con código %s", rc)
            return rc

        logging.info("Actualización finalizada correctamente")
        return 0

    except Exception as e:
        logging.exception("Error en la actualización: %s", e)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

## Cómo lo usaría

### Modo diario

Rehace una pequeña ventana reciente:

```bash
python update_us_auto.py \
  --qlib-data-dir ~/.qlib/qlib_data/us_data \
  --qlib-repo-dir ~/src/qlib \
  --mode daily \
  --lookback-days 5 \
  --log-file ~/qlib_workspace/logs/update_us_daily.log
```

### Modo mensual

Rehace desde el día 1 del mes actual:

```bash
python update_us_auto.py \
  --qlib-data-dir ~/.qlib/qlib_data/us_data \
  --qlib-repo-dir ~/src/qlib \
  --mode month \
  --log-file ~/qlib_workspace/logs/update_us_month.log
```

## Cómo lo programaría

Yo haría esto:

### Cada día laborable

```
15 23 * * 1-5 /usr/bin/python3 /home/toni/qlib_workspace/scripts/update_us_auto.py --qlib-data-dir /home/toni/.qlib/qlib_data/us_data --qlib-repo-dir /home/toni/src/qlib --mode daily --lookback-days 5 --log-file /home/toni/qlib_workspace/logs/update_us_daily.log
```

### Una vez por semana o al inicio de mes

```
30 23 * * 6 /usr/bin/python3 /home/toni/qlib_workspace/scripts/update_us_auto.py --qlib-data-dir /home/toni/.qlib/qlib_data/us_data --qlib-repo-dir /home/toni/src/qlib --mode month --log-file /home/toni/qlib_workspace/logs/update_us_month.log
```

## Por qué lo haría así

Qlib sigue teniendo en `collector.py` las clases específicas para US como `YahooCollectorUS` y `YahooCollectorUS1d`, así que ese flujo sigue siendo el camino soportado para `us_data`. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/collector.py?utm_source=chatgpt.com))

También hay que tener presente que el propio repo advierte que los datos de Yahoo pueden no ser perfectos, y además hay incidencias reportadas recientes sobre el Yahoo collector. Por eso prefiero una ventana diaria con algo de solape y un refresco mensual más amplio. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

Un detalle importante: en la documentación de Qlib para actualización diaria se recomienda hacer una actualización manual inicial y luego automatizar; además, el uso de `end_date` como límite superior no incluido es consistente con el patrón de usar `mañana` para cubrir hasta hoy. ([Qlib Documentation](https://qlib-xiaoge.readthedocs.io/en/latest/component/data.html?utm_source=chatgpt.com))

## Mi ajuste para tu caso

Yo dejaría esta política:

- `daily` con `lookback_days=5`
- `month` una vez por semana o el primer día hábil del mes
- validación después de cada update

Te paso también una versión con un flag extra `--auto-mode` que cambie solo a `month` cuando sea el primer día del mes.

si

Claro. Yo añadiría un `--auto-mode` que haga esto:

- use **`month`** si hoy es el **día 1 del mes**,
- en cualquier otro caso use **`daily`**.

Eso encaja bien con el flujo recomendado por Qlib para Yahoo: construir el dataset desde cero con el collector y luego hacer actualizaciones incrementales; además, Qlib deja claro que **no** se puede actualizar incrementalmente a partir del dataset offline empaquetado por Qlib. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

## Script completo: `update_us_auto_mode.py`

```python
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

def setup_logging(log_file: Path | None) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
    )

def read_last_calendar_date(qlib_data_dir: Path) -> pd.Timestamp:
    day_file = qlib_data_dir / "calendars" / "day.txt"
    if not day_file.exists():
        raise FileNotFoundError(f"No existe el calendario: {day_file}")

    cal = pd.read_csv(day_file, header=None)
    if cal.empty:
        raise ValueError(f"El calendario está vacío: {day_file}")

    return pd.to_datetime(cal.iloc[-1, 0]).normalize()

def first_day_of_current_month(today: pd.Timestamp | None = None) -> pd.Timestamp:
    if today is None:
        today = pd.Timestamp.today().normalize()
    return today.replace(day=1)

def resolve_mode(
    auto_mode: bool,
    explicit_mode: str | None,
    today: pd.Timestamp | None = None,
) -> str:
    if explicit_mode is not None:
        return explicit_mode

    if today is None:
        today = pd.Timestamp.today().normalize()

    if auto_mode:
        return "month" if today.day == 1 else "daily"

    return "daily"

def build_window(
    mode: str,
    last_dt: pd.Timestamp,
    lookback_days: int,
    end_offset_days: int,
    today: pd.Timestamp | None = None,
) -> tuple[str, str]:
    if today is None:
        today = pd.Timestamp.today().normalize()

    if mode == "daily":
        start_dt = last_dt - timedelta(days=lookback_days)
    elif mode == "month":
        start_dt = first_day_of_current_month(today)
    else:
        raise ValueError(f"Modo no soportado: {mode}")

    # En Qlib/Yahoo collector, end_date se usa como límite superior abierto.
    end_dt = today + timedelta(days=end_offset_days)

    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

def run_update(
    qlib_repo_dir: Path,
    qlib_data_dir: Path,
    trading_date: str,
    end_date: str,
    python_bin: str,
) -> int:
    collector = qlib_repo_dir / "scripts" / "data_collector" / "yahoo" / "collector.py"
    if not collector.exists():
        raise FileNotFoundError(f"No encuentro collector.py en: {collector}")

    cmd = [
        python_bin,
        str(collector),
        "update_data_to_bin",
        "--qlib_data_1d_dir",
        str(qlib_data_dir),
        "--trading_date",
        trading_date,
        "--end_date",
        end_date,
        "--region",
        "US",
    ]

    logging.info("Ejecutando: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode

def main() -> int:
    parser = argparse.ArgumentParser(description="Actualización automática de us_data en Qlib")

    parser.add_argument("--qlib-data-dir", required=True, help="Ruta a ~/.qlib/qlib_data/us_data")
    parser.add_argument("--qlib-repo-dir", required=True, help="Ruta al repo clonado de Qlib")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--mode",
        choices=["daily", "month"],
        default=None,
        help="Modo explícito: daily o month",
    )
    mode_group.add_argument(
        "--auto-mode",
        action="store_true",
        help="Si hoy es día 1 usa month; si no, daily",
    )

    parser.add_argument(
        "--lookback-days",
        type=int,
        default=5,
        help="Solo para daily: días hacia atrás desde la última fecha",
    )
    parser.add_argument(
        "--end-offset-days",
        type=int,
        default=1,
        help="1 = usar mañana como end_date",
    )
    parser.add_argument("--python-bin", default=sys.executable, help="Python para lanzar collector.py")
    parser.add_argument("--log-file", default=None, help="Fichero de log opcional")

    args = parser.parse_args()

    qlib_data_dir = Path(args.qlib_data_dir).expanduser().resolve()
    qlib_repo_dir = Path(args.qlib_repo_dir).expanduser().resolve()
    log_file = Path(args.log_file).expanduser().resolve() if args.log_file else None

    setup_logging(log_file)

    try:
        today = pd.Timestamp.today().normalize()
        last_dt = read_last_calendar_date(qlib_data_dir)
        mode = resolve_mode(
            auto_mode=args.auto_mode,
            explicit_mode=args.mode,
            today=today,
        )
        trading_date, end_date = build_window(
            mode=mode,
            last_dt=last_dt,
            lookback_days=args.lookback_days,
            end_offset_days=args.end_offset_days,
            today=today,
        )

        logging.info("Fecha de hoy: %s", today.date())
        logging.info("Última fecha en calendario: %s", last_dt.date())
        logging.info("Modo resuelto: %s", mode)
        logging.info("Ventana a actualizar: [%s, %s)", trading_date, end_date)

        rc = run_update(
            qlib_repo_dir=qlib_repo_dir,
            qlib_data_dir=qlib_data_dir,
            trading_date=trading_date,
            end_date=end_date,
            python_bin=args.python_bin,
        )

        if rc != 0:
            logging.error("collector.py terminó con código %s", rc)
            return rc

        logging.info("Actualización finalizada correctamente")
        return 0

    except Exception as e:
        logging.exception("Error en la actualización: %s", e)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

## Cómo lo usaría

### Automático

```bash
python update_us_auto_mode.py \
  --qlib-data-dir ~/.qlib/qlib_data/us_data \
  --qlib-repo-dir ~/src/qlib \
  --auto-mode \
  --lookback-days 5 \
  --log-file ~/qlib_workspace/logs/update_us_auto_mode.log
```

### Forzando modo diario

```bash
python update_us_auto_mode.py \
  --qlib-data-dir ~/.qlib/qlib_data/us_data \
  --qlib-repo-dir ~/src/qlib \
  --mode daily
```

### Forzando modo mensual

```bash
python update_us_auto_mode.py \
  --qlib-data-dir ~/.qlib/qlib_data/us_data \
  --qlib-repo-dir ~/src/qlib \
  --mode month
```

## Cómo lo dejaría en cron

Todos los días laborables a las 23:15:

```
15 23 * * 1-5 /usr/bin/python3 /home/toni/qlib_workspace/scripts/update_us_auto_mode.py --qlib-data-dir /home/toni/.qlib/qlib_data/us_data --qlib-repo-dir /home/toni/src/qlib --auto-mode --lookback-days 5 --log-file /home/toni/qlib_workspace/logs/update_us_auto_mode.log
```

## Mi criterio práctico

Yo usaría esta política:

- **`daily`** con `lookback_days=5` para rehacer una ventana corta y cubrir huecos.
- **`month`** cuando el día del mes sea `1`, para recomponer el tramo mensual desde el principio.
- `end_offset_days=1`, porque en el collector `end_date` funciona como límite superior abierto; por eso “mañana” suele cubrir hasta hoy. ([GitHub](https://github.com/zhostev/sqlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

## Dos detalles importantes

El collector de Yahoo para US daily sigue existiendo en el código como `YahooCollectorUS1d`, así que ese flujo sigue siendo válido para `us_data`. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/collector.py?utm_source=chatgpt.com))

Y seguiría haciendo una validación posterior al update, porque el propio README advierte que los datos de Yahoo pueden no ser perfectos, y además hay incidencias recientes reportadas en el collector. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

El siguiente paso natural es añadirle un `--validate-after` para que, si el update termina bien, ejecute automáticamente tu `validate_data.py`.

Vale

Perfecto 👍

Con eso ya tienes un pipeline bastante sólido y “production-like” dentro de Qlib:

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

## Validar que el Dataset no tiene gaps silenciosos

Yo lo validaría en **4 capas**. Con Yahoo es importante, porque el propio proyecto de Qlib avisa de que los datos “might not be perfect”, recomienda usar datos propios si necesitas más calidad, y además señala que las fuentes públicas pueden tener datos faltantes o erróneos. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))

## 1. Validación de calendario

Primero comprueba que el calendario de `calendars/day.txt` no tenga saltos inesperados y que la última fecha sea la que esperas. Qlib documenta que puedes usar los ficheros `.bin` con `numpy` para validar datos, y el calendario es la referencia base para saber qué sesiones deberían existir. ([qlib.readthedocs.io](https://qlib.readthedocs.io/en/latest/component/data.html?utm_source=chatgpt.com))

## 2. Cobertura por símbolo

Luego, para cada ticker relevante, compara:

- número esperado de sesiones en el rango,
- número real de filas,
- porcentaje de huecos,
- rachas de huecos consecutivos.

Aquí no intentaría revisar los miles de símbolos cada día; empezaría por:

- benchmarks: `SPY`, `QQQ`, `^GSPC`
- top holdings líquidas: `AAPL`, `MSFT`, `NVDA`, etc.
- el universo que realmente operas.
    
    Eso reduce mucho el riesgo de “gap silencioso” en nombres importantes, que es justo uno de los problemas plausibles al usar Yahoo/Qlib. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))
    

## 3. Validación transversal del universo

Además de validar nombres concretos, miraría el universo completo:

- cuántos símbolos tienen dato en la última sesión,
- cuántos tenían dato ayer,
- variación porcentual de cobertura entre ambos días.

Si hoy cae de golpe la cobertura del universo, aunque el proceso haya terminado “bien”, casi seguro tienes un gap silencioso o un fallo parcial del collector. Esto es especialmente relevante porque ha habido incidencias reportadas recientemente en el Yahoo collector de Qlib. ([GitHub](https://github.com/microsoft/qlib/issues/1981?utm_source=chatgpt.com))

## 4. Validación OHLCV básica

Por último, revisaría reglas de sanidad:

- `volume < 0` no permitido
- `high < low` no permitido
- `close`, `open`, `high`, `low` no nulos
- cambios diarios absurdos por encima de un umbral para revisión manual

Qlib ya muestra ejemplos de “abnormal data” en el README del Yahoo collector, así que no basta con comprobar que el fichero exista; hay que validar también que el contenido tenga sentido. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

Te dejo un script práctico para hacerlo.

```python
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def load_calendar(qlib_dir: Path) -> pd.DatetimeIndex:
    day_file = qlib_dir / "calendars" / "day.txt"
    cal = pd.read_csv(day_file, header=None)[0]
    return pd.DatetimeIndex(pd.to_datetime(cal).normalize())

def validate_calendar_continuity(cal: pd.DatetimeIndex) -> list[str]:
    issues = []
    if cal.empty:
        return ["calendar vacío"]

    if not cal.is_monotonic_increasing:
        issues.append("calendar no está ordenado ascendentemente")

    if cal.has_duplicates:
        issues.append("calendar contiene fechas duplicadas")

    return issues

def load_symbol_csv(csv_dir: Path, symbol: str) -> pd.DataFrame:
    path = csv_dir / f"{symbol.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    df = pd.read_csv(path)
    if "date" not in df.columns:
        raise ValueError(f"{path} no tiene columna 'date'")

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date").drop_duplicates(subset=["date"])
    return df

def validate_symbol_against_calendar(
    df: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    if start_date:
        start = pd.Timestamp(start_date).normalize()
    else:
        start = calendar.min()

    if end_date:
        end = pd.Timestamp(end_date).normalize()
    else:
        end = calendar.max()

    cal_slice = calendar[(calendar >= start) & (calendar <= end)]
    obs = pd.DatetimeIndex(df["date"])

    missing = cal_slice.difference(obs)
    extra = obs.difference(cal_slice)

    # racha máxima de huecos consecutivos en días de trading
    missing_mask = pd.Series(cal_slice.isin(missing), index=cal_slice)
    max_gap_run = 0
    current = 0
    for is_missing in missing_mask:
        if is_missing:
            current += 1
            max_gap_run = max(max_gap_run, current)
        else:
            current = 0

    out = {
        "expected_sessions": len(cal_slice),
        "observed_sessions": len(obs[(obs >= start) & (obs <= end)]),
        "missing_sessions": len(missing),
        "missing_pct": float(len(missing) / len(cal_slice)) if len(cal_slice) else np.nan,
        "max_consecutive_missing": int(max_gap_run),
        "extra_sessions": len(extra),
        "last_obs_date": obs.max() if len(obs) else pd.NaT,
    }

    return out

def validate_ohlcv(df: pd.DataFrame) -> list[str]:
    issues = []
    required = ["open", "high", "low", "close", "volume"]

    for col in required:
        if col not in df.columns:
            issues.append(f"falta columna {col}")

    if issues:
        return issues

    if df[required].isna().any().any():
        issues.append("hay nulos en OHLCV")

    bad_hilo = (df["high"] < df["low"]).sum()
    if bad_hilo:
        issues.append(f"{bad_hilo} filas con high < low")

    neg_vol = (df["volume"] < 0).sum()
    if neg_vol:
        issues.append(f"{neg_vol} filas con volume < 0")

    zero_price = ((df["open"] <= 0) | (df["high"] <= 0) | (df["low"] <= 0) | (df["close"] <= 0)).sum()
    if zero_price:
        issues.append(f"{zero_price} filas con precio <= 0")

    return issues

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qlib-dir", required=True, help="Ruta a qlib_data/us_data")
    parser.add_argument("--csv-dir", required=True, help="Ruta a raw csv descargados por Yahoo collector")
    parser.add_argument("--symbols", nargs="+", required=True, help="Símbolos a validar")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--max-missing-pct", type=float, default=0.01)
    parser.add_argument("--max-gap-run", type=int, default=1)
    args = parser.parse_args()

    qlib_dir = Path(args.qlib_dir).expanduser().resolve()
    csv_dir = Path(args.csv_dir).expanduser().resolve()

    calendar = load_calendar(qlib_dir)
    cal_issues = validate_calendar_continuity(calendar)

    if cal_issues:
        print("[ERROR] Problemas en calendar:")
        for x in cal_issues:
            print(" -", x)
        return 1

    print(f"[OK] calendar válido. Última sesión: {calendar.max().date()}")

    failed = False
    for symbol in args.symbols:
        try:
            df = load_symbol_csv(csv_dir, symbol)
            cov = validate_symbol_against_calendar(
                df, calendar, start_date=args.start_date, end_date=args.end_date
            )
            ohlcv_issues = validate_ohlcv(df)

            print(f"\n[{symbol}]")
            print(cov)

            if ohlcv_issues:
                failed = True
                print("  OHLCV issues:")
                for i in ohlcv_issues:
                    print("   -", i)

            if cov["missing_pct"] > args.max_missing_pct:
                failed = True
                print(f"  - missing_pct demasiado alto: {cov['missing_pct']:.2%}")

            if cov["max_consecutive_missing"] > args.max_gap_run:
                failed = True
                print(f"  - racha de huecos demasiado alta: {cov['max_consecutive_missing']}")

            if pd.isna(cov["last_obs_date"]) or cov["last_obs_date"] < calendar.max():
                failed = True
                print(f"  - última fecha observada atrasada: {cov['last_obs_date']}")

        except Exception as e:
            failed = True
            print(f"\n[{symbol}] ERROR: {e}")

    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
```

Ejemplo de uso:

```bash
python validate_gaps.py \
  --qlib-dir ~/.qlib/qlib_data/us_data \
  --csv-dir ~/qlib_workspace/data/live_us/raw_yahoo \
  --symbols SPY QQQ AAPL MSFT NVDA \
  --start-date 2026-01-01 \
  --max-missing-pct 0.002 \
  --max-gap-run 1
```

## Qué métricas vigilaría yo de verdad

Para un pipeline diario, pondría alertas si pasa cualquiera de estas:

- la última fecha del calendario no avanzó cuando debía,
- falta la última sesión en `SPY` o `QQQ`,
- más de `0.2%` de huecos en los símbolos core,
- una racha de más de `1` sesión faltante en un ticker líquido,
- la cobertura del universo en la última sesión cae bruscamente frente al día anterior.
    
    Esto no viene como umbral oficial de Qlib; es mi recomendación operativa para evitar falsas sensaciones de “todo ha ido bien”. La necesidad de ese tipo de chequeos sí está respaldada por las advertencias del propio proyecto sobre Yahoo y datos anómalos. ([GitHub](https://github.com/microsoft/qlib/tree/main/scripts/data_collector/yahoo?utm_source=chatgpt.com))
    

## Lo más importante

No validaría solo los `.bin`. Validaría también los **CSV raw** previos al dump, porque así puedes distinguir:

- fallo en descarga,
- fallo en normalización,
- fallo en conversión a bin.
    
    Qlib separa claramente el flujo de Yahoo collector y la conversión a formato Qlib, así que inspeccionar ambas capas te da mucha más trazabilidad. ([qlib.readthedocs.io](https://qlib.readthedocs.io/en/v0.6.2/component/data.html?utm_source=chatgpt.com))
    

Si quieres, te dejo una versión adaptada exactamente a tu estructura de carpetas `research_us/live_us` y con salida tipo `PASS/FAIL` para cron.

Perfecto

Genial, entonces te dejo una versión **lista para producción (cron-friendly)** adaptada a tu estructura `live_us` y con salida clara `PASS / FAIL`.
La idea:
• valida calendario
• valida símbolos críticos
• valida cobertura del universo (rápido)
• devuelve exit code ≠ 0 si algo falla → perfecto para cron
**✅ `validate_dataset_health.py`**

`from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import sys

CRITICAL_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT"]

def load_calendar(qlib_dir: Path) -> pd.DatetimeIndex:
    day_file = qlib_dir / "calendars" / "day.txt"
    cal = pd.read_csv(day_file, header=None)[0]
    return pd.DatetimeIndex(pd.to_datetime(cal).normalize())

def load_csv(csv_dir: Path, symbol: str) -> pd.DataFrame:
    path = csv_dir / f"{symbol.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df.sort_values("date").drop_duplicates("date")

def check_symbol(df: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict:
    obs = pd.DatetimeIndex(df["date"])
    missing = calendar.difference(obs)

    last_obs = obs.max() if len(obs) else pd.NaT

    return {
        "missing_pct": len(missing) / len(calendar),
        "last_date_ok": last_obs == calendar.max(),
        "rows": len(df),
    }

def check_universe_coverage(csv_dir: Path, calendar: pd.DatetimeIndex) -> dict:
    last_day = calendar.max()

    count_today = 0
    count_total = 0

    for f in csv_dir.glob("*.csv"):
        try:
            df = pd.read_csv(f, usecols=["date"])
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()

            if last_day in set(df["date"]):
                count_today += 1

            count_total += 1
        except:
            continue

    coverage = count_today / count_total if count_total else 0

    return {
        "total_symbols": count_total,
        "symbols_with_last_day": count_today,
        "coverage": coverage,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qlib-dir", required=True)
    parser.add_argument("--csv-dir", required=True)
    args = parser.parse_args()

    qlib_dir = Path(args.qlib_dir).expanduser()
    csv_dir = Path(args.csv_dir).expanduser()

    try:
        calendar = load_calendar(qlib_dir)
        last_day = calendar.max()

        print(f"[INFO] Last trading day: {last_day.date()}")

        # ---- CRITICAL SYMBOLS ----
        failed = False

        for sym in CRITICAL_SYMBOLS:
            try:
                df = load_csv(csv_dir, sym)
                res = check_symbol(df, calendar)

                print(f"[CHECK] {sym} → missing={res['missing_pct']:.3%}, last_ok={res['last_date_ok']}")

                if res["missing_pct"] > 0.002:
                    print(f"[FAIL] {sym} too many missing days")
                    failed = True

                if not res["last_date_ok"]:
                    print(f"[FAIL] {sym} missing latest day")
                    failed = True

            except Exception as e:
                print(f"[FAIL] {sym} error: {e}")
                failed = True

        # ---- UNIVERSE COVERAGE ----
        cov = check_universe_coverage(csv_dir, calendar)

        print(f"[INFO] Universe coverage: {cov['coverage']:.2%} ({cov['symbols_with_last_day']}/{cov['total_symbols']})")

        if cov["coverage"] < 0.9:
            print("[FAIL] Coverage too low")
            failed = True

        # ---- RESULT ----
        if failed:
            print("\n❌ DATASET HEALTH: FAIL")
            return 1
        else:
            print("\n✅ DATASET HEALTH: PASS")
            return 0

    except Exception as e:
        print(f"[ERROR] {e}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())`

**🧪 Uso**

`python validate_dataset_health.py \
  --qlib-dir ~/.qlib/qlib_data/us_data \
  --csv-dir ~/qlib_workspace/data/live_us/raw_yahoo`

**🔁 Integrado en tu pipeline**

`python update_us_auto_mode.py ...
python validate_dataset_health.py ...

# solo si PASS
python run_inference_lgb_alpha158.py ...
python build_target_weights.py ...`

**🧠 Qué detecta esto (importante)**
Este script te protege contra los **problemas reales de Yahoo/Qlib**:
**1. Dataset no actualizado**
→ SPY/QQQ no tienen el último día
**2. Fallo parcial del collector**
→ cobertura baja del universo
**3. Huecos silenciosos**
→ missing_pct alto
**4. Descarga corrupta de símbolos clave**
→ error directo en CSV

**🚀 Mejora (muy recomendada)**
Si quieres hacerlo más pro aún, añade:
**✔️ alerta por Slack / email
✔️ guardar histórico de métricas
✔️ comparar cobertura vs ayer**
Ejemplo clave:

`hoy: 92% cobertura
ayer: 98% → ALERTA`

**💡 Mi regla de oro**
Si falla cualquiera de estas:
• SPY o QQQ sin último día
• cobertura < 90%
• huecos en top symbols
👉 **NO generes señales ese día**

Si quieres, siguiente paso potente:
👉 añadir **detección automática de anomalías de precios (splits mal ajustados, spikes, etc.)**, que es el siguiente gran problema real con Yahoo.

Adelante

Perfecto. El siguiente control que yo añadiría es **detección de anomalías de precio** para cazar cosas como:

- **splits mal ajustados**
- **spikes absurdos**
- **velas imposibles**
- **volumen sospechoso**
- **gaps gigantes no explicables**

La idea no es “adivinar” si un dato es malo, sino marcarlo para **bloquear señales** o al menos **revisarlo**.

## Qué validaría

Yo usaría estas reglas:

1. **OHLC consistente**
    - `high >= max(open, close, low)`
    - `low <= min(open, close, high)`
2. **Precios positivos**
    - `open, high, low, close > 0`
3. **Retornos diarios extremos**
    - por ejemplo `abs(close_t / close_t-1 - 1) > 40%`
    - no siempre es error, pero en mega caps suele ser sospechoso
4. **Rango intradía extremo**
    - `(high / low - 1) > 30%`
5. **Volumen cero o anómalo**
    - para símbolos líquidos, volumen 0 suele ser mala señal
    - también puedes marcar volumen > 20x mediana reciente
6. **Saltos tipo split mal ajustado**
    - ratios cercanos a `2x`, `3x`, `0.5x`, `0.333x`, etc.
    - no hace falta acertar el split; basta con marcarlo

---

## Script: `validate_price_anomalies.py`

```python
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

DEFAULT_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]

def load_symbol_csv(csv_dir: Path, symbol: str) -> pd.DataFrame:
    path = csv_dir / f"{symbol.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    df = pd.read_csv(path)
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path} no tiene columnas requeridas: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def near_split_ratio(x: float, tol: float = 0.08) -> str | None:
    if not np.isfinite(x) or x <= 0:
        return None

    targets = {
        "2:1": 2.0,
        "3:1": 3.0,
        "4:1": 4.0,
        "1:2": 0.5,
        "1:3": 1 / 3,
        "1:4": 0.25,
    }

    for label, target in targets.items():
        if abs(x / target - 1) <= tol:
            return label
    return None

def detect_anomalies(
    df: pd.DataFrame,
    max_abs_return: float = 0.40,
    max_intraday_range: float = 0.30,
    max_volume_spike: float = 20.0,
    rolling_volume_window: int = 20,
) -> pd.DataFrame:
    out = df.copy()

    out["prev_close"] = out["close"].shift(1)
    out["ret_close"] = out["close"] / out["prev_close"] - 1.0
    out["gap_open"] = out["open"] / out["prev_close"] - 1.0
    out["intraday_range"] = out["high"] / out["low"] - 1.0

    vol_med = out["volume"].rolling(rolling_volume_window, min_periods=5).median().shift(1)
    out["volume_vs_median"] = out["volume"] / vol_med.replace(0, np.nan)

    flags: list[dict] = []

    for row in out.itertuples(index=False):
        row_flags: list[str] = []

        o = row.open
        h = row.high
        l = row.low
        c = row.close
        v = row.volume
        prev_c = row.prev_close
        ret_c = row.ret_close
        gap_o = row.gap_open
        intraday = row.intraday_range
        vol_ratio = row.volume_vs_median

        if pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c) or pd.isna(v):
            row_flags.append("nan_in_ohlcv")

        if pd.notna(o) and o <= 0:
            row_flags.append("open_non_positive")
        if pd.notna(h) and h <= 0:
            row_flags.append("high_non_positive")
        if pd.notna(l) and l <= 0:
            row_flags.append("low_non_positive")
        if pd.notna(c) and c <= 0:
            row_flags.append("close_non_positive")
        if pd.notna(v) and v < 0:
            row_flags.append("negative_volume")

        if pd.notna(h) and pd.notna(o) and pd.notna(c) and pd.notna(l):
            if h < max(o, c, l):
                row_flags.append("high_inconsistent")
            if l > min(o, c, h):
                row_flags.append("low_inconsistent")

        if pd.notna(ret_c) and abs(ret_c) > max_abs_return:
            row_flags.append(f"extreme_close_return>{max_abs_return:.0%}")

        if pd.notna(gap_o) and abs(gap_o) > max_abs_return:
            row_flags.append(f"extreme_open_gap>{max_abs_return:.0%}")

        if pd.notna(intraday) and intraday > max_intraday_range:
            row_flags.append(f"extreme_intraday_range>{max_intraday_range:.0%}")

        if pd.notna(v) and v == 0:
            row_flags.append("zero_volume")

        if pd.notna(vol_ratio) and vol_ratio > max_volume_spike:
            row_flags.append(f"volume_spike>{max_volume_spike:.1f}x")

        if pd.notna(prev_c) and prev_c > 0 and pd.notna(c):
            ratio = c / prev_c
            split_label = near_split_ratio(ratio)
            if split_label is not None:
                row_flags.append(f"possible_split_like_move_{split_label}")

        if row_flags:
            flags.append(
                {
                    "date": row.date,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "volume": v,
                    "prev_close": prev_c,
                    "ret_close": ret_c,
                    "gap_open": gap_o,
                    "intraday_range": intraday,
                    "volume_vs_median": vol_ratio,
                    "flags": ",".join(row_flags),
                }
            )

    return pd.DataFrame(flags)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-abs-return", type=float, default=0.40)
    parser.add_argument("--max-intraday-range", type=float, default=0.30)
    parser.add_argument("--max-volume-spike", type=float, default=20.0)
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    any_fail = False
    summary_rows = []

    for symbol in args.symbols:
        try:
            df = load_symbol_csv(csv_dir, symbol)
            anomalies = detect_anomalies(
                df,
                max_abs_return=args.max_abs_return,
                max_intraday_range=args.max_intraday_range,
                max_volume_spike=args.max_volume_spike,
            )

            out_file = output_dir / f"{symbol.upper()}_anomalies.csv"
            anomalies.to_csv(out_file, index=False)

            n = len(anomalies)
            summary_rows.append({"symbol": symbol.upper(), "anomaly_rows": n, "file": str(out_file)})

            if n > 0:
                any_fail = True
                print(f"[WARN] {symbol.upper()}: {n} anomalías -> {out_file}")
            else:
                print(f"[OK] {symbol.upper()}: sin anomalías relevantes")

        except Exception as e:
            any_fail = True
            summary_rows.append({"symbol": symbol.upper(), "anomaly_rows": -1, "file": str(e)})
            print(f"[FAIL] {symbol.upper()}: {e}")

    summary = pd.DataFrame(summary_rows)
    summary_file = output_dir / "anomaly_summary.csv"
    summary.to_csv(summary_file, index=False)

    if any_fail:
        print(f"\n[FAIL] Price anomaly check failed. Resumen: {summary_file}")
        return 1

    print(f"\n[PASS] Price anomaly check passed. Resumen: {summary_file}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## Cómo lo usaría

```bash
python validate_price_anomalies.py \
  --csv-dir ~/qlib_workspace/data/live_us/raw_yahoo \
  --output-dir ~/qlib_workspace/logs/anomalies \
  --symbols SPY QQQ AAPL MSFT NVDA
```

## Cómo integrarlo en el pipeline

```bash
python update_us_auto_mode.py ...
python validate_dataset_health.py ...
python validate_price_anomalies.py ...

# solo si todo pasa
python run_inference_lgb_alpha158.py ...
python build_target_weights.py ...
```

## Mi criterio práctico

Yo pondría estas reglas operativas:

- si falla **SPY** o **QQQ** → no generar señales
- si hay anomalías en más de `X` símbolos core → no generar señales
- si la anomalía es solo en un nombre aislado → excluir ese símbolo ese día

## Mejora muy útil

La siguiente evolución sería no solo revisar símbolos fijos, sino también:

- el **top 50 por score** del día anterior
- el **universo elegible** actual
- las **posiciones reales** que ya tienes en cartera

Eso es mejor que revisar solo `SPY/QQQ/AAPL/MSFT`, porque captura errores justo donde más te afectan.

## Regla simple que usaría yo

- **health check general**
- **price anomaly check**
- **si hay fail, no inferencia**
- **si hay warn aislado, excluir símbolo**

El siguiente paso bueno es juntar ambos scripts en uno solo, con salida tipo:

- `PASS`
- `WARN`
- `FAIL`

y además generar un `excluded_symbols.csv` para que `build_target_weights.py` no use esos nombres.

Adelante

Perfecto. Yo lo uniría en un **único chequeo de calidad** que haga tres cosas:

- emitir un estado global: `PASS`, `WARN` o `FAIL`
- generar `excluded_symbols.csv`
- devolver un **exit code** útil para cron/pipeline

Esto tiene sentido con Qlib porque el collector de Yahoo puede traer datos anómalos o incompletos, y el propio proyecto recomienda usar el Yahoo collector para construir/actualizar tus datos desde cero si quieres incremental; además, el ejemplo oficial de workflow usa recorder/modelo/dataset de forma modular, así que encaja bien meter esta validación como un paso previo a inferencia. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

## Regla operativa que usaría

**FAIL**

- falta el último día en `SPY` o `QQQ`
- cobertura del universo por debajo de un umbral duro
- OHLC inconsistente en benchmarks
- demasiadas anomalías en símbolos críticos

**WARN**

- anomalías aisladas en algunos nombres
- cobertura algo baja pero no catastrófica
- gaps pequeños en símbolos no core

**PASS**

- todo razonable

Y además:

- `excluded_symbols.csv` con los tickers a bloquear ese día
- `health_report.json` con métricas
- `health_summary.csv` con resumen por símbolo

## Script unificado: `dataset_guard.py`

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_CRITICAL_SYMBOLS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]
DEFAULT_BENCHMARK_SYMBOLS = ["SPY", "QQQ"]

def load_calendar(qlib_dir: Path) -> pd.DatetimeIndex:
    day_file = qlib_dir / "calendars" / "day.txt"
    if not day_file.exists():
        raise FileNotFoundError(f"No existe el calendario: {day_file}")

    cal = pd.read_csv(day_file, header=None)[0]
    cal = pd.DatetimeIndex(pd.to_datetime(cal).normalize())

    if cal.empty:
        raise ValueError("El calendario está vacío")
    if not cal.is_monotonic_increasing:
        raise ValueError("El calendario no está ordenado")
    if cal.has_duplicates:
        raise ValueError("El calendario tiene fechas duplicadas")

    return cal

def load_symbol_csv(csv_dir: Path, symbol: str) -> pd.DataFrame:
    path = csv_dir / f"{symbol.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    df = pd.read_csv(path)

    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} sin columnas requeridas: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

def check_symbol_coverage(df: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict[str, Any]:
    obs = pd.DatetimeIndex(df["date"])
    missing = calendar.difference(obs)
    missing_mask = pd.Series(calendar.isin(missing), index=calendar)

    max_gap_run = 0
    current = 0
    for is_missing in missing_mask:
        if is_missing:
            current += 1
            max_gap_run = max(max_gap_run, current)
        else:
            current = 0

    last_obs = obs.max() if len(obs) else pd.NaT

    return {
        "rows": int(len(df)),
        "missing_sessions": int(len(missing)),
        "missing_pct": float(len(missing) / len(calendar)),
        "max_consecutive_missing": int(max_gap_run),
        "last_obs_date": None if pd.isna(last_obs) else str(pd.Timestamp(last_obs).date()),
        "last_date_ok": bool(last_obs == calendar.max()),
    }

def near_split_ratio(x: float, tol: float = 0.08) -> str | None:
    if not np.isfinite(x) or x <= 0:
        return None

    targets = {
        "2:1": 2.0,
        "3:1": 3.0,
        "4:1": 4.0,
        "1:2": 0.5,
        "1:3": 1 / 3,
        "1:4": 0.25,
    }
    for label, target in targets.items():
        if abs(x / target - 1) <= tol:
            return label
    return None

def detect_price_flags(
    df: pd.DataFrame,
    max_abs_return: float,
    max_intraday_range: float,
    max_volume_spike: float,
    rolling_volume_window: int = 20,
) -> pd.DataFrame:
    out = df.copy()
    out["prev_close"] = out["close"].shift(1)
    out["ret_close"] = out["close"] / out["prev_close"] - 1.0
    out["gap_open"] = out["open"] / out["prev_close"] - 1.0
    out["intraday_range"] = out["high"] / out["low"] - 1.0

    vol_med = out["volume"].rolling(rolling_volume_window, min_periods=5).median().shift(1)
    out["volume_vs_median"] = out["volume"] / vol_med.replace(0, np.nan)

    rows: list[dict[str, Any]] = []

    for row in out.itertuples(index=False):
        flags: list[str] = []

        o, h, l, c, v = row.open, row.high, row.low, row.close, row.volume
        prev_c = row.prev_close
        ret_c = row.ret_close
        gap_o = row.gap_open
        intraday = row.intraday_range
        vol_ratio = row.volume_vs_median

        if pd.isna(o) or pd.isna(h) or pd.isna(l) or pd.isna(c) or pd.isna(v):
            flags.append("nan_in_ohlcv")

        if pd.notna(o) and o <= 0:
            flags.append("open_non_positive")
        if pd.notna(h) and h <= 0:
            flags.append("high_non_positive")
        if pd.notna(l) and l <= 0:
            flags.append("low_non_positive")
        if pd.notna(c) and c <= 0:
            flags.append("close_non_positive")
        if pd.notna(v) and v < 0:
            flags.append("negative_volume")

        if pd.notna(h) and pd.notna(o) and pd.notna(c) and pd.notna(l):
            if h < max(o, c, l):
                flags.append("high_inconsistent")
            if l > min(o, c, h):
                flags.append("low_inconsistent")

        if pd.notna(ret_c) and abs(ret_c) > max_abs_return:
            flags.append(f"extreme_close_return>{max_abs_return:.0%}")

        if pd.notna(gap_o) and abs(gap_o) > max_abs_return:
            flags.append(f"extreme_open_gap>{max_abs_return:.0%}")

        if pd.notna(intraday) and intraday > max_intraday_range:
            flags.append(f"extreme_intraday_range>{max_intraday_range:.0%}")

        if pd.notna(v) and v == 0:
            flags.append("zero_volume")

        if pd.notna(vol_ratio) and vol_ratio > max_volume_spike:
            flags.append(f"volume_spike>{max_volume_spike:.1f}x")

        if pd.notna(prev_c) and prev_c > 0 and pd.notna(c):
            split_label = near_split_ratio(c / prev_c)
            if split_label is not None:
                flags.append(f"possible_split_like_move_{split_label}")

        if flags:
            rows.append(
                {
                    "date": str(pd.Timestamp(row.date).date()),
                    "flags": flags,
                    "open": None if pd.isna(o) else float(o),
                    "high": None if pd.isna(h) else float(h),
                    "low": None if pd.isna(l) else float(l),
                    "close": None if pd.isna(c) else float(c),
                    "volume": None if pd.isna(v) else float(v),
                }
            )

    return pd.DataFrame(rows)

def check_universe_coverage(csv_dir: Path, last_day: pd.Timestamp) -> dict[str, Any]:
    total = 0
    with_last_day = 0
    readable = 0

    for f in csv_dir.glob("*.csv"):
        total += 1
        try:
            df = pd.read_csv(f, usecols=["date"])
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            readable += 1
            if last_day in set(df["date"]):
                with_last_day += 1
        except Exception:
            continue

    coverage = with_last_day / readable if readable else 0.0
    return {
        "files_total": int(total),
        "files_readable": int(readable),
        "symbols_with_last_day": int(with_last_day),
        "coverage": float(coverage),
    }

def classify_symbol(
    symbol: str,
    coverage: dict[str, Any],
    price_flags: pd.DataFrame,
    critical_symbols: set[str],
    benchmark_symbols: set[str],
    max_missing_pct_warn: float,
    max_missing_pct_fail: float,
    max_gap_warn: int,
    max_gap_fail: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    level = "PASS"

    missing_pct = coverage["missing_pct"]
    max_gap = coverage["max_consecutive_missing"]
    last_date_ok = coverage["last_date_ok"]

    if missing_pct > max_missing_pct_fail:
        level = "FAIL"
        reasons.append(f"missing_pct>{max_missing_pct_fail:.2%}")
    elif missing_pct > max_missing_pct_warn and level != "FAIL":
        level = "WARN"
        reasons.append(f"missing_pct>{max_missing_pct_warn:.2%}")

    if max_gap > max_gap_fail:
        level = "FAIL"
        reasons.append(f"max_gap>{max_gap_fail}")
    elif max_gap > max_gap_warn and level != "FAIL":
        level = "WARN"
        reasons.append(f"max_gap>{max_gap_warn}")

    if not last_date_ok:
        if symbol in benchmark_symbols:
            level = "FAIL"
            reasons.append("missing_latest_day_benchmark")
        elif level != "FAIL":
            level = "WARN"
            reasons.append("missing_latest_day")

    if not price_flags.empty:
        serious_flags = {
            "nan_in_ohlcv",
            "open_non_positive",
            "high_non_positive",
            "low_non_positive",
            "close_non_positive",
            "negative_volume",
            "high_inconsistent",
            "low_inconsistent",
        }

        any_serious = False
        for row_flags in price_flags["flags"]:
            if any(flag in serious_flags for flag in row_flags):
                any_serious = True
                break

        if any_serious:
            if symbol in benchmark_symbols:
                level = "FAIL"
                reasons.append("serious_price_inconsistency_benchmark")
            else:
                level = "FAIL"
                reasons.append("serious_price_inconsistency")
        else:
            if symbol in critical_symbols and level != "FAIL":
                level = "WARN"
                reasons.append("price_anomaly_critical")
            elif level == "PASS":
                level = "WARN"
                reasons.append("price_anomaly")

    return level, reasons

def save_outputs(
    output_dir: Path,
    summary_rows: list[dict[str, Any]],
    excluded_rows: list[dict[str, Any]],
    report: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(summary_rows).to_csv(output_dir / "health_summary.csv", index=False)
    pd.DataFrame(excluded_rows).to_csv(output_dir / "excluded_symbols.csv", index=False)

    with open(output_dir / "health_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

def main() -> int:
    parser = argparse.ArgumentParser(description="Guard de dataset para Qlib/Yahoo")
    parser.add_argument("--qlib-dir", required=True)
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--critical-symbols", nargs="*", default=DEFAULT_CRITICAL_SYMBOLS)
    parser.add_argument("--benchmark-symbols", nargs="*", default=DEFAULT_BENCHMARK_SYMBOLS)
    parser.add_argument("--max-missing-pct-warn", type=float, default=0.002)
    parser.add_argument("--max-missing-pct-fail", type=float, default=0.01)
    parser.add_argument("--max-gap-warn", type=int, default=1)
    parser.add_argument("--max-gap-fail", type=int, default=2)
    parser.add_argument("--min-universe-coverage-warn", type=float, default=0.90)
    parser.add_argument("--min-universe-coverage-fail", type=float, default=0.80)
    parser.add_argument("--max-abs-return", type=float, default=0.40)
    parser.add_argument("--max-intraday-range", type=float, default=0.30)
    parser.add_argument("--max-volume-spike", type=float, default=20.0)
    args = parser.parse_args()

    qlib_dir = Path(args.qlib_dir).expanduser().resolve()
    csv_dir = Path(args.csv_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    calendar = load_calendar(qlib_dir)
    last_day = calendar.max()

    universe_cov = check_universe_coverage(csv_dir, last_day)

    critical_symbols = {s.upper() for s in args.critical_symbols}
    benchmark_symbols = {s.upper() for s in args.benchmark_symbols}
    symbols_to_check = sorted(critical_symbols | benchmark_symbols)

    summary_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    symbol_reports: dict[str, Any] = {}

    global_level = "PASS"
    global_reasons: list[str] = []

    for symbol in symbols_to_check:
        try:
            df = load_symbol_csv(csv_dir, symbol)
            cov = check_symbol_coverage(df, calendar)
            flags_df = detect_price_flags(
                df=df,
                max_abs_return=args.max_abs_return,
                max_intraday_range=args.max_intraday_range,
                max_volume_spike=args.max_volume_spike,
            )

            level, reasons = classify_symbol(
                symbol=symbol,
                coverage=cov,
                price_flags=flags_df,
                critical_symbols=critical_symbols,
                benchmark_symbols=benchmark_symbols,
                max_missing_pct_warn=args.max_missing_pct_warn,
                max_missing_pct_fail=args.max_missing_pct_fail,
                max_gap_warn=args.max_gap_warn,
                max_gap_fail=args.max_gap_fail,
            )

            if level == "FAIL":
                global_level = "FAIL"
            elif level == "WARN" and global_level == "PASS":
                global_level = "WARN"

            if level in {"WARN", "FAIL"}:
                excluded_rows.append(
                    {
                        "symbol": symbol,
                        "level": level,
                        "reasons": "|".join(reasons),
                    }
                )

            summary_rows.append(
                {
                    "symbol": symbol,
                    "level": level,
                    "rows": cov["rows"],
                    "missing_pct": cov["missing_pct"],
                    "max_consecutive_missing": cov["max_consecutive_missing"],
                    "last_date_ok": cov["last_date_ok"],
                    "price_flag_rows": int(len(flags_df)),
                    "reasons": "|".join(reasons),
                }
            )

            symbol_reports[symbol] = {
                "coverage": cov,
                "price_flag_rows": int(len(flags_df)),
                "price_flags_preview": flags_df.head(10).to_dict(orient="records"),
                "level": level,
                "reasons": reasons,
            }

            flags_out = output_dir / f"{symbol}_price_flags.csv"
            output_dir.mkdir(parents=True, exist_ok=True)
            flags_df.to_csv(flags_out, index=False)

        except Exception as e:
            global_level = "FAIL"
            reason = f"load_or_validation_error:{e}"
            excluded_rows.append({"symbol": symbol, "level": "FAIL", "reasons": reason})
            summary_rows.append(
                {
                    "symbol": symbol,
                    "level": "FAIL",
                    "rows": 0,
                    "missing_pct": None,
                    "max_consecutive_missing": None,
                    "last_date_ok": False,
                    "price_flag_rows": None,
                    "reasons": reason,
                }
            )
            symbol_reports[symbol] = {"level": "FAIL", "reasons": [reason]}

    cov = universe_cov["coverage"]
    if cov < args.min_universe_coverage_fail:
        global_level = "FAIL"
        global_reasons.append(f"universe_coverage<{args.min_universe_coverage_fail:.0%}")
    elif cov < args.min_universe_coverage_warn and global_level != "FAIL":
        global_level = "WARN"
        global_reasons.append(f"universe_coverage<{args.min_universe_coverage_warn:.0%}")

    report = {
        "status": global_level,
        "date": str(pd.Timestamp(last_day).date()),
        "global_reasons": global_reasons,
        "universe_coverage": universe_cov,
        "symbols": symbol_reports,
    }

    save_outputs(output_dir, summary_rows, excluded_rows, report)

    print(f"[INFO] Last trading day: {last_day.date()}")
    print(
        f"[INFO] Universe coverage: {universe_cov['coverage']:.2%} "
        f"({universe_cov['symbols_with_last_day']}/{universe_cov['files_readable']})"
    )
    print(f"[INFO] Output dir: {output_dir}")

    if global_level == "PASS":
        print("\n✅ DATASET GUARD: PASS")
        return 0
    if global_level == "WARN":
        print("\n⚠️ DATASET GUARD: WARN")
        return 10

    print("\n❌ DATASET GUARD: FAIL")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

## Cómo lo usaría

```bash
python dataset_guard.py \
  --qlib-dir ~/.qlib/qlib_data/us_data \
  --csv-dir ~/qlib_workspace/data/live_us/raw_yahoo \
  --output-dir ~/qlib_workspace/logs/dataset_guard
```

## Qué te genera

En `~/qlib_workspace/logs/dataset_guard`:

- `health_summary.csv`
- `excluded_symbols.csv`
- `health_report.json`
- `SPY_price_flags.csv`
- `QQQ_price_flags.csv`
- etc.

## Cómo lo integraría en el pipeline

```bash
python update_us_auto_mode.py ...

python dataset_guard.py \
  --qlib-dir ~/.qlib/qlib_data/us_data \
  --csv-dir ~/qlib_workspace/data/live_us/raw_yahoo \
  --output-dir ~/qlib_workspace/logs/dataset_guard

rc=$?

if [ "$rc" -eq 1 ]; then
  echo "[STOP] dataset guard FAIL"
  exit 1
fi

python run_inference_lgb_alpha158.py ...

python build_target_weights.py \
  --scores ~/qlib_workspace/signals/predictions/latest_scores.parquet \
  --output ~/qlib_workspace/signals/orders/target_weights.csv \
  --topk 20 \
  --max-weight 0.10
```

## Cómo usar `excluded_symbols.csv`

En `build_target_weights.py`, antes de elegir el top-k:

```python
excluded = pd.read_csv("~/qlib_workspace/logs/dataset_guard/excluded_symbols.csv")
excluded_set = set(excluded["symbol"].str.upper())

df["instrument"] = df["instrument"].str.upper()
df = df[~df["instrument"].isin(excluded_set)].copy()
```

## Mi recomendación práctica

Yo haría esto:

- `PASS` → seguir normal
- `WARN` → seguir, pero excluyendo símbolos marcados
- `FAIL` → no generar señales

Eso es especialmente razonable con Yahoo, porque el collector está pensado para research y el propio README advierte que puede haber datos anómalos; además, la ruta recomendada para incremental es construir los datos con el collector desde cero y mantenerlos con ese flujo. ([GitHub](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/yahoo/README.md?utm_source=chatgpt.com))

## Una mejora más, muy útil

El siguiente paso que haría es que `dataset_guard.py` lea también:

- las **posiciones actuales**
- el **top 50 scoreado ayer**
- el **universo elegible de hoy**

y eleve a `FAIL` cualquier anomalía que afecte a una posición viva o a un candidato con score alto.

Eso te protege mucho más que revisar solo `SPY`, `QQQ`, `AAPL`, `MSFT` y `NVDA`.

Si quieres, te dejo ahora `build_target_weights.py` ya modificado para consumir `excluded_symbols.csv` y aplicar además un buffer de turnover.

Adelante

Perfecto. Te dejo `build_target_weights.py` ya preparado para:

- leer `latest_scores.parquet`
- excluir símbolos desde `excluded_symbols.csv`
- aplicar **buffer de turnover**
- limitar peso máximo por nombre
- exportar **target weights** y también **órdenes delta**

Así ya lo puedes conectar con posiciones reales o paper trading.

---

## Idea del turnover buffer

En vez de rehacer toda la cartera cada día, haces esto:

- si un valor **ya está en cartera** y sigue “más o menos bien”, lo mantienes
- solo metes cambios cuando la diferencia supera un umbral
- así reduces rotación y costes

Una versión simple y bastante útil es:

- eliges candidatos por score
- conservas posiciones actuales si siguen dentro de un rango ampliado
- solo compras/vendes si el cambio de peso supera `min_trade_weight`

---

## Script: `build_target_weights.py`

```python
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

def load_scores(scores_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(scores_path)
    required = {"datetime", "instrument", "score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en scores: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df

def load_excluded(excluded_path: Path | None) -> set[str]:
    if excluded_path is None or not excluded_path.exists():
        return set()

    df = pd.read_csv(excluded_path)
    if "symbol" not in df.columns:
        raise ValueError("excluded_symbols.csv debe tener columna 'symbol'")

    return set(df["symbol"].astype(str).str.upper())

def load_current_positions(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["instrument", "current_weight"])

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError("current_positions debe ser csv o parquet")

    required = {"instrument", "current_weight"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en current_positions: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["current_weight"] = pd.to_numeric(df["current_weight"], errors="coerce").fillna(0.0)
    return df[["instrument", "current_weight"]]

def select_with_buffer(
    scores: pd.DataFrame,
    current_positions: pd.DataFrame,
    topk: int,
    buffer_names: int,
) -> pd.DataFrame:
    scores = scores.sort_values("score", ascending=False).reset_index(drop=True).copy()
    current_set = set(current_positions["instrument"])

    hard_selected = scores.head(topk).copy()
    buffer_selected = scores.head(topk + buffer_names).copy()

    keep_current = buffer_selected[buffer_selected["instrument"].isin(current_set)].copy()
    merged = pd.concat([hard_selected, keep_current], ignore_index=True)
    merged = merged.drop_duplicates(subset=["instrument"]).sort_values("score", ascending=False)

    if len(merged) > topk:
        protected = set(keep_current["instrument"])
        rows = []
        for _, row in merged.iterrows():
            if len(rows) < topk:
                rows.append(row)
                continue

            if row["instrument"] in protected:
                continue

        merged = merged.head(topk).copy()

    return merged.head(topk).copy()

def build_equal_weight_targets(
    selected: pd.DataFrame,
    max_weight: float,
) -> pd.DataFrame:
    selected = selected.copy()
    n = len(selected)
    if n == 0:
        selected["target_weight"] = []
        return selected

    raw_weight = 1.0 / n
    capped = min(raw_weight, max_weight)
    selected["target_weight"] = capped

    total = selected["target_weight"].sum()
    if total > 0:
        selected["target_weight"] = selected["target_weight"] / total

    return selected

def apply_turnover_floor(
    target_df: pd.DataFrame,
    current_positions: pd.DataFrame,
    min_trade_weight: float,
) -> pd.DataFrame:
    merged = target_df.merge(current_positions, on="instrument", how="left")
    merged["current_weight"] = merged["current_weight"].fillna(0.0)
    merged["delta_weight"] = merged["target_weight"] - merged["current_weight"]

    small_change_mask = merged["delta_weight"].abs() < min_trade_weight
    merged.loc[small_change_mask, "target_weight"] = merged.loc[small_change_mask, "current_weight"]

    total = merged["target_weight"].sum()
    if total > 0:
        merged["target_weight"] = merged["target_weight"] / total

    merged["delta_weight"] = merged["target_weight"] - merged["current_weight"]
    return merged

def add_exits(
    target_df: pd.DataFrame,
    current_positions: pd.DataFrame,
) -> pd.DataFrame:
    target_names = set(target_df["instrument"])
    exits = current_positions[~current_positions["instrument"].isin(target_names)].copy()

    if exits.empty:
        return target_df

    exits["datetime"] = target_df["datetime"].iloc[0] if len(target_df) else pd.Timestamp.utcnow().normalize()
    exits["score"] = pd.NA
    exits["target_weight"] = 0.0
    exits["delta_weight"] = -exits["current_weight"]

    cols = ["datetime", "instrument", "score", "current_weight", "target_weight", "delta_weight"]
    base = target_df.copy()
    if "current_weight" not in base.columns:
        base["current_weight"] = 0.0
    if "delta_weight" not in base.columns:
        base["delta_weight"] = base["target_weight"] - base["current_weight"]

    return pd.concat([base[cols], exits[cols]], ignore_index=True).sort_values(
        ["target_weight", "score"], ascending=[False, False], na_position="last"
    )

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", required=True)
    parser.add_argument("--output-targets", required=True)
    parser.add_argument("--output-orders", required=True)
    parser.add_argument("--excluded-symbols", default=None)
    parser.add_argument("--current-positions", default=None)
    parser.add_argument("--topk", type=int, default=20)
    parser.add_argument("--buffer-names", type=int, default=10)
    parser.add_argument("--max-weight", type=float, default=0.10)
    parser.add_argument("--min-trade-weight", type=float, default=0.01)
    args = parser.parse_args()

    scores_path = Path(args.scores).expanduser().resolve()
    output_targets = Path(args.output_targets).expanduser().resolve()
    output_orders = Path(args.output_orders).expanduser().resolve()
    excluded_path = Path(args.excluded_symbols).expanduser().resolve() if args.excluded_symbols else None
    current_positions_path = Path(args.current_positions).expanduser().resolve() if args.current_positions else None

    scores = load_scores(scores_path)
    excluded = load_excluded(excluded_path)
    current_positions = load_current_positions(current_positions_path)

    latest_dt = scores["datetime"].max()
    latest = scores[scores["datetime"] == latest_dt].copy()

    if excluded:
        latest = latest[~latest["instrument"].isin(excluded)].copy()

    latest = latest.sort_values("score", ascending=False).reset_index(drop=True)

    selected = select_with_buffer(
        scores=latest,
        current_positions=current_positions,
        topk=args.topk,
        buffer_names=args.buffer_names,
    )

    targets = build_equal_weight_targets(
        selected=selected,
        max_weight=args.max_weight,
    )

    targets["datetime"] = latest_dt

    targets = apply_turnover_floor(
        target_df=targets,
        current_positions=current_positions,
        min_trade_weight=args.min_trade_weight,
    )

    orders = add_exits(
        target_df=targets,
        current_positions=current_positions,
    )

    output_targets.parent.mkdir(parents=True, exist_ok=True)
    output_orders.parent.mkdir(parents=True, exist_ok=True)

    targets[["datetime", "instrument", "score", "current_weight", "target_weight", "delta_weight"]].to_csv(
        output_targets, index=False
    )
    orders[["datetime", "instrument", "score", "current_weight", "target_weight", "delta_weight"]].to_csv(
        output_orders, index=False
    )

    print(f"[OK] Targets guardados en: {output_targets}")
    print(f"[OK] Orders guardadas en: {output_orders}")

if __name__ == "__main__":
    main()
```

---

## Formato esperado de `current_positions.csv`

```
instrument,current_weight
AAPL,0.08
MSFT,0.07
NVDA,0.06
QQQ,0.05
```

Son **pesos actuales**, no número de acciones.

---

## Formato de `excluded_symbols.csv`

El que genera `dataset_guard.py` ya te vale:

```
symbol,level,reasons
AAPL,WARN,price_anomaly_critical
QQQ,FAIL,missing_latest_day_benchmark
```

Aquí solo usamos la columna `symbol`.

---

## Ejemplo de uso

```bash
python build_target_weights.py \
  --scores ~/qlib_workspace/signals/predictions/latest_scores.parquet \
  --output-targets ~/qlib_workspace/signals/orders/target_weights.csv \
  --output-orders ~/qlib_workspace/signals/orders/orders_delta.csv \
  --excluded-symbols ~/qlib_workspace/logs/dataset_guard/excluded_symbols.csv \
  --current-positions ~/qlib_workspace/live/current_positions.csv \
  --topk 20 \
  --buffer-names 10 \
  --max-weight 0.10 \
  --min-trade-weight 0.01
```

---

## Qué hace exactamente

### 1. Excluye símbolos problemáticos

Si `dataset_guard.py` marcó algo, no entra en selección.

### 2. Selecciona con buffer

Con `topk=20` y `buffer_names=10`:

- eliges top 20 por score
- pero permites conservar nombres actuales si siguen dentro del top 30

Eso baja bastante la rotación.

### 3. Asigna pesos objetivo

Ahora mismo lo dejo en **equal weight** con tope `max_weight`.

### 4. Aplica suelo de trading

Si el cambio de peso es demasiado pequeño, no lo opera.

Ejemplo:

- actual: `4.8%`
- target: `5.2%`
- delta: `0.4%`
- si `min_trade_weight=1%`, no hace nada

### 5. Genera salidas

- `target_weights.csv` → cartera objetivo
- `orders_delta.csv` → cambios vs cartera actual

---

## Recomendación práctica de parámetros

Para empezar:

- `topk = 20`
- `buffer_names = 10`
- `max_weight = 0.10`
- `min_trade_weight = 0.01`

Si ves demasiada rotación:

- sube `buffer_names` a `15`
- sube `min_trade_weight` a `0.015` o `0.02`

---

## Dos mejoras que yo haría después

La primera sería **pesar por score**, no equal weight.

Ejemplo:

- convertir score a pesos proporcionales
- luego cap por nombre
- luego renormalizar

La segunda sería usar también:

- liquidez mínima
- ADV mínimo
- precio mínimo
- exclusión de símbolos demasiado volátiles ese día

---

## Un detalle importante del script

Hay una simplificación en `select_with_buffer`: el buffer protege nombres actuales, pero no implementa todavía una lógica muy fina de “rank de salida” y “rank de entrada” separada. Funciona bien como primera versión, pero si quieres una implementación más seria, yo pasaría a una regla tipo:

- entrar solo si rank <= `entry_rank`
- mantener mientras rank <= `hold_rank`

Eso suele ser mejor que un único `topk + buffer`.

La siguiente versión que te recomendaría es justo esa: **entry/hold buffer estilo top-k dropout más realista**.

Adelante

Sí. Yo pasaría de `topk + buffer_names` a una regla **entry / hold** más parecida a la lógica real de cartera:
• **entrar** solo si el valor está muy arriba en el ranking
• **mantener** una posición actual mientras no caiga demasiado
• **salir** cuando ya no cumple el umbral de mantenimiento
Eso encaja bastante bien con la idea de `TopkDropoutStrategy`: Qlib define `topk` como número de posiciones y `n_drop` como el número de nombres que se reemplazan en cada fecha; además, la implementación oficial también contempla `hold_thresh`, `only_tradable` y `forbid_all_trade_at_limit`, o sea que la lógica de cartera en Qlib ya va por la línea de combinar ranking con restricciones operativas. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/component/strategy.rst))
**Regla que usaría**
Con `topk=20`, por ejemplo:
• **entry_rank = 20**
Si no lo tienes, solo entra si está en el top 20.
• **hold_rank = 30**
Si ya lo tienes, lo mantienes mientras siga en el top 30.
• **exit**
Si ya lo tienes pero cae por debajo de 30, sale.
Eso reduce bastante la rotación frente a “top 20 puro”, pero sigue siendo muy interpretable.
**Script mejorado**
Este reemplaza la parte de selección y turnover por una lógica más seria:

`from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

def load_scores(scores_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(scores_path)
    required = {"datetime", "instrument", "score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en scores: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df

def load_excluded(excluded_path: Path | None) -> set[str]:
    if excluded_path is None or not excluded_path.exists():
        return set()

    df = pd.read_csv(excluded_path)
    if "symbol" not in df.columns:
        raise ValueError("excluded_symbols.csv debe tener columna 'symbol'")

    return set(df["symbol"].astype(str).str.upper())

def load_current_positions(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["instrument", "current_weight"])

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError("current_positions debe ser csv o parquet")

    required = {"instrument", "current_weight"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en current_positions: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["current_weight"] = pd.to_numeric(df["current_weight"], errors="coerce").fillna(0.0)
    return df[["instrument", "current_weight"]]

def rank_scores(latest: pd.DataFrame) -> pd.DataFrame:
    latest = latest.sort_values("score", ascending=False).reset_index(drop=True).copy()
    latest["rank"] = range(1, len(latest) + 1)
    return latest

def select_entry_hold(
    latest: pd.DataFrame,
    current_positions: pd.DataFrame,
    topk: int,
    entry_rank: int,
    hold_rank: int,
) -> pd.DataFrame:
    if entry_rank > hold_rank:
        raise ValueError("entry_rank no puede ser mayor que hold_rank")

    current_set = set(current_positions["instrument"])
    latest = rank_scores(latest)

    # 1) Mantener posiciones actuales que sigan dentro de hold_rank
    keep = latest[
        latest["instrument"].isin(current_set) & (latest["rank"] <= hold_rank)
    ].copy()

    # 2) Nuevas entradas solo desde entry_rank
    new_entries = latest[
        ~latest["instrument"].isin(set(keep["instrument"])) & (latest["rank"] <= entry_rank)
    ].copy()

    # 3) Completar hasta topk
    selected = pd.concat([keep, new_entries], ignore_index=True)
    selected = selected.sort_values("score", ascending=False).drop_duplicates("instrument")

    if len(selected) < topk:
        fallback = latest[~latest["instrument"].isin(set(selected["instrument"]))].copy()
        selected = pd.concat([selected, fallback], ignore_index=True)
        selected = selected.drop_duplicates("instrument").sort_values("score", ascending=False)

    return selected.head(topk).copy()

def build_score_weight_targets(
    selected: pd.DataFrame,
    max_weight: float,
    score_power: float = 1.0,
) -> pd.DataFrame:
    selected = selected.copy()

    if selected.empty:
        selected["target_weight"] = pd.Series(dtype=float)
        return selected

    # Shift para evitar pesos negativos si hubiera scores negativos
    min_score = selected["score"].min()
    shifted = selected["score"] - min_score + 1e-12
    raw = shifted ** score_power

    if raw.sum() <= 0:
        selected["target_weight"] = 1.0 / len(selected)
    else:
        selected["target_weight"] = raw / raw.sum()

    # cap iterativo simple
    remaining = selected.index.tolist()
    final_weights = pd.Series(0.0, index=selected.index)
    leftover = 1.0

    while remaining:
        base = selected.loc[remaining, "target_weight"]
        base = base / base.sum() * leftover

        capped = base.clip(upper=max_weight)
        final_weights.loc[remaining] = capped

        fixed = capped[capped >= max_weight - 1e-12].index.tolist()
        if not fixed:
            break

        leftover = 1.0 - final_weights.sum()
        remaining = [i for i in remaining if i not in fixed]

        if leftover <= 1e-12:
            break

    not_fixed = final_weights == 0
    if not_fixed.any():
        base = selected.loc[not_fixed, "target_weight"]
        base = base / base.sum() * (1.0 - final_weights.sum())
        final_weights.loc[not_fixed] = base

    selected["target_weight"] = final_weights / final_weights.sum()
    return selected

def apply_turnover_floor(
    target_df: pd.DataFrame,
    current_positions: pd.DataFrame,
    min_trade_weight: float,
) -> pd.DataFrame:
    merged = target_df.merge(current_positions, on="instrument", how="left")
    merged["current_weight"] = merged["current_weight"].fillna(0.0)
    merged["delta_weight"] = merged["target_weight"] - merged["current_weight"]

    # si el cambio es muy pequeño, no lo tocamos
    small_change = merged["delta_weight"].abs() < min_trade_weight
    merged.loc[small_change, "target_weight"] = merged.loc[small_change, "current_weight"]

    total = merged["target_weight"].sum()
    if total > 0:
        merged["target_weight"] = merged["target_weight"] / total

    merged["delta_weight"] = merged["target_weight"] - merged["current_weight"]
    return merged

def add_exits(
    target_df: pd.DataFrame,
    current_positions: pd.DataFrame,
    dt: pd.Timestamp,
) -> pd.DataFrame:
    target_names = set(target_df["instrument"])
    exits = current_positions[~current_positions["instrument"].isin(target_names)].copy()

    if exits.empty:
        base = target_df.copy()
        if "current_weight" not in base.columns:
            base["current_weight"] = 0.0
        if "delta_weight" not in base.columns:
            base["delta_weight"] = base["target_weight"] - base["current_weight"]
        return base

    exits["datetime"] = dt
    exits["score"] = pd.NA
    exits["rank"] = pd.NA
    exits["target_weight"] = 0.0
    exits["delta_weight"] = -exits["current_weight"]

    base = target_df.copy()
    if "current_weight" not in base.columns:
        base["current_weight"] = 0.0
    if "delta_weight" not in base.columns:
        base["delta_weight"] = base["target_weight"] - base["current_weight"]

    cols = [
        "datetime",
        "instrument",
        "score",
        "rank",
        "current_weight",
        "target_weight",
        "delta_weight",
    ]
    return pd.concat([base[cols], exits[cols]], ignore_index=True)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", required=True)
    parser.add_argument("--output-targets", required=True)
    parser.add_argument("--output-orders", required=True)
    parser.add_argument("--excluded-symbols", default=None)
    parser.add_argument("--current-positions", default=None)
    parser.add_argument("--topk", type=int, default=20)
    parser.add_argument("--entry-rank", type=int, default=20)
    parser.add_argument("--hold-rank", type=int, default=30)
    parser.add_argument("--max-weight", type=float, default=0.10)
    parser.add_argument("--min-trade-weight", type=float, default=0.01)
    parser.add_argument("--score-power", type=float, default=1.0)
    args = parser.parse_args()

    scores_path = Path(args.scores).expanduser().resolve()
    output_targets = Path(args.output_targets).expanduser().resolve()
    output_orders = Path(args.output_orders).expanduser().resolve()
    excluded_path = Path(args.excluded_symbols).expanduser().resolve() if args.excluded_symbols else None
    current_positions_path = Path(args.current_positions).expanduser().resolve() if args.current_positions else None

    scores = load_scores(scores_path)
    excluded = load_excluded(excluded_path)
    current_positions = load_current_positions(current_positions_path)

    latest_dt = scores["datetime"].max()
    latest = scores[scores["datetime"] == latest_dt].copy()

    if excluded:
        latest = latest[~latest["instrument"].isin(excluded)].copy()

    selected = select_entry_hold(
        latest=latest,
        current_positions=current_positions,
        topk=args.topk,
        entry_rank=args.entry_rank,
        hold_rank=args.hold_rank,
    )

    targets = build_score_weight_targets(
        selected=selected,
        max_weight=args.max_weight,
        score_power=args.score_power,
    )
    targets["datetime"] = latest_dt

    targets = apply_turnover_floor(
        target_df=targets,
        current_positions=current_positions,
        min_trade_weight=args.min_trade_weight,
    )

    orders = add_exits(
        target_df=targets,
        current_positions=current_positions,
        dt=latest_dt,
    )

    output_targets.parent.mkdir(parents=True, exist_ok=True)
    output_orders.parent.mkdir(parents=True, exist_ok=True)

    targets[
        ["datetime", "instrument", "score", "rank", "current_weight", "target_weight", "delta_weight"]
    ].to_csv(output_targets, index=False)

    orders[
        ["datetime", "instrument", "score", "rank", "current_weight", "target_weight", "delta_weight"]
    ].to_csv(output_orders, index=False)

    print(f"[OK] Targets guardados en: {output_targets}")
    print(f"[OK] Orders guardadas en: {output_orders}")

if __name__ == "__main__":
    main()`

**Qué cambia respecto a la versión anterior**
Antes hacías algo como “top 20 + buffer 10”.
Ahora haces esto:
• si **ya lo tienes** y sigue con `rank <= hold_rank`, se puede quedar
• si **no lo tienes**, solo entra con `rank <= entry_rank`
• luego rellenas hasta `topk`
Eso suele dar una cartera bastante más estable.
**Parámetros que usaría al empezar**
Para una cartera de 20 nombres:
• `topk = 20`
• `entry_rank = 20`
• `hold_rank = 30`
• `max_weight = 0.10`
• `min_trade_weight = 0.01`
• `score_power = 1.0`
Comando:

`python build_target_weights.py \
  --scores ~/qlib_workspace/signals/predictions/latest_scores.parquet \
  --output-targets ~/qlib_workspace/signals/orders/target_weights.csv \
  --output-orders ~/qlib_workspace/signals/orders/orders_delta.csv \
  --excluded-symbols ~/qlib_workspace/logs/dataset_guard/excluded_symbols.csv \
  --current-positions ~/qlib_workspace/live/current_positions.csv \
  --topk 20 \
  --entry-rank 20 \
  --hold-rank 30 \
  --max-weight 0.10 \
  --min-trade-weight 0.01 \
  --score-power 1.0`

**Cómo pensarlo**
Un ejemplo simple:
• hoy tienes `AAPL` en cartera y baja de rank 12 a rank 26
→ con top 20 puro la venderías
→ con `hold_rank=30` la mantienes
• `TSLA` no está en cartera y sube a rank 24
→ no entra todavía
• `META` no está en cartera y sube a rank 14
→ sí entra
Eso reduce bastante el “flip-flop” diario.
**Dos mejoras útiles**
La primera sería usar **ADV/liquidez** aquí mismo, no solo en el dataset guard.
La segunda sería convertir `current_weight` en **posición real + cash + precios** para generar órdenes en importe o acciones, no solo en pesos.
Si quieres, el siguiente paso bueno es dejarte una versión que además aplique **filtro de liquidez/ADV** antes de construir la cartera.

Adelante

Perfecto. Yo lo haría **antes de seleccionar `entry/hold`**, filtrando el universo elegible por liquidez. En Qlib tiene sentido porque la capa de estrategia está pensada para que puedas personalizar la generación de posiciones objetivo, y `TopkDropoutStrategy` es solo una implementación base; además, Qlib documenta la actualización automática diaria y también ofrece chequeos de salud del dataset, así que meter un filtro adicional de elegibilidad en tu pipeline encaja muy bien con su flujo. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/component/strategy.rst))

La versión práctica que te recomiendo es:

- calcular **ADV20** = media de `close * volume` de 20 sesiones
- exigir también **precio mínimo**
- exigir **volumen medio mínimo**
- opcionalmente excluir símbolos con demasiados días faltantes recientes

Como Qlib trabaja con OHLCV básicos en el dataset y su capa de datos está pensada para construir features y filtros a partir de ahí, este enfoque encaja bien aunque tú lo implementes fuera de la estrategia, en `build_target_weights.py`. ([Qlib Documentation](https://qlib.readthedocs.io/en/latest/component/data.html))

## Cambio de diseño

Tu pipeline quedaría así:

1. `dataset_guard.py`
2. `run_inference_lgb_alpha158.py`
3. `build_target_weights.py`
    - carga scores
    - excluye `excluded_symbols.csv`
    - **aplica filtro de liquidez**
    - luego hace `entry/hold`
    - luego pesos
    - luego órdenes

## Script mejorado

Te dejo una versión de `build_target_weights.py` con filtro de liquidez usando tus CSV raw de Yahoo.

```python
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

def load_scores(scores_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(scores_path)
    required = {"datetime", "instrument", "score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en scores: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df

def load_excluded(excluded_path: Path | None) -> set[str]:
    if excluded_path is None or not excluded_path.exists():
        return set()

    df = pd.read_csv(excluded_path)
    if "symbol" not in df.columns:
        raise ValueError("excluded_symbols.csv debe tener columna 'symbol'")

    return set(df["symbol"].astype(str).str.upper())

def load_current_positions(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["instrument", "current_weight"])

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        raise ValueError("current_positions debe ser csv o parquet")

    required = {"instrument", "current_weight"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en current_positions: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["current_weight"] = pd.to_numeric(df["current_weight"], errors="coerce").fillna(0.0)
    return df[["instrument", "current_weight"]]

def load_symbol_csv(csv_dir: Path, symbol: str) -> pd.DataFrame:
    path = csv_dir / f"{symbol.upper()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    df = pd.read_csv(path)
    required = {"date", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} sin columnas requeridas: {sorted(missing)}")

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
    return df

def build_liquidity_snapshot(
    instruments: list[str],
    csv_dir: Path,
    asof_date: pd.Timestamp,
    adv_window: int,
    vol_window: int,
) -> pd.DataFrame:
    rows = []

    for symbol in instruments:
        try:
            df = load_symbol_csv(csv_dir, symbol)
            df = df[df["date"] <= asof_date].copy()

            if df.empty:
                rows.append(
                    {
                        "instrument": symbol,
                        "last_close": np.nan,
                        "adv": np.nan,
                        "avg_volume": np.nan,
                        "last_volume": np.nan,
                        "liquidity_ok": False,
                        "liquidity_reason": "no_history",
                    }
                )
                continue

            df["dollar_volume"] = df["close"] * df["volume"]

            tail_adv = df.tail(adv_window)
            tail_vol = df.tail(vol_window)

            last_close = df["close"].iloc[-1]
            last_volume = df["volume"].iloc[-1]
            adv = tail_adv["dollar_volume"].mean() if len(tail_adv) else np.nan
            avg_volume = tail_vol["volume"].mean() if len(tail_vol) else np.nan

            rows.append(
                {
                    "instrument": symbol,
                    "last_close": float(last_close) if pd.notna(last_close) else np.nan,
                    "adv": float(adv) if pd.notna(adv) else np.nan,
                    "avg_volume": float(avg_volume) if pd.notna(avg_volume) else np.nan,
                    "last_volume": float(last_volume) if pd.notna(last_volume) else np.nan,
                }
            )
        except Exception as e:
            rows.append(
                {
                    "instrument": symbol,
                    "last_close": np.nan,
                    "adv": np.nan,
                    "avg_volume": np.nan,
                    "last_volume": np.nan,
                    "liquidity_ok": False,
                    "liquidity_reason": f"load_error:{e}",
                }
            )

    return pd.DataFrame(rows)

def apply_liquidity_filter(
    latest: pd.DataFrame,
    csv_dir: Path | None,
    min_price: float,
    min_adv: float,
    min_avg_volume: float,
    keep_current_positions: pd.DataFrame,
    adv_window: int = 20,
    vol_window: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if csv_dir is None:
        latest = latest.copy()
        latest["liquidity_ok"] = True
        latest["liquidity_reason"] = ""
        return latest, pd.DataFrame(columns=["instrument", "liquidity_reason"])

    asof_date = pd.Timestamp(latest["datetime"].max()).normalize()
    current_set = set(keep_current_positions["instrument"])

    liq = build_liquidity_snapshot(
        instruments=sorted(latest["instrument"].unique()),
        csv_dir=csv_dir,
        asof_date=asof_date,
        adv_window=adv_window,
        vol_window=vol_window,
    )

    merged = latest.merge(liq, on="instrument", how="left")

    def classify_row(row: pd.Series) -> tuple[bool, str]:
        reasons = []

        if pd.isna(row["last_close"]):
            reasons.append("missing_close")
        elif row["last_close"] < min_price:
            reasons.append(f"price<{min_price}")

        if pd.isna(row["adv"]):
            reasons.append("missing_adv")
        elif row["adv"] < min_adv:
            reasons.append(f"adv<{min_adv}")

        if pd.isna(row["avg_volume"]):
            reasons.append("missing_avg_volume")
        elif row["avg_volume"] < min_avg_volume:
            reasons.append(f"avg_volume<{min_avg_volume}")

        # Si ya está en cartera, puedes ser un poco más permisivo:
        # solo bloqueamos si falla 2 o más condiciones duras.
        if row["instrument"] in current_set:
            hard_fail = len(reasons) >= 2
            return (not hard_fail), "|".join(reasons)

        return (len(reasons) == 0), "|".join(reasons)

    status = merged.apply(classify_row, axis=1, result_type="expand")
    merged["liquidity_ok"] = status[0]
    merged["liquidity_reason"] = status[1]

    excluded = merged.loc[~merged["liquidity_ok"], ["instrument", "liquidity_reason"]].drop_duplicates()
    filtered = merged[merged["liquidity_ok"]].copy()

    return filtered, excluded

def rank_scores(latest: pd.DataFrame) -> pd.DataFrame:
    latest = latest.sort_values("score", ascending=False).reset_index(drop=True).copy()
    latest["rank"] = range(1, len(latest) + 1)
    return latest

def select_entry_hold(
    latest: pd.DataFrame,
    current_positions: pd.DataFrame,
    topk: int,
    entry_rank: int,
    hold_rank: int,
) -> pd.DataFrame:
    if entry_rank > hold_rank:
        raise ValueError("entry_rank no puede ser mayor que hold_rank")

    current_set = set(current_positions["instrument"])
    latest = rank_scores(latest)

    keep = latest[
        latest["instrument"].isin(current_set) & (latest["rank"] <= hold_rank)
    ].copy()

    new_entries = latest[
        ~latest["instrument"].isin(set(keep["instrument"])) & (latest["rank"] <= entry_rank)
    ].copy()

    selected = pd.concat([keep, new_entries], ignore_index=True)
    selected = selected.sort_values("score", ascending=False).drop_duplicates("instrument")

    if len(selected) < topk:
        fallback = latest[~latest["instrument"].isin(set(selected["instrument"]))].copy()
        selected = pd.concat([selected, fallback], ignore_index=True)
        selected = selected.drop_duplicates("instrument").sort_values("score", ascending=False)

    return selected.head(topk).copy()

def build_score_weight_targets(
    selected: pd.DataFrame,
    max_weight: float,
    score_power: float = 1.0,
) -> pd.DataFrame:
    selected = selected.copy()

    if selected.empty:
        selected["target_weight"] = pd.Series(dtype=float)
        return selected

    min_score = selected["score"].min()
    shifted = selected["score"] - min_score + 1e-12
    raw = shifted ** score_power

    if raw.sum() <= 0:
        selected["target_weight"] = 1.0 / len(selected)
    else:
        selected["target_weight"] = raw / raw.sum()

    remaining = selected.index.tolist()
    final_weights = pd.Series(0.0, index=selected.index)
    leftover = 1.0

    while remaining:
        base = selected.loc[remaining, "target_weight"]
        base = base / base.sum() * leftover
        capped = base.clip(upper=max_weight)
        final_weights.loc[remaining] = capped

        fixed = capped[capped >= max_weight - 1e-12].index.tolist()
        if not fixed:
            break

        leftover = 1.0 - final_weights.sum()
        remaining = [i for i in remaining if i not in fixed]

        if leftover <= 1e-12:
            break

    not_fixed = final_weights == 0
    if not_fixed.any():
        base = selected.loc[not_fixed, "target_weight"]
        base = base / base.sum() * (1.0 - final_weights.sum())
        final_weights.loc[not_fixed] = base

    selected["target_weight"] = final_weights / final_weights.sum()
    return selected

def apply_turnover_floor(
    target_df: pd.DataFrame,
    current_positions: pd.DataFrame,
    min_trade_weight: float,
) -> pd.DataFrame:
    merged = target_df.merge(current_positions, on="instrument", how="left")
    merged["current_weight"] = merged["current_weight"].fillna(0.0)
    merged["delta_weight"] = merged["target_weight"] - merged["current_weight"]

    small_change = merged["delta_weight"].abs() < min_trade_weight
    merged.loc[small_change, "target_weight"] = merged.loc[small_change, "current_weight"]

    total = merged["target_weight"].sum()
    if total > 0:
        merged["target_weight"] = merged["target_weight"] / total

    merged["delta_weight"] = merged["target_weight"] - merged["current_weight"]
    return merged

def add_exits(
    target_df: pd.DataFrame,
    current_positions: pd.DataFrame,
    dt: pd.Timestamp,
) -> pd.DataFrame:
    target_names = set(target_df["instrument"])
    exits = current_positions[~current_positions["instrument"].isin(target_names)].copy()

    base = target_df.copy()
    if "current_weight" not in base.columns:
        base["current_weight"] = 0.0
    if "delta_weight" not in base.columns:
        base["delta_weight"] = base["target_weight"] - base["current_weight"]

    if exits.empty:
        return base

    exits["datetime"] = dt
    exits["score"] = pd.NA
    exits["rank"] = pd.NA
    exits["target_weight"] = 0.0
    exits["delta_weight"] = -exits["current_weight"]

    cols = [
        "datetime", "instrument", "score", "rank",
        "current_weight", "target_weight", "delta_weight"
    ]
    return pd.concat([base[cols], exits[cols]], ignore_index=True)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", required=True)
    parser.add_argument("--output-targets", required=True)
    parser.add_argument("--output-orders", required=True)
    parser.add_argument("--output-liquidity-excluded", required=True)
    parser.add_argument("--excluded-symbols", default=None)
    parser.add_argument("--current-positions", default=None)
    parser.add_argument("--raw-csv-dir", default=None)

    parser.add_argument("--topk", type=int, default=20)
    parser.add_argument("--entry-rank", type=int, default=20)
    parser.add_argument("--hold-rank", type=int, default=30)
    parser.add_argument("--max-weight", type=float, default=0.10)
    parser.add_argument("--min-trade-weight", type=float, default=0.01)
    parser.add_argument("--score-power", type=float, default=1.0)

    parser.add_argument("--min-price", type=float, default=5.0)
    parser.add_argument("--min-adv", type=float, default=10_000_000.0)
    parser.add_argument("--min-avg-volume", type=float, default=200_000.0)
    parser.add_argument("--adv-window", type=int, default=20)
    parser.add_argument("--vol-window", type=int, default=20)

    args = parser.parse_args()

    scores_path = Path(args.scores).expanduser().resolve()
    output_targets = Path(args.output_targets).expanduser().resolve()
    output_orders = Path(args.output_orders).expanduser().resolve()
    output_liq_excluded = Path(args.output_liquidity_excluded).expanduser().resolve()
    excluded_path = Path(args.excluded_symbols).expanduser().resolve() if args.excluded_symbols else None
    current_positions_path = Path(args.current_positions).expanduser().resolve() if args.current_positions else None
    raw_csv_dir = Path(args.raw_csv_dir).expanduser().resolve() if args.raw_csv_dir else None

    scores = load_scores(scores_path)
    excluded = load_excluded(excluded_path)
    current_positions = load_current_positions(current_positions_path)

    latest_dt = scores["datetime"].max()
    latest = scores[scores["datetime"] == latest_dt].copy()

    if excluded:
        latest = latest[~latest["instrument"].isin(excluded)].copy()

    latest, liq_excluded = apply_liquidity_filter(
        latest=latest,
        csv_dir=raw_csv_dir,
        min_price=args.min_price,
        min_adv=args.min_adv,
        min_avg_volume=args.min_avg_volume,
        keep_current_positions=current_positions,
        adv_window=args.adv_window,
        vol_window=args.vol_window,
    )

    selected = select_entry_hold(
        latest=latest,
        current_positions=current_positions,
        topk=args.topk,
        entry_rank=args.entry_rank,
        hold_rank=args.hold_rank,
    )

    targets = build_score_weight_targets(
        selected=selected,
        max_weight=args.max_weight,
        score_power=args.score_power,
    )
    targets["datetime"] = latest_dt

    targets = apply_turnover_floor(
        target_df=targets,
        current_positions=current_positions,
        min_trade_weight=args.min_trade_weight,
    )

    orders = add_exits(
        target_df=targets,
        current_positions=current_positions,
        dt=latest_dt,
    )

    output_targets.parent.mkdir(parents=True, exist_ok=True)
    output_orders.parent.mkdir(parents=True, exist_ok=True)
    output_liq_excluded.parent.mkdir(parents=True, exist_ok=True)

    targets[
        ["datetime", "instrument", "score", "rank", "current_weight", "target_weight", "delta_weight"]
    ].to_csv(output_targets, index=False)

    orders[
        ["datetime", "instrument", "score", "rank", "current_weight", "target_weight", "delta_weight"]
    ].to_csv(output_orders, index=False)

    liq_excluded.to_csv(output_liq_excluded, index=False)

    print(f"[OK] Targets guardados en: {output_targets}")
    print(f"[OK] Orders guardadas en: {output_orders}")
    print(f"[OK] Exclusiones por liquidez en: {output_liq_excluded}")

if __name__ == "__main__":
    main()
```

## Cómo lo usaría

```bash
python build_target_weights.py \
  --scores ~/qlib_workspace/signals/predictions/latest_scores.parquet \
  --output-targets ~/qlib_workspace/signals/orders/target_weights.csv \
  --output-orders ~/qlib_workspace/signals/orders/orders_delta.csv \
  --output-liquidity-excluded ~/qlib_workspace/signals/orders/liquidity_excluded.csv \
  --excluded-symbols ~/qlib_workspace/logs/dataset_guard/excluded_symbols.csv \
  --current-positions ~/qlib_workspace/live/current_positions.csv \
  --raw-csv-dir ~/qlib_workspace/data/live_us/raw_yahoo \
  --topk 20 \
  --entry-rank 20 \
  --hold-rank 30 \
  --max-weight 0.10 \
  --min-trade-weight 0.01 \
  --score-power 1.0 \
  --min-price 5 \
  --min-adv 10000000 \
  --min-avg-volume 200000
```

## Parámetros que pondría al empezar

Para US equities, de entrada usaría algo así:

- `min_price = 5`
- `min_adv = 10M`
- `min_avg_volume = 200k`

Si quieres algo más conservador:

- `min_price = 10`
- `min_adv = 20M`
- `min_avg_volume = 500k`

## Mi criterio práctico

Yo haría esta distinción:

- **nombres nuevos**: filtro duro
- **posiciones actuales**: filtro algo más permisivo

Eso evita ventas innecesarias por una sola sesión rara de volumen, pero bloquea bien entradas nuevas poco líquidas.

## Qué gana esta versión

Ahora mismo ya tienes:

- exclusión por calidad de datos
- exclusión por anomalías
- exclusión por liquidez
- selección `entry/hold`
- turnover floor
- pesos capados

Eso ya se parece bastante más a una cartera operable.

## El siguiente paso bueno

El siguiente salto natural sería convertir `current_weight` a **posición real del broker + cash + precio actual** para sacar **órdenes en dólares o número de acciones**, no solo en pesos. Qlib separa claramente la investigación de la capa de ejecución/portfolio, así que mantener esta traducción fuera del modelo y cerca del ejecutor suele ser una buena arquitectura. ([GitHub](https://github.com/microsoft/qlib/blob/main/docs/component/strategy.rst))

Adelante

Claro. Te dejo una versión para pasar de **pesos objetivo** a **órdenes ejecutables** en:

- **importe** (`notional`)
- **acciones** (`shares`)

usando:

- posiciones reales del broker
- cash disponible
- precios actuales

## Idea

Partimos de:

- `target_weights.csv` con `instrument,target_weight`
- `broker_positions.csv` con `instrument,shares`
- `latest_prices.csv` con `instrument,price`
- `portfolio_cash.csv` con el cash disponible

Y calculamos:

1. **equity total** = valor posiciones + cash
2. **target_notional** = `target_weight * equity_total`
3. **current_notional** = `shares * price`
4. **delta_notional** = target - current
5. **order_shares** = `delta_notional / price`
6. redondeo a acciones enteras
7. filtro por mínimo tamaño de orden

---

# Script: `build_broker_orders.py`

```python
from __future__ import annotations

import argparse
from pathlib import Path
import math
import pandas as pd

def load_targets(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"instrument", "target_weight"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en targets: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["target_weight"] = pd.to_numeric(df["target_weight"], errors="coerce").fillna(0.0)
    return df[["instrument", "target_weight"]]

def load_positions(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"instrument", "shares"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en broker_positions: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["shares"] = pd.to_numeric(df["shares"], errors="coerce").fillna(0.0)
    return df[["instrument", "shares"]]

def load_prices(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"instrument", "price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en latest_prices: {sorted(missing)}")

    df = df.copy()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["price"])
    df = df[df["price"] > 0]
    return df[["instrument", "price"]]

def load_cash(path: Path) -> float:
    df = pd.read_csv(path)
    if "cash" not in df.columns:
        raise ValueError("portfolio_cash.csv debe tener columna 'cash'")
    cash = pd.to_numeric(df["cash"], errors="coerce").dropna()
    if cash.empty:
        raise ValueError("No se pudo leer cash")
    return float(cash.iloc[0])

def round_shares(x: float) -> int:
    if x > 0:
        return math.floor(x)
    if x < 0:
        return math.ceil(x)
    return 0

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--broker-positions", required=True)
    parser.add_argument("--latest-prices", required=True)
    parser.add_argument("--portfolio-cash", required=True)
    parser.add_argument("--output-orders", required=True)
    parser.add_argument("--output-reconciliation", required=True)
    parser.add_argument("--min-order-notional", type=float, default=100.0)
    parser.add_argument("--min-order-shares", type=int, default=1)
    args = parser.parse_args()

    targets = load_targets(Path(args.targets).expanduser().resolve())
    positions = load_positions(Path(args.broker_positions).expanduser().resolve())
    prices = load_prices(Path(args.latest_prices).expanduser().resolve())
    cash = load_cash(Path(args.portfolio_cash).expanduser().resolve())

    universe = (
        pd.DataFrame(
            {
                "instrument": sorted(
                    set(targets["instrument"]) |
                    set(positions["instrument"]) |
                    set(prices["instrument"])
                )
            }
        )
    )

    df = (
        universe
        .merge(targets, on="instrument", how="left")
        .merge(positions, on="instrument", how="left")
        .merge(prices, on="instrument", how="left")
    )

    df["target_weight"] = df["target_weight"].fillna(0.0)
    df["shares"] = df["shares"].fillna(0.0)

    # Solo podremos operar nombres con precio válido
    tradable = df["price"].notna() & (df["price"] > 0)

    df["current_notional"] = df["shares"] * df["price"]
    current_gross = df.loc[tradable, "current_notional"].fillna(0.0).sum()
    equity_total = current_gross + cash

    if equity_total <= 0:
        raise ValueError("Equity total no positiva")

    df["target_notional"] = df["target_weight"] * equity_total
    df["delta_notional"] = df["target_notional"] - df["current_notional"]

    df["raw_order_shares"] = df["delta_notional"] / df["price"]
    df.loc[~tradable, "raw_order_shares"] = 0.0

    df["order_shares"] = df["raw_order_shares"].apply(round_shares)
    df["order_notional"] = df["order_shares"] * df["price"]

    # filtros mínimos
    too_small = (
        df["order_notional"].abs() < args.min_order_notional
    ) | (
        df["order_shares"].abs() < args.min_order_shares
    )
    df.loc[too_small, "order_shares"] = 0
    df.loc[too_small, "order_notional"] = 0.0

    df["side"] = ""
    df.loc[df["order_shares"] > 0, "side"] = "BUY"
    df.loc[df["order_shares"] < 0, "side"] = "SELL"

    # cartera estimada tras órdenes
    df["post_shares"] = df["shares"] + df["order_shares"]
    df["post_notional"] = df["post_shares"] * df["price"]

    traded_notional = df["order_notional"].sum()
    # BUY consume cash (+), SELL libera cash (-) porque order_notional de sell es negativo
    est_cash_after = cash - traded_notional
    est_equity_after = df["post_notional"].fillna(0.0).sum() + est_cash_after
    df["post_weight"] = df["post_notional"] / est_equity_after if est_equity_after > 0 else 0.0
    df["weight_error"] = df["post_weight"] - df["target_weight"]

    orders = df[df["order_shares"] != 0].copy()
    orders = orders[
        [
            "instrument",
            "side",
            "price",
            "shares",
            "target_weight",
            "current_notional",
            "target_notional",
            "delta_notional",
            "order_shares",
            "order_notional",
        ]
    ].sort_values(["side", "order_notional"], ascending=[True, False])

    reconciliation = df[
        [
            "instrument",
            "price",
            "shares",
            "post_shares",
            "target_weight",
            "post_weight",
            "weight_error",
            "current_notional",
            "target_notional",
            "order_shares",
            "order_notional",
        ]
    ].sort_values("target_weight", ascending=False)

    out_orders = Path(args.output_orders).expanduser().resolve()
    out_recon = Path(args.output_reconciliation).expanduser().resolve()
    out_orders.parent.mkdir(parents=True, exist_ok=True)
    out_recon.parent.mkdir(parents=True, exist_ok=True)

    orders.to_csv(out_orders, index=False)
    reconciliation.to_csv(out_recon, index=False)

    print(f"[OK] Equity total: {equity_total:,.2f}")
    print(f"[OK] Cash actual: {cash:,.2f}")
    print(f"[OK] Cash estimado tras órdenes: {est_cash_after:,.2f}")
    print(f"[OK] Orders guardadas en: {out_orders}")
    print(f"[OK] Reconciliation guardada en: {out_recon}")

if __name__ == "__main__":
    main()
```

---

# Formatos esperados

## `target_weights.csv`

```
instrument,target_weight
AAPL,0.10
MSFT,0.10
NVDA,0.08
AMZN,0.07
```

## `broker_positions.csv`

```
instrument,shares
AAPL,120
MSFT,85
QQQ,40
```

## `latest_prices.csv`

```
instrument,price
AAPL,212.45
MSFT,428.10
NVDA,118.32
AMZN,192.18
QQQ,503.77
```

## `portfolio_cash.csv`

```
cash
15432.78
```

---

# Uso

```bash
python build_broker_orders.py \
  --targets ~/qlib_workspace/signals/orders/target_weights.csv \
  --broker-positions ~/qlib_workspace/live/broker_positions.csv \
  --latest-prices ~/qlib_workspace/live/latest_prices.csv \
  --portfolio-cash ~/qlib_workspace/live/portfolio_cash.csv \
  --output-orders ~/qlib_workspace/live/orders_to_send.csv \
  --output-reconciliation ~/qlib_workspace/live/reconciliation.csv \
  --min-order-notional 100 \
  --min-order-shares 1
```

---

# Qué produce

## `orders_to_send.csv`

Lista limpia de órdenes:

- símbolo
- lado
- precio de referencia
- acciones a comprar/vender
- delta nocional

## `reconciliation.csv`

Sirve para revisar:

- peso objetivo
- peso estimado después de órdenes
- error residual

---

# Mejoras que yo haría justo después

La más importante es añadir:

- **buffer de cash**
- **comisiones/slippage**
- **redondeo por lotes** si tu broker lo necesita
- **prohibir ventas por debajo de cero**
- **priorización de ventas antes que compras**

## Buffer de cash

Muy útil dejar, por ejemplo, `1%` o `2%` en cash.

Se hace cambiando:

```python
df["target_notional"] = df["target_weight"] * equity_total
```

por algo así:

```python
investable_equity = equity_total * 0.98
df["target_notional"] = df["target_weight"] * investable_equity
```

## Costes

También puedes descontar un pequeño haircut:

```python
investable_equity = equity_total * 0.995
```

---

# Recomendación práctica

Para empezar:

- `cash buffer = 2%`
- `min_order_notional = 100` o `200`
- `min_order_shares = 1`

Y mantendría una regla simple:

- primero generar órdenes
- luego revisar `reconciliation.csv`
- solo después enviar al broker

El siguiente paso útil es dejarte una versión con:

- **cash buffer**
- **prioridad ventas > compras**
- **bloqueo de short accidental**
- **export ready para IBKR/CSV broker**