"""Orchestrate reproducible nested comparisons without opening final holdout."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NESTED_RUNNER = Path(__file__).with_name("run_nested_walk_forward.py")
UNIVERSES = {
    "original_5": ("BTC", "ETH", "SOL", "XLM", "ADA"),
    "full_9": ("BTC", "ETH", "SOL", "XLM", "ADA", "XRP", "DOGE", "LINK", "LTC"),
    "reduced_8_no_xlm": ("BTC", "ETH", "SOL", "ADA", "XRP", "DOGE", "LINK", "LTC"),
}


def parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not seeds:
        raise ValueError("At least one seed is required")
    return seeds


def comparison_plan(seeds: tuple[int, ...]) -> list[dict[str, object]]:
    return [
        {"universe": name, "instruments": list(instruments), "seed": seed}
        for name, instruments in UNIVERSES.items()
        for seed in seeds
    ]


def aggregate_reports(reports: list[dict[str, object]]) -> dict[str, object]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for report in reports:
        grouped.setdefault(str(report["comparison_universe"]), []).append(report)
    result: dict[str, object] = {}
    for universe, items in grouped.items():
        fold_sharpes = [
            float(fold["test_metrics"]["sharpe"])
            for item in items
            for fold in item["folds"]
        ]
        calibrated_sharpes = [
            float(fold["calibrated_cost_metrics"]["sharpe"])
            for item in items
            for fold in item["folds"]
        ]
        calibrated_drawdowns = [
            float(fold["calibrated_cost_metrics"]["max_drawdown"])
            for item in items
            for fold in item["folds"]
        ]
        adverse_sharpes = [
            float(fold["cost_scenarios"]["adverse"]["sharpe"])
            for item in items
            for fold in item["folds"]
        ]
        outperformance = [
            float(fold["test_metrics"]["outperformance"]) > 0
            for item in items
            for fold in item["folds"]
        ]
        result[universe] = {
            "seeds": sorted(int(item["seed"]) for item in items),
            "runs": len(items),
            "fold_observations": len(fold_sharpes),
            "sharpe_mean": float(np.mean(fold_sharpes)),
            "sharpe_std": float(np.std(fold_sharpes)),
            "sharpe_min": float(np.min(fold_sharpes)),
            "sharpe_max": float(np.max(fold_sharpes)),
            "calibrated_cost_sharpe_mean": float(np.mean(calibrated_sharpes)),
            "calibrated_cost_sharpe_median": float(np.median(calibrated_sharpes)),
            "calibrated_cost_sharpe_std": float(np.std(calibrated_sharpes)),
            "calibrated_cost_sharpe_min": float(np.min(calibrated_sharpes)),
            "calibrated_cost_sharpe_max": float(np.max(calibrated_sharpes)),
            "calibrated_cost_positive_fold_fraction": float(
                np.mean(np.asarray(calibrated_sharpes) > 0)
            ),
            "maximum_drawdown_worst_fold": float(np.min(calibrated_drawdowns)),
            "adverse_cost_sharpe_mean": float(np.mean(adverse_sharpes)),
            "outperform_benchmark_fold_fraction": float(np.mean(outperformance)),
        }
    return result


def main() -> None:
    seeds = parse_seeds(os.getenv("CRYPTO_COMPARISON_SEEDS", "42,43,44"))
    output_root = Path(
        os.getenv("CRYPTO_COMPARISON_OUTPUT_DIR", "work/crypto/output/universe_comparison")
    )
    if not output_root.is_absolute():
        output_root = PROJECT_ROOT / output_root
    output_root.mkdir(parents=True, exist_ok=True)
    plan = comparison_plan(seeds)
    (output_root / "plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if os.getenv("CRYPTO_COMPARISON_DRY_RUN", "false").lower() in {"1", "true", "yes"}:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return

    reports: list[dict[str, object]] = []
    if os.getenv("CRYPTO_COMPARISON_REBUILD_ONLY", "false").lower() in {"1", "true", "yes"}:
        for item in plan:
            run_dir = output_root / f"{item['universe']}_seed_{item['seed']}"
            report = json.loads((run_dir / "nested_results.json").read_text(encoding="utf-8"))
            report["comparison_universe"] = item["universe"]
            reports.append(report)
        comparison = {
            "protocol": "same nested settings per universe; final holdout not evaluated",
            "plan": plan,
            "aggregate": aggregate_reports(reports),
        }
        (output_root / "comparison.json").write_text(
            json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(comparison, indent=2, sort_keys=True))
        return

    for item in plan:
        run_dir = output_root / f"{item['universe']}_seed_{item['seed']}"
        run_dir.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        environment.update(
            {
                "CRYPTO_INSTRUMENTS": ",".join(item["instruments"]),
                "CRYPTO_SEED": str(item["seed"]),
                "CRYPTO_NESTED_OUTPUT_DIR": str(run_dir),
            }
        )
        completed = subprocess.run(
            [sys.executable, str(NESTED_RUNNER)],
            cwd=PROJECT_ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        (run_dir / "run.log").write_text(completed.stdout, encoding="utf-8")
        if completed.returncode != 0:
            raise RuntimeError(
                f"Comparison run failed for {item['universe']} seed {item['seed']}; "
                f"see {run_dir / 'run.log'}"
            )
        report = json.loads((run_dir / "nested_results.json").read_text(encoding="utf-8"))
        if report["final_holdout"]["evaluated"] is not False:
            raise RuntimeError("A comparison run evaluated the final holdout")
        report["comparison_universe"] = item["universe"]
        reports.append(report)

    comparison = {
        "protocol": "same nested settings per universe; final holdout not evaluated",
        "plan": plan,
        "aggregate": aggregate_reports(reports),
    }
    (output_root / "comparison.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(comparison, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
