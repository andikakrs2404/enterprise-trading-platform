#!/usr/bin/env python3
"""
Layer 3 - Financial Indicators (Pure Python)
Implementasi indikator teknis utama yang dipakai feature engine:
- ATR (Average True Range)
- ADX (Average Directional Index)
- BB Width (Bollinger Band Width)
- VWAP Distance
- OI Delta
- Funding Delta
"""
from typing import List, Dict, Any, Optional, Tuple


class Indicators:
    """Collection stateless indikator teknis - pure Python, tanpa dependency eksternal."""
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """
        Average True Range.
        TRUE RANGE = max(high-low, |high-prev_close|, |low-prev_close|)
        ATR = SMA dari true range selama `period`.
        
        Args:
            highs: List harga tertinggi
            lows: List harga terendah
            closes: List harga penutupan
            period: Periode ATR (default 14)
            
        Returns:
            List nilai ATR - Panjang sama dengan input (prefix diisi 0)
        """
        n = len(highs)
        if n < 2:
            return [0.0] * n
        
        true_ranges = [0.0]
        for i in range(1, n):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        # SMA dari true ranges
        atr_values = [0.0] * n
        for i in range(period, n):
            atr_values[i] = sum(true_ranges[i-period+1:i+1]) / period
        
        return atr_values
    
    @staticmethod
    def adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[float]:
        """
        Average Directional Index.
        Mengukur kekuatan trend (0-100). ADX > 30 = trending kuat.
        
        Returns:
            List nilai ADX - Panjang sama dengan input (prefix diisi 0)
        """
        n = len(highs)
        if n < period * 2:
            return [0.0] * n
        
        # True Range, +DM, -DM
        tr = [0.0] * n
        plus_dm = [0.0] * n
        minus_dm = [0.0] * n
        
        for i in range(1, n):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]
            
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            
            plus_dm[i] = high_diff if (high_diff > low_diff and high_diff > 0) else 0.0
            minus_dm[i] = low_diff if (low_diff > high_diff and low_diff > 0) else 0.0
        
        # Smoothed values (Wilder)
        adx_values = [0.0] * n
        tr_sum = sum(tr[1:period+1])
        plus_sum = sum(plus_dm[1:period+1])
        minus_sum = sum(minus_dm[1:period+1])
        
        dx_values = []
        for i in range(period+1, n):
            tr_sum = tr_sum - (tr_sum / period) + tr[i]
            plus_sum = plus_sum - (plus_sum / period) + plus_dm[i]
            minus_sum = minus_sum - (minus_sum / period) + minus_dm[i]
            
            if tr_sum > 0:
                plus_di = 100 * (plus_sum / tr_sum)
                minus_di = 100 * (minus_sum / tr_sum)
                di_sum = plus_di + minus_di
                if di_sum > 0:
                    dx = 100 * abs(plus_di - minus_di) / di_sum
                    dx_values.append(dx)
                else:
                    dx_values.append(0.0)
            else:
                dx_values.append(0.0)
        
        # AVERAGE DX
        if len(dx_values) >= period:
            adx_start_idx = period + 1 + period
            if adx_start_idx < n:
                adx_values[adx_start_idx-1] = sum(dx_values[:period]) / period
                for i in range(period, len(dx_values)):
                    idx = adx_start_idx - 1 + i - (period - 1)
                    if idx < n:
                        # Wilder smoothing
                        prev_adx = adx_values[idx-1] if idx > 0 else 0.0
                        adx_values[idx] = (prev_adx * (period - 1) + dx_values[i]) / period
        
        return adx_values
    
    @staticmethod
    def bollinger_bands(closes: List[float], period: int = 20, num_std: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
        """
        Bollinger Bands: SMA, Upper, Lower.
        
        Returns:
            Tuple (middle, upper, lower) - masing-masing list
        """
        n = len(closes)
        middle = [0.0] * n
        upper = [0.0] * n
        lower = [0.0] * n
        
        for i in range(period-1, n):
            window = closes[i-period+1:i+1]
            sma = sum(window) / period
            # Population std
            variance = sum((x - sma) ** 2 for x in window) / period
            std = variance ** 0.5
            middle[i] = sma
            upper[i] = sma + num_std * std
            lower[i] = sma - num_std * std
        
        return middle, upper, lower
    
    @staticmethod
    def bb_width(closes: List[float], period: int = 20, num_std: float = 2.0) -> List[float]:
        """
        Bollinger Band Width.
        bb_width = (upper - lower) / middle
        
        Berguna untuk deteksi compression/expansion:
        - bb_width kecil (< 0.03) = COMPRESSION
        - bb_width membesar = VOLATILITY_EXPANSION
        """
        middle, upper, lower = Indicators.bollinger_bands(closes, period, num_std)
        width = [0.0] * len(closes)
        for i in range(len(closes)):
            if middle[i] != 0:
                width[i] = (upper[i] - lower[i]) / middle[i]
        return width
    
    @staticmethod
    def vwap_distance(closes: List[float], volumes: List[float], period: int = 20) -> List[float]:
        """
        Jarak harga dari VWAP (Volume Weighted Average Price).
        vwap_return = (price - vwap) / vwap
        
        Positif = price di atas VWAP (bullish), negatif = di bawah (bearish).
        """
        n = len(closes)
        distances = [0.0] * n
        
        for i in range(min(period, n)):
            start = 0
            window_c = closes[start:i+1]
            window_v = volumes[start:i+1]
            total_vol = sum(window_v)
            if total_vol > 0:
                vwap = sum(c * v for c, v in zip(window_c, window_v)) / total_vol
                if vwap != 0:
                    distances[i] = (closes[i] - vwap) / vwap
        
        for i in range(period, n):
            window_c = closes[i-period+1:i+1]
            window_v = volumes[i-period+1:i+1]
            total_vol = sum(window_v)
            if total_vol > 0:
                vwap = sum(c * v for c, v in zip(window_c, window_v)) / total_vol
                if vwap != 0:
                    distances[i] = (closes[i] - vwap) / vwap
        
        return distances
    
    @staticmethod
    def oi_delta(open_interest: List[float], period: int = 1) -> List[float]:
        """
        Open Interest Delta (perubahan OI).
        OI naik = posisi baru dibuka, OI turun = posisi ditutup.
        """
        n = len(open_interest)
        deltas = [0.0] * n
        for i in range(period, n):
            deltas[i] = open_interest[i] - open_interest[i-period]
        return deltas
    
    @staticmethod
    def funding_delta(funding_rates: List[float], period: int = 1) -> List[float]:
        """Funding Rate Delta (perubahan funding rate)."""
        n = len(funding_rates)
        deltas = [0.0] * n
        for i in range(period, n):
            deltas[i] = funding_rates[i] - funding_rates[i-period]
        return deltas
    
    @staticmethod
    def volume_ratio(volumes: List[float], period: int = 20) -> List[float]:
        """
        Volume Ratio = volume / volume_ma20
        Ratio > 1 = volume di atas rata-rata (unusual activity).
        Ratio > 2-3 = sangat tinggi (sering jadi trigger breakout).
        """
        n = len(volumes)
        ratios = [0.0] * n
        for i in range(min(period, n)):
            window = volumes[:i+1]
            ma = sum(window) / len(window) if window else 0
            ratios[i] = volumes[i] / ma if ma > 0 else 0.0
        for i in range(period, n):
            window = volumes[i-period+1:i+1]
            ma = sum(window) / period
            ratios[i] = volumes[i] / ma if ma > 0 else 0.0
        return ratios


# Quick test
if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("INDICATORS MODULE TEST")
    print("=" * 60)
    
    # Generate sample data
    random.seed(42)
    n = 60
    closes = []
    price = 100.0
    for i in range(n):
        price += random.uniform(-1.5, 1.5)
        closes.append(price)
    
    highs = [c + random.uniform(0.2, 1.0) for c in closes]
    lows = [c - random.uniform(0.2, 1.0) for c in closes]
    volumes = [random.uniform(1000, 5000) for _ in range(n)]
    
    # Test ATR
    atr_values = Indicators.atr(highs, lows, closes, period=14)
    print(f"\nATR (14): last={atr_values[-1]:.4f}, mean_nz={sum(atr_values)/n:.4f}")
    
    # Test ADX
    adx_values = Indicators.adx(highs, lows, closes, period=14)
    print(f"ADX (14): last={adx_values[-1]:.4f}")
    
    # Test BB
    middle, upper, lower = Indicators.bollinger_bands(closes, period=20)
    print(f"BB: last upper={upper[-1]:.2f}, mid={middle[-1]:.2f}, lower={lower[-1]:.2f}")
    
    # Test BB Width
    bbw = Indicators.bb_width(closes, period=20)
    print(f"BB Width: last={bbw[-1]:.6f}")
    
    # Test VWAP Distance
    vwap_dist = Indicators.vwap_distance(closes, volumes, period=20)
    print(f"VWAP Distance: last={vwap_dist[-1]:.6f}")
    
    # Test OI Delta
    oi = [5000 + random.uniform(-50, 50) for _ in range(n)]
    oi_d = Indicators.oi_delta(oi, period=1)
    print(f"OI Delta: last={oi_d[-1]:.2f}")
    
    # Test Volume Ratio
    vol_ratio = Indicators.volume_ratio(volumes, period=20)
    print(f"Volume Ratio: last={vol_ratio[-1]:.4f}")
    
    print("\n" + "=" * 60)
    print("✓ Indicators Module Operational")
    print("=" * 60)
