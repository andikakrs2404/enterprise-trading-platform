#!/usr/bin/env /usr/bin/python3.11
"""
Tardis Sample Fetcher — download file gratis (hari pertama bulan, tanpa API key)
=================================================================================
Free samples: dataset untuk hari pertama tiap bulan tersedia TANPA API key.
Ini cukup untuk compatibility gate (schema/timestamp/reconstruction/determinism).

Usage:
  python3.11 tardis_sample_fetcher.py --out /tmp/tardis_sample \
      --date 2024-01-01 --symbol BTCUSDT

Downloads:
  - trades BTCUSDT (per-symbol, kecil ~20MB)
  - incremental_book_L2 FUTURES (145MB — subset via head header+baris pertama)
"""
import argparse, urllib.request, gzip, os, sys
from pathlib import Path

BASE = "https://datasets.tardis.dev/v1/binance-futures"

def download(url, dest, max_bytes=None):
    """Download with optional size cap (streaming, stop after max_bytes)."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, 'wb') as f:
        total = 0
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if max_bytes and total >= max_bytes:
                break
    return dest

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/tardis_sample')
    ap.add_argument('--date', default='2024-01-01', help='first day of month (free)')
    ap.add_argument('--symbol', default='BTCUSDT')
    ap.add_argument('--max-l2-mb', type=int, default=30,
                    help='cap L2 download size (MB) untuk sample kecil')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    y, m, d = a.date.split('-')

    # Trades per-symbol (small)
    trades_url = f"{BASE}/trades/{y}/{m}/{d}/{a.symbol}.csv.gz"
    trades_dest = out / f"trades_{a.symbol}_{a.date}.csv.gz"
    if not trades_dest.exists():
        print(f"Download trades: {trades_url}")
        download(trades_url, trades_dest)
        print(f"  -> {trades_dest} ({trades_dest.stat().st_size/1e6:.1f} MB)")
    else:
        print(f"  trades already cached: {trades_dest}")

    # L2 incremental FUTURES (big) — download capped
    l2_url = f"{BASE}/incremental_book_L2/{y}/{m}/{d}/FUTURES.csv.gz"
    l2_dest = out / f"l2_FUTURES_{a.date}.csv.gz"
    if not l2_dest.exists():
        print(f"Download L2 (capped {a.max_l2_mb}MB): {l2_url}")
        max_bytes = a.max_l2_mb * 1024 * 1024
        download(l2_url, l2_dest, max_bytes=max_bytes)
        size_mb = l2_dest.stat().st_size / 1e6
        print(f"  -> {l2_dest} ({size_mb:.1f} MB, capped)")
    else:
        print(f"  l2 already cached: {l2_dest}")

    print("\nSamples ready:")
    for f in sorted(out.glob('*.csv.gz')):
        print(f"  {f.name} ({f.stat().st_size/1e6:.1f} MB)")
    print(f"\nRun gate: python3.11 tardis_compat_gate.py --sample-dir {out}")

if __name__ == '__main__':
    main()