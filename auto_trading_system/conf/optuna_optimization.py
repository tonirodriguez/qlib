import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


PROVIDER_URI = "~/.qlib/qlib_data/us_data"
EXPERIMENT_NAME = "optuna_lgbm"

DATA_HANDLER_CONFIG = {
    "start_time": "2018-01-01",
    "end_time": "2026-03-31",
    "fit_start_time": "2018-01-01",
    "fit_end_time": "2023-12-31",
    "instruments": "sp500",
    "infer_processors": [
        {
            "class": "RobustZScoreNorm",
            "kwargs": {
                "fields_group": "feature",
                "clip_outlier": True,
            },
        },
        {
            "class": "Fillna",
            "kwargs": {
                "fields_group": "feature",
            },
        },
    ],
    "learn_processors": [
        {"class": "DropnaLabel"},
        {
            "class": "CSRankNorm",
            "kwargs": {
                "fields_group": "label",
            },
        },
    ],
}

DATASET_CONFIG = {
    "class": "DatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
        "handler": {
            "class": "Alpha158",
            "module_path": "qlib.contrib.data.handler",
            "kwargs": DATA_HANDLER_CONFIG,
        },
        "segments": {
            "train": ("2018-01-01", "2023-12-31"),
            "valid": ("2024-01-01", "2024-12-31"),
            "test": ("2025-01-01", "2026-03-31"),
        },
    },
}


def ensure_qlib_initialized() -> None:
    try:
        import qlib
        from qlib.constant import REG_US
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "No se ha podido importar Qlib. Revisa las dependencias del entorno, por ejemplo 'setuptools_scm' y las librerias de qlib."
        ) from exc

    provider_uri = str(Path(PROVIDER_URI).expanduser())
    qlib.init(provider_uri=provider_uri, region=REG_US, skip_if_reg=True)


def build_task_config(trial) -> dict:
    model_kwargs = {
        "loss": "mse",
        "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.05, log=True),
        "num_boost_round": trial.suggest_int("num_boost_round", 300, 1500, step=100),
        "early_stopping_rounds": trial.suggest_int("early_stopping_rounds", 50, 200, step=25),
        "num_leaves": trial.suggest_int("num_leaves", 15, 127),
        "max_depth": trial.suggest_int("max_depth", 4, 10),
        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 50, 400, step=25),
        "subsample": trial.suggest_float("subsample", 0.6, 0.95),
        "subsample_freq": 1,
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 0.95),
        "lambda_l1": trial.suggest_float("lambda_l1", 0.0, 20.0),
        "lambda_l2": trial.suggest_float("lambda_l2", 0.0, 60.0),
        "num_threads": 8,
    }

    return {
        "model": {
            "class": "LGBModel",
            "module_path": "qlib.contrib.model.gbdt",
            "kwargs": model_kwargs,
        },
        "dataset": DATASET_CONFIG,
    }


def objective(trial) -> float:
    import optuna
    from qlib.contrib.eva.alpha import calc_ic
    from qlib.data.dataset.handler import DataHandlerLP
    from qlib.utils import init_instance_by_config
    from qlib.workflow import R

    task = build_task_config(trial)
    model = init_instance_by_config(task["model"])
    dataset = init_instance_by_config(task["dataset"])

    with R.start(experiment_name=EXPERIMENT_NAME):
        model.fit(dataset)
        pred_valid = model.predict(dataset, segment="valid")
        label_valid = dataset.prepare("valid", col_set="label", data_key=DataHandlerLP.DK_L)

        ic_series, _ = calc_ic(pred_valid, label_valid.iloc[:, 0], dropna=True)
        mean_ic = float(ic_series.mean())

        if ic_series.empty or mean_ic != mean_ic:
            raise optuna.TrialPruned("El trial no produjo un IC válido en validación.")

        R.log_metrics(mean_valid_ic=mean_ic)
        return mean_ic


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimización de hiperparámetros de LightGBM con Optuna y Qlib.")
    parser.add_argument("--n-trials", type=int, default=20, help="Número de trials de Optuna.")
    parser.add_argument("--study-name", type=str, default="optuna_lgbm_study", help="Nombre del estudio.")
    parser.add_argument("--storage", type=str, default=None, help="Storage opcional de Optuna, por ejemplo sqlite:///optuna.db")
    parser.add_argument("--seed", type=int, default=42, help="Semilla para el sampler de Optuna.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import optuna
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "No se ha encontrado el paquete 'optuna'. Instala la dependencia antes de ejecutar este script."
        ) from exc

    ensure_qlib_initialized()

    sampler = optuna.samplers.TPESampler(seed=args.seed)
    study = optuna.create_study(
        direction="maximize",
        study_name=args.study_name,
        storage=args.storage,
        load_if_exists=bool(args.storage),
        sampler=sampler,
    )
    study.optimize(objective, n_trials=args.n_trials)

    print("Mejores parámetros encontrados:", study.best_params)
    print("Mejor IC medio en validación:", study.best_value)


if __name__ == "__main__":
    main()
