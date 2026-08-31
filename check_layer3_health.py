#!/usr/bin/env python3
"""
Layer 3 - Feature Engine Health Check
Memverifikasi seluruh komponen Layer 3 berjalan dengan benar.
"""
import sys
import os

# Set paths
PROJECT = '/home/rtk/enterprise-trading-platform'
sys.path.insert(0, PROJECT)

print("=" * 60)
print("⚡ LAYER 3 HEALTH CHECK - Feature Engineering Engine")
print("=" * 60)

passed = True
checks = []

# 1. Import considerations
try:
    from layer3_feature_engine.engine import FeatureEngine
    from layer3_feature_engine.registry.feature_registry import FeatureRegistry
    from layer3_feature_engine.calculators.base_calculator import BaseCalculator
    from layer3_feature_engine.indicators.indicators import Indicators
    checks.append(("Imports", True, "Semua modul Layer 3 bisa di-import"))
except Exception as e:
    checks.append(("Imports", False, f"Import error: {e}"))
    passed = False

# 2. Indicators working
try:
    highs = [100, 102, 101, 104, 103]
    lows = [98, 99, 100, 101, 100]
    closes = [99, 101, 100, 103, 102]
    atr = Indicators.atr(highs, lows, closes)
    adx = Indicators.adx(highs, lows, closes)
    checks.append(("Indicators", True, f"ATR & ADX berfungsi (ATR last={atr[-1]:.2f}, ADX last={adx[-1]:.2f})"))
except Exception as e:
    checks.append(("Indicators", False, f"Indicator error: {e}"))
    passed = False

# 3. Registry working
try:
    reg = FeatureRegistry()
    reg.register("test_feature", lambda d: 42, ["d"], "test", "Test feature")
    has = reg.has("test_feature")
    count = reg.feature_count()
    checks.append(("Registry", True, f"Registry berfungsi (features={count}, has_test={has})"))
except Exception as e:
    checks.append(("Registry", False, f"Registry error: {e}"))
    passed = False

# 4. Feature Engine working
try:
    import random
    n = 50
    closes_data = []
    price = 100.0
    for i in range(n):
        price += random.uniform(-1, 1)
        closes_data.append(price)
    market_data = {
        "close": closes_data,
        "high": [c + 1 for c in closes_data],
        "low": [c - 1 for c in closes_data],
        "volume": [1000] * n,
        "open_interest": [50000] * n,
        "funding_rate": [0.0001] * n,
        "timestamp": list(range(n)),
    }
    engine = FeatureEngine()
    features = engine.compute_features(market_data)
    checks.append(("FeatureEngine", True, 
                   f"Engine berfungsi ({len(features)} bars, {engine.get_summary()['total_features']} features)"))
except Exception as e:
    checks.append(("FeatureEngine", False, f"Engine error: {e}"))
    passed = False

# 5. Config file exists
try:
    config_ok = os.path.exists(os.path.join(PROJECT, '.coderabbit/config.yaml'))
    checks.append(("CodeRabbit Config", config_ok, 
                   "Config CodeRabbit ada" if config_ok else "Config CodeRabbit TIDAK ada"))
    if not config_ok:
        passed = False
except Exception as e:
    passed = False

# Print results
print("\n" + "-" * 60)
for name, ok, msg in checks:
    status = "✅" if ok else "❌"
    print(f"{status} {name}: {msg}")
    if not ok:
        passed = False

print("\n" + "=" * 60)
if passed:
    print("🟢 OVERALL: HEALTHY")
    print("✅ Layer 3 Feature Engine siap dan beroperasi")
    print("✅ CodeRabbit config terpasang")
else:
    print("🔴 OVERALL: UNHEALTHY")
    print("❌ Perbaiki komponen di atas")
print("=" * 60 + "\n")

sys.exit(0 if passed else 1)
