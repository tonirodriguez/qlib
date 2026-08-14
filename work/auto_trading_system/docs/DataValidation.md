
> Cuando ejecuto el script update_us_qlib_daily.sh, ¿dónde se almacenan los CSV descargados de Yahoo y dónde se almacenan los ficheros normalizados? necesito saber las ubicaciones de los datos a lo largo de todo el proceso de descarga de la información a través del script.

En tu entorno actual (`HOME=/home/toni`, repo en `/mnt/c/...`), el flujo queda así:

1. **Dataset final Qlib**
   Definido en [scripts/update_us_qlib_daily.sh](/mnt/c/Users/trodriguez/src/qlib/scripts/update_us_qlib_daily.sh:10):

   ```bash
   /home/toni/.qlib/qlib_data/us_data
   ```

   Ahí acaban los datos finales en formato Qlib:
   - `/home/toni/.qlib/qlib_data/us_data/features/<symbol>/*.day.bin`
   - `/home/toni/.qlib/qlib_data/us_data/calendars/day.txt`
   - `/home/toni/.qlib/qlib_data/us_data/instruments/all.txt`
   - también se refrescan instrumentos de índices como `SP500`, `NASDAQ100`, `DJIA`, `SP400`.

2. **CSV brutos descargados de Yahoo**
   El script llama a `scripts/update_us_all.py`, que en este repo bajo `/mnt/...` usa un directorio temporal para evitar trabajar dentro de `/mnt`:

   ```bash
   /tmp/qlib_us_work/source/*.csv
   ```

   Esto sale de `_resolve_work_base_dir()` en [scripts/update_us_all.py](/mnt/c/Users/trodriguez/src/qlib/scripts/update_us_all.py:163): si el repo está bajo `/mnt`, usa `/tmp/qlib_us_work`.

3. **CSV normalizados**
   Se escriben en:

   ```bash
   /tmp/qlib_us_work/normalize/*.csv
   ```

   `USAllRun` asigna `source_dir = work_base_dir / "source"` y `normalize_dir = work_base_dir / "normalize"` en [scripts/update_us_all.py](/mnt/c/Users/trodriguez/src/qlib/scripts/update_us_all.py:429).

4. **Conversión a `.bin`**
   Los CSV normalizados de `/tmp/qlib_us_work/normalize` se pasan a `DumpDataUpdate` o `DumpDataAll`, que escribe en el `DATA_DIR` final. En update normal ocurre aquí: [scripts/update_us_all.py](/mnt/c/Users/trodriguez/src/qlib/scripts/update_us_all.py:584).

Resumen rápido:

```text
Yahoo
  -> /tmp/qlib_us_work/source/*.csv          CSV brutos descargados
  -> /tmp/qlib_us_work/normalize/*.csv       CSV normalizados
  -> /home/toni/.qlib/qlib_data/us_data/     dataset final Qlib
```

Puedes cambiar el directorio intermedio definiendo `QLIB_US_WORK_DIR` o `QLIB_WORK_DIR`. Por ejemplo:

```bash
QLIB_US_WORK_DIR=/home/toni/.qlib/yahoo_us_work ./scripts/update_us_qlib_daily.sh
```

Entonces los CSV quedarían en `/home/toni/.qlib/yahoo_us_work/source` y `/home/toni/.qlib/yahoo_us_work/normalize`.

## Tipos de Issues (Errores) que pueden aparecer en raw_issues.csv

Sí. En `validation_script1.py`, los tipos (`issue`) que pueden aparecer en `raw_issues.csv` son estos:

| Issue | Severidad | Qué indica |
|---|---:|---|
| `invalid_date` | `error` | La fecha no se pudo parsear. En `value` queda la fecha original problemática. |
| `duplicate_symbol_date` | `error` | Hay más de una fila para el mismo `symbol` y la misma fecha diaria normalizada. Marca todas las filas duplicadas. |
| `missing_open` | `warning` | `open` está vacío o no se pudo convertir a número. |
| `missing_high` | `warning` | `high` está vacío o no se pudo convertir a número. |
| `missing_low` | `warning` | `low` está vacío o no se pudo convertir a número. |
| `missing_close` | `error` | `close` está vacío o no se pudo convertir a número. Bloqueante. |
| `missing_volume` | `error` | `volume` está vacío o no se pudo convertir a número. Bloqueante. |
| `non_positive_open` | `error` | `open <= 0`. |
| `non_positive_high` | `error` | `high <= 0`. |
| `non_positive_low` | `error` | `low <= 0`. |
| `non_positive_close` | `error` | `close <= 0`. |
| `negative_volume` | `error` | `volume < 0`. |
| `high_less_than_low` | `error` | `high < low`, inconsistente para OHLC. |
| `open_outside_high_low` | `error` | `open` está fuera del rango `[low, high]`. |
| `close_outside_high_low` | `error` | `close` está fuera del rango `[low, high]`. |
| `very_low_price` | `warning` | `close < 0.5` por defecto. Puede ser válido, pero se marca como sospechoso. |
| `large_raw_return` | `warning` | Retorno diario absoluto mayor a `0.40` por defecto. Posible split, ajuste raro o dato erróneo. |
| `volume_spike_gt_50x_20d_median` | `warning` | Volumen mayor que 50 veces la mediana móvil de 20 días. |
| `zero_volume` | `warning` | `volume == 0`. Puede pasar en activos ilíquidos, pero es sospechoso. |
| `high_missing_close_ratio` | `error` | Para un símbolo, más del `5%` de sus filas tienen `close` ausente. |

Además, hay un caso que **no aparece como fila en `raw_issues.csv`** porque aborta directamente:

```text
Missing required columns
```

Eso ocurre si el CSV no tiene alguna columna obligatoria: `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`.

Los umbrales actuales son:

```python
min_price = 0.5
max_abs_daily_return = 0.40
max_missing_ratio_per_symbol = 0.05
```