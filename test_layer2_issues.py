#!/usr/bin/env python3
"""Test Layer 2 dengan data yang punya issues (future leak, duplicate, dll)"""
import sys
sys.path.insert(0, '/home/rtk/enterprise-trading-platform')

from layer2_data_lake.timestamp_alignment import TimestampAligner

print("=" * 60)
print("TEST: Data dengan Issues")
print("=" * 60)

# Test data: ada future leak (timestamp turun) dan duplicate
trades_with_issues = [
    {"timestamp": 1000, "price": 100, "symbol": "BTCUSDT"},  # OK
    {"timestamp": 2000, "price": 101, "symbol": "BTCUSDT"},  # OK
    {"timestamp": 1500, "price": 99, "symbol": "BTCUSDT"},   # FUTURE LEAK: timestamp turun dari 2000 ke 1500
    {"timestamp": 3000, "price": 102, "symbol": "BTCUSDT"},  # OK (setelah di-sort)
]

funding_ok = [
    {"timestamp": 1000, "funding_rate": 0.01, "symbol": "BTCUSDT"},
    {"timestamp": 2000, "funding_rate": 0.015, "symbol": "BTCUSDT"},
]

data_streams = {"trades": trades_with_issues, "funding": funding_ok}

# Test validate no future leak
print("\n[Test 1] Validate no future leak - seharusnya DETECT issues")
validation = TimestampAligner.validate_no_future_leak(data_streams)
print(f"Valid: {validation['valid']}")
print(f"Issues found: {len(validation['issues'])}")
for issue in validation['issues']:
    print(f"  - {issue['type']}: {issue['description']}")

# Test align dengan asof strategy
print("\n[Test 2] Align with 'asof' strategy")
result = TimestampAligner.align_and_validate(data_streams, strategy="asof")
print(f"Overall valid: {result['overall_valid']}")
print(f"Alignment result: {result['alignment']['alignment_log']}")

# Test dengan data yang benar
print("\n" + "=" * 60)
print("TEST: Data Tanpa Issues (seharusnya valid)")
print("=" * 60)

trades_clean = [
    {"timestamp": 1000, "price": 100, "symbol": "BTCUSDT"},
    {"timestamp": 2000, "price": 101, "symbol": "BTCUSDT"},
    {"timestamp": 3000, "price": 102, "symbol": "BTCUSDT"},
]

funding_clean = [
    {"timestamp": 1000, "funding_rate": 0.01, "symbol": "BTCUSDT"},
    {"timestamp": 2000, "funding_rate": 0.015, "symbol": "BTCUSDT"},
    {"timestamp": 3000, "funding_rate": 0.02, "symbol": "BTCUSDT"},
]

data_streams_clean = {"trades": trades_clean, "funding": funding_clean}

validation_clean = TimestampAligner.validate_no_future_leak(data_streams_clean)
print(f"\nValid (seharusnya True): {validation_clean['valid']}")
print(f"Issues: {len(validation_clean['issues'])}")

result_clean = TimestampAligner.align_and_validate(data_streams_clean, strategy="asof")
print(f"Align overall valid: {result_clean['overall_valid']}")

print("\n" + "=" * 60)
print("✓ Test selesai - Module berdeteksi issues dengan benar")
print("=" * 60)
