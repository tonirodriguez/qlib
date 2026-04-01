from loguru import logger
from infra.paths import LOGS_DIR


def setup_logging() -> None:
    logger.remove()
    logger.add(
        LOGS_DIR / "system.log",
        rotation="10 MB",
        retention=10,
        level="INFO",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
    )