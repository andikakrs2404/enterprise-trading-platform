#!/usr/bin/env python3
"""
Test script Layer 1 - Market Data Platform Basic Functionality
Menguji: Normalizer + Konsep Gateway (tanpa library eksternal)
"""
import sys
import os
sys.path.insert(0, '/home/rtk/enterprise-trading-platform')

from layer1_market_data.normalizer.normalizer import normalize_to_internal, INTERNAL_FORMAT_SCHEMA
from layer1_market_data.normalizer.normal_format import ExchangeFormatNormalizer

def test_normalizer():
    """Test normalizer dengan data test case"""
    print("=" * 60)
    print("TEST 1: Normalizer Basic Functionality")
    print("=" * 60)
    
    test_cases = [
        ("binance", {"e": "24hrTicker", "s": "BTCUSDT", "c": "115000", "q": "1200", "E": 1234567890, "m": False}),
        ("bybit", {"symbol": "BTCUSDT", "price": "115000", "side": "Buy", "qty": "1.5", "timestamp": 1234567890}),
        ("okx", {"instId": "BTC-USDT", "px": "115000", "sz": "1.5", "side": "buy", "ts": 1234567890}),
    ]
    
    all_passed = True
    for exchange, raw_data in test_cases:
        try:
            result = normalize_to_internal(exchange, raw_data)
            # Validate schema
            assert isinstance(result["exchange"], str), "exchange harus string"
            assert isinstance(result["symbol"], str), "symbol harus string"
            assert isinstance(result["price"], (int, float)), "price harus numeric"
            assert isinstance(result["qty"], (int, float)), "qty harus numeric"
            assert result["side"] in ["buy", "sell"], "side harus buy/sell"
            assert isinstance(result["timestamp"], int), "timestamp harus int"
            
            print(f"✓ {exchange.upper()}: OK")
            print(f"  Output: exchange={result['exchange']}, symbol={result['symbol']}, price={result['price']}, qty={result['qty']}, side={result['side']}, timestamp={result['timestamp']}")
        except Exception as e:
            print(f"✗ {exchange.upper()}: FAILED - {e}")
            all_passed = False
    
    print()
    
    # Test schema validation
    print("=" * 60)
    print("TEST 2: Schema Validation")
    print("=" * 60)
    
    valid_data = {
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "price": 115000.0,
        "qty": 1.5,
        "side": "buy",
        "timestamp": 1234567890
    }
    
    # Check all required fields ada
    required_fields = ["exchange", "symbol", "price", "qty", "side", "timestamp"]
    missing = [f for f in required_fields if f not in valid_data]
    
    if missing:
        print(f"✗ Missing fields: {missing}")
        all_passed = False
    else:
        print(f"✓ All required fields present")
    
    # Check type constraints
    type_checks = {
        "exchange": str,
        "symbol": str,
        "price": (int, float),
        "qty": (int, float),
        "side": str,
        "timestamp": int
    }
    
    for field, expected_type in type_checks.items():
        actual_type = type(valid_data.get(field))
        if actual_type != expected_type:
            print(f"✗ {field}: expected {expected_type.__name__}, got {actual_type.__name__}")
            all_passed = False
    
    if all_passed:
        print("✓ Schema validation passed")
    print()
    
    # Test data integrity - ensure price > 0, qty > 0
    print("=" * 60)
    print("TEST 3: Data Integrity Checks")
    print("=" * 60)
    
    for exchange, raw_data in test_cases:
        result = normalize_to_internal(exchange, raw_data)
        if result["price"] <= 0:
            print(f"✗ {exchange}: price harus > 0, got {result['price']}")
            all_passed = False
        else:
            print(f"✓ {exchange}: price > 0 ✓")
        
        if result["qty"] <= 0:
            print(f"✗ {exchange}: qty harus > 0, got {result['qty']}")
            all_passed = False
        else:
            print(f"✓ {exchange}: qty > 0 ✓")
    
    print()
    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = test_normalizer()
    sys.exit(0 if success else 1)
