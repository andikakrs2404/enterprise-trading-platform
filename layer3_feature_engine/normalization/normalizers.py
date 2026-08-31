#!/usr/bin/env python3
"""
Layer 3 - Normalization
Mengubah feature absolut menjadi asset-agnostic.

Kenapa penting:
ATR BTC = 0.5%, ATR DOGE = 2% → tidak bisa dibandingkan absolut.
BB Width < 0.02 untuk BTC ≠ untuk SUI.

Solusi: rolling percentile, rolling z-score, cross-sectional percentile.
"""
from typing import List, Dict, Any, Optional
import math


class RollingZScore:
    """Z-score dengan rolling window. Asset-agnostic."""
    
    def __init__(self, window: int = 100, min_samples: int = 20):
        self.window = window
        self.min_samples = min_samples
    
    def transform_series(self, values: List[float]) -> List[float]:
        """Transformasi series menjadi rolling z-score."""
        n = len(values)
        result = [0.0] * n
        for i in range(n):
            start = max(0, i - self.window + 1)
            window = values[start:i+1]
            if len(window) >= self.min_samples:
                mean = sum(window) / len(window)
                var = sum((x - mean)**2 for x in window) / len(window)
                std = math.sqrt(var)
                if std > 1e-12:
                    result[i] = (values[i] - mean) / std
                else:
                    result[i] = 0.0
            else:
                # Belum cukup data — WARMUP
                result[i] = 0.0
        return result
    
    def state_from_zscore(self, z: float) -> str:
        """State label dari z-score."""
        if z > 2.0:
            return "EXTREME_HIGH"
        elif z > 1.0:
            return "HIGH"
        elif z < -2.0:
            return "EXTREME_LOW"
        elif z < -1.0:
            return "LOW"
        else:
            return "NORMAL"


class RollingPercentile:
    """Percentile dengan rolling window. Asset-agnostic."""
    
    def __init__(self, window: int = 500, min_samples: int = 20):
        self.window = window
        self.min_samples = min_samples
    
    def transform_series(self, values: List[float]) -> List[float]:
        """Transformasi series menjadi rolling percentile (0-1)."""
        n = len(values)
        result = [0.5] * n
        for i in range(n):
            start = max(0, i - self.window + 1)
            window = values[start:i+1]
            if len(window) >= self.min_samples:
                count_less = sum(1 for v in window if v < values[i])
                result[i] = count_less / len(window)
            else:
                result[i] = 0.5  # default
        return result
    
    def state_from_percentile(self, p: float) -> str:
        """State label dari percentile (0-1)."""
        if p > 0.95:
            return "EXTREME_HIGH"
        elif p > 0.75:
            return "HIGH"
        elif p < 0.05:
            return "EXTREME_LOW"
        elif p < 0.25:
            return "LOW"
        else:
            return "NORMAL"


class CrossSectionalPercentile:
    """
    Percentile lintas aset pada waktu yang sama.
    Membandingkan satu aset terhadap universe pasar.
    
    Example:
    SOL volume_ratio = 3.2
    universe percentile = 97%
    → SOL paling ekstrem dibanding semua aset.
    """
    
    def transform_timestep(self, values_by_asset: Dict[str, float], target_asset: str) -> float:
        """
        Hitung percentile target_asset terhadap semua aset.
        
        Args:
            values_by_asset: {symbol: value} pada timestep yang sama
            target_asset: symbol yang dihitung percentilenya
            
        Returns:
            percentile 0-1
        """
        if target_asset not in values_by_asset:
            return 0.5
        target_val = values_by_asset[target_asset]
        all_values = list(values_by_asset.values())
        if len(all_values) < 2:
            return 0.5
        count_less = sum(1 for v in all_values if v < target_val)
        return count_less / len(all_values)


# Quick test
if __name__ == "__main__":
    import random
    random.seed(10)
    
    print("=" * 60)
    print("NORMALIZATION TEST — Asset-Agnostic")
    print("=" * 60)
    
    # Simulasi 2 aset dengan skala sangat berbeda
    # BTC atr_ratio ~0.5 - 0.9, DOGE ~0.02 - 0.1
    btc = [0.5 + random.random()*0.4 for _ in range(120)]
    doge = [0.02 + random.random()*0.08 for _ in range(120)]
    
    # Tapi keduanya bisa se-ekstrem dalam percentile
    zsc = RollingZScore(window=100, min_samples=30)
    pct = RollingPercentile(window=100, min_samples=30)
    
    btc_z = zsc.transform_series(btc)
    doge_z = zsc.transform_series(doge)
    btc_p = pct.transform_series(btc)
    doge_p = pct.transform_series(doge)
    
    print("\nNilai ABSOLUT sangat berbeda:")
    print(f"  BTC atr_ratio terakhir: {btc[-1]:.3f}")
    print(f"  DOGE atr_ratio terakhir: {doge[-1]:.3f}")
    print(f"  (tidak bisa dibandingkan langsung)")
    
    print("\nSetelah Z-score (asset-agnostic):")
    print(f"  BTC z-score last: {btc_z[-1]:.2f} ({zsc.state_from_zscore(btc_z[-1])})")
    print(f"  DOGE z-score last: {doge_z[-1]:.2f} ({zsc.state_from_zscore(doge_z[-1])})")
    
    print("\nSetelah Percentile:")
    print(f"  BTC percentile: {btc_p[-1]:.2f}")
    print(f"  DOGE percentile: {doge_p[-1]:.2f}")
    
    print("\n" + "=" * 60)
    print("✓ Normalization Operational — feature asset-agnostic")
    print("=" * 60)
