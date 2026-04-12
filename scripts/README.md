
- [Download Qlib Data](#Download-Qlib-Data)
  - [Download CN Data](#Download-CN-Data)
  - [Download US Data](#Download-US-Data)
  - [Download CN Simple Data](#Download-CN-Simple-Data)
  - [Help](#Help)
- [Using in Qlib](#Using-in-Qlib)
  - [US data](#US-data)
  - [CN data](#CN-data)


## Download Qlib Data


### Download CN Data

```bash
# daily data
python get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn

# 1min  data (Optional for running non-high-frequency strategies)
python get_data.py qlib_data --target_dir ~/.qlib/qlib_data/cn_data_1min --region cn --interval 1min
```

### Download US Data


```bash
python get_data.py qlib_data --target_dir ~/.qlib/qlib_data/us_data --region us
```

### Download CN Simple Data

```bash
python get_data.py qlib_data --name qlib_data_simple --target_dir ~/.qlib/qlib_data/cn_data --region cn
```

### Help

```bash
python get_data.py qlib_data --help
```

## Using in Qlib
> For more information: https://qlib.readthedocs.io/en/latest/start/initialization.html


### US data

> Need to download data first: [Download US Data](#Download-US-Data)

```python
import qlib
from qlib.config import REG_US
provider_uri = "~/.qlib/qlib_data/us_data"  # target_dir
qlib.init(provider_uri=provider_uri, region=REG_US)
```

### CN data

> Need to download data first: [Download CN Data](#Download-CN-Data)

```python
import qlib
from qlib.constant import REG_CN

provider_uri = "~/.qlib/qlib_data/cn_data"  # target_dir
qlib.init(provider_uri=provider_uri, region=REG_CN)
```

## Use Crowd Sourced Data
The is also a [crowd sourced version of qlib data](data_collector/crowd_source/README.md): https://github.com/chenditc/investment_data/releases
```bash
wget https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
tar -zxvf qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=2
```


## Normalize y regeneración de Bins. (Ultimo error de datos)

```bash
/home/toni/miniconda3/envs/qlib/bin/python /mnt/c/Users/toni/src/qlib/scripts/clean_normalize_daily_csv.py run --normalize_dir /tmp/qlib_us_work/normalize --apply --backup_dir /tmp/qlib_us_work/normalize_backup_before_cleanup
```

Si **ya tienes `normalize/` correcto** y solo quieres **volver a generar los `.bin`**, haz esto:

**Para regrabar todo desde cero**
```bash
/home/toni/miniconda3/envs/qlib/bin/python /mnt/c/Users/toni/src/qlib/scripts/dump_bin.py dump_all \
  --data_path /tmp/qlib_us_work/normalize \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --exclude_fields symbol,date \
  --max_workers 4
```

Pero hay una advertencia importante: si `~/.qlib/qlib_data/us_data` ya existe, `dump_all` no “repara” limpiamente lo anterior; lo correcto es hacerlo sobre un directorio vacío o tras mover el dataset viejo a backup.

La opción más segura es:

```bash
mv ~/.qlib/qlib_data/us_data ~/.qlib/qlib_data/us_data_backup_manual
mkdir -p ~/.qlib/qlib_data/us_data
/home/toni/miniconda3/envs/qlib/bin/python /mnt/c/Users/toni/src/qlib/scripts/dump_bin.py dump_all \
  --data_path /tmp/qlib_us_work/normalize \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --exclude_fields symbol,date \
  --max_workers 4
```

**No uses `dump_update`** si has corregido fechas antiguas dentro de `normalize/`.  
`dump_update` sirve para **añadir fechas nuevas**, pero no para rehacer bien históricos ya escritos; para arreglos como el de `2026-03-03`, necesitas `dump_all` sobre dataset limpio.

Si quieres, te puedo dejar también un comando de verificación justo después del dump para comprobar `AAPL/MSFT/SPY` en `2026-03-03`.

Usa este chequeo después del `dump_all`:

```bash
/home/toni/miniconda3/envs/qlib/bin/python - <<'PY'
from pathlib import Path
import struct, math

base = Path.home() / ".qlib/qlib_data/us_data"
symbols = ["aapl", "msft", "spy", "nvda", "qqq"]
target_dates = ["2026-03-02", "2026-03-03", "2026-03-04"]

with open(base / "calendars" / "day.txt") as f:
    cal = [line.strip() for line in f if line.strip()]

for sym in symbols:
    print(f"\n{sym.upper()}")
    p = base / "features" / sym / "close.day.bin"
    vals = [x[0] for x in struct.iter_unpack("<f", p.read_bytes())]
    start = int(vals[0])
    for d in target_dates:
        idx = cal.index(d)
        rel = idx - start
        v = vals[1 + rel]
        print(d, "NaN" if math.isnan(v) else v)
PY
```

Qué deberías ver:
- `2026-03-02`, `2026-03-03` y `2026-03-04` con valores numéricos.
- Si `2026-03-03` sigue saliendo `NaN` en esos símbolos, entonces el problema seguiría en el `normalize/` usado para el dump o en que el dump no se hizo sobre un `qlib_dir` limpio.

Si quieres una comprobación más completa, también puedes comparar los `.bin` contra los CSV normalizados con:

```bash
/home/toni/miniconda3/envs/qlib/bin/python /mnt/c/Users/toni/src/qlib/scripts/check_dump_bin.py \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --csv_path /tmp/qlib_us_work/normalize \
  --check_fields close,open,high,low,volume,factor \
  --max_workers 4
```

Si quieres, en el siguiente paso te preparo un script `scripts/check_us_bin_rebuild.py` para no tener que pegar estos comandos largos cada vez.

He añadido el script [check_us_bin_rebuild.py](/mnt/c/Users/toni/src/qlib/scripts/check_us_bin_rebuild.py).

Cómo ejecutarlo:
```bash
python3 /mnt/c/Users/toni/src/qlib/scripts/check_us_bin_rebuild.py \
  --data-dir ~/.qlib/qlib_data/us_data
```

Qué hace:
- Revisa por defecto `AAPL MSFT SPY NVDA QQQ`
- Comprueba por defecto las fechas `2026-03-02 2026-03-03 2026-03-04`
- Lee directamente los `.bin`
- Sale con `result: OK` si todo está bien
- Sale con `result: FAIL` si encuentra `NaN`, falta un binario o la fecha no está en calendario

También puedes pasar símbolos, fechas o campos concretos:
```bash
python3 /mnt/c/Users/toni/src/qlib/scripts/check_us_bin_rebuild.py \
  --data-dir ~/.qlib/qlib_data/us_data \
  --symbols AAPL MSFT SPY \
  --dates 2026-03-02 2026-03-03 2026-03-04 \
  --fields close open high low volume factor
```

Lo he probado contra tu dataset actual y ahora mismo da `FAIL`, porque `2026-03-03` sigue en `NaN` en los `.bin` actuales. Eso es esperable hasta que rehagas el `dump/rebuild` con los CSV ya saneados.

Orden recomendado ahora:
1. Ejecuta el `--clean-rebuild`.
2. Lanza este chequeo.
3. Si devuelve `OK`, ya puedes confiar bastante en que el problema quedó resuelto.

Si quieres, en el siguiente paso te dejo el comando exacto de rebuild más seguro para tu entorno, usando lo que ya hemos limpiado.

## REGLA DE USO

Usa esta regla práctica:

1. `update_us_qlib_daily.sh`
   Úsalo cuando solo quieres traer días nuevos desde Yahoo y tu dataset actual está sano.
   Caso típico: ayer funcionaba bien, hoy solo quieres actualizar hasta la fecha actual.

2. `update_us_qlib_daily.sh --clean-rebuild`
   Úsalo cuando sospechas que el histórico binario está dañado o inconsistente.
   Caso típico: ves `NaN` en días que deberían tener datos, desalineaciones raras, bins truncados, o has tocado lógica de normalización/recolección y quieres rehacer `us_data` completo.

3. `dump_bin.py dump_all`
   Úsalo cuando ya tienes `normalize/` correcto y solo quieres regenerar los `.bin` sin volver a descargar ni renormalizar.
   Caso típico: has limpiado o corregido manualmente los CSV de `normalize/` y quieres reconstruir los bins desde esos CSV.

Regla mental rápida:
- Datos nuevos: `update_us_qlib_daily.sh`
- Histórico roto: `update_us_qlib_daily.sh --clean-rebuild`
- `normalize/` ya arreglado y solo falta volcar a bin: `dump_bin.py dump_all`

Para tu caso actual, como ya había fechas rotas y además hemos limpiado `normalize/`, la opción correcta es:
- `--clean-rebuild`, o alternativamente
- `dump_all` sobre un `qlib_dir` limpio si no quieres repetir descarga/normalización.

Y después:
```bash
python3 /mnt/c/Users/toni/src/qlib/scripts/check_us_bin_rebuild.py --data-dir ~/.qlib/qlib_data/us_data
```

Si quieres, te dejo ahora mismo el comando exacto que yo ejecutaría en tu situación concreta.