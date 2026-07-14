import os
import sys

# Ensure parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_fetcher import read_stocks, get_access_token, fetch_historical_data, save_historical_data, to_fyers_symbol
from data.data_fetcher import STOCKS_FILE

WATCHLIST_FILE = os.path.join(os.path.dirname(STOCKS_FILE), "stocks_watchlist.txt")
NEW_STOCKS_FILE = os.path.join(os.path.dirname(STOCKS_FILE), "Newly_added_stocks.txt")

def add_new_stocks():
    print("========================================")
    print("          ADD NEW STOCKS MODULE         ")
    print("========================================")
    
    if not os.path.exists(NEW_STOCKS_FILE):
        print(f"Error: {NEW_STOCKS_FILE} does not exist.")
        return
        
    new_stocks = read_stocks(NEW_STOCKS_FILE)
    if not new_stocks:
        print("No valid stocks found in Newly_added_stocks.txt.")
        return
        
    main_stocks = read_stocks(STOCKS_FILE)
    watchlist_stocks = read_stocks(WATCHLIST_FILE) if os.path.exists(WATCHLIST_FILE) else []
    
    existing_stocks = set(main_stocks + watchlist_stocks)
    
    unique_new_stocks = []
    for s in new_stocks:
        if s not in existing_stocks:
            unique_new_stocks.append(s)
            
    if not unique_new_stocks:
        print("All stocks in Newly_added_stocks.txt are already tracked. Nothing to add.")
        return
        
    print(f"Found {len(unique_new_stocks)} new unique stocks to add.")
    
    # Append to stocks_watchlist.txt
    with open(WATCHLIST_FILE, "a") as f:
        f.write("\n# Newly added stocks\n")
        for s in unique_new_stocks:
            f.write(f"{s}\n")
            
    print(f"Appended {len(unique_new_stocks)} stocks to {os.path.basename(WATCHLIST_FILE)}.")
    
    print("Fetching historical data for new stocks...")
    access_token = get_access_token()
    
    success = 0
    for i, symbol in enumerate(unique_new_stocks, 1):
        fyers_symbol = to_fyers_symbol(symbol)
        print(f"[{i}/{len(unique_new_stocks)}] Fetching {fyers_symbol}...", end=" ")
        try:
            df = fetch_historical_data(fyers_symbol, access_token, days=365)
            path = save_historical_data(fyers_symbol, df)
            print(f"OK ({len(df)} rows)")
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            
    print(f"\nCompleted! {success}/{len(unique_new_stocks)} new stocks fully fetched.")
    
    # Clear the Newly_added_stocks.txt file
    with open(NEW_STOCKS_FILE, "w") as f:
        f.write("# Active Stocks List\n")
    print("Cleared Newly_added_stocks.txt to prevent duplication.")

if __name__ == "__main__":
    add_new_stocks()
