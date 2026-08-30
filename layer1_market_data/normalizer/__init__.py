"""
Normalizer Layer 1 - Mengubah format multi-exchange jadi format internal
Masalah: Setiap exchange punya format JSON berbeda
Tuju: Semua data menjadi format internal konsisten
"""
import re
from typing import Dict, Any, Optional

# Format internal yang konsisten di seluruh sistem
INTERNAL_FORMAT_SCHEMA = {
    "exchange": str,       # asal exchange (binance/bybit/okx)
    "symbol": str,         # pasangan mata uang (BTCUSDT)
    "price": float,        # harga
    "qty": float,          # jumlah (quantity)
    "side": str,           # buy/sell
    "timestamp": int       # unix timestamp ms
}

class ExchangeFormatNormalizer:
    """
    Normalizer yang menangani per-bedanya format antar exchange
    """
    
    @staticmethod
    def normalize_binance(data: Dict) -> Dict:
        """
        Normalisasi data dari Binance ke format internal
        Binance format: {'e': '24hrTicker', 'c': 'closePrice', 'q': 'quoteQty', ...}
        """
        try:
            normalized = {
                "exchange": "binance",
                "symbol": data.get('s', 'UNKNOWN').replace('/USDT', 'USDT').replace('/USD', 'USD'),
                "price": float(data.get('c', data.get('lastPrice', 0))),
                "qty": float(data.get('q', data.get('quoteQty', 0))),
                "side": data.get('m', False) and 'sell' or 'buy',  # m = is maker
                "timestamp": int(float(data.get('E', 0)))
            }
            return normalized
        except Exception as e:
            raise ValueError(f"Binance normalize error: {e}")
    
    @staticmethod
    def normalize_bybit(data: Dict) -> Dict:
        """
        Normalisasi data dari Bybit ke format internal
        Bybit format: {'symbol': 'BTCUSDT', 'price': '115000', 'side': 'Buy', 'qty': '1.5', ...}
        """
        try:
            normalized = {
                "exchange": "bybit",
                "symbol": data.get('symbol', 'UNKNOWN'),
                "price": float(data.get('price', 0)),
                "qty": float(data.get('qty', 0)),
                "side": data.get('side', '').lower() or 'buy',
                "timestamp": int(float(data.get('timestamp', 0)))
            }
            return normalized
        except Exception as e:
            raise ValueError(f"Bybit normalize error: {e}")
    
    @staticmethod
    def normalize_okx(data: Dict) -> Dict:
        """
        Normalisasi data dari OKX ke format internal
        OKX format: {'instId': 'BTC-USDT', 'px': '115000', 'sz': '1.5', ...}
        """
        try:
            # OKX symbol format: BTC-USDT -> BTCUSDT
            symbol = data.get('instId', '').replace('-', '')
            normalized = {
                "exchange": "okx",
                "symbol": symbol,
                "price": float(data.get('px', 0)),
                "qty": float(data.get('sz', 0)),
                "side": data.get('side', 'unknown').lower() or 'buy',
                "timestamp": int(float(data.get('ts', 0)))
            }
            return normalized
        except Exception as e:
            raise ValueError(f"OKX normalize error: {e}")
    
    @staticmethod
    def normalize_to_internal(exchange: str, raw_data: Dict) -> Dict:
        """
        Factory method: normalize data based on exchange origin
        """
        try:
            if exchange == "binance":
                return ExchangeFormatNormalizer.normalize_binance(raw_data)
            elif exchange == "bybit":
                return ExchangeFormatNormalizer.normalize_bybit(raw_data)
            elif exchange == "okx":
                return ExchangeFormatNormalizer.normalize_okx(raw_data)
            else:
                raise ValueError(f"Unknown exchange: {exchange}")
        except Exception as e:
            raise ValueError(f"Normalization failed for {exchange}: {e}")

# Testing
if __name__ == "__main__":
    # Test data dari masing-masing exchange
    binance_raw = {
        "e": "24hrTicker",
        "s": "BTCUSDT",
        "c": "115000",
        "q": "1200",
        "E": 1234567890
    }
    
    bybit_raw = {
        "symbol": "BTCUSDT",
        "price": "115000",
        "side": "Buy",
        "qty": "1.5",
        "timestamp": 1234567890
    }
    
    okx_raw = {
        "instId": "BTC-USDT",
        "px": "115000",
        "sz": "1.5",
        "side": "buy",
        "ts": 1234567890
    }
    
    print("=== Normalizer Test ===")
    print(f"Binance: {ExchangeFormatNormalizer.normalize_binance(binance_raw)}")
    print(f"Bybit: {ExchangeFormatNormalizer.normalize_bybit(bybit_raw)}")
    print(f"OKX: {ExchangeFormatNormalizer.normalize_okx(okx_raw)}")
    
    # Test ke format internal
    print("\n=== Ke Format Internal ===")
    print(f"Binance -> Internal: {ExchangeFormatNormalizer.normalize_to_internal('binance', binance_raw)}")
    print(f"Bybit -> Internal: {ExchangeFormatNormalizer.normalize_to_internal('bybit', bybit_raw)}")
    print(f"OKX -> Internal: {ExchangeFormatNormalizer.normalize_to_internal('okx', okx_raw)}")
