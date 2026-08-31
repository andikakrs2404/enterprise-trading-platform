#!/usr/bin/env python3
"""
Backtester - Strategies: Compression Breakout v1
Strategi pertama yang menjadi baseline regression test.

KONSUMSI feature dari Feature Store V3 (tidak menghitung sendiri).
Menggunakan komponen context dari Layer 3 + regime dari Layer 4.

Logika (dasar):
- Entry BUY: compression_score tinggi (market termampat) 
  → regim COMPRESSION, siap breakout
- Exit SELL: expansion_score naik / oi_delta positif (breakout terjadi)
"""
from typing import Dict, List, Optional


class CompressionBreakoutV1:
    """
    Compression Breakout strategy v1.
    Hanya membaca feature — TIDAK menghitung indikator sendiri.
    """
    
    STRATEGY_VERSION = "compression_v1"
    
    def __init__(self, config: Optional[Dict] = None):
        cfg = config or {}
        # Threshold dari config (tidak hardcoded)
        self.entry_compression_threshold = cfg.get("entry_compression_threshold", 0.6)
        self.exit_expansion_threshold = cfg.get("exit_expansion_threshold", 0.4)
        self.exit_oi_delta_threshold = cfg.get("exit_oi_delta_threshold", 1.0)
    
    def generate_signal(self, row: Dict, position: Dict) -> Dict:
        """
        Generate sinyal dari features.
        
        Args:
            row: feature row (dari L3, sudah termasuk compression_score, dll)
            position: posisi saat ini {active, ...}
            
        Returns:
            Dict: {"action": "BUY"/"SELL"/"HOLD", "reason": "...", ...}
        """
        if not position.get("active"):
            # Cari entry: compression (siap breakout)
            comp_score = row.get("compression_score", 0)
            if comp_score > self.entry_compression_threshold:
                return {
                    "action": "BUY",
                    "reason": "compression_breakout",
                    "compression_score": comp_score,
                    "regime": "COMPRESSION",
                }
        else:
            # Cari exit: expansion (breakout terjadi)
            exp_score = row.get("expansion_score", 0)
            oi_delta = row.get("oi_delta", 0)
            if exp_score > self.exit_expansion_threshold or oi_delta > self.exit_oi_delta_threshold:
                return {
                    "action": "SELL",
                    "reason": "breakout_realized",
                    "expansion_score": exp_score,
                    "oi_delta": oi_delta,
                    "regime": "VOLATILITY_EXPANSION",
                }
        
        return {"action": "HOLD", "reason": ""}
    
    def create_strategy_fn(self):
        """Wrap generate_signal sebagai function signature untuk backtester."""
        return self.generate_signal


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("COMPRESSION BREAKOUT V1 STRATEGY TEST")
    print("=" * 60)
    
    strat = CompressionBreakoutV1()
    
    # Test entry: compression tinggi
    entry_signal = strat.generate_signal(
        {"compression_score": 0.85, "expansion_score": 0.1, "oi_delta": 0.2},
        {"active": False},
    )
    print(f"\nEntry saat compression_score=0.85:")
    print(f"  {entry_signal}")
    
    # Test exit: expansion
    pos = {"active": True, "entry": 100, "qty": 1}
    exit_signal = strat.generate_signal(
        {"compression_score": 0.1, "expansion_score": 0.7, "oi_delta": 5.0},
        pos,
    )
    print(f"\nExit saat expansion_score=0.7:")
    print(f"  {exit_signal}")
    
    # Test hold: tidak ada kondisi
    hold_signal = strat.generate_signal(
        {"compression_score": 0.3, "expansion_score": 0.2, "oi_delta": 0.0},
        {"active": False},
    )
    print(f"\nHold (tidak ada kondisi):")
    print(f"  {hold_signal}")
    
    print("\n" + "=" * 60)
    print("✓ COMPRESSION BREAKOUT V1 OPERATIONAL")
    print("✓ Hanya konsumsi feature, tidak hitung indikator")
    print("=" * 60)
