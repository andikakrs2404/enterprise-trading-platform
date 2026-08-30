"""
Normalizer Module - Main entry point
Menggabungkan semua normalize functions
"""
from typing import Dict

# Lazy import - import di dalam fungsi untuk menghindari module-level import issues
# Ketika normalize_to_internal dipanggil, kita import normal_format di situ

__all__ = [
    'ExchangeFormatNormalizer',
    'INTERNAL_FORMAT_SCHEMA',
    'normalize_to_internal',
]

# Placeholder - akan di-set saat fungsi pertama kali dipanggil
_ExchangeFormatNormalizer = None
_INTERNAL_FORMAT_SCHEMA = None

def _ensure_imports():
    """Ensure normal_format modules are imported (lazy loading)"""
    global _ExchangeFormatNormalizer, _INTERNAL_FORMAT_SCHEMA
    if _ExchangeFormatNormalizer is None or _INTERNAL_FORMAT_SCHEMA is None:
        try:
            from layer1_market_data.normalizer.normal_format import ExchangeFormatNormalizer, INTERNAL_FORMAT_SCHEMA
        except ImportError:
            # Fallback: import dari direktori saat ini
            import normal_format
            _ExchangeFormatNormalizer = normal_format.ExchangeFormatNormalizer
            _INTERNAL_FORMAT_SCHEMA = normal_format.INTERNAL_FORMAT_SCHEMA

def normalize_to_internal(exchange: str, raw_data: Dict) -> Dict:
    """
    Main entry point for normalizing raw exchange data
    """
    _ensure_imports()
    return _ExchangeFormatNormalizer.normalize_to_internal(exchange, raw_data)

if __name__ == "__main__":
    import sys
    from pprint import pprint
    
    test_cases = [
        ("binance", {"e": "24hrTicker", "s": "BTCUSDT", "c": "115000", "q": "1200", "E": 1234567890}),
        ("bybit", {"symbol": "BTCUSDT", "price": "115000", "side": "Buy", "qty": "1.5", "timestamp": 1234567890}),
        ("okx", {"instId": "BTC-USDT", "px": "115000", "sz": "1.5", "side": "buy", "ts": 1234567890}),
    ]
    
    print("=" * 60)
    print("NORMALIZER MODULE TEST")
    print("=" * 60)
    
    all_passed = True
    for exchange, data in test_cases:
        try:
            result = normalize_to_internal(exchange, data)
            pprint(result)
            print(f"  ✓ {exchange} OK")
        except Exception as e:
            print(f"  ✗ {exchange}: FAILED - {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if all_passed else 1)
