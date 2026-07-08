import backtrader as bt

class KeltnerChannel(bt.Indicator):
    lines = ('mid', 'top', 'bot',)
    params = (
        ('period', 20),
        ('devfactor', 1.5),
    )

    def __init__(self):
        self.lines.mid = bt.indicators.EMA(self.data, period=self.params.period)
        atr = bt.indicators.ATR(self.data, period=self.params.period)
        self.lines.top = self.lines.mid + (atr * self.params.devfactor)
        self.lines.bot = self.lines.mid - (atr * self.params.devfactor)

class KeltnerBreakoutStrategy(bt.Strategy):
    params = (
        ('kc_period', 20),
        ('kc_devfactor', 1.5),
    )

    def __init__(self):
        self.kc = KeltnerChannel(
            self.data, period=self.params.kc_period, devfactor=self.params.kc_devfactor
        )
        self.order = None

    def next(self):
        if self.order:
            return

        if not self.position:
            # BUY Condition: Close price breaks above upper Keltner Channel
            if self.data.close[0] > self.kc.lines.top[0]:
                self.order = self.buy()
        else:
            # SELL/Close Condition: Price drops below the middle Keltner line (EMA)
            if self.data.close[0] < self.kc.lines.mid[0]:
                self.order = self.sell()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            self.bar_executed = len(self)
        self.order = None
