import pytest

from work.crypto.temporal_validation import (
    final_holdout_boundary,
    nested_walk_forward_folds,
    validate_nested_folds,
)


def test_nested_folds_are_disjoint_and_stop_before_final_holdout():
    total = 1_000
    decision_end = final_holdout_boundary(total, holdout_fraction=0.15)
    folds = nested_walk_forward_folds(decision_end, n_folds=3)
    validate_nested_folds(folds, decision_end)

    assert decision_end == 850
    assert folds[-1].test_end == 850
    assert all(fold.test_end <= decision_end for fold in folds)
    assert all(left.test_end == right.test_start for left, right in zip(folds, folds[1:]))
    assert all(fold.train_end == fold.validation_start for fold in folds)


def test_invalid_holdout_or_fold_configuration_is_rejected():
    with pytest.raises(ValueError):
        final_holdout_boundary(50)
    with pytest.raises(ValueError):
        nested_walk_forward_folds(200, n_folds=20)
