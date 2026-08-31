#!/usr/bin/env python3
"""
Domain 4 - Market Participation Features (Futures Specific)
Penting untuk futures: open interest & funding menunjukkan "siapa yang ada di pasar".
"""
from typing import List, Dict, Any, Optional


class ParticipationFeatures:
    """
    DOMAIN 4 — MARKET PARTICIPATION (FUTURES)
    
    Feature yang dihitung:
    - oi_delta: OI - OI_prev (perubahan posisi)
    - oi_pct: (OI - OI_prev) / OI_prev (perubahan %)
    - funding: funding_rate (positioning indicator)
    - positioning_implied: harga vs OI & funding → long/short domination
    
    INTERPRETASI (kombinasi dengan price):
    - Price up, OI up   = NEW LONG (+)
    - Price down, OI up = NEW SHORT (-)
    - Price up, OI down = SHORT COVERING (bullish reversal)
    - Price down, OI down = LONG LIQUIDATION (bearish)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.oi_delta_period = cfg.get("oi_delta_period", 1)
    
    def compute_all(self, data: Dict[str, List]) -> List[Dict[str, float]]:
        """
        Hitung semua feature participation.
        
        Args:
            data: Dict yang mengandung:
                - close: List harga
                - open_interest: List OI
                - funding_rate: List funding
                - timestamp: List timestamp (optional)
        """
        closes = data.get("close", [])
        oi = data.get("open_interest", [])
        funding = data.get("funding_rate", [])
        timestamps = data.get("timestamp", list(range(len(closes))))
        
        n = len(closes)
        results = []
        
        for i in range(n):
            row = {
                "timestamp": timestamps[i] if i < len(timestamps) else i,
            }
            
            # --- OI Delta ---
            if i >= self.oi_delta_period and i < len(oi) and oi[i] is not None:
                oi_prev = oi[i - self.oi_delta_period] if oi[i-self.oi_delta_period] is not None else 0
                row["oi_delta"] = oi[i] - oi_prev
            else:
                row["oi_delta"] = 0.0
            
            # --- OI Percent Change ---
            if i >= 1 and i < len(oi):
                oi_prev = oi[i-1] if oi[i-1] else 0
                if oi_prev != 0 and oi[i] is not None:
                    row["oi_pct"] = (oi[i] - oi_prev) / oi_prev
                else:
                    row["oi_pct"] = 0.0
            else:
                row["oi_pct"] = 0.0
            
            # --- Funding ---
            if i < len(funding) and funding[i] is not None:
                row["funding"] = funding[i]
            else:
                row["funding"] = 0.0
            
            # --- Positioning Implied (dengan price) ---
            # Kombinasi: harga & OI untuk tahu posisi dominan
            if i >= 1 and i < len(oi) and i < len(closes):
                price_up = closes[i] > closes[i-1] if closes[i-1] is not None else False
                oi_up = oi[i] > oi[i-1] if oi[i-1] is not None else False
                
                if price_up and oi_up:
                    row["positioning"] = 1.0    # New Long
                elif not price_up and oi_up:
                    row["positioning"] = -1.0   # New Short
                elif price_up and not oi_up:
                    row["positioning"] = 0.5    # Short Covering
                else:
                    row["positioning"] = -0.5   # Long Liquidation
            else:
                row["positioning"] = 0.0
            
            results.append(row)
        
        return results


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("DOMAIN 4 — MARKET PARTICIPATION TEST")
    print("=" * 60)
    
    # Test data dengan skenario berbeda
    data = {
        "close": [100, 101, 102, 103, 102, 101],
        "open_interest": [1000, 1500, 2000, 2500, 2300, 2100],  # naik, lalu turun
        "funding_rate": [0.0001, 0.0002, 0.0003, 0.0004, 0.0002, 0.0001],
        "timestamp": [0, 1, 2, 3, 4, 5],
    }
    
    calc = ParticipationFeatures()
    features = calc.compute_all(data)
    
    print("\nInterpretasi positioning per bar:")
    for f in features:
        print(f"  ts={f['timestamp']}: oi_delta={f['oi_delta']:.0f}, oi_pct={f['oi_pct']:.1%}, "
              f"funding={f['funding']:.5f}, positioning={f['positioning']}")
    
    print("\n" + "=" * 60)
    print("✓ Domain 4 Market Participation Operational")
    print("=" * 60)
