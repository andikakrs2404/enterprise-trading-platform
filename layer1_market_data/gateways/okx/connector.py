"""
OKX Market Data Gateway using cryptofeed
Connect ke OKX WebSocket, kirim data ke normalizer
"""
import asyncio
from cryptofeed import FeedHandler
from cryptofeed.exchanges import OKX

async def okx_handler(msg):
    """Handle incoming OKX market data"""
    try:
        normalized = {
            "exchange": "okx",
            "symbol": msg.symbol,
            "price": getattr(msg, 'price', getattr(msg, 'last', None)),
            "qty": getattr(msg, 'size', getattr(msg, 'qty', None)),
            "side": getattr(msg, 'side', getattr(msg, 'tickDirection', 'unknown')),
            "timestamp": getattr(msg, 'timestamp', None)
        }
        print(f"[OKX] {normalized}")
        # TODO: kirim ke normalizer pipeline
    except Exception as e:
        print(f"[ERROR] OKX handler: {e}")

def start_okx_gateway(symbols=None):
    """
    Mulai OKX gateway untuk symbols yang ditentukan
    Default: BTCUSDT, ETHUSDT jika tidak spesifik
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT"]
    
    feed_handler = FeedHandler()
    
    for symbol in symbols:
        feed_handler.add_subscribe(
            OKX,
            symbols=[symbol],
            channels=["trades", "orderbook"]
        )
    
    feed_handler.add_listener(okx_handler)
    
    print(f"[OKX GATEWAY] Starting for symbols: {symbols}")
    feed_handler.run()

if __name__ == "__main__":
    import sys
    symbols = sys.argv[1:].split(',') if sys.argv[1:] else None
    start_okx_gateway(symbols)
