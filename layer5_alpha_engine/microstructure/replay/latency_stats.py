#!/usr/bin/env /usr/bin/python3.11
"""
Latency Measurement — exchange_ts vs collector_ts
===================================================
Setiap record punya exchange_ts (T/E/time) dan collector_ts (recv_ms).
Latency = collector_ts - exchange_ts.

Statistik yang dilaporkan: mean, median, p95, p99, max, min (ms).
Termasuk: deteksi clock drift (latency negatif = clock offset).
"""
import numpy as np
import pandas as pd
from pathlib import Path


def latency_from_depth(depth_dir: Path):
    """Latency dari depth snapshots: recv_ms - E (exchange event time)."""
    files = sorted(Path(depth_dir).glob("*/depth_*.parquet"))
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    if "E" not in df.columns or "recv_ms" not in df.columns:
        return None
    lat = (df["recv_ms"] - df["E"]).dropna()
    return latency_stats(lat, "depth")


def latency_from_aggtrades(sym_dir: Path):
    """Latency daritrades: recv_ms - T. NOTE: aggTrades WS tidak punya recv_ms
    (hanya REST yang isi T). fallback: estimator dari bookTicker time vs recv.
    """
    files = sorted(Path(sym_dir).glob("*/aggTrades_*.parquet"))
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    if "recv_ms" not in df.columns:
        return {"note": "aggTrades tidak punya recv_ms (REST-only) — latency tidak tersedia"}
    lat = (df["recv_ms"] - df["ts_ms"]).dropna()
    return latency_stats(lat, "trade")


def latency_from_tickers(sym_dir: Path):
    """bookTicker latency: recv_ms - time."""
    files = sorted(Path(sym_dir).glob("*/bookTicker_*.parquet"))
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    if "recv_ms" not in df.columns or "time" not in df.columns:
        return None
    lat = (df["recv_ms"] - df["time"]).dropna()
    return latency_stats(lat, "ticker")


def latency_stats(lat, source):
    if lat is None or len(lat) == 0:
        return {"source": source, "n": 0, "note": "no data"}
    lat = lat.astype(float)
    arr = lat.values
    return {
        "source": source,
        "n": int(len(arr)),
        "mean_ms": round(float(arr.mean()), 2),
        "median_ms": round(float(np.median(arr)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "p99_ms": round(float(np.percentile(arr, 99)), 2),
        "max_ms": round(float(arr.max()), 2),
        "min_ms": round(float(arr.min()), 2),
        "neg_count": int((arr < 0).sum()),  # clock drift indicator
        "pct_neg": round(float((arr < 0).mean() * 100), 2),
    }


if __name__ == "__main__":
    import sys
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("layer5_alpha_engine/data/micro/BTCUSDT")
    print("=== LATENCY (collector_ts - exchange_ts) ===")
    for fn, src in [(latency_from_depth, "depth"),
                    (latency_from_tickers, "ticker")]:
        r = fn(base)
        if r:
            print(f"\n[{src}]")
            for k, v in r.items():
                print(f"  {k}: {v}")
    r = latency_from_aggtrades(base)
    if r:
        print(f"\n[trade]")
        for k, v in r.items():
            print(f"  {k}: {v}")