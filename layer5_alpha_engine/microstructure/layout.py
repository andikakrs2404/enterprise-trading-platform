#!/usr/bin/env /usr/bin/python3.11
"""
Multi-symbol layout — siapkan struktur data untuk 4 simbol
============================================================
Created: STUDY-016A (BTCUSDT) pilot. Layout untuk perluasan:

  data/micro/BTCUSDT/
  data/micro/ETHUSDT/
  data/micro/SOLUSDT/
  data/micro/BNBUSDT/

Fungsi:
  - ensure_layout(): buat direktori + README untuk setiap simbol
  - move_to_layout(): (jika perlu) reorganisasi data existing
"""
from pathlib import Path
import json

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
BASE = Path(__file__).resolve().parent.parent / "data" / "micro"

README_TEMPLATE = """# {symbol} — Microstructure Data

**Status:** {status}
**Collector:** STUDY-016A (REST-only, systemd `study016a-collector`)
**Format:** Parquet per hari (`YYYYMMDD/`)

## Files
- `aggTrades_*` — agg trade level (agg_id, price, qty, ts_ms, is_buyer_maker)
- `depth_*` — L2 depth snapshot 100 levels (bids, asks, recv_ms)
- `bookTicker_*` — best bid/ask (bidPrice, askPrice, time, recv_ms)

## Quality Gates (STUDY-016A)
- aggTrades: zero-gap (agg_id continuity)
- depth: snapshot ≥ 1s (acl: resolution ~3.6s saat ini)
- spread: diukur dari depth (bps of mid)

## Symbols
{symbols}
"""


def ensure_layout():
    for sym in SYMBOLS:
        d = BASE / sym
        d.mkdir(parents=True, exist_ok=True)
        readme = d / "README.md"
        if not readme.exists():
            status = "PILOT RUNNING" if sym == "BTCUSDT" else "EMPTY (planned)"
            readme.write_text(README_TEMPLATE.format(
                symbol=sym, status=status,
                symbols="\n".join(f"- {s}" for s in SYMBOLS)))
    manifest = BASE / "LAYOUT_MANIFEST.json"
    manifest.write_text(json.dumps({
        "program": "STUDY-016",
        "symbols": SYMBOLS,
        "status": {
            "BTCUSDT": "collector running (systemd)",
            "ETHUSDT": "planned",
            "SOLUSDT": "planned",
            "BNBUSDT": "planned",
        },
        "format": "parquet per symbol per day",
        "collector": "collector_btcusdt_rest.py",
    }, indent=2))
    return manifest


if __name__ == "__main__":
    m = ensure_layout()
    print(f"Layout manifest: {m}")
    for sym in SYMBOLS:
        d = BASE / sym
        files = list(d.glob("README.md"))
        print(f"  {sym}: {'OK' if files else 'MISSING'}")
    print(f"Created layout for {len(SYMBOLS)} symbols")