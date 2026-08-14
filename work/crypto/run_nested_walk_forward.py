"""Nested walk-forward model selection that never evaluates the final holdout."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import random

import numpy as np
import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
import pandas as pd
import qlib
from qlib.config import REG_US
from sklearn.preprocessing import MinMaxScaler
import torch
from torch.utils.data import DataLoader, TensorDataset

from calibrate_execution_costs import estimate_asset_costs
from research_utils import apply_clip_bounds, fit_clip_bounds
from temporal_validation import (
    final_holdout_boundary,
    nested_walk_forward_folds,
    validate_nested_folds,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_PATH = Path(__file__).with_name("qlib_sfm_pipeline.v4.py")
DEFAULT_SEED = 42


def load_pipeline_module():
    spec = importlib.util.spec_from_file_location("crypto_sfm_v4", PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {PIPELINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def env_path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


def make_study(fold_index: int, seed: int) -> optuna.Study:
    return optuna.create_study(
        direction="minimize",
        sampler=TPESampler(seed=seed + fold_index),
        pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=3, interval_steps=1),
        study_name=f"sfm_nested_fold_{fold_index + 1}",
        storage=None,
    )


def fold_cost_vector(
    instruments: list[str], source_dir: Path, train_end_date: pd.Timestamp, order_notional: float
) -> np.ndarray:
    costs: list[float] = []
    cutoff = pd.Timestamp(train_end_date)
    if cutoff.tzinfo is None:
        cutoff = cutoff.tz_localize("UTC")
    for instrument in instruments:
        frame = pd.read_csv(source_dir / f"{instrument.upper()}.csv")
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        train_frame = frame[frame["date"] <= cutoff]
        estimate = estimate_asset_costs(train_frame, (order_notional,))[0]
        costs.append(float(estimate["one_way_cost"]))
    return np.asarray(costs, dtype=float)


def run() -> dict[str, object]:
    pipeline = load_pipeline_module()
    seed = int(os.getenv("CRYPTO_SEED", str(DEFAULT_SEED)))
    pipeline.SEED = seed
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    instruments = [
        value.strip().lower()
        for value in os.getenv(
            "CRYPTO_INSTRUMENTS", "BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC"
        ).split(",")
        if value.strip()
    ]
    provider = env_path("CRYPTO_QLIB_OUTPUT_DIR", "data/qlib_crypto")
    output_dir = env_path("CRYPTO_NESTED_OUTPUT_DIR", "work/crypto/output/nested_walk_forward")
    output_dir.mkdir(parents=True, exist_ok=True)
    start_date = os.getenv("CRYPTO_START_DATE", "2023-08-11")
    end_date = os.getenv("CRYPTO_END_DATE", pd.Timestamp.utcnow().strftime("%Y-%m-%d"))
    holdout_fraction = float(os.getenv("CRYPTO_FINAL_HOLDOUT_FRACTION", "0.15"))
    n_folds = int(os.getenv("CRYPTO_NESTED_FOLDS", "3"))
    n_trials = int(os.getenv("CRYPTO_NESTED_TRIALS", "30"))
    final_epochs = int(os.getenv("CRYPTO_NESTED_FINAL_EPOCHS", "60"))
    order_notional = float(os.getenv("CRYPTO_ORDER_NOTIONAL", "10000"))
    ohlcv_dir = env_path("CRYPTO_OHLCV_DIR", "scripts/crypto/csv_data/crypto/ohlcv")

    qlib.init(
        provider_uri=str(provider),
        region=REG_US,
        kernels=int(os.getenv("QLIB_KERNELS", "1")),
    )
    market, labels, dates = pipeline.load_and_process_crypto_data(
        instruments, start_date, end_date, denoise=False
    )
    decision_end = final_holdout_boundary(len(market), holdout_fraction)
    folds = nested_walk_forward_folds(
        decision_end,
        n_folds=n_folds,
        initial_train_fraction=float(os.getenv("CRYPTO_NESTED_INITIAL_TRAIN_FRACTION", "0.50")),
        validation_fraction=float(os.getenv("CRYPTO_NESTED_VALIDATION_FRACTION", "0.10")),
    )
    validate_nested_folds(folds, decision_end)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    results: list[dict[str, object]] = []

    for fold_index, fold in enumerate(folds):
        train_market = market[fold.train_start : fold.train_end]
        validation_market = market[fold.validation_start : fold.validation_end]
        test_market = market[fold.test_start : fold.test_end]
        train_labels = labels[fold.train_start : fold.train_end]
        validation_labels = labels[fold.validation_start : fold.validation_end]
        test_labels = labels[fold.test_start : fold.test_end]

        bounds = fit_clip_bounds(train_market)
        train_market = apply_clip_bounds(train_market, bounds)
        validation_market = apply_clip_bounds(validation_market, bounds)
        test_market = apply_clip_bounds(test_market, bounds)
        scaler = MinMaxScaler(feature_range=(-1, 1))
        train_scaled = scaler.fit_transform(train_market)
        validation_scaled = scaler.transform(validation_market)
        test_scaled = scaler.transform(test_market)

        study = make_study(fold_index, seed)
        study.optimize(
            lambda trial: pipeline.objective(
                trial,
                instruments,
                train_scaled,
                train_labels,
                validation_scaled,
                validation_labels,
                market.shape[1],
                len(instruments),
                device,
            ),
            n_trials=n_trials,
            show_progress_bar=False,
        )
        params = study.best_trial.params
        lookback = params["lookback"]
        X_train, y_train = pipeline.make_sliding_windows(train_scaled, train_labels, lookback)
        X_validation, y_validation = pipeline.make_sliding_windows(
            validation_scaled, validation_labels, lookback
        )
        X_test, y_test = pipeline.make_sliding_windows(test_scaled, test_labels, lookback)
        combined_loader = DataLoader(
            TensorDataset(
                torch.cat([X_train, X_validation]),
                torch.cat([y_train, y_validation]),
            ),
            batch_size=params["batch_size"],
            shuffle=False,
        )
        torch.manual_seed(seed + 10_000 + fold_index)
        model = pipeline.SFMModelRefined(
            market.shape[1],
            params["hidden_dim"],
            params["freq_components"],
            len(instruments),
            dropout_rate=params["dropout_rate"],
        ).to(device)
        model_path = output_dir / f"sfm_nested_fold_{fold_index + 1}.pth"
        model = pipeline.train_final(
            model,
            combined_loader,
            None,
            epochs=final_epochs,
            lr=params["lr"],
            weight_decay=params["weight_decay"],
            device=device,
            patience=int(os.getenv("CRYPTO_NESTED_PATIENCE", "10")),
            model_path=str(model_path),
        )
        one_way_costs = fold_cost_vector(
            instruments,
            ohlcv_dir,
            dates[fold.train_end - 1],
            order_notional,
        )
        metrics = pipeline.evaluate_trial(
            model, X_test, y_test, device, one_way_costs=one_way_costs
        )
        results.append(
            {
                "fold": fold_index + 1,
                "boundaries": fold.to_dict(),
                "date_ranges": {
                    "train": [dates[fold.train_start].isoformat(), dates[fold.train_end - 1].isoformat()],
                    "validation": [
                        dates[fold.validation_start].isoformat(),
                        dates[fold.validation_end - 1].isoformat(),
                    ],
                    "test": [dates[fold.test_start].isoformat(), dates[fold.test_end - 1].isoformat()],
                },
                "best_validation_sharpe": float(-study.best_value),
                "best_params": params,
                "cost_calibration": {
                    "order_notional": order_notional,
                    "trained_through": dates[fold.train_end - 1].isoformat(),
                    "one_way_cost_by_asset": {
                        asset: float(cost)
                        for asset, cost in zip(instruments, one_way_costs)
                    },
                    "source": "train-only daily OHLCV proxy",
                },
                "test_metrics": {
                    key: float(metrics[key])
                    for key in (
                        "test_loss", "equity_final", "benchmark_final", "sharpe",
                        "direction_acc", "max_drawdown", "turnover", "outperformance",
                    )
                },
                "cost_scenarios": metrics["cost_scenarios"],
                "calibrated_cost_metrics": metrics["calibrated_cost_metrics"],
            }
        )

    sharpe_values = [result["test_metrics"]["sharpe"] for result in results]
    report: dict[str, object] = {
        "protocol": "nested_walk_forward",
        "seed": seed,
        "instruments": instruments,
        "decision_rows": decision_end,
        "final_holdout": {
            "evaluated": False,
            "rows": len(market) - decision_end,
            "start": dates[decision_end].isoformat(),
            "end": dates[-1].isoformat(),
        },
        "n_trials_per_fold": n_trials,
        "folds": results,
        "aggregate": {
            "sharpe_mean": float(np.mean(sharpe_values)),
            "sharpe_std": float(np.std(sharpe_values)),
            "sharpe_min": float(np.min(sharpe_values)),
            "sharpe_max": float(np.max(sharpe_values)),
        },
    }
    (output_dir / "nested_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    run()
