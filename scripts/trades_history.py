"""
Trades History — Audit log for all buy/sell actions.
Records every trade with timestamp, ticker, qty, price, and action type.
"""

import os
import json
from datetime import datetime

TRADES_LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'trades_history.json')


def _load_history(log_path=TRADES_LOG_PATH):
    """Loads the trades history JSON file."""
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def _save_history(history, log_path=TRADES_LOG_PATH):
    """Saves the trades history to JSON."""
    dir_name = os.path.dirname(log_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(log_path, 'w') as f:
        json.dump(history, f, indent=4)


def log_trade(symbol, qty, price, action, log_path=TRADES_LOG_PATH):
    """
    Logs a trade to the audit history.
    
    Args:
        symbol: Ticker symbol (e.g., 'RELIANCE')
        qty: Number of shares
        price: Trade price per share
        action: 'BUY' or 'SELL'
        log_path: Path to the trades history JSON file
    """
    history = _load_history(log_path)
    
    trade_record = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "symbol": symbol.upper(),
        "qty": qty,
        "price": price,
        "action": action.upper(),
        "total_value": round(qty * price, 2)
    }
    
    history.append(trade_record)
    _save_history(history, log_path)
    
    print(f"[TRADE LOG] {trade_record['action']} {trade_record['qty']} x {trade_record['symbol']} @ {trade_record['price']} = Rs.{trade_record['total_value']}")
    return trade_record


def get_history(symbol=None, action=None, log_path=TRADES_LOG_PATH):
    """
    Retrieves trade history with optional filters.
    
    Args:
        symbol: Filter by ticker symbol (optional)
        action: Filter by 'BUY' or 'SELL' (optional)
        log_path: Path to the trades history JSON file
    
    Returns:
        List of matching trade records
    """
    history = _load_history(log_path)
    
    if symbol:
        history = [t for t in history if t['symbol'] == symbol.upper()]
    if action:
        history = [t for t in history if t['action'] == action.upper()]
    
    return history


def print_history(symbol=None, action=None, log_path=TRADES_LOG_PATH):
    """Prints a formatted trade history table."""
    trades = get_history(symbol, action, log_path)
    
    if not trades:
        print("No trades found.")
        return
    
    print("=" * 80)
    print(f"  {'Date':<12} {'Action':<6} {'Symbol':<15} {'Qty':>6} {'Price':>10} {'Value':>12}")
    print("-" * 80)
    
    total_bought = 0
    total_sold = 0
    
    for t in trades:
        print(f"  {t['date']:<12} {t['action']:<6} {t['symbol']:<15} {t['qty']:>6} {t['price']:>10.2f} Rs.{t['total_value']:>11.2f}")
        if t['action'] == 'BUY':
            total_bought += t['total_value']
        else:
            total_sold += t['total_value']
    
    print("-" * 80)
    print(f"  Total Bought: Rs.{total_bought:,.2f}  |  Total Sold: Rs.{total_sold:,.2f}  |  Net: Rs.{total_sold - total_bought:,.2f}")
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="View or log trades")
    parser.add_argument("--symbol", help="Filter by ticker symbol")
    parser.add_argument("--action", choices=["BUY", "SELL"], help="Filter by action")
    args = parser.parse_args()
    
    print_history(args.symbol, args.action)
