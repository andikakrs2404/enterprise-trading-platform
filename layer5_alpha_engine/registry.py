#!/usr/bin/env python3
"""
Layer 5 - Alpha Registry
Mendaftarkan semua alpha edges dan metadata research-nya.

Dengan registry, platform tahu:
- Alpha apa yang aktif?
- Feature apa yang dibutuhkan?
- Timeframe apa?
- Family apa?
- Versi berapa?
- Status research apa? (candidate / validated / production)
"""
from typing import Dict, List, Any, Optional
import json
import os


class AlphaRegistry:
    """
    Registry metadata alpha edges.
    """
    
    # Default file registri
    DEFAULT_REGISTRY = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "config", "alpha_registry.json"
    )
    
    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file or self.DEFAULT_REGISTRY
        self.registry: Dict[str, Dict] = self._load()
    
    def _load(self) -> Dict:
        if os.path.exists(self.registry_file):
            with open(self.registry_file) as f:
                return json.load(f)
        # Empty registry
        return {}
    
    def _save(self):
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        with open(self.registry_file, "w") as f:
            json.dump(self.registry, f, indent=2)
    
    def register(self, alpha_id: str, family: str, required_features: List[str],
                 required_context: List[str], timeframes: List[str],
                 version: str = "1.0.0", state: str = "candidate",
                 description: str = "") -> Dict:
        """
        Daftarkan alpha edge.
        
        Args:
            alpha_id: "compression_breakout_v1"
            family: "volatility"
            required_features: ["bb_width_percentile", "atr_ratio", ...]
            required_context: ["compression"]
            timeframes: ["5m", "15m", "1h"]
            version: "1.0.0"
            state: "candidate" 
            description: deskripsi singkat
        """
        entry = {
            "id": alpha_id,
            "family": family,
            "required_features": required_features,
            "required_context": required_context,
            "timeframes": timeframes,
            "version": version,
            "state": state,            # candidate / validated / production
            "description": description,
        }
        self.registry[alpha_id] = entry
        self._save()
        return entry
    
    def get(self, alpha_id: str) -> Optional[Dict]:
        """Ambil metadata alpha."""
        return self.registry.get(alpha_id)
    
    def list_alphas(self, state: Optional[str] = None) -> List[Dict]:
        """List semua alpha (opsional filter state)."""
        alphas = list(self.registry.values())
        if state:
            alphas = [a for a in alphas if a["state"] == state]
        return alphas
    
    def update_state(self, alpha_id: str, state: str):
        """Update status research alpha."""
        if alpha_id in self.registry:
            valid_states = ["candidate", "validated", "production", "deprecated"]
            if state in valid_states:
                self.registry[alpha_id]["state"] = state
                self._save()
    
    def get_timeframes(self, alpha_id: str) -> List[str]:
        """Timeframe yang dibutuhkan alpha."""
        return self.registry.get(alpha_id, {}).get("timeframes", [])
    
    def get_required_features(self, alpha_id: str) -> List[str]:
        """Feature yang dibutuhkan alpha."""
        return self.registry.get(alpha_id, {}).get("required_features", [])


# Quick test
if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    print("=" * 60)
    print("ALPHA REGISTRY TEST")
    print("=" * 60)
    
    reg = AlphaRegistry(registry_file="/tmp/alpha_registry_test.json")
    
    # Daftarkan Compression Breakout V1
    entry = reg.register(
        "compression_breakout_v1",
        family="volatility",
        required_features=["bb_width", "atr_ratio", "volume_ratio", "oi_delta"],
        required_context=["compression"],
        timeframes=["5m", "15m", "1h"],
        version="1.0.0",
        state="candidate",
        description="Compression setup → breakout trigger",
    )
    print(f"\nRegistered: {entry['id']} (family={entry['family']})")
    
    print("\nList semua alpha:")
    for a in reg.list_alphas():
        print(f"  {a['id']} [{a['state']}] - {a['description']}")
    
    print(f"\nRequired features: {reg.get_required_features('compression_breakout_v1')}")
    print(f"Timeframes: {reg.get_timeframes('compression_breakout_v1')}")
    
    # Update state ke validated (setelah riset)
    reg.update_state("compression_breakout_v1", "validated")
    print(f"\nSetelah update state: {reg.get('compression_breakout_v1')['state']}")
    
    print("\n" + "=" * 60)
    print("✓ ALPHA REGISTRY OPERATIONAL")
    print("=" * 60)
    
    # Cleanup
    os.remove("/tmp/alpha_registry_test.json")
