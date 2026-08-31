#!/usr/bin/env python3
"""
Layer 3 - Base Calculator
Class dasar untuk semua feature calculators.
Setiap feature calculator harus meng-extend class ini dan 
mengimplementasikan metode `compute`.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseCalculator(ABC):
    """
    Base class untuk semua feature calculators.
    Memberikan kerangka standard untuk komputasi feature.
    
    Subclass harus:
    - Set `name`, `description`, `inputs`, `output` sebagai class attributes
    - Implementasikan metode `compute(self, data)` untuk menghitung feature
    
    Contoh subclass:
    ```python
    class ATRCalculator(BaseCalculator):
        name = "atr_14"
        description = "Average True Range (14 periods)"
        inputs = ["ohlc"]
        output = "atr"
        
        def compute(self, data):
            # implementasi ATR
            return result
    ```
    """
    
    # Class attributes - harus di-override di subclass
    name: str = "base_calculator"
    description: str = "Base calculator - override in subclass"
    inputs: List[str] = []
    output: str = "result"
    
    def __init__(self, **params):
        """
        Inisialisasi calculator dengan parameter tambahan.
        
        Args:
            **params: Parameter spesifik calculator (period, threshold, dll)
        """
        self.params = params
        self.validate_params()
    
    def validate_params(self):
        """Validasi parameter yang diberikan. Override di subclass jika perlu."""
        pass
    
    @abstractmethod
    def compute(self, data: Any) -> Any:
        """
        Hitung feature dari data yang diberikan.
        
        Args:
            data: Data input untuk kalkulasi
            
        Returns:
            Hasil kalkulasi feature
        """
        pass
    
    def validate_input(self, data: Any) -> bool:
        """
        Validasi input sebelum komputasi.
        Bisa di-override di subclass untuk validasi spesifik.
        """
        if data is None:
            raise ValueError(f"[{self.name}] Data tidak boleh None")
        return True
    
    def __call__(self, data: Any) -> Any:
        """Helper: panggil calculator seperti fungsi."""
        self.validate_input(data)
        return self.compute(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Representasi dict dari calculator (untuk registry/metadata)."""
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "output": self.output,
            "params": self.params,
        }


# Contoh implementasi
class SimpleATRCalculator(BaseCalculator):
    """Contoh implementasi ATR sederhana"""
    name = "atr_14"
    description = "Average True Range dengan periode 14"
    inputs = ["ohlc"]
    output = "atr"
    
    def validate_params(self):
        if "period" in self.params:
            if self.params["period"] < 1:
                raise ValueError("Period harus >= 1")
    
    def compute(self, data: Any) -> float:
        # Sederhana: average of high-low range
        if not data or len(data) < 2:
            return 0.0
        ranges = [d["high"] - d["low"] for d in data]
        period = self.params.get("period", 14)
        recent = ranges[-period:]
        return sum(recent) / len(recent) if recent else 0.0


if __name__ == "__main__":
    print("=" * 60)
    print("BASE CALCULATOR TEST")
    print("=" * 60)
    
    # Test dengan contoh subclass
    calc = SimpleATRCalculator(period=14)
    
    sample_data = [
        {"high": 102, "low": 98, "close": 100},
        {"high": 103, "low": 99, "close": 101},
        {"high": 101, "low": 97, "close": 99},
        {"high": 102, "low": 98, "close": 100},
    ]
    
    print(f"Name: {calc.name}")
    print(f"Description: {calc.description}")
    print(f"Inputs: {calc.inputs}")
    print(f"Output: {calc.output}")
    print(f"Params: {calc.params}")
    
    # Panggil calculator
    result = calc(sample_data)
    print(f"\nResult (via __call__): {result:.4f}")
    
    print("\n" + "=" * 60)
    print("✓ Base Calculator Operational")
    print("=" * 60)
