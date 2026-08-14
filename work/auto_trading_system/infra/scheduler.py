from time import sleep
from infra.logging_conf import setup_logging
from infra.db import init_db
from infra.scheduler import start_scheduler
from run_daily import run_pipeline

setup_logging()
init_db()
scheduler = start_scheduler(run_pipeline)

while True:
    sleep(60)