---
name: trading-menu
description: Triggers when the user says "Hi" or "Hello" and displays a menu of trading actions. This is the main orchestrator that routes to all sub-agents.
---

# Trading Menu Skill (Main Orchestrator)

When the user says "Hi", "Hello", or asks for the menu, you must reply with the following menu:

```markdown
# 📈 Trading System Menu

1. **Dry Run (Scanner Agent)**: Run the daily scanner — refreshes data, scans for BUY signals, cross-references your portfolio.
2. **Update Historical Data**: Append the latest market data to all existing historical stock records.
3. **Deep Analysis (Fundamental Analyst)**: Perform a combined technical + fundamental analysis on a specific stock.
4. **Add New Stocks**: Import stocks from `Newly_added_stocks.txt` and fetch their history.
5. **Portfolio Scan (Portfolio Watchdog)**: Analyze your active holdings for SELL/CAUTION/HOLD signals with risk report.
6. **Trade History**: View your complete trade audit log.

*Reply with a number to select an option, or describe what you need.*
```

## Option Handlers

When the user selects an option, follow the corresponding sub-agent skill instructions:

### Option 1: Dry Run (Scanner Agent)
Follow the instructions in the `scanner-agent` skill (`.agents/skills/scanner_agent/SKILL.md`):
1. Run `python scripts/update_historical_data.py` to refresh data.
2. Run `python scripts/dry_run.py` to scan for signals.
3. Cross-reference BUY signals against Portfolio.txt to mark stocks already held.
4. Present results sorted by quality (EXCELLENT first, then GOOD).
5. Suggest buying any new opportunities.

### Option 2: Update Historical Data
1. Run `python scripts/update_historical_data.py`.
2. Inform the user how many stocks were updated.

### Option 3: Deep Analysis (Fundamental Analyst)
Follow the instructions in the `fundamental-analyst` skill (`.agents/skills/fundamental_analyst/SKILL.md`):
1. If the user hasn't specified a ticker symbol, ask them for one.
2. Run `python scripts/deep_analysis.py <TICKER>` (with `--ltp <PRICE>` if a live price is provided).
3. Search the web for latest news, earnings, and analyst views on the ticker.
4. Synthesize technicals + fundamentals into a final Buy/Hold/Avoid verdict.

### Option 4: Add New Stocks
1. Run `python scripts/add_new_stocks.py`.
2. This script will read `Newly_added_stocks.txt`, deduplicate against existing lists, append to `stocks_watchlist.txt`, fetch their historical data, and finally clear `Newly_added_stocks.txt`.
3. Report the newly added stocks to the user. Do NOT run a backtest or dry run automatically.

### Option 5: Portfolio Scan (Portfolio Watchdog)
Follow the instructions in the `portfolio-watchdog` skill (`.agents/skills/portfolio_watchdog/SKILL.md`):
1. Run `python scripts/portfolio_analysis.py`.
2. Categorize stocks as SELL (🔴), CAUTION (⚠️), or STRONG HOLD (✅).
3. Calculate portfolio health percentage.
4. Ask if the user wants to sell any SELL-signal positions.

### Option 6: Trade History
1. Run `python scripts/trades_history.py` to display the complete audit log.
2. If the user asks to filter: `python scripts/trades_history.py --symbol <TICKER>` or `--action BUY/SELL`.

## Trade Execution (Any Context)
When the user says "Buy X shares of Y at Z" or "Sell Y" at any point, follow the `trade-executor` skill (`.agents/skills/trade_executor/SKILL.md`):
1. Validate the ticker and parse the order.
2. Execute via `portfolio_db.py` (add_trade / remove_trade).
3. Log to audit trail via `trades_history.py` (log_trade).
4. Confirm with a formatted summary.

## Post-Execution Rule
IMPORTANT: **Always** display the main Trading System Menu again at the very end of your response after completing ANY of the options above. Along with the menu, provide any relevant follow-up suggestions based on the task that was just completed.
