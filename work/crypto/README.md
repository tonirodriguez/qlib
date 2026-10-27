# Crypto research workspace

> [!CAUTION]
> This directory is for research and education only. It is not approved for
> live trading, investment decisions, order execution, or claims of expected
> financial performance.

## Estado actual (2026-10-27)

**Pipeline SFM: cerrado.** La auditoría de `AUDITORIA_V8.md` confirmó tres fugas de
futuro en v8; sus métricas (Sharpe 2.74, equity 20x) no son evidencia válida. El
cron diario de v8 se eliminó y no queda ningún job apuntando a ese pipeline. Los
ficheros se conservan como base de código y comparación histórica.

**Paper trading activo — dos estrategias, dos lógicas distintas:**

| Estrategia | Script | Cron | Lógica | Estado al 27-oct |
|---|---|---|---|---|
| TSMOM20 vol40/vol60-breadth | `paper_trading_tsmom.py` | diario 09:00 | momentum 20d + vol-target + filtro de amplitud | 100% efectivo: 0 señales, amplitud 0% |
| Carry de funding | `carry_paper_trading.py` | diario 09:05 | long spot + short perpetuo (funding) | carry-9 +16,82 pb, carry-majors +3,81 pb |

Capital ficticio 10.000 € por variante. Libros en `output/paper_trading/ledger.csv`
y `output/carry/paper_trading/ledger.csv`.

**Evidencia de backtest (2016-2026, 9 criptos, 10 pb por operación):** TSMOM
vol40-breadth +4.625% total (42%/año, Sharpe 1.27, DD −41%) frente a BTC buy&hold
+18.519% (Sharpe 1.06, DD −83%); carry siempre +116% (12%/año, Sharpe 4.60, DD
−6,5%). El Sharpe del carry está inflado por la baja volatilidad diaria del
funding. Correlación diaria entre ambas ≈ 0,00 (rolling 63d media −0,15), por lo
que se complementan: 50/50 sube el Sharpe a 1.85 y baja el DD a −21,4%.

**Límites:** ninguna de las dos está aprobada para capital real. El TSMOM no bate
claramente a holdear BTC en riqueza y su t-stat ≈ 1,4; el carry rinde ya solo
~4-5%/año y asume riesgo de contraparte y de funding. El paper trading debe
acumular semanas antes de decidir.

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
