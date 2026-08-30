"""
Binance Market Data Gateway using cryptofeed
Connect ke Binance WebSocket, kirim data ke normalizer
"""
import asyncio
from cryptofeed import FeedHandler
from cryptofeed.exchanges import Binance

# Normalized output format
NORMALIZED_FORMAT = {
    "exchange": "binance",
    "symbol": None,  # akan di-set per subscription
    "price": None,
    "qty": None,
    "side": None,
    "timestamp": None
}

async def binance_handler(msg):
    """Handle incoming Binance market data"""
    try:
        # msg from cryptofeed sudah memiliki atribut yang standar
        normalized = {
            "exchange": "binance",
            "symbol": msg.symbol,
            "price": msg.price,
            "qty": msg.size,
            "side": msg.side,
            "timestamp": msg.timestamp
        }
        print(f"[BINANCE] {normalized}")
        # TODO: kirim ke normalizer pipeline
    except Exception as e:
        print(f"[ERROR] Binance handler: {e}")

def start_binance_gateway(symbols=None):
    """
    Mulai Binance gateway untuk symbols yang ditentukan
    Default: BTCUSDT, ETHUSDT jika tidak spesifik
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT"]
    
    feed_handler = FeedHandler()
    
    for symbol in symbols:
        # Subscribe to trades and orderbook for each symbol
        feed_handler.add_subscribe(
            Binance,
            symbols=[symbol],
            channels=["trades", "orderbook"]
        )
    
    # Add handler for all feeds
    feed_handler.add_listener(binance_handler)
    
    print(f"[BINANCE GATEWAY] Starting for symbols: {symbols}")
    feed_handler.run()

if __name__ == "__main__":
    import sys
    symbols = sys.argv[1:].split(',') if sys.argv[1:] else None
    start_binance_gateway(symbols)
