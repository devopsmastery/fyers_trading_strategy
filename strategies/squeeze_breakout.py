import backtrader as bt
from .keltner_breakout import KeltnerChannel

class SqueezeBreakoutStrategy(bt.Strategy):
    params = (
        ('period', 20),
        ('bb_devfactor', 2.0),
        ('kc_devfactor', 1.5),
        ('rsi_period', 14),
    )

    def __init__(self):
        # Indicators
        self.bband = bt.indicators.BollingerBands(
            self.data, period=self.params.period, devfactor=self.params.bb_devfactor
        )
        self.kc = KeltnerChannel(
            self.data, period=self.params.period, devfactor=self.params.kc_devfactor
        )
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.params.rsi_period
        )
        self.order = None
        
        # Squeeze logic
        self.squeeze_on = bt.And(
            self.bband.lines.top < self.kc.lines.top,
            self.bband.lines.bot > self.kc.lines.bot
        )
        
        # We want to track if squeeze was on recently
        self.was_squeezed = False

    def next(self):
        if self.order:
            return

        # Check if squeeze is on currently
        if self.squeeze_on[0]:
            self.was_squeezed = True
            
        if not self.position:
            # If we were squeezed, and now we break out
            if self.was_squeezed and not self.squeeze_on[0]:
                # Long Breakout: Price breaks above upper BB, RSI > 50 (momentum)
                if self.data.close[0] > self.bband.lines.top[0] and self.rsi[0] > 50:
                    self.order = self.buy()
                    self.was_squeezed = False
                
                # Short Breakout: Price breaks below lower BB, RSI < 50
                elif self.data.close[0] < self.bband.lines.bot[0] and self.rsi[0] < 50:
                    self.order = self.sell()
                    self.was_squeezed = False
        else:
            # Exit Logic
            if self.position.size > 0:
                # Exit Long: Price crosses below middle line (EMA) or RSI gets too exhausted
                if self.data.close[0] < self.kc.lines.mid[0] or self.rsi[0] > 80:
                    self.order = self.sell()
            elif self.position.size < 0:
                # Exit Short: Price crosses above middle line
                if self.data.close[0] > self.kc.lines.mid[0] or self.rsi[0] < 20:
                    self.order = self.buy()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            self.bar_executed = len(self)
        self.order = None
