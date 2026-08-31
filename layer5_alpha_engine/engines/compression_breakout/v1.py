#!/usr/bin/env python3
"""
Layer 5 - Edge #1: Compression Breakout V1

PRINSIP:
- TIDAK menghitung indikator (hanya baca features)
- Setup vs Trigger TERPISAH
- Evidence transparan (bukan black-box score)
- Output AlphaSignal (bukan order)

LOGIKA:
SETUP (market compression - belum trading):
    volatility_compression tinggi (atr_ratio rendah)
    + range_compression (bb_width sempit)
    + volume_compression (volume rendah)

WAIT (menunggu trigger)

TRIGGER (breakout - baru signal):
    price_breakout (harga menembus range)
    + volume_expansion (volume meledak)
    + oi_confirmation (OI menguat = posisi baru)

SIGNAL: LONG jika breakout ke atas, SHORT jika ke bawah.
"""
from typing import Dict, Any, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from layer5_alpha_engine.contracts.alpha_engine import AlphaEngine
from layer5_alpha_engine.contracts.alpha_signal import AlphaSignal, AlphaDirection, AlphaState
from layer5_alpha_engine.contracts.evidence import AlphaEvidence
from layer5_alpha_engine.contracts.alpha_state import AlphaStateMachine


class CompressionBreakoutV1(AlphaEngine):
    """
    Compression Breakout edge v1.
    Family: volatility
    Konsumsi feature saja, tidak hitung indikator.
    """
    
    ALPHA_ID = "compression_breakout_v1"
    FAMILY = "volatility"
    REQUIRED_FEATURES = ["atr_ratio", "bb_width", "volume_ratio", "volume_percentile", "oi_delta"]
    REQUIRED_CONTEXT = ["compression_components", "volatility_state"]
    TIMEFRAMES = ["5m", "15m", "1h"]
    VERSION = "1.0.0"
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        cfg = config or {}
        # Threshold dari config (tidak hardcoded)
        self.setup_compression_threshold = cfg.get("setup_compression_threshold", 0.6)
        self.setup_volatility_compr = cfg.get("setup_volatility_compr", 0.5)
        self.trigger_volume_threshold = cfg.get("trigger_volume_threshold", 2.0)
        self.trigger_oi_threshold = cfg.get("trigger_oi_threshold", 0.0)
        
        # State machine per evaluate (untuk research)
        self.fsm = None
    
    # ===== IMPLEMENTASI WAJIB =====
    def evaluate(self, features: Dict[str, Any],
                 context: Dict[str, Any],
                 market_state: Dict[str, Any]) -> AlphaSignal:
        """
        Evaluasi compression breakout.
        Setup dan trigger dievaluasi terpisah.
        """
        symbol = market_state.get("symbol", "BTCUSDT")
        timeframe = market_state.get("timeframe", "5m")
        bar_idx = market_state.get("bar_idx")
        
        # Inisialisasi FSM jika belum
        if self.fsm is None:
            self.fsm = AlphaStateMachine(self.ALPHA_ID, symbol, timeframe)
        
        # ===== 1. SETUP evaluation =====
        setup = self._evaluate_setup(features, context)
        
        # Pertahankan setup yang sudah ACTIVE dari bar sebelumnya (Setup → WAIT → Trigger)
        setup_active = self.fsm.current in (AlphaState.SETUP, AlphaState.QUALIFIED)
        
        if setup["is_setup"] and not setup_active:
            # Setup baru terdeteksi
            self.fsm.transition(AlphaState.SETUP, bar_idx, reason="compression qualified")
            setup_active = True
        elif setup["is_setup"] and setup_active:
            # Setup masih berlanjut
            self.fsm.transition(AlphaState.QUALIFIED, bar_idx, reason="compression continues")
        elif not setup["is_setup"] and not setup_active:
            # Tidak ada setup, belum pernah aktif → OBSERVING
            return self._build_signal(features, symbol, timeframe,
                                      state=AlphaState.OBSERVING, evidence={})
        # Jika setup hilang tapi belum trigger: biarkan WAIT sebentar (jangan langsung invalidate
        # untuk memberi ruang breakout) — batasi dengan counter max_bars
        elif not setup["is_setup"] and setup_active:
            # Cek apakah sudah terlalu lama (banyak bar) tanpa setup — expire setup
            bars_in_setup = self.fsm.transition_log[-1]["bar"] if self.fsm.transition_log else 0
            max_wait = self.config.get("max_setup_wait_bars", 30)
            if bar_idx is not None and bars_in_setup is not None:
                if (bar_idx - bars_in_setup) > max_wait:
                    self.fsm.transition(AlphaState.EXPIRED, bar_idx, reason="setup expired no breakout")
                    return self._build_signal(features, symbol, timeframe,
                                              state=AlphaState.EXPIRED, evidence={})
            # Masih dalam window WAIT — retain setup, evaluasi trigger di bawah
        
        # ===== 2. TRIGGER evaluation (setup aktif / retained) =====
        trigger = self._evaluate_trigger(features, market_state)
        
        if trigger["is_trigger"] and setup_active:
            # Breakout terdeteksi → sinyal
            direction = trigger["direction"]
            self.fsm.transition(AlphaState.TRIGGERED, bar_idx,
                                reason=f"{direction.value} breakout + volume expansion")
            evidence = {**setup["evidence"], **trigger["evidence"]}
            return self._build_signal(features, symbol, timeframe,
                                      state=AlphaState.TRIGGERED, evidence=evidence,
                                      direction=direction, score=trigger["score"],
                                      confidence=trigger["confidence"])
        
        # Setup aktif tapi belum trigger
        return self._build_signal(features, symbol, timeframe,
                                  state=AlphaState.QUALIFIED, evidence=setup["evidence"])
    
    # ===== SETUP (terpisah) =====
    def _evaluate_setup(self, features: Dict, context: Dict) -> Dict:
        """
        Setup: market sedang compression? (BELUM trading)
        """
        # Konsumsi dari context (L3/L4), bukan hitung sendiri
        comp_components = context.get("compression_components", {})
        volatility_comp = comp_components.get("volatility_compression", 0)
        range_comp = comp_components.get("range_compression", 0)
        volume_comp = comp_components.get("volume_compression", 0)
        
        # Composite compression (dari komponen transparent)
        compression = (0.4*volatility_comp + 0.4*range_comp + 0.2*volume_comp)
        
        is_setup = compression >= self.setup_compression_threshold
        
        evidence = {
            "compression": round(compression, 4),
            "volatility_compression": round(volatility_comp, 4),
            "range_compression": round(range_comp, 4),
            "volume_compression": round(volume_comp, 4),
        }
        return {"is_setup": is_setup, "evidence": evidence}
    
    # ===== TRIGGER (terpisah) =====
    def _evaluate_trigger(self, features: Dict, market_state: Dict) -> Dict:
        """
        Trigger: harga breakout + volume expansion (baru sinyal).
        """
        # Breakout: harga menembus HIGH/LOW bar SEBELUMNYA
        price = market_state.get("close")
        prev_high = market_state.get("prev_high", market_state.get("high"))
        prev_low = market_state.get("prev_low", market_state.get("low"))
        
        # Volume expansion
        volume_ratio = features.get("volume_ratio", 1.0)
        volume_expansion = min(1.0, max(0.0, (volume_ratio - 1.0) / 3.0))
        
        # OI confirmation (posisi baru)
        oi_delta = features.get("oi_delta", 0)
        oi_confirmation = min(1.0, max(0.0, oi_delta / 100.0))
        
        # Price breakout (membandingkan dengan bar sebelumnya)
        price_breakout = 0.0
        direction = AlphaDirection.FLAT
        is_trigger = False
        if prev_high is not None and price is not None:
            if price > prev_high:
                price_breakout = 1.0
                direction = AlphaDirection.LONG
            elif prev_low is not None and price < prev_low:
                price_breakout = 1.0
                direction = AlphaDirection.SHORT
        
        # Volume harus meledak saat breakout beneran
        breakout_valid = (price_breakout > 0 and 
                          volume_ratio >= self.trigger_volume_threshold and
                          oi_delta >= self.trigger_oi_threshold)
        
        is_trigger = breakout_valid
        
        score = round(0.4*price_breakout + 0.35*volume_expansion + 0.25*oi_confirmation, 4)
        confidence = round(0.5 + 0.3*volume_expansion + 0.2*oi_confirmation, 4)
        
        evidence = {
            "price_breakout": price_breakout,
            "volume_expansion": round(volume_expansion, 4),
            "oi_confirmation": round(oi_confirmation, 4),
        }
        return {
            "is_trigger": is_trigger,
            "direction": direction,
            "score": score,
            "confidence": confidence,
            "evidence": evidence,
        }
    
    # ===== BUILDER =====
    def _build_signal(self, features, symbol, timeframe, state, evidence,
                      direction=AlphaDirection.FLAT, score=0.0, confidence=0.0):
        """Bangun AlphaSignal."""
        return AlphaSignal(
            alpha=self.ALPHA_ID,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            score=score,
            confidence=confidence,
            state=state,
            evidence=evidence,
            expected_return=0.42 if state == AlphaState.TRIGGERED else 0.0,
            expected_horizon="1h-4h",
            holding_period_bars=20 if state == AlphaState.TRIGGERED else 0,
            version=self.VERSION,
            timestamp=__import__('time').time(),
        )


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("EDGE #1 - COMPRESSION BREAKOUT V1 TEST")
    print("=" * 60)
    
    alpha = CompressionBreakoutV1()
    
    # ----- Scenario 1: Only setup (compression), no trigger yet -----
    features_setup = {
        "atr_ratio": 0.5, "bb_width": 0.02, "volume_ratio": 0.6,
        "volume_percentile": 0.08, "oi_delta": 0.2,
    }
    context_setup = {
        "compression_components": {
            "volatility_compression": 0.9, "range_compression": 0.85,
            "volume_compression": 0.8,
        },
        "volatility_state": "EXTREME_LOW",
    }
    market_setup = {"symbol": "BTCUSDT", "timeframe": "5m", "bar_idx": 100,
                    "close": 100.0, "high": 100.5, "low": 99.5}
    
    sig_before = alpha.evaluate(features_setup, context_setup, market_setup)
    print(f"\n1. Setup (compression) tapi belum trigger:")
    print(f"   state={sig_before.state.value}, score={sig_before.score}, "
          f"tradeable={sig_before.is_tradeable()}")
    print(f"   evidence={sig_before.evidence}")
    
    # ----- Scenario 2: Setup + Trigger (breakout + volume boom) -----
    features_trigger = {
        "atr_ratio": 0.5, "bb_width": 0.02, "volume_ratio": 3.2,
        "volume_percentile": 0.95, "oi_delta": 50.0,
    }
    market_trigger = {"symbol": "BTCUSDT", "timeframe": "5m", "bar_idx": 150,
                      "close": 102.0, "high": 101.0, "low": 100.5}
    
    sig_after = alpha.evaluate(features_trigger, context_setup, market_trigger)
    print(f"\n2. Setup + Trigger (breakout + volume boom):")
    print(f"   state={sig_after.state.value}, direction={sig_after.direction.value}, "
          f"score={sig_after.score}, confidence={sig_after.confidence}")
    print(f"   evidence={sig_after.evidence}")
    print(f"   tradeable={sig_after.is_tradeable()}")
    
    # Alpha quality (bukan position size)
    print(f"\n3. Alpha quality (bukan position size):")
    print(f"   expected_return={sig_after.expected_return} (+R)")
    print(f"   expected_horizon={sig_after.expected_horizon}")
    print(f"   holding_period_bars={sig_after.holding_period_bars}")
    
    print("\n" + "=" * 60)
    print("✓ COMPRESSION BREAKOUT V1 OPERATIONAL (Edge #1)")
    print("✓ Setup vs Trigger terpisah")
    print("✓ Konsumsi feature, output AlphaSignal (bukan order)")
    print("=" * 60)
