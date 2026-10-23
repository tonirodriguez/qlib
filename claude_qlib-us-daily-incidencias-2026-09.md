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
| 5 | Ticker `NA` (Nano Labs) leído como NaN (no documentado en este fichero) | Resuelto parcialmente; ver Fallo 6 |
| 6 | Días 2026-09-30 y 2026-10-09 con barras intradía y NaN + `all.txt` congelado | **Resuelto — 2026-10-17** (clean rebuild) |
| 7 | Última sesión sin `close` en ~30% de símbolos (NaN desde el 2026-10-19) | **Fix aplicado — 2026-10-23**; datos se reparan con el resync del 24-oct |

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

### Sesgo de supervivencia residual (NO resuelto por este fix)

El Fallo 4 era una poda accidental del universo, no el sesgo de supervivencia clásico.
Corregirlo **no** deja el dataset libre de dicho sesgo. Medido sobre el dataset del
2026-09-08:

Bajas registradas en `all.txt` por año de `end_date`:

```
2012:   2    2016:  15    2018: 124    2020: 195    2022: 146    2024: 191
2013:   5    2017:  31    2019:  91    2021: 104    2023: 230    2025: 177
                                                                 2026: 13.645 (vivos)
```

Solo **1.311 de 14.956** símbolos son bajas, y casi ninguna anterior a 2018, en un
dataset que arranca en 1999-12-31: no hay prácticamente nada de la burbuja puntocom ni
de la crisis de 2008.

Prueba directa sobre el S&P 500 histórico: de sus **1.132 miembros point-in-time, 380
(33,6%) no tienen datos**. Los ausentes son justamente los nombres que definen el sesgo:
`AAMRQ` (American Airlines, quiebra), `ABKFQ` (Ambac, quiebra), `AABA` (Altaba/Yahoo),
`ALTR` (Altera→Intel), `AGN` (Allergan→AbbVie), `ABMD` (Abiomed→J&J), `AKS` (AK Steel).
Un backtest sobre este dataset seguiría comprando solo empresas que sabemos que
sobrevivieron.

**Causa**: es la fuente, no el código. `nasdaqtraded.txt` / `otherlisted.txt` y Eastmoney
listan valores **vivos hoy**, sin delistados históricos. Y Yahoo no sirve historial de
tickers ya delistados: de los 19.579 símbolos del universo, 4.623 devolvieron
`The stock may be delisted, please check`.

**Lo que sí aporta el fix**: el universo deja de auto-podarse, recupera los vivos que
faltaban (+8.496) y, **de aquí en adelante**, conserva las bajas — cuando un símbolo
desaparece de la fuente externa pero está en el histórico local, sigue en el universo con
su `end_date`. Es una solución *forward-looking*: detiene la acumulación del sesgo hacia
el futuro, pero no reconstruye el agujero de 1999-2017.

**Matiz importante**: esa preservación opera sobre el *universo de descarga*, no sobre
`all.txt`. En un clean rebuild, `all.txt` se regenera a partir de los CSV que Yahoo
devolvió; si un delistado deja de dar datos, desaparece de `all.txt` y en el rebuild
siguiente ya no está ni en el histórico local. La protección es real pero no hermética.

**Opciones para cerrarlo de verdad** (requieren fuente con delistados):

| Fuente | Coste aprox. | Cobertura |
|--------|--------------|-----------|
| Sharadar SEP (Nasdaq Data Link) | ~$50/mes | US equities con delistados desde 1998 |
| Norgate Data | ~$70/mes | US con delistados desde 1990 |
| Polygon.io | ~$30-200/mes | Delistados vía API de tickers |
| CRSP | académico/institucional | El estándar, desde 1925 |

