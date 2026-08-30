"""
Bybit Market Data Gateway using cryptofeed
Connect ke Bybit WebSocket, kirim data ke normalizer
"""
import asyncio
from cryptofeed import FeedHandler
from cryptofeed.exchanges import Bybit

async def bybit_handler(msg):
    """Handle incoming Bybit market data"""
    try:
        normalized = {
            "exchange": "bybit",
            "symbol": msg.symbol,
            "price": getattr(msg, 'price', getattr(msg, 'last', None)),
            "qty": getattr(msg, 'size', getattr(msg, 'qty', None)),
            "side": getattr(msg, 'side', getattr(msg, 'tickDirection', 'unknown')),
            "timestamp": getattr(msg, 'timestamp', None)
        }
        print(f"[BYBIT] {normalized}")
        # TODO: kirim ke normalizer pipeline
    except Exception as e:
        print(f"[ERROR] Bybit handler: {e}")

def start_bybit_gateway(symbols=None):
    """
    Mulai Bybit gateway untuk symbols yang ditentukan
    Default: BTCUSDT, ETHUSDT jika tidak spesifik
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT"]
    
    feed_handler = FeedHandler()
    
    for symbol in symbols:
        feed_handler.add_subscribe(
            Bybit,
            symbols=[symbol],
            channels=["trades", "orderbook"]
        )
    
    feed_handler.add_listener(bybit_handler)
    
    print(f"[BYBIT GATEWAY] Starting for symbols: {symbols}")
    feed_handler.run()

if __name__ == "__main__":
    import sys
    symbols = sys.argv[1:].split(',') if sys.argv[1:] else None
    start_bybit_gateway(symbols)
