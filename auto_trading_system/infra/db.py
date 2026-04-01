import sqlite3
from contextlib import contextmanager
from infra.paths import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    date TEXT NOT NULL,
    instrument TEXT NOT NULL,
    score REAL NOT NULL,
    rank INTEGER,
    model_version TEXT,
    PRIMARY KEY (date, instrument, model_version)
);

CREATE TABLE IF NOT EXISTS target_positions (
    date TEXT NOT NULL,
    instrument TEXT NOT NULL,
    target_weight REAL NOT NULL,
    score REAL,
    rank INTEGER,
    PRIMARY KEY (date, instrument)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    instrument TEXT NOT NULL,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    price REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    instrument TEXT NOT NULL,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    price REAL NOT NULL,
    fee REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS broker_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
