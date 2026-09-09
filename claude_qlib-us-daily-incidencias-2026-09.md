# Incidencias del pipeline US diario (Qlib)

> Documento reconstruido el 2026-09-09. El original con los Fallos 1-3 no se localizó en
> el sistema de ficheros; aquí solo se referencian de forma resumida, y se documenta en
> detalle el **Fallo 4**, diagnosticado y corregido en esta sesión.

## Índice de fallos

| # | Fallo | Estado |
|---|-------|--------|
| 1 | Dataset incoherente (agosto 2026) | Resuelto (ver documento original) |
| 2 | `BrokenProcessPool` por OOM en `dump_bin.py` | Documentado, sin resolver de raíz |
| 3 | (no recuperado del documento original) | Resuelto |
| 4 | Universo de símbolos circular en `USAllCollector` | **Resuelto — 2026-09-08** |

---

## Fallo 4 — El universo de símbolos solo podía encogerse

### Síntoma

`instruments/all.txt` había pasado de ~12.707 símbolos (backup del 14-ago) a **6.460**.
Habían desaparecido 6.307 símbolos con historial real de precios, incluyendo tickers
activos y líquidos hoy: `SOFI`, `RGTI`, `TUYA` no aparecían ni en `all.txt` ni en
`features/`, pese a cotizar con normalidad.

No era sesgo de supervivencia por quiebras: era una poda accidental, probablemente
relacionada con el Fallo 1 (dataset incoherente de agosto).

### Causa raíz

`USAllCollector` en `scripts/update_us_all.py` sobrescribía `get_instrument_list()` con
una implementación **circular**: leía el `instruments/all.txt` existente y lo filtraba por
`active_mask` (fechas `start_date`/`end_date` contra `US_ALL_EFFECTIVE_DATE`), sin
consultar ninguna fuente externa.

Consecuencia: el universo nunca podía crecer ni recuperar símbolos perdidos. Cualquier
poda accidental era permanente y se propagaba a todos los rebuilds posteriores.

La clase padre `YahooCollectorUS` (`scripts/data_collector/yahoo/collector.py:264`) ya
implementaba `get_instrument_list()` correctamente vía `get_us_stock_symbols()`
(`scripts/data_collector/utils.py:289`), que consulta NASDAQ Trader FTP
(`otherlisted.txt`, `nasdaqtraded.txt`), Eastmoney (vía `akshare`) y NYSE.
`YahooCollectorUS1d` hereda esto sin cambios. Solo `USAllCollector` lo rompía.

### Fix aplicado (2026-09-07)

**1. `scripts/update_us_all.py` — `USAllCollector.get_instrument_list()`**

Reemplazada la implementación circular por la unión de:

- el universo fresco de la fuente externa (`super().get_instrument_list()`), y
- el histórico ya presente en `instruments/all.txt`, para no perder las fechas
  point-in-time de las bajas ya registradas (coherente con el Parche B del S&P 500).

Se retiraron `US_ALL_EFFECTIVE_DATE` y `US_ALL_USE_ALL_SYMBOLS`, que solo se consumían en
el `active_mask` eliminado (verificado con `grep` sobre todo el repo). Se conservan
`US_ALL_INSTRUMENTS_SOURCE_DIR` y `US_ALL_INSTRUMENTS_DATA_DIR`. Se añadió una guarda que
aborta si el universo resultante queda vacío.

**2. `scripts/data_collector/utils.py` — `get_us_stock_symbols()`**

- `import akshare as ak` movido de la cabecera de la función a la primera línea de
  `_get_eastmoney()`, para que la ausencia de `akshare` no impida usar la vía
  NASDAQ/NYSE.
  *Nota: `akshare` 1.18.94 **sí** está instalado en el entorno conda `qlib`; el
  diagnóstico inicial se hizo con el `python3` del PATH base, que no lo tiene.*
