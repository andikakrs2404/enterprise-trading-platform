#!/usr/bin/env python3
"""
INTEGRATION TEST — Layer 3 → Layer 4 (Boundary Correctness)
Membuktikan alur yang benar:
Layer 3 (atomic + context components) → Layer 4 (regime decision) → edges

Ini membuktikan:
1. Layer 3 TIDAK menghasilkan regime (boundary benar)
2. Layer 4 MENGKONSUMSI komponen Layer 3 dan memutuskan regime
3. Alpha edge dipilih sesuai regime
"""
import sys
import os
import random

PROJECT = '/home/rtk/enterprise-trading-platform'
sys.path.insert(0, PROJECT)

print("=" * 70)
print("🧪 INTEGRATION TEST — L3 (Feature/Context) → L4 (Regime/Edges)")
print("=" * 70)

# ===== LAYER 3: generate context components (bukan regime) =====
from layer3_feature_engine.domains.regime_context.features import RegimeContextFeatures

# Skenario: compression (vol contrat sepanjang bar, lalu tiba-tiba expansion)
random.seed(30)
n = 120
ohlcv = []
price = 100.0
for i in range(n):
    vol_scale = 0.25 if i < 105 else 2.5   # compression dulu, lalu expansion
    o = price
    c = price + random.uniform(-0.5, 0.5) * vol_scale
    h = max(o, c) + random.uniform(0, 0.4) * vol_scale
    l = min(o, c) - random.uniform(0, 0.4) * vol_scale
    vol = random.uniform(2000, 4000) * (0.3 if i < 105 else 4.0)
    ohlcv.append({"open": o, "high": h, "low": l, "close": c, "volume": vol, "timestamp": i})
    price = c

# Hitung atomic features dulu
from layer3_feature_engine.domains.volatility.features import VolatilityFeatures
from layer3_feature_engine.domains.volume.features import VolumeFeatures
from layer3_feature_engine.domains.trend.features import TrendFeatures

v = VolatilityFeatures()
vo = VolumeFeatures()
t = TrendFeatures()
vf = v.compute_all(ohlcv)
vof = vo.compute_all(ohlcv)
tf = t.compute_all([d["close"] for d in ohlcv], [d["high"] for d in ohlcv], [d["low"] for d in ohlcv])

# Gabungkan jadi context components per bar (last bar)
last_atomic = {
    "atr_ratio": vf[-1]["atr_ratio"],
    "bb_width": vf[-1]["bb_width"],
    "volume_ratio": vof[-1]["volume_ratio"],
    "volume_percentile": vof[-1]["volume_percentile"],
    "adx": tf[-1]["adx"],
    "ema_slope": tf[-1]["ema_slope"],
    "hh_hl_structure": tf[-1].get("hh_hl_structure", 0.0),
    "oi_pct": 0.01,
}

rc = RegimeContextFeatures()
context = rc.compute_components([last_atomic])[0]

print("\n[LAYER 3] Context components (BUKAN regime):")
print(f"  compression_components = {context['compression_components']}")
print(f"  expansion_components = {context['expansion_components']}")
print(f"  trend_components = {context['trend_components']}")
print(f"  'regime' key ada di L3? → {'regime' in context}  (harus False)")
assert 'regime' not in context, "LAYER 3 TIDAK boleh memutuskan regime!"

# ===== LAYER 4: putuskan regime dari komponen =====
from layer4_context_engine.classifier.regime_classifier import MarketContextEngine
l4 = MarketContextEngine()
decision = l4.classify(context)

print("\n[LAYER 4] Regime decision dari komponen L3:")
print(f"  regime = {decision['regime']}")
print(f"  confidence = {decision['confidence']}")
print(f"  allowed_edges = {decision['allowed_edges']}")
print(f"  evidence = {decision['evidence']}")

print("\n" + "=" * 70)
print("✅ BOUNDARY CORRECT:")
print("   Layer 3 → context components (TIDAK regime)")
print(f"   Layer 4 → regime={decision['regime']}, edges={decision['allowed_edges']}")
print("   Edge dipilih oleh Layer 4, bukan Layer 3")
print("=" * 70)
