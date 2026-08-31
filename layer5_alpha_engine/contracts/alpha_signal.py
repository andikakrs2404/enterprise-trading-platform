#!/usr/bin/env python3
"""
Layer 5 - Contract: AlphaSignal
Output dari Alpha Engine.

PENTING: AlphaSignal BUKAN order.
Tidak ada:
- modal
- leverage
- SL
- order type
- jumlah BTC
Ini bukan tanggung jawab Alpha.

Alpha hanya menghasilkan:
- alpha id
- simbol
- timeframe
- direction
- score
- confidence
- state
- expected horizon
- evidence (transparan)
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class AlphaDirection(Enum):
    """Arah alpha."""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class AlphaState(Enum):
    """
    Lifecycle state alpha (untuk research).
    Bukan hanya signal = BUY.
    """
    OBSERVING = "OBSERVING"          # Market diamati, belum ada setup
    SETUP = "SETUP"                  # Setup terbentuk (market compression) - belum trading
    QUALIFIED = "QUALIFIED"          # Setup memenuhi syarat
    TRIGGERED = "TRIGGERED"          # Trigger terpenuhi (breakout + volume) - SINYAL
    ACTIVE = "ACTIVE"                # Alpha aktif (posisi berjalan)
    INVALIDATED = "INVALIDATED"      # Setup gagal / batal
    EXPIRED = "EXPIRED"              # Setup kadaluarsa tanpa trigger


@dataclass
class AlphaSignal:
    """
    Output standar semua alpha engines.
    Semua edge harus punya interface yang sama.
    """
    
    alpha: str                              # "compression_breakout_v1"
    symbol: str                             # "BTCUSDT"
    timeframe: str                          # "5m"
    direction: AlphaDirection = AlphaDirection.FLAT
    score: float = 0.0                      # 0-1 strength
    confidence: float = 0.0                 # 0-1 confidence
    state: AlphaState = AlphaState.OBSERVING
    
    # Alpha quality (bukan position size)
    expected_return: float = 0.0            # estimasi expected return
    expected_horizon: str = ""              # "1h-4h"
    holding_period_bars: int = 0
    
    # Evidence - transparan (untuk attribution)
    evidence: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    context: Optional[Dict] = None          # regime context saat itu
    version: str = "1.0.0"
    timestamp: Optional[int] = None
    
    # --- Helpers ---
    def is_tradeable(self) -> bool:
        """Apakah signal layak jadi trade (TRIGGERED)?"""
        return self.state == AlphaState.TRIGGERED and self.direction in (AlphaDirection.LONG, AlphaDirection.SHORT)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialisasi ke dict (outsource ke portfolio/risk)."""
        return {
            "alpha": self.alpha,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "score": self.score,
            "confidence": self.confidence,
            "state": self.state.value,
            "expected_return": self.expected_return,
            "expected_horizon": self.expected_horizon,
            "holding_period_bars": self.holding_period_bars,
            "evidence": self.evidence,
            "version": self.version,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """Serialisasi ke JSON."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def triggered(cls, alpha, symbol, timeframe, direction, score, confidence,
                  evidence, expected_return=0.0, expected_horizon="",
                  holding_period_bars=0, **kwargs) -> "AlphaSignal":
        """Factory untuk signal TRIGGERED."""
        return cls(
            alpha=alpha, symbol=symbol, timeframe=timeframe,
            direction=direction, score=score, confidence=confidence,
            state=AlphaState.TRIGGERED, evidence=evidence,
            expected_return=expected_return, expected_horizon=expected_horizon,
            holding_period_bars=holding_period_bars, **kwargs
        )


# Quick test
if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print("ALPHA SIGNAL CONTRACT TEST")
    print("=" * 60)
    
    # Contoh sinyal Compression Breakout
    sig = AlphaSignal.triggered(
        alpha="compression_breakout_v1",
        symbol="BTCUSDT",
        timeframe="5m",
        direction=AlphaDirection.LONG,
        score=0.87,
        confidence=0.81,
        evidence={
            "compression": 0.91,
            "volume_expansion": 0.84,
            "price_breakout": 0.88,
            "oi_confirmation": 0.72,
        },
        expected_return=0.42,
        expected_horizon="1h-4h",
        holding_period_bars=20,
    )
    
    print("\nApa yang ALPHA tahu (bukan order):")
    print(sig.to_json())
    print(f"\nis_tradeable? {sig.is_tradeable()} (TRIGGERED + LONG = layak)")
    print(f"\nYang TIDAK ada di AlphaSignal: modal, leverage, SL, order type, qty ✓")
    
    print("\n" + "=" * 60)
    print("✓ ALPHA SIGNAL CONTRACT OPERATIONAL")
    print("= Output adalah sinyal alpha, BUKAN order")
    print("=" * 60)
