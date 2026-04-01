from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SIGNALS_DIR = DATA_DIR / "signals"
ORDERS_DIR = DATA_DIR / "orders"
STATE_DIR = DATA_DIR / "state"
REPORTS_DIR = DATA_DIR / "reports"

for folder in [SIGNALS_DIR, ORDERS_DIR, STATE_DIR, REPORTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)