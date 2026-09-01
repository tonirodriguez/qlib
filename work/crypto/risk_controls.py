"""
risk_controls.py — Risk controls para el paper trading SFM v8.

Implementa los controles que exige el repo en "Required gates before any
real-world use" (Risk controls): stale-data protection, drawdown limit,
exposure limits, reconciliation, kill-switch y alertas.

Todas las funciones son puras (sin red ni IO) salvo `emit_alert`, que sólo
imprime/notifica. Así son testeables en offline.

Uso desde sfm_paper_trading.py:
    import risk_controls as rc
    issues = rc.run_all_checks(...)   # -> lista de alertas
    if issues: rc.emit_alerts(issues); ... (decidir si bloquear)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


# =====================================================================
# Config
# =====================================================================
# Umbrales por defecto (override por env en la integración)
DEFAULTS = {
    "max_signal_age_days": 1,        # stale: señal de hace más de 1 día -> no operar
    "max_drawdown_pct": 0.15,        # 15% drawdown -> detener
    "max_per_asset_exposure_pct": 0.40,  # máx % de cartera en una sola moneda
    "max_total_exposure_pct": 0.90,  # máx % de cartera invertida
    "kill_switch_enabled": True,
}


def normalize(state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fusiona defaults y config explícita."""
    cfg = dict(DEFAULTS)
    if config:
        cfg.update(config)
    return cfg


# =====================================================================
# 1. STALE-DATA PROTECTION
# =====================================================================
def check_stale_data(signal_date: str | date, cfg: dict[str, Any]) -> tuple[bool, str]:
    """Devuelve (es_stale, mensaje). Si la señal es vieja no se debe operar."""
    max_days = int(cfg["max_signal_age_days"])
    if isinstance(signal_date, str):
        sig = datetime.fromisoformat(signal_date).date() if "T" in signal_date else date.fromisoformat(signal_date)
    else:
        sig = signal_date
    age_days = (date.today() - sig).days
    if age_days > max_days:
        return True, f"STALE_DATA: señal de {sig} (hace {age_days}d, max {max_days}d). No operar."
    return False, f"señal fresca (hace {age_days}d)"


# =====================================================================
# 2. DRAWNDOWN LIMIT
# =====================================================================
def compute_drawdown(current_value: float, peak_capital: float) -> float:
    """Devuelve el drawdown desde el pico (fracción, ej. 0.12 = 12%)."""
    if peak_capital <= 0:
        return 0.0
    return max(0.0, (peak_capital - current_value) / peak_capital)


def check_drawdown(current_value: float, peak_capital: float, cfg: dict[str, Any]) -> tuple[bool, str]:
    """Devuelve (excede_límite, mensaje). Si drawdown > límite -> detener."""
    dd = compute_drawdown(current_value, peak_capital)
    max_dd = float(cfg["max_drawdown_pct"])
    if dd > max_dd:
        return True, f"DRAWDOWN: {dd*100:.1f}% > límite {max_dd*100:.1f}%. Detener."
    return False, f"drawdown {dd*100:.1f}% (límite {max_dd*100:.1f}%)"


# =====================================================================
# 3. EXPOSURE LIMITS
# =====================================================================
def compute_exposure(state: dict[str, Any], prices: dict[str, float]) -> tuple[dict[str, float], float]:
    """Devuelve (exposición_por_moneda, exposición_total) en fracciones de cartera."""
    total = float(state.get("cash_usd", 0.0))
    per_symbol: dict[str, float] = {}
    for sym, pos in state.get("positions", {}).items():
        price = prices.get(sym)
        if price is not None:
            total += float(pos["shares"]) * float(price)
    for sym, pos in state.get("positions", {}).items():
        price = prices.get(sym)
        if price is not None and total > 0:
            per_symbol[sym] = float(pos["shares"]) * float(price) / total
    total_exposure = 1.0 - float(state.get("cash_usd", 0.0)) / total if total > 0 else 0.0
    return per_symbol, total_exposure


def check_exposure(state: dict[str, Any], prices: dict[str, float], cfg: dict[str, Any]) -> list[tuple[bool, str]]:
    """Comprueba límites de exposición por moneda y total."""
    issues: list[tuple[bool, str]] = []
    per_symbol, total_expo = compute_exposure(state, prices)
    max_asset = float(cfg["max_per_asset_exposure_pct"])
    max_total = float(cfg["max_total_exposure_pct"])
    for sym, expo in per_symbol.items():
        if expo > max_asset:
            issues.append((True, f"EXPOSURE {sym}: {expo*100:.1f}% > límite {max_asset*100:.1f}%"))
    if total_expo > max_total:
        issues.append((True, f"EXPOSURE total: {total_expo*100:.1f}% > límite {max_total*100:.1f}%"))
    return issues


# =====================================================================
# 4. RECONCILIATION
# =====================================================================
def reconcile(state: dict[str, Any], prices: dict[str, float], epsilon: float = 1e-6) -> list[str]:
    """Valida la coherencia interna del estado vs precios.

    - Las posiciones deben tener shares>0 y entry_price>0.
    - cash_usd no negativo.
    - total = cash + Σ(shares*precio) debe ser finito y ≥ 0.
    Devuelve lista de discrepancias (vacía = OK).
    """
    issues: list[str] = []
    total_val = float(state.get("cash_usd", 0.0))
    for sym, pos in state.get("positions", {}).items():
        shares = float(pos.get("shares", 0))
        entry = float(pos.get("entry_price", 0))
        if shares <= 0:
            issues.append(f"RECON {sym}: shares<=0 ({shares})")
        if entry <= 0:
            issues.append(f"RECON {sym}: entry_price<=0 ({entry})")
        price = prices.get(sym)
        if price is not None:
            total_val += shares * float(price)
        else:
            issues.append(f"RECON {sym}: sin precio disponible")
    if float(state.get("cash_usd", 0.0)) < -epsilon:
        issues.append(f"RECON: cash_usd negativo ({state['cash_usd']:.4f})")
    if not (total_val >= 0) or total_val != total_val:  # también atrapa NaN
        issues.append(f"RECON: valor total inválido ({total_val})")
    return issues


# =====================================================================
# 5. KILL-SWITCH
# =====================================================================
def check_kill_switch(state: dict[str, Any], cfg: dict[str, Any]) -> tuple[bool, str]:
    """Devuelve (activo, mensaje). Si kill_switch está ON en estado -> detener."""
    enabled = bool(cfg.get("kill_switch_enabled", True))
    if not enabled:
        return False, "kill-switch deshabilitado en config"
    if state.get("kill_switch_triggered", False):
        return True, "KILL-SWITCH: activado manualmente. NO operar."
    return False, "kill-switch OK"


# =====================================================================
# 6. ALERTAS
# =====================================================================
def emit_alerts(issues: list[str]) -> None:
    """Notifica las alertas (por ahora a consola/log; se puede añadir TG/email)."""
    if not issues:
        return
    for msg in issues:
        print(f"   🚨 ALERTA: {msg}")


# =====================================================================
# ORQUESTACIÓN
# =====================================================================
def run_all_checks(
    state: dict[str, Any],
    prices: dict[str, float],
    signal_date: str | date,
    peak_capital: float | None = None,
    config: dict[str, Any] | None = None,
) -> list[str]:
    """Ejecuta todos los checks. Devuelve lista de alertas bloqueantes.

    Una alerta con prefijo en mayúsculas (STALE_DATA, DRAWDOWN, EXPOSURE,
    KILL-SWITCH) indica que la operación debe bloquearse.
    Las de RECON indican datos inconsistentes (bloqueante también).
    """
    cfg = normalize(state, config)
    issues: list[str] = []

    stale, msg = check_stale_data(signal_date, cfg)
    if stale:
        issues.append(msg)

    current_total = compute_total_value(state, prices)
    peak = peak_capital if peak_capital is not None else float(state.get("peak_capital", current_total))
    dd_over, dd_msg = check_drawdown(current_total, peak, cfg)
    if dd_over:
        issues.append(dd_msg)

    for _, exp_msg in check_exposure(state, prices, cfg):
        issues.append(exp_msg)

    issues.extend(reconcile(state, prices))

    ks_off, ks_msg = check_kill_switch(state, cfg)
    if ks_off:
        issues.append(ks_msg)

    return issues


def compute_total_value(state: dict[str, Any], prices: dict[str, float]) -> float:
    total = float(state.get("cash_usd", 0.0))
    for sym, pos in state.get("positions", {}).items():
        price = prices.get(sym)
        if price is not None:
            total += float(pos["shares"]) * float(price)
    return total


# =====================================================================
# CLI de prueba rápida
# =====================================================================
if __name__ == "__main__":
    # Smoke test
    demo_state = {"cash_usd": 8000.0, "positions": {"BTC": {"shares": 0.02, "entry_price": 100000}},
                  "peak_capital": 11000.0, "kill_switch_triggered": False}
    demo_prices = {"BTC": 95000.0}
    for issue in run_all_checks(demo_state, demo_prices, date.today(), config={"max_drawdown_pct": 0.10}):
        print(" ", issue)
    print("smoke OK")