"""
Deep-dive analysis for all GOOD quality (65-79%) signal stocks.
Ranks them by a composite score combining multiple factors.
"""

import os
import sys
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from live_trading.fyers_auth import get_access_token
from data.data_fetcher import to_fyers_symbol, fetch_historical_data, append_live_quote
from live_trading.execute_trades import compute_indicators


# All GOOD quality stocks from today's scan (65-79%)
GOOD_CANDIDATES = [
    ("ADANIENSOL", 75), ("CUPID", 75), ("THANGAMAYL", 75), ("STYL", 75),
    ("PAISALO", 75), ("LODHA", 75), ("SPARC", 75), ("TORNTPHARM", 75),
    ("ASTRAMICRO", 70), ("FIVESTAR", 70), ("EBGNG", 70), ("GANESHHOU", 70),
    ("AKUMS", 70), ("CGCL", 70), ("RPEL", 70), ("NYKAA", 70),
    ("STOVEKRAFT", 65), ("ATHERENERG", 65), ("ANANDRATHI", 65),
    ("ZYDUSLIFE", 65), ("HONASA", 65), ("PRESTIGE", 65),
]


def analyze_stock(symbol, access_token):
    """Compute deep metrics and return as dict for ranking."""
    fyers_symbol = to_fyers_symbol(symbol)
    df = fetch_historical_data(fyers_symbol, access_token, days=365)
    df = append_live_quote(df, fyers_symbol, access_token)
    df = compute_indicators(df)

    latest = df.iloc[-1]
    close = latest["Close"]
    high_52w = df["High"].max()
    low_52w = df["Low"].min()

    close_5d = df["Close"].iloc[-6] if len(df) > 5 else close
    close_20d = df["Close"].iloc[-21] if len(df) > 20 else close
    close_60d = df["Close"].iloc[-61] if len(df) > 60 else close

    pct_5d = ((close - close_5d) / close_5d) * 100
    pct_20d = ((close - close_20d) / close_20d) * 100
    pct_60d = ((close - close_60d) / close_60d) * 100

    # RSI 14
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]

    # Volume
    vol = latest["Volume"]
    vol_avg = latest["VOL_SMA"]
    vol_ratio = vol / vol_avg if vol_avg > 0 else 0

    # Keltner
    kc_upper = latest["KC_UPPER"]
    kc_mid = latest["KC_MID"]
    kc_lower = latest["KC_LOWER"]
    atr = latest["ATR"]
    breakout_pct = ((close - kc_upper) / atr) * 100 if atr > 0 else 0

    # EMA
    ema_fast = latest["EMA_FAST"]
    ema_slow = latest["EMA_SLOW"]
    ema_gap = ((ema_fast - ema_slow) / ema_slow) * 100

    # Risk
    daily_returns = df["Close"].pct_change().dropna()
    volatility_daily = daily_returns.std() * 100
    volatility_annual = volatility_daily * np.sqrt(252)

    max_drawdown = 0
    peak = df["Close"].iloc[0]
    for price in df["Close"]:
        if price > peak:
            peak = price
        dd = ((peak - price) / peak) * 100
        if dd > max_drawdown:
            max_drawdown = dd

    # Stop loss & risk
    stop_loss = max(kc_mid, close - 2 * atr)
    risk_pct = ((close - stop_loss) / close) * 100
    target_1 = close + (close - stop_loss)
    target_2 = close + 2 * (close - stop_loss)

    # Distance from 52W high (room to run)
    dist_52w_high = ((high_52w - close) / close) * 100

    # Support/Resistance
    recent = df.tail(60)
    support = recent["Low"].rolling(5).min().dropna().iloc[-1]
    resistance = recent["High"].rolling(5).max().dropna().iloc[-1]

    # --- COMPOSITE RANKING SCORE ---
    # Factors: lower RSI is better, lower volatility is better,
    # higher volume ratio is better, more room to 52W high is better,
    # lower risk_pct (tighter stop) is better, stronger EMA gap is better
    rank_score = 0

    # RSI: prefer 60-75 range (strong but not overbought)
    if current_rsi < 70:
        rank_score += 25
    elif current_rsi < 75:
        rank_score += 15
    elif current_rsi < 80:
        rank_score += 5

    # Volatility: lower is better for positional
    if volatility_annual < 35:
        rank_score += 20
    elif volatility_annual < 45:
        rank_score += 15
    elif volatility_annual < 55:
        rank_score += 10

    # Volume confirmation
    if vol_ratio > 2.0:
        rank_score += 20
    elif vol_ratio > 1.5:
        rank_score += 15
    elif vol_ratio > 1.0:
        rank_score += 5

    # Room to 52W high
    if dist_52w_high > 20:
        rank_score += 15
    elif dist_52w_high > 10:
        rank_score += 10
    elif dist_52w_high > 5:
        rank_score += 5

    # Risk (stop loss distance)
    if risk_pct < 8:
        rank_score += 15
    elif risk_pct < 12:
        rank_score += 10
    elif risk_pct < 15:
        rank_score += 5

    # EMA trend strength
    if ema_gap > 5:
        rank_score += 10
    elif ema_gap > 3:
        rank_score += 7
    elif ema_gap > 1:
        rank_score += 3

    return {
        "Symbol": symbol,
        "Close": close,
        "RSI": current_rsi,
        "Breakout%": breakout_pct,
        "EMA_Gap%": ema_gap,
        "Vol_Ratio": vol_ratio,
        "Volatility%": volatility_annual,
        "MaxDD%": max_drawdown,
        "Risk%": risk_pct,
        "Dist_52WH%": dist_52w_high,
        "5D_Ret%": pct_5d,
        "20D_Ret%": pct_20d,
        "60D_Ret%": pct_60d,
        "KC_Mid": kc_mid,
        "StopLoss": stop_loss,
        "Target1": target_1,
        "Target2": target_2,
        "Support": support,
        "Resistance": resistance,
        "High_52W": high_52w,
        "Low_52W": low_52w,
        "RankScore": rank_score,
        "SignalQuality": 0,  # filled later
    }


