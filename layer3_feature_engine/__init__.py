"""
Layer 3 - Feature Engineering Engine
Di sinilah alpha mulai muncul.
Input: OHLCV, OI, Funding, Orderbook, Liquidation
Output: ATR, ADX, BB Width, VWAP Distance, OI Delta, Funding Delta, Liquidity Score, Volume Score

VERSIONING (sesuai rekomendasi review arsitektur):
- V1 (registry, calculators, indicators) = DEPRECATED (compatibility layer)
- V2 (engine_v2) = TRANSITION (masih ada, tapi bukan canonical)
- V3 (engine_v3, contracts, domains, normalization, validation, lineage) = CANONICAL

BOUNDARY (refactor penting):
- Layer 3 menghasilkan ATOMIC features + CONTEXT components
- Layer 3 TIDAK memutuskan regime final
- Layer 4 (layer4_context_engine) yang memutuskan regime
"""
# V3 - CANONICAL (sumber kebenaran utama)
from .engine_v3 import FeatureEngineV3

# V1 - DEPRECATED (compatibility, tidak dihapus)
from .registry.feature_registry import FeatureRegistry
from .calculators.base_calculator import BaseCalculator

__all__ = [
    'FeatureEngineV3',   # CANONICAL
    'FeatureRegistry',   # DEPRECATED
    'BaseCalculator',    # DEPRECATED
]
