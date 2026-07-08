import backtrader as bt

class BollingerRSIStrategy(bt.Strategy):
    params = (
        ('bb_period', 20),
        ('bb_devfactor', 2.0),
        ('rsi_period', 14),
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
    )

    def __init__(self):
        self.bband = bt.indicators.BollingerBands(
            self.data.close, period=self.params.bb_period, devfactor=self.params.bb_devfactor
        )
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.params.rsi_period
        )
        self.order = None

    def next(self):
        # Do nothing if an order is pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # BUY Condition: Price <= Lower BB AND RSI < Oversold
            if self.data.close[0] <= self.bband.lines.bot[0] and self.rsi[0] < self.params.rsi_oversold:
                self.order = self.buy()
        else:
            # SELL Condition: Price >= Upper BB AND RSI > Overbought
            if self.data.close[0] >= self.bband.lines.top[0] and self.rsi[0] > self.params.rsi_overbought:
                self.order = self.sell()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                # self.log(f'BUY EXECUTED, Price: {order.executed.price}')
                pass
            elif order.issell():
                # self.log(f'SELL EXECUTED, Price: {order.executed.price}')
                pass
            self.bar_executed = len(self)
        
        self.order = None
