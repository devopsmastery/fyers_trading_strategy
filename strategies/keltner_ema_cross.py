import backtrader as bt
from .keltner_breakout import KeltnerChannel


class KeltnerEMACrossStrategy(bt.Strategy):
    """
    Combined EMA Crossover + Keltner Channel Filter + Volume Confirmation Strategy.

    Entry (BUY) Rules:
      1. EMA10 crosses ABOVE EMA21 (Golden Cross)
      2. Price is ABOVE the KC mid-line (bullish zone)
      3. Volume on the crossover bar >= vol_factor x 20-day average (confirmation)

    Exit (SELL) Rules:
      1. EMA10 crosses BELOW EMA21 (Death Cross)  -- primary signal
      OR
      2. Price closes below KC Lower (stop-out for strong downtrend)

    Volume confirmation eliminates low-conviction crossovers, improving signal quality.
    """
    params = (
        ('kc_period', 20),
        ('kc_devfactor', 2.0),
        ('ema_fast', 10),
        ('ema_slow', 21),
        ('vol_period', 20),      # lookback for volume average
        ('vol_factor', 1.2),     # minimum volume ratio to confirm BUY signal
    )

    def __init__(self):
        self.kc = KeltnerChannel(
            self.data, period=self.params.kc_period, devfactor=self.params.kc_devfactor
        )
        self.ema_fast = bt.indicators.EMA(self.data.close, period=self.params.ema_fast)
        self.ema_slow = bt.indicators.EMA(self.data.close, period=self.params.ema_slow)

        # EMA cross signals
        self.ema_crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)

        # Volume SMA for confirmation
        self.vol_sma = bt.indicators.SMA(self.data.volume, period=self.params.vol_period)

        self.order = None

    def next(self):
        if self.order:
            return

        kc_mid   = self.kc.lines.mid[0]
        kc_lower = self.kc.lines.bot[0]
        price    = self.data.close[0]
        volume   = self.data.volume[0]
        vol_avg  = self.vol_sma[0]

        # Volume confirmation: is today's volume above the required threshold?
        vol_ok = (vol_avg > 0) and (volume >= vol_avg * self.params.vol_factor)

        if not self.position:
            # BUY: Golden cross + price in upper half of KC + volume confirms
            if (self.ema_crossover[0] > 0 and
                    price > kc_mid and
                    vol_ok):
                self.order = self.buy()
        else:
            # SELL: Death cross OR price crashes below KC lower band
            if (self.ema_crossover[0] < 0 or
                    price < kc_lower):
                self.order = self.sell()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        if order.status in [order.Completed]:
            self.bar_executed = len(self)
        self.order = None
