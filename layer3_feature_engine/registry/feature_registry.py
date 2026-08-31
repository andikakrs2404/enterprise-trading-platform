#!/usr/bin/env python3
"""
Layer 3 - Feature Registry
Mendaftarkan semua feature calculators dan feature yang tersedia.
Setiap feature punya nama, kalkulator, input required, dan output.
"""
from typing import Dict, List, Any, Optional, Callable

class FeatureRegistry:
    """
    Registry pusat untuk semua feature calculations.
    Enterprise-grade: pemisahan antara pendaftaran feature dan komputasinya.
    """
    
    def __init__(self):
        self._features = {}  # name -> feature definition
        self._calculators = {}  # name -> callable
    
    def register(self, name: str, calculator: Callable, 
                 inputs: List[str], output: str, description: str = ""):
        """
        Daftarkan feature baru ke registry.
        
        Args:
            name: Nama feature (contoh: "atr_14")
            calculator: Fungsi yang menghitung feature
            inputs: Daftar input yang dibutuhkan (contoh: ["ohlc"])
            output: Nama kolom output (contoh: "atr")
            description: Deskripsi feature
        """
        import datetime
        self._features[name] = {
            "name": name,
            "inputs": inputs,
            "output": output,
            "description": description,
            "registered_at": datetime.datetime.now().isoformat()
        }
        self._calculators[name] = calculator
    
    def get(self, name: str) -> Optional[Callable]:
        """Dapatkan calculator untuk feature tertentu."""
        return self._calculators.get(name)
    
    def list_features(self) -> List[Dict[str, Any]]:
        """List semua feature yang terdaftar."""
        return list(self._features.values())
    
    def has(self, name: str) -> bool:
        """Cek apakah feature sudah terdaftar."""
        return name in self._features
    
    def calculate(self, name: str, data: Any) -> Any:
        """Hitung feature tertentu dengan data yang diberikan."""
        if name not in self._calculators:
            raise ValueError(f"Feature '{name}' belum terdaftar di registry")
        return self._calculators[name](data)
    
    def batch_calculate(self, names: List[str], data: Any) -> Dict[str, Any]:
        """Hitung beberapa feature sekaligus."""
        results = {}
        for name in names:
            results[name] = self.calculate(name, data)
        return results
    
    def feature_count(self) -> int:
        """Jumlah feature yang terdaftar."""
        return len(self._features)


# Contoh penggunaan
if __name__ == "__main__":
    import datetime
    
    # Contoh calculator sederhana
    def calc_atr(data):
        """Hitung ATR sederhana dari OHLC data"""
        # Data contoh: [{"high": 100, "low": 98, "close": 99}, ...]
        if not data or len(data) < 2:
            return 0.0
        ranges = [d["high"] - d["low"] for d in data]
        return sum(ranges) / len(ranges)
    
    # Daftarkan feature
    registry = FeatureRegistry()
    registry.register(
        name="atr_14",
        calculator=calc_atr,
        inputs=["ohlc"],
        output="atr",
        description="Average True Range dengan periode 14"
    )
    
    print("=" * 60)
    print("FEATURE REGISTRY TEST")
    print("=" * 60)
    
    # Test pendaftaran & listing
    print(f"Registered features: {registry.list_features()}")
    print(f"Total features: {registry.feature_count()}")
    print(f"Mempunyai atr_14: {registry.has('atr_14')}")
    
    # Test kalkulasi
    sample_data = [
        {"high": 102, "low": 98, "close": 100},
        {"high": 103, "low": 99, "close": 101},
        {"high": 101, "low": 97, "close": 99},
        {"high": 102, "low": 98, "close": 100},
    ]
    result = registry.calculate("atr_14", sample_data)
    print(f"ATR result: {result:.4f}")
    
    print("=" * 60)
    print("✓ Feature Registry Operational")
    print("=" * 60)
