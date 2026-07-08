"""
Unit tests for trading strategies and data utilities.
Run with: pytest tests/test_strategies.py -v
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Test Helpers: Create synthetic price data
# ============================================================

def make_sample_data(rows=100, trend="up"):
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range(start="2025-01-01", periods=rows, freq="B")
    np.random.seed(42)

    if trend == "up":
        close = 100 + np.cumsum(np.random.randn(rows) * 0.5 + 0.3)
    elif trend == "down":
        close = 200 + np.cumsum(np.random.randn(rows) * 0.5 - 0.3)
    else:
        close = 150 + np.cumsum(np.random.randn(rows) * 0.2)

    high = close + np.abs(np.random.randn(rows)) * 2
    low = close - np.abs(np.random.randn(rows)) * 2
    open_ = close + np.random.randn(rows) * 0.5
    volume = np.random.randint(10000, 500000, rows)

    df = pd.DataFrame({
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates)
    df.index.name = "Date"
    return df


# ============================================================
# Tests: data_fetcher utilities
# ============================================================

class TestDataFetcher:
    def test_to_fyers_symbol_plain(self):
        from data.data_fetcher import to_fyers_symbol
        assert to_fyers_symbol("RELIANCE") == "NSE:RELIANCE-EQ"

    def test_to_fyers_symbol_already_formatted(self):
        from data.data_fetcher import to_fyers_symbol
        assert to_fyers_symbol("NSE:RELIANCE-EQ") == "NSE:RELIANCE-EQ"

    def test_to_fyers_symbol_with_suffix(self):
        from data.data_fetcher import to_fyers_symbol
        assert to_fyers_symbol("APS-SM") == "NSE:APS-SM"

    def test_read_stocks_ignores_comments(self, tmp_path):
        from data.data_fetcher import read_stocks
        f = tmp_path / "stocks.txt"
        f.write_text("# comment\nRELIANCE\n\n# another comment\nTCS\n")
        result = read_stocks(str(f))
        assert result == ["RELIANCE", "TCS"]

    def test_read_stocks_empty_file(self, tmp_path):
        from data.data_fetcher import read_stocks
        f = tmp_path / "empty.txt"
        f.write_text("# only comments\n")
        result = read_stocks(str(f))
        assert result == []


# ============================================================
# Tests: Indicator computation (from execute_trades)
# ============================================================

class TestIndicators:
    def test_compute_indicators_columns(self):
        from live_trading.execute_trades import compute_indicators
        df = make_sample_data(100)
        result = compute_indicators(df)
        assert "KC_MID" in result.columns
        assert "KC_UPPER" in result.columns
        assert "KC_LOWER" in result.columns
        assert "EMA_FAST" in result.columns
        assert "EMA_SLOW" in result.columns
        assert "ATR" in result.columns

    def test_kc_upper_above_mid(self):
        from live_trading.execute_trades import compute_indicators
        df = make_sample_data(100)
        result = compute_indicators(df)
        # Upper channel must always be above mid
        valid = result.dropna()
        assert (valid["KC_UPPER"] > valid["KC_MID"]).all()

    def test_kc_lower_below_mid(self):
        from live_trading.execute_trades import compute_indicators
        df = make_sample_data(100)
        result = compute_indicators(df)
        valid = result.dropna()
        assert (valid["KC_LOWER"] < valid["KC_MID"]).all()

    def test_ema_fast_responds_quicker(self):
        from live_trading.execute_trades import compute_indicators
        # In a strong uptrend, EMA fast should be above EMA slow
        df = make_sample_data(100, trend="up")
        result = compute_indicators(df)
        last = result.iloc[-1]
        assert last["EMA_FAST"] > last["EMA_SLOW"]


# ============================================================
# Tests: Signal generation
# ============================================================

class TestSignals:
    def test_signal_hold_insufficient_data(self):
        from live_trading.execute_trades import generate_signal, compute_indicators
        df = make_sample_data(10)  # Too few rows
        df = compute_indicators(df)
        signal, score, reasons = generate_signal(df)
        assert signal == "HOLD"

    def test_signal_returns_valid_value(self):
        from live_trading.execute_trades import generate_signal, compute_indicators
        df = make_sample_data(100)
        df = compute_indicators(df)
        signal, score, reasons = generate_signal(df)
        assert signal in ("BUY", "SELL", "HOLD")

    def test_signal_returns_score_and_reasons(self):
        from live_trading.execute_trades import generate_signal, compute_indicators
        df = make_sample_data(100)
        df = compute_indicators(df)
        signal, score, reasons = generate_signal(df)
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100
        assert isinstance(reasons, list)
        assert len(reasons) > 0


# ============================================================
# Tests: Backtrader strategies run without error
# ============================================================

class TestBacktraderStrategies:
    def _run_strategy(self, strategy_class):
        """Helper to run a backtrader strategy on synthetic data."""
        import backtrader as bt
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy_class)
        df = make_sample_data(100, trend="up")
        data = bt.feeds.PandasData(dataname=df)
        cerebro.adddata(data)
        cerebro.broker.setcash(100000)
        results = cerebro.run()
        return cerebro.broker.getvalue()

    def test_bollinger_rsi_runs(self):
        from strategies import BollingerRSIStrategy
        value = self._run_strategy(BollingerRSIStrategy)
        assert value > 0  # Should not crash

    def test_keltner_breakout_runs(self):
        from strategies import KeltnerBreakoutStrategy
        value = self._run_strategy(KeltnerBreakoutStrategy)
        assert value > 0

    def test_keltner_tuned_runs(self):
        from strategies import KeltnerBreakoutTunedStrategy
        value = self._run_strategy(KeltnerBreakoutTunedStrategy)
        assert value > 0

    def test_squeeze_breakout_runs(self):
        from strategies import SqueezeBreakoutStrategy
        value = self._run_strategy(SqueezeBreakoutStrategy)
        assert value > 0

    def test_keltner_tuned_profitable_in_uptrend(self):
        """In a strong uptrend, the breakout strategy should be profitable."""
        from strategies import KeltnerBreakoutTunedStrategy
        value = self._run_strategy(KeltnerBreakoutTunedStrategy)
        assert value >= 100000  # Should at least not lose money in strong uptrend
