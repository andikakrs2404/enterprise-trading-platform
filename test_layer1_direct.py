#!/usr/bin/env python3
"""
Test script Layer 1 - Direct module import (skip package __init__.py)
"""
import sys
import os

# Import langsung dari module, bukan package
# Add the normalizer directory to path
sys.path.insert(0, '/home/rtk/enterprise-trading-platform/layer1_market_data/normalizer')

# Import the normalizer module functions directly
import importlib.util
normalizer_spec = importlib.util.spec_from_file_location("normalizer", '/home/rtk/enterprise-trading-platform/layer1_market_data/normalizer/normalizer.py')
normalizer_module = importlib.util.module_from_spec(normalizer_spec)

# Also import normal_format
normal_format_spec = importlib.util.spec_from_file_location("normal_format", '/home/rtk/enterprise-trading-platform/layer1_market_data/normalizer/normal_format.py')
normal_format_module = importlib.util.module_from_spec(normal_format_spec)

normal_format_module_normalizer = importlib.util.module_from_spec(normal_format_spec)
sys.modules['layer1_market_data.normalizer.normal_format'] = normal_format_module
normal_format_spec.loader.exec_module(normal_format_module)

# Now import from normalizer
normalizer_spec.loader.exec_module(normalizer_module)

normalize_to_internal = normalizer_module.normalize_to_internal
INTERNAL_FORMAT_SCHEMA = normalizer_module.INTERNAL_FORMAT_SCHEMA
ExchangeFormatNormalizer = normal_format_module.ExchangeFormatNormalizer

print("=" * 60)
print("TEST: Direct Module Import - Layer 1 Normalizer")
print("=" * 60)

# Test 1: Basic normalize functionality
print("\n[TEST 1] Normalizer Basic Functionality")
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
print("=" * 60)
if all_passed:
    print("✓ ALL TESTS PASSED")
else:
    print("✗ SOME TESTS FAILED")
print("=" * 60)
