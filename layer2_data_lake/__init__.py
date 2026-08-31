"""
Layer 2 - Data Lake & Quality Foundation
Modular sub-structure: core, config, validators, features, storage
"""
from .core.data_quality import DataQualityValidator, QualityIssue
from .core.timestamp_alignment import TimestampAligner

__all__ = [
    'DataQualityValidator',
    'QualityIssue',
    'TimestampAligner',
]

print("[LAYER 2] Data Lake & Quality Foundation initialized")
