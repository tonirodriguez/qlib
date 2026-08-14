import argparse
from pathlib import Path

import pandas as pd
from pandas.tseries.offsets import BDay
import qlib
from qlib.constant import REG_US
from qlib.data import D
from qlib.data.dataset.handler import DataHandlerLP
from qlib.workflow import R
from qlib.workflow.recorder import Recorder
from qlib.utils.exceptions import LoadObjectError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MLRUNS_DIR = PROJECT_ROOT / "auto_trading_system" / "mlruns"
MLRUNS_URI = f"file:{MLRUNS_DIR}"
EXPERIMENT_NAME = "config_analysis_improved_v2"
#EXPERIMENT_NAME = "workflow_lightgbm_analysis"
#EXPERIMENT_NAME = "config_analysis_optuna"

PROVIDER_URI = "~/.qlib/qlib_data/us_data"


def init_qlib() -> None:
    qlib.init(provider_uri=str(Path(PROVIDER_URI).expanduser()), region=REG_US, skip_if_reg=True)
    R.set_uri(MLRUNS_URI)


def get_latest_valid_recorder(experiment_name: str):
    experiment = R.get_exp(experiment_name=experiment_name, create=False)
    recorders = experiment.list_recorders(status=Recorder.STATUS_FI, rtype=experiment.RT_L)

    for recorder in recorders:
        try:
            recorder.load_object("params.pkl")
            recorder.load_object("dataset")
            return recorder
        except LoadObjectError:
            continue

    raise FileNotFoundError(
        f"No se ha encontrado ningún recorder FINISHED en '{experiment_name}' con los artefactos 'params.pkl' y 'dataset'."
    )


def prepare_inference_dataset(dataset, signal_date: str):
    signal_ts = pd.Timestamp(signal_date)
    dataset.config(
        handler_kwargs={
            "start_time": dataset.handler.start_time,
            "end_time": signal_ts,
        },
        segments={"test": (signal_ts, signal_ts)},
    )
    dataset.setup_data(handler_kwargs={"init_type": DataHandlerLP.IT_LS})
    return dataset


def get_next_trade_date(signal_date: str, execution_date: str | None = None):
    signal_ts = pd.Timestamp(signal_date)
    if execution_date is not None:
        return pd.Timestamp(execution_date), False

    calendar = D.calendar(start_time=signal_ts, freq="day")

    if len(calendar) >= 2 and pd.Timestamp(calendar[0]) == signal_ts:
        return pd.Timestamp(calendar[1]), False

    # Si el calendario local termina en signal_date, estimamos el siguiente día hábil.
    return signal_ts + BDay(1), True


def get_top_signals(
    n_top: int = 5,
    experiment_name: str = EXPERIMENT_NAME,
    signal_date: str = "2026-04-01",
    execution_date: str | None = None,
):
    recorder = get_latest_valid_recorder(experiment_name)
    model = recorder.load_object("params.pkl")
    dataset = recorder.load_object("dataset")
    dataset = prepare_inference_dataset(dataset, signal_date)

    pred = model.predict(dataset, segment="test")
    latest_date = pred.index.get_level_values("datetime").max()
    current_pred = pred.xs(latest_date, level="datetime").sort_values(ascending=False).head(n_top)
    next_trade_date, is_estimated = get_next_trade_date(signal_date, execution_date=execution_date)

    print(f"Recorder usado: {recorder.id}")
    print(f"Señal calculada con datos al cierre de: {latest_date.date()}")
    if is_estimated:
        print(f"Fecha objetivo de ejecución estimada: {next_trade_date.date()}")
    else:
        print(f"Fecha objetivo de ejecución: {next_trade_date.date()}")
    return current_pred


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scanner diario para generar órdenes de la siguiente sesión.")
    parser.add_argument("--n-top", type=int, default=10, help="Número de señales a mostrar.")
    parser.add_argument(
        "--signal-date",
        type=str,
        default="2026-04-01",
        help="Fecha de cierre con la que se calcula la señal, por ejemplo 2026-04-01.",
    )
    parser.add_argument(
        "--execution-date",
        type=str,
        default=None,
        help="Fecha en la que quieres ejecutar las órdenes. Si no se indica, se intenta calcular con el calendario de Qlib.",
    )
    parser.add_argument("--experiment-name", type=str, default=EXPERIMENT_NAME, help="Experimento de MLflow/Qlib.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    init_qlib()
    signals = get_top_signals(
        n_top=args.n_top,
        experiment_name=args.experiment_name,
        signal_date=args.signal_date,
        execution_date=args.execution_date,
    )

    print("\nOPORTUNIDADES DE COMPRA DETECTADAS")
    print("=================================")
    for ticker, score in signals.items():
        print(f"Ticker: {ticker} | Score de confianza: {score:.4f}")


if __name__ == "__main__":
    main()