Alternativa barata y parcial: hacer que `all.txt` nunca pierda un símbolo ya registrado
(unión también en la **escritura**, no solo en el universo de descarga), fijando los
delistados que Yahoo aún sirve con su `end_date` antes de que dejen de estar disponibles.
No recupera 1999-2017, pero detiene la sangría. **Pendiente de implementar.**

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
  2026-09-08; el rebuild del 2026-09-09 no se ejecutó. Con el universo ya sano, el modo
  incremental (`update_us_qlib_daily.sh` sin `--clean-rebuild`) tiene más sentido como
  tarea diaria: un rebuild completo son ahora ~19 h y se solaparía consigo mismo.
- **Sesgo de supervivencia**: sigue abierto pese al Fallo 4 — ver la sección dedicada más
  arriba. El dataset no es apto para backtests que dependan de delistados anteriores a
  2018.

---

## Fallo 6 — Barras del día en curso volcadas como cierre + `all.txt` congelado

> Diagnóstico y fix: 2026-10-13. Reparación: clean rebuild completo del 2026-10-16/17.
> Verificación: 2026-10-19.

### Síntoma

Los días 2026-09-30 y 2026-10-09 tenían `$close` a NaN para la mayoría de símbolos; los
pocos que tenían dato traían valores intradía en vez de cierres (AAPL 441,94 el 30-sep,
frente al cierre real de 433,18). Cobertura de esos días: 29% y 32%, frente al ~81%
normal (medido el 13-oct con `_check_recent_coverage`).

### Causa 1 — descarga con `end_date = TODAY`

La ejecución de la 01:01 descargaba con `end_date = TODAY`, y Yahoo devolvía barras del
día en curso para unos pocos cientos de símbolos. Ese volcado metía el día en el
calendario con una cobertura del ~33% y NaN para el resto. `DumpDataUpdate` no reescribe
fechas ya volcadas (filtra por `> effective_end`, calculado con el final de cada `.bin`),
así que el NaN se quedaba para siempre y ni siquiera el resync semanal lo corregía.

### Causa 2 (encadenada) — `save_instruments` abortaba por el ticker `NA`

`dump_bin.py` reventaba al final, en `save_instruments`, con
`AttributeError: 'float' object has no attribute 'lower'`. Otra vez era el ticker `NA`
(Nano Labs) leído como NaN, aunque esta vez desde la columna `symbol` de los CSV
normalizados y no desde `instruments/all.txt`. Como el fallo ocurre **después** de
escribir los `.bin`, los precios y el calendario avanzaban, pero `instruments/all.txt`
se quedó congelado en 2026-09-11. Con él se congeló también el cálculo de la fecha de
arranque incremental: todas las noches se volvían a descargar ~20 días
(`Incremental effective date=2026-09-11` en todos los logs). Por eso el fix del Fallo 5
parecía funcionar cuando en realidad solo estaba aplicado a medias.

### Fix aplicado (2026-10-13)

a. `scripts/dump_bin.py`: `_get_source_data` rellena el símbolo a partir del nombre del
   fichero cuando pandas lo lee como nulo, y `save_instruments` descarta las filas sin
   símbolo con un warning en vez de abortar.
b. `scripts/update_us_all.py`: nueva función `_last_closed_session_date()` (16:00 ET
   + 15 min de margen). El sanitizador descarta las filas posteriores a la última sesión
   cerrada y lo registra como `future_rows_removed`.
c. El sanitizador pasa a usar `pd.to_datetime(..., format="mixed")`. Antes infería el
   formato a partir de la primera fila y convertía en NaT las filas con hora, que luego
   se descartaban en silencio.
d. Nueva función `_check_recent_coverage()`. Se ejecuta al final de cada update y de
   cada rebuild, y registra un ERROR si algún día reciente baja del 60% de cobertura.
   Se probó el 13-oct: detectó el 30-sep al 29% y el 9-oct al 32%, frente al 81% normal.

### Backups (2026-10-13)

- `scripts/dump_bin.py.bak_20261013_135104`
- `scripts/update_us_all.py.bak2_20261013_135142`
- Dataset: `/opt/qlib_home/qlib_data/us_data_prepatch_20261013_135945` (1,7 GB)
- El rebuild dejó además un backup automático del dataset anterior:
  `/opt/qlib_home/qlib_data/us_data_backup_20261016_220705` (1,7 GB)

### Reparación de los dos días

Se intentó un parche quirúrgico sobre los `.bin`. El script de dry-run quedó validado
(200.969 valores en 13.465 símbolos), pero la escritura se bloqueó por permisos, así que
la reparación se hizo con un **clean rebuild completo** (`DumpDataAll`), lanzado por una
línea one-shot del cron:

- Inicio: 2026-10-16 22:07:05. Fin: 2026-10-17 08:46:18. **Duración: ~10 h 39 min**
  (se esperaban ~19-20 h). Log: `scripts/logs/run_full_20261016`.
- Rango: `1999-12-31 → 2026-10-16`. El calendario termina en **2026-10-15**, lo cual es
  correcto: a las 22:07 CEST la sesión del 16-oct aún no superaba el margen de 16:15 ET.
- El resync del sábado 2026-10-17 a la 01:01 no llegó a ejecutarse porque el lock lo
  tenía el rebuild (`run_rebuild_20261017` está vacío). Era lo esperado.

**Resultado (medido el 2026-10-19): la reparación FUNCIONÓ.**

- `_check_recent_coverage(lookback=25)` → `anomalias: []`. Todos los días entre
  2026-09-11 y 2026-10-15 tienen una cobertura del 91-94% sobre la muestra de 800
  símbolos. El 2026-09-30 está al **94%** y el 2026-10-09 al **93%**.
- AAPL `$close` el 2026-09-30 = **433,1848** (el cierre real; antes era 441,94). Valores
  de alrededor: 29-sep 428,48 · 01-oct 429,67 · 09-oct 437,89.
- Sin `Traceback`, `AttributeError` ni `ERROR` en el log. `NA` aparece en `all.txt`
  (`NA 2022-07-12 2026-10-15`), así que el fix (a) funciona en un volcado completo.
- `instruments/all.txt` se ha regenerado (08:32 del 17-oct): todas las filas activas
  terminan en 2026-10-15.

### Efecto secundario: el universo se redujo en ~2.400 símbolos

| Dataset | Filas `all.txt` | Directorios en `features/` |
|---------|----------------:|---------------------------:|
| `us_data_prepatch_20261013_135945` | 14.981 | 15.485 |
| `us_data_backup_20261016_220705` (justo antes del rebuild) | 15.484 | 15.485 |
| `us_data` tras el rebuild | **13.122** | **13.122** |

- 2.387 símbolos del dataset anterior no están en el nuevo. De ellos, 1.739 terminaban
  antes de sept-2026 (delistados que Yahoo ya no sirve: es el sesgo de supervivencia del
  Fallo 4, que el clean rebuild empeora, tal y como se advertía en esa sección) y 644
  terminaban entre sept y oct-2026, con picos el 09-oct (160) y el 13-oct (134).
- El log registra **6.699 descargas vacías** (`save_instrument: ... is empty`) de 19.825
  símbolos solicitados. La mayoría son delistados de verdad, pero hay al menos una
  pérdida transitoria importante: **ABT (Abbott, miembro actual del S&P 500) no tiene
  datos**. Yahoo devolvió error dos veces a las 22:30 del 16-oct y el símbolo se descartó.
  El resto de miembros actuales de sp500 y nasdaq100 sí tienen `features/` (`BF.B` y
  `BRK.B` existen como `bf-b` y `brk-b`).
- **Pendiente**: recuperar ABT (y revisar los 644 símbolos con fin en sept-oct) a partir
  de `us_data_backup_20261016_220705` o con una descarga puntual. Además, valorar
  reintentos con backoff en `get_data_from_remote` para que un fallo transitorio de Yahoo
  no elimine un símbolo en un rebuild completo.