def main():
    access_token = get_access_token()

    print("\n" + "=" * 70)
    print("  DEEP DIVE: ALL GOOD QUALITY CANDIDATES (65-79%)")
    print("  Analyzing 22 stocks to find the best 3...")
    print("=" * 70)

    results = []
    for symbol, quality in GOOD_CANDIDATES:
        try:
            print(f"  Analyzing {symbol:20s}...", end="", flush=True)
            data = analyze_stock(symbol, access_token)
            data["SignalQuality"] = quality
            results.append(data)
            print(f"  Rank Score: {data['RankScore']}")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Sort by composite rank score descending
    results.sort(key=lambda x: x["RankScore"], reverse=True)

    # Print full ranking table
    print(f"\n{'=' * 70}")
    print(f"  COMPOSITE RANKING (higher = better risk-adjusted trade)")
    print(f"{'=' * 70}")
    print(f"  {'#':>3}  {'Stock':<15} {'Close':>10} {'Rank':>5} {'RSI':>6} {'Vol':>5} "
          f"{'Volat%':>7} {'Risk%':>6} {'Room%':>6} {'EMA%':>6}")
    print(f"  {'-'*3}  {'-'*15} {'-'*10} {'-'*5} {'-'*6} {'-'*5} {'-'*7} {'-'*6} {'-'*6} {'-'*6}")

    for i, r in enumerate(results, 1):
        marker = " <<" if i <= 3 else ""
        print(f"  {i:3d}  {r['Symbol']:<15} {r['Close']:>10,.2f} {r['RankScore']:>5} "
              f"{r['RSI']:>6.1f} {r['Vol_Ratio']:>5.1f}x {r['Volatility%']:>6.1f}% "
              f"{r['Risk%']:>5.1f}% {r['Dist_52WH%']:>5.1f}% {r['EMA_Gap%']:>5.1f}%{marker}")

    # Detailed view of top 3
    print(f"\n{'=' * 70}")
    print(f"  TOP 3 RECOMMENDED TRADES FROM GOOD CANDIDATES")
    print(f"{'=' * 70}")

    for i, r in enumerate(results[:3], 1):
        print(f"\n  --- #{i}: {r['Symbol']} (Rank Score: {r['RankScore']}) ---")
        print(f"  {'Price:':<25} Rs.{r['Close']:,.2f}")
        print(f"  {'52-Week Range:':<25} Rs.{r['Low_52W']:,.2f} - Rs.{r['High_52W']:,.2f} "
              f"({r['Dist_52WH%']:.1f}% below high)")
        print(f"  {'Returns (5D/20D/60D):':<25} {r['5D_Ret%']:+.1f}% / {r['20D_Ret%']:+.1f}% / {r['60D_Ret%']:+.1f}%")
        print(f"  {'RSI:':<25} {r['RSI']:.1f}")
        print(f"  {'Volume Ratio:':<25} {r['Vol_Ratio']:.1f}x avg")
        print(f"  {'EMA Gap:':<25} {r['EMA_Gap%']:.1f}%")
        print(f"  {'Breakout Strength:':<25} {r['Breakout%']:.0f}% of ATR")
        print(f"  {'Annual Volatility:':<25} {r['Volatility%']:.1f}%")
        print(f"  {'Max Drawdown (1Y):':<25} {r['MaxDD%']:.1f}%")
        print(f"  {'Entry:':<25} Rs.{r['Close']:,.2f}")
        print(f"  {'Stop Loss:':<25} Rs.{r['StopLoss']:,.2f}  (Risk: {r['Risk%']:.1f}%)")
        print(f"  {'Target 1 (1:1 R:R):':<25} Rs.{r['Target1']:,.2f}")
        print(f"  {'Target 2 (1:2 R:R):':<25} Rs.{r['Target2']:,.2f}")

    print()


if __name__ == "__main__":
    main()
