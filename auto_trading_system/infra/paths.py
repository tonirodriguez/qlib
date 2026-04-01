from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

SIGNALS_DIR = DATA_DIR / "signals"
ORDERS_DIR = DATA_DIR / "orders"
REPORTS_DIR = DATA_DIR / "reports"
LOGS_DIR = DATA_DIR / "logs"
STATE_DIR = DATA_DIR / "state"

for folder in [SIGNALS_DIR, ORDERS_DIR, REPORTS_DIR, LOGS_DIR, STATE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

DB_PATH = STATE_DIR / "trading.db"