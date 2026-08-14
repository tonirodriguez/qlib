import importlib.util
from pathlib import Path

import pytest


def test_legacy_daily_signal_path_is_fail_closed():
    path = Path(__file__).parents[2] / "work" / "crypto" / "generate_daily_signals.py"
    spec = importlib.util.spec_from_file_location("generate_daily_signals", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(RuntimeError, match="disabled"):
        module.generate_daily_signals(None, None)
