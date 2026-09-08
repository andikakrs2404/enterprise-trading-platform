#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016B — Economic Feasibility Baseline
==========================================
Measure distribution of 5-180s forward returns from aggTrades (BTCUSDT futures)
BEFORE any signal discovery. Determines if the prediction problem is worth
solving given transaction costs (fee + spread + slippage).

Usage:
  /usr/bin/python3.11 run_study016B_economic.py --data data/micro/BTCUSDT

Output:
  STUDY-016B_ECONOMIC.json + console table
"""
import argparse, json, glob, sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = Path("/home/rtk/enterprise-trading-platform/layer5_alpha_engine/data/micro")

# Cost model (locked, Binance futures)
FEE_TAKER_RT_BPS = 8.0   # 4 bps per side
FEE_MAKER_RT_BPS = 4.0   # 2 bps per side
HORIZONS = [5, 15, 30, 60, 180]

def load_aggtrades(sym_dir: Path):
    files = sorted(sym_dir.glob("*/aggTrades_*.parquet"))
    if not files:
        print(f"NO aggTrades files in {sym_dir}", file=sys.stderr)
        sys.exit(1)
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.drop_duplicates('agg_id').sort_values('ts_ms').reset_index(drop=True)
    return df

def build_1s_price(df):
    """1s bar from trade price (last trade per second)."""
    s = pd.Series(df['price'].values.astype(float), index=pd.to_datetime(df['ts_ms'], unit='ms', utc=True))
    # last price per second
    bars = s.resample('1s').last().dropna()
    return bars

def forward_returns(price_1s, horizons):
    """Overlapping forward returns in bps."""
    p = price_1s.values
    ts = price_1s.index
    out = {}
    for h in horizons:
        # vectorized: R(t) = P(t+h)/P(t) - 1 (in bps)
        r = (p[h:] / p[:-h] - 1.0) * 10000
        out[h] = r
    return out

def non_overlap_returns(price_1s, h):
    """Non-overlap grid returns for sanity (HAC)."""
    p = price_1s.values
    idx = np.arange(0, len(p) - h, h)
    r = (p[idx + h] / p[idx] - 1.0) * 10000
    return r

def dist_stats(r):
    r = np.asarray(r, dtype=float)
    if len(r) == 0:
        return None
    return {
        'n': int(len(r)),
        'median_abs_bps': round(float(np.median(np.abs(r))), 3),
        'p75_abs_bps': round(float(np.percentile(np.abs(r), 75)), 3),
        'p90_abs_bps': round(float(np.percentile(np.abs(r), 90)), 3),
        'p95_abs_bps': round(float(np.percentile(np.abs(r), 95)), 3),
        'p99_abs_bps': round(float(np.percentile(np.abs(r), 99)), 3),
        'max_abs_bps': round(float(np.abs(r).max()), 3),
        'mean_abs_bps': round(float(np.mean(np.abs(r))), 3),
        'median_signed_bps': round(float(np.median(r)), 3),
        'mean_signed_bps': round(float(np.mean(r)), 3),
        'skew': round(float(pd.Series(r).skew()), 3),
        'std_bps': round(float(r.std()), 3),
    }

def verdict(stat, fee_rt):
    """Apply economic gates G1/G2/G3 per horizon."""
    if stat is None:
        return 'NO_DATA'
    g1 = stat['median_abs_bps'] >= fee_rt
    g2 = stat['p90_abs_bps'] >= 2 * fee_rt
    g3 = stat['n'] >= 1000
    if g1 and g2 and g3:
        return f'LAYAK (G1+G2+G3)'
    elif g2 and g3:
        return f'LAYAK_EVENT_ONLY (G2+G3, median<fee)'
    elif g3:
        return f'MARJINAL (G3 only)'
    else:
        return f'TIDAK_LAYAK'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(DATA / 'BTCUSDT'))
    a = ap.parse_args()
    sym_dir = Path(a.data)
    print(f"[STUDY-016B] Loading aggTrades from {sym_dir}")
    df = load_aggtrades(sym_dir)
    print(f"  aggTrades rows: {len(df)}")
    span_h = (df['ts_ms'].max() - df['ts_ms'].min()) / 3600000
    print(f"  span: {span_h:.2f} h")

    price_1s = build_1s_price(df)
    print(f"  1s bars: {len(price_1s)}")

    fr = forward_returns(price_1s, HORIZONS)

    print("\n" + "="*100)
    print(f"ECONOMIC FEASIBILITY — BTCUSDT futures | fee taker RT={FEE_TAKER_RT_BPS}bps | maker RT={FEE_MAKER_RT_BPS}bps")
    print("="*100)
    hdr = f"{'H':>5} | {'n':>9} | {'med|R|':>8} {'p75':>7} {'p90':>7} {'p95':>7} {'p99':>7} {'max':>7} | {'medR':>7} {'skew':>6} | {'NON-OVERLAP med':>15} | VERDICT"
    print(hdr)
    print("-"*100)

    report = {'symbol': sym_dir.name,
              'span_hours': round(span_h, 2),
              'agg_rows': len(df),
              'fee_taker_rt_bps': FEE_TAKER_RT_BPS,
              'fee_maker_rt_bps': FEE_MAKER_RT_BPS,
              'horizons': {}}
    for h in HORIZONS:
        st = dist_stats(fr[h])
        no = dist_stats(non_overlap_returns(price_1s, h))
        v = verdict(st, FEE_TAKER_RT_BPS)
        if st:
            print(f"{h:>5} | {st['n']:>9,} | {st['median_abs_bps']:>8.3f} {st['p75_abs_bps']:>7.3f} "
                  f"{st['p90_abs_bps']:>7.3f} {st['p95_abs_bps']:>7.3f} {st['p99_abs_bps']:>7.3f} {st['max_abs_bps']:>7.3f} | "
                  f"{st['median_signed_bps']:>7.3f} {st['skew']:>6.2f} | "
                  f"{no['median_abs_bps'] if no else 0:>15.3f} | {v}")
        report['horizons'][str(h)] = {'overlap': st, 'non_overlap': no, 'verdict': v}

    # Summary verdict
    ok_h = [h for h in HORIZONS if 'LAYAK' in report['horizons'][str(h)]['verdict']]
    print("\n" + "="*100)
    if not ok_h:
        print("VERDICT: TIDAK ADA horizon layak secara ekonomi (median |R| < fee).")
        print("-> STOP trade-flow discovery, dokumentasikan temuan negatif.")
    else:
        print(f"VERDICT: Horizon layak utk eksplorasi: {ok_h}")
        print("-> Lanjut STUDY-017 dengan family feature (hanya utk horizon layak).")
    print("="*100)

    out = Path(__file__).resolve().parent / 'STUDY-016B_ECONOMIC.json'
    with open(out, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved -> {out}")

if __name__ == '__main__':
    main()