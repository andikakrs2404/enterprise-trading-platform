#!/usr/bin/env python3
"""
Layer 3 - Feature Engine V3 (CANONICAL)
Ini adalah refactor boundary: Feature → Context → Alpha → Signal

PERUBAHAN KONSEP PENTING (dari review arsitektur):
- Layer 3 HANYA menghasilkan ATOMIC features & CONTEXT components.
- Layer 3 TIDAK memutuskan regime final. Itu Layer 4.
- Semua feature punya metadata/warmup/normalization.
- Context components disimpan individual (untuk multi-edge).
- Versioning lengkap (feature/schema/code/config lineage).
- Multi-timeframe support.

V1 = deprecated, V2 = transition, V3 = CANONICAL.
"""
from typing import Dict, List, Any, Optional
import json
import os

from .contracts.feature_schema import FeatureSchema, CURRENT_SCHEMA
from .domains.price_structure.features import PriceStructureFeatures
from .domains.volatility.features import VolatilityFeatures
from .domains.volume.features import VolumeFeatures
from .domains.participation.features import ParticipationFeatures
from .domains.trend.features import TrendFeatures
from .domains.regime_context.features import RegimeContextFeatures
from .domains.cross_asset.features import CrossAssetFeatures
from .normalization.normalizers import RollingZScore, RollingPercentile, CrossSectionalPercentile
from .validation.warmup_leakage import WarmupValidator, LeakageValidator
from .validation.correlation import FeatureCorrelationAnalyzer
from .lineage.feature_lineage import FeatureLineage
from .store.feature_store import FeatureStore
from .serving.multi_timeframe import MultiTimeframeEngine


