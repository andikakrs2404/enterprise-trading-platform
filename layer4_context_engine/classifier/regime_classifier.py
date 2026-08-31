#!/usr/bin/env python3
"""
Layer 4 - Market Context Engine (Regime Classifier)
Memutuskan regime PASKA menerima komponen context dari Layer 3.

Boundary yang benar:
Layer 3 (feature engine): menghasilkan AUTOMIC + CONTEXT COMPONENTS
      ↓
Layer 4 (context engine): MEMUTUSKAN regime dari komponen tersebut
      ↓
Layer 5+ (alpha engine): memilih edge berdasarkan regime
      ↓
Signal

Layer 4 menerima komponen dari Layer 3 (bukan memutuskan sendiri),
dan memilih edge yang cocok untuk regime.
"""
from typing import Dict, List, Any, Optional
import json
import os


class MarketContextEngine:
    """
    Layer 4 - Context/Regime Engine.
    Menerima komponen context dari Layer 3, memutuskan regime,
    dan merouter ke alpha edges yang cocok.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.methods = self.config.get("classifier", {}).get("methods", {})
        self.regimes = self.config.get("regimes", {})
    
    def _load_config(self, config_path: Optional[str]) -> Dict:
        if config_path and os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        # Default: cari di folder config (resolusi path robust)
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "config", "classifier_config.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "config", "classifier_config.json"),
        ]
        for path in candidates:
            path = os.path.normpath(path)
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        return {"classifier": {"methods": {}}, "regimes": {}}
    
    def classify(self, context_components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Klasifikasi regime dari komponen context Layer 3.
        
        Args:
            context_components: dari Layer 3 RegimeContextFeatures
                {
                    "compression_components": {...},
                    "compression_score": 0.8,
                    "trend_components": {...},
                    "trend_score": 0.1,
                    "expansion_components": {...},
                    "expansion_score": 0.2,
                    "volatility_state": "...",
                    "trend_state": "...",
                    "participation_state": "...",
                }
                
        Returns:
            Dict: {regime, confidence, allowed_edges, evidence}
        """
        comp = context_components.get("compression_score", 0.0)
        exp = context_components.get("expansion_score", 0.0)
        trend = context_components.get("trend_score", 0.0)
        trend_strength = context_components.get("trend_strength", 0.0)
        
        # Ambil thresholds dari config
        comp_thresh = self.methods.get("compression", {}).get("threshold", 0.6)
        exp_thresh = self.methods.get("volatility_expansion", {}).get("threshold", 0.6)
        trend_thresh = self.methods.get("trending", {}).get("threshold_abs", 0.5)
        strength_min = self.methods.get("trending", {}).get("strength_min", 0.5)
        
        # --- Decision logic (Layer 4, bukan Layer 3) ---
        regime = "RANGE"
        confidence = 0.5
        evidence = {}
        
        if exp > exp_thresh and abs(trend) > trend_thresh and trend_strength > strength_min:
            regime = "TRENDING"
            direction = "UP" if trend > 0 else "DOWN"
            confidence = min(0.95, 0.6 + exp * 0.3 + abs(trend) * 0.1)
            evidence = {
                "expansion_score": exp,
                "trend_score": trend,
                "trend_direction": direction,
            }
        elif exp > exp_thresh:
            regime = "VOLATILITY_EXPANSION"
            confidence = min(0.9, 0.5 + exp * 0.4)
            evidence = {"expansion_score": exp}
        elif comp > comp_thresh:
            regime = "COMPRESSION"
            confidence = min(0.9, 0.5 + comp * 0.4)
            evidence = {
                "compression_score": comp,
                "volatility_compression": context_components.get(
                    "compression_components", {}).get("volatility_compression"),
                "volume_compression": context_components.get(
                    "compression_components", {}).get("volume_compression"),
            }
        
        # Jika tidak terdeteksi: RANGE (fallback)
        
        allowed_edges = self.regimes.get(regime, {}).get("allowed_edges", [])
        
        return {
            "regime": regime,
            "confidence": round(confidence, 4),
            "allowed_edges": allowed_edges,
            "evidence": evidence,
        }
    
    def classify_series(self, context_rows: List[Dict]) -> List[Dict]:
        """Klasifikasi regime untuk series context rows."""
        return [self.classify(row) for row in context_rows]
    
    def build_full_context(self, context_components: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gabungkan komponen Layer 3 + keputusan regime Layer 4.
        Ini yang dikonsumsi Alpha Engine.
        """
        decision = self.classify(context_components)
        return {
            **context_components,   # dari Layer 3
            **decision,             # dari Layer 4 (regime, confidence, edges)
        }


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("LAYER 4 - MARKET CONTEXT ENGINE TEST")
    print("=" * 60)
    
    engine = MarketContextEngine()
    
    # Skenario dari Layer 3 (komponen, bukan keputusan regime)
    scenarios = [
        {
            "name": "COMPRESSION (L3 output)",
            "context": {"compression_score": 0.82, "expansion_score": 0.15,
                        "trend_score": 0.1, "trend_strength": 0.2,
                        "compression_components": {"volatility_compression": 0.9,
                                                    "volume_compression": 0.84}}
        },
        {
            "name": "EXPANSION (L3 output)",
            "context": {"compression_score": 0.1, "expansion_score": 0.9,
                        "trend_score": 0.3, "trend_strength": 0.6,
                        "compression_components": {"volatility_compression": 0.1,
                                                    "volume_compression": 0.1}}
        },
        {
            "name": "RANGE (L3 output)",
            "context": {"compression_score": 0.4, "expansion_score": 0.2,
                        "trend_score": 0.1, "trend_strength": 0.3,
                        "compression_components": {"volatility_compression": 0.5,
                                                    "volume_compression": 0.5}}
        },
    ]
    
    for s in scenarios:
        print(f"\nScenario: {s['name']}")
        result = engine.classify(s['context'])
        print(f"  → regime={result['regime']}, confidence={result['confidence']}")
        print(f"  → allowed_edges={result['allowed_edges']}")
        print(f"  → evidence={result['evidence']}")
    
    print("\n" + "=" * 60)
    print("✓ LAYER 4 CONTEXT ENGINE OPERATIONAL")
    print("✓ Regime diputuskan Layer 4 dari komponen Layer 3 (boundary benar)")
    print("=" * 60)
