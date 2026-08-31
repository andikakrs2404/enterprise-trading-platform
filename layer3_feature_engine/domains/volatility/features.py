#!/usr/bin/env python3
"""
Domain 2 - Volatility Features
INi domain PALING PENTING untuk crypto futures.
Banyak edge lahir dari perubahan volatilitas.
"""
from typing import List, Dict, Any, Optional


class VolatilityFeatures:
    """
    DOMAIN 2 — VOLATILITY
    
    Feature yang dihitung:
    - atr: ATR(14) — volatilitas absolut
    - atr_ratio: ATR(14)/ATR(100) — RELATIVE volatility (kunci!)
      > 1.5 = volatility expansion
      < 0.7 = compression
    - bb_width: (upper-lower)/middle — compression indicator inti
    - realized_vol: std(log_return) — lebih kuat dari ATR
    
    INI ADALAH DOMAIN YANG MENGHASILKAN EDGE.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.atr_period = cfg.get("atr_period", 14)
        self.atr_long_period = cfg.get("atr_long_period", 100)
        self.bb_period = cfg.get("bb_period", 20)
        self.bb_std = cfg.get("bb_std", 2.0)
        self.realized_vol_window = cfg.get("realized_vol_window", 14)
    
    def compute_all(self, ohlcv: List[Dict[str, float]]) -> List[Dict[str, float]]:
        """Hitung semua feature volatility."""
        if not ohlcv:
            return []
        
        n = len(ohlcv)
        closes = [d["close"] for d in ohlcv]
        highs = [d["high"] for d in ohlcv]
        lows = [d["low"] for d in ohlcv]
        
        # --- ATR series ---
        atr_series = self._compute_atr(highs, lows, closes, self.atr_period)
        atr_long_series = self._compute_atr(highs, lows, closes, self.atr_long_period)
        
        # --- Realized vol (std of log returns) ---
        log_returns = []
        for i in range(1, n):
            if closes[i-1] > 0 and closes[i] > 0:
                log_returns.append(__import__('math').log(closes[i] / closes[i-1]))
            else:
                log_returns.append(0.0)
        log_returns = [0.0] + log_returns  # align index
        
        results = []
        for i in range(n):
            close = closes[i]
            row = {
                "timestamp": ohlcv[i].get("timestamp", i),
                "symbol": ohlcv[i].get("symbol", "UNKNOWN"),
            }
            
            # ATR
            row["atr"] = atr_series[i]
            
            # ATR Ratio — RELATIVE VOLATILITY (KUNCI EDGE)
            if atr_long_series[i] > 0 and atr_long_series[i] < float('inf'):
                row["atr_ratio"] = atr_series[i] / atr_long_series[i]
            else:
                row["atr_ratio"] = 0.0
            
            # BB Width
            if i >= self.bb_period - 1:
                window = closes[i-self.bb_period+1:i+1]
                sma = sum(window) / self.bb_period
                variance = sum((x - sma)**2 for x in window) / self.bb_period
                std = variance ** 0.5
                upper = sma + self.bb_std * std
                lower = sma - self.bb_std * std
                if sma > 0:
                    row["bb_width"] = (upper - lower) / sma
                else:
                    row["bb_width"] = 0.0
            else:
                row["bb_width"] = 0.0
            
            # Realized Volatility (annualized-ish / per bar)
            if i >= self.realized_vol_window:
                window_log = log_returns[i-self.realized_vol_window+1:i+1]
                mean_lr = sum(window_log) / self.realized_vol_window
                variance = sum((x - mean_lr)**2 for x in window_log) / self.realized_vol_window
                row["realized_vol"] = variance ** 0.5
            else:
                row["realized_vol"] = 0.0
            
            results.append(row)
        
        return results
    
    def _compute_atr(self, highs, lows, closes, period):
        """Compute Average True Range tinja-Wilder style."""
        n = len(highs)
        atr = [0.0] * n
        if n < 2:
            return atr
        
        tr = [0.0] * n
        for i in range(1, n):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
        
        # ATR period pertama = simple average
        if n > period:
            atr[period] = sum(tr[1:period+1]) / period
            # Wilder smoothing selanjutnya
            for i in range(period+1, n):
                atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        return atr


# Quick test
if __name__ == "__main__":
    import random
    import math
    
    print("=" * 60)
    print("DOMAIN 2 — VOLATILITY TEST")
    print("=" * 60)
    
    random.seed(2)
    n = 120
    ohlcv = []
    price = 100.0
    for i in range(n):
        # Simulasi: makin kecil volatilitas di akhir (compression)
        vol_scale = 1.0 if i < 80 else 0.3
        open_ = price
        close = price + random.uniform(-1, 1) * vol_scale
        high = max(open_, close) + random.uniform(0, 0.7) * vol_scale
        low = min(open_, close) - random.uniform(0, 0.7) * vol_scale
        ohlcv.append({"open": open_, "high": high, "low": low, "close": close,
                      "volume": random.uniform(1000, 5000), "timestamp": i, "symbol": "BTCUSDT"})
        price = close
    
    calc = VolatilityFeatures()
    features = calc.compute_all(ohlcv)
    
    # Bandingkan ATR ratio di fase normal vs kompresi
    print("\nATR Ratio comparison:")
    print(f"  Early (normal):   atr_ratio={features[60]['atr_ratio']:.3f}, bb_width={features[60]['bb_width']:.4f}")
    print(f"  Late (compression): atr_ratio={features[-5]['atr_ratio']:.3f}, bb_width={features[-5]['bb_width']:.4f}")
    print(f"  Realized vol early: {features[60]['realized_vol']:.5f}, late: {features[-5]['realized_vol']:.5f}")
    
    print("\nInterpretasi (compression detection):")
    if features[-5]['atr_ratio'] < 0.7:
        print("  ✅ COMPRESSION terdeteksi (atr_ratio < 0.7)")
    else:
        print(f"  atr_ratio={features[-5]['atr_ratio']:.3f} (belum < 0.7)")
    
    print("\n" + "=" * 60)
    print("✓ Domain 2 Volatility Operational")
    print("=" * 60)
