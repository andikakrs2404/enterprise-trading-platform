#!/usr/bin/env python3
"""
Backtester - Regression Test (P0)
Menyimpan baseline dan mendeteksi perubahan materiil.

Baseline:
Dataset: v1
Feature: v3.0
Context: v1
Strategy: compression_v1
Hasil: Trades, PF, WR, Expectancy, Max DD

Setiap perubahan code harus bisa dibandingkan:
    OLD vs NEW

Kalau PF berubah:
    PF 2.31 → 1.42
Sistem HARUS memberi tahu:
    "Feature/logic change materially changed strategy behavior"
"""
from typing import Dict, List, Any, Optional
import json
import os
import hashlib


# Lokasi baseline
DEFAULT_BASELINE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "regression", "baselines.json"
)


class RegressionTest:
    """
    Regression test untuk strategy behavior.
    Menyimpan baseline dan membandingkan dengan run baru.
    """
    
    # Ambang perubahan materiil (config-driven)
    PF_CHANGE_THRESHOLD = 0.30     # PF berubah > 30% = materiil
    EXPECTANCY_CHANGE_THRESHOLD = 0.50
    MAX_DD_CHANGE_THRESHOLD = 0.30
    
    def __init__(self, baseline_file: Optional[str] = None):
        self.baseline_file = baseline_file or DEFAULT_BASELINE_FILE
        self.baselines = self._load_baselines()
    
    def _load_baselines(self) -> Dict:
        """Load baseline tersimpan."""
        if os.path.exists(self.baseline_file):
            with open(self.baseline_file) as f:
                return json.load(f)
        return {}
    
    def _save_baselines(self):
        """Simpan baseline."""
        os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
        with open(self.baseline_file, "w") as f:
            json.dump(self.baselines, f, indent=2)
    
    def compute_fingerprint(self, code_dir: str) -> str:
        """
        Hitung fingerprint/checksum dari kode.
        Deteksi perubahan code yang mempengaruhi feature/strategy.
        """
        hash_obj = hashlib.sha256()
        # Hash kode di directory tertentu (engine + contracts)
        for root, dirs, files in os.walk(code_dir):
            for fname in sorted(files):
                if fname.endswith(".py"):
                    path = os.path.join(root, fname)
                    with open(path, "rb") as f:
                        hash_obj.update(path.encode())
                        hash_obj.update(f.read())
        return hash_obj.hexdigest()[:12]
    
    def save_baseline(self, name: str, metrics: Dict, metadata: Dict) -> Dict:
        """
        Simpan baseline untuk strategi tertentu.
        
        Args:
            name: nama strategi (compression_v1)
            metrics: hasil compute_metrics (pf, wr, expectancy, max_dd, trades)
            metadata: versi (dataset, feature, context, strategy), symbol, dst
        """
        baseline = {
            "metrics": metrics,
            "metadata": metadata,
            "saved_at": __import__('datetime').datetime.utcnow().isoformat(),
        }
        # Simpan di bawah nama strategi
        self.baselines.setdefault(name, {})
        # Append versi (buat history)
        version_key = f"{metadata.get('strategy_version', 'v1')}@{metadata.get('feature_version', 'v3.0')}"
        self.baselines[name][version_key] = baseline
        self._save_baselines()
        return baseline
    
    def check_regression(self, name: str, new_metrics: Dict, 
                         baseline_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Bandingkan metrics baru dengan baseline.
        Deteksi perubahan materiil.
        
        Returns:
            Dict: {is_regression, changes: {...}, warnings: [...]}
        """
        strategy_baselines = self.baselines.get(name, {})
        if not strategy_baselines:
            return {"is_regression": False, "warnings": ["No baseline yet"], "changes": {}}
        
        # Ambil baseline terbaru
        if baseline_version:
            baseline_metrics = strategy_baselines.get(baseline_version, {}).get("metrics", {})
        else:
            latest_key = sorted(strategy_baselines.keys())[-1]
            baseline_metrics = strategy_baselines[latest_key]["metrics"]
        
        if not baseline_metrics:
            return {"is_regression": False, "warnings": ["No baseline metrics"], "changes": {}}
        
        changes = {}
        warnings = []
        
        # Bandingkan PF
        old_pf = baseline_metrics.get("pf", 0)
        new_pf = new_metrics.get("pf", 0)
        if old_pf > 0:
            pf_change = abs(new_pf - old_pf) / old_pf
            changes["pf"] = {"old": old_pf, "new": new_pf, "pct_change": round(pf_change, 3)}
            if pf_change > self.PF_CHANGE_THRESHOLD:
                warnings.append(
                    f"MATERIIL: PF berubah {old_pf} → {new_pf} "
                    f"({pf_change:.0%} > {self.PF_CHANGE_THRESHOLD:.0%}). "
                    f"Feature/logic change materially changed strategy behavior!"
                )
        
        # Max DD
        old_dd = baseline_metrics.get("max_dd", 0)
        new_dd = new_metrics.get("max_dd", 0)
        if old_dd > 0:
            dd_change = abs(new_dd - old_dd) / old_dd
            changes["max_dd"] = {"old": old_dd, "new": new_dd, "pct_change": round(dd_change, 3)}
            if dd_change > self.MAX_DD_CHANGE_THRESHOLD:
                warnings.append(f"MATERIIL: Max DD berubah {old_dd} → {new_dd}")
        
        is_regression = len(warnings) > 0
        return {
            "is_regression": is_regression,
            "changes": changes,
            "warnings": warnings,
        }


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("REGRESSION TEST — Baseline & Material Change Detection")
    print("=" * 60)
    
    rt = RegressionTest(baseline_file="/tmp/regression_test_baseline.json")
    
    # Baseline pertama (initial)
    baseline_metrics = {
        "num_trades": 74, "pf": 2.31, "win_rate": 0.41,
        "expectancy": 0.42, "max_dd": 3.1, "total_pnl": 302.5,
    }
    metadata = {
        "dataset_version": "v1", "feature_version": "v3.0",
        "context_version": "v1", "strategy_version": "compression_v1",
        "symbol": "BTCUSDT", "timeframe": "5m",
        "date_range": "2026-08-01 to 2026-08-10",
    }
    rt.save_baseline("compression_v1", baseline_metrics, metadata)
    print("\nBaseline disimpan: PF=2.31, WR=0.41, MaxDD=3.1, Trades=74")
    
    # Run baru yang SAMA (harus tidak ada regression)
    same_metrics = dict(baseline_metrics)
    check_same = rt.check_regression("compression_v1", same_metrics)
    print(f"\nRun identik:")
    print(f"  is_regression={check_same['is_regression']}, warnings={check_same['warnings']}")
    
    # Run baru yang BERUBAH (PF turun drastis)
    degraded_metrics = dict(baseline_metrics)
    degraded_metrics["pf"] = 1.42
    degraded_metrics["max_dd"] = 4.8
    check_degraded = rt.check_regression("compression_v1", degraded_metrics)
    print(f"\nRun TEREGRESI (PF 2.31→1.42):")
    print(f"  is_regression={check_degraded['is_regression']}")
    for w in check_degraded['warnings']:
        print(f"  ⚠️ {w}")
    
    print("\n" + "=" * 60)
    print("✓ REGRESSION TEST OPERATIONAL")
    print("✔ Mendeteksi perubahan materiil pada edge behavior")
    print("=" * 60)
    
    # Cleanup
    os.remove("/tmp/regression_test_baseline.json")
