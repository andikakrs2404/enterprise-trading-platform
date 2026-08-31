#!/usr/bin/env python3
"""
Domain 1 - Price Structure Features
Menjawab pertanyaan: "Harga sedang melakukan apa?"
Feature orthogonality: fokus pada struktur harga, bukan momentum.
"""
from typing import List, Dict, Any, Optional


class PriceStructureFeatures:
    """
    DOMAIN 1 — PRICE STRUCTURE
    
    Feature yang dihitung:
    - ret_1: 1 bar return (short-term)
    - ret_5: 5 bar return (medium)
    - ret_24: 24 bar return (longer)
    - range_pct: (high - low) / close — agresivitas candle
    - body_ratio: |close - open| / (high - low) — conviction
    - hh_hl_structure: higher-high/higher-low market structure
    """
    
    # Config threshold dari file config
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def compute_all(self, ohlcv: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """
        Hitung semua feature price structure.
        
        Args:
            ohlcv: List dict dengan keys open, high, low, close, volume
            
        Returns:
            List dict dengan feature per bar
        """
        if not ohlcv:
            return []
        
        n = len(ohlcv)
        results = []
        
        for i in range(n):
            close = ohlcv[i]["close"]
            high = ohlcv[i]["high"]
            low = ohlcv[i]["low"]
            open_ = ohlcv[i]["open"]
            
            row = {
                "timestamp": ohlcv[i].get("timestamp", i),
                "symbol": ohlcv[i].get("symbol", "UNKNOWN"),
            }
            
            # --- Return features ---
            # ret_1: return 1 bar
            if i >= 1 and ohlcv[i-1]["close"] != 0:
                row["ret_1"] = (close / ohlcv[i-1]["close"]) - 1
            else:
                row["ret_1"] = 0.0
            
            # ret_5: return 5 bar
            if i >= 5 and ohlcv[i-5]["close"] != 0:
                row["ret_5"] = (close / ohlcv[i-5]["close"]) - 1
            else:
                row["ret_5"] = 0.0
            
            # ret_24: return 24 bar
            if i >= 24 and ohlcv[i-24]["close"] != 0:
                row["ret_24"] = (close / ohlcv[i-24]["close"]) - 1
            else:
                row["ret_24"] = 0.0
            
            # --- Range ---
            # range_pct: agresivitas candle
            if close != 0:
                row["range_pct"] = (high - low) / close
            else:
                row["range_pct"] = 0.0
            
            # --- Body ratio ---
            # body_ratio: conviction (body seberapa besar dari range penuh)
            body = abs(close - open_)
            candle_range = high - low
            if candle_range > 0:
                row["body_ratio"] = (body / candle_range)* 1.0
            else:
                row["body_ratio"] = 0.0
            
            # --- Higher High / Lower Low structure ---
            # hh_hl_structure: 1 = HH & HL (bullish), -1 = LH & LL (bearish), 0 = netral
            if i >= 2:
                higher_high = high > ohlcv[i-1]["high"] and high > ohlcv[i-2]["high"]
                higher_low = low > ohlcv[i-1]["low"] and low > ohlcv[i-2]["low"]
                lower_high = high < ohlcv[i-1]["high"] and high < ohlcv[i-2]["high"]
                lower_low = low < ohlcv[i-1]["low"] and low < ohlcv[i-2]["low"]
                
                if higher_high and higher_low:
                    row["hh_hl_structure"] = 1.0  # Bullish structure (HH+HL)
                elif lower_high and lower_low:
                    row["hh_hl_structure"] = -1.0  # Bearish structure (LH+LL)
                elif higher_high:
                    row["hh_hl_structure"] = 0.5  # Some bullish
                elif lower_low:
                    row["hh_hl_structure"] = -0.5  # Some bearish
                else:
                    row["hh_hl_structure"] = 0.0  # Netral
            else:
                row["hh_hl_structure"] = 0.0
            
            results.append(row)
        
        return results


# Quick test
if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("DOMAIN 1 — PRICE STRUCTURE TEST")
    print("=" * 60)
    
    random.seed(1)
    n = 30
    
    # Generate OHLCV data
    ohlcv = []
    price = 100.0
    for i in range(n):
        open_ = price
        close = price + random.uniform(-2, 2)
        high = max(open_, close) + random.uniform(0, 1.5)
        low = min(open_, close) - random.uniform(0, 1.5)
        vol = random.uniform(1000, 5000)
        ohlcv.append({
            "open": open_, "high": high, "low": low, "close": close,
            "volume": vol, "timestamp": i, "symbol": "BTCUSDT"
        })
        price = close
    
    calc = PriceStructureFeatures()
    features = calc.compute_all(ohlcv)
    
    # Tampilkan beberapa bar terakhir
    print("\nLast 3 feature rows:")
    for row in features[-3:]:
        print(f"  ts={row['timestamp']}: ret_1={row['ret_1']:.5f}, ret_5={row['ret_5']:.5f}, "
              f"ret_24={row['ret_24']:.5f}, range_pct={row['range_pct']:.5f}, "
              f"body_ratio={row['body_ratio']:.3f}, struct={row['hh_hl_structure']}")
    
    print("\n" + "=" * 60)
    print("✓ Domain 1 Price Structure Operational")
    print("=" * 60)