class FeatureEngineV3:
    """
    Orchestrator CANONICAL Layer 3.
    Menghasilkan atomic features + context components (bukan regime decision).
    """
    
    ENGINE_VERSION = "v3"
    
    def __init__(self, config_path: Optional[str] = None, storage_dir: Optional[str] = None):
        """Inisialisasi engine V3."""
        self.config = self._load_config(config_path)
        self.schema = FeatureSchema(engine_version="v3", config_version=self.config.get("config_version", "1.0.0"))
        self.store = FeatureStore(storage_dir=storage_dir)
        self.lineage = FeatureLineage()
        self.warmup_validator = WarmupValidator()
        self.leakage_validator = LeakageValidator()
        self.correlation_analyzer = FeatureCorrelationAnalyzer()
        
        # Domain calculators
        params = self.config.get("parameters", {})
        self.price_structure = PriceStructureFeatures(params)
        self.volatility = VolatilityFeatures(params)
        self.volume = VolumeFeatures(params)
        self.participation = ParticipationFeatures(params)
        self.trend = TrendFeatures(params)
        self.regime_context = RegimeContextFeatures(params)
        self.cross_asset = CrossAssetFeatures()
        
        # Normalizers
        self.zscore = RollingZScore(window=100, min_samples=30)
        self.percentile = RollingPercentile(window=500, min_samples=30)
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load config dari file JSON (config-driven, bukan hardcoded)."""
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        # Default config
        return {
            "config_version": "1.1.0",
            "parameters": {},
            "critical_features": ["atr_ratio", "bb_width", "volume_ratio"],
        }
    
    # ============ PIPELINE UTAMA ============
    def compute_all_atomic(self, ohlcv: List[Dict], 
                           open_interest: Optional[List] = None,
                           funding_rate: Optional[List] = None,
                           orderbooks: Optional[List] = None) -> List[Dict]:
        """
        Hitung semua ATOMIC features dari semua domain.
        Output: observasi mentah — BUKAN interpretasi/regime.
        """
        if not ohlcv:
            return []
        n = len(ohlcv)
        
        # Hitung per domain
        price_f = self.price_structure.compute_all(ohlcv)
        vol_f = self.volatility.compute_all(ohlcv)
        volu_f = self.volume.compute_all(ohlcv)
        
        part_data = {
            "close": [d["close"] for d in ohlcv],
            "open_interest": open_interest or [],
            "funding_rate": funding_rate or [],
            "timestamp": [d.get("timestamp", i) for i, d in enumerate(ohlcv)],
        }
        part_f = self.participation.compute_all(part_data)
        
        trend_f = self.trend.compute_all(
            [d["close"] for d in ohlcv], [d["high"] for d in ohlcv], [d["low"] for d in ohlcv],
            [d.get("timestamp", i) for i, d in enumerate(ohlcv)]
        )
        
        # Gabungkan per bar (ATOMIC only)
        merged = []
        for i in range(n):
            row = {"timestamp": ohlcv[i].get("timestamp", i)}
            for src in (price_f, vol_f, volu_f, part_f, trend_f):
                if i < len(src):
                    for k, v in src[i].items():
                        if k not in ("timestamp", "symbol") and k not in ("positing",):
                            row[k] = v
            merged.append(row)
        return merged
    
    def compute_context(self, atomic_rows: List[Dict]) -> List[Dict]:
        """
        Hitung CONTEXT components dari atomic features.
        Ini HANYA interpretasi state — BUKAN keputusan regime (Layer 4).
        """
        return self.regime_context.compute_components(atomic_rows)
    
    def add_normalization(self, atomic_rows: List[Dict]) -> List[Dict]:
        """
        Tambahkan normalized version dari feature (z-score, percentile).
        Feature tetap, tapi ada kolom _zscore / _percentile.
        Membuat feature asset-agnostic.
        """
        if not atomic_rows:
            return []
        
        # Kumpulkan nilai per feature
        feat_series = {}
        for k in atomic_rows[0]:
            if k in ("timestamp", "symbol"):
                continue
            if isinstance(atomic_rows[0][k], (int, float)):
                feat_series[k] = [r.get(k, 0.0) for r in atomic_rows]
        
        # Hitung zscore & percentile
        zscores = {}
        percentiles = {}
        for feat, series in feat_series.items():
            zscores[feat] = self.zscore.transform_series(series)
            percentiles[feat] = self.percentile.transform_series(series)
        
        # Gabungkan
        result = []
        for i, row in enumerate(atomic_rows):
            enriched = dict(row)
            for feat in feat_series:
                enriched[f"{feat}_zscore"] = round(zscores[feat][i], 4)
                enriched[f"{feat}_percentile"] = round(percentiles[feat][i], 4)
            result.append(enriched)
        
        return result
    
    def enforce_warmup(self, rows: List[Dict]) -> List[Dict]:
        """Tandai feature WARMUP berdasarkan metadata lookback."""
        return self.warmup_validator.validate_warmup(rows)
    
    def format_snapshot(self, atomic_rows: List[Dict], context_rows: List[Dict],
                        symbol: str) -> List[Dict]:
        """
        Format final row: atomic + context + warmup status.
        Dengan schema version untuk lineage.
        """
        final = []
        for i in range(min(len(atomic_rows), len(context_rows))):
            row = {
                "symbol": symbol,
                **atomic_rows[i],
                **context_rows[i],
            }
            # Tambahkan schema info (slide untuk lineage)
            row["_schema_version"] = self.schema.feature_schema
            row["_engine_version"] = self.schema.engine_version
            row["_code_version"] = self.schema.code_version
            row["_config_version"] = self.schema.config_version
            final.append(row)
        return final
    
    # ============ FULL PIPELINE ============
    def process_symbol(self, symbol: str, ohlcv: List[Dict],
                       open_interest: Optional[List] = None,
                       funding_rate: Optional[List] = None,
                       store_results: bool = True, 
                       compute_context_components: bool = True) -> Dict[str, Any]:
        """
        Proses lengkap satu symbol: atomic + context + normalization + warmup.
        
        PENTING: Menghasilkan CONTEXT (state description), BUKAN regime decision.
        """
        # 1. Atomic features
        atomic_rows = self.compute_all_atomic(ohlcv, open_interest, funding_rate)
        
        # 2. Context components (bukan regime)
        context_rows = []
        if compute_context_components:
            context_rows = self.compute_context(atomic_rows)
        
        # 3. Normalization (asset-agnostic)
        normalized = self.add_normalization(atomic_rows)
        
        # 4. Warmup enforcement
        warmed = self.enforce_warmup(normalized)
        
        # 5. Format final snapshot
        final_rows = self.format_snapshot(warmed, context_rows, symbol)
        
        # 6. Leakage check
        leakage = self.leakage_validator.check_leakage(atomic_rows)
        
        # 7. Simpan ke Feature Store (jika diminta)
        store_info = {"stored": False}
        if store_results:
            store_info = self.store.save_features(symbol, final_rows, source="feature_engine_v3")
        
        return {
            "symbol": symbol,
            "total_rows": len(final_rows),
            "atomic_features": self._list_features(atomic_rows),
            "context_features": self._list_features(context_rows),
            "leakage_check": leakage,
            "store_info": store_info,
            "schema": self.schema.to_dict(),
        }
    
    def _list_features(self, rows: List[Dict]) -> List[str]:
        """List nama feature dari rows."""
        if not rows:
            return []
        return sorted(k for k in rows[0] if k not in ("timestamp", "symbol"))
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Ringkasan state pipeline."""
        return {
            "engine": self.ENGINE_VERSION,
            "status": "operational",
            "boundary": "Feature → Context → (Layer4: Alpha → Signal)",
            "decides_regime": False,  # Layer 4 yang memutuskan
            "schema": self.schema.to_dict(),
            "lineage_features": len(self.lineage.graph),
        }


