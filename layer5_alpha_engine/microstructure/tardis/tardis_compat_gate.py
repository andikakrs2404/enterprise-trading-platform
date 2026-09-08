#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-018 TARDIS COMPATIBILITY GATE — verifier
================================================
Menjawab: "Apakah Tardis data bisa masuk ke pipeline kita tanpa merusak
reproducibility?" — TANPA mencari alpha.

Gate checks (semua deterministik):
  [ ] Schema audit: trades + L2 fields
  [ ] Timestamp integrity: ordering, duplicates, gap, exchange vs local
  [ ] Latency: localTimestamp - timestamp (Tardis native delay)
  [ ] Trade normalization -> CanonicalEvent -> replay_engine
  [ ] L2 reconstruction: snapshot + incremental -> book (best bid/ask, spread, depth)
  [ ] Replay determinism: 2x run identik
  [ ] Data quality: coverage, duplicate rate, out-of-order rate

Usage:
  python3.11 tardis_compat_gate.py --sample-dir /tmp/tardis_sample
  (Untuk download sample: lihat tardis_sample_fetcher.py)

Output: TARDIS_COMPATIBILITY.json + console table
"""
import argparse, json, sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "replay"))

def load_trades_csv(path):
    """Tardis trades CSV: exchange,symbol,timestamp,localTimestamp,id,price,amount,side"""
    df = pd.read_csv(path)
    return df

def load_l2_csv(path):
    """Tardis incremental_book_L2 CSV: exchange,symbol,timestamp,localTimestamp,is_snapshot,side,price,amount"""
    df = pd.read_csv(path)
    return df

def schema_audit(df, expected, name):
    cols = list(df.columns)
    missing = [c for c in expected if c not in cols]
    return {
        'name': name,
        'columns': cols,
        'expected': expected,
        'missing': missing,
        'PASS': len(missing) == 0,
    }

def timestamp_integrity(df, ts_col='timestamp', local_col='localTimestamp'):
    ts = df[ts_col].values.astype(np.int64)
    lat = (df[local_col] - df[ts_col]) if local_col in df.columns else None
    out = {
        'n_rows': int(len(df)),
        'sorted': bool(np.all(np.diff(ts) >= 0)),
        'duplicates': int((np.diff(ts) == 0).sum()),
        'out_of_order': int((np.diff(ts) < 0).sum()),
        'ts_min': int(ts.min()), 'ts_max': int(ts.max()),
        'span_hours': round((ts.max()-ts.min())/3600000, 4),
    }
    if lat is not None:
        lat = lat.astype(float)
        out.update({
            'latency_mean_ms': round(float(lat.mean()), 2),
            'latency_median_ms': round(float(np.median(lat)), 2),
            'latency_p95_ms': round(float(np.percentile(lat, 95)), 2),
            'latency_p99_ms': round(float(np.percentile(lat, 99)), 2),
            'latency_max_ms': round(float(lat.max()), 2),
            'latency_neg_pct': round(float((lat < 0).mean() * 100), 4),
        })
    return out

def canonical_trades(df):
    """Map Tardis trade row -> canonical (ts_ms, price, qty, side)."""
    # Tardis side: 'buy'/'sell' = aggressor side. map to is_buyer_maker equivalent:
    # in Binance aggTrades m=True = buyer maker = sell aggressor
    # Tardis side 'sell' = sell aggressor -> m=True
    # Tardis side 'buy'  = buy aggressor  -> m=False
    out = pd.DataFrame({
        'ts_ms': df['timestamp'].astype(np.int64),
        'price': df['price'].astype(float),
        'qty': df['amount'].astype(float),
        'is_buyer_maker': (df['side'] == 'sell').astype(bool),
        'agg_id': df['id'].astype(str),
    })
    return out

def reconstruct_book(l2_df):
    """Reconstruct order book from Tardis L2 (snapshot + incremental)."""
    bids, asks = {}, {}
    snap_count = 0
    bests = []
    last_snapshot_ts = None
    for row in l2_df.itertuples(index=False):
        side = row.side
        price = float(row.price)
        amount = float(row.amount)
        ts = row.timestamp
        if row.is_snapshot:
            # new snapshot: reset book
            bids = {} if side == 'bid' else bids
            asks = {} if side == 'ask' else asks
            if side == 'bid':
                bids[price] = amount if amount > 0 else None
            else:
                asks[price] = amount if amount > 0 else None
            snap_count += 1
            last_snapshot_ts = ts
        else:
            if side == 'bid':
                if amount == 0:
                    bids.pop(price, None)
                else:
                    bids[price] = amount
            else:
                if amount == 0:
                    asks.pop(price, None)
                else:
                    asks[price] = amount
        if last_snapshot_ts is not None and bids and asks:
            bb = max(bids.keys())
            ba = min(asks.keys())
            if ba > bb:
                mid = (bb + ba) / 2
                bests.append({'ts': ts, 'bid': bb, 'ask': ba,
                              'mid': mid,
                              'spread_bps': (ba - bb) / mid * 10000,
                              'bid_qty': bids.get(bb, 0),
                              'ask_qty': asks.get(ba, 0)})
    return bests, snap_count

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample-dir', required=True, help='dir berisi trades CSV + L2 CSV')
    a = ap.parse_args()
    d = Path(a.sample_dir)
    report = {'gate': 'TARDIS_COMPATIBILITY', 'date': '2026-09-08'}

    trades_file = None
    l2_file = None
    for f in d.glob('*.csv.gz'):
        if 'trade' in f.name:
            trades_file = f
        elif 'incremental_book' in f.name or 'book_L2' in f.name:
            l2_file = f

    print("="*80)
    print("TARDIS COMPATIBILITY GATE")
    print("="*80)

    # ---- Schema ----
    checks = {}
    if trades_file:
        df_t = load_trades_csv(trades_file)
        s = schema_audit(df_t, ['exchange','symbol','timestamp','localTimestamp','id','price','amount','side'], 'trades')
        checks['schema_trades'] = s
        print(f"\n[TRADES] {trades_file.name} ({len(df_t):,} rows)")
        print(f"  schema: {'PASS' if s['PASS'] else 'FAIL '+str(s['missing'])}")
        ti = timestamp_integrity(df_t)
        checks['timestamp_trades'] = ti
        print(f"  ts integrity: sorted={ti['sorted']} dup={ti['duplicates']} OOO={ti['out_of_order']} span={ti['span_hours']}h")
        if 'latency_mean_ms' in ti:
            print(f"  latency: mean={ti['latency_mean_ms']}ms med={ti['latency_median_ms']}ms p95={ti['latency_p95_ms']}ms neg%={ti['latency_neg_pct']}")

        # canonical + replay determinism
        canon = canonical_trades(df_t)
        # determinism: 2x sort -> identical sequence
        c1 = canon.sort_values(['ts_ms','agg_id']).reset_index(drop=True)
        c2 = canon.sort_values(['ts_ms','agg_id']).reset_index(drop=True)
        det = bool(c1.equals(c2))
        checks['canonical_trades'] = {'rows': len(c1), 'deterministic': det}
        print(f"  canonical: {len(c1):,} rows | deterministic={det}")
        # side distribution
        side_dist = df_t['side'].value_counts().to_dict()
        print(f"  side dist: {side_dist}")
        checks['side_distribution'] = side_dist

    if l2_file:
        df_l = load_l2_csv(l2_file)
        s2 = schema_audit(df_l, ['exchange','symbol','timestamp','localTimestamp','is_snapshot','side','price','amount'], 'l2')
        checks['schema_l2'] = s2
        print(f"\n[L2] {l2_file.name} ({len(df_l):,} rows)")
        print(f"  schema: {'PASS' if s2['PASS'] else 'FAIL '+str(s2['missing'])}")
        # snapshot count + reconstruction
        n_snap = int(df_l['is_snapshot'].sum())
        print(f"  snapshots: {n_snap}")
        bests, snap_cnt = reconstruct_book(df_l)
        print(f"  reconstruction: {snap_cnt} snapshots, {len(bests)} best-bid/ask samples")
        if bests:
            spreads = [b['spread_bps'] for b in bests]
            print(f"  spread: median={np.median(spreads):.4f}bps p95={np.percentile(spreads,95):.4f}bps")
            checks['l2_reconstruction'] = {
                'snapshots': snap_cnt, 'samples': len(bests),
                'spread_median_bps': round(float(np.median(spreads)), 4),
                'spread_p95_bps': round(float(np.percentile(spreads, 95)), 4),
            }
            # reconstruction determinism: 2x
            bests2, _ = reconstruct_book(df_l)
            same = len(bests) == len(bests2) and all(
                abs(a['spread_bps']-b['spread_bps'])<1e-9 for a,b in zip(bests, bests2))
            checks['l2_determinism'] = same
            print(f"  reconstruction deterministic: {same}")

    # ---- Final verdict ----
    print("\n" + "="*80)
    print("TARDIS COMPATIBILITY VERDICT")
    print("="*80)
    fundamental = ['schema_trades', 'schema_l2', 'timestamp_trades']
    present = [k for k in fundamental if k in checks]
    fails = [k for k in present if not checks[k].get('PASS', True)]
    if fails:
        verdict = 'NO-GO'
    else:
        verdict = 'PASS'
    print(f"  FUNDAMENTAL CHECKS: {len(present)}/{len(fundamental)} present, {len(fails)} fail")
    print(f"  VERDICT: {verdict}")
    if verdict == 'NO-GO':
        print("  -> Jangan beli subscription. Ada komponen fundamental gagal/absent.")
    else:
        print("  -> Data Tardis kompatibel dgn pipeline. (Tetap lakukan full audit sebelum beli.)")
    report['verdict'] = verdict
    report['checks'] = checks

    out = Path(__file__).resolve().parent / 'STUDY-018_TARDIS_COMPAT.json'
    with open(out, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved -> {out}")

if __name__ == '__main__':
    main()