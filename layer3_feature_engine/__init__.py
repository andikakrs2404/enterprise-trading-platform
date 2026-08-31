"""
Layer 3 - Feature Engineering Engine
Di sinilah alpha mulai muncul.
Input: OHLCV, OI, Funding, Orderbook, Liquidation
Output: ATR, ADX, BB Width, VWAP Distance, OI Delta, Funding Delta, Liquidity Score, Volume Score
"""
from .registry.feature_registry import FeatureRegistry
from .calculators.base_calculator import BaseCalculator

__all__ = [
    'FeatureRegistry',
    'BaseCalculator',
]

print("[LAYER 3] Feature Engineering Engine initialized")
