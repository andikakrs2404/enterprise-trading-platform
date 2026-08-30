#!/usr/bin/env python3
"""
Test script Layer 1 - Simple import test
Mengimport langsung logika normalize tanpa kompleks import package
"""
import sys
import os

# Baca dan exec file normal_format.py secara langsung
with open('/home/rtk/enterprise-trading-platform/layer1_market_data/normalizer/normal_format.py', 'r') as f:
    content = f.read()
    # Extract just the class and schema we need
    exec(content)

# Baca dan exec normalizer.py dengan context yang benar
with open('/home/rtk/enterprise-trading-platform/layer1_market_data/normalizer/normalizer.py', 'r') as f:
    content = f.read()
    # Remove the relative import, replace with direct
    content = content.replace('from .normal_format import ExchangeFormatNormalizer, INTERNAL_FORMAT_SCHEMA', 
                              'from normal_format import ExchangeFormatNormalizer, INTERNAL_FORMAT_SCHEMA')
    exec(content)

# Now the functions should be available
normalize_to_internal = normalizer_module.normalize_to_internal if 'normalizer_module' in dir() else None
INTERNAL_FORMAT_SCHEMA = normalizer_module.INTERNAL_FORMAT_SCHEMA if 'normalizer_module' in dir() else None

print("=" * 60)
print("TEST: Layer 1 Simple Import")
print("=" * 60)

# Test normalize
print("\n[TEST 1] Normalize Test")
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
        print(f"  Output: price={result['price']}, qty={result['qty']}, side={result['side']}")
    except Exception as e:
        print(f"✗ {exchange.upper()}: FAILED - {e}")
        all_passed = False

print()
print("=" * 60)
if all_passed:
    print("✓ ALL TESTS PASSED")
else:
    print("✗ SOME TESTS FAILED")
print("=" * 60)
