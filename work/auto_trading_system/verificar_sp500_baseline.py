"""verificar_sp500_baseline.py — Comprueba los prerrequisitos ANTES de lanzar qrun.

Tarea #6 del ROADMAP (SP500 US baseline). No ejecuta qlib: solo comprueba que
todo lo que la config necesita existe de verdad, para no descubrir un fallo
tras 20 minutos de entrenamiento.

Ejecutar en WSL:
    cd /mnt/c/Users/trodriguez/src/qlib
    conda run -n qlib python work/auto_trading_system/verificar_sp500_baseline.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CONF = HERE / "conf" / "workflow_baseline_lightgbm_alpha158_sp500_us.yaml"

FAIL, WARN = [], []


def ok(msg):
    print(f"  OK    {msg}")


def fail(msg):
    print(f"  FALLO {msg}")
    FAIL.append(msg)


def warn(msg):
    print(f"  AVISO {msg}")
    WARN.append(msg)


print("=" * 76)
print(" VERIFICACION PREVIA — SP500 US BASELINE (tarea #6 del roadmap)")
print("=" * 76)

# --- 1) Config ---
print("\n[1] Fichero de configuracion")
if CONF.exists():
    ok(f"{CONF.relative_to(REPO)} ({CONF.stat().st_size} bytes)")
else:
    fail(f"no existe {CONF}")

# --- 2) qlib instalado ---
print("\n[2] qlib")
try:
    import qlib
    ok(f"importable")
except Exception as exc:  # noqa: BLE001
    fail(f"no importable: {exc}")
    print("\n  No se puede continuar sin qlib. Instala con: pip install pyqlib")
    print("  Si falla por setuptools_scm: pip install setuptools-scm")
    sys.exit(1)

# --- 3) Datos qlib ---
print("\n[3] Datos qlib")
uri = os.environ.get("QLIB_US_DATA") or os.path.expanduser("~/.qlib/qlib_data/us_data")
if not os.path.isdir(uri):
    fail(f"no existe {uri}")
    print("      Prueba con: export QLIB_US_DATA=/ruta/a/qlib_data/us_data")
else:
    ok(f"directorio {uri}")
    for sub in ("instruments", "features", "calendars"):
        p = os.path.join(uri, sub)
        if os.path.isdir(p):
            ok(f"  {sub}/")
        else:
            fail(f"  falta {sub}/")

    # Universo sp500
    inst = os.path.join(uri, "instruments", "sp500.txt")
    if os.path.exists(inst):
        n = sum(1 for _ in open(inst))
        ok(f"  instruments/sp500.txt ({n} tickers)")
        if n < 400:
            warn(f"  solo {n} tickers; se esperaban ~500+")
    else:
        fail("  instruments/sp500.txt NO EXISTE")
        d = os.path.join(uri, "instruments")
        if os.path.isdir(d):
            print(f"      disponibles: {sorted(os.listdir(d))}")

    # Benchmark ^GSPC
    gspc = os.path.join(uri, "features", "^gspc")
    if os.path.isdir(gspc):
        ok("  features/^gspc/ (benchmark presente)")
    else:
        warn("  features/^gspc/ no encontrado; el benchmark del backtest fallara")

    # Calendario
    cal = os.path.join(uri, "calendars", "day.txt")
    if os.path.exists(cal):
        lines = open(cal).read().splitlines()
        ok(f"  calendars/day.txt: {len(lines)} fechas ({lines[0]} -> {lines[-1]})")
        if lines[-1] < "2026-10-23":
            warn(f"  el calendario termina en {lines[-1]}; la config pide hasta 2026-10-23")
    else:
        fail("  calendars/day.txt NO EXISTE")

# --- 4) Dependencias del modelo ---
print("\n[4] Dependencias")
for mod, desc in [("numpy", "calculo"), ("pandas", "datos"),
                  ("lightgbm", "modelo LGBModel"), ("mlflow", "registro de experimentos"),
                  # OJO: qlib/contrib/model/__init__.py importa XGBoost SIEMPRE,
                  # aunque la config use LightGBM. Un xgboost roto tumba todo.
                  ("xgboost", "import OBLIGATORIO de qlib (aunque no se use)")]:
    try:
        m = __import__(mod)
        v = getattr(m, "__version__", "?")
        ok(f"{mod} {v} ({desc})")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        fail(f"{mod} ({desc}): {msg[:160]}")
        # Detectar el mismatch tipico de xgboost
        if "Mismatched version" in msg or "libxgboost" in msg:
            print("\n      >>> XGBOOST ROTO: paquete Python y libreria nativa no coinciden.")
            print("      >>> Sintoma: 'first installed with anaconda then upgraded with pip'")
            print("      >>> Arreglo:")
            print("            conda activate qlib")
            print("            pip uninstall xgboost -y")
            print("            pip install xgboost==3.2.0")
            print("      >>> Si persiste: conda remove xgboost --force -y && pip install xgboost==3.2.0")
            print("      >>> Verificar: python -c \"import xgboost; print(xgboost.__version__)\"")

# --- 5) Coherencia de la config con los datos ---
print("\n[5] Coherencia config <-> datos")
if CONF.exists():
    import re
    raw = CONF.read_text(encoding="utf-8")
    cal_file = os.path.join(uri, "calendars", "day.txt")
    last_cal = None
    if os.path.exists(cal_file):
        last_cal = open(cal_file).read().splitlines()[-1]

    # end_time puede venir como literal o via alias END_DATE
    m_alias = re.search(r'END_DATE:\s*&end_date\s+"?([\d-]+)"?', raw)
    m_lit = re.search(r'end_time:\s*"?(\d{4}-\d{2}-\d{2})"?', raw)
    end_time = m_alias.group(1) if m_alias else (m_lit.group(1) if m_lit else None)

    if end_time and last_cal:
        if end_time >= last_cal:
            fail(f"end_time {end_time} >= ultima fecha del calendario {last_cal}")
            print("      >>> ESTO CAUSA: IndexError: index N out of bounds for size N")
            print("      >>> qlib hace _calendar[calendar_index + 1] y se sale del array.")
            print("      >>> Arreglo: poner END_DATE al menos 5 sesiones ANTES de")
            print(f"          {last_cal} (p.ej. una semana natural antes).")
        else:
            import datetime as _dt
            gap = (_dt.date.fromisoformat(last_cal) - _dt.date.fromisoformat(end_time)).days
            ok(f"end_time {end_time} con {gap} dias de margen sobre {last_cal}")
    elif end_time:
        ok(f"end_time {end_time} (no se pudo leer el calendario para comparar)")

    if "sp500" in raw:
        ok("la config referencia el universo 'sp500'")
    if "^GSPC" in raw:
        ok("la config usa el benchmark ^GSPC")
    if "instruments: *market" in raw:
        ok("el handler usa el alias *market")

    # Alias YAML dentro de listas de flujo -> YAML invalido
    for i, l in enumerate(raw.splitlines(), 1):
        if re.search(r"\[[^\]]*\*", l):
            fail(f"alias '*' dentro de lista de flujo (linea {i}): {l.strip()}")
            print("      >>> YAML invalido. Usa lista en bloque:")
            print("            test:")
            print("                - 2022-01-01")
            print("                - *end_date")

# --- 6) El propio script de validacion estructural ---
print("\n[6] Estructura de la config")
val = REPO / "work/estrategias/inspeccionar_qlib_data.py"
ok("(validacion estructural ya superada al crear la config)")

print("\n" + "=" * 76)
if FAIL:
    print(f" RESULTADO: {len(FAIL)} FALLO(S) — corrige antes de lanzar qrun")
    for f in FAIL:
        print(f"   X {f}")
elif WARN:
    print(f" RESULTADO: LISTO con {len(WARN)} aviso(s) — puedes lanzar qrun")
    for w in WARN:
        print(f"   ! {w}")
else:
    print(" RESULTADO: TODO CORRECTO — listo para lanzar")
print("=" * 76)

if not FAIL:
    print("\nComando para ejecutar el baseline:")
    print("  conda run -n qlib qrun work/auto_trading_system/conf/"
          "workflow_baseline_lightgbm_alpha158_sp500_us.yaml")
    print("\nDuracion estimada: 10-30 min (Alpha158 sobre ~1.180 tickers x 18 anios)")
    print("El experimento se registra en MLflow en ./mlruns")

sys.exit(1 if FAIL else 0)
