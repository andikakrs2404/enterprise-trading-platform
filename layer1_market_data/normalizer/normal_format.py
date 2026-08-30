"""
Normalizer Format Module - Definisi format dan fungsi normalisasi per-exchange
"""
from typing import Dict, Any, Optional

# Format internal yang konsisten di seluruh sistem trading
INTERNAL_FORMAT_SCHEMA = {
    "exchange": str,
    "symbol": str,
    "price": float,
    "qty": float,
    "side": str,
    "timestamp": int
}

class ExchangeFormatNormalizer:
    """Class berisi metode normalisasi untuk setiap exchange"""
    
    @staticmethod
    def normalize_binance(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisasi data dari Binance ke format internal"""
        try:
            raw_symbol = data.get('s', 'UNKNOWN')
            symbol = raw_symbol.replace('/', '').replace('-', '').upper()
            price = float(data.get('c', data.get('lastPrice', data.get('p', 0))))
            qty = float(data.get('q', data.get('quoteQty', data.get('sz', 0))))
            maker = data.get('m', False)
            side = "sell" if maker else "buy"
            timestamp = int(float(data.get('E', 0)))
            
            normalized = {
                "exchange": "binance",
                "symbol": symbol,
                "price": price,
                "qty": qty,
                "side": side,
                "timestamp": timestamp
            }
            if price <= 0: raise ValueError(f"Invalid price: {price}")
            if qty <= 0: raise ValueError(f"Invalid qty: {qty}")
            return normalized
        except Exception as e:
            raise ValueError(f"Binance normalize error: {e}")
    
    @staticmethod
    def normalize_bybit(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisasi data dari Bybit ke format internal"""
        try:
            raw_symbol = data.get('symbol', 'UNKNOWN')
            symbol = raw_symbol.replace('/', '').replace('-', '').upper()
            price = float(data.get('price', 0))
            qty = float(data.get('qty', 0))
            raw_side = data.get('side', '')
            side = raw_side.strip().lower()
            if side in ['buy', 'b']: side = "buy"
            elif side in ['sell', 's']: side = "sell"
            else: side = "unknown"
            timestamp = int(float(data.get('timestamp', 0)))
            
            normalized = {
                "exchange": "bybit",
                "symbol": symbol,
                "price": price,
                "qty": qty,
                "side": side,
                "timestamp": timestamp
            }
            if price <= 0: raise ValueError(f"Invalid price: {price}")
            if qty <= 0: raise ValueError(f"Invalid qty: {qty}")
            return normalized
        except Exception as e:
            raise ValueError(f"Bybit normalize error: {e}")
    
    @staticmethod
    def normalize_okx(data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalisasi data dari OKX ke format internal"""
        try:
            raw_symbol = data.get('instId', '')
            symbol = raw_symbol.replace('-', '').upper()
            price = float(data.get('px', 0))
            qty = float(data.get('sz', 0))
            raw_side = data.get('side', '')
            side = raw_side.strip().lower()
            if side in ['buy', 'b']: side = "buy"
            elif side in ['sell', 's']: side = "sell"
            else: side = "unknown"
            timestamp = int(float(data.get('ts', 0)))
            
            normalized = {
                "exchange": "okx",
                "symbol": symbol,
                "price": price,
                "qty": qty,
                "side": side,
                "timestamp": timestamp
            }
            if price <= 0: raise ValueError(f"Invalid price: {price}")
            if qty <= 0: raise ValueError(f"Invalid qty: {qty}")
            return normalized
        except Exception as e:
            raise ValueError(f"OKX normalize error: {e}")
    
    @staticmethod
    def normalize_to_internal(exchange: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Factory method: pilih normalisasi berdasarkan exchange asal"""
        if exchange == "binance":
            return ExchangeFormatNormalizer.normalize_binance(raw_data)
        elif exchange == "bybit":
            return ExchangeFormatNormalizer.normalize_bybit(raw_data)
        elif exchange == "okx":
            return ExchangeFormatNormalizer.normalize_okx(raw_data)
        else:
            raise ValueError(f"Unknown exchange: {exchange}. Supported: binance, bybit, okx")
