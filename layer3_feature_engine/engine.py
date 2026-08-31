#!/usr/bin/env python3
"""
Layer 3 - Feature Engineering Engine (Orchestrator)
Menghubungkan indicators, calculators, dan registry.
Menghitung fitur dari data pasar mentah dan menghasilkan output terstruktur.
"""
from typing import Dict, List, Any, Optional
import json

from .indicators.indicators import Indicators
from .registry.feature_registry import FeatureRegistry


class FeatureEngine:
    """
    Orchestrator utama Layer 3.
    Menerima data pasar (OHLCV, OI, Funding) dan menghasilkan
    fitur yang siap dipakai Layer 4 (Regime Classification).
    
    Output per bar:
    {
        "timestamp": ...,
        "atr": ...,
        "adx": ...,
        "bb_width": ...,
        "vwap_distance": ...,
        "oi_delta": ...,
        "funding_delta": ...,
        "volume_ratio": ...
    }
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.registry = FeatureRegistry()
        self._register_default_features()
    
    def _default_config(self) -> Dict:
        return {
            "atr_period": 14,
            "adx_period": 14,
            "bb_period": 20,
            "bb_std": 2.0,
            "vwap_period": 20,
            "volume_ratio_period": 20,
        }
    
    def _register_default_features(self):
        """Daftarkan fitur default ke registry."""
        cfg = self.config
        
        def make_atr_calc():
            p = cfg["atr_period"]
            def calc(data):
                return Indicators.atr(data["high"], data["low"], data["close"], period=p)
            return calc
        
        def make_adx_calc():
            p = cfg["adx_period"]
            def calc(data):
                return Indicators.adx(data["high"], data["low"], data["close"], period=p)
            return calc
        
        def make_bbw_calc():
            p = cfg["bb_period"]
            s = cfg["bb_std"]
            def calc(data):
                return Indicators.bb_width(data["close"], period=p, num_std=s)
            return calc
        
        def make_vwap_calc():
            p = cfg["vwap_period"]
            def calc(data):
                return Indicators.vwap_distance(data["close"], data.get("volume", [0]*len(data["close"])), period=p)
            return calc
        
        def make_oid_calc():
            def calc(data):
                return Indicators.oi_delta(data.get("open_interest", []))
            return calc
        
        def make_fd_calc():
            def calc(data):
                return Indicators.funding_delta(data.get("funding_rate", []))
            return calc
        
        def make_vr_calc():
            p = cfg["volume_ratio_period"]
            def calc(data):
                return Indicators.volume_ratio(data.get("volume", []), period=p)
            return calc
        
        self.registry.register("atr", make_atr_calc(), ["ohlc"], "atr", "Average True Range")
        self.registry.register("adx", make_adx_calc(), ["ohlc"], "adx", "Average Directional Index")
        self.registry.register("bb_width", make_bbw_calc(), ["ohlc"], "bb_width", "Bollinger Band Width")
        self.registry.register("vwap_distance", make_vwap_calc(), ["ohlc", "volume"], "vwap_distance", "VWAP Distance")
        self.registry.register("oi_delta", make_oid_calc(), ["open_interest"], "oi_delta", "OI Delta")
        self.registry.register("funding_delta", make_fd_calc(), ["funding_rate"], "funding_delta", "Funding Delta")
        self.registry.register("volume_ratio", make_vr_calc(), ["volume"], "volume_ratio", "Volume Ratio")
    
    def compute_features(self, market_data: Dict[str, List]) -> List[Dict[str, Any]]:
        """
        Hitung semua fitur dari data pasar.
        
        Args:
            market_data: Dict dengan lists: close, high, low, volume, 
                         open_interest, funding_rate
                         
        Returns:
            List dict fitur per timestamp
        """
        n = self._get_length(market_data)
        if n == 0:
            return []
        
        # Hitung semua fitur
        feature_values = {}
        for name in ["atr", "adx", "bb_width", "vwap_distance", 
                     "oi_delta", "funding_delta", "volume_ratio"]:
            try:
                feature_values[name] = self.registry.calculate(name, market_data)
            except Exception as e:
                feature_values[name] = [0.0] * n
        
        # Bangun output per bar
        timestamps = market_data.get("timestamp", list(range(n)))
        results = []
        for i in range(n):
            row = {
                "timestamp": timestamps[i],
            }
            for name, values in feature_values.items():
                row[name] = values[i] if i < len(values) else 0.0
            results.append(row)
        
        return results
    
    def _get_length(self, market_data: Dict[str, List]) -> int:
        """Dapatkan panjang data dari field yang ada."""
        for key in ["close", "high", "low", "volume", "open_interest", "funding_rate", "timestamp"]:
            if key in market_data and market_data[key]:
                return len(market_data[key])
        return 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Ringkasan state Feature Engine."""
        return {
            "registered_features": self.registry.list_features(),
            "total_features": self.registry.feature_count(),
            "config": self.config,
            "status": "operational"
        }


# Quick test
if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("FEATURE ENGINE TEST")
    print("=" * 60)
    
    # Generate market data
    random.seed(7)
    n = 100
    closes, highs, lows, volumes = [], [], [], []
    price = 50000.0
    for i in range(n):
        price += random.uniform(-300, 300)
        closes.append(price)
        highs.append(price + random.uniform(50, 200))
        lows.append(price - random.uniform(50, 200))
        volumes.append(random.uniform(100, 10000))
    
    oi = [5000000 + random.uniform(-10000, 10000) for _ in range(n)]
    funding = [0.0001 + random.uniform(-0.00005, 0.00005) for _ in range(n)]
    
    market_data = {
        "close": closes,
        "high": highs,
        "low": lows,
        "volume": volumes,
        "open_interest": oi,
        "funding_rate": funding,
        "timestamp": list(range(n)),
    }
    
    # Inisialisasi engine
    engine = FeatureEngine()
    print(f"Registered features: {engine.get_summary()['registered_features']}")
    
    # Hitung fitur
    features = engine.compute_features(market_data)
    print(f"\nTotal bars: {len(features)}")
    
    # Tampilkan beberapa bar terakhir
    print("\nLast 3 feature rows:")
    for row in features[-3:]:
        print(f"  ts={row['timestamp']}: atr={row['atr']:.2f}, adx={row['adx']:.1f}, "
              f"bbw={row['bb_width']:.4f}, vwapd={row['vwap_distance']:.5f}, "
              f"oid={row['oi_delta']:.0f}, fd={row['funding_delta']:.6f}, "
              f"vr={row['volume_ratio']:.3f}")
    
    print("\n" + "=" * 60)
    print("✓ Feature Engine Operational")
    print("=" * 60)
