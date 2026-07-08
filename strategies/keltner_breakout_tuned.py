import backtrader as bt
from .keltner_breakout import KeltnerChannel


class KeltnerBreakoutTunedStrategy(bt.Strategy):
    """
    Tuned Keltner Channel Breakout with EMA 10/21 confirmation.
    
    Entry: Price breaks above upper Keltner (ATR 2.0) AND EMA10 > EMA21 (bullish trend).
    Exit: Price drops below middle Keltner line (EMA) OR EMA10 crosses below EMA21.
    """
    params = (
        ('kc_period', 20),
        ('kc_devfactor', 2.0),  # Tuned from 1.5 to 2.0
        ('ema_fast', 10),
        ('ema_slow', 21),
    )

    def __init__(self):
        self.kc = KeltnerChannel(
            self.data, period=self.params.kc_period, devfactor=self.params.kc_devfactor
        )
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow)

        # EMA crossover signal: positive when fast > slow
        self.ema_crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)

        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # BUY: Price breaks above upper Keltner AND EMA10 > EMA21 (bullish trend)
            if (self.data.close[0] > self.kc.lines.top[0] and
                    self.ema_fast[0] > self.ema_slow[0]):
                self.order = self.buy()
        else:
            # SELL: Price drops below middle Keltner OR EMA10 crosses below EMA21
            if (self.data.close[0] < self.kc.lines.mid[0] or
                    self.ema_crossover[0] < 0):
                self.order = self.sell()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            self.bar_executed = len(self)
        self.order = None
