"""
watchdog_v8.py — Vigilancia de "pipeline detenido / datos obsoletos" (Paso 7).

Cumple la alerta pendiente del checklist de produccion:
  "Alertas de pipeline detenido / falta de datos".

Comprueba el estado de salud de la operativa diaria de SFM v8:
  1. FRESHNESS del pipeline: que el cron diario haya corrido recientemente
     (se detecta por un log de pipeline en output/sfm_v8/logs/ con fecha reciente).
  2. FRESHNESS de datos: que la ultima fecha en data/qlib sea reciente
     (no haya gap de datos).
  3. Estado del paper (posiciones/cash) - informe.

Si algo falla, notifica a Telegram via notifications.py (bot @oscarbot_toni_bot).
Si todo esta OK en modo vigilancia, es silencioso (no molesta).

Uso:
  <python> work/crypto/watchdog_v8.py            # vigilancia (silencioso si OK)
  <python> work/crypto/watchdog_v8.py --report   # informe de salud (notifica siempre)
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work" / "crypto"))

from notifications import send_message  # noqa: E402

OUT_DIR = PROJECT_ROOT / "work" / "crypto" / "output" / "sfm_v8"
LOGS_DIR = OUT_DIR / "logs"
QLIB_DIR = PROJECT_ROOT / "data" / "qlib"
STATE_FILE = OUT_DIR / "state_paper_trading.json"

# Cuanto tiempo puede pasar sin pipeline antes de disparar alerta (horas)
MAX_PIPELINE_STALE_HOURS = 27
# Cuantos dias sin actualizar datos antes de disparar alerta
MAX_DATA_STALE_DAYS = 2


def recent_pipeline_log(max_hours: float = MAX_PIPELINE_STALE_HOURS) -> bool:
    """True si hay un log de pipeline con antiguedad <= max_hours."""
    import time
    if not LOGS_DIR.exists():
        return False
    cutoff = time.time() - max_hours * 3600
    for f in LOGS_DIR.glob("pipeline_*.log"):
        try:
            if f.stat().st_mtime >= cutoff:
                return True
        except OSError:
            continue
    return False


def data_freshness_days() -> int | None:
    """Dias desde la ultima fecha en data/qlib con datos, o None si no se determina."""
    inst_file = QLIB_DIR / "instruments" / "crypto.txt"
    if not inst_file.exists():
        return None
    last_dates = []
    for line in inst_file.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and not parts[0].startswith("#"):
            last_dates.append(parts[2])
    if not last_dates:
        return None
    latest = max(last_dates)
    try:
        last_ts = dt.datetime.strptime(latest, "%Y-%m-%d")
    except ValueError:
        try:
            last_ts = dt.datetime.strptime(latest, "%Y/%m/%d")
        except ValueError:
            return None
    return (dt.datetime.now() - last_ts).days


def read_state() -> dict | None:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return None
    return None


def check() -> dict:
    """Devuelve el diagnostico de salud completo."""
    pipeline_ok = recent_pipeline_log()
    data_days = data_freshness_days()
    data_ok = data_days is not None and data_days <= MAX_DATA_STALE_DAYS

    state = read_state()
    n_positions = len(state.get("positions", {})) if state else 0
    cash = state.get("cash_usd") if state else None
    total = state.get("capital_usd") if state else None  # capital total del paper

    issues = []
    if not pipeline_ok:
        issues.append(
            f"⛔ PIPELINE DETENIDO: no hay log de pipeline en las últimas "
            f"{MAX_PIPELINE_STALE_HOURS}h. Revisa el cron diario (9:00) y {LOGS_DIR}."
        )
    if not data_ok:
        issues.append(
            f"⚠️ DATOS OBSOLETOS: última fecha en data/qlib hace {data_days} días "
            f"(máx permitido {MAX_DATA_STALE_DAYS}). Revisa update_crypto_daily_coinbase.py."
        )
    if state is None:
        issues.append("⚠️ Estado del paper no encontrado (state_paper_trading.json).")

    return {
        "pipeline_ok": pipeline_ok,
        "data_freshness_days": data_days,
        "data_ok": data_ok,
        "state_found": state is not None,
        "n_positions": n_positions,
        "cash_usd": cash,
        "total_value": total,
        "healthy": len(issues) == 0,
        "issues": issues,
    }


def build_message(diag: dict, force: bool = False) -> str | None:
    """Construye el mensaje a enviar. None = no enviar (todo OK y no --report)."""
    lines = []
    if not diag["healthy"]:
        lines.append("🩺 HEALTHCHECK SFM v8 — PROBLEMA DETECTADO")
        lines += diag["issues"]
    elif force:
        lines.append("🩺 HEALTHCHECK SFM v8 — OK")
    else:
        return None  # todo OK, modo vigilancia: silencioso

    # Info del estado (siempre)
    if diag["state_found"]:
        cash_txt = diag["cash_usd"] if diag["cash_usd"] is not None else "n/d"
        total_txt = diag["total_value"] if diag["total_value"] is not None else "n/d"
        lines.append(f"  Posiciones abiertas: {diag['n_positions']} | Cash: ${cash_txt} | Total: {total_txt}")
    data_txt = "al día" if diag["data_ok"] else f"STALE {diag['data_freshness_days']}d"
    lines.append(f"  Dataset data/qlib: {data_txt}")
    return "\n".join(lines)


def main():
    force_report = "--report" in sys.argv
    diag = check()
    msg = build_message(diag, force=force_report)
    if msg:
        send_message(msg, subject="🩺 Healthcheck v8")
        print(msg)
    else:
        print("✅ Healthcheck OK (silencioso)")


if __name__ == "__main__":
    main()