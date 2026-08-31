#!/usr/bin/env python3
"""
Domain 5 - Trend Features
Menjawab: "Arah dominan?"
Lebih penting daripada 200 indikator yang saling berkorelasi.
"""
from typing import List, Dict, Any, Optional
import math


class TrendFeatures:
    """
    DOMAIN 5 — TREND
    
    Feature yang dihitung:
    - ema_dist: (close - ema50) / ema50 — jauh lebih informatif
      daripada EMA crossover
    - ema_slope: ema50 - ema50_prev — kemiringan trend
    - adx: kekuatan trend (bukan arah)
    - regression_slope: slope dari linear regression (matematis)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.ema_period = cfg.get("ema_period", 50)
        self.adx_period = cfg.get("adx_period", 14)
        self.regression_window = cfg.get("regression_window", 20)
    
    def compute_all(self, closes: List[float], highs: List[float] = None,
                    lows: List[float] = None, timestamps: List = None) -> List[Dict[str, float]]:
        """Hitung semua feature trend dari close prices."""
        if not closes:
            return []
        
        n = len(closes)
        ema = self._compute_ema(closes, self.ema_period)
        
        # ADX (jika highs/lows tersedia)
        adx_series = self._compute_adx(closes, highs or closes, lows or closes, self.adx_period) if highs and lows else [0.0]*n
        
        results = []
        for i in range(n):
            close = closes[i]
            row = {
                "timestamp": timestamps[i] if timestamps and i < len(timestamps) else i,
            }
            
            # --- EMA Distance ---
            # (close - ema50)/ema50 — distance dari mean
            if ema[i] > 0:
                row["ema_dist"] = (close - ema[i]) / ema[i]
            else:
                row["ema_dist"] = 0.0
            
            # --- EMA Slope ---
            if i >= 1:
                row["ema_slope"] = ema[i] - ema[i-1]
            else:
                row["ema_slope"] = 0.0
            
            # --- ADX (kekuatan trend) ---
            row["adx"] = adx_series[i]
            
            # --- Regression Slope ---
            if i >= self.regression_window:
                window = closes[i-self.regression_window+1:i+1]
                row["regression_slope"] = self._lin_reg_slope(window)
            else:
                window = closes[:i+1]
                row["regression_slope"] = self._lin_reg_slope(window) if len(window) >= 3 else 0.0
            
            results.append(row)
        
        return results
    
    def _compute_ema(self, data: List[float], period: int) -> List[float]:
        """Exponential Moving Average."""
        n = len(data)
        if n == 0:
            return []
        k = 2 / (period + 1)
        ema = [0.0] * n
        # Seed dengan SMA pertama
        if n >= period:
            ema[period-1] = sum(data[:period]) / period
            for i in range(period, n):
                ema[i] = data[i] * k + ema[i-1] * (1 - k)
        else:
            ema[0] = data[0]
            for i in range(1, n):
                ema[i] = data[i] * k + ema[i-1] * (1 - k)
        return ema
    
    def _compute_adx(self, closes, highs, lows, period):
        """Average Directional Index (Wilder)."""
        n = len(closes)
        if n < period * 2:
            return [0.0] * n
        tr = [0.0] * n
        plus_dm = [0.0] * n
        minus_dm = [0.0] * n
        for i in range(1, n):
            hd = highs[i] - highs[i-1]
            ld = lows[i-1] - lows[i]
            tr[i] = max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
            plus_dm[i] = hd if (hd > ld and hd > 0) else 0.0
            minus_dm[i] = ld if (ld > hd and ld > 0) else 0.0
        adx = [0.0] * n
        # Wilder smoothing
        tr_sum = sum(tr[1:period+1])
        plus_sum = sum(plus_dm[1:period+1])
        minus_sum = sum(minus_dm[1:period+1])
        if tr_sum == 0:
            return adx
        dx_list = []
        for i in range(period+1, n):
            tr_sum = tr_sum - (tr_sum/period) + tr[i]
            plus_sum = plus_sum - (plus_sum/period) + plus_dm[i]
            minus_sum = minus_sum - (minus_sum/period) + minus_dm[i]
            if tr_sum > 0:
                pdi = 100 * (plus_sum/tr_sum)
                mdi = 100 * (minus_sum/tr_sum)
                s = pdi + mdi
                dx_list.append(100 * abs(pdi-mdi)/s if s > 0 else 0.0)
            else:
                dx_list.append(0.0)
        # ADX = average of DX
        if len(dx_list) >= period:
            idx = period + period
            if idx < n:
                adx[idx] = sum(dx_list[:period]) / period
                for k in range(period, len(dx_list)):
                    j = idx + k - period + 1
                    if j < n:
                        prev = adx[j-1] if j > 0 else 0.0
                        adx[j] = (prev * (period-1) + dx_list[k]) / period
        return adx
    
    def _lin_reg_slope(self, data: List[float]) -> float:
        """Slope dari simple linear regression y = ax + b."""
        n = len(data)
        if n < 2:
            return 0.0
        x_mean = (n-1)/2.0
        y_mean = sum(data)/n
        num = 0.0
        den = 0.0
        for i, y in enumerate(data):
            num += (i - x_mean) * (y - y_mean)
            den += (i - x_mean) ** 2
        return num / den if den != 0 else 0.0


# Quick test
if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("DOMAIN 5 — TREND TEST")
    print("=" * 60)
    
    random.seed(5)
    n = 80
    
    # Uptrend di awal, downtrend di akhir
    closes = []
    price = 100.0
    for i in range(n):
        if i < 40:
            price += 0.5 + random.uniform(-0.2, 0.2)  # uptrend
        else:
            price -= 0.4 + random.uniform(-0.2, 0.2)  # downtrend
        closes.append(price)
    
    highs = [c + random.uniform(0.2, 1) for c in closes]
    lows = [c - random.uniform(0.2, 1) for c in closes]
    
    calc = TrendFeatures()
    features = calc.compute_all(closes, highs, lows)
    
    print("\nPerbandingan trend phase:")
    print(f"  Uptrend (bar 35):  ema_dist={features[35]['ema_dist']:.4f}, slope={features[35]['ema_slope']:.3f}, adx={features[35]['adx']:.1f}")
    print(f"  Downtrend (bar 70): ema_dist={features[70]['ema_dist']:.4f}, slope={features[70]['ema_slope']:.3f}, adx={features[70]['adx']:.1f}")
    print(f"  Regression slope awal: {features[35]['regression_slope']:.3f}, akhir: {features[70]['regression_slope']:.3f}")
    
    print("\n" + "=" * 60)
    print("✓ Domain 5 Trend Operational")
    print("=" * 60)