# Quick test
if __name__ == "__main__":
    import random
    random.seed(14)
    
    print("=" * 60)
    print("FEATURE ENGINE V3 - CANONICAL (boundary refactor test)")
    print("=" * 60)
    
    # Generate OHLCV: compression di akhir
    n = 120
    ohlcv = []
    price = 100.0
    for i in range(n):
        vol_scale = 1.0 if i < 80 else 0.3
        o = price
        c = price + random.uniform(-1, 1) * vol_scale
        h = max(o, c) + random.uniform(0, 0.7) * vol_scale
        l = min(o, c) - random.uniform(0, 0.7) * vol_scale
        vol = random.uniform(2000, 5000) * (0.3 if i > 80 else 1.0)
        ohlcv.append({"open": o, "high": h, "low": l, "close": c,
                      "volume": vol, "timestamp": i})
        price = c
    oi = [100000] * n
    fund = [0.0001] * n
    
    engine = FeatureEngineV3()
    result = engine.process_symbol("BTCUSDT", ohlcv, oi, fund, store_results=False)
    
    print(f"\nTotal rows: {result['total_rows']}")
    print(f"Boundary: {engine.get_pipeline_summary()['boundary']}")
    print(f"Decides regime? {engine.get_pipeline_summary()['decides_regime']} (harus False)")
    print(f"Atomic features ({len(result['atomic_features'])}): {result['atomic_features'][:8]}...")
    
    # Tampilkan context dari bar terakhir (komponen, bukan regime)
    # Ambil contoh dengan recompute
    atomic = engine.compute_all_atomic(ohlcv, oi, fund)
    context = engine.compute_context(atomic)
    
    print("\nContext komponen (bukan keputusan regime) bar terakhir:")
    last_ctx = context[-1]
    print(f"  compression_components = {last_ctx.get('compression_components')}")
    print(f"  trend_components = {last_ctx.get('trend_components')}")
    print(f"  volatility_state = {last_ctx.get('volatility_state')}")
    print(f"  trend_state = {last_ctx.get('trend_state')}")
    print(f"  'regime' di context? → {'regime' in last_ctx} (harus False — Layer 4 putuskan)")
    
    print("\n" + "=" * 60)
    print("✓ FEATURE ENGINE V3 CANONICAL OPERATIONAL")
    print("✓ Layer 3 TIDAK mengambil keputusan regime (diserahkan Layer 4)")
    print("=" * 60)
