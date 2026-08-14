# Calidad de los Datos de QLib

> **Objetivo:** Verificar la integridad, consistencia y calidad de los datos descargados para QLib
> **Fecha:** 30 Junio 2026

---

## 🔍 Herramienta oficial: `check_data_health.py`

QLib incluye un script específico para validar la calidad de los datos: `DataHealthChecker` en `vendor/microsoft-qlib/scripts/check_data_health.py`.

### Verificar datos en formato binario QLib (después del dump)

```bash
cd qlib
.venv/bin/python vendor/microsoft-qlib/scripts/check_data_health.py \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --freq day
```

Esto comprueba automáticamente:
- **Columnas OHLCV faltantes** (`open`, `high`, `low`, `close`, `volume`)
- **Datos missing** (gaps en la serie temporal)
- **Saltos anormales** en precio (>50%) o volumen (>3x) entre días consecutivos
- **Factores faltantes** en el dataset
- **Errores en nombres de archivos** (mayúsculas, minúsculas, caracteres especiales)

### Verificar datos CSV raw (antes del dump)

```bash
cd qlib
.venv/bin/python vendor/microsoft-qlib/scripts/check_data_health.py \
  --csv_path ~/.qlib/stock_data/source/us_1d_nor
```

---

## 🛠️ Verificación manual con Python

Para explorar el dataset más a fondo:

```python
cd qlib
.venv/bin/python -c "
import qlib
qlib.init(provider_uri='~/.qlib/qlib_data/us_data', region='us')
from qlib.data import D

# 1. Listar instituciones disponibles (SP500)
instruments = D.list_instruments(D.instruments('sp500'), as_list=True, freq='day')
print(f'Total tickers en SP500: {len(instruments)}')

# 2. Ver rango de fechas de un ticker concreto
if instruments:
    test_ticker = instruments[0]
    df = D.features([test_ticker], ['\$open', '\$close', '\$volume'], freq='day')
    print(f'Ticker: {test_ticker}')
    print(f'Rango: {df.index.get_level_values(1).min()} → {df.index.get_level_values(1).max()}')
    print(f'Filas totales: {len(df)}')
    print(df.head())

# 3. Ver cuántos datos missing hay por ticker
from qlib.data.dataset import DatasetH
from qlib.contrib.data.handler import Alpha158
print('Alpha158 handler: OK')
"
```

---

## 📊 Indicadores de calidad clave

| Indicador | Qué mide | Threshold de alerta |
|-----------|----------|:-------------------:|
| **Missing data** | % de días sin datos en un ticker | >5% del periodo |
| **Large step change (price)** | Cambio >=50% en un día | Cualquier ocurrencia (revisar split/dividendo) |
| **Large step change (volume)** | Cambio >=3x volumen diario | Revisar eventos corporativos |
| **Required columns** | OHLCV presentes | Cualquier columna faltante |
| **Missing factor** | Factores alpha158/360 presentes | Cualquier factor faltante |
| **File naming** | Nombres de archivo en minúsculas | Errores = problemas en Windows |

---

## ⚠️ Problemas comunes con datos de Yahoo Finance

| Problema | Causa | Solución |
|----------|-------|----------|
| **Gaps en fechas** | Días festivos USA no registrados | Verificar calendario de trading |
| **Saltos de precio** | Splits o dividendos no ajustados | Usar `adjust_price` en el collector |
| **Tickers desaparecidos** | Empresas eliminadas del SP500 | El collector de Wikipedia gestiona adds/removes |
| **Volumen a 0** | Días sin trading | Filtrar o imputar |
| **Errores 404** | Ticker ya no existe en Yahoo | El collector lo salta automáticamente |

---

## 🔗 Referencias

- **Script de health check:** `vendor/microsoft-qlib/scripts/check_data_health.py`
- **Script de dump validation:** `vendor/microsoft-qlib/scripts/check_dump_bin.py`
- **Guía de descarga:** `04 Experiments/Datos Collector Daily Yahoo.md`
- **Instrucciones de ejecución:** `04 Experiments/Ejecución Prioridad 1.md`

---

*Documento generado: 30 Junio 2026*
