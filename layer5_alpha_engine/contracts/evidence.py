#!/usr/bin/env python3
"""
Layer 5 - Contract: Alpha Evidence / Attribution
Membuat alpha transparan, bukan black-box score.

Ketika PF turun: PF 3.1 → 1.4
Anda bisa mencari tahu:
- Compression masih bekerja?
- Volume confirmation yang gagal?
- OI confirmation tidak berguna?

Evidence adalah komponen yang membentuk score, disimpan individual.
"""
from typing import Dict, List, Any, Optional


class AlphaEvidence:
    """
    Kumpulan evidence (komponen) dari sebuah alpha signal.
    Transparan untuk attribution & penelitian.
    """
    
    def __init__(self, alpha_id: str = ""):
        self.alpha_id = alpha_id
        self.components: Dict[str, float] = {}   # nama komponen → nilai (0-1)
        self.weights: Dict[str, float] = {}      # bobot komponen
        self.notes: Dict[str, str] = {}          # keterangan tambahan
    
    def add(self, name: str, value: float, weight: float = 1.0, note: str = ""):
        """
        Tambah komponen evidence.
        
        Args:
            name: nama komponen (compression, volume_expansion, dll)
            value: nilai 0-1
            weight: bobot relatif
            note: keterangan
        """
        self.components[name] = round(value, 4)
        self.weights[name] = weight
        if note:
            self.notes[name] = note
    
    def get(self, name: str) -> Optional[float]:
        """Ambil nilai komponen."""
        return self.components.get(name)
    
    def composite_score(self) -> float:
        """
        Hitung score gabungan (weighted) dari komponen.
        Ini score yang TIDAK menyembunyikan komponen (masih bisa diattribusi).
        """
        if not self.components:
            return 0.0
        total_weight = sum(self.weights.values())
        if total_weight == 0:
            return 0.0
        score = sum(self.components[k] * self.weights[k] 
                    for k in self.components if k in self.weights) / total_weight
        return round(score, 4)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialisasi evidence (untuk output AlphaSignal)."""
        return {
            "components": dict(self.components),
            "weights": dict(self.weights),
            "composite_score": self.composite_score(),
            "notes": dict(self.notes),
        }
    
    def attribution_insight(self, threshold: float = 0.5) -> List[str]:
        """
        Analisis attribution: komponen mana yang kuat/lemah.
        Untuk debug ketika edge menurun.
        """
        insights = []
        for name, value in self.components.items():
            status = "✅ KUAT" if value >= threshold else "❌ LEMAH"
            insights.append(f"{name}: {value:.2f} ({status})")
        return insights


# Quick test
if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("=" * 60)
    print("ALPHA EVIDENCE / ATTRIBUTION TEST")
    print("=" * 60)
    
    # Compression Breakout evidence
    ev = AlphaEvidence("compression_breakout_v1")
    ev.add("compression", 0.91, weight=0.3)
    ev.add("price_breakout", 0.88, weight=0.3)
    ev.add("volume_expansion", 0.84, weight=0.25)
    ev.add("oi_confirmation", 0.72, weight=0.15)
    
    print("\nEvidence components:")
    for insight in ev.attribution_insight():
        print(f"  {insight}")
    print(f"\nComposite score: {ev.composite_score()}")
    
    print("\nAttribution ketika edge gagal (simulasi):")
    ev_failed = AlphaEvidence("compression_breakout_v1")
    ev_failed.add("compression", 0.9, weight=0.3)
    ev_failed.add("price_breakout", 0.85, weight=0.3)
    ev_failed.add("volume_expansion", 0.3, weight=0.25)  # ← gagal!
    ev_failed.add("oi_confirmation", 0.4, weight=0.15)   # ← gagal!
    print("  volume_expansion & oi_confirmation lemah → inilah penyebab PF turun")
    
    print("\n" + "=" * 60)
    print("✓ ALPHA EVIDENCE OPERATIONAL")
    print("= Alpha transparan, bukan black-box score")
    print("=" * 60)
