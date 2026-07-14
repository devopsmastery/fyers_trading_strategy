import os
import sys
import argparse
import pandas as pd
import numpy as np

# Ensure parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_fetcher import load_historical_csv, to_fyers_symbol
from live_trading.execute_trades import compute_indicators

def compute_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def deep_analysis(symbol: str, ltp: float = None):
    fyers_symbol = to_fyers_symbol(symbol)
    try:
        df = load_historical_csv(fyers_symbol)
    except FileNotFoundError:
        print(f"Error: No historical data found for {symbol}.")
        print("Please ensure the symbol is correct and you have fetched its data.")
        return

    if df is None or df.empty:
        print(f"Error: Empty historical data found for {symbol}.")
        return

    if ltp is not None:
        import datetime
        last_row = df.iloc[-1].copy()
        last_row['Close'] = ltp
        last_row['High'] = max(last_row['High'], ltp)
        last_row['Low'] = min(last_row['Low'], ltp)
        
        # Determine the next business day (or just use today if not already in index)
        today = datetime.datetime.now()
        # If the last candle is not today, append a new row
        if pd.to_datetime(df.index[-1]).date() != today.date():
            last_row.name = today
            df = pd.concat([df, pd.DataFrame([last_row])])
        else:
            # Overwrite today's candle if it already exists
            df.iloc[-1] = last_row
    # Compute base indicators
    df = compute_indicators(df)
    
    # Compute extra indicators for deep dive
    df['RSI_14'] = compute_rsi(df['Close'], 14)
    
    # MACD (12, 26, 9)
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    latest = df.iloc[-1]
    
    print("=" * 60)
    print(f"  DEEP DIVE ANALYSIS: {fyers_symbol}")
    print(f"  Date: {latest.name.date()}")
    print("=" * 60)
    print(f"  Close Price:   {latest['Close']:.2f}")
    print(f"  Volume:        {latest['Volume']}")
    print(f"  Avg Volume:    {latest['VOL_SMA']:.0f}")
    
    vol_ratio = latest['Volume'] / latest['VOL_SMA'] if latest['VOL_SMA'] else 0
    print(f"  Volume Ratio:  {vol_ratio:.2f}x")
    print("-" * 60)
    
    # Trend Analysis
    print("  --- TREND & MOMENTUM ---")
    print(f"  EMA 10:        {latest['EMA_FAST']:.2f}")
    print(f"  EMA 21:        {latest['EMA_SLOW']:.2f}")
    if latest['EMA_FAST'] > latest['EMA_SLOW']:
        print("  Trend Status:  BULLISH (EMA 10 > EMA 21)")
    else:
        print("  Trend Status:  BEARISH (EMA 10 < EMA 21)")
        
    print(f"  RSI (14):      {latest['RSI_14']:.2f}", end=" ")
    if latest['RSI_14'] > 70:
        print("(Overbought)")
    elif latest['RSI_14'] < 30:
        print("(Oversold)")
    else:
        print("(Neutral)")
        
    print(f"  MACD:          {latest['MACD']:.2f}")
    print(f"  MACD Signal:   {latest['MACD_Signal']:.2f}")
    if latest['MACD_Hist'] > 0:
        print("  MACD Momentum: POSITIVE (MACD > Signal)")
    else:
        print("  MACD Momentum: NEGATIVE (MACD < Signal)")
    
    print("-" * 60)
    print("  --- KELTNER CHANNELS ---")
    print(f"  Upper Band:    {latest['KC_UPPER']:.2f}")
    print(f"  Middle Band:   {latest['KC_MID']:.2f}")
    print(f"  Lower Band:    {latest['KC_LOWER']:.2f}")
    
    if latest['Close'] > latest['KC_UPPER']:
        print("  Position:      BREAKOUT (Above Upper Band)")
    elif latest['Close'] < latest['KC_LOWER']:
        print("  Position:      BREAKDOWN (Below Lower Band)")
    else:
        print("  Position:      INSIDE CHANNEL")
        
    print("=" * 60)
    
    # Generate overall summary recommendation based on indicators
    score = 0
    if latest['EMA_FAST'] > latest['EMA_SLOW']: score += 1
    if latest['Close'] > latest['KC_UPPER']: score += 1
    if vol_ratio > 1.2: score += 1
    if latest['MACD_Hist'] > 0: score += 1
    if 40 <= latest['RSI_14'] <= 70: score += 1
    
    print(f"  OVERALL STRENGTH SCORE: {score}/5")
    if score >= 4:
        print("  CONCLUSION: Very Strong Candidate")
    elif score >= 2:
        print("  CONCLUSION: Moderate / Mixed Signals")
    else:
        print("  CONCLUSION: Weak / Avoid")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a deep dive technical analysis on a stock.")
    parser.add_argument("symbol", nargs="?", help="The ticker symbol to analyze")
    parser.add_argument("--ltp", type=float, help="Optional Last Traded Price to simulate today's current market price")
    args = parser.parse_args()

    symbol = args.symbol
    if not symbol:
        symbol = input("Enter ticker symbol for deep analysis: ").strip()
        while not symbol:
            symbol = input("Invalid input. Enter ticker symbol: ").strip()
            
    deep_analysis(symbol, args.ltp)