- Añadida tolerancia a fallos por fuente (`_collect()`): si Eastmoney, NASDAQ o NYSE
  fallan, se registra un warning y se continúa con las demás; solo se aborta si ninguna
  devuelve símbolos. Antes, un fallo de Eastmoney reintentaba 5 veces (~80 min) y luego
  tiraba todo el universo, matando el rebuild aunque NASDAQ hubiera respondido bien.

### Backups

```
scripts/update_us_all.py.bak_20260907_181055
scripts/data_collector/utils.py.bak_20260907_18*
/home/toni/.qlib/qlib_data/us_data_backup_20260908_010103   (dataset previo, 6.460 símbolos)
```

### Validación

Llamada directa a la fuente tras el fix del import:

```
TOTAL 19420 símbolos — SOFI True, RGTI True, TUYA True
```

Test end-to-end del collector parcheado:

```
Universo: 19423 de fuente actual + 6460 historicos = 19579 total
SOFI True | RGTI True | TUYA True | AAPL True | ^GSPC True
```

Solo 156 de los 6.460 símbolos históricos no aparecen en la fuente externa (bajas reales
point-in-time), lo que confirma que la poda de agosto fue accidental y no supervivencia.

### Rebuild completo de validación (2026-09-08)

Lanzado por el cron a las 01:01, terminado a las 20:08 (**19 h 07 min**), con
`MAX_WORKERS=4` / `NORMALIZE_MAX_WORKERS=5`.

| Fase | Duración |
|------|----------|
| Construcción del universo | 13 min (01:01 → 01:14) |
| Descarga (19.579 símbolos) | 18 h 28 min (01:14 → 19:29) |
| Normalización | 11 min (19:29 → 19:40) |
| `dump_bin` (14.956 ficheros) | 28 min (19:40 → 20:08) |

Resultado:

| Métrica | Antes | Después |
|---------|-------|---------|
| `instruments/all.txt` | 6.460 | **14.956** (+8.496) |
| `features/` | 6.460 | **14.956** |
| `instruments/sp500.txt` | 1.177 | 1.180 |
| Tamaño del dataset | 1,1 GB | 1,5 GB |

`SOFI`, `RGTI` y `TUYA` recuperados, presentes en `all.txt` y en `features/`. Calendario
hasta 2026-09-04 (el 7-sep fue Labor Day, mercado cerrado). De los 19.579 símbolos del
universo, 14.956 tenían datos reales; el resto son delistados sin histórico en Yahoo.

**El Fallo 2 no se reprodujo**: `dump_bin` completó con 5 workers y la RAM disponible
nunca bajó de ~3,7 GB. Esta máquina tiene 15,8 GB de RAM y 2 GB de swap, no los 3,8 GB /
0 swap que asumía el diagnóstico del Fallo 2 — conviene revisar esa nota.

### Observaciones abiertas

- **`_get_nyse()` está roto**: devuelve `'NoneType' object has no attribute 'replace'` al
  parsear la respuesta de `nyse.com/api/quotes/filter`. Ya no es bloqueante (se ignora con
  warning), pero la fuente NYSE no aporta nada actualmente.
- **La fase Eastmoney añade ~13 min fijos** por ejecución (905 páginas vía `akshare`).
  NASDAQ cubre prácticamente el mismo universo; valorar una variable de entorno para
  omitirla.
- **`DJIA` y `SP400` no se generan** (`No suitable data source has been found!`). Es
  preexistente: tampoco existían en el dataset anterior.
- **Disco al 95%** (12 GB libres). Un rebuild completo necesita ~5 GB entre `source/`,
  `normalize/` y el dataset final, más el backup automático del dataset anterior.
- El backup `us_data_backup_20260814_112445.zip`, evidencia original de los 12.707
  símbolos, ya no está en `~/.qlib/backups/` (directorio vaciado el 2026-09-08).
- El cron del rebuild diario (`1 1 * * 2-6`) ya no figura en el crontab desde el
  2026-09-08; el rebuild del 2026-09-09 no se ejecutó.
