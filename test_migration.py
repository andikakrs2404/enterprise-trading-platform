#!/usr/bin/env python3
"""
MIGRATION TEST — V1 → V2 → V3
Memastikan deprecation bersih:
- V1 = deprecated (masih import, compatibility)
- V2 = transition (masih ada)
- V3 = canonical (sumber kebenaran)

Uji: V3 accessible, V1 masih import, tidak ada breakage.
"""
import sys, os
sys.path.insert(0, '/home/rtk/enterprise-trading-platform')

print("=" * 60)
print("MIGRATION TEST — V1 deprecated, V2 transition, V3 canonical")
print("=" * 60)

passed = True

# V1 - deprecated tapi masih ada
try:
    from layer3_feature_engine.registry.feature_registry import FeatureRegistry
    from layer3_feature_engine.calculators.base_calculator import BaseCalculator
    print("✅ V1 (deprecated): FeatureRegistry + BaseCalculator masih importable")
except Exception as e:
    print(f"❌ V1 import failed: {e}")
    passed = False

# V2 - transition tetap ada
try:
    from layer3_feature_engine.engine_v2 import FeatureEngineV2
    print("✅ V2 (transition): FeatureEngineV2 masih ada")
except Exception as e:
    print(f"❌ V2 import failed: {e}")
    passed = False

# V3 - canonical
try:
    from layer3_feature_engine.engine_v3 import FeatureEngineV3
    from layer3_feature_engine.contracts import ATOMIC_FEATURES, CONTEXT_FEATURES
    print("✅ V3 (CANONICAL): FeatureEngineV3 + contracts importable")
    print(f"   Atomic={len(ATOMIC_FEATURES)}, Context={len(CONTEXT_FEATURES)}")
except Exception as e:
    print(f"❌ V3 import failed: {e}")
    passed = False

# Root __init__ menunjuk V3 sebagai canonical
try:
    from layer3_feature_engine import FeatureEngineV3 as RootV3
    print("✅ Root __init__ mengekspor FeatureEngineV3 (canonical)")
except Exception as e:
    print(f"❌ Root export failed: {e}")
    passed = False

print("\n" + "=" * 60)
print("🟢 MIGRATION CLEAN" if passed else "🔴 MIGRATION ISSUE")
print("=" * 60)
sys.exit(0 if passed else 1)
