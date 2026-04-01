python research/run_workflow.py
python -m research.export_signals
python -m portfolio.rebalance data/signals/signals_2026-03-24.parquet conf/strategy.yaml
python -m execution.executor data/orders/target_positions_2026-03-24.parquet '{"AAPL":190,"MSFT":420,"NVDA":880,"AMZN":180,"META":500,"GOOGL":160,"AVGO":1350,"TSLA":175,"AMD":165,"NFLX":610,"ADBE":540}'