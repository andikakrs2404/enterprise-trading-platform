#!/usr/bin/env python3
"""
Layer 5 - Alpha Engine Health Check
Memverifikasi seluruh kontrak L5 sesuai requirement user.
"""
import sys
import os

PROJECT = '/home/rtk/enterprise-trading-platform'
sys.path.insert(0, PROJECT)

print("=" * 65)
print("⚡ LAYER 5 - ALPHA ENGINE HEALTH CHECK")
print("=" * 65)

results = []
passed = True

def check(name, ok, msg):
    global passed
    results.append((name, ok, msg))
    if not ok:
        passed = False

# 1. Alpha Contract (interface seragam)
try:
    from layer5_alpha_engine.contracts.alpha_signal import AlphaSignal, AlphaDirection, AlphaState
    from layer5_alpha_engine.contracts.alpha_engine import AlphaEngine
    from layer5_alpha_engine.contracts.alpha_state import AlphaStateMachine
    from layer5_alpha_engine.contracts.evidence import AlphaEvidence
    
    # AlphaSignal bukan order (tidak ada qty/leverage/sl)
    s = AlphaSignal.triggered(alpha="test", symbol="BTCUSDT", timeframe="5m",
                              direction=AlphaDirection.LONG, score=0.8, confidence=0.8,
                              evidence={"c": 0.8})
    d = s.to_dict()
    forbidden_order_fields = ["qty", "leverage", "stop_loss", "take_profit", "order_type", "price", "size"]
    leaks = [f for f in forbidden_order_fields if f in d]
    check("AlphaSignal = alpha (bukan order)", not leaks,
          f"Tanpa field order {leaks}" if leaks else "Output alpha, bukan order ✅")
    
    # AlphaEngine abstract interface
    import abc
    check("AlphaEngine abstract", AlphaEngine.__abstractmethods__ == {"evaluate"},
          "Interface evaluate(features, context, market_state) wajib")
except Exception as e:
    check("Alpha Contract", False, str(e))

# 2. Alpha State Machine (lifecycle)
try:
    from layer5_alpha_engine.contracts.alpha_signal import AlphaState
    all_states = [s.value for s in AlphaState]
    required = ["OBSERVING", "SETUP", "QUALIFIED", "TRIGGERED", "ACTIVE", "INVALIDATED", "EXPIRED"]
    missing = [r for r in required if r not in all_states]
    check("Alpha State Machine", not missing,
          f"Lifecycle lengkap: {required} ✅" if not missing else f"Missing {missing}")
except Exception as e:
    check("Alpha State Machine", False, str(e))

# 3. Alpha Registry
try:
    from layer5_alpha_engine.registry import AlphaRegistry
    reg = AlphaRegistry()
    entries = reg.list_alphas()
    check("Alpha Registry", len(entries) >= 1,
          f"{len(entries)} alpha terdaftar (compression_breakout_v1)")
except Exception as e:
    check("Alpha Registry", False, str(e))

# 4. Compression Breakout V1 — Edge #1
try:
    from layer5_alpha_engine.engines.compression_breakout.v1 import CompressionBreakoutV1
    alpha = CompressionBreakoutV1()
    
    # a. Kontrak: tidak hitung indikator
    ok_no_indicator = alpha.check_not_computing_indicator()
    check("Edge#1 tidak hitung indikator", ok_no_indicator,
          "Hanya konsumsi features "+("✅" if ok_no_indicator else "❌"))
    
    # b. Setup saja (belum trigger) → QUALIFIED, not tradeable
    f_setup = {"atr_ratio": 0.5, "bb_width": 0.02, "volume_ratio": 0.6,
               "volume_percentile": 0.08, "oi_delta": 0.2}
    ctx_setup = {"compression_components": {
        "volatility_compression": 0.9, "range_compression": 0.85,
        "volume_compression": 0.8}, "volatility_state": "LOW"}
    mkt = {"symbol": "BTCUSDT", "timeframe": "5m", "close": 100.0,
           "high": 100.3, "low": 99.7, "prev_high": 100.3, "prev_low": 99.7, "bar_idx": 0}
    # Reset FSM
    alpha.fsm = None
    sig1 = alpha.evaluate(f_setup, ctx_setup, mkt)
    check("Setup terpisah dari Trigger",
          sig1.state.value == "QUALIFIED" and not sig1.is_tradeable(),
          f"compression setup → {sig1.state.value}, tradeable={sig1.is_tradeable()} ✅" if
          (sig1.state.value == "QUALIFIED" and not sig1.is_tradeable()) else "❌ setup langsung trigger")
    
    # c. Setup + Trigger → TRIGGERED tradeable
    alpha.fsm = None
    sig1 = alpha.evaluate(f_setup, ctx_setup, mkt)  # setup dulu
    f_trig = {"atr_ratio": 0.5, "bb_width": 0.02, "volume_ratio": 4.0,
              "volume_percentile": 0.95, "oi_delta": 80.0}
    mkt_trig = {"symbol": "BTCUSDT", "timeframe": "5m", "close": 105.0,
                "high": 104.0, "low": 100.0, "prev_high": 101.0, "prev_low": 99.0, "bar_idx": 10}
    sig2 = alpha.evaluate(f_trig, ctx_setup, mkt_trig)
    check("Setup→Trigger→Signal",
          sig2.is_tradeable() and sig2.direction.value == "LONG",
          f"breakout → {sig2.state.value} {sig2.direction.value}, score={sig2.score} ✅" if
          (sig2.is_tradeable()) else f"❌ state={sig2.state.value}")
    
    # d. Evidence transparan (bukan black-box)
    has_evidence = "compression" in sig2.evidence and "price_breakout" in sig2.evidence
    check("Evidence transparan", has_evidence,
          f"Komponen: {list(sig2.evidence.keys())}")
    
    # e. Alpha quality (bukan position size)
    has_quality = sig2.expected_horizon != "" and sig2.expected_return != 0
    check("Alpha quality (horizon, bukan size)", has_quality,
          f"expected_horizon={sig2.expected_horizon}, expected_return={sig2.expected_return}")
except Exception as e:
    check("Compression Breakout V1", False, str(e))

# 5. Backtester integration (inkremental)
try:
    import random
    from layer5_alpha_engine.engine import AlphaBacktestRunner
    # Data konstruksi deterministik: compression (range kecil) → breakout naik + volume
    # Ini memastikan alpha menghasilkan LONG trigger (membuktikan integrasi, bukan optimasi PF)
    n_comp, n_break = 60, 40
    ohlcv = []
    price = 100.0
    for i in range(n_comp):
        c = price + 0.01
        ohlcv.append({"open": price, "high": max(price, c)+0.02, "low": min(price, c)-0.02,
                      "close": c, "volume": 800, "timestamp": i})
        price = c
    for i in range(n_break):
        c = price + 0.8
        ohlcv.append({"open": price, "high": max(price, c)+0.5, "low": min(price, c)-0.1,
                      "close": c, "volume": 8000, "timestamp": n_comp+i})
        price = c
    oi = [100000+i*100 for i in range(n_comp+n_break)]
    runner = AlphaBacktestRunner(alpha)
    result = runner.run_backtest(ohlcv, oi)
    check("Backtester integration (L5)", result["metrics"]["num_trades"] > 0,
          f"{result['metrics']['num_trades']} trades via AlphaSignal ✅" if
          result["metrics"]["num_trades"] > 0 else "0 trades (data sintetis)")
except Exception as e:
    check("Backtester integration (L5)", False, str(e))

# ===== OUTPUT =====
print("\n" + "-" * 65)
for name, ok, msg in results:
    print(f"{'✅' if ok else '❌'} {name}: {msg}")
    if not ok:
        passed = False

print("\n" + "=" * 65)
print("🟢 L5 ALPHA ENGINE HEALTHY" if passed else "🔴 L5 ALPHA ENGINE UNHEALTHY")
print("=" * 65 + "\n")
sys.exit(0 if passed else 1)