### Cron

Línea one-shot `7 22 16 10 * ... update_us_qlib_rebuild.sh --full` y su comentario
retirados del crontab el 2026-10-19 (copia previa en `/tmp/crontab.bak_20261019_115357`).
Se mantienen el incremental `1 1 * * 2-5` y el resync `1 1 * * 6`.

### Disco (2026-10-19)

`/opt`: 477 GB libres (46% de uso). `/`: 83 GB libres. No hay presión de espacio. Los
backups `us_data_prepatch_20261013_135945` (1,7 GB), `us_data_backup_20261016_220705`
(1,7 GB) y `us_data_backup_20260912_010103` (1,5 GB) se podrían borrar, pero **no
conviene borrar el del 16-oct hasta haber recuperado ABT** y los demás símbolos perdidos.

### Hallazgo (2026-10-19): `.bin` desalineados por el append ciego de `DumpDataUpdate`

Al revisar los backups antes de restaurar desde ellos, se encontró que en modo update
`_data_to_bin` escribía con `open("ab")`: añadía los valores al final del fichero
suponiendo que ese final era el día anterior al primer dato nuevo. Con `all.txt`
congelado en 2026-09-11 (Causa 2), cada noche se volvía a añadir todo lo posterior al
11-sep, y las fechas quedaban desplazadas.

| Dataset | `.bin` más largos que su calendario | Exceso (mediana / máx.) |
|---------|------------------------------------:|------------------------:|
| `us_data_backup_20260912_010103` | 0 | — |
| `us_data_prepatch_20261013_135945` | 13.694 | 195 / 1.244 |
| `us_data_backup_20261016_220705` | 13.701 | 216 / 1.341 |
| `us_data` tras el clean rebuild | **0** | — |

Conclusión: entre el 12-sep y el 16-oct, **los datos posteriores al 11-sep de la mayoría
de los símbolos estaban desplazados de fecha**. Cualquier señal o backtest calculado con
ese dataset en ese periodo es sospechoso. El clean rebuild lo dejó limpio. Los backups del
13-oct y del 16-oct **no deben usarse para restaurar `.bin`** (sí sirven sus `all.txt`).

### Mejoras implementadas (2026-10-19)

**`scripts/dump_bin.py`** (backup `dump_bin.py.bak_20261019_120241`):
- `_write_bin_positional()`: en modo update, cada fecha se escribe en su posición del
  calendario y se pueden repetir sin efectos. Se probó en una copia: con `all.txt`
  retrasado, los `.bin` quedan idénticos (el append antiguo los habría alargado), y un
  día nuevo cae en su posición.
- `DumpDataUpdate`: `_read_instruments` con `keep_default_na=False` y relleno del símbolo
  desde el nombre del fichero en `_load_all_source_data`. Antes, `NA` (Nano Labs) se
  perdía de `all.txt` en cada incremental (no estaba en el backup del 16-oct) y nunca se
  actualizaba.

**`scripts/update_us_all.py`**:
- `_retry_missing_downloads()`: tras la descarga, vuelve a pedir los símbolos esperados
  sin CSV, por rondas con esperas crecientes (`QLIB_MISSING_RETRY_WAITS`, por defecto
  `60,300,900`), y para cuando una ronda no recupera nada.
  - Rebuild: símbolos activos del dataset anterior + miembros de sp500/nasdaq100.
  - Incremental: solo los miembros de los índices que ya existen en `all.txt`.
- `_restore_missing_from_backup()`: al terminar `DumpDataAll`, copia desde el dataset
  anterior los símbolos que faltan, con su `end_date` original. `all.txt` ya no
  pierde símbolos en un clean rebuild. Si los calendarios difieren, reubica los `.bin`, y
  rechaza los `.bin` más largos que su calendario.
- `_check_universe_after_rebuild()`: compara el universo antes y después y registra un
  ERROR si faltan símbolos o algún miembro actual de los índices no tiene datos.
- Modo `known` (incremental nocturno): solo símbolos con dato en los últimos
  `US_ALL_KNOWN_ACTIVE_DAYS` (30) días, para no pedir cada noche los delistados que
  ahora se conservan. Hoy son 13.112 símbolos.
- `US_ALL_SYMBOLS_FILE`: lista explícita de símbolos para la descarga (reintentos y
  recuperación).

**`scripts/recover_lost_symbols.py`** (nuevo): recupera lo que perdió el rebuild. Por
defecto solo simula.

### Recuperación de los símbolos perdidos — simulación del 2026-10-19

Log: `scripts/logs/recover_dryrun_20261019_1206`.
- Perdidos frente a los backups del 16-oct y el 12-sep: **2.391**.
- Activos desde el 2026-09-01: 648. 607 dejaron un CSV y los otros 41 no devolvieron
  nada. **Corrección (aplicación, 2026-10-19):** 605 de esos 607 CSV tenían **una sola
  fila** (la última cotización de warrants o derechos muertos: sufijos W, R, -WT), sin
  histórico. El script los contaba como recuperados y no son fallos puntuales: Yahoo ya
  no sirve su histórico. Fallos puntuales reales: ABT y muy pocos más.
- 1.784 restantes: 1.772 se pueden copiar desde `us_data_backup_20260912_010103`
  (limpio) y 12 no tienen fuente (altas posteriores al 12-sep que Yahoo no sirve).

**Pendiente: ejecutar con `--apply`** (la escritura sobre el dataset real necesita
permiso del usuario):

    cp -a /opt/qlib_home/qlib_data/us_data /opt/qlib_home/qlib_data/us_data_prerecover_$(date +%Y%m%d_%H%M%S)
    cd /opt/qlib && /usr/bin/flock -n /tmp/qlib_us_pipeline.lock \
      /home/toni/miniconda3/envs/qlib/bin/python scripts/recover_lost_symbols.py \
      --backup_dirs /opt/qlib_home/qlib_data/us_data_backup_20261016_220705,/opt/qlib_home/qlib_data/us_data_backup_20260912_010103 \
      --restore_dir /opt/qlib_home/qlib_data/us_data_backup_20260912_010103 --apply \
      > scripts/logs/recover_apply_$(date +%Y%m%d_%H%M) 2>&1

Conviene hacerlo **antes del resync del sábado**: el resync recorre el universo completo y
crearía ABT y los otros 606 solo con datos desde el día 1 del mes anterior. La
recuperación ya no podría completar su histórico, porque `DumpDataUpdate` no rellena
hacia atrás y la restauración no sobrescribe directorios que ya existen.

### Recuperación aplicada (2026-10-19)

Copia previa: `/opt/qlib_home/qlib_data/us_data_prerecover_20261019_125801`.

1. `recover_lost_symbols.py --apply` (log `scripts/logs/recover_apply_20261019_125801`):
   se volcaron ABT y AELV con su histórico completo y se restauraron 1.772 símbolos
   desde `us_data_backup_20260912_010103`. Por el criterio erróneo de "hay CSV", los
   605 de una sola fila quedaron fuera de la restauración (283 de ellos estaban en el
   backup), y LGMK se volcó con una única sesión y perdió su histórico desde 2013.
2. Corrección del script: ahora normaliza siempre y solo da por recuperado lo que tiene
   `--min_rows` (20) sesiones o más. Lo demás va a la fase B.
3. Fase B manual (log `scripts/logs/recover_phaseB_20261019_1502`): se quitó LGMK y se
   restauraron desde el backup del 12-sep **284 símbolos** (los 283 + LGMK).

**Estado final verificado (2026-10-19 15:05):**
- `all.txt`: **15.180** símbolos, sin duplicados, y todos con `features/`. El universo pasó
  de 14.956 (backup del 12-sep) a 15.180 (+224 / −0). El dataset del rebuild tenía 13.122.
- **0 `.bin` desbordados** en todo el dataset. Calendario: 6.738 días, hasta 2026-10-15.
- Ningún miembro actual de sp500/nasdaq100 sin datos. ABT 1999-12-31 → 2026-10-15,
  `NA` y LGMK (2013-08-23 → 2026-09-04) presentes.
- Cobertura de los últimos días: 92-95%. `_check_recent_coverage` ahora toma la muestra
  solo de los símbolos activos, para que los delistados conservados no la bajen.
- AAPL 2026-09-30 = 433,18 (sin cambios).
- Sin recuperar: los 41 símbolos activos que Yahoo no sirve y 12 altas posteriores al
  12-sep sin fuente.

---

## Cambios del 2026-10-19 (tarde): resync que reescribe su rango, ajustes por dividendo y OOM

### OOM del incremental (el del 2026-10-16 murió con `Killed`)

`run_daily_20261016` terminó con `Killed` al empezar la normalización (06:21). El 16 no
se volcó: el 15 y el 16 llegaron con el clean rebuild. Hay dos causas, y las dos
habrían vuelto a matar el incremental del 20-oct (la máquina tiene 15 GB):
1. `_get_old_data` cargaba con `D.features` el histórico completo de todos los símbolos
   (~15.000 × 6.700 días × 7 campos) solo para quedarse con el último valor de cada uno.
   **Fix:** se lee cada `.bin` con `np.memmap` (33 s; mismos valores que `D.features`,
   verificado en 20 símbolos, entre ellos `NA`, `CON`, `PRN` y `BRK-B`).
2. `update_data_to_bin` no vaciaba `source/` ni `normalize/` y `save_instrument`
   concatena con el CSV existente: se acumulaban las descargas de todas las noches, y
   ahora estaban los 13.126 históricos completos del rebuild (~88 M filas).
   **Fix:** se vacían al empezar cada ejecución.
- Además, `DumpDataUpdate.__getstate__` deja de serializar `_all_data` en cada tarea del
  ProcessPoolExecutor, y si no hay filas nuevas (un festivo) el update termina limpio en
  vez de fallar con `No objects to concatenate`.
- Prueba del incremental en una copia: añade el día nuevo en su posición con un máximo de
  **488 MB de RAM**.

### Resync semanal: reescribe todo su rango

Antes, `DumpDataUpdate` solo escribía las fechas posteriores al último dato, así que el
resync no corregía nada de lo ya volcado (tampoco el 30-sep ni el 9-oct). Ahora
(`update_data_to_bin --rewrite_window True`, que el wrapper pasa cuando hay `START_DATE`):
- La normalización extendida enlaza la descarga con el **primer día de la ventana ya
  guardado**, no con el último, y devuelve la ventana entera.
- `DumpDataUpdate(rewrite_from=...)` reescribe por posición todas las fechas >= inicio
  de la ventana. Un NaN nuevo no borra un valor ya guardado.
- `dump_bin`: en modo update, también los `.bin` que aún no existen se escriben por
  posición. Antes, el primer dividendo de un símbolo creaba `dividends.day.bin` con la
  posición relativa al tramo nuevo, es decir, desalineado.

### Reconstrucción completa por dividendos y splits

- `adjust_state.csv` (en el directorio del dataset) guarda, para cada símbolo,
  `full_as_of`: la fecha hasta la que su histórico entero está ajustado. El clean
  rebuild lo escribe para todos. Si no existe, se usa `QLIB_ADJ_BASELINE` (el wrapper
  pone 2026-10-15, el último rebuild).
- El resync lee las columnas `dividends`/`splits` de la descarga. Cada símbolo con un
  evento posterior a su `full_as_of`, y cada símbolo que no estaba en el dataset, se
  descarga desde 1999 y se sustituye entero (`DumpDataUpdate(full_replace=True)`, por
  lotes de 300). Solo se sustituye si la descarga llega hasta su `end_date` actual; si
  no, se reintenta la semana siguiente.
- Volumen estimado: 400-1.600 símbolos por semana con algún evento (la mayoría, fondos
  con dividendo mensual), lo que suma ~1-2 h al resync.

**Verificación (copias del dataset, 2026-10-19):**
- Resync 01-sep→16-oct sobre el dataset actual: AAPL y MSFT reescritos con diferencias
  ≤ 1,2e-7 (precisión float32); NVDA, JEPI y SPY reconstruidos con diferencias ≤ 1,4e-6
  frente al clean rebuild. SPY, borrado para simular un alta, vuelve con su histórico
  desde 1999. Ningún `.bin` desbordado.
- Resync sobre el backup del 12-sep (antes de los dividendos de septiembre/octubre de
  JEPI, O y KO): los tres se reconstruyen y coinciden con el clean rebuild (≤ 2,2e-6).

**Hallazgo:** AAPL, solo enlazado y sin reconstruir, también coincide (≤ 1,5e-6), y el
backup del 12-sep ya tenía los mismos niveles históricos que el rebuild del 16-oct.
Con la normalización de Qlib (todo dividido por el primer cierre ajustado), un
dividendo o split nuevo multiplica por igual los valores anteriores al ex-date y ese
primer cierre, así que **los valores ya guardados no cambian**. Solo cambian los
posteriores al ex-date, que caen en la ventana enlazada. La reconstrucción completa
queda como red de seguridad frente a revisiones de Yahoo y se puede desactivar con
`QLIB_RESYNC_FULL_ON_ADJUST=0`. Los símbolos nuevos se reconstruyen siempre.

---

## Fallo 7 — Última sesión descargada sin cierre (NaN en `close`)

> Diagnóstico y fix: 2026-10-23.

### Síntoma

Desde el 2026-10-19, ~3.500 símbolos por día (NVO, JPM, MSFT…) tienen `$close` a NaN
con `open`, `high`, `low`, `volume` y `factor` válidos. Cobertura de `close` del 19 al
22-oct: 62–68%, frente al 92–95% habitual. `_check_recent_coverage` no avisó porque
el umbral era del 60%.

### Causa raíz

A la 01:01 (hora de Madrid) Yahoo todavía no ha consolidado la última sesión para ~30%
de los símbolos. Devuelve la barra con OHLV, pero con `close` y `adjclose` vacíos (hoy:
3.598 de 12.176 filas del 22-oct). El sanitizador no filtraba esas filas,
`dump_bin` las escribía como NaN y `DumpDataUpdate` no reescribe fechas ya volcadas,
así que el NaN se quedaba aunque la diaria siguiente sí trajera el cierre. Los días
anteriores al 19-oct no lo muestran porque salen del clean rebuild del 17-oct.

### Fix aplicado (2026-10-23)

a. `_sanitize_normalized_daily_csv` descarta las filas con `close` NaN y algún dato
   OHLV válido. Lo registra como `incomplete_close_removed`. El `.bin` de ese símbolo
   termina un día antes, y la diaria siguiente, que arranca en la última fecha del
   calendario, vuelve a descargar ese día ya con cierre y lo añade por posición.
b. `_check_recent_coverage`: el umbral pasa de 0,6 a 0,85. La última sesión se mide
   contra `last_min_ratio=0,4`, porque tras (a) en ella es normal un ~65%.

Backup: `scripts/update_us_all.py.bak_20261023_122846`.

### Reparación de los datos

Los NaN del 19 al 22-oct se corrigen con el resync semanal (`--rewrite_window`, que
reescribe desde el 1-sep), porque un valor nuevo válido sustituye al NaN. Hay que
verificar tras el resync del 2026-10-24 que la cobertura de esos días vuelve a >90%.

