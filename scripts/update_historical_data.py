import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.fyers_auth import get_access_token
from data.data_fetcher import (
    read_stocks, 
    to_fyers_symbol, 
    load_historical_csv, 
    save_historical_data,
    STOCKS_FILE
)
from data.data_fetcher import HISTORY_URL, FYERS_APP_ID
import requests

WATCHLIST_FILE = os.path.join(os.path.dirname(STOCKS_FILE), "stocks_watchlist.txt")

def fetch_missing_data(symbol: str, access_token: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Fetches candle data for a specific date range."""
    headers = {"Authorization": f"{FYERS_APP_ID}:{access_token}"}
    params = {
        "symbol": symbol,
        "resolution": "D",
        "date_format": "1",
        "range_from": start_date.strftime("%Y-%m-%d"),
        "range_to": end_date.strftime("%Y-%m-%d"),
        "cont_flag": "1",
    }
    
    response = requests.get(HISTORY_URL, params=params, headers=headers)
    data = response.json()
    
    if data.get("s") == "ok" and "candles" in data and len(data["candles"]) > 0:
        df = pd.DataFrame(data["candles"], columns=["Epoch", "Open", "High", "Low", "Close", "Volume"])
        df["Date"] = pd.to_datetime(df["Epoch"], unit="s")
        df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]
        df.sort_values("Date", inplace=True)
        df.set_index("Date", inplace=True)
        return df
    return pd.DataFrame()

def main():
    print("========================================")
    print("      UPDATING HISTORICAL DATA          ")
    print("========================================")
    
    # Load all unique stocks
    main_stocks = read_stocks(STOCKS_FILE)
    watchlist_stocks = read_stocks(WATCHLIST_FILE) if os.path.exists(WATCHLIST_FILE) else []
    all_stocks = list(dict.fromkeys(main_stocks + watchlist_stocks))
    
    if not all_stocks:
        print("No stocks found.")
        return
        
    access_token = get_access_token()
    today = datetime.now()
    
    updated_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(all_stocks, 1):
        fyers_symbol = to_fyers_symbol(symbol)
        print(f"[{i}/{len(all_stocks)}] Updating {fyers_symbol}...", end=" ")
        
        try:
            df = load_historical_csv(fyers_symbol)
            if df.empty:
                print("CSV is empty, skipping append.")
                fail_count += 1
                continue
                
            last_date = df.index[-1]
            if not isinstance(last_date, datetime):
                last_date = pd.to_datetime(last_date)
                
            # If we already have today's data (or yesterday's depending on time), maybe skip
            if last_date.date() >= today.date():
                print("Already up to date.")
                continue
                
            start_fetch = last_date + timedelta(days=1)
            
            if start_fetch.date() > today.date():
                print("Already up to date.")
                continue
                
            new_df = fetch_missing_data(fyers_symbol, access_token, start_fetch, today)
            
            if not new_df.empty:
                combined_df = pd.concat([df, new_df])
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                combined_df.sort_index(inplace=True)
                save_historical_data(fyers_symbol, combined_df)
                print(f"Appended {len(new_df)} new rows.")
                updated_count += 1
            else:
                print("No new data available.")
                
        except FileNotFoundError:
            print("No existing CSV. Needs full fetch.")
            fail_count += 1
        except Exception as e:
            print(f"FAILED: {e}")
            fail_count += 1
            
        time.sleep(0.3)  # Rate limiting
        
    print(f"\nDone! {updated_count} stocks updated, {fail_count} failed/skipped.")

if __name__ == "__main__":
    main()
