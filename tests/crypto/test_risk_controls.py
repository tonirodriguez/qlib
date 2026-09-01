"""Tests para work/crypto/risk_controls.py (punto 1 de produccion v8).

Cubre stale-data, drawdown, exposure, reconciliation, kill-switch y el
orquestador run_all_checks. Al ser funciones puras no requieren red ni Qlib.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "work" / "crypto"))

from work.crypto import risk_controls as rc  # noqa: E402


TODAY = date.today()


# ---------------------------------------------------------------- stale
def test_stale_data_fresh_signal_not_blocked():
    stale, _ = rc.check_stale_data(TODAY, rc.DEFAULTS)
    assert stale is False


def test_stale_data_old_signal_blocks():
    stale, _ = rc.check_stale_data(TODAY - timedelta(days=3), rc.DEFAULTS)
    assert stale is True


def test_stale_data_iso_string_date():
    stale, _ = rc.check_stale_data(str(TODAY), rc.DEFAULTS)
    assert stale is False


# ---------------------------------------------------------------- drawdown
def test_drawdown_zero_at_peak():
    assert rc.compute_drawdown(10000, 10000) == 0.0


def test_drawdown_calculation():
    dd = rc.compute_drawdown(8500, 10000)
    assert abs(dd - 0.15) < 1e-9


def test_check_drawdown_under_limit_ok():
    over, _ = rc.check_drawdown(9000, 10000, {"max_drawdown_pct": 0.15})
    assert over is False


def test_check_drawdown_over_limit_blocks():
    over, _ = rc.check_drawdown(8000, 10000, {"max_drawdown_pct": 0.15})
    assert over is True


# ---------------------------------------------------------------- exposure
def test_exposure_total_and_per_asset():
    state = {"cash_usd": 6000.0, "positions": {"BTC": {"shares": 0.04, "entry_price": 0}}}
    prices = {"BTC": 100000.0}
    per, total = rc.compute_exposure(state, prices)
    assert abs(total - 0.40) < 1e-9  # 40% invertido
    assert abs(per["BTC"] - 0.40) < 1e-9


def test_exposure_limit_blocks_over_concentration():
    state = {"cash_usd": 5000.0, "positions": {"BTC": {"shares": 0.06, "entry_price": 0}}}
    prices = {"BTC": 100000.0}  # ~54% en BTC
    issues = rc.check_exposure(state, prices, {"max_per_asset_exposure_pct": 0.40,
                                               "max_total_exposure_pct": 0.90})
    assert any("EXPOSURE" in m and "BTC" in m for _, m in issues)


def test_exposure_total_limit_blocks():
    state = {"cash_usd": 500.0, "positions": {"BTC": {"shares": 0.05, "entry_price": 0}}}
    prices = {"BTC": 100000.0}  # ~91% invertido
    issues = rc.check_exposure(state, prices, {"max_per_asset_exposure_pct": 0.95,
                                               "max_total_exposure_pct": 0.90})
    assert any("EXPOSURE total" in m for _, m in issues)


# ---------------------------------------------------------------- reconciliation
def test_reconcile_ok_no_issues():
    state = {"cash_usd": 5000.0, "positions": {"BTC": {"shares": 0.05, "entry_price": 100000}}}
    prices = {"BTC": 100000.0}
    assert rc.reconcile(state, prices) == []


def test_reconcile_detects_negative_shares():
    state = {"cash_usd": 5000.0, "positions": {"BTC": {"shares": -1, "entry_price": 100000}}}
    prices = {"BTC": 100000.0}
    issues = rc.reconcile(state, prices)
    assert any("shares<=0" in m for m in issues)


def test_reconcile_detects_negative_cash():
    state = {"cash_usd": -100.0, "positions": {}}
    issues = rc.reconcile(state, {})
    assert any("cash_usd negativo" in m for m in issues)


def test_reconcile_detects_missing_price():
    state = {"cash_usd": 5000.0, "positions": {"SOL": {"shares": 5, "entry_price": 10}}}
    prices = {}
    issues = rc.reconcile(state, prices)
    assert any("SOL" in m and "precio" in m for m in issues)


# ---------------------------------------------------------------- kill-switch
def test_kill_switch_off_when_not_triggered():
    over, _ = rc.check_kill_switch({"kill_switch_triggered": False}, {"kill_switch_enabled": True})
    assert over is False


def test_kill_switch_blocks_when_triggered():
    over, _ = rc.check_kill_switch({"kill_switch_triggered": True}, {"kill_switch_enabled": True})
    assert over is True


def test_kill_switch_disabled_in_config():
    over, _ = rc.check_kill_switch({"kill_switch_triggered": True}, {"kill_switch_enabled": False})
    assert over is False


# ---------------------------------------------------------------- orchestrator
def test_run_all_checks_clean_state_no_issues():
    state = {"cash_usd": 10000.0, "positions": {}, "peak_capital": 10000.0,
             "kill_switch_triggered": False}
    assert rc.run_all_checks(state, {}, TODAY) == []


def test_run_all_checks_detects_drawdown():
    state = {"cash_usd": 7000.0, "positions": {}, "peak_capital": 10000.0,
             "kill_switch_triggered": False}
    issues = rc.run_all_checks(state, {}, TODAY)
    assert any("DRAWDOWN" in m for m in issues)


def test_run_all_checks_blocks_on_kill_switch():
    state = {"cash_usd": 10000.0, "positions": {}, "peak_capital": 10000.0,
             "kill_switch_triggered": True}
    issues = rc.run_all_checks(state, {}, TODAY, config={"max_drawdown_pct": 0.99})
    assert any("KILL-SWITCH" in m for m in issues)