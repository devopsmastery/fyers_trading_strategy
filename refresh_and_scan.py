"""
refresh_and_scan.py
Reusable script that:
  1. Refreshes historical data (last 90 days) for all stocks in stocks_to_test.txt
     by re-fetching from Fyers API and overwriting the cached CSVs.
  2. Immediately runs the live scanner on the freshened data + live quote.
"""

import os
import sys
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from live_trading.fyers_auth import get_access_token
from data.data_fetcher import (
    read_stocks, to_fyers_symbol, fetch_historical_data, save_historical_data
)

PROJECT_DIR  = os.path.dirname(os.path.abspath(__file__))
STOCKS_FILE  = os.path.join(PROJECT_DIR, "stocks_to_test.txt")
REFRESH_DAYS = 90   # Fetch last 90 days to ensure enough data for all indicators


def refresh_historical_data(access_token: str):
    """Re-fetches and overwrites cached CSVs for all stocks in stocks_to_test.txt."""
    stocks = read_stocks(STOCKS_FILE)
    if not stocks:
        print("No stocks found in stocks_to_test.txt")
        return False

    print(f"\n{'='*60}")
    print(f"  STEP 1/2 — REFRESHING HISTORICAL DATA")
    print(f"  {len(stocks)} stocks | Last {REFRESH_DAYS} days")
    print(f"{'='*60}\n")

    success = 0
    failed  = []

    for i, symbol in enumerate(stocks, 1):
        fyers_symbol = to_fyers_symbol(symbol)
        print(f"  [{i:2d}/{len(stocks)}] {symbol:<20}", end="", flush=True)
        try:
            df = fetch_historical_data(fyers_symbol, access_token, days=REFRESH_DAYS)
            save_historical_data(fyers_symbol, df)
            print(f"  {len(df)} rows  (last: {df.index[-1].date()})")
            success += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed.append(symbol)

    print(f"\n  Done: {success} refreshed, {len(failed)} failed.")
    if failed:
        print(f"  Failed: {', '.join(failed)}")

    return success > 0


def main():
    access_token = get_access_token()

    # Step 1: Refresh all historical CSVs
    ok = refresh_historical_data(access_token)
    if not ok:
        print("Aborting — no data refreshed.")
        sys.exit(1)

    # Step 2: Run the live scanner (uses refreshed data + live quote overlay)
    print(f"\n{'='*60}")
    print(f"  STEP 2/2 — RUNNING LIVE SCAN")
    print(f"{'='*60}\n")

    scanner = os.path.join(PROJECT_DIR, "live_trading", "execute_trades.py")
    subprocess.run([sys.executable, scanner], check=False)


if __name__ == "__main__":
    main()
