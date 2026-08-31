#!/usr/bin/env python3
"""
Layer 5 Backtester Integration (P1.6)
Menghubungkan Alpha Engine (L5) dengan Feature Backtester.

Alur:
L3 features → L4 context → L5 AlphaSignal → Backtester (bukan order)
"""
from typing import Dict, List, Optional, Any
import sys, os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

from layer3_feature_engine.engine_v3 import FeatureEngineV3
from layer3_feature_engine.domains.regime_context.features import RegimeContextFeatures
from layer5_alpha_engine.contracts.alpha_signal import AlphaSignal, AlphaState
from backtester.engine.feature_backtester import FeatureBacktester


class AlphaBacktestRunner:
    """
    Runner yang mengintegrasikan L3→L4→L5→Backtester.
    Backtester MENGKONSUMSI AlphaSignal (bukan order), konsisten dengan kontrak.
    """
    
    def __init__(self, alpha_engine, config: Optional[Dict] = None):
        """
        Args:
            alpha_engine: instance AlphaEngine (L5 edge, misal CompressionBreakoutV1)
        """
        self.alpha_engine = alpha_engine
        self.feature_engine = FeatureEngineV3()
        self.regime_context = RegimeContextFeatures()
        self.config = config or {}
    
    def build_pipeline_rows(self, ohlcv: List[Dict], 
                            open_interest: Optional[List] = None,
                            funding_rate: Optional[List] = None) -> List[Dict]:
        """
        Bangun rows feature + context untuk alpha.
        Satu-satunya sumber perhitungan (L3 + L4).
        """
        # L3 - atomic features + context components
        atomic = self.feature_engine.compute_all_atomic(ohlcv, open_interest, funding_rate)
        
        # L4 - context components (bukan regime final, tapi untuk alpha)
        # RegimeContext menghasilkan komponen, L5 alpha membaca
        context_rows = self.regime_context.compute_components(atomic)
        
        # Gabungkan: atomic + context + price (market_state untuk trigger)
        combined = []
        for i in range(len(atomic)):
            row = {
                **atomic[i],
                **context_rows[i],
                # market_state untuk trigger — pakai bar SEBELUMNYA untuk deteksi breakout
                "close": ohlcv[i].get("close"),
                "high": ohlcv[i].get("high"),
                "low": ohlcv[i].get("low"),
                "prev_high": ohlcv[i-1].get("high") if i > 0 else ohlcv[i].get("high"),
                "prev_low": ohlcv[i-1].get("low") if i > 0 else ohlcv[i].get("low"),
                "bar_idx": i,
            }
            combined.append(row)
        return combined
    
    def run_backtest(self, ohlcv: List[Dict],
                     open_interest: Optional[List] = None,
                     funding_rate: Optional[List] = None,
                     initial_capital: float = 10000.0,
                     risk_per_trade: float = 0.01,
                     symbol: str = "BTCUSDT", timeframe: str = "5m") -> Dict[str, Any]:
        """
        Jalankan backtest dengan alpha engine sebagai sumber sinyal.
        """
        # Reset alpha state (FSM) agar backtest mulai dari bersih.
        if hasattr(self.alpha_engine, "fsm"):
            self.alpha_engine.fsm = None
        
        # Build pipeline rows
        rows = self.build_pipeline_rows(ohlcv, open_interest, funding_rate)
        
        # Backtester
        bt = FeatureBacktester(rows)
        bt.set_metadata(
            symbol=symbol, timeframe=timeframe,
            dataset_version="v1", feature_version="v3.0",
            context_version="v1", strategy_version=self.alpha_engine.ALPHA_ID,
        )
        
        # Alpha-driven strategy function
        def alpha_strategy(row, position):
            # Siapkan market_state untuk alpha
            market_state = {
                "symbol": symbol, "timeframe": timeframe,
                "close": row.get("close"), "high": row.get("high"),
                "low": row.get("low"),
                "prev_high": row.get("prev_high"), "prev_low": row.get("prev_low"),
                "bar_idx": row.get("bar_idx"),
            }
            # Feature & context (dari pipeline, bukan hitung self)
            alpha_signal = self.alpha_engine.evaluate(row, row, market_state)
            
            # Backtester berinteraksi dengan AlphaSignal state
            if not position["active"]:
                if alpha_signal.state == AlphaState.TRIGGERED and alpha_signal.direction.value == "LONG":
                    return {"action": "BUY", "reason": alpha_signal.alpha,
                            "signal": alpha_signal.to_dict()}
                return {"action": "HOLD", "reason": f"{alpha_signal.state.value}"}
            else:
                # Exit: sinyal ter-invalidasi/expired, atau posisi sudah terlalu lama,
                # atau harga berbalik melawan entry (protektif).
                entry_idx = position.get("entry_idx", row.get("bar_idx"))
                bars_held = (row.get("bar_idx") or 0) - (entry_idx or 0)
                max_hold = self.config.get("max_hold_bars", 30)
                # Berbalik melawan entry: close < entry untuk LONG (sederhana)
                reversal = (row.get("close") < position.get("entry", row.get("close")))
                if alpha_signal.state in (AlphaState.INVALIDATED, AlphaState.EXPIRED) \
                   or bars_held >= max_hold or reversal:
                    return {"action": "SELL", "reason": f"{alpha_signal.state.value}/maxhold/reversal",
                            "signal": alpha_signal.to_dict()}
                return {"action": "HOLD", "reason": "position running"}
        
        result = bt.run(alpha_strategy, initial_capital, risk_per_trade)
        result["alpha_id"] = self.alpha_engine.ALPHA_ID
        return result


# Quick test
if __name__ == "__main__":
    import random
    random.seed(7)
    
    print("=" * 60)
    print("L5 BACKTESTER INTEGRATION TEST")
    print("=" * 60)
    
    from layer5_alpha_engine.engines.compression_breakout.v1 import CompressionBreakoutV1
    
    # Generate data: compression segments → breakout
    n = 600
    ohlcv = []
    price = 100.0
    for i in range(n):
        seg = i // 120
        vol_scale = [0.25, 1.5, 0.3, 2.0, 0.25][seg]
        o = price
        c = price + random.uniform(-0.5, 0.5) * vol_scale
        h = max(o, c) + random.uniform(0, 0.4) * max(vol_scale, 0.3)
        l = min(o, c) - random.uniform(0, 0.4) * max(vol_scale, 0.3)
        vol = random.uniform(2000, 4000) * (0.4 if vol_scale < 0.5 else 2.0)
        ohlcv.append({"open": o, "high": h, "low": l, "close": c, "volume": vol, "timestamp": i})
        price = c
    oi = [100000 + i*5 for i in range(n)]
    
    # Alpha engine
    alpha = CompressionBreakoutV1()
    
    # Runner
    runner = AlphaBacktestRunner(alpha)
    result = runner.run_backtest(ohlcv, oi, initial_capital=10000, risk_per_trade=0.01)
    
    print(f"\nAlpha: {result['alpha_id']}")
    print(f"Trades: {result['metrics']['num_trades']}")
    print(f"Metrics: {result['metrics']}")
    print(f"Final capital: {result['final_capital']}")
    
    print("\nContoh signal yang dihasilkan alpha (bukan order):")
    if result['trades']:
        t = result['trades'][0]
        print(f"  trade[0]: {t['signal']}")
    
    print("\n" + "=" * 60)
    print("✓ L5 BACKTESTER INTEGRATION OPERATIONAL")
    print("= Alpha menghasilkan AlphaSignal, backtester mengonsumsinya")
    print("=" * 60)
