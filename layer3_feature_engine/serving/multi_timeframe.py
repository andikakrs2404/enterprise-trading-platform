#!/usr/bin/env python3
"""
Layer 3 - Multi-Timeframe Feature Architecture (P0)

Jangan Layer 3 hanya menghasilkan BTC 5m.
Sistem multi-edge membutuhkan:
  BTC 1m, 5m, 15m, 1h, 4h, 1D

Setiap timeframe punya namespace sendiri:
  5m.atr_ratio
  15m.atr_ratio
  1h.atr_ratio
  4h.adx
  1h.ema_distance

Contoh context yang kaya:
  4H = TREND
  1H = TREND
  15M = COMPRESSION
  5M = EXPANSION
(bukan hanya: 5M = COMPRESSION)

Feature lama diproses per timeframe, lalu digabung dengan namespace.
"""
from typing import Dict, List, Any, Optional
from ..domains.price_structure.features import PriceStructureFeatures
from ..domains.volatility.features import VolatilityFeatures
from ..domains.volume.features import VolumeFeatures
from ..domains.participation.features import ParticipationFeatures
from ..domains.trend.features import TrendFeatures


class MultiTimeframeEngine:
    """
    Proses feature di beberapa timeframe, gabungkan dengan namespace.
    """
    
    # Support timeframe dan prioritas
    DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1D"]
    
    def __init__(self, timeframes: List[str] = None):
        self.timeframes = timeframes or self.DEFAULT_TIMEFRAMES
        # Satu set calculators, dipakai ulang untuk semua timeframe
        self.price = PriceStructureFeatures()
        self.volatility = VolatilityFeatures()
        self.volume = VolumeFeatures()
        self.participation = ParticipationFeatures()
        self.trend = TrendFeatures()
    
    def process_timeframe(self, tf: str, ohlcv: List[Dict], 
                           open_interest: List = None, 
                           funding: List = None) -> List[Dict]:
        """
        Proses feature untuk SATU timeframe, dengan namespace prefix.
        
        Contoh output: {"5m.atr_ratio": 0.51, "5m.adx": 31, ...}
        """
        price_f = self.price.compute_all(ohlcv)
        vol_f = self.volatility.compute_all(ohlcv)
        volu_f = self.volume.compute_all(ohlcv)
        
        part_data = {
            "close": [d["close"] for d in ohlcv],
            "open_interest": open_interest or [],
            "funding_rate": funding or [],
            "timestamp": [d.get("timestamp", i) for i, d in enumerate(ohlcv)],
        }
        part_f = self.participation.compute_all(part_data)
        
        trend_f = self.trend.compute_all(
            [d["close"] for d in ohlcv],
            [d["high"] for d in ohlcv],
            [d["low"] for d in ohlcv],
            [d.get("timestamp", i) for i, d in enumerate(ohlcv)],
        )
        
        # Gabungkan per bar dengan namespace tf prefix
        n = len(ohlcv)
        result = []
        for i in range(n):
            row = {"timestamp": ohlcv[i].get("timestamp", i), "timeframe": tf}
            for src, feats in [(price_f, ["ret_1", "ret_5", "ret_24", "range_pct", "body_ratio", "hh_hl_structure"]),
                               (vol_f, ["atr", "atr_ratio", "bb_width", "realized_vol"]),
                               (volu_f, ["volume_ratio", "dollar_volume", "volume_percentile"]),
                               (part_f, ["oi_delta", "oi_pct", "funding", "positioning"]),
                               (trend_f, ["ema_dist", "ema_slope", "adx", "regression_slope"])]:
                if i < len(src):
                    for feat_name in feats:
                        if feat_name in src[i]:
                            # Namespace: "5m.atr_ratio"
                            row[f"{tf}.{feat_name}"] = src[i][feat_name]
            result.append(row)
        return result
    
    def process_all(self, data_by_tf: Dict[str, Dict], default_n: int = 100) -> List[Dict]:
        """
        Proses semua timeframe dan gabungkan jadi satu unified row per timestamp.
        
        Args:
            data_by_tf: {
                "5m": {"ohlcv": [...], "open_interest": [...], "funding": [...]},
                "1h": {"ohlcv": [...], ...},
                ...
            }
            
        Returns:
            List unified rows dengan namespaced features untuk semua timeframe.
        """
        tf_results = {}
        for tf, data in data_by_tf.items():
            if data and data.get("ohlcv"):
                tf_results[tf] = self.process_timeframe(
                    tf, data["ohlcv"], data.get("open_interest"), data.get("funding"))
        
        # Gabungkan berdasarkan timestamp (pendekatan: ambil bar terakhir per tf)
        # Untuk keperluan serving real-time, kita gabungkan bar terbaru setiap tf.
        if not tf_results:
            return []
        
        # Ambil timestamp yang tersedia paling baru
        unified = []
        # Asumsikan semua tf align pada timestamp yang sama (atau gunakan tf terkecil)
        smallest_tf = self.timeframes[0] if self.timeframes[0] in tf_results else list(tf_results)[0]
        base_rows = tf_results[smallest_tf]
        
        for base in base_rows:
            ts = base["timestamp"]
            unified_row = {"timestamp": ts}
            # Salin feature dari setiap timeframe
            for tf, rows in tf_results.items():
                # Cari bar dengan timestamp ini (approximate: gunakan index alignment)
                # Simple: pakai bar terakhir yang timestamp <= ts
                match = None
                for r in reversed(rows):
                    if r["timestamp"] <= ts:
                        match = r
                        break
                if match:
                    for k, v in match.items():
                        if k not in ("timestamp", "timeframe"):
                            unified_row[k] = v
            unified.append(unified_row)
        
        return unified


# Quick test
if __name__ == "__main__":
    import random
    random.seed(11)
    
    print("=" * 60)
    print("MULTI-TIMEFRAME TEST - namespace ft.atr_ratio")
    print("=" * 60)
    
    mtf = MultiTimeframeEngine(timeframes=["5m", "15m", "1h"])
    
    # Generate data untuk 3 timeframe (berbeda skala)
    def gen(n, start_price, vol_scale):
        ohlcv = []
        price = start_price
        for i in range(n):
            o = price
            c = price + random.uniform(-1, 1) * vol_scale
            highs = max(o, c) + random.uniform(0, 0.7) * vol_scale
            lows = min(o, c) - random.uniform(0, 0.7) * vol_scale
            ohlcv.append({"open": o, "high": highs, "low": lows, "close": c,
                          "volume": random.uniform(2000, 5000), "timestamp": i})
            price = c
        return ohlcv
    
    data_by_tf = {
        "5m": {"ohlcv": gen(80, 100, 0.3)},   # compression (low vol)
        "15m": {"ohlcv": gen(80, 100, 1.0)},  # normal
        "1h": {"ohlcv": gen(80, 100, 2.0)},   # high vol (trend)
    }
    
    unified = mtf.process_all(data_by_tf)
    
    print("\nBaris terakhir (unified multi-timeframe):")
    last = unified[-1]
    for k, v in last.items():
        if isinstance(v, float):
            print(f"  {k} = {v:.3f}")
        else:
            print(f"  {k} = {v}")
    
    print("\n" + "=" * 60)
    print("✓ Multi-Timeframe Operational")
    print("= (setiap tf punya namespace: 5m.atr_ratio, 1h.adx, dst)")
    print("=" * 60)
