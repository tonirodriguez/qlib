"""Estrategia TopkDropout con Vol-Targeting.

Ajusta dinámicamente la exposición (risk_degree) según la volatilidad reciente
del benchmark: si la vol sube, reduce la exposición; si baja, la aumenta.
Mantiene una volatilidad objetivo constante (vol-targeting clásico).

Uso en yml:
    strategy:
        class: VolTargetTopkStrategy
        module_path: toni.vol_target_strategy
        kwargs:
            signal: <PRED>
            topk: 5
            n_drop: 0
            only_tradable: true
            vol_target: 0.20        # volatilidad anual objetivo (20%)
            vol_window: 20          # ventana de cálculo de vol (días)
            min_risk_degree: 0.3     # exposición mínima (30%)
            max_risk_degree: 1.0    # exposición máxima (100%)
"""
import numpy as np

from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy
from qlib.data import D
from qlib.log import get_module_logger

logger = get_module_logger("VolTargetTopkStrategy")


class VolTargetTopkStrategy(TopkDropoutStrategy):
    def __init__(
        self,
        *,
        vol_target: float = 0.20,
        vol_window: int = 20,
        min_risk_degree: float = 0.3,
        max_risk_degree: float = 1.0,
        benchmark: str = "^NDX",
        benchmark_freq: str = None,  # None = auto-detect del trade_calendar
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.vol_target = vol_target
        self.vol_window = vol_window
        self.min_risk_degree = min_risk_degree
        self.max_risk_degree = max_risk_degree
        self.benchmark = benchmark
        self.benchmark_freq = benchmark_freq
        self._vol_cache = {}

    def _get_benchmark_vol(self, trade_date):
        """Volatilidad anualizada del benchmark en la ventana previa a trade_date."""
        if trade_date in self._vol_cache:
            return self._vol_cache[trade_date]

        try:
            from qlib.utils import get_pre_trading_date

            # Frecuencia del cálculo: auto-detect del trade_calendar si no se fija
            if self.benchmark_freq is None:
                try:
                    freq = self.trade_calendar.get_freq()
                except Exception:
                    freq = "day"
            else:
                freq = self.benchmark_freq

            end = trade_date
            start = trade_date
            for _ in range(self.vol_window + 2):
                start = get_pre_trading_date(start, future=False)
            close = D.features(
                [self.benchmark],
                ["$close"],
                start_time=start,
                end_time=end,
                freq=freq,
            )
            close = close["$close"].dropna()
            if len(close) < 5:
                self._vol_cache[trade_date] = None
                return None
            ret = close.pct_change().dropna()
            vol_daily = ret.std()
            # anualizar según frecuencia (asumimos ~252 días / ~52 semanas mercado US)
            periods_per_year = 252 if freq in ("day", "1d") else 52
            vol_annual = vol_daily * np.sqrt(periods_per_year)
            self._vol_cache[trade_date] = vol_annual
            return vol_annual
        except Exception as e:
            logger.warning(f"Vol calc failed for {trade_date}: {e}")
            self._vol_cache[trade_date] = None
            return None

    def generate_trade_decision(self, execute_result=None):
        """Ajustar risk_degree según vol antes de generar la decisión."""
        trade_step = self.trade_calendar.get_trade_step()
        trade_start_time, _ = self.trade_calendar.get_step_time(trade_step)
        vol = self._get_benchmark_vol(trade_start_time)

        if vol and vol > 0:
            raw = self.vol_target / vol
            self.risk_degree = float(np.clip(raw, self.min_risk_degree, self.max_risk_degree))
        else:
            self.risk_degree = self.max_risk_degree

        return super().generate_trade_decision(execute_result)
