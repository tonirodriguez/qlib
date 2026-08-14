from pathlib import Path

import numpy as np
import pandas as pd
from autogluon.tabular import TabularPredictor

from qlib.model.base import Model
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP


class AutoGluonQlibModel(Model):
    """
    Wrapper Qlib -> AutoGluon Tabular.

    Cada fila es un par (instrument, datetime).
    Las columnas son factores de Qlib.
    La etiqueta es el retorno futuro definido por el DataHandler.
    """

    # Evita picklear todos los modelos internos de AutoGluon dentro del objeto Qlib.
    # AutoGluon ya guarda sus modelos en predictor_path.
    exclude_attr = ["predictor"]

    def __init__(
        self,
        label="LABEL0",
        problem_type="regression",
        eval_metric="root_mean_squared_error",
        path="./ag_models/qlib_autogluon",
        presets="medium_quality",
        time_limit=3600,
        num_cpus="auto",
        num_gpus=0,
        hyperparameters=None,
        verbosity=2,
        **fit_kwargs,
    ):
        self.label = label
        self.problem_type = problem_type
        self.eval_metric = eval_metric
        self.predictor_path = str(Path(path).expanduser())
        self.presets = presets
        self.time_limit = time_limit
        self.num_cpus = num_cpus
        self.num_gpus = num_gpus
        self.hyperparameters = hyperparameters
        self.verbosity = verbosity
        self.fit_kwargs = fit_kwargs
        self.predictor = None

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["__".join(map(str, c)).strip("_") for c in df.columns]
        else:
            df.columns = [str(c) for c in df.columns]
        return df

    def _to_autogluon_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        x = self._flatten_columns(df["feature"])
        y = df["label"]

        if isinstance(y, pd.DataFrame):
            if y.shape[1] != 1:
                raise ValueError("Este wrapper espera una sola etiqueta.")
            y = y.iloc[:, 0]

        out = x.copy()
        out[self.label] = y.astype(float).to_numpy()
        out = out.replace([np.inf, -np.inf], np.nan)

        # La etiqueta no puede faltar. Las features con NaN puede tratarlas AutoGluon.
        out = out.dropna(subset=[self.label])
        return out

    def _load_predictor_if_needed(self):
        if self.predictor is None:
            self.predictor = TabularPredictor.load(self.predictor_path)
        return self.predictor

    def fit(self, dataset: DatasetH, reweighter=None):
        df_train, df_valid = dataset.prepare(
            ["train", "valid"],
            col_set=["feature", "label"],
            data_key=DataHandlerLP.DK_L,
        )

        train_data = self._to_autogluon_frame(df_train)
        valid_data = self._to_autogluon_frame(df_valid)

        self.predictor = TabularPredictor(
            label=self.label,
            problem_type=self.problem_type,
            eval_metric=self.eval_metric,
            path=self.predictor_path,
            verbosity=self.verbosity,
        )

        self.predictor.fit(
            train_data=train_data,
            tuning_data=valid_data,
            presets=self.presets,
            time_limit=self.time_limit,
            num_cpus=self.num_cpus,
            num_gpus=self.num_gpus,
            hyperparameters=self.hyperparameters,
            **self.fit_kwargs,
        )

        return self

    def predict(self, dataset: DatasetH, segment="test"):
        predictor = self._load_predictor_if_needed()

        x = dataset.prepare(
            segment,
            col_set="feature",
            data_key=DataHandlerLP.DK_I,
        )

        x = self._flatten_columns(x)
        x = x.replace([np.inf, -np.inf], np.nan)

        pred = predictor.predict(x)
        return pd.Series(pred.to_numpy(), index=x.index, name="score")