#!/usr/bin/env python3
"""
Layer 3 - Feature Engine Orchestrator (V2 - 7 Domain Framework)
Menggabungkan semua 7 domain feature + Feature Store pipeline.
Ini adalah CTO-level orchestration: menjalankan semua engine dan 
menyimpan hasilnya dengan versioning.

Domain:
1. Price Structure
2. Volatility
3. Volume
4. Market Participation
5. Trend
6. Liquidity
7. Regime
"""
from typing import Dict, List, Any, Optional
import json
import os

from .domains.price_structure.features import PriceStructureFeatures
from .domains.volatility.features import VolatilityFeatures
from .domains.volume.features import VolumeFeatures
from .domains.participation.features import ParticipationFeatures
from .domains.trend.features import TrendFeatures
from .domains.liquidity.features import LiquidityFeatures
from .domains.regime.features import RegimeFeatures
from .store.feature_store import FeatureStore


class FeatureEngineV2:
    """
    Orchestrator utama Layer 3 (V2).
    Menjalankan semua 7 domain, mengkombinasikan hasilnya,
    dan menyimpan ke Feature Store.
    """
    
    def __init__(self, config_path: Optional[str] = None, storage_dir: Optional[str] = None):
        """
        Inisialisasi Feature Engine V2.
        
        Args:
            config_path: Path ke file config JSON
            storage_dir: Direktori untuk Feature Store
        """
        self.config = self._load_config(config_path)
        self.store = FeatureStore(storage_dir=storage_dir or self.config.get("storage_dir"))
        
        # Inisialisasi semua domain calculators
        self.price_structure = PriceStructureFeatures(self.config.get("parameters", {}))
        self.volatility = VolatilityFeatures(self.config.get("parameters", {}))
        self.volume = VolumeFeatures(self.config.get("parameters", {}))
        self.participation = ParticipationFeatures(self.config.get("parameters", {}))
        self.trend = TrendFeatures(self.config.get("parameters", {}))
        self.liquidity = LiquidityFeatures(self.config.get("parameters", {}))
        self.regime = RegimeFeatures(self.config.get("parameters", {}))
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load config dari file JSON."""
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        # Default config
        return {
            "parameters": {},
            "critical_features": ["atr", "atr_ratio", "bb_width", "volume_ratio", "compression_score"]
        }
    
    # --- FULL PIPELINE ---
    def process_symbol(self, symbol: str, ohlcv: List[Dict], 
                       open_interest: Optional[List] = None,
                       funding_rate: Optional[List] = None,
                       orderbooks: Optional[List] = None,
                       store_results: bool = True) -> Dict[str, Any]:
        """
        Proses LENGKAP satu symbol: hitung semua domain feature lalu simpan.
        
        Args:
            symbol: Symbol pasar
            ohlcv: List dict OHLCV (open, high, low, close, volume, timestamp)
            open_interest: List OI (align dengan ohlcv)
            funding_rate: List funding rate (align dengan ohlcv)
            orderbooks: List orderbook snapshots (optional)
            store_results: Simpan ke Feature Store?
            
        Returns:
            Dict: {rows, features_computed, stored, ...}
        """
        # --- Step 1: Hitung setiap domain ---
        price_features = self.price_structure.compute_all(ohlcv)
        vol_features = self.volatility.compute_all(ohlcv)
        volu_features = self.volume.compute_all(ohlcv)
        
        # Participation butuh data khusus
        part_data = {
            "close": [d["close"] for d in ohlcv],
            "open_interest": open_interest or [],
            "funding_rate": funding_rate or [],
            "timestamp": [d.get("timestamp", i) for i, d in enumerate(ohlcv)],
        }
        part_features = self.participation.compute_all(part_data)
        
        # Trend
        trend_features = self.trend.compute_all(
            [d["close"] for d in ohlcv],
            [d["high"] for d in ohlcv],
            [d["low"] for d in ohlcv],
            [d.get("timestamp", i) for i, d in enumerate(ohlcv)]
        )
        
        # Liquidity (jika orderbook tersedia)
        liq_features = []
        if orderbooks:
            liq_features = self.liquidity.compute_series(orderbooks)
        
        # --- Step 2: Gabungkan semua domain features per bar ---
        combined = self._merge_features(
            price_features, vol_features, volu_features, 
            part_features, trend_features, liq_features, ohlcv=ohlcv
        )
        
        # --- Step 3: Hitung regime scores dari gabungan ---
        regime_features = self.regime.compute_scores(combined)
        
        # --- Step 4: Merge regime scores ke combined ---
        final_rows = []
        for i, row in enumerate(combined):
            reg = regime_features[i] if i < len(regime_features) else {}
            merged_row = {**row, **reg}
            merged_row["symbol"] = symbol
            final_rows.append(merged_row)
        
        # --- Step 5: Simpan ke Feature Store ---
        store_info = {"stored": False}
        if store_results:
            store_info = self.store.save_features(symbol, final_rows, source="feature_engine_v2")
        
        # --- Step 6: Validasi ---
        validation = self.store.validate_features(
            final_rows, required_features=self.config.get("critical_features", [])
        )
        
        return {
            "rows": final_rows,
            "total_rows": len(final_rows),
            "features_computed": self._feature_names(final_rows),
            "store_info": store_info,
            "validation": validation,
            "symbol": symbol,
        }
    
    def _feature_names(self, rows: List[Dict]) -> List[str]:
        """Dapatkan nama-nama feature dari rows."""
        if not rows:
            return []
        return sorted(k for k in rows[0] if k not in 
            ["timestamp", "symbol", "saved_at", "source", "quality_score",
             "schema_version", "dataset_version"])
    
    def _merge_features(self, *feature_lists, ohlcv) -> List[Dict]:
        """
        Gabungkan beberapa list feature per domain menjadi satu list per bar.
        """
        n = len(ohlcv)
        merged = []
        for i in range(n):
            row = {
                "timestamp": ohlcv[i].get("timestamp", i),
                "symbol": ohlcv[i].get("symbol", "UNKNOWN"),
            }
            for feature_list in feature_lists:
                if i < len(feature_list):
                    for k, v in feature_list[i].items():
                        if k not in ["timestamp", "symbol"]:
                            row[k] = v
            merged.append(row)
        return merged
    
    def get_summary(self) -> Dict[str, Any]:
        """Ringkasan state engine."""
        return {
            "status": "operational",
            "domains_enabled": ["price_structure", "volatility", "volume", 
                                "participation", "trend", "liquidity", "regime"],
            "feature_store": {
                "schema_version": self.store.SCHEMA_VERSION,
                "dataset_version": self.store.dataset_version,
                "storage_dir": self.store.storage_dir,
            },
        }


# Quick test
if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("FEATURE ENGINE V2 - FULL 7-DOMAIN TEST")
    print("=" * 60)
    
    # Generate sample OHLCV
    random.seed(9)
    n = 80
    ohlcv = []
    price = 100.0
    for i in range(n):
        open_ = price
        # Compression di akhir (seperti yang dicari)
        vol_scale = 1.0 if i < 55 else 0.25
        close = price + random.uniform(-1, 1) * vol_scale
        high = max(open_, close) + random.uniform(0, 0.7) * vol_scale
        low = min(open_, close) - random.uniform(0, 0.7) * vol_scale
        vol = random.uniform(2000, 5000) * (0.3 if i > 55 else 1.0)
        ohlcv.append({"open": open_, "high": high, "low": low, "close": close,
                      "volume": vol, "timestamp": i, "symbol": "BTCUSDT"})
        price = close
    
    open_interest = [100000 + random.uniform(-100, 100) for _ in range(n)]
    funding_rate = [0.0001 + random.uniform(-0.00002, 0.00002) for _ in range(n)]
    
    # Inisialisasi engine
    engine = FeatureEngineV2()
    
    # Proses lengkap
    result = engine.process_symbol("BTCUSDT", ohlcv, open_interest, funding_rate)
    
    print(f"\nTotal rows: {result['total_rows']}")
    print(f"Features computed ({len(result['features_computed'])}): {result['features_computed']}")
    print(f"Validation: valid={result['validation']['is_valid']}")
    
    # Tampilkan compression → expansion detection
    print("\nRegime detection (terakhir 8 bar):")
    for row in result['rows'][-8:]:
        print(f"  ts={row['timestamp']}: comp={row.get('compression_score',0):.2f}, "
              f"exp={row.get('expansion_score',0):.2f}, "
              f"atr_ratio={row.get('atr_ratio',0):.2f}, "
              f"regime={row.get('regime','?')}")
    
    print("\n" + "=" * 60)
    print("✓ FEATURE ENGINE V2 OPERATIONAL - 7 Domain + Feature Store")
    print("=" * 60)
