#!/usr/bin/env python3
"""
Layer 5 - Registry Setup
Mendaftarkan semua alpha edges ke Alpha Registry dari metadata kelas.
Ini memastikan registry selalu sinkron dengan implementasi.

Setiap edge yang baru dibuat cukup didaftarkan di sini.
"""
import sys
import os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

from layer5_alpha_engine.registry import AlphaRegistry


def register_all():
    """Daftarkan semua alpha edges yang sudah diimplementasikan."""
    reg = AlphaRegistry()
    
    # Edge #1: Compression Breakout V1
    from layer5_alpha_engine.engines.compression_breakout.v1 import CompressionBreakoutV1
    c = CompressionBreakoutV1()
    meta = c.get_metadata()
    reg.register(
        alpha_id=meta["id"],
        family=meta["family"],
        required_features=meta["required_features"],
        required_context=meta["required_context"],
        timeframes=meta["timeframes"],
        version=meta["version"],
        state="candidate",
        description="Compression setup → breakout trigger (Edge #1)",
    )
    print(f"✓ Registered: {meta['id']} (family={meta['family']}, state=candidate)")
    
    return reg


if __name__ == "__main__":
    print("=" * 60)
    print("ALPHA REGISTRY SETUP")
    print("=" * 60)
    reg = register_all()
    
    print("\nSemua alpha terdaftar:")
    for a in reg.list_alphas():
        print(f"  • {a['id']} [{a['state']}] family={a['family']}")
        print(f"      features: {a['required_features']}")
        print(f"      context:  {a['required_context']}")
        print(f"      tfs:      {a['timeframes']}")
    
    print(f"\nRegistry file: {reg.registry_file}")
    print("=" * 60)
