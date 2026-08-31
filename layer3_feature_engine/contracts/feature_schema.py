#!/usr/bin/env python3
"""
Layer 3 - Contracts: Feature Schema
Schema untuk menentukan struktur data feature di Feature Store.
Memastikan konsistensi versi dataset (reproducibility backtest).

Schema versioning diperketat (sesuai rekomendasi):
- feature_version
- dataset_version
- code_version
- config_version
- calculation_version
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import os
import subprocess
import datetime


@dataclass
class FeatureSchema:
    """Schema version untuk feature data."""
    feature_schema: str = "1.0.0"        # Struktur feature
    engine_version: str = "v3"           # Versi engine (v1 deprecated, v2 canonical)
    code_version: str = ""               # Git commit hash (dari git)
    config_version: str = "1.0.0"        # Versi config
    cal_version: str = "1.0.0"           # Versi calculation logic
    
    def __post_init__(self):
        if not self.code_version:
            self.code_version = self._get_git_hash()
    
    def _get_git_hash(self) -> str:
        """Dapatkan git commit hash saat ini (untuk lineage)."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, check=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
    
    def to_dict(self) -> Dict[str, str]:
        """Serialisasi ke dict."""
        return {
            "feature_schema": self.feature_schema,
            "engine_version": self.engine_version,
            "code_version": self.code_version,
            "config_version": self.config_version,
            "cal_version": self.cal_version,
        }
    
    def to_json(self) -> str:
        """Serialisasi ke JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Concrete schema untuk dataset yang dipakai
CURRENT_SCHEMA = FeatureSchema(engine_version="v2", config_version="1.1.0")


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("FEATURE SCHEMA - Versioning Test")
    print("=" * 60)
    
    schema = FeatureSchema(engine_version="v2", config_version="1.1.0")
    print("\nSchema version yang dipakai:")
    print(schema.to_json())
    
    print("\n" + "=" * 60)
    print("✓ Feature Schema Operational")
    print("=" * 60)
