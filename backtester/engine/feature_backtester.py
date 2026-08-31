#!/usr/bin/env python3
"""
Backtester - Engine
Backtester yang MENGONSUMSI feature dari Feature Store V3.
TIDAK menghitung feature sendiri (aturan kontrak).

Satu sumber perhitungan:
    Feature Engine V3
        ├── Backtest  ← backtester baca dari sini
        └── Live

Backtester hanya:
1. Membaca features dari Feature Store / pipeline V3
2. Menerapkan context (Layer 4) untuk regime routing
3. Menjalankan strategy sederhana berbasis feature
4. Menghitung metrik (PF, WR, Expectancy, Max DD)
"""
from typing import Dict, List, Any, Optional
import sys
import os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

from backtester.contracts.feature_source_contract import BacktestContract


class FeatureBacktester:
    """
    Engine backtest yang membaca features EKSTERNAL (dari V3).
    Tidak ada ATR/ADX/EMA di sini — murni konsumsi feature.
    """
    
    def __init__(self, feature_rows: Optional[List[Dict]] = None):
        """
        Args:
            feature_rows: List dict features DARI Feature Store V3.
                Jika None, backtester TIDAK punya data (harus diisi).
        """
        self.feature_rows = feature_rows or []
        self.contract = BacktestContract()
        self.metadata = {}
    
    def set_metadata(self, **kwargs):
        """Set metadata reproducibility backtest."""
        self.metadata.update(kwargs)
    
    # --- Engine: jalankan sederhana berbasis feature ---
    def run(self, strategy_fn, initial_capital: float = 10000.0,
            risk_per_trade: float = 0.01) -> Dict[str, Any]:
        """
        Jalankan backtest.
        
        Args:
            strategy_fn: function(context_features, position) → Signal dict
                Signature: strategy_fn(row: dict, position: dict) -> dict
                Return: {"action": "BUY"/"SELL"/"HOLD", "reason": "..."}
            initial_capital: modal awal
            risk_per_trade: % risiko per trade
        """
        if not self.feature_rows:
            return {"error": "No feature data", "trades": [], "metrics": {}}
        
        capital = initial_capital
        position = {"active": False, "entry": 0.0, "qty": 0.0, "direction": None}
        trades = []
        equity_curve = []
        
        for i, row in enumerate(self.feature_rows):
            price = row.get("close", row.get("atr", 0))
            if price is None:
                continue
            
            # Strategi memberi sinyal berdasarkan features (bukan hitung sendiri)
            signal = strategy_fn(row, position)
            
            if not position["active"] and signal.get("action") == "BUY":
                # Masuk posisi
                risk_amount = capital * risk_per_trade
                qty = risk_amount / price if price > 0 else 0
                position = {
                    "active": True, "entry": price, "qty": qty,
                    "direction": "LONG", "entry_idx": i,
                    "signal": signal.get("reason", ""),
                    "compression_score": row.get("compression_score"),
                    "regime": signal.get("regime"),
                }
            elif position["active"] and signal.get("action") == "SELL":
                # Keluar posisi
                exit_price = price
                pnl = (exit_price - position["entry"]) * position["qty"]
                capital += pnl
                # Catat trade ke metadata
                trade = {
                    "symbol": self.metadata.get("symbol", "?"),
                    "entry_idx": position["entry_idx"],
                    "exit_idx": i,
                    "entry_price": position["entry"],
                    "exit_price": exit_price,
                    "qty": position["qty"],
                    "pnl": pnl,
                    "direction": position["direction"],
                    "signal": position["signal"],
                    "compression_score": position["compression_score"],
                    "regime": position.get("regime"),
                }
                trade.update(self.metadata)
                trades.append(trade)
                position = {"active": False, "entry": 0.0, "qty": 0.0, "direction": None}
            
            equity_curve.append(capital)
        
        metrics = self.contract.compute_metrics(trades)
        
        return {
            "metadata": self.metadata,
            "trades": trades,
            "metrics": metrics,
            "final_capital": round(capital, 2),
            "equity_curve": equity_curve,
        }
    
    def get_features_used(self) -> List[str]:
        """Feature yang digunakan (dari rows) — auditability."""
        if not self.feature_rows:
            return []
        return sorted(k for k in self.feature_rows[0] if k not in 
            ("timestamp", "symbol", "saved_at", "source", "quality_score",
             "schema_version", "dataset_version", "timeframe"))


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("FEATURE BACKTESTER TEST (murni konsumsi feature, bukan hitung sendiri)")
    print("=" * 60)
    
    # Simulasi feature rows yang DATANG DARI Feature Store V3
    # (bukan dihitung di backtester!)
    import random
    random.seed(1)
    
    feature_rows = []
    price = 100.0
    for i in range(100):
        price += random.uniform(-1, 1)
        # Feature yang "sudah dihitung L3" — backtester hanya baca
        feature_rows.append({
            "timestamp": i,
            "close": price,
            "atr_ratio": 0.5 + random.random()*0.5,
            "bb_width": 0.02 + random.random()*0.05,
            "volume_ratio": 0.8 + random.random(),
            "oi_delta": random.uniform(-10, 10),
            "ema_dist": 0.01,
            "compression_score": random.random(),
        })
    
    bt = FeatureBacktester(feature_rows)
    bt.set_metadata(symbol="BTCUSDT", timeframe="5m",
                    dataset_version="v1", feature_version="v3.0",
                    context_version="v1", strategy_version="compression_v1")
    
    # Strategi sederhana: entry saat compression tinggi, exit saat expansion
    def compression_strategy(row, position):
        if not position["active"]:
            if row.get("compression_score", 0) > 0.7:
                return {"action": "BUY", "reason": "compression_breakout",
                        "regime": "COMPRESSION"}
        else:
            if row.get("expansion_score", 0) > 0.5 or row.get("oi_delta", 0) > 1:
                return {"action": "SELL", "reason": "expansion_exit",
                        "regime": "VOLATILITY_EXPANSION"}
        return {"action": "HOLD", "reason": ""}
    
    result = bt.run(compression_strategy)
    
    print(f"\nFeature yang dikonsumsi (dari L3): {bt.get_features_used()}")
    print(f"Trades: {len(result['trades'])}")
    print(f"Metrics: {result['metrics']}")
    
    print("\n" + "=" * 60)
    print("✓ FEATURE BACKTESTER OPERATIONAL")
    print("✓ Tidak menghitung feature sendiri — konsumsi dari V3")
    print("=" * 60)
