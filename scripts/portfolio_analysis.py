import os
import sys

# Ensure parent dir is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.portfolio_db import sync_portfolio
from data.data_fetcher import load_historical_csv, to_fyers_symbol
from live_trading.execute_trades import compute_indicators

def analyze_portfolio():
    db = sync_portfolio()
    if not db:
        print("Portfolio is empty. Add stocks to Portfolio.txt first.")
        return
        
    print("=" * 80)
    print("                 PORTFOLIO SCAN REPORT")
    print("=" * 80)
    print(f"{'SYMBOL':<15} | {'BUY P.':<10} | {'CUR. P.':<10} | {'P&L %':<8} | {'STATUS':<15}")
    print("-" * 80)
    
    strong_hold = []
    caution = []
    sell = []
    errors = []
    access_token = None
    
    for symbol, data in db.items():
        qty = data.get('qty', 0)
        buy_price = data.get('avg_cost', 0.0)
        
        fyers_sym = to_fyers_symbol(symbol)
        try:
            df = load_historical_csv(fyers_sym)
        except FileNotFoundError:
            if not access_token:
                from live_trading.fyers_auth import get_access_token
                access_token = get_access_token()
            try:
                from data.data_fetcher import fetch_historical_data, save_historical_data
                df = fetch_historical_data(fyers_sym, access_token)
                if df is not None and not df.empty:
                    save_historical_data(fyers_sym, df)
            except Exception as e:
                print(f"Failed to fetch {symbol}: {e}")
                df = None
            
        if df is None or df.empty:
            errors.append(symbol)
            continue
            
        # Compute indicators
        try:
            df = compute_indicators(df)
            latest = df.iloc[-1]
            close = latest['Close']
            
            pnl_pct = 0.0
            if buy_price > 0:
                pnl_pct = ((close - buy_price) / buy_price) * 100
                
            kc_upper = latest['KC_UPPER']
            kc_mid = latest['KC_MID']
            ema10 = latest['EMA_FAST']
            ema21 = latest['EMA_SLOW']
            
            # Categorize
            if close > kc_upper and ema10 > ema21:
                status = "STRONG HOLD"
                strong_hold.append(symbol)
            elif close < kc_mid or ema10 < ema21:
                status = "SELL"
                sell.append(symbol)
            else:
                status = "CAUTION"
                caution.append(symbol)
                
            pnl_str = f"{pnl_pct:+.1f}%"
            print(f"{symbol:<15} | {buy_price:<10.2f} | {close:<10.2f} | {pnl_str:<8} | {status:<15}")
            
        except Exception as e:
            errors.append(symbol)
            
    print("=" * 80)
    print(f"Summary: {len(strong_hold)} STRONG HOLD | {len(caution)} CAUTION | {len(sell)} SELL")
    if errors:
        print(f"Warning: Could not analyze {len(errors)} stocks (missing historical data).")
    print("=" * 80)

if __name__ == "__main__":
    analyze_portfolio()
