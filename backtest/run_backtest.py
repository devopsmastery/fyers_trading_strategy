"""
Backtest Orchestrator: Runs all three strategies across all stocks
and produces a comparative performance report.
"""

import sys
import os
import backtrader as bt
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_fetcher import read_stocks, get_data_for_symbol, to_fyers_symbol, load_historical_csv
from strategies import BollingerRSIStrategy, KeltnerBreakoutStrategy, KeltnerBreakoutTunedStrategy, SqueezeBreakoutStrategy

STOCKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stocks_to_test.txt")
INITIAL_CASH = 100000.0


def run_backtest_for_strategy(strategy_class, data_feed, name):
    """Runs a single backtrader simulation for a given strategy and data feed."""
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_class)

    data = bt.feeds.PandasData(dataname=data_feed)
    cerebro.adddata(data)

    cerebro.broker.setcash(INITIAL_CASH)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    results = cerebro.run()
    strat = results[0]

    final_value = cerebro.broker.getvalue()
    pnl = final_value - INITIAL_CASH
    pnl_pct = (pnl / INITIAL_CASH) * 100

    # Extract trade stats
    trade_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trade_analysis.get('total', {}).get('total', 0)
    won = trade_analysis.get('won', {}).get('total', 0)
    lost = trade_analysis.get('lost', {}).get('total', 0)
    win_rate = (won / total_trades * 100) if total_trades > 0 else 0

    # Extract drawdown
    dd_analysis = strat.analyzers.drawdown.get_analysis()
    max_drawdown_pct = dd_analysis.get('max', {}).get('drawdown', 0)

    return {
        "Strategy": name,
        "Final Value": round(final_value, 2),
        "PnL": round(pnl, 2),
        "PnL %": round(pnl_pct, 2),
        "Total Trades": total_trades,
        "Won": won,
        "Lost": lost,
        "Win Rate %": round(win_rate, 2),
        "Max Drawdown %": round(max_drawdown_pct, 2),
    }


def main():
    stocks = read_stocks(STOCKS_FILE)
    if not stocks:
        print("No stocks found to backtest.")
        return

    print(f"Found {len(stocks)} stocks to backtest.")
    print("Loading cached historical CSV data...")

    strategies = [
        (BollingerRSIStrategy, "Bollinger RSI"),
        (KeltnerBreakoutStrategy, "Keltner Breakout (ATR 1.5)"),
        (KeltnerBreakoutTunedStrategy, "Keltner Tuned (ATR 2.0 + EMA)"),
        (SqueezeBreakoutStrategy, "Squeeze Breakout"),
    ]

    overall_results = []
    skipped = []

    for i, symbol in enumerate(stocks, 1):
        fyers_symbol = to_fyers_symbol(symbol)
        try:
            df = load_historical_csv(fyers_symbol)
        except FileNotFoundError:
            skipped.append(symbol)
            continue

        if len(df) < 25:
            print(f"  [{i}] {symbol}: Skipped (only {len(df)} rows, need 25+)")
            skipped.append(symbol)
            continue

        for StratClass, name in strategies:
            try:
                res = run_backtest_for_strategy(StratClass, df, name)
                res["Symbol"] = symbol
                overall_results.append(res)
            except Exception as e:
                print(f"  [{i}] {symbol} / {name}: Error - {e}")

    if skipped:
        print(f"\nSkipped {len(skipped)} symbols (no data or insufficient rows): {', '.join(skipped[:10])}{'...' if len(skipped) > 10 else ''}")

    if overall_results:
        results_df = pd.DataFrame(overall_results)

        # Aggregate results by strategy
        agg = results_df.groupby("Strategy").agg({
            "PnL": "sum",
            "PnL %": "mean",
            "Total Trades": "sum",
            "Won": "sum",
            "Lost": "sum",
            "Max Drawdown %": "max",
        }).reset_index()
        agg["Win Rate %"] = (agg["Won"] / agg["Total Trades"] * 100).round(2)
        agg = agg.sort_values(by="PnL", ascending=False)

        print("\n" + "=" * 80)
        print("  STRATEGY COMPARISON (AGGREGATED ACROSS ALL STOCKS)")
        print("=" * 80)
        print(agg[["Strategy", "PnL", "PnL %", "Total Trades", "Win Rate %", "Max Drawdown %"]].to_string(index=False))

        best_strategy = agg.iloc[0]['Strategy']
        best_pnl = agg.iloc[0]['PnL']
        print(f"\n=> WINNER: {best_strategy} with total PnL = Rs.{best_pnl:,.2f}")

        # Save detailed results to CSV
        results_path = os.path.join(os.path.dirname(__file__), "backtest_results.csv")
        results_df.to_csv(results_path, index=False)
        print(f"\nDetailed symbol-by-symbol results saved to {results_path}")
    else:
        print("\nNo valid backtest results generated.")
        print("Please run `python data/data_fetcher.py` first to fetch historical data from Fyers API.")


if __name__ == "__main__":
    main()
