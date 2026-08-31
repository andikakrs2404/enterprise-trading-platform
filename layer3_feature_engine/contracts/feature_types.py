#!/usr/bin/env python3
"""
Layer 3 - Contracts: Feature Types
Definisi tipe-tipe feature yang dipakai seluruh sistem.
Memisahkan ATOMIC (observasi) dari CONTEXT (interpretasi) dari ALPHA (keputusan).

Ini adalah boundary penting:
Feature  → Context → Alpha → Signal
JANGAN langsung: Feature → Signal
"""
from enum import Enum


class FeatureType(Enum):
    """Tipe dasar feature."""
    CONTINUOUS = "continuous"        # Nilai float berkelanjutan (atr_ratio)
    DISCRETE = "discrete"            # Nilai integer/kategori
    BINARY = "binary"                # 0/1
    CATEGORICAL = "categorical"      # Label (regime_name)


class FeatureRole(Enum):
    """
    PERAN feature — INI KUNCI PISAHAN BOUNDARY.
    
    ATOMIC: observasi mentah dari data (tidak ada interpretasi).
        Contoh: atr_ratio=0.52, volume_ratio=0.63, ema_slope=0.004
    
    CONTEXT: interpretasi dari kombinasi atomic features.
        Contoh: volatility_state=EXTREME_LOW, compression_components
        Bukan keputusan trading, hanya state description.
    
    REGIME: klasifikasi kondisi pasar — INI TUGAS LAYER 4, BUKAN LAYER 3.
        Contoh: regime=COMPRESSION
        Diputuskan oleh Layer 4 dari Context features.
    """
    ATOMIC = "atomic"
    CONTEXT = "context"
    REGIME = "regime"        # Dipindah ke Layer 4 / Context Engine


class FeatureState(Enum):
    """Status/state dari sebuah feature value."""
    VALID = "VALID"                  # Siap dipakai
    WARMUP = "WARMUP"                # Belum cukup data (lookback belum terpenuhi)
    EXTREME_LOW = "EXTREME_LOW"      # Percentile < 5%
    LOW = "LOW"                      # Percentile 5-25%
    NORMAL = "NORMAL"                # Percentile 25-75%
    HIGH = "HIGH"                    # Percentile 75-95%
    EXTREME_HIGH = "EXTREME_HIGH"    # Percentile > 95%
    STALE = "STALE"                  # Data tidak update
    MISSING = "MISSING"              # Data tidak ada


class FeatureAvailability(Enum):
    """Kapan feature tersedia."""
    BAR_CLOSE = "bar_close"           # Tersedia di close setiap bar (OHLCV features)
    BAR_OPEN = "bar_open"             # Tersedia di open bar
    REALTIME_TICK = "realtime_tick"   # Tersedia realtime per tick (orderbook)
    REALTIME_ORDERBOOK = "realtime_orderbook"  # Hanya realtime, tidak untuk backtest
    DELAYED = "delayed"               # Tersedia dengan delay tertentu
