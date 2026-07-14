---
name: trading-menu
description: Triggers when the user says "Hi" or "Hello" and displays a menu of trading actions.
---

# Trading Menu Skill

When the user says "Hi", "Hello", or asks for the menu, you must reply with the following menu:

```markdown
# 📈 Trading System Menu

1. **Dry Run**: Run the daily scanner without placing live orders and suggest stocks for the day.
2. **Update Historical Data**: Append the latest market data to all existing historical stock records.
3. **Deep Analysis**: Perform a deep dive technical analysis on a specific stock.
4. **Add New Stocks**: Import stocks from `Newly_added_stocks.txt` and fetch their history.
5. **Portfolio Scan**: Analyze your active holdings in `Portfolio.txt` for SELL/HOLD signals.

*Reply with a number to select an option.*
```

## Option Handlers

When the user selects an option, execute the corresponding script from the `scripts/` directory:

### Option 1: Dry Run
1. Run `python scripts/dry_run.py`.
2. Present the recommended BUY signals to the user.
3. Suggest doing a Deep Analysis on any of the recommended stocks.
4. **Interactive Trade Execution**: Ask the user if they want to "Buy" any of the recommendations. If they say "Buy 100 shares of SYMBOL at PRICE", run `python -c "from scripts.portfolio_db import add_trade; add_trade('SYMBOL', 100, PRICE)"` to log it to the database and update `Portfolio.txt`.

### Option 2: Update Historical Data
1. Run `python scripts/update_historical_data.py`.
2. Inform the user how many stocks were updated.

### Option 3: Deep Analysis
1. If the user hasn't specified a ticker symbol, ask them for one. If they provide an invalid symbol, ask again.
2. Run `python scripts/deep_analysis.py <TICKER>`.
3. Present the analysis report (Trend, RSI, Support/Resistance, Volume Profile) to the user using an artifact or markdown.

### Option 4: Add New Stocks
1. Run `python scripts/add_new_stocks.py`.
2. This script will read `Newly_added_stocks.txt`, deduplicate against existing lists, append to `stocks_watchlist.txt`, fetch their historical data, and finally clear `Newly_added_stocks.txt`.
3. Report the newly added stocks to the user. Do NOT run a backtest or dry run automatically.

### Option 5: Portfolio Scan
1. Invoke the `portfolio_manager` subagent or just run `python scripts/portfolio_analysis.py` directly.
2. The script reads `Portfolio.txt` and gives a detailed scan categorizing stocks as STRONG HOLD, CAUTION, or SELL.
3. Ask the user if they want to "Sell" any of the active positions based on the report. If they say yes, run `python -c "from scripts.portfolio_db import remove_trade; remove_trade('SYMBOL')"` to remove it from the active portfolio.

## Post-Execution Rule
IMPORTANT: **Always** display the main Trading System Menu again at the very end of your response after completing ANY of the options above. Along with the menu, provide any relevant follow-up suggestions based on the task that was just completed.
