"""Tests para work/crypto/paper_metrics.py (Paso 6 produccion v8).

Verifica el calculo de metricas, la derivacion de retornos desde el historial
y el snapshot, sin red ni dependencia de Qlib.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "work" / "crypto"))

from work.crypto import paper_metrics as pm  # noqa: E402


def test_compute_metrics_unknown_numpy_unused():
    # retornos sinteticos de un activo alcista estable
    returns = np.array([0.01, 0.01, 0.01, 0.01, -0.005, 0.01, 0.01, 0.01, 0.01, 0.01])
    m = pm.compute_metrics(returns, 10000.0)
    assert m["n_days"] == 10
    assert m["total_return_pct"] > 0
    assert m["win_rate_pct"] > 50.0
    assert m["sharpe"] > 0
    assert m["max_drawdown_pct"] < 0  # max_drawdown es negativo (subtractivo)


def test_compute_metrics_empty_history():
    m = pm.compute_metrics(np.array([]), 10000.0)
    assert m["n_days"] == 0
    assert "note" in m


def test_compute_metrics_all_losses():
    returns = np.array([-0.02, -0.02, -0.02, -0.02])
    m = pm.compute_metrics(returns, 10000.0)
    assert m["total_return_pct"] < 0
    assert m["win_rate_pct"] == 0.0


def test_snapshot_metrics_positive():
    s = pm.snapshot_metrics(11000.0, 10000.0)
    assert s["total_return_pct"] == 10.0


def test_snapshot_metrics_negative():
    s = pm.snapshot_metrics(9000.0, 10000.0)
    assert s["total_return_pct"] == -10.0


def test_returns_from_history_total_value(tmp_path):
    # csv con columna total_value -> retornos por pct_change
    csv = tmp_path / "h.csv"
    csv.write_text("date,total_value\n2026-09-01,10000\n2026-09-02,10100\n2026-09-03,10150\n")
    rets = pm.returns_from_history(csv, 10000.0)
    assert len(rets) == 2
    np.testing.assert_allclose(rets, [0.01, 0.0049504950], atol=1e-9)


def test_save_metrics_creates_json(tmp_path, monkeypatch):
    out = tmp_path / "metrics.json"
    monkeypatch.setattr(pm, "METRICS_OUT", out)
    pm.save_metrics({"n_days": 5, "sharpe": 1.2})
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["sharpe"] == 1.2