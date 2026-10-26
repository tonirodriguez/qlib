"""gated_strategy.py — Estrategia top-k con gate de exposicion, escrita desde cero.

POR QUE UNA ESTRATEGIA PROPIA
    Subclasear `TopkDropoutStrategy` no funciono: los 4 backtests daban Sharpe
    identico (1.1513) aunque el override ajustaba `self.topk`. Las causas
    posibles (metodo no invocado, `self.topk` cacheado, orden de llamadas) no
    se pudieron determinar leyendo el codigo de qlib.

    Esta implementacion NO hereda de TopkDropoutStrategy. Extiende
    `BaseSignalStrategy` y genera las ordenes explicitamente, asi que el
    efecto del gate es verificable leyendo el codigo.

LOGICA
    Cada dia de rebalanceo (el executor marca la frecuencia):
        gate = nivel vigente (1.0 / 0.5 / 0.0)
        target_n = round(base_topk * gate)

        gate = 0.0  -> VENDER TODA la cartera (100% cash)
        gate > 0.0  -> mantener las mejores `target_n` posiciones;
                       vender el resto; comprar hasta llegar a target_n,
                       repartiendo el capital a partes iguales.

    La senal se usa SOLO para ordenar (mayor = mejor). El gate controla
    CUANTAS posiciones se tienen, que es lo que modula la exposicion.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.backtest.signal import create_signal_from
from qlib.contrib.strategy.signal_strategy import BaseSignalStrategy


class GatedTopkStrategy(BaseSignalStrategy):
    """Top-k con numero de posiciones modulado por un gate externo.

    Parameters
    ----------
    signal : la senal de qlib (Series/DataFrame/etc.)
    gate : pd.Series
        Nivel de exposicion por fecha (0..1). Se toma el ultimo valor <= fecha.
    base_topk : int
        Numero de posiciones con gate=1.0.
    only_tradable : bool
        Respetar el estado negociable de cada valor.
    """

    # ------------------------------------------------------------------
    # El gate se pasa por ATRIBUTO DE CLASE, no por kwarg.
    #
    # MOTIVO (causa raiz del fallo de v2):
    #   qlib/utils/mod.py:178-184 hace
    #       try:    klass(**cls_kwargs, **try_kwargs, **kwargs)
    #       except TypeError: klass(**cls_kwargs, **kwargs)
    #   Es decir, si el constructor lanza TypeError, qlib REINTENTA
    #   SILENCIOSAMENTE sin los kwargs extra. Resultado: la estrategia se
    #   construye sin `gate`, `level_at` devuelve 1.0 siempre y el backtest
    #   sale identico al puro. Exactamente lo observado ({1.0: 240}).
    #
    #   Pasando el gate como atributo de clase y construyendo la estrategia
    #   NOSOTROS MISMOS (instancia ya creada), `init_instance_by_config`
    #   la devuelve tal cual (accept_types) sin reconstruirla.
    # ------------------------------------------------------------------
    _class_gate: pd.Series | None = None
    _class_base_topk: int = 30

    @classmethod
    def configure(cls, gate: pd.Series, base_topk: int = 30) -> None:
        """Fija el gate a nivel de clase (se lee en cada instancia)."""
        g = pd.Series(gate).copy()
        g.index = pd.to_datetime(g.index)
        try:
            g.index = g.index.tz_localize(None)
        except (TypeError, AttributeError):
            pass
        cls._class_gate = g.sort_index()
        cls._class_base_topk = int(base_topk)

    def __init__(
        self,
        *,
        signal=None,
        gate: pd.Series | None = None,
        base_topk: int | None = None,
        only_tradable: bool = True,
        **kwargs,
    ):
        # NO se pasan gate/base_topk a super(): solo lo que espera la clase base.
        super().__init__(signal=signal, **kwargs)
        if gate is None:
            gate = type(self)._class_gate
        if base_topk is None:
            base_topk = type(self)._class_base_topk
        self.base_topk = int(base_topk) if base_topk else 30
        self.only_tradable = bool(only_tradable)
        # normalizar el indice del gate a datetime sin tz, para comparar bien
        if gate is not None:
            g = pd.Series(gate).copy()
            g.index = pd.to_datetime(g.index)
            try:
                g.index = g.index.tz_localize(None)
            except (TypeError, AttributeError):
                pass
            self.gate = g.sort_index()
        # contadores de diagnostico
        self.dbg_calls = 0
        self.dbg_levels: dict = {}
        self.dbg_targets: dict = {}
        self.dbg_sellall = 0

    # -- nivel de gate ------------------------------------------------------

    def level_at(self, date) -> float:
        """Nivel de gate vigente en `date` (ultimo valor <= date)."""
        if self.gate is None or len(self.gate) == 0:
            return 1.0
        d = pd.Timestamp(date)
        try:
            d = d.tz_localize(None)
        except (TypeError, AttributeError):
            pass
        sub = self.gate.loc[:d]
        if len(sub) == 0:
            return 1.0
        v = float(sub.iloc[-1])
        return 1.0 if v != v else v  # NaN -> 1.0

    # -- decision -----------------------------------------------------------

    def generate_trade_decision(self, execute_result=None):
        self.dbg_calls += 1

        start_time, end_time = self.trade_calendar.get_step_time()
        level = self.level_at(start_time)
        target_n = int(round(self.base_topk * level))

        self.dbg_levels[level] = self.dbg_levels.get(level, 0) + 1
        self.dbg_targets[target_n] = self.dbg_targets.get(target_n, 0) + 1

        # posiciones actuales
        pos = self.trade_position
        held = list(pos.get_stock_list())

        # --- GATE 0: vender todo -> 100% cash ---
        if target_n <= 0:
            self.dbg_sellall += 1
            orders = []
            for code in held:
                amt = pos.get_stock_amount(code)
                if amt and amt > 0:
                    orders.append(Order(
                        stock_id=code, amount=amt, direction=OrderDir.SELL,
                        start_time=start_time, end_time=end_time,
                    ))
            return TradeDecisionWO(orders, self)

        # --- puntuaciones de hoy ---
        score: pd.Series = self.signal.get_signal(start_time, end_time)
        if score is None or len(score) == 0:
            return TradeDecisionWO([], self)

        score = score.dropna()
        if self.only_tradable:
            keep = []
            for code in score.index:
                try:
                    if self.trade_exchange.is_stock_tradable(
                        stock_id=code, start_time=start_time,
                        end_time=end_time, direction=None,
                    ):
                        keep.append(code)
                except Exception:
                    keep.append(code)
            if keep:
                score = score.reindex(keep).dropna()

        ranked = score.sort_values(ascending=False)
        want = list(ranked.index[:target_n])

        orders = []

        # 1) vender lo que ya no queremos
        for code in held:
            if code not in want:
                amt = pos.get_stock_amount(code)
                if amt and amt > 0:
                    orders.append(Order(
                        stock_id=code, amount=amt, direction=OrderDir.SELL,
                        start_time=start_time, end_time=end_time,
                    ))

        # 2) repartir el capital entre las `target_n` posiciones objetivo.
        #
        # El capital objetivo es el VALOR TOTAL de la cartera (posiciones +
        # cash). Al reducir target_n, el mismo capital se reparte entre menos
        # nombres -> cada posicion pesa mas, y el resto del capital que antes
        # estaba en nombres descartados se queda en cash hasta el proximo
        # rebalanceo. Este es el efecto buscado: el gate recorta exposicion.
        total_value = pos.calculate_stock_value() + pos.get_cash()
        if total_value <= 0 or target_n <= 0:
            return TradeDecisionWO(orders, self)
        target_val = total_value / target_n

        for code in want:
            try:
                price = self.trade_exchange.get_deal_price(
                    stock_id=code, start_time=start_time, end_time=end_time,
                    direction=OrderDir.BUY,
                )
            except Exception:
                price = None
            if price is None or price != price or price <= 0:
                continue
            held_amt = pos.get_stock_amount(code) if code in held else 0.0
            held_val = held_amt * price
            diff_val = target_val - held_val
            # umbral minimo para no generar ordenes ridiculas cada rebalanceo
            if abs(diff_val) < 0.02 * target_val:
                continue
            shares = int(abs(diff_val) / price)
            if shares <= 0:
                continue
            direction = OrderDir.BUY if diff_val > 0 else OrderDir.SELL
            orders.append(Order(
                stock_id=code, amount=shares, direction=direction,
                start_time=start_time, end_time=end_time,
            ))

        return TradeDecisionWO(orders, self)


def make_signal(series):
    """Crea una senal de qlib a partir de una Series con MultiIndex."""
    return create_signal_from(series)
