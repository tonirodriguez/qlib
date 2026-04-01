from pathlib import Path
import subprocess

from loguru import logger


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "conf" / "workflow_lightgbm.yaml"

    cmd = ["qrun", str(config_path)]
    logger.info(f"Running workflow: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=base_dir, check=False)
    if result.returncode != 0:
        raise SystemExit(f"qrun failed with exit code {result.returncode}")

    logger.info("Workflow completed successfully.")


if __name__ == "__main__":
    main()