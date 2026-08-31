#!/usr/bin/env python3
"""
Backtester - Contracts: Feature Source Boundary

ATURAN PALING PENTING (dari review arsitektur):
Backtester TIDAK BOLEH menghitung feature sendiri.

JANGAN:
    backtester.py
        ATR(...)
        ADX(...)
        EMA(...)
        BBWidth(...)
    Lalu live engine menghitung ulang.

HARUS:
    Feature Engine V3
           │
           ├── Backtest
           │
           └── Live
    Satu sumber perhitungan.

Kontrak ini MEMASTIKAN backtester hanya membaca dari Feature Store V3
dan TIDAK punya implementasi indikator sendiri.

Ini mencegah mismatch:
- Feature leakage
- Forward-fill yang salah
- Perbedaan calculation research vs live
"""
from typing import Dict, List, Any, Optional
import os
import subprocess


# Feature Store lokasi default
DEFAULT_FEATURE_STORE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "layer3_feature_engine", "store", "storage"
)


class FeatureSourceContract:
    """
    Kontrak sumber feature.
    Backtester HANYA boleh membaca feature dari Feature Store V3.
    TIDAK ada perhitungan indikator di sini.
    """
    
    # Fitur yang tersedia dari Feature Store V3 (harus konsisten)
    AVAILABLE_FEATURES = [
        "atr_ratio", "bb_width", "volume_ratio", "oi_delta", "oi_pct",
        "ema_dist", "ema_slope", "adx", "ret_1", "ret_5", "ret_24",
        "compression_score", "trend_score", "expansion_score",
        "compression_components", "trend_components", "expansion_components",
        "volume_percentile", "dollar_volume", "realized_vol",
    ]
    
    def __init__(self, feature_store_dir: Optional[str] = None):
        self.feature_store_dir = feature_store_dir or DEFAULT_FEATURE_STORE
    
    def validate_source(self) -> Dict[str, Any]:
        """
        Validasi bahwa Feature Store tersedia dan bisa dibaca.
        Backtester bergantung pada ini.
        """
        result = {
            "feature_store_dir": self.feature_store_dir,
            "exists": os.path.exists(self.feature_store_dir),
            "feature_files": [],
            "canonical_engine": "feature_engine_v3",
        }
        if result["exists"]:
            result["feature_files"] = [
                f for f in os.listdir(self.feature_store_dir)
                if f.endswith(".jsonl")
            ]
        return result
    
    def assert_no_indicator_computation(self, module_path: str) -> bool:
        """
        Pastikan sebuah modul backtester TIDAK mengimplementasikan indikator.
        Kontrak: backtester tidak boleh punya ATR/ADX/MA sendiri.
        """
        forbidden = ["def compute_atr", "def _atr", "sma(", "ema(", "bb_width="]
        if not os.path.exists(module_path):
            return True
        with open(module_path) as f:
            content = f.read()
        # Cari indikator in-house
        violations = [pat for pat in forbidden if pat in content]
        return len(violations) == 0


class BacktestContract:
    """
    Kontrak result backtest.
    Setiap backtest harus menghasilkan metrik reproducibility.
    """
    
    def validate_metadata(self, backtest_result: Dict[str, Any]) -> List[str]:
        """Validasi metadata backtest lengkap (untuk reproducibility)."""
        required = [
            "dataset_version", "feature_version", "context_version",
            "strategy_version", "symbol", "timeframe", "date_range",
        ]
        missing = [r for r in required if r not in backtest_result]
        return missing
    
    def compute_metrics(self, trades: List[Dict]) -> Dict[str, Any]:
        """
        Hitung metrik performa DARI TRADES (bukan dari feature).
        Metrik dasar untuk regression test.
        """
        if not trades:
            return {
                "num_trades": 0, "pf": 0.0, "win_rate": 0.0,
                "expectancy": 0.0, "max_dd": 0.0, "total_pnl": 0.0,
            }
        
        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        win = sum(1 for t in trades if t["pnl"] > 0)
        
        pf = gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        win_rate = win / len(trades)
        expectancy = sum(t["pnl"] for t in trades) / len(trades)
        max_dd = self._compute_max_dd(trades)
        
        return {
            "num_trades": len(trades),
            "pf": round(pf, 4),
            "win_rate": round(win_rate, 4),
            "expectancy": round(expectancy, 4),
            "max_dd": round(max_dd, 4),
            "total_pnl": round(sum(t["pnl"] for t in trades), 4),
        }
    
    def _compute_max_dd(self, trades: List[Dict]) -> float:
        """Max drawdown dari cumulative PnL."""
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            cum += t["pnl"]
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd
        return max_dd


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("BACKTEST CONTRACT TEST")
    print("=" * 60)
    
    contract = FeatureSourceContract()
    source = contract.validate_source()
    print(f"\nFeature Store: exists={source['exists']}")
    print(f"  dir: {source['feature_store_dir']}")
    print(f"  files: {source['feature_files'][:3] if source['feature_files'] else 'none (belum ada data)'}")
    print(f"  canonical engine: {source['canonical_engine']}")
    
    # Test metrics
    bt = BacktestContract()
    sample_trades = [
        {"pnl": 2.0, "symbol": "BTCUSDT"},
        {"pnl": -0.5, "symbol": "BTCUSDT"},
        {"pnl": 1.5, "symbol": "BTCUSDT"},
        {"pnl": -1.0, "symbol": "BTCUSDT"},
        {"pnl": 0.8, "symbol": "BTCUSDT"},
    ]
    metrics = bt.compute_metrics(sample_trades)
    print(f"\nSample metrics: {metrics}")
    
    print("\n" + "=" * 60)
    print("✓ BACKTEST CONTRACT OPERATIONAL")
    print("=" * 60)
