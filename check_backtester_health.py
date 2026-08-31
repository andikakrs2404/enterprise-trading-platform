#!/usr/bin/env python3
"""
Backtester - Health Check
Memverifikasi seluruh komponen reproducible backtest.
"""
import sys
import os

PROJECT = '/home/rtk/enterprise-trading-platform'
sys.path.insert(0, PROJECT)

print("=" * 60)
print("⚡ BACKTESTER HEALTH CHECK")
print("=" * 60)

passed = True
results = []

# 1. Contracts
try:
    from backtester.contracts.feature_source_contract import FeatureSourceContract, BacktestContract
    results.append(("Contracts", True, "FeatureSource + Backtest contract OK"))
except Exception as e:
    results.append(("Contracts", False, str(e)))
    passed = False

# 2. Backtester consumption (tidak hitung feature sendiri)
try:
    from backtester.engine.feature_backtester import FeatureBacktester
    # Verifikasi tidak ada indikator in-house
    from backtester.contracts.feature_source_contract import FeatureSourceContract
    contract = FeatureSourceContract()
    ok = contract.assert_no_indicator_computation(
        os.path.join(PROJECT, "backtester", "engine", "feature_backtester.py"))
    results.append(("No self-computation", ok, 
                    "Backtester TIDAK menghitung indikator sendiri" if ok else "MELANGGAR kontrak"))
    if not ok:
        passed = False
except Exception as e:
    results.append(("No self-computation", False, str(e)))
    passed = False

# 3. Parity (backtest == live)
try:
    from backtester.parity.parity_test import ParityTest
    import random
    random.seed(1)
    ohlcv = []
    price = 100.0
    for i in range(100):
        o = price; c = price + random.uniform(-0.5, 0.5)
        ohlcv.append({"open": o, "high": max(o,c)+0.3, "low": min(o,c)-0.3,
                      "close": c, "volume": 2000, "timestamp": i})
        price = c
    oi = [100000]*100
    parity = ParityTest()
    result = parity.run_parity(ohlcv, oi)
    results.append(("Parity (backtest==live)", result["all_exact"],
                    "Feature identik di kedua jalur" if result["all_exact"] else "MISMATCH"))
    if not result["all_exact"]:
        passed = False
except Exception as e:
    results.append(("Parity (backtest==live)", False, str(e)))
    passed = False

# 4. Regression baseline
try:
    from backtester.regression.regression_test import RegressionTest
    rt = RegressionTest()
    # Baseline harus sudah ada dari run sebelumnya
    has_baseline = "compression_v1" in rt.baselines
    results.append(("Regression baseline", has_baseline,
                    "Baseline compression_v1 tersimpan" if has_baseline else "Belum ada baseline"))
except Exception as e:
    results.append(("Regression baseline", False, str(e)))
    passed = False

# 5. Summary file ada
try:
    import json
    summary_path = os.path.join(PROJECT, "backtester", "last_backtest_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            summary = json.load(f)
        results.append(("Last backtest summary", True,
                        f"PF={summary['pf']}, trades={summary['n_trades']}"))
    else:
        results.append(("Last backtest summary", False, "File summary belum ada"))
        passed = False
except Exception as e:
    results.append(("Last backtest summary", False, str(e)))
    passed = False

print("\n" + "-" * 60)
for name, ok, msg in results:
    status = "✅" if ok else "❌"
    print(f"{status} {name}: {msg}")
    if not ok:
        passed = False

print("\n" + "=" * 60)
print("🟢 BACKTESTER HEALTHY" if passed else "🔴 BACKTESTER UNHEALTHY")
print("=" * 60 + "\n")
sys.exit(0 if passed else 1)
