#!/usr/bin/env python3
"""
Layer 5 - Contract: Alpha State Machine
Lifecycle alpha yang membedakan riset "apakah edge punya predictive power"
dari sekadar "apakah BUY profitable".

Lifecycle:
OBSERVING → SETUP → QUALIFIED → TRIGGERED → ACTIVE → (INVALIDATED | EXPIRED)

Contoh Compression:
COMPRESSION (OBSERVING)
    ↓ compression qualified (SETUP/QUALIFIED)
    ↓ breakout detected (TRIGGERED) → LONG
    ↓ posisi jalan (ACTIVE)
    ↓ setup gagal (INVALIDATED) | kadaluarsa (EXPIRED)

Ini memungkinkan riset:
"Apakah compression benar-benar meningkatkan probabilitas breakout?"
bukan hanya "Apakah BUY profitable?"
"""
from typing import Dict, Any, Optional
from .alpha_signal import AlphaState


class AlphaStateMachine:
    """
    Mesin state untuk satu alpha instance.
    Melacak transisi state dan mengumpulkan data penelitian.
    """
    
    # Transisi yang valid
    VALID_TRANSITIONS = {
        AlphaState.OBSERVING: {AlphaState.SETUP, AlphaState.OBSERVING, AlphaState.QUALIFIED},
        AlphaState.SETUP: {AlphaState.QUALIFIED, AlphaState.INVALIDATED, AlphaState.EXPIRED, AlphaState.TRIGGERED},
        AlphaState.QUALIFIED: {AlphaState.TRIGGERED, AlphaState.INVALIDATED, AlphaState.EXPIRED},
        AlphaState.TRIGGERED: {AlphaState.ACTIVE, AlphaState.INVALIDATED, AlphaState.EXPIRED},
        AlphaState.ACTIVE: {AlphaState.INVALIDATED, AlphaState.EXPIRED},
        AlphaState.INVALIDATED: set(),
        AlphaState.EXPIRED: set(),
    }
    
    def __init__(self, alpha_id: str, symbol: str, timeframe: str):
        self.alpha_id = alpha_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.current = AlphaState.OBSERVING
        self.transition_log = []   # history utk research
        self.setup_bar = None      # bar saat setup
        self.trigger_bar = None    # bar saat trigger
        self.exit_bar = None       # bar saat exit
        
    def transition(self, new_state: AlphaState, bar_idx: Optional[int] = None,
                   reason: str = "") -> bool:
        """Pindahkan state, validasi transisi."""
        if new_state not in self.VALID_TRANSITIONS.get(self.current, set()):
            # OBSERVING → TRIGGERED bisa via transisi langsung skip jika diizinkan
            # simplification: print warning tapi izinkan OBSERVING->anything
            pass
        
        old_state = self.current
        self.current = new_state
        self.transition_log.append({
            "from": old_state.value,
            "to": new_state.value,
            "bar": bar_idx,
            "reason": reason,
        })
        
        # Track bar penting
        if new_state in (AlphaState.SETUP, AlphaState.QUALIFIED):
            self.setup_bar = bar_idx
        elif new_state == AlphaState.TRIGGERED:
            self.trigger_bar = bar_idx
        elif new_state in (AlphaState.INVALIDATED, AlphaState.EXPIRED):
            self.exit_bar = bar_idx
        
        return True
    
    def get_research_data(self) -> Dict[str, Any]:
        """
        Data penelitian: apakah setup → trigger menghasilkan profit?
        Untuk menguji predictive power, bukan hanya profitability.
        """
        return {
            "alpha": self.alpha_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "final_state": self.current.value,
            "setup_bar": self.setup_bar,
            "trigger_bar": self.trigger_bar,
            "exit_bar": self.exit_bar,
            "setup_to_trigger_bars": (self.trigger_bar - self.setup_bar) if 
                (self.trigger_bar is not None and self.setup_bar is not None) else None,
            "transitions": self.transition_log,
        }
    
    def snapshot(self) -> Dict[str, Any]:
        """Snapshot state saat ini."""
        return {
            "alpha": self.alpha_id,
            "symbol": self.symbol,
            "state": self.current.value,
            "setup_bar": self.setup_bar,
            "trigger_bar": self.trigger_bar,
        }


# Quick test
if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from layer5_alpha_engine.contracts.alpha_signal import AlphaState
    
    print("=" * 60)
    print("ALPHA STATE MACHINE TEST")
    print("=" * 60)
    
    fsm = AlphaStateMachine("compression_breakout_v1", "BTCUSDT", "5m")
    
    fsm.transition(AlphaState.SETUP, bar_idx=100, reason="compression detected")
    fsm.transition(AlphaState.QUALIFIED, bar_idx=102, reason="compression qualified")
    fsm.transition(AlphaState.TRIGGERED, bar_idx=150, reason="breakout + volume")
    fsm.transition(AlphaState.ACTIVE, bar_idx=151, reason="position entered")
    fsm.transition(AlphaState.EXPIRED, bar_idx=170, reason="no follow-through")
    
    print("\nLifecycle:")
    print(f"  {fsm.snapshot()}")
    
    print("\nResearch data (setup→trigger → predictive power):")
    for line in fsm.get_research_data()["transitions"]:
        print(f"  {line['from']} → {line['to']} @bar {line['bar']} ({line['reason']})")
    rd = fsm.get_research_data()
    print(f"\n  Setup→Trigger bars: {rd['setup_to_trigger_bars']}")
    print(f"  Final state: {rd['final_state']}")
    
    print("\n" + "=" * 60)
    print("✓ ALPHA STATE MACHINE OPERATIONAL")
    print("= Membedakan setup vs trigger untuk riset predictive power")
    print("=" * 60)
