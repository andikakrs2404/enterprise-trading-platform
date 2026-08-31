#!/usr/bin/env python3
"""
Layer 3 - Contracts: Feature Metadata
Metadata untuk setiap feature — WAJIB untuk enterprise Feature Registry.

Setiap feature punya metadata lengkap:
- name, domain, type, role (atomic/context)
- lookback, warmup (mencegah bug backtest)
- source (dari data apa)
- normalization, availability, version

Ini yang membuat sistem tahu:
- feature apa?
- berasal dari mana?
- berapa lookback?
- kapan tersedia?
- bagaimana normalisasinya?
- versinya berapa?
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .feature_types import FeatureType, FeatureRole, FeatureAvailability
import json


@dataclass
class FeatureMetadata:
    """Metadata lengkap sebuah feature."""
    name: str                                  # atr_ratio
    domain: str                                # volatility
    role: FeatureRole = FeatureRole.ATOMIC     # atomic (bukan regime decision)
    feature_type: FeatureType = FeatureType.CONTINUOUS
    lookback: int = 0                          # jumlah bar yang dibutuhkan
    warmup: int = 0                            # minimal bar sebelum VALID
    source: List[str] = field(default_factory=list)  # [high, low, close]
    normalization: str = "none"                # none / rolling_zscore / percentile
    availability: FeatureAvailability = FeatureAvailability.BAR_CLOSE
    version: str = "1.0.0"
    description: str = ""
    # Untuk lineage
    dependencies: List[str] = field(default_factory=list)  # feature dependencies
    
    def to_dict(self) -> Dict:
        """Serialisasi ke dict."""
        return {
            "name": self.name,
            "domain": self.domain,
            "role": self.role.value,
            "feature_type": self.feature_type.value,
            "lookback": self.lookback,
            "warmup": self.warmup,
            "source": self.source,
            "normalization": self.normalization,
            "availability": self.availability.value,
            "version": self.version,
            "description": self.description,
            "dependencies": self.dependencies,
        }
    
    def to_json(self) -> str:
        """Serialisasi ke JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# ============ FEATURE REGISTRY (metadata definition) ============

# ATOMIC FEATURES - observasi mentah, tidak ada interpretasi
ATOMIC_FEATURES: Dict[str, FeatureMetadata] = {
    # --- Price Structure ---
    "ret_1": FeatureMetadata("ret_1", "price_structure", lookback=1, warmup=1,
                             source=["close"], normalization="none",
                             description="1-bar return"),
    "ret_5": FeatureMetadata("ret_5", "price_structure", lookback=5, warmup=5,
                             source=["close"], normalization="none",
                             description="5-bar return"),
    "ret_24": FeatureMetadata("ret_24", "price_structure", lookback=24, warmup=24,
                              source=["close"], normalization="none",
                              description="24-bar return"),
    "range_pct": FeatureMetadata("range_pct", "price_structure", lookback=1, warmup=1,
                                 source=["high", "low", "close"], normalization="none",
                                 description="(high-low)/close"),
    "body_ratio": FeatureMetadata("body_ratio", "price_structure", lookback=1, warmup=1,
                                  source=["open", "high", "low", "close"], normalization="none",
                                  description="body/range conviction"),
    "hh_hl_structure": FeatureMetadata("hh_hl_structure", "price_structure", lookback=2, warmup=2,
                                       source=["high", "low"], normalization="none",
                                       description="higher-high/higher-low structure"),
    
    # --- Volatility ---
    "atr": FeatureMetadata("atr", "volatility", lookback=14, warmup=14,
                           source=["high", "low", "close"], normalization="none",
                           description="Average True Range 14"),
    "atr_ratio": FeatureMetadata("atr_ratio", "volatility", lookback=100, warmup=100,
                                 source=["atr_14", "atr_100"], normalization="rolling_zscore",
                                 description="ATR14/ATR100 relative volatility", 
                                 dependencies=["atr"]),
    "bb_width": FeatureMetadata("bb_width", "volatility", lookback=20, warmup=20,
                                source=["close"], normalization="percentile",
                                description="Bollinger band width"),
    "realized_vol": FeatureMetadata("realized_vol", "volatility", lookback=14, warmup=14,
                                    source=["close"], normalization="rolling_zscore",
                                    description="std of log returns"),
    
    # --- Volume ---
    "volume_ratio": FeatureMetadata("volume_ratio", "volume", lookback=20, warmup=20,
                                    source=["volume"], normalization="rolling_zscore",
                                    description="volume/volume_ma20"),
    "dollar_volume": FeatureMetadata("dollar_volume", "volume", lookback=1, warmup=1,
                                     source=["volume", "close"], normalization="none",
                                     description="volume*close"),
    "volume_percentile": FeatureMetadata("volume_percentile", "volume", lookback=500, warmup=20,
                                         source=["volume"], normalization="percentile",
                                         description="volume vs historical percentile"),
    
    # --- Participation ---
    "oi_delta": FeatureMetadata("oi_delta", "participation", lookback=1, warmup=1,
                                source=["open_interest"], normalization="rolling_zscore",
                                description="OI change"),
    "oi_pct": FeatureMetadata("oi_pct", "participation", lookback=1, warmup=1,
                              source=["open_interest"], normalization="rolling_zscore",
                              description="OI % change"),
    "funding": FeatureMetadata("funding", "participation", lookback=1, warmup=1,
                               source=["funding_rate"], normalization="rolling_zscore",
                               description="funding rate"),
    
    # --- Trend ---
    "ema_dist": FeatureMetadata("ema_dist", "trend", lookback=50, warmup=50,
                                source=["close", "ema50"], normalization="rolling_zscore",
                                description="(close-ema50)/ema50"),
    "ema_slope": FeatureMetadata("ema_slope", "trend", lookback=51, warmup=51,
                                 source=["ema50"], normalization="rolling_zscore",
                                 description="ema50 slope"),
    "adx": FeatureMetadata("adx", "trend", lookback=14, warmup=28,
                           source=["high", "low", "close"], normalization="none",
                           description="Average Directional Index"),
    "regression_slope": FeatureMetadata("regression_slope", "trend", lookback=20, warmup=20,
                                        source=["close"], normalization="rolling_zscore",
                                        description="lin reg slope"),
    
    # --- Liquidity (Microstructure - realtime only) ---
    "bid_ask_spread": FeatureMetadata("bid_ask_spread", "liquidity", 
                                      availability=FeatureAvailability.REALTIME_ORDERBOOK,
                                      lookback=1, warmup=1, source=["orderbook"], normalization="none",
                                      description="ask-bid"),
    "orderbook_imbalance": FeatureMetadata("orderbook_imbalance", "liquidity",
                                            availability=FeatureAvailability.REALTIME_ORDERBOOK,
                                            lookback=1, warmup=1, source=["orderbook"], normalization="none",
                                            description="bid_vol/ask_vol"),
}


# CONTEXT FEATURES - interpretasi dari atomic, bukan regime decision
# Role = CONTEXT, bukan REGIME (regime diputuskan Layer 4)
CONTEXT_FEATURES: Dict[str, FeatureMetadata] = {
    "compression_components": FeatureMetadata(
        "compression_components", "regime_context", role=FeatureRole.CONTEXT,
        lookback=100, warmup=100, source=["atr_ratio", "bb_width", "volume_ratio"],
        normalization="none",
        description="Komponen compression (volatility/range/volume/liquidity/positioning) - BUKAN regime final",
        dependencies=["atr_ratio", "bb_width", "volume_ratio", "volume_percentile"]),
    "trend_components": FeatureMetadata(
        "trend_components", "regime_context", role=FeatureRole.CONTEXT,
        lookback=50, warmup=50, source=["adx", "ema_slope", "hh_hl_structure"],
        normalization="none",
        description="Komponen trend (strength/direction) - BUKAN regime final",
        dependencies=["adx", "ema_slope", "hh_hl_structure"]),
    "expansion_components": FeatureMetadata(
        "expansion_components", "regime_context", role=FeatureRole.CONTEXT,
        lookback=100, warmup=100, source=["atr_ratio", "volume_ratio", "oi_pct"],
        normalization="none",
        description="Komponen expansion (vol/volume/oi spike) - BUKAN regime final",
        dependencies=["atr_ratio", "volume_ratio", "oi_pct"]),
}


def get_feature_metadata(name: str) -> Optional[FeatureMetadata]:
    """Dapatkan metadata feature berdasarkan nama."""
    if name in ATOMIC_FEATURES:
        return ATOMIC_FEATURES[name]
    if name in CONTEXT_FEATURES:
        return CONTEXT_FEATURES[name]
    return None


def export_registry_to_json() -> str:
    """Export seluruh registry ke JSON (untuk persisted config)."""
    all_features = {}
    for name, meta in {**ATOMIC_FEATURES, **CONTEXT_FEATURES}.items():
        all_features[name] = meta.to_dict()
    return json.dumps(all_features, indent=2)


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("FEATURE REGISTRY - Metadata Test")
    print("=" * 60)
    
    print(f"\nAtomic features: {len(ATOMIC_FEATURES)}")
    print(f"Context features: {len(CONTEXT_FEATURES)}")
    print(f"Total: {len(ATOMIC_FEATURES) + len(CONTEXT_FEATURES)}")
    
    print("\nContoh metadata atr_ratio:")
    print(ATOMIC_FEATURES["atr_ratio"].to_json())
    
    print("\nContoh context (komponen, bukan regime final):")
    print(CONTEXT_FEATURES["compression_components"].to_json())
    
    print("\n" + "=" * 60)
    print("✓ Feature Registry Metadata Operational")
    print("=" * 60)
