"""
Layer 1 - Market Data Platform
Enterprise-grade cryptocurrency market data pipeline

Components:
1. Market Data Gateway - Connect to multiple exchanges
2. Normalizer - Unified format from diverse exchange formats
3. Time Series Storage - Hot + Cold storage architecture
"""
from .normalizer.normalizer import normalize_to_internal, INTERNAL_FORMAT_SCHEMA
from .gateways.binance.connector import start_binance_gateway
from .gateways.bybit.connector import start_bybit_gateway
from .gateways.okx.connector import start_okx_gateway

__all__ = [
    'normalize_to_internal',
    'INTERNAL_FORMAT_SCHEMA', 
    'start_binance_gateway',
    'start_bybit_gateway',
    'start_okx_gateway',
]

print("[LAYER 1] Market Data Platform initialized")
