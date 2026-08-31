#!/usr/bin/env python3
"""
Domain 6 - Liquidity Features
Penting untuk execution dan HFT.
Mengukur kedalaman pasar dan potential slippage.
"""
from typing import List, Dict, Any, Optional


class LiquidityFeatures:
    """
    DOMAIN 6 — LIQUIDITY
    
    Feature yang dihitung:
    - bid_ask_spread: ask - bid (raw & pct)
    - orderbook_imbalance: bid_volume / ask_volume
    - depth: total volume di top-N levels (potential slippage)
    
    Biasanya butuh orderbook data (bukan hanya OHLCV).
    Orderbook disediakan oleh Layer 1 (Market Data Gateway).
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        cfg = config or {}
        self.depth_levels = cfg.get("depth_levels", 10)
    
    def compute_from_orderbook(self, orderbook: Dict[str, Any]) -> Dict[str, float]:
        """
        Hitung liquidity features dari orderbook snapshot.
        
        Args:
            orderbook: Dict dengan:
                - "bids": List of [price, volume]
                - "asks": List of [price, volume]
                - "timestamp": int (optional)
                - "symbol": str (optional)
        """
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        row = {
            "timestamp": orderbook.get("timestamp", 0),
            "symbol": orderbook.get("symbol", "UNKNOWN"),
        }
        
        if not bids or not asks:
            # No orderbook data - return default
            row.update({
                "bid_ask_spread": 0.0,
                "spread_pct": 0.0,
                "orderbook_imbalance": 0.0,
                "bid_depth": 0.0,
                "ask_depth": 0.0,
            })
            return row
        
        # --- Bid-Ask Spread ---
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = best_ask - best_bid
        
        row["bid_ask_spread"] = spread
        # Spread sebagai % dari mid price
        mid = (best_bid + best_ask) / 2
        row["spread_pct"] = spread / mid if mid > 0 else 0.0
        
        # --- Bid-Ask Depth (top-N) ---
        n_levels = min(self.depth_levels, len(bids), len(asks))
        bid_vol = sum(b[1] for b in bids[:n_levels])
        ask_vol = sum(a[1] for a in asks[:n_levels])
        
        row["bid_depth"] = bid_vol
        row["ask_depth"] = ask_vol
        
        # --- Orderbook Imbalance ---
        if ask_vol > 0:
            row["orderbook_imbalance"] = bid_vol / ask_vol
        else:
            row["orderbook_imbalance"] = 0.0
        
        return row
    
    def compute_series(self, orderbooks: List[Dict]) -> List[Dict[str, float]]:
        """Hitung liquidity features untuk series orderbook snapshots."""
        return [self.compute_from_orderbook(ob) for ob in orderbooks]


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("DOMAIN 6 — LIQUIDITY TEST")
    print("=" * 60)
    
    # Contoh orderbook: bid load berat (buy pressure)
    orderbook_bullish = {
        "bids": [[100.0, 50], [99.5, 80], [99.0, 120], [98.5, 60], [98.0, 40]],
        "asks": [[100.5, 20], [101.0, 15], [101.5, 10], [102.0, 8], [102.5, 5]],
        "timestamp": 1000,
        "symbol": "BTCUSDT",
    }
    
    # Contoh orderbook: ask load berat (sell pressure)
    orderbook_bearish = {
        "bids": [[100.0, 20], [99.5, 15], [99.0, 10], [98.5, 8], [98.0, 5]],
        "asks": [[100.5, 50], [101.0, 80], [101.5, 120], [102.0, 60], [102.5, 40]],
        "timestamp": 2000,
        "symbol": "BTCUSDT",
    }
    
    calc = LiquidityFeatures({"depth_levels": 5})
    
    print("\nBullish orderbook:")
    f = calc.compute_from_orderbook(orderbook_bullish)
    print(f"  spread={f['bid_ask_spread']:.2f}, spread_pct={f['spread_pct']:.4%}")
    print(f"  imbalance={f['orderbook_imbalance']:.2f} (bid>ask = buy pressure), "
          f"bid_depth={f['bid_depth']:.0f}, ask_depth={f['ask_depth']:.0f}")
    
    print("\nBearish orderbook:")
    f2 = calc.compute_from_orderbook(orderbook_bearish)
    print(f"  imbalance={f2['orderbook_imbalance']:.2f} (ask>bid = sell pressure)")
    
    print("\n" + "=" * 60)
    print("✓ Domain 6 Liquidity Operational")
    print("=" * 60)
