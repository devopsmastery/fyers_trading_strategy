"""
Fyers Live Trading Script: Keltner Tuned (ATR 2.0 + EMA 10/21)

This script:
1. Authenticates with Fyers API
2. Fetches latest daily candle data for stocks in stocks_to_test.txt
3. Computes Keltner Channel (ATR 2.0) and EMA 10/21 indicators
4. Generates color-coded BUY/SELL signals with quality scores
5. Places orders via Fyers API (when DRY_RUN=False)

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

# Enable ANSI colors on Windows
if sys.platform == "win32":
    os.system("")  # Enables ANSI escape sequences in Windows terminal

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


# ============================================================
# ANSI Color Codes
# ============================================================
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    DIM = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"


def colored(text, color):
    return f"{color}{text}{Colors.RESET}"


# ============================================================
# Indicator Computation
# ============================================================

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

    # Volume SMA for volume confirmation
    df["VOL_SMA"] = df["Volume"].rolling(window=20).mean()

    return df


# ============================================================
# Signal Generation with Quality Score
# ============================================================

def generate_signal(df: pd.DataFrame) -> tuple:
    """
    Generate a trading signal with quality metrics.

    Returns: (signal, quality_score, reasons)
        signal: 'BUY', 'SELL', or 'HOLD'
        quality_score: 0-100 (higher = stronger signal)
        reasons: list of strings explaining why
    """
    if len(df) < KC_PERIOD + 1:
        return "HOLD", 0, ["Insufficient data"]

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    close = latest["Close"]
    kc_upper = latest["KC_UPPER"]
    kc_mid = latest["KC_MID"]
    kc_lower = latest["KC_LOWER"]
    atr = latest["ATR"]
    ema_fast = latest["EMA_FAST"]
    ema_slow = latest["EMA_SLOW"]
    prev_ema_fast = prev["EMA_FAST"]
    prev_ema_slow = prev["EMA_SLOW"]
    volume = latest["Volume"]
    vol_sma = latest["VOL_SMA"]

    # ---- BUY SIGNAL ----
    if close > kc_upper and ema_fast > ema_slow:
        score = 40  # Base score for meeting entry criteria
        reasons = []

        # Quality Factor 1: Breakout strength (how far above upper KC)
        breakout_pct = ((close - kc_upper) / atr) * 100 if atr > 0 else 0
        if breakout_pct > 50:
            score += 15
            reasons.append(f"Strong breakout ({breakout_pct:.0f}% of ATR above KC)")
        elif breakout_pct > 20:
            score += 10
            reasons.append(f"Moderate breakout ({breakout_pct:.0f}% of ATR above KC)")
        else:
            score += 5
            reasons.append(f"Marginal breakout ({breakout_pct:.0f}% of ATR above KC)")

        # Quality Factor 2: EMA trend strength (gap between EMA10 and EMA21)
        ema_gap_pct = ((ema_fast - ema_slow) / ema_slow) * 100
        if ema_gap_pct > 2:
            score += 15
            reasons.append(f"Strong EMA trend (EMA10 {ema_gap_pct:.1f}% above EMA21)")
        elif ema_gap_pct > 0.5:
            score += 10
            reasons.append(f"Moderate EMA trend (EMA10 {ema_gap_pct:.1f}% above EMA21)")
        else:
            score += 5
            reasons.append(f"Weak EMA trend (EMA10 {ema_gap_pct:.1f}% above EMA21)")

        # Quality Factor 3: Fresh EMA crossover (recently crossed up)
        if prev_ema_fast <= prev_ema_slow and ema_fast > ema_slow:
            score += 10
            reasons.append("Fresh EMA crossover (today)")

        # Quality Factor 4: Volume confirmation
        if vol_sma > 0 and volume > vol_sma * 1.5:
            score += 15
            reasons.append(f"High volume ({volume/vol_sma:.1f}x avg)")
        elif vol_sma > 0 and volume > vol_sma:
            score += 5
            reasons.append(f"Above-avg volume ({volume/vol_sma:.1f}x avg)")

        # Quality Factor 5: Price above both EMAs (strong uptrend)
        if close > ema_fast > ema_slow:
            score += 5
            reasons.append("Price > EMA10 > EMA21 (aligned uptrend)")

        return "BUY", min(score, 100), reasons

    # ---- SELL SIGNAL ----
    ema_crossover_down = (prev_ema_fast >= prev_ema_slow) and (ema_fast < ema_slow)
    if close < kc_mid or ema_crossover_down:
        score = 50
        reasons = []

        if close < kc_mid:
            reasons.append("Price below KC mid-line")
        if ema_crossover_down:
            reasons.append("EMA10 crossed below EMA21 (bearish)")
            score += 20
        if close < kc_lower:
            reasons.append("Price below KC lower band (strong sell)")
            score += 20
        if ema_fast < ema_slow:
            reasons.append("EMA10 < EMA21 (downtrend)")

        return "SELL", min(score, 100), reasons

    # ---- HOLD ----
    reasons = []
    if close < kc_upper:
        reasons.append("Price inside Keltner Channel")
    if ema_fast <= ema_slow:
        reasons.append("EMA10 <= EMA21 (no bullish trend)")
    return "HOLD", 0, reasons


def quality_bar(score):
    """Create a visual quality bar: [======    ] 60%"""
    filled = int(score / 10)
    empty = 10 - filled
    if score >= 75:
        color = Colors.GREEN
    elif score >= 50:
        color = Colors.YELLOW
    else:
        color = Colors.RED
    return f"{color}[{'=' * filled}{' ' * empty}] {score}%{Colors.RESET}"


def quality_label(score):
    """Return a text label for the score."""
    if score >= 80:
        return colored("EXCELLENT", Colors.BOLD + Colors.GREEN)
    elif score >= 65:
        return colored("GOOD", Colors.GREEN)
    elif score >= 50:
        return colored("MODERATE", Colors.YELLOW)
    else:
        return colored("WEAK", Colors.RED)


# ============================================================
# Order Placement
# ============================================================

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
        side_text = colored("BUY", Colors.GREEN) if side == 1 else colored("SELL", Colors.RED)
        print(f"    Order placed: {symbol} {side_text} x{qty} - Order ID: {data.get('id', 'N/A')}")
    else:
        print(colored(f"    Order FAILED: {symbol} - {data.get('message', data)}", Colors.RED))

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


# ============================================================
# Main
# ============================================================

def main():
    print()
    print(colored("=" * 70, Colors.CYAN))
    print(colored("  KELTNER TUNED LIVE SCANNER  (ATR 2.0 + EMA 10/21)", Colors.BOLD + Colors.CYAN))
    print(colored(f"  {datetime.now().strftime('%A, %d %B %Y  %H:%M:%S')}", Colors.CYAN))
    print(colored("=" * 70, Colors.CYAN))

    access_token = get_access_token()
    stocks = read_stocks(STOCKS_FILE)

    if not stocks:
        print(colored("No stocks found in stocks_to_test.txt", Colors.RED))
        return

    print(f"\n  Scanning {colored(str(len(stocks)), Colors.BOLD)} stocks for signals...\n")

    # Fetch current positions
    positions = get_positions(access_token)

    buy_signals = []
    sell_signals = []
    hold_count = 0
    error_count = 0

    for i, symbol in enumerate(stocks, 1):
        fyers_symbol = to_fyers_symbol(symbol)
        try:
            # Fetch latest 60 days of data (enough for indicators)
            df = fetch_historical_data(fyers_symbol, access_token, days=60)
            df = compute_indicators(df)
            signal, score, reasons = generate_signal(df)

            current_qty = positions.get(fyers_symbol, 0)
            latest_close = df.iloc[-1]["Close"]

            progress = colored(f"[{i:3d}/{len(stocks)}]", Colors.DIM)

            if signal == "BUY" and current_qty == 0:
                buy_signals.append((fyers_symbol, latest_close, score, reasons))
                tag = colored(" BUY ", Colors.BOLD + Colors.WHITE + Colors.BG_GREEN)
                print(f"  {progress} {tag} {fyers_symbol:25s}  Close: {latest_close:>10.2f}  {quality_bar(score)}")
            elif signal == "SELL" and current_qty > 0:
                sell_signals.append((fyers_symbol, latest_close, current_qty, score, reasons))
                tag = colored(" SELL", Colors.BOLD + Colors.WHITE + Colors.BG_RED)
                print(f"  {progress} {tag} {fyers_symbol:25s}  Close: {latest_close:>10.2f}  Qty: {current_qty}")
            else:
                hold_count += 1
                tag = colored("HOLD", Colors.DIM)
                print(f"  {progress} {tag}  {fyers_symbol:25s}  Close: {latest_close:>10.2f}")

        except Exception as e:
            error_count += 1
            tag = colored(" ERR ", Colors.BOLD + Colors.RED)
            print(f"  {progress} {tag} {fyers_symbol:25s}  {e}")

    # ============================================================
    # SIGNAL SUMMARY DASHBOARD
    # ============================================================
    print()
    print(colored("=" * 70, Colors.CYAN))
    print(colored("  SIGNAL DASHBOARD", Colors.BOLD + Colors.CYAN))
    print(colored("=" * 70, Colors.CYAN))
    print(f"  Stocks scanned: {len(stocks)}")
    print(f"  {colored('BUY signals:', Colors.GREEN)}  {len(buy_signals)}")
    print(f"  {colored('SELL signals:', Colors.RED)} {len(sell_signals)}")
    print(f"  {colored('HOLD:', Colors.DIM)}         {hold_count}")
    if error_count:
        print(f"  {colored('Errors:', Colors.RED)}       {error_count}")

    # ---- BUY SIGNAL DETAILS ----
    if buy_signals:
        # Sort by quality score descending (best signals first)
        buy_signals.sort(key=lambda x: x[2], reverse=True)

        print()
        print(colored("  --- BUY SIGNALS (sorted by quality) ---", Colors.GREEN + Colors.BOLD))
        print()
        for fyers_symbol, close, score, reasons in buy_signals:
            name = fyers_symbol.replace("NSE:", "").replace("-EQ", "")
            print(f"  {colored(name, Colors.BOLD + Colors.GREEN):20s}  "
                  f"Close: {close:>10.2f}  "
                  f"Quality: {quality_bar(score)}  {quality_label(score)}")
            for reason in reasons:
                print(f"    {colored('>', Colors.GREEN)} {reason}")
            print()

    # ---- SELL SIGNAL DETAILS ----
    if sell_signals:
        print()
        print(colored("  --- SELL SIGNALS ---", Colors.RED + Colors.BOLD))
        print()
        for fyers_symbol, close, qty, score, reasons in sell_signals:
            name = fyers_symbol.replace("NSE:", "").replace("-EQ", "")
            print(f"  {colored(name, Colors.BOLD + Colors.RED):20s}  "
                  f"Close: {close:>10.2f}  Qty: {qty}")
            for reason in reasons:
                print(f"    {colored('>', Colors.RED)} {reason}")
            print()

    # ---- NO SIGNALS ----
    if not buy_signals and not sell_signals:
        print(f"\n  {colored('No actionable signals today.', Colors.YELLOW)}")
        return

    # ---- TRADING GUIDE ----
    print(colored("-" * 70, Colors.DIM))
    print(colored("  HOW TO READ SIGNALS:", Colors.BOLD))
    print(f"  {colored('Quality Score:', Colors.BOLD)} Higher = stronger signal. Look for {colored('65+', Colors.GREEN)} for good trades.")
    print(f"  {colored('EXCELLENT (80+):', Colors.GREEN)} All factors aligned - strong breakout, trend, volume")
    print(f"  {colored('GOOD (65-79):', Colors.GREEN)} Most factors aligned - solid entry candidate")
    print(f"  {colored('MODERATE (50-64):', Colors.YELLOW)} Some factors present - enter with caution")
    print(f"  {colored('WEAK (<50):', Colors.RED)} Few factors - consider skipping")
    print(colored("-" * 70, Colors.DIM))

    # ---- ORDER PLACEMENT ----
    dry_run = os.getenv("DRY_RUN", "True").lower() != "false"

    if dry_run:
        print(f"\n  {colored('** DRY RUN MODE **', Colors.YELLOW + Colors.BOLD)}")
        print(f"  {colored('Orders NOT placed. Set DRY_RUN=False in .env to enable live trading.', Colors.YELLOW)}")
    else:
        print(f"\n  {colored('** LIVE MODE - PLACING ORDERS **', Colors.RED + Colors.BOLD)}")
        # Place SELL orders first (free up capital)
        for fyers_symbol, close, qty, score, reasons in sell_signals:
            place_order(access_token, fyers_symbol, side=-1, qty=qty)

        # Place BUY orders
        for fyers_symbol, close, score, reasons in buy_signals:
            place_order(access_token, fyers_symbol, side=1, qty=QUANTITY)

    print()


if __name__ == "__main__":
    main()
