#!/usr/bin/env python3
"""
Domain 7 - Regime Features
INI ADALAH HATI DARI SISTEM ANDA.
Menjawab: "Market dalam kondisi apa?"
Menggabungkan feature dari domain lain menjadi skor regime.
"""
from typing import List, Dict, Any, Optional


class RegimeFeatures:
    """
    DOMAIN 7 — REGIME FEATURES
    
    Feature yang dihitung:
    - compression_score: kombinasi ATR Ratio + BB Width + Volume Contraction
      MAGNA: Compression → Expansion adalah edge paling kuat.
      ATR Ratio < 0.6 + BB Width < 10% + Volume Ratio < 0.8 = compression penuh
    - trend_score: kombinasi ADX + EMA Slope + HH/HL
    - expansion_score: kombinasi ATR Spike + Volume Spike + OI Spike
    
    Edge yg dicari (dari riset user):
    compression_score tinggi → ATR Ratio < 0.6, BB Width low, Volume low
    Lalu breakout → expansion
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        # Threshold dari config (tidak hardcoded — fix CodeRabbit)
        self.compression_atr_threshold = cfg.get("compression_atr_ratio_threshold", 0.7)
        self.compression_bb_threshold = cfg.get("compression_bb_width_threshold", 0.03)
        self.expansion_atr_threshold = cfg.get("expansion_atr_ratio_threshold", 1.5)
    
    def compute_scores(self, feature_rows: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """
        Hitung skor regime dari feature rows (gabungan domain 1-6).
        
        Args:
            feature_rows: List dict yang sudah berisi feature dari domain lain:
                atr_ratio, bb_width, volume_ratio, adx, ema_slope, oi_delta, dll.
                (Sesuai output FeatureStore)
                
        Returns:
            List dict dengan compression_score, trend_score, expansion_score
        """
        results = []
        for r in feature_rows:
            row = {
                "timestamp": r.get("timestamp", 0),
                "symbol": r.get("symbol", "UNKNOWN"),
            }
            
            # --- COMPRESSION SCORE (0-1) ---
            # Semakin tinggi = semakin terkompresi (siap breakout)
            atr_ratio = r.get("atr_ratio", 1.0)
            bb_width = r.get("bb_width", 0.05)
            volume_ratio = r.get("volume_ratio", 1.0)
            
            # Komponen compression
            # 1. ATR ratio rendah = volatilitas menyempit
            atr_comp = max(0.0, 1.0 - (atr_ratio / self.compression_atr_threshold)) 
            atr_comp = min(1.0, atr_comp)  # clamp
            # Jika atr_ratio < threshold, atr_comp > 0
            atr_comp = 1.0 if atr_ratio <= self.compression_atr_threshold else atr_comp
            
            # 2. BB Width rendah = band menyempit
            bb_comp = 1.0 if bb_width <= self.compression_bb_threshold else max(0.0, 1.0 - bb_width/0.05)
            
            # 3. Volume contraction
            vol_comp = max(0.0, 1.0 - volume_ratio)
            
            # Weighted compression score
            row["compression_score"] = (0.4 * atr_comp + 0.4 * bb_comp + 0.2 * vol_comp)
            row["compression_score"] = min(1.0, max(0.0, row["compression_score"]))
            
            # --- TREND SCORE (-1 to 1) ---
            # Positif = uptrend, negatif = downtrend
            adx = r.get("adx", 0.0)
            ema_slope = r.get("ema_slope", 0.0)
            ema_dist = r.get("ema_dist", 0.0)
            struct = r.get("hh_hl_structure", 0.0)
            
            # Komponen trend
            trend_dir = 0.0
            # EMA slope direction
            if ema_slope > 0:
                trend_dir += 0.4
            elif ema_slope < 0:
                trend_dir -= 0.4
            # EMA dist
            if ema_dist > 0:
                trend_dir += 0.3
            elif ema_dist < 0:
                trend_dir -= 0.3
            # Structure higher-high/lower-low
            trend_dir += 0.3 * struct
            
            # Scale dengan ADX strength (jika ADX tinggi, trend lebih valid)
            adx_strength = min(1.0, adx / 50.0)  # ADX 50 = sangat kuat
            row["trend_score"] = trend_dir * (0.5 + 0.5 * adx_strength)
            row["trend_score"] = min(1.0, max(-1.0, row["trend_score"]))
            row["trend_strength"] = adx_strength
            
            # --- EXPANSION SCORE (0-1) ---
            # Semakin tinggi = volatilitas meletus
            atr_exp = atr_ratio / self.expansion_atr_threshold
            atr_exp = min(1.0, atr_exp)
            # Volume spike
            vol_exp = min(1.0, max(0.0, (volume_ratio - 1.0) / 2.0))
            # OI spike
            oi_pct = r.get("oi_pct", 0.0)
            oi_exp = min(1.0, max(0.0, oi_pct * 20))
            
            row["expansion_score"] = (0.4 * atr_exp + 0.4 * vol_exp + 0.2 * oi_exp)
            row["expansion_score"] = min(1.0, max(0.0, row["expansion_score"]))
            
            # --- REGIME LABEL ---
            # Gabungkan ketiga skor jadi label
            row["regime"] = self._classify_regime(
                row["compression_score"], row["expansion_score"], row["trend_score"]
            )
            
            results.append(row)
        
        return results
    
    def _classify_regime(self, comp, exp, trend):
        """Klasifikasi regime berdasarkan skor."""
        if exp > 0.6 and trend > 0.5:
            return "TRENDING_UP"
        elif exp > 0.6 and trend < -0.5:
            return "TRENDING_DOWN"
        elif exp > 0.6:
            return "VOLATILITY_EXPANSION"
        elif comp > 0.6:
            return "COMPRESSION"
        elif comp > 0.4:
            return "RANGE"
        else:
            return "NORMAL"


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("DOMAIN 7 — REGIME FEATURES TEST")
    print("=" * 60)
    
    # Test: 3 scenario
    # 1. Compression penuh (siap breakout)
    compression = [
        {"timestamp": 1, "symbol": "BTCUSDT", "atr_ratio": 0.5, "bb_width": 0.02,
         "volume_ratio": 0.6, "adx": 15, "ema_slope": 0.01, "ema_dist": 0.0,
         "hh_hl_structure": 0.0, "oi_pct": 0.001}
    ]
    # 2. Expansion/breakout
    expansion = [
        {"timestamp": 2, "symbol": "BTCUSDT", "atr_ratio": 2.0, "bb_width": 0.08,
         "volume_ratio": 3.5, "adx": 40, "ema_slope": 2.0, "ema_dist": 0.05,
         "hh_hl_structure": 1.0, "oi_pct": 0.05}
    ]
    # 3. Range/tidak jelas
    range_ = [
        {"timestamp": 3, "symbol": "BTCUSDT", "atr_ratio": 1.0, "bb_width": 0.04,
         "volume_ratio": 1.0, "adx": 20, "ema_slope": 0.0, "ema_dist": 0.01,
         "hh_hl_structure": 0.0, "oi_pct": 0.005}
    ]
    
    calc = RegimeFeatures()
    
    for scenario_name, rows in [("COMPRESSION", compression), 
                                 ("EXPANSION", expansion), 
                                 ("RANGE", range_)]:
        result = calc.compute_scores(rows)[0]
        print(f"\nScenario {scenario_name}:")
        print(f"  compression_score={result['compression_score']:.2f}")
        print(f"  expansion_score={result['expansion_score']:.2f}")
        print(f"  trend_score={result['trend_score']:.2f}")
        print(f"  regime={result['regime']}")
    
    print("\n" + "=" * 60)
    print("✓ Domain 7 Regime Features Operational — COMPRESSION→EXPANSION edge")
    print("=" * 60)
