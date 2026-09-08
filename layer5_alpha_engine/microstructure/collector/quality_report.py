#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016A — Quality Report Generator
======================================
Evaluates collected microstructure data and generates a quality report
per protocol STUDY-016 section 3 (gap detection + quality gates).

Usage:
  /usr/bin/python3.11 quality_report.py --symbol BTCUSDT --dir data/micro/BTCUSDT

Output:
  Prints quality metrics; writes data/micro/BTCUSDT/quality_report.json
"""
import argparse, json, os, sys, datetime as dt
from pathlib import Path
import pandas as pd
import numpy as np

def day_str(ts_ms):
    return dt.datetime.fromtimestamp(ts_ms/1000, tz=dt.timezone.utc).strftime("%Y%m%d")

def analyze_aggtrades(dirpath):
    """Check aggTrade id continuity, completeness, gaps."""
    files = sorted(Path(dirpath).glob("*/aggTrades_*.parquet"))
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.drop_duplicates('agg_id').sort_values('agg_id').reset_index(drop=True)
    ids = df['agg_id'].values
    gaps = []
    for i in range(len(ids)-1):
        if ids[i+1] != ids[i] + 1:
            gaps.append((int(ids[i]), int(ids[i+1])))
    n_gaps = len(gaps)
    gap_rows = sum(b - a - 1 for a, b in gaps)
    total_span = ids[-1] - ids[0] + 1 if len(ids) > 1 else 0
    completeness = (len(ids) / total_span * 100) if total_span > 0 else 0
    # temporal coverage
    ts = pd.to_datetime(df['ts_ms'], unit='ms', utc=True)
    span_h = (ts.max() - ts.min()).total_seconds() / 3600
    # trade intensity
    tps = len(df) / max(span_h * 3600, 1)
    return {
        'file_count': len(files),
        'rows': len(df),
        'id_min': int(ids[0]) if len(ids) else None,
        'id_max': int(ids[-1]) if len(ids) else None,
        'n_gaps': n_gaps,
        'gap_rows': gap_rows,
        'completeness_pct': round(completeness, 3),
        'span_hours': round(span_h, 2),
        'avg_trades_per_sec': round(tps, 2),
        'first_ts': str(ts.min()),
        'last_ts': str(ts.max()),
        'largest_gap': max((b-a for a,b in gaps), default=0),
        'gap_samples': gaps[:20],
    }

def analyze_depth(dirpath):
    """Check depth snapshot count vs expected (1/s), time gaps."""
    files = sorted(Path(dirpath).glob("*/depth_*.parquet"))
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.sort_values('recv_ms').reset_index(drop=True)
    ts = pd.to_datetime(df['recv_ms'], unit='ms', utc=True)
    span_s = (ts.max() - ts.min()).total_seconds()
    expected = span_s / 1.0  # 1 snapshot per second
    coverage = len(df) / expected * 100 if expected > 0 else 0
    # gap in recv_ms
    deltas = df['recv_ms'].diff().dropna()
    big_gaps = (deltas > 3000).sum()  # >3s gap
    # depth validity: check bids/asks parseable
    valid = 0
    for _, row in df.iterrows():
        try:
            if isinstance(row['bids'], (list, np.ndarray)) and len(row['bids']) > 0:
                valid += 1
        except Exception:
            pass
    return {
        'rows': len(df),
        'span_hours': round(span_s/3600, 2),
        'coverage_pct': round(coverage, 2),
        'big_gaps_3s': int(big_gaps),
        'valid_snapshots': valid,
        'best_bid_ask_sample': _sample_book(df),
    }

def _sample_book(df):
    """Return first valid top-of-book."""
    for _, row in df.iterrows():
        try:
            bids, asks = row['bids'], row['asks']
            if isinstance(bids, list) and isinstance(asks, list) and bids and asks:
                return {'best_bid': float(bids[0][0]), 'bid_qty': float(bids[0][1]),
                        'best_ask': float(asks[0][0]), 'ask_qty': float(asks[0][1]),
                        'spread_pct': (float(asks[0][0])-float(bids[0][0]))/float(bids[0][0])*100}
        except Exception:
            continue
    return None

def spread_distribution(dirpath):
    """Compute spread distribution from depth snapshots (bps of mid)."""
    files = sorted(Path(dirpath).glob("*/depth_*.parquet"))
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    spreads_bps = []
    for _, row in df.iterrows():
        try:
            bids, asks = row['bids'], row['asks']
            if not (isinstance(bids, (list, np.ndarray)) and isinstance(asks, (list, np.ndarray))):
                continue
            if len(bids) == 0 or len(asks) == 0:
                continue
            bb = float(bids[0][0]); ba = float(asks[0][0])
            if bb <= 0 or ba <= 0 or ba < bb:
                continue
            mid = (bb + ba) / 2
            spreads_bps.append((ba - bb) / mid * 10000)
        except Exception:
            continue
    if not spreads_bps:
        return None
    arr = np.array(spreads_bps)
    return {
        'n_snapshots_used': len(arr),
        'spread_mean_bps': round(float(arr.mean()), 4),
        'spread_median_bps': round(float(np.median(arr)), 4),
        'spread_p95_bps': round(float(np.percentile(arr, 95)), 4),
        'spread_p99_bps': round(float(np.percentile(arr, 99)), 4),
        'spread_max_bps': round(float(arr.max()), 4),
        'spread_min_bps': round(float(arr.min()), 4),
        'spread_std_bps': round(float(arr.std()), 4),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default='BTCUSDT')
    ap.add_argument('--dir', default=None, help='data/micro/<SYM>')
    a = ap.parse_args()
    d = Path(a.dir) if a.dir else Path(f'data/micro/{a.symbol}')
    if not d.exists():
        # try repo-relative
        d = Path('/home/rtk/enterprise-trading-platform/layer5_alpha_engine') / d
    print(f"Quality report for {a.symbol} in {d}")
    report = {'symbol': a.symbol, 'dir': str(d), 'generated': str(dt.datetime.now(dt.timezone.utc))}
    agg = analyze_aggtrades(d)
    dep = analyze_depth(d)
    report['aggTrades'] = agg
    report['depth'] = dep
    # spread distribution from depth snapshots
    spread = spread_distribution(d)
    report['spread'] = spread

    print("\n" + "="*60)
    print("AGGTRADES")
    print("="*60)
    if agg:
        for k, v in agg.items():
            if k != 'gap_samples':
                print(f"  {k:<22}: {v}")
        print(f"  gaps: {agg['n_gaps']} ({agg['gap_rows']} missing rows) — completeness {agg['completeness_pct']}%")

    print("\n" + "="*60)
    print("SPREAD DISTRIBUTION (bps of mid)")
    print("="*60)
    if spread:
        for k, v in spread.items():
            print(f"  {k:<22}: {v}")

    print("\n" + "="*60)
    print("DEPTH")
    print("="*60)
    if dep:
        for k, v in dep.items():
            if k != 'best_bid_ask_sample':
                print(f"  {k:<22}: {v}")
        if dep['best_bid_ask_sample']:
            s = dep['best_bid_ask_sample']
            print(f"  sample spread: {s['spread_pct']:.4f}% (bid {s['best_bid']} ask {s['best_ask']})")

    out = d / 'quality_report.json'
    with open(out, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved -> {out}")

if __name__ == '__main__':
    main()