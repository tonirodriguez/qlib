# Crypto research workspace

> [!CAUTION]
> This directory is for research and education only. It is not approved for
> live trading, investment decisions, order execution, or claims of expected
> financial performance.

## Status of the experiments

The current SFM v2, v3, and v4 experiments have a known temporal data leakage:
wavelet denoising is applied to the complete time series before the
train/validation/test split. In v4, global percentile clipping is also computed
before that split. Consequently, future observations can influence historical
features.

All metrics, charts, JSON reports, and model checkpoints produced by those
versions are **invalid as out-of-sample financial evidence**. They may be kept
for debugging and historical comparison, but must not be promoted, deployed,
or used to select a trading strategy. Retraining the same code does not remove
the leakage.

`qlib_sfm_pipeline.v5.py` and `output/optuna_sfm_v5/` are SP500 equity
experiments despite their location in this directory. They are not crypto
models or crypto results. Their current outputs are also research-only and
share the same non-causal denoising limitation.

The original pipeline, `qlib_sfm_pipeline.py`, and
`qlib_sfm_pipeline_grafica.py` are earlier prototypes, not validated production
alternatives. `generate_daily_signals.py` is an incomplete experiment and must
not be scheduled or connected to an exchange.

## Canonical data path

For crypto data work, the intended path is:

1. `download_crypto.py` downloads public OHLCV data through ccxt into CSV files.
2. `convert_crypto_qlib.py` converts the configured CSV inputs into a Qlib data
   provider.
3. `use_crypto.py` performs a read-only provider and feature smoke check.
4. A future validated training pipeline may consume that provider only after
   the gates below pass.

The default research universe is `BTC, ETH, SOL, XLM, ADA, XRP, DOGE, LINK,
LTC`. It is configurable through `CRYPTO_INSTRUMENTS`; every run must record
the exact ordered universe because it defines the model's input/output schema.

Configuration is read from the repository-root `.env` file or environment
variables. Secrets must never be committed. The current downloader uses public
market data and does not require exchange credentials.

The older collector under `scripts/data_collector/crypto/` is a separate
CoinGecko ingestion path. Do not silently mix CoinGecko and ccxt/Binance data in
one experiment; record the source and dataset version explicitly.

## Required gates before any real-world use

No model or signal from this workspace may progress beyond research until all
of these conditions are met:

- Causality: changing data after time `t` cannot change features or predictions
  at or before `t`; preprocessing is fitted independently inside each temporal
  fold.
- Evaluation: hyperparameter selection is nested within walk-forward windows,
  with a final untouched holdout and reproducible dataset/run manifests.
- Execution model: backtests apply costs on position changes and model spread,
  slippage, liquidity, funding/borrow, latency, and the 24/7 crypto calendar.
- Data quality: timestamps are UTC, candles are closed and fresh, OHLCV schema
  and continuity are validated, and dataset provenance and hashes are stored.
- Reproducibility: dependencies are locked and a clean environment can rerun a
  small experiment and its tests from documented configuration.
- Testing: offline tests cover ingestion, conversion, labels, temporal splits,
  anti-leakage invariants, costs, serialization, and model/scaler/schema
  compatibility.
- Risk controls: paper trading has reconciliation, exposure and drawdown limits,
  stale-data protection, alerts, and a tested kill switch. Live credentials, if
  ever introduced, are least-privilege and withdrawal-disabled.
- Review: data, model, backtest, and operational-risk reviews explicitly approve
  the exact version proposed for use.

Until every gate passes, outputs must retain the labels **research-only** and
**not valid out-of-sample evidence**.

## Remediation candidate

`qlib_sfm_pipeline.v4.py` now defaults to a remediation configuration: global
wavelet denoising is disabled, clipping and scaling are fitted from training
observations only, crypto metrics annualize over 365 days, and transaction
costs are charged on actual position changes. It writes to
`output/optuna_sfm_v4_causal/` so that it cannot overwrite the invalid legacy
evidence. The old walk-forward report is disabled because hyperparameter
selection is not yet nested inside each window.

These changes make v4 a candidate for further validation, not an approved
strategy. A fresh run, nested walk-forward implementation, untouched holdout,
cost sensitivity analysis and the remaining gates above are still required.

## Output policy

See `output/README.md` before interpreting or adding generated artifacts.
Future output directories should include a manifest containing at least the Git
commit, dirty-worktree status, configuration, dependency versions, random
seeds, data source and hash, temporal ranges, feature schema, preprocessing
fit ranges, cost assumptions, and artifact checksums.
