
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