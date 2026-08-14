# Datos Collector Daily Yahoo — Mercado USA

> **Objetivo:** Descargar y preparar datos del mercado USA (S&P 500) desde Yahoo Finance para QLib
> **Fecha:** 30 Junio 2026
> **Config:** `config/workflow_baseline_lightgbm_alpha158_sp500_us.yaml`

---

## 📦 Opción 1: Dataset pre-empaquetado de QLib (recomendado para empezar)

El dataset pre-empaquetado de QLib para USA está disponible en su repositorio público.

**Comando:**

```bash
cd qlib
.venv/bin/python scripts/get_data.py qlib_data \
  --name qlib_data \
  --target_dir ~/.qlib/qlib_data/us_data \
  --interval 1d \
  --region us
```

**Rango de fechas:** El dataset cubre aproximadamente desde **2008-01-01 hasta 2023-2024** (dependiendo de cuándo se generó el paquete).

**Tiempo estimado:** 5-10 minutos (dependiendo de conexión).

**Provider URI resultante:** `~/.qlib/qlib_data/us_data`

---

## 🐍 Opción 2: Collector Yahoo Finance (datos frescos hasta el presente)

Si necesitas datos hasta la fecha actual o controlar la calidad, usa el collector de Yahoo.

### Paso 1 — Descargar datos raw

```bash
cd qlib
.venv/bin/python vendor/microsoft-qlib/scripts/data_collector/yahoo/collector.py download_data \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --start 2008-01-01 --end 2026-01-01 --delay 1 --interval 1d --region US
```

- `--start` / `--end`: rango de fechas deseado
- `--delay 1`: pausa de 1s entre requests para evitar rate limiting
- `--interval 1d`: datos diarios
- `--region US`: mercado USA
- Descarga datos CSV de cada ticker del S&P 500 históricamente

### Paso 2 — Normalizar datos

```bash
cd qlib
.venv/bin/python vendor/microsoft-qlib/scripts/data_collector/yahoo/collector.py normalize_data \
  --source_dir ~/.qlib/stock_data/source/us_data \
  --normalize_dir ~/.qlib/stock_data/source/us_1d_nor \
  --region US --interval 1d
```

Convierte los CSVs raw al formato normalizado que QLib necesita.

### Paso 3 — Convertir a formato binario QLib

```bash
cd qlib
.venv/bin/python vendor/microsoft-qlib/scripts/dump_bin.py dump_all \
  --data_path ~/.qlib/stock_data/source/us_1d_nor \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --freq day \
  --exclude_fields date,symbol \
  --file_suffix .csv
```

Convierte los CSV normalizados al formato binario QLib (features + calendars + instruments).

---

## 📊 Origen de los datos

Los datos provienen de **Yahoo Finance** (`finance.yahoo.com`). QLib utiliza la librería `yahooquery` para acceder a la API.

**Tickers del S&P 500:** Se obtienen desde Wikipedia:
- Fuente: `https://en.wikipedia.org/wiki/List_of_S%26P_500_companies`

---

## ⚠️ Consideraciones

| Factor | Dataset pre-empaquetado | Yahoo Collector |
|--------|:-----------------------:|:---------------:|
| **Esfuerzo** | Mínimo (1 comando) | Alto (~3 pasos, horas de descarga) |
| **Tiempo** | 5-10 min | 2-6 horas (hay ~500 tickers) |
| **Actualización** | Fecha fija del paquete | Hasta la fecha que especifiques |
| **Calidad** | Controlada por QLib | Depende de Yahoo Finance |
| **Rate limiting** | Ninguno | Riesgo de bloqueo IP |

**Recomendación:** Para empezar, usa el pre-empaquetado. Si luego necesitas datos frescos para operativa en vivo, migra al collector.

---

## 🔗 Provider URI

Nuestra config usa:
```yaml
qlib_init:
  provider_uri: ~/.qlib/qlib_data/us_data
  region: us
```

Alternativas:
- Proyecto local: `data/us_qlib/` (portable)
- Usuario global: `~/.qlib/qlib_data/us_data` (recomendado, más estable)

---

## 📋 Referencias

- **Código fuente:** `vendor/microsoft-qlib/scripts/data_collector/yahoo/collector.py`
- **Script de descarga:** `scripts/get_data.py` (wrappeo del GetData de QLib)
- **Guía de trading USA:** `docs/us-market-trading-plan.md`
- **Instrucciones de ejecución:** `04 Experiments/Ejecución Prioridad 1.md`
- **Roadmap general:** `04 Experiments/ROADMAP TRABAJO.md`

---

*Documento generado: 30 Junio 2026*
*Próximo paso: lanzar descarga de datos y ejecutar baseline SP500*
