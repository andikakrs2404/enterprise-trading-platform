#!/usr/bin/env python3
"""Layer 1 Health Check - simplified, direct import test"""
import sys
import os

# Set paths manually FIRST
PROJECT = '/home/rtk/enterprise-trading-platform'
sys.path.insert(0, PROJECT)
sys.path.insert(0, os.path.join(PROJECT, 'layer1_market_data/normalizer'))

# Import directly from module files (NOT via package)
from normalizer import normalize_to_internal
from normal_format import ExchangeFormatNormalizer, INTERNAL_FORMAT_SCHEMA

print("✓ All imports successful")

def check_normalizer():
    test_cases = [
        ("binance", {"e": "24hrTicker", "s": "BTCUSDT", "c": "115000", "q": "1200", "E": 1234567890, "m": False}),
        ("bybit", {"symbol": "BTCUSDT", "price": "115000", "side": "Buy", "qty": "1.5", "timestamp": 1234567890}),
        ("okx", {"instId": "BTC-USDT", "px": "115000", "sz": "1.5", "side": "buy", "ts": 1234567890}),
    ]
    
    all_ok = True
    results = []
    for exchange, raw_data in test_cases:
        try:
            result = normalize_to_internal(exchange, raw_data)
            required = ["exchange", "symbol", "price", "qty", "side", "timestamp"]
            missing = [f for f in required if f not in result]
            if missing:
                results.append(f"✗ {exchange}: missing {missing}")
                all_ok = False
            else:
                tc = all(isinstance(result[f], (str, int, float)) for f in required)
                td = result["price"] > 0 and result["qty"] > 0 and result["side"] in ["buy", "sell"]
                if tc and td:
                    results.append(f"✓ {exchange}: OK")
                else:
                    results.append(f"✗ {exchange}: type/business rule fail")
                    all_ok = False
        except Exception as e:
            results.append(f"✗ {exchange}: {e}")
            all_ok = False
    
    print("\n".join(results))
    return all_ok

def check_gateways():
    gateways_ok = True
    statuses = []
    for g in ['binance', 'bybit', 'okx']:
        f = os.path.join(PROJECT, f'layer1_market_data/gateways/{g}/connector.py')
        if os.path.exists(f):
            try:
                with open(f) as fh:
                    compile(fh.read(), f, 'exec')
                statuses.append(f"✓ {g}: syntax OK")
            except SyntaxError:
                statuses.append(f"✗ {g}: syntax error")
                gateways_ok = False
        else:
            statuses.append(f"✗ {g}: not found")
            gateways_ok = False
    print("\n".join(statuses))
    return gateways_ok

def check_storage():
    sd = os.path.join(PROJECT, 'layer1_market_data/storage')
    if os.path.exists(sd):
        print(f"✓ Storage dir exists: {sd}")
        return True
    os.makedirs(sd, exist_ok=True)
    print(f"✓ Storage dir created: {sd}")
    return True

def check_integrity():
    normalize_to_internal("binance", {"e": "24hrTicker", "s": "BTCUSDT", "c": "115000", "q": "1200", "E": 1234567890, "m": False})
    normalize_to_internal("bybit", {"symbol": "BTCUSDT", "price": "115000", "side": "Buy", "qty": "1.5", "timestamp": 1234567890})
    normalize_to_internal("okx", {"instId": "BTC-USDT", "px": "115000", "sz": "1.5", "side": "buy", "ts": 1234567890})
    
    # Key fields must be consistent (except qty which differs by design)
    b = normalize_to_internal("binance", {"e": "24hrTicker", "s": "BTCUSDT", "c": "115000", "q": "1200", "E": 1234567890, "m": False})
    y = normalize_to_internal("bybit", {"symbol": "BTCUSDT", "price": "115000", "side": "Buy", "qty": "1.5", "timestamp": 1234567890})
    o = normalize_to_internal("okx", {"instId": "BTC-USDT", "px": "115000", "sz": "1.5", "side": "buy", "ts": 1234567890})
    
    fields_ok = all([
        b["symbol"] == y["symbol"] == o["symbol"],  # BTCUSDT
        b["price"] == y["price"] == o["price"],    # 115000.0
        b["side"] == y["side"] == o["side"],        # buy
        abs(b["timestamp"] - y["timestamp"]) <= 1000,  # timestamps close
    ])
    
    # qty > 0 for all (design difference is OK)
    qty_ok = b["qty"] > 0 and y["qty"] > 0 and o["qty"] > 0
    
    if fields_ok and qty_ok:
        print("✓ Data integrity: ALL KEY FIELDS OK + qty > 0")
        return True
    else:
        print(f"✗ Data integrity fail: fields_ok={fields_ok}, qty_ok={qty_ok}")
        return False

def main():
    print("=" * 60)
    print("⚡ LAYER 1 HEALTH CHECK")
    print("=" * 60)
    
    n = check_normalizer()
    g = check_gateways()
    s = check_storage()
    i = check_integrity()
    
    print("\n" + "=" * 60)
    if n and g and s and i:
        print("🟢 OVERALL: HEALTHY")
        print("✅ BOLEH PROSEDING ke Layer 2+ dan position management")
        print("✅ Sistem minimum terpenuhi")
        result = "HEALTHY"
    else:
        print("🔴 OVERALL: UNHEALTHY")
        print("❌ PERBAIKI sebelum melangkah ke Layer 2+")
        result = "UNHEALTHY"
    
    print("=" * 60 + "\n")
    sys.exit(0 if result == "HEALTHY" else 1)

if __name__ == "__main__":
    main()
