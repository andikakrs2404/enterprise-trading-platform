#!/usr/bin/env python3
"""
Domain 7 - Regime Context Features
BUKAN pengambil keputusan regime!

Perubahan konsep penting (sesuai review arsitektur):
Sebelumnya:
  Regime → compression_score → trend_score → expansion_score → regime=COMPRESSION
  (INI SALAH — Layer 3 terlalu cepat memutuskan regime)

Sekarang:
  Regime Context → compression_components (volatility/range/volume/liquidity/positioning)
                  → trend_components (strength/direction)
                  → expansion_components (vol/volume/oi)
  Lalu LAYER 4 yang menentukan regime final.

Domain ini hanya MENYEDIAKAN komponen, bukan MENGAMBIL KEPUTUSAN.
"""
from typing import List, Dict, Any, Optional


class RegimeContextFeatures:
    """
    DOMAIN 7 — REGIME CONTEXT
    
    Dihasilkan (komponen-level, semua disimpan):
    - compression_components: dict dari sub-komponen compression
        volatility_compression, range_compression, volume_compression,
        liquidity_compression, positioning_compression
    - trend_components: dict dari sub-komponen trend
        adx_strength, ema_slope_state, structure_state
    - expansion_components: dict dari sub-komponen expansion
        volatility_expansion, volume_expansion, oi_expansion
    
    Composite scores DIPERTAHANKAN sebagai convenience, tetapi
    komponen individual SELALU disimpan (edge berbeda butuh komponen berbeda).
    
    TIDAK menghasilkan label regime final — itu tugas Layer 4.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        # Threshold dari config (tidak hardcoded)
        self.compression_atr_threshold = cfg.get("compression_atr_ratio_threshold", 0.7)
        self.compression_bb_threshold = cfg.get("compression_bb_width_threshold", 0.03)
        self.expansion_atr_threshold = cfg.get("expansion_atr_ratio_threshold", 1.5)
    
    def compute_components(self, feature_rows: List[Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        Hitung komponen regime context dari atomic features.
        
        Args:
            feature_rows: List dict atomic features (dari Layer 3 atomic compute)
                atr_ratio, bb_width, volume_ratio, volume_percentile,
                adx, ema_slope, hh_hl_structure, oi_pct, dll.
                
        Returns:
            List dict dengan komponen context - BUKAN regime label.
        """
        results = []
        for r in feature_rows:
            row = {
                "timestamp": r.get("timestamp", 0),
                "symbol": r.get("symbol", "UNKNOWN"),
            }
            
            # --- COMPRESSION COMPONENTS (semua disimpan individual) ---
            atr_ratio = r.get("atr_ratio", 1.0)
            bb_width = r.get("bb_width", 0.05)
            volume_ratio = r.get("volume_ratio", 1.0)
            volume_pct = r.get("volume_percentile", 0.5)
            
            # 1. Volatility compression (ATR ratio rendah)
            atr_comp = min(1.0, max(0.0, 1.0 - atr_ratio / self.compression_atr_threshold))
            # 2. Range compression (BB width sempit)
            bb_comp = min(1.0, max(0.0, 1.0 - bb_width / 0.05))
            # 3. Volume compression (volume rendah relatif)
            vol_comp = min(1.0, max(0.0, 1.0 - volume_ratio))
            # 4. Liquidity compression (proxy: volume percentile rendah)
            liq_comp = min(1.0, max(0.0, 1.0 - volume_pct))
            # 5. Positioning compression (proxy: OI change rendah)
            oi_pct = r.get("oi_pct", 0.0)
            pos_comp = min(1.0, max(0.0, 1.0 - abs(oi_pct) * 50))
            
            # Composite compression = weighted dari komponen
            row["compression_components"] = {
                "volatility_compression": round(atr_comp, 4),
                "range_compression": round(bb_comp, 4),
                "volume_compression": round(vol_comp, 4),
                "liquidity_compression": round(liq_comp, 4),
                "positioning_compression": round(pos_comp, 4),
            }
            # Composite convenience score (tetap simpan komponen!)
            row["compression_score"] = round(
                0.3*atr_comp + 0.3*bb_comp + 0.2*vol_comp + 0.1*liq_comp + 0.1*pos_comp, 4
            )
            
            # --- TREND COMPONENTS ---
            adx = r.get("adx", 0.0)
            ema_slope = r.get("ema_slope", 0.0)
            struct = r.get("hh_hl_structure", 0.0)
            
            # Strength
            adx_strength = min(1.0, adx / 50.0)
            # Direction dari ema slope & structure
            slope_dir = 1.0 if ema_slope > 0 else (-1.0 if ema_slope < 0 else 0.0)
            struct_dir = struct  # -1..1 (higher-high/lower-low)
            direction = (slope_dir * 0.5 + struct_dir * 0.5)  # -1..1
            
            row["trend_components"] = {
                "adx_strength": round(adx_strength, 4),
                "ema_slope_state": "UP" if slope_dir > 0 else ("DOWN" if slope_dir < 0 else "FLAT"),
                "structure_state": "BULLISH" if struct_dir > 0 else ("BEARISH" if struct_dir < 0 else "NEUTRAL"),
                "direction": round(direction, 4),
            }
            row["trend_score"] = round(direction * (0.5 + 0.5*adx_strength), 4)
            row["trend_strength"] = round(adx_strength, 4)
            
            # --- EXPANSION COMPONENTS ---
            atr_exp = min(1.0, atr_ratio / self.expansion_atr_threshold)
            vol_exp = min(1.0, max(0.0, (volume_ratio - 1.0) / 2.0))
            oi_exp = min(1.0, max(0.0, abs(oi_pct) * 20))
            
            row["expansion_components"] = {
                "volatility_expansion": round(atr_exp, 4),
                "volume_expansion": round(vol_exp, 4),
                "oi_expansion": round(oi_exp, 4),
            }
            row["expansion_score"] = round(0.4*atr_exp + 0.4*vol_exp + 0.2*oi_exp, 4)
            
            # --- Volatility / Trend / Participation / Liquidity STATE ---
            # State description (bukan decision!)
            row["volatility_state"] = self._state_from_score(1.0 - atr_comp)
            row["trend_state"] = "STRONG_TREND" if adx_strength > 0.5 else (
                "WEAK_TREND" if adx_strength > 0.3 else "NO_TREND")
            row["participation_state"] = "BUILDING" if oi_pct > 0.01 else (
                "REDUCING" if oi_pct < -0.01 else "NEUTRAL")
            
            # TIDAK ADA row["regime"] — itu keputusan Layer 4!
            
            results.append(row)
        
        return results
    
    def _state_from_score(self, score: float) -> str:
        """State label dari score 0-1 (untuk state description)."""
        if score > 0.7:
            return "EXTREME"
        elif score > 0.55:
            return "HIGH"
        elif score > 0.35:
            return "NORMAL"
        elif score > 0.2:
            return "LOW"
        else:
            return "EXTREME_LOW"


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("DOMAIN 7 — REGIME CONTEXT (bukan REGIME!) — Component-level Test")
    print("=" * 60)
    
    # Test: 2 scenario
    compression = [
        {"timestamp": 1, "symbol": "BTCUSDT", "atr_ratio": 0.52, "bb_width": 0.018,
         "volume_ratio": 0.6, "volume_percentile": 0.08, "adx": 15,
         "ema_slope": 0.004, "hh_hl_structure": 0.0, "oi_pct": 0.005}
    ]
    expansion = [
        {"timestamp": 2, "symbol": "BTCUSDT", "atr_ratio": 2.0, "bb_width": 0.09,
         "volume_ratio": 3.5, "volume_percentile": 0.97, "adx": 45,
         "ema_slope": 2.0, "hh_hl_structure": 1.0, "oi_pct": 0.05}
    ]
    
    calc = RegimeContextFeatures()
    
    print("\nCOMPRESSION scenario (komponen disimpan individual):")
    r = calc.compute_components(compression)[0]
    print(f"  compression_components = {r['compression_components']}")
    print(f"  compression_score (convenience) = {r['compression_score']}")
    print(f"  volatility_state = {r['volatility_state']}")
    print(f"  trend_state = {r['trend_state']}")
    print(f"  'regime' key ada? → {'regime' in r}  (harus False, Layer 4 yang putuskan)")
    
    print("\nEXPANSION scenario:")
    r2 = calc.compute_components(expansion)[0]
    print(f"  expansion_components = {r2['expansion_components']}")
    print(f"  expansion_score = {r2['expansion_score']}")
    print(f"  trend_components = {r2['trend_components']}")
    print(f"  participation_state = {r2['participation_state']}")
    
    print("\n" + "=" * 60)
    print("✓ Domain 7 Regime CONTEXT Operational (komponen, bukan keputusan)")
    print("✓ Tidak ada label regime final — diserahkan ke Layer 4")
    print("=" * 60)
