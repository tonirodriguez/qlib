"""Temporal split primitives shared by crypto validation workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class NestedFold:
    train_start: int
    train_end: int
    validation_start: int
    validation_end: int
    test_start: int
    test_end: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def final_holdout_boundary(n_total: int, holdout_fraction: float = 0.15) -> int:
    if n_total < 100:
        raise ValueError("At least 100 observations are required")
    if not 0 < holdout_fraction < 0.5:
        raise ValueError("holdout_fraction must be in (0, 0.5)")
    boundary = int(n_total * (1.0 - holdout_fraction))
    if boundary <= 0 or boundary >= n_total:
        raise ValueError("Invalid final holdout boundary")
    return boundary


def nested_walk_forward_folds(
    decision_rows: int,
    n_folds: int = 3,
    initial_train_fraction: float = 0.50,
    validation_fraction: float = 0.10,
) -> list[NestedFold]:
    """Create expanding nested folds entirely inside the decision sample.

    Validation immediately precedes each outer test. Outer test blocks are
    disjoint and never cross ``decision_rows``, the final-holdout boundary.
    """
    if decision_rows < 100:
        raise ValueError("At least 100 decision observations are required")
    if n_folds < 2:
        raise ValueError("At least two nested folds are required")
    if not 0.2 <= initial_train_fraction < 0.8:
        raise ValueError("initial_train_fraction must be in [0.2, 0.8)")
    if not 0.05 <= validation_fraction < 0.3:
        raise ValueError("validation_fraction must be in [0.05, 0.3)")

    initial_train = int(decision_rows * initial_train_fraction)
    validation_size = int(decision_rows * validation_fraction)
    remaining = decision_rows - initial_train - validation_size
    test_size = remaining // n_folds
    if test_size < 10:
        raise ValueError("Not enough rows for the requested number of folds")

    folds: list[NestedFold] = []
    for index in range(n_folds):
        test_start = initial_train + validation_size + index * test_size
        test_end = decision_rows if index == n_folds - 1 else test_start + test_size
        validation_end = test_start
        validation_start = validation_end - validation_size
        folds.append(
            NestedFold(
                train_start=0,
                train_end=validation_start,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    return folds


def validate_nested_folds(folds: list[NestedFold], decision_rows: int) -> None:
    if not folds:
        raise ValueError("At least one fold is required")
    previous_test_end: int | None = None
    for fold in folds:
        if not (
            fold.train_start == 0
            and fold.train_end == fold.validation_start
            and fold.validation_start < fold.validation_end == fold.test_start
            and fold.test_start < fold.test_end <= decision_rows
        ):
            raise ValueError(f"Invalid temporal fold: {fold}")
        if previous_test_end is not None and fold.test_start != previous_test_end:
            raise ValueError("Outer test windows must be contiguous and disjoint")
        previous_test_end = fold.test_end
    if folds[-1].test_end != decision_rows:
        raise ValueError("Nested folds must stop exactly at the holdout boundary")
