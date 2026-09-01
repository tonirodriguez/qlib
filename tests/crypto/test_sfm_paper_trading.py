"""Tests de logica de operaciones del paper trading SFM v8 (sin red ni Qlib).

Cubre default_state, value_portfolio y la logica de execute_trades con
precios/senales sinteticos (sin tocar el state real ni hacer llamadas de red).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "work" / "crypto"))

import sfm_paper_trading as pt  # noqa: E402


# ---------------------------------------------------------------- estado base
def test_default_state_has_expected_structure():
    st = pt.default_state()
    assert st["capital_usd"] > 0
    assert st["cash_usd"] == st["capital_usd"]
    assert st["positions"] == {}
    assert st["total_trades"] == 0
    assert "peak_capital" in st


# ---------------------------------------------------------------- valoracion
def test_value_portfolio_all_cash():
    st = pt.default_state()
    total, details = pt.value_portfolio(st, {"BTC": 100000})
    assert total == st["capital_usd"]
    assert details == []


def test_value_portfolio_with_position():
    st = {"cash_usd": 6000.0, "positions": {"BTC": {"shares": 0.04, "entry_price": 90000}}}
    total, details = pt.value_portfolio(st, {"BTC": 100000})
    assert abs(total - (6000 + 0.04 * 100000)) < 1e-6  # cash + 4000
    assert len(details) == 1
    assert details[0]["symbol"] == "BTC"
    # el codigo redondea pnl_pct a 2 decimales (11.11), comparar con tolerancia de redondeo
    expected = round((100000 - 90000) / 90000 * 100, 2)
    assert details[0]["pnl_pct"] == expected


# ---------------------------------------------------------------- execute_trades
def test_execute_sells_when_signal_not_buy():
    st = {"cash_usd": 4000.0, "positions": {"BTC": {"shares": 0.05, "entry_price": 90000}},
          "total_trades": 0, "wins": 0, "losses": 0, "total_fees_paid": 0.0}
    signal = {"signals": [{"crypto": "BTC", "signal": "🔻 VENTA", "confidence": "MEDIA",
                           "score": 0.0}]}
    trades = pt.execute_trades(st, signal, {"BTC": 100000})
    assert any(t["type"] == "SELL" for t in trades)
    assert "BTC" not in st["positions"]
    assert st["total_trades"] == 1


def test_execute_does_not_buy_below_min_confidence():
    st = {"cash_usd": 9000.0, "positions": {}, "total_trades": 0, "wins": 0,
          "losses": 0, "total_fees_paid": 0.0}
    signal = {"signals": [{"crypto": "BTC", "signal": "🟢 COMPRA", "confidence": "MEDIA",
                           "score": 0.01}]}
    trades = pt.execute_trades(st, signal, {"BTC": 100000})
    # MIN_CONFIDENCE es ALTA por default, MEDIA no debe comprar
    assert all(t["type"] != "BUY" for t in trades)


def test_execute_buys_when_high_confidence():
    st = {"cash_usd": 9000.0, "positions": {}, "total_trades": 0, "wins": 0,
          "losses": 0, "total_fees_paid": 0.0}
    signal = {"signals": [{"crypto": "BTC", "signal": "🟢 COMPRA", "confidence": "ALTA",
                           "score": 0.05}]}
    trades = pt.execute_trades(st, signal, {"BTC": 100000})
    assert any(t["type"] == "BUY" for t in trades)
    assert "BTC" in st["positions"]
    assert st["total_trades"] == 1


def test_execute_does_not_buy_same_position_twice():
    st = {"cash_usd": 9000.0, "positions": {"BTC": {"shares": 0.02, "entry_price": 100000}},
          "total_trades": 0, "wins": 0, "losses": 0, "total_fees_paid": 0.0}
    signal = {"signals": [{"crypto": "BTC", "signal": "🟢 COMPRA", "confidence": "ALTA",
                           "score": 0.05}]}
    trades = pt.execute_trades(st, signal, {"BTC": 100000})
    assert all(t["type"] != "BUY" for t in trades)  # ya tiene posicion


def test_fee_charged_on_buy():
    st = {"cash_usd": 9000.0, "positions": {}, "total_trades": 0, "wins": 0,
          "losses": 0, "total_fees_paid": 0.0}
    cost_before = st["total_fees_paid"]
    signal = {"signals": [{"crypto": "BTC", "signal": "🟢 COMPRA", "confidence": "ALTA",
                           "score": 0.05}]}
    pt.execute_trades(st, signal, {"BTC": 100000})
    assert st["total_fees_paid"] > cost_before  # se pago fee


def test_respects_max_positions():
    # Con MAX_POSITIONS default=2, no compra > 2 posiciones en un dia
    st = {"cash_usd": 20000.0, "positions": {}, "total_trades": 0, "wins": 0,
          "losses": 0, "total_fees_paid": 0.0}
    signs = [{"crypto": c, "signal": "🟢 COMPRA", "confidence": "ALTA", "score": 0.05}
             for c in ["BTC", "ETH", "SOL", "ADA"]]
    signal = {"signals": signs}
    prices = {c: 1000 for c in ["BTC", "ETH", "SOL", "ADA"]}
    pt.execute_trades(st, signal, prices)
    assert len(st["positions"]) <= pt.MAX_POSITIONS