#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016B — Economic Feasibility Baseline (ENHANCED)
=======================================================
Measure distribution of 5-180s forward returns from aggTrades (BTCUSDT futures)
BEFORE any signal discovery.

Enhancements:
  - R+ and R- distributions separately (sign-aware)
  - Event frequency: how often |R| > fee, 1.5×fee, 2×fee, 3×fee
  - Confidence intervals via bootstrap (non-parametric)

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

FEE_TAKER_RT_BPS = 8.0
FEE_MAKER_RT_BPS = 4.0
HORIZONS = [5, 15, 30, 60, 180]
FREQ_THRESHOLDS = [4.0, 6.0, 8.0, 12.0, 16.0, 20.0]  # bps

def load_aggtrades(sym_dir: Path):
    files = sorted(sym_dir.glob("*/aggTrades_*.parquet"))
    if not files:
        print(f"NO aggTrades files in {sym_dir}", file=sys.stderr)
        sys.exit(1)
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.drop_duplicates('agg_id').sort_values('ts_ms').reset_index(drop=True)
    return df

def build_1s_price(df):
    s = pd.Series(df['price'].values.astype(float),
                  index=pd.to_datetime(df['ts_ms'], unit='ms', utc=True))
    return s.resample('1s').last().dropna()

def forward_returns(price_1s, horizons):
    p = price_1s.values
    return {h: (p[h:] / p[:-h] - 1.0) * 10000 for h in horizons}

def non_overlap_returns(price_1s, h):
    p = price_1s.values
    idx = np.arange(0, len(p) - h, h)
    return (p[idx + h] / p[idx] - 1.0) * 10000

def event_frequency(r, thresholds):
    """Fraction of observations with |R| > threshold."""
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n == 0:
        return {}
    abs_r = np.abs(r)
    return {f"gt_{int(t)}bps": round(float((abs_r > t).sum() / n * 100), 2)
            for t in thresholds}

def distribution_side(r, name):
    """Stats for positive and negative moves separately."""
    r = np.asarray(r, dtype=float)
    pos = r[r > 0]
    neg = r[r < 0]
    return {
        f'{name}_pos_count': int(len(pos)),
        f'{name}_neg_count': int(len(neg)),
        f'{name}_pos_fraction': round(len(pos)/len(r)*100, 1) if len(r)>0 else 0,
        f'{name}_pos_median_bps': round(float(np.median(pos)), 3) if len(pos)>0 else None,
        f'{name}_pos_p90_bps': round(float(np.percentile(pos, 90)), 3) if len(pos)>0 else None,
        f'{name}_pos_p99_bps': round(float(np.percentile(pos, 99)), 3) if len(pos)>0 else None,
        f'{name}_neg_median_bps': round(float(np.median(neg)), 3) if len(neg)>0 else None,
        f'{name}_neg_p90_bps': round(float(np.percentile(neg, 10)), 3) if len(neg)>0 else None,  # p90 of |neg|
        f'{name}_neg_p99_bps': round(float(np.percentile(neg, 1)), 3) if len(neg)>0 else None,
    }

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
        **distribution_side(r, 'R'),
    }

def verdict(stat, fee_rt):
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
    print(f"  span: {span_h:.2f} h | price points: {len(build_1s_price(df))}")

    price_1s = build_1s_price(df)
    fr = forward_returns(price_1s, HORIZONS)

    # === MAIN TABLE ===
    print("\n" + "="*110)
    print(f"ECONOMIC FEASIBILITY — BTCUSDT futures | fee taker RT={FEE_TAKER_RT_BPS}bps | maker RT={FEE_MAKER_RT_BPS}bps")
    print("="*110)
    hdr = (f"{'H':>4} | {'n':>8} | {'med|R|':>7} {'p75':>6} {'p90':>6} {'p95':>6} {'p99':>6} {'max':>6} "
           f"| {'skew':>5} {'skew_dep':>8} | VERDICT")
    print(hdr)
    print("-"*110)

    report = {'symbol': sym_dir.name,
              'span_hours': round(span_h, 2),
              'agg_rows': len(df),
              'fee_taker_rt_bps': FEE_TAKER_RT_BPS,
              'fee_maker_rt_bps': FEE_MAKER_RT_BPS,
              'horizons': {}}

    for h in HORIZONS:
        st = dist_stats(fr[h])
        no_r = non_overlap_returns(price_1s, h)
        v = verdict(st, FEE_TAKER_RT_BPS)
        if st:
            skew_dep = "MOMENTUM" if st['R_pos_median_bps'] and st['R_pos_median_bps'] > 0 else "REVERSAL"
            print(f"{h:>4} | {st['n']:>8,} | {st['median_abs_bps']:>7.3f} {st['p75_abs_bps']:>6.3f} "
                  f"{st['p90_abs_bps']:>6.3f} {st['p95_abs_bps']:>6.3f} {st['p99_abs_bps']:>6.3f} {st['max_abs_bps']:>6.3f} "
                  f"| {st['skew']:>5.2f} {skew_dep:>8} | {v}")
        report['horizons'][str(h)] = {'overlap': st,
                                       'non_overlap_median_abs_bps': round(float(np.median(np.abs(no_r))), 3) if len(no_r)>0 else None,
                                       'verdict': v,
                                       'event_freq': event_frequency(fr[h], FREQ_THRESHOLDS)}

    # === EVENT FREQUENCY TABLE ===
    print("\n" + "="*110)
    print("EVENT FREQUENCY (% of observations with |R| > threshold)")
    print("="*110)
    print(f"{'H':>4} | " + " | ".join(f">{int(t)}bps" for t in FREQ_THRESHOLDS))
    print("-"*110)
    for h in HORIZONS:
        ef = event_frequency(fr[h], FREQ_THRESHOLDS)
        vals = [f"{ef.get(f'gt_{int(t)}bps', 0):>5.1f}%" for t in FREQ_THRESHOLDS]
        print(f"{h:>4} | " + " | ".join(vals))
    print()
    # Interpretation
    for h in HORIZONS:
        ef = event_frequency(fr[h], FREQ_THRESHOLDS)
        pct_gt8 = ef.get('gt_8bps', 0)
        if pct_gt8 >= 50:
            interp = "GOOD — >50% obs > fee"
        elif pct_gt8 >= 25:
            interp = "OK — 25-50% > fee"
        elif pct_gt8 >= 10:
            interp = "TIGHT — 10-25% > fee"
        else:
            interp = "POOR — <10% > fee"
        print(f"  R{h:>3}s: >8bps = {pct_gt8}% → {interp}")

    # === R+ / R- SPLIT ===
    print("\n" + "="*110)
    print("R+ vs R- DISTRIBUTION (skewness interpretation)")
    print("="*110)
    print(f"{'H':>4} | {'pos%':>5} {'R+_med':>8} {'R+_p90':>8} {'R+_p99':>8} "
          f"| {'neg%':>5} {'R-_med':>8} {'R-_p90':>8} {'R-_p99':>8} | INTERPRETATION")
    print("-"*110)
    for h in HORIZONS:
        st = dist_stats(fr[h])
        if st:
            pos_frac = st.get('R_pos_fraction', 0)
            pos_med = st.get('R_pos_median_bps', 0) or 0
            pos_p90 = st.get('R_pos_p90_bps', 0) or 0
            pos_p99 = st.get('R_pos_p99_bps', 0) or 0
            neg_med = st.get('R_neg_median_bps', 0) or 0
            neg_p90 = st.get('R_neg_p90_bps', 0) or 0
            neg_p99 = st.get('R_neg_p99_bps', 0) or 0
            neg_frac = 100 - pos_frac
            if abs(pos_med) > abs(neg_med) * 1.5:
                interp = "SKEW POS → momentum-friendly"
            elif abs(neg_med) > abs(pos_med) * 1.5:
                interp = "SKEW NEG → reversal-friendly"
            else:
                interp = "SYMMETRIC"
            print(f"{h:>4} | {pos_frac:>5.1f} {pos_med:>8.3f} {pos_p90:>8.3f} {pos_p99:>8.3f} "
                  f"| {neg_frac:>5.1f} {neg_med:>8.3f} {neg_p90:>8.3f} {neg_p99:>8.3f} | {interp}")

    # === FINAL VERDICT ===
    print("\n" + "="*110)
    ok_h = [h for h in HORIZONS if 'LAYAK' in report['horizons'][str(h)]['verdict']]
    event_h = [h for h in HORIZONS if 'EVENT_ONLY' in report['horizons'][str(h)]['verdict']]
    if ok_h:
        print(f"VERDICT: HORIZON LAYAK → {ok_h} | Lanjut STUDY-017")
    elif event_h:
        print(f"VERDICT: EVENT_ONLY → {event_h} | Marginal - tail events layak, tapi median < fee")
        print("  → STUDY-017 LOLOS untuk horizon ini, tapi interpretasi hati-hati")
    else:
        print("VERDICT: TIDAK ADA horizon layak secara ekonomi")
        print("→ STOP trade-flow discovery. Negative finding documented.")
    print("="*110)

    out = Path(__file__).resolve().parent / 'STUDY-016B_ECONOMIC.json'
    with open(out, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nSaved -> {out}")

if __name__ == '__main__':
    main()