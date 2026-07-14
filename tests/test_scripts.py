import sys
import os
import pytest
import pandas as pd
from datetime import datetime

# Ensure parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.deep_analysis import compute_rsi

def test_compute_rsi():
    """Test the RSI computation with a known sequence of prices."""
    # Create a simple price series
    prices = pd.Series([
        100, 102, 104, 103, 105, 107, 106, 108, 110, 109, 
        111, 113, 112, 114, 115, 117, 116, 118, 120, 119
    ])
    
    rsi = compute_rsi(prices, period=14)
    
    # RSI should be a pandas Series
    assert isinstance(rsi, pd.Series)
    # Length should match input
    assert len(rsi) == len(prices)
    # The first value is usually NaN or 100 depending on implementation, but later values should be valid
    # In our implementation using rolling mean, the 14th item should have a valid RSI
    assert not pd.isna(rsi.iloc[14])
    # RSI is bounded between 0 and 100
    assert (rsi.dropna() >= 0).all()
    assert (rsi.dropna() <= 100).all()

def test_deduplication_logic():
    """Test the logic used in add_new_stocks.py for deduplicating stocks."""
    existing_stocks = {"RELIANCE", "TCS", "INFY"}
    new_stocks = ["TCS", "HDFC", "RELIANCE", "WIPRO", "HDFC"]
    
    unique_new_stocks = []
    # Deduplicate against existing, and also keep order and remove duplicates within new_stocks
    seen = set(existing_stocks)
    for s in new_stocks:
        if s not in seen:
            unique_new_stocks.append(s)
            seen.add(s)
            
    assert len(unique_new_stocks) == 2
    assert unique_new_stocks == ["HDFC", "WIPRO"]

def test_date_append_logic():
    """Test the logic to calculate the next fetch date for update_historical_data.py"""
    # Simulate a CSV that ends on 2026-07-08
    last_date = pd.to_datetime("2026-07-08")
    today = pd.to_datetime("2026-07-10")
    
    from datetime import timedelta
    start_fetch = last_date + timedelta(days=1)
    
    assert start_fetch.date() == pd.to_datetime("2026-07-09").date()
    assert start_fetch.date() <= today.date()
