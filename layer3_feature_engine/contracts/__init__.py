"""
Layer 3 - Contracts
Definisi tipe, metadata, dan schema untuk feature system.
Ini adalah sumber kebenaran struktur feature yang konsisten.
"""
from .feature_types import FeatureType, FeatureRole, FeatureState, FeatureAvailability
from .feature_metadata import (
    FeatureMetadata, ATOMIC_FEATURES, CONTEXT_FEATURES,
    get_feature_metadata, export_registry_to_json
)
from .feature_schema import FeatureSchema, CURRENT_SCHEMA

__all__ = [
    "FeatureType", "FeatureRole", "FeatureState", "FeatureAvailability",
    "FeatureMetadata", "ATOMIC_FEATURES", "CONTEXT_FEATURES",
    "get_feature_metadata", "export_registry_to_json",
    "FeatureSchema", "CURRENT_SCHEMA",
]
