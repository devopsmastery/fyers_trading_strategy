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
├── scripts/
│   ├── add_new_stocks.py          # Import & deduplicate new tickers
│   ├── deep_analysis.py           # Single-stock deep dive (supports live LTP)
│   ├── dry_run.py                 # Daily scanner wrapper
│   ├── portfolio_analysis.py      # Scan Portfolio.txt for HOLD/CAUTION/SELL
│   ├── portfolio_db.py            # Sync Portfolio.txt with JSON database
│   ├── remove_duplicates.py       # Utility for list deduplication
│   └── update_historical_data.py  # Updater for local cached CSVs
├── tests/
│   └── test_strategies.py         # Unit tests
├── Portfolio.txt                  # Active portfolio tracking in broker CSV format
├── stocks_to_test.txt             # List of stock symbols to trade
├── stocks_watchlist.txt           # Watchlist for tracking potential buys
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

## AI Assistant Workflow & Menu Options

The AI Agent comes with an interactive "Trading Menu" skill. Saying **"Hi"** to the assistant will present the following workflow options:

1. **Dry Run**: Run the daily scanner (`execute_trades.py`) to get fresh BUY recommendations. You can interactively say "Buy X shares of Y at Z" to record a paper trade.
2. **Update Historical Data**: Incrementally fetch the latest daily candles for all stocks.
3. **Deep Analysis**: Run `deep_analysis.py` on a specific ticker. Supports passing a live market price via `--ltp` to simulate current intra-day indicators.
4. **Add New Stocks**: Import symbols from `Newly_added_stocks.txt`, download their historical data, deduplicate, and move them to `stocks_watchlist.txt`.
5. **Portfolio Scan**: Analyze your active holdings using `Portfolio.txt`.

## Portfolio Tracking (`Portfolio.txt`)

The system uses `Portfolio.txt` to track active positions. 
- You can simply paste your broker's exported CSV directly into this file (it looks for columns like `Instrument,Qty.,Avg. cost`).
- Running the **Portfolio Scan** (Option 5) will calculate live P&L % and categorize every held stock as **STRONG HOLD**, **CAUTION**, or **SELL** based on Keltner Channel and EMA crossover signals.
- If a stock is missing historical data during the scan, the system will automatically authenticate and download the missing data.