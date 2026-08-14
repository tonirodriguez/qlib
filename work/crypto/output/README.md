# Generated experiment outputs

> [!WARNING]
> Every artifact currently stored below this directory is research-only and
> must not be used for live trading, investment decisions, or performance
> claims.

## `optuna_sfm_v4`

The JSON metrics, PNG charts, and `.pth` checkpoints are invalid as
out-of-sample financial evidence. The generating v4 pipeline performs wavelet
denoising, and global percentile clipping, before the temporal split, allowing
future observations to influence historical features.

These files are retained only as historical/debugging artifacts. Their names
such as `top`, `best`, or `walk_forward` do not imply validation or approval.

## `optuna_sfm_v5`

These are SP500 equity artifacts, not cryptocurrency artifacts. They are
mislocated for historical reasons and are also invalid as out-of-sample
evidence because their generating pipeline performs non-causal denoising before
the temporal split.

## Replacement criteria

Do not overwrite or relabel these artifacts as validated. A replacement run
must use a causal pipeline, pass the gates in `../README.md`, and be written to
a new versioned directory with a complete reproducibility manifest. The final
holdout must remain untouched by preprocessing fit, hyperparameter selection,
and model selection.
