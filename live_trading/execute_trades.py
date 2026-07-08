"""
Fyers Live Trading Script: Keltner Tuned (ATR 2.0 + EMA 10/21)

This script:
1. Authenticates with Fyers API
2. Fetches latest daily candle data for stocks in stocks_to_test.txt
3. Computes Keltner Channel (ATR 2.0) and EMA 10/21 indicators
4. Generates BUY/SELL signals
5. Places orders via Fyers API

Usage:
    python live_trading/execute_trades.py
"""

import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from live_trading.fyers_auth import get_access_token, FYERS_APP_ID
from data.data_fetcher import (
    read_stocks, to_fyers_symbol, fetch_historical_data,
    save_historical_data, HISTORICAL_DATA_DIR
)

STOCKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stocks_to_test.txt")
ORDER_URL = "https://api-t1.fyers.in/api/v3/orders/sync"

# Strategy Parameters
KC_PERIOD = 20
KC_ATR_MULTIPLIER = 2.0
EMA_FAST = 10
EMA_SLOW = 21
QUANTITY = 1  # Default quantity per order; adjust per stock


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Keltner Channel (ATR 2.0) and EMA 10/21 on a DataFrame."""
    df = df.copy()

    # EMA for Keltner mid-line
    df["KC_MID"] = df["Close"].ewm(span=KC_PERIOD, adjust=False).mean()

    # ATR
    df["TR"] = np.maximum(
        df["High"] - df["Low"],
        np.maximum(
            abs(df["High"] - df["Close"].shift(1)),
            abs(df["Low"] - df["Close"].shift(1))
        )
    )
    df["ATR"] = df["TR"].ewm(span=KC_PERIOD, adjust=False).mean()

    # Keltner Channels
    df["KC_UPPER"] = df["KC_MID"] + (KC_ATR_MULTIPLIER * df["ATR"])
    df["KC_LOWER"] = df["KC_MID"] - (KC_ATR_MULTIPLIER * df["ATR"])

    # EMA Fast / Slow
    df["EMA_FAST"] = df["Close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["EMA_SLOW"] = df["Close"].ewm(span=EMA_SLOW, adjust=False).mean()

    return df


def generate_signal(df: pd.DataFrame) -> str:
    """
    Generate a trading signal based on the latest row of indicator data.

    Returns: 'BUY', 'SELL', or 'HOLD'
    """
    if len(df) < KC_PERIOD + 1:
        return "HOLD"

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    close = latest["Close"]
    kc_upper = latest["KC_UPPER"]
    kc_mid = latest["KC_MID"]
    ema_fast = latest["EMA_FAST"]
    ema_slow = latest["EMA_SLOW"]
    prev_ema_fast = prev["EMA_FAST"]
    prev_ema_slow = prev["EMA_SLOW"]

    # BUY: Close breaks above upper Keltner AND EMA10 > EMA21
    if close > kc_upper and ema_fast > ema_slow:
        return "BUY"

    # SELL: Close drops below KC mid OR EMA10 crosses below EMA21
    ema_crossover_down = (prev_ema_fast >= prev_ema_slow) and (ema_fast < ema_slow)
    if close < kc_mid or ema_crossover_down:
        return "SELL"

    return "HOLD"


def place_order(access_token: str, symbol: str, side: int, qty: int = QUANTITY):
    """
    Places an order on Fyers.

    Args:
        access_token: Fyers access token
        symbol: Fyers symbol (e.g., NSE:RELIANCE-EQ)
        side: 1 = BUY, -1 = SELL
        qty: Number of shares
    """
    headers = {
        "Authorization": f"{FYERS_APP_ID}:{access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "symbol": symbol,
        "qty": qty,
        "type": 2,          # Market order
        "side": side,        # 1=Buy, -1=Sell
        "productType": "CNC",  # Cash and Carry (delivery)
        "limitPrice": 0,
        "stopPrice": 0,
        "validity": "DAY",
        "disclosedQty": 0,
        "offlineOrder": False,
        "stopLoss": 0,
        "takeProfit": 0,
    }

    response = requests.post(ORDER_URL, json=payload, headers=headers)
    data = response.json()

    if data.get("s") == "ok":
        print(f"    Order placed: {symbol} {'BUY' if side == 1 else 'SELL'} x{qty} - Order ID: {data.get('id', 'N/A')}")
    else:
        print(f"    Order FAILED: {symbol} - {data.get('message', data)}")

    return data


def get_positions(access_token: str) -> dict:
    """Fetches current open positions from Fyers."""
    headers = {"Authorization": f"{FYERS_APP_ID}:{access_token}"}
    url = "https://api-t1.fyers.in/api/v3/positions"
    response = requests.get(url, headers=headers)
    data = response.json()
    positions = {}
    if data.get("s") == "ok":
        for pos in data.get("netPositions", []):
            positions[pos["symbol"]] = pos.get("netQty", 0)
    return positions


def main():
    print("=" * 60)
    print("  KELTNER TUNED LIVE TRADING (ATR 2.0 + EMA 10/21)")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    access_token = get_access_token()
    stocks = read_stocks(STOCKS_FILE)

    if not stocks:
        print("No stocks found in stocks_to_test.txt")
        return

    print(f"\nScanning {len(stocks)} stocks for signals...\n")

    # Fetch current positions
    positions = get_positions(access_token)

    buy_signals = []
    sell_signals = []

    for symbol in stocks:
        fyers_symbol = to_fyers_symbol(symbol)
        try:
            # Fetch latest 60 days of data (enough for indicators)
            df = fetch_historical_data(fyers_symbol, access_token, days=60)
            df = compute_indicators(df)
            signal = generate_signal(df)

            current_qty = positions.get(fyers_symbol, 0)
            latest_close = df.iloc[-1]["Close"]

            if signal == "BUY" and current_qty == 0:
                buy_signals.append((fyers_symbol, latest_close))
                print(f"  [BUY SIGNAL]  {fyers_symbol:30s}  Close: {latest_close:.2f}")
            elif signal == "SELL" and current_qty > 0:
                sell_signals.append((fyers_symbol, latest_close, current_qty))
                print(f"  [SELL SIGNAL] {fyers_symbol:30s}  Close: {latest_close:.2f}  Qty: {current_qty}")
            else:
                print(f"  [HOLD]        {fyers_symbol:30s}  Close: {latest_close:.2f}")

        except Exception as e:
            print(f"  [ERROR]       {fyers_symbol:30s}  {e}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  SIGNALS SUMMARY")
    print(f"{'=' * 60}")
    print(f"  BUY signals:  {len(buy_signals)}")
    print(f"  SELL signals: {len(sell_signals)}")

    if not buy_signals and not sell_signals:
        print("  No actionable signals today.")
        return

    # Confirm before placing orders
    print(f"\n  ** DRY RUN MODE **")
    print(f"  To place real orders, set DRY_RUN=False in your .env file")
    print()

    dry_run = os.getenv("DRY_RUN", "True").lower() != "false"

    if dry_run:
        print("  Orders NOT placed (Dry Run mode).")
        print("  Set DRY_RUN=False in .env to enable live trading.")
    else:
        # Place SELL orders first (free up capital)
        for fyers_symbol, close, qty in sell_signals:
            place_order(access_token, fyers_symbol, side=-1, qty=qty)

        # Place BUY orders
        for fyers_symbol, close in buy_signals:
            place_order(access_token, fyers_symbol, side=1, qty=QUANTITY)


if __name__ == "__main__":
    main()
