#!/usr/bin/env python3
"""
Layer 5 - Contract: AlphaEngine (Base Interface)
Semua edge harus mengimplementasikan interface yang sama.

PRINSIP TERPENTING:
- Alpha TIDAK menghitung indikator (ATR, EMA, RSI, BBWidth)
- Alpha HANYA membaca:
      features["atr_ratio"]
      features["bb_width_percentile"]
      features["volume_ratio"]
      context["regime"]
- Alpha output: AlphaSignal (bukan order)

Semua edge:
    evaluate(features, context, market_state) → AlphaSignal
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from .alpha_signal import AlphaSignal


class AlphaEngine(ABC):
    """
    Base class semua alpha engines.
    Interface seragam untuk multi-edge.
    """
    
    # Metadata yang harus di-override subclass
    ALPHA_ID = "base_alpha"
    FAMILY = "base"
    REQUIRED_FEATURES: list = []
    REQUIRED_CONTEXT: list = []
    TIMEFRAMES: list = []
    VERSION = "1.0.0"
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    # ===== INTERFACE WAJIB (subclass implement) =====
    @abstractmethod
    def evaluate(self, features: Dict[str, Any],
                 context: Dict[str, Any],
                 market_state: Dict[str, Any]) -> AlphaSignal:
        """
        Evaluasi alpha dari features & context.
        
        Args:
            features: atomic features dari L3 (atr_ratio, bb_width, dll)
            context: regime context dari L4
            market_state: state pasar (price, dll)
            
        Returns:
            AlphaSignal
        """
        ...
    
    # ===== HELPER (template method) =====
    def validate_inputs(self, features: Dict, context: Dict) -> Optional[str]:
        """
        Validasi bahwa feature & context yang dibutuhkan TERSEDIA.
        Memastikan alpha tidak menghitung sendiri (kontrak).
        """
        missing_features = [f for f in self.REQUIRED_FEATURES if f not in features]
        missing_context = [c for c in self.REQUIRED_CONTEXT if c not in context]
        
        if missing_features:
            return f"Missing features: {missing_features}"
        if missing_context:
            return f"Missing context: {missing_context}"
        return None
    
    def check_not_computing_indicator(self) -> bool:
        """
        Kontrak: alpha tidak boleh memanggil fungsi indikator sendiri.
        """
        forbidden = ["import talib", "from talib", "atr(", "ema(", "rsi(", "bbwidth"]
        # Inspect source untuk indikator forbidden
        import inspect
        source = inspect.getsource(self.__class__)
        violations = [f for f in forbidden if f in source]
        return len(violations) == 0
    
    def get_metadata(self) -> Dict[str, Any]:
        """Metadata alpha (untuk registry)."""
        return {
            "id": self.ALPHA_ID,
            "family": self.FAMILY,
            "required_features": self.REQUIRED_FEATURES,
            "required_context": self.REQUIRED_CONTEXT,
            "timeframes": self.TIMEFRAMES,
            "version": self.VERSION,
        }


# Quick test
if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from layer5_alpha_engine.contracts.alpha_signal import AlphaSignal
    
    print("=" * 60)
    print("ALPHA ENGINE BASE CONTRACT TEST")
    print("=" * 60)
    
    # Contoh implementasi edge (belum lengkap, ilustrasi kontrak)
    class DemoAlpha(AlphaEngine):
        ALPHA_ID = "demo_alpha"
        FAMILY = "volatility"
        REQUIRED_FEATURES = ["atr_ratio", "bb_width", "volume_ratio"]
        REQUIRED_CONTEXT = ["regime"]
        TIMEFRAMES = ["5m", "15m"]
        
        def evaluate(self, features, context, market_state):
            # Baca feature (TIDAK hitung)
            score = features["atr_ratio"] * 0.5
            return AlphaSignal(
                alpha=self.ALPHA_ID, symbol="BTCUSDT", timeframe="5m",
                score=score, confidence=0.5,
            )
    
    demo = DemoAlpha()
    print(f"\nMetadata: {demo.get_metadata()}")
    
    # Validasi input tersedia
    features = {"atr_ratio": 0.5, "bb_width": 0.02, "volume_ratio": 1.2}
    context = {"regime": "COMPRESSION"}
    err = demo.validate_inputs(features, context)
    print(f"Input valid? {'✅' if err is None else f'❌ {err}'}")
    
    # Kontrak: tidak hitung indikator
    print(f"Tidak menghitung indikator sendiri? {demo.check_not_computing_indicator()}")
    
    print("\n" + "=" * 60)
    print("✓ ALPHA ENGINE BASE CONTRACT OPERATIONAL")
    print("= Interface seragam untuk semua edge")
    print("=" * 60)
