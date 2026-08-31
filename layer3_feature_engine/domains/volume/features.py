#!/usr/bin/env python3
"""
Domain 3 - Volume Features
Menjawab: "Apakah ada partisipasi?"
"""
from typing import List, Dict, Any, Optional


class VolumeFeatures:
    """
    DOMAIN 3 — VOLUME
    
    Feature yang dihitung:
    - volume_ratio: volume / volume_ma20 (wajib!)
      3.0 = volume 3x normal
    - dollar_volume: volume * close (lebih penting dari volume biasa)
      100 BTC != 100 DOGE
    - volume_percentile: volume saat ini > berapa % dari historical
      Lebih stabil daripada volume_ratio
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.volume_ma_period = cfg.get("volume_ma_period", 20)
        self.volume_percentile_window = cfg.get("volume_percentile_window", 500)
    
    def compute_all(self, ohlcv: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """Hitung semua feature volume."""
        if not ohlcv:
            return []
        
        n = len(ohlcv)
        results = []
        
        for i in range(n):
            close = ohlcv[i]["close"]
            volume = ohlcv[i]["volume"]
            
            row = {
                "timestamp": ohlcv[i].get("timestamp", i),
                "symbol": ohlcv[i].get("symbol", "UNKNOWN"),
            }
            
            # --- Volume Ratio ---
            # volume / MA(window)
            if i >= self.volume_ma_period:
                window_vol = [d["volume"] for d in ohlcv[i-self.volume_ma_period+1:i+1]]
                ma_vol = sum(window_vol) / self.volume_ma_period
                row["volume_ratio"] = volume / ma_vol if ma_vol > 0 else 0.0
            else:
                # Partial window
                window_vol = [d["volume"] for d in ohlcv[:i+1]]
                ma_vol = sum(window_vol) / len(window_vol) if window_vol else 0
                row["volume_ratio"] = volume / ma_vol if ma_vol > 0 else 0.0
            
            # --- Dollar Volume ---
            # volume * close
            row["dollar_volume"] = volume * close
            
            # --- Volume Percentile ---
            # Volume saat ini lebih tinggi dari X% historical
            if i >= 1:
                # Ambil window history (sebelum bar ini)
                start = max(0, i - self.volume_percentile_window)
                historical_vols = [d["volume"] for d in ohlcv[start:i]]
                if historical_vols:
                    # Hitung percent rank: % dari historical yang < current volume
                    count_less = sum(1 for v in historical_vols if v < volume)
                    row["volume_percentile"] = count_less / len(historical_vols)
                else:
                    row["volume_percentile"] = 0.5
            else:
                row["volume_percentile"] = 0.5
            
            results.append(row)
        
        return results


# Quick test
if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("DOMAIN 3 — VOLUME TEST")
    print("=" * 60)
    
    random.seed(3)
    n = 60
    ohlcv = []
    price = 100.0
    for i in range(n):
        close = price + random.uniform(-1, 1)
        # Spike volume di beberapa titik
        base_vol = 2000
        if i in [30, 45]:
            vol = base_vol * 4  # 4x spike
        elif i in [20, 35]:
            vol = base_vol * 2.5
        else:
            vol = base_vol + random.uniform(-500, 500)
        ohlcv.append({"open": price, "high": close + 1, "low": close - 1,
                      "close": close, "volume": vol, "timestamp": i, "symbol": "BTCUSDT"})
        price = close
    
    calc = VolumeFeatures()
    features = calc.compute_all(ohlcv)
    
    print("\nVolume Ratio mengidentifikasi spike volume:")
    for i in [19, 20, 29, 30, 35, 44, 45]:
        f = features[i]
        flag = " ⚡SPIKE" if f['volume_ratio'] > 2 else ""
        print(f"  bar {i}: vol_ratio={f['volume_ratio']:.2f}, percentile={f['volume_percentile']:.0%}, "
              f"$vol={f['dollar_volume']/1e6:.1f}M{flag}")
    
    print("\n" + "=" * 60)
    print("✓ Domain 3 Volume Operational")
    print("=" * 60)
