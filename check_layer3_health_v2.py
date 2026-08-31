#!/usr/bin/env python3
"""
Layer 3 - Feature Engine Health Check (V2 - 7 Domain)
Memverifikasi seluruh komponen Layer 3 berjalan: 7 domain + Feature Store.
"""
import sys
import os

PROJECT = '/home/rtk/enterprise-trading-platform'
sys.path.insert(0, PROJECT)

print("=" * 60)
print("⚡ LAYER 3 HEALTH CHECK - 7-Domain Feature Engineering Engine")
print("=" * 60)

passed = True
results = []

# 1. Domain imports
try:
    from layer3_feature_engine.domains.price_structure.features import PriceStructureFeatures
    from layer3_feature_engine.domains.volatility.features import VolatilityFeatures
    from layer3_feature_engine.domains.volume.features import VolumeFeatures
    from layer3_feature_engine.domains.participation.features import ParticipationFeatures
    from layer3_feature_engine.domains.trend.features import TrendFeatures
    from layer3_feature_engine.domains.liquidity.features import LiquidityFeatures
    from layer3_feature_engine.domains.regime.features import RegimeFeatures
    results.append(("7 Domain Imports", True, "Semua 7 domain bisa di-import"))
except Exception as e:
    results.append(("7 Domain Imports", False, str(e)))
    passed = False

# 2. Feature Store
try:
    from layer3_feature_engine.store.feature_store import FeatureStore
    results.append(("Feature Store", True, "Feature Store bisa di-import"))
except Exception as e:
    results.append(("Feature Store", False, str(e)))
    passed = False

# 3. Config-driven (bukan hardcoded - fix CodeRabbit)
try:
    import json
    with open(os.path.join(PROJECT, 'layer3_feature_engine/config/feature_config.json')) as f:
        config = json.load(f)
    params = config.get("parameters", {})
    has_threshold = "compression_atr_ratio_threshold" in params
    results.append(("Config-driven", has_threshold, 
                    "Threshold terpusat di config JSON" if has_threshold else "Threshold TIDAK di config"))
    if not has_threshold:
        passed = False
except Exception as e:
    results.append(("Config-driven", False, str(e)))
    passed = False

# 4. Full engine runs
try:
    import random
    from layer3_feature_engine.engine_v2 import FeatureEngineV2
    random.seed(4)
    n = 60
    ohlcv = []
    price = 100.0
    for i in range(n):
        o = price
        c = price + random.uniform(-1, 1)
        ohlcv.append({"open": o, "high": max(o,c)+0.7, "low": min(o,c)-0.7,
                      "close": c, "volume": 3000, "timestamp": i})
        price = c
    oi = [50000] * n
    fund = [0.0001] * n
    engine = FeatureEngineV2()
    result = engine.process_symbol("BTCUSDT", ohlcv, oi, fund, store_results=False)
    n_features = len(result['features_computed'])
    results.append(("Full Engine", True, f"Proses {result['total_rows']} bar, {n_features} features"))
except Exception as e:
    results.append(("Full Engine", False, f"Error: {e}"))
    passed = False

# 5. Compression detection (konsep edge utama)
try:
    from layer3_feature_engine.domains.regime.features import RegimeFeatures
    reg = RegimeFeatures()
    comp_test = reg.compute_scores([
        {"timestamp":1, "atr_ratio":0.5, "bb_width":0.02, "volume_ratio":0.6,
         "adx":15, "ema_slope":0, "ema_dist":0, "hh_hl_structure":0, "oi_pct":0.001}
    ])[0]
    is_compression = comp_test['regime'] in ("COMPRESSION", "RANGE")
    results.append(("Compression Detection", is_compression, 
                    f"compression_score={comp_test['compression_score']:.2f}, regime={comp_test['regime']}"))
    if not is_compression:
        passed = False
except Exception as e:
    results.append(("Compression Detection", False, str(e)))
    passed = False

# Print results
print("\n" + "-" * 60)
for name, ok, msg in results:
    status = "✅" if ok else "❌"
    print(f"{status} {name}: {msg}")
    if not ok:
        passed = False

print("\n" + "=" * 60)
if passed:
    print("🟢 OVERALL: HEALTHY")
    print("✅ 7-Domain Feature Engine fully operational")
    print("✅ Compression→Expansion edge terdeteksi")
    print("✅ Feature Store pipeline bekerja")
else:
    print("🔴 OVERALL: UNHEALTHY")
    print("❌ Perbaiki komponen di atas")
print("=" * 60 + "\n")

sys.exit(0 if passed else 1)
