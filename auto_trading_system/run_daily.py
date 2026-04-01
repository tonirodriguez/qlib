from infra.logging_conf import setup_logging
from infra.db import init_db
from research.run_workflow import main as run_workflow
from research.export_signals import export_latest_predictions
from portfolio.rebalance import build_target_positions
from execution.executor import execute_target_positions

def fetch_mock_prices():
    return {
        "BKR": 190.0,
        "SNDK": 420.0,
        "Q": 880.0,
        "DLTR": 180.0,
        "WRB": 500.0,
        "WDAY": 160.0,
        "VRSK": 1350.0,
        "AOS": 175.0,
        "AMD": 165.0,
        "ANET": 610.0,
        "WEC": 540.0,
    }


def run_pipeline():
    run_workflow()
    signal_path = export_latest_predictions(experiment_name="backtest_analysis")
    target_path = build_target_positions(signal_path, "conf/strategy.yaml")
    prices = fetch_mock_prices()
    execute_target_positions(target_path, prices)


if __name__ == "__main__":
    setup_logging()
    init_db()
    run_pipeline()