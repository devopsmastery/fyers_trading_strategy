# Fyers Trading Strategy

Automated trading strategies for NSE stocks using the Fyers API. Includes backtesting framework and live trading scripts.

## Winning Strategy: Keltner Channel Breakout (ATR 2.0 + EMA 10/21)

- **Entry:** Price breaks above the upper Keltner Channel (20-period EMA + 2.0x ATR) AND EMA 10 > EMA 21.
- **Exit:** Price drops below the middle Keltner line (EMA 20) OR EMA 10 crosses below EMA 21.
- **Backtest Result:** Rs.8,98,510 total PnL across 71 stocks, 37.38% win rate, 41.67% max drawdown.

## Project Structure

```
fyers_trading_strategy/
├── data/
│   ├── historical_data/           # Cached CSV files from Fyers API
│   └── data_fetcher.py            # Fetch & cache historical data from Fyers
├── strategies/
│   ├── bollinger_rsi.py           # Strategy 1: Bollinger + RSI Mean Reversion
│   ├── keltner_breakout.py        # Strategy 2: Keltner Channel Breakout (ATR 1.5)
│   ├── keltner_breakout_tuned.py  # Strategy 3: Tuned Keltner (ATR 2.0 + EMA) ★
│   └── squeeze_breakout.py        # Strategy 4: Bollinger-Keltner Squeeze
├── backtest/
│   ├── run_backtest.py            # Run all strategies and compare results
│   └── backtest_results.csv       # Detailed per-stock results
├── live_trading/
│   ├── fyers_auth.py              # OAuth authentication (raw HTTP, no SDK)
│   └── execute_trades.py          # Live signal scanner & order placement
├── tests/
│   └── test_strategies.py         # Unit tests
├── stocks_to_test.txt             # List of stock symbols to trade
├── requirements.txt               # Python dependencies
├── .env                           # API credentials (git-ignored)
└── .gitignore
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials** in `.env`:
   ```
   FYERS_APP_ID=your_app_id
   FYERS_SECRET_KEY=your_secret_key
   FYERS_REDIRECT_URI=https://trade.fyers.in/api-login/redirect-uri/index.html
   FYERS_AUTH_CODE=your_auth_code
   ```

3. **Fetch historical data:**
   ```bash
   python data/data_fetcher.py
   ```

4. **Run backtest:**
   ```bash
   python backtest/run_backtest.py
   ```

5. **Scan for live signals (dry run):**
   ```bash
   python live_trading/execute_trades.py
   ```

6. **Enable live trading:** Set `DRY_RUN=False` in `.env`.