"""Evaluate predeclared experiment gates without touching model data or holdout."""

from __future__ import annotations

import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def evaluate_universe(
    metrics: dict[str, float | int | list[int]], gates: dict[str, float | int | bool]
) -> dict[str, object]:
    checks = {
        "minimum_seed_count": len(metrics["seeds"]) >= int(gates["minimum_seed_count"]),
        "minimum_outer_fold_count": int(metrics["fold_observations"])
        >= len(metrics["seeds"]) * int(gates["minimum_outer_fold_count_per_seed"]),
        "calibrated_cost_sharpe_median": float(metrics["calibrated_cost_sharpe_median"])
        >= float(gates["calibrated_cost_sharpe_median_min"]),
        "positive_fold_fraction": float(metrics["calibrated_cost_positive_fold_fraction"])
        >= float(gates["calibrated_cost_positive_fold_fraction_min"]),
        "maximum_drawdown": float(metrics["maximum_drawdown_worst_fold"])
        >= float(gates["maximum_drawdown_worst_fold_min"]),
        "adverse_cost_sharpe": float(metrics["adverse_cost_sharpe_mean"])
        >= float(gates["adverse_cost_sharpe_mean_min"]),
        "benchmark_outperformance": float(metrics["outperform_benchmark_fold_fraction"])
        >= float(gates["outperform_benchmark_fold_fraction_min"]),
    }
    return {"passed": all(checks.values()), "checks": checks}


def main() -> None:
    protocol_path = PROJECT_ROOT / os.getenv(
        "CRYPTO_EXPERIMENT_PROTOCOL", "work/crypto/experiment_protocol.json"
    )
    comparison_path = PROJECT_ROOT / os.getenv(
        "CRYPTO_COMPARISON_RESULT",
        "work/crypto/output/universe_comparison/comparison.json",
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    evaluations = {
        universe: evaluate_universe(metrics, protocol["predeclared_gates"])
        for universe, metrics in comparison["aggregate"].items()
    }
    report = {
        "protocol_status": protocol["status"],
        "comparison": str(comparison_path),
        "any_universe_passed": any(item["passed"] for item in evaluations.values()),
        "holdout_may_be_opened": False,
        "evaluations": evaluations,
    }
    output = comparison_path.with_name("gate_evaluation.json")
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
