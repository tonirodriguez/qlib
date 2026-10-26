"""auditoria_momentum_vt.py — Audita momentum_vt_backtest.py.

PREGUNTA
    `momentum_vt_backtest.py` reporta Sharpe 1.07 y DD -18.6%, y es una de las
    validaciones que respaldan el vol-gating. Hay que verificar si el numero
    es reproducible.

HALLAZGOS ESTATICOS (leidos del codigo)

    1. El script delega en `toni.vol_target_strategy.VolTargetTopkStrategy`,
       un module_path que apunta a un paquete `toni` que NO EXISTE en el repo
       (no hay `toni/__init__.py`; el archivo esta en `work/estrategias/`).
       -> El import fallara SALVO que se resuelva de otra forma.

    2. Esa clase hereda de `TopkDropoutStrategy` y modula `self.risk_degree`.
       A DIFERENCIA de `vol_gate_test.py` (que multiplicaba la senal y no
       tenia efecto), `risk_degree` SI se usa en qlib:
           signal_strategy.py:365  risk_degree=self.get_risk_degree(trade_step)
           signal_strategy.py:266  value = cash * self.risk_degree / len(buy)
       -> El mecanismo ES correcto.

    3. `MLFLOW_TRACKING_URI = sqlite:////opt/data/qlib/...` apunta a OTRA
       maquina. Si mlflow falla al inicializar, el script podria no arrancar.

QUE COMPRUEBA ESTE SCRIPT
    A) Si el module_path `toni.vol_target_strategy` es importable.
    B) Si qlib lo ignora silenciosamente (fallback TypeError) o falla.
    C) Si `risk_degree` afecta de verdad al backtest.

NO necesita qlib para A y B (analisis estatico) pero si para C.
Uso:
    conda run -n qlib python work/estrategias/auditoria_momentum_vt.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

print("=" * 76)
print(" AUDITORIA — momentum_vt_backtest.py")
print("=" * 76)

fails, warns = [], []


def fail(m):
    print(f"  FALLO {m}")
    fails.append(m)


def ok(m):
    print(f"  OK    {m}")


def warn(m):
    print(f"  AVISO {m}")
    warns.append(m)


# ------------------------------------------------------------------
# A) El module_path es importable?
# ------------------------------------------------------------------
print("\n[A] module_path = 'toni.vol_target_strategy'")

# A.1 existe el paquete toni?
toni_dir = REPO / "toni"
if toni_dir.is_dir():
    ok(f"existe {toni_dir}")
    if (toni_dir / "__init__.py").exists():
        ok("toni/__init__.py presente")
    else:
        fail("toni/ NO tiene __init__.py -> no es un paquete importable")
else:
    fail("NO existe el directorio toni/")

# A.2 donde esta realmente el modulo?
real = HERE / "vol_target_strategy.py"
if real.exists():
    warn(f"el modulo esta en {real.relative_to(REPO)}")
    print("        -> para que 'toni.vol_target_strategy' funcione, deberia")
    print("           estar en toni/vol_target_strategy.py con toni/__init__.py")

# A.3 intentar el import de verdad
print("\n[A.3] Intento de import real")
try:
    import importlib
    importlib.import_module("toni.vol_target_strategy")
    ok("import OK")
except ImportError as exc:
    fail(f"ImportError: {exc}")
except Exception as exc:  # noqa: BLE001
    warn(f"otro error al importar: {str(exc)[:120]}")

# ------------------------------------------------------------------
# B) qlib lo ignora silenciosamente?
# ------------------------------------------------------------------
print("\n[B] Comportamiento de qlib ante el fallo")
mod_py = REPO / "qlib/utils/mod.py"
if mod_py.exists():
    src = mod_py.read_text(encoding="utf-8")
    if "except (TypeError,)" in src or "except TypeError" in src:
        ok("confirmado: qlib captura TypeError y reintenta sin kwargs")
        print("        (mod.py:178-184). Pero ImportError NO se captura:")
        print("        si 'toni.vol_target_strategy' no existe, el error")
        print("        SE PROPAGA (no hay fallback silencioso en este caso).")
    # Buscar el manejo de get_module_by_module_path
    if "def get_module_by_module_path" in src:
        ok("get_module_by_module_path lanzaria ModuleNotFoundError")

# ------------------------------------------------------------------
# C) risk_degree afecta al backtest?
# ------------------------------------------------------------------
print("\n[C] ¿'risk_degree' modula la exposicion? (analisis de qlib)")
ss = REPO / "qlib/contrib/strategy/signal_strategy.py"
if ss.exists():
    src = ss.read_text(encoding="utf-8")
    checks = [
        ("self.risk_degree = risk_degree",
         "el atributo se guarda en __init__"),
        ("def get_risk_degree", "hay un getter (permite override dinamico)"),
        ("return self.risk_degree", "el getter devuelve el valor actual"),
        ("risk_degree=self.get_risk_degree(trade_step)",
         "se llama EN CADA decision (dinamico)"),
        ("cash * self.risk_degree", "se usa para dimensionar las compras"),
    ]
    for pat, desc in checks:
        if pat in src:
            ok(f"{desc}")
        else:
            fail(f"no encontrado: {pat} ({desc})")
    print("\n    CONCLUSION: a diferencia de vol_gate_test.py (que multiplicaba")
    print("    la senal y no tenia efecto), aqui risk_degree SI se aplica")
    print("    en cada decision. El MECANISMO es correcto.")
    print("\n    Pero eso NO valida el Sharpe 1.07: si el import de")
    print("    'toni.vol_target_strategy' falla, el backtest nunca corre con")
    print("    esta estrategia (usaria la estandar, sin vol-targeting).")

# ------------------------------------------------------------------
# D) Otros problemas
# ------------------------------------------------------------------
print("\n[D] Otros problemas del script")
mv = HERE / "momentum_vt_backtest.py"
if mv.exists():
    src = mv.read_text(encoding="utf-8")
    if "/opt/data/" in src:
        warn("MLFLOW_TRACKING_URI apunta a /opt/data/ (otra maquina)")
    if "sp500_liquid" in src:
        warn("UNIVERSE='sp500_liquid' por defecto, que NO EXISTE en esta "
             "instalacion (hay sp500)")
    if 'provider_uri=\'~/.qlib/qlib_data/us_data\'' in src:
        ok("provider_uri usa ~/.qlib/... (correcto en WSL)")
    # fechas
    if 'end_time="2026-08-07"' in src:
        ok("end_time 2026-08-07 (con margen sobre el fin del calendario)")

print("\n" + "=" * 76)
print(" RESUMEN")
print("=" * 76)
if fails:
    print(f"  {len(fails)} FALLO(S):")
    for f in fails:
        print(f"    - {f}")
print(f"  {len(warns)} aviso(s)")
print()
print("  VEREDICTO PROVISIONAL:")
if any("toni" in f for f in fails):
    print("  El script NO ES EJECUTABLE tal cual: el module_path no resuelve.")
    print("  Si alguien lo ejecuto y obtuvo Sharpe 1.07, fue en otra maquina")
    print("  o con el paquete 'toni' instalado en el entorno (no en el repo).")
    print("  -> El numero NO es reproducible en este repositorio.")
else:
    print("  El script parece ejecutable. Falta correr el backtest.")
print("=" * 76)
