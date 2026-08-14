import json

import pandas as pd
import pytest

from work.crypto.convert_crypto_qlib import CryptoQlibConfig, convert_to_qlib


def config_for(tmp_path, source_dir):
    return CryptoQlibConfig(
        input_csv=tmp_path / "unused.csv",
        ohlcv_dir=source_dir,
        ohlcv_file_pattern="{instrument}.csv",
        output_dir=tmp_path / "provider",
        date_column="date",
        instruments=("BTC",),
        qlib_fields=("close", "volume"),
        frequency="day",
        universe="crypto",
        start_date=None,
        end_date=None,
        dropna=False,
        instrument_case="lower",
        write_all_universe=True,
        synthesize_missing_fields=False,
        factor_default=1.0,
        dividends_default=0.0,
        splits_default=0.0,
        volume_default=0.0,
        change_fill_value=0.0,
    )


def write_source(source_dir, include_close=True):
    source_dir.mkdir()
    data = {
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "volume": [10.0, 11.0, 12.0],
    }
    if include_close:
        data["close"] = [100.0, 101.0, 102.0]
    pd.DataFrame(data).to_csv(source_dir / "BTC.csv", index=False)


def test_conversion_replaces_provider_only_after_validation(tmp_path):
    source_dir = tmp_path / "source"
    write_source(source_dir)
    config = config_for(tmp_path, source_dir)
    config.output_dir.mkdir()
    (config.output_dir / "old.txt").write_text("old provider", encoding="utf-8")

    summary = convert_to_qlib(config)

    assert not (config.output_dir / "old.txt").exists()
    assert (config.output_dir / "features" / "btc" / "close.day.bin").is_file()
    manifest = json.loads((config.output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["ordered_instruments"] == ["btc"]
    assert manifest["rows"] == 3
    assert summary["manifest"].endswith("manifest.json")
    assert not list(tmp_path.glob(".provider.staging-*"))
    assert not list(tmp_path.glob(".provider.backup-*"))


def test_failed_build_preserves_existing_provider(tmp_path):
    source_dir = tmp_path / "source"
    write_source(source_dir, include_close=False)
    config = config_for(tmp_path, source_dir)
    config.output_dir.mkdir()
    sentinel = config.output_dir / "sentinel.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    with pytest.raises(ValueError, match="close"):
        convert_to_qlib(config)

    assert sentinel.read_text(encoding="utf-8") == "keep me"
    assert not list(tmp_path.glob(".provider.staging-*"))
