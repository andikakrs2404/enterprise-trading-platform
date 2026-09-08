#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016B — Rolling Economic Baseline (per 6h window + market session)
=========================================================================
Bukan keputusan final. Hanya observasi bagaimana distribusi berubah
antar sesi pasar (Asia/London/NY) dan antar window 6 jam.

Menjawab: apakah ada sesi/window yang secara ekonomi lebih menarik?
(TPS, EV10 frequency, p95|R60s|, buy/sell ratio, realized vol)

Usage:
  /usr/bin/python3.11 run_study016B_rolling.py --data layer5_alpha_engine/data/micro/BTCUSDT

Output: console table + STUDY-016B_ROLLING.json (append mode)
"""
import argparse, json, sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = Path("/home/rtk/enterprise-trading-platform/layer5_alpha_engine/data/micro")

# Sesi pasar (UTC, partisi 24 jam tanpa overlap)
SESSIONS = [
    ("Asia", 0, 8),
    ("London", 8, 16),
    ("NY", 16, 24),
]

def load_aggtrades(sym_dir: Path):
    files = sorted(sym_dir.glob("*/aggTrades_*.parquet"))
    if not files:
        print(f"NO aggTrades in {sym_dir}", file=sys.stderr)
        sys.exit(1)
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.drop_duplicates('agg_id').sort_values('ts_ms').reset_index(drop=True)
    df['qty'] = df['qty'].astype(float)
    df['price'] = df['price'].astype(float)
    df['dt'] = pd.to_datetime(df['ts_ms'], unit='ms', utc=True)
    df['hour_utc'] = df['dt'].dt.hour
    return df

def window_stats(df, start_ms, end_ms):
    sub = df[(df['ts_ms'] >= start_ms) & (df['ts_ms'] < end_ms)]
    if len(sub) < 10:
        return None
    span_s = (sub['ts_ms'].max() - sub['ts_ms'].min()) / 1000
    tps = len(sub) / span_s if span_s > 0 else 0
    # buy/sell aggressor
    buy_vol = sub.loc[~sub['is_buyer_maker'], 'qty'].sum()
    sell_vol = sub.loc[sub['is_buyer_maker'], 'qty'].sum()
    tot_vol = buy_vol + sell_vol
    buy_ratio = buy_vol / tot_vol if tot_vol > 0 else np.nan
    # 1s price series + forward returns 60s
    px = sub.set_index('dt')['price'].astype(float).resample('1s').last().dropna()
    if len(px) < 120:
        return None
    r60 = (px.values[60:] / px.values[:-60] - 1.0) * 10000
    rv = float(np.std(px.pct_change().dropna()) * np.sqrt(365 * 24 * 3600) * 100)  # annualized %
    return {
        'n_trades': int(len(sub)),
        'tps': round(tps, 2),
        'buy_ratio': round(buy_ratio, 4),
        'EV10_60s_pct': round(float((np.abs(r60) > 10).mean() * 100), 3),
        'EV20_60s_pct': round(float((np.abs(r60) > 20).mean() * 100), 3),
        'p95_abs_R60_bps': round(float(np.percentile(np.abs(r60), 95)), 2),
        'median_abs_R60_bps': round(float(np.median(np.abs(r60))), 3),
        'rv_ann_pct': round(rv, 1),
        'start': str(pd.to_datetime(start_ms, unit='ms', utc=True)),
        'end': str(pd.to_datetime(end_ms, unit='ms', utc=True)),
    }

def session_stats(df):
    out = {}
    for name, h0, h1 in SESSIONS:
        sub = df[(df['hour_utc'] >= h0) & (df['hour_utc'] < h1)]
        if len(sub) < 10:
            out[name] = None
            continue
        span_s = (sub['ts_ms'].max() - sub['ts_ms'].min()) / 1000
        tps = len(sub) / span_s if span_s > 0 else 0
        buy_vol = sub.loc[~sub['is_buyer_maker'], 'qty'].sum()
        sell_vol = sub.loc[sub['is_buyer_maker'], 'qty'].sum()
        buy_ratio = buy_vol / (buy_vol + sell_vol) if (buy_vol + sell_vol) > 0 else np.nan
        px = sub.set_index('dt')['price'].astype(float).resample('1s').last().dropna()
        if len(px) >= 120:
            r60 = (px.values[60:] / px.values[:-60] - 1.0) * 10000
            ev10 = float((np.abs(r60) > 10).mean() * 100)
            p95 = float(np.percentile(np.abs(r60), 95))
        else:
            ev10, p95 = np.nan, np.nan
        out[name] = {
            'n_trades': int(len(sub)),
            'tps': round(tps, 2),
            'buy_ratio': round(buy_ratio, 4),
            'EV10_60s_pct': round(ev10, 3),
            'p95_abs_R60_bps': round(p95, 2),
        }
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default=str(DATA / 'BTCUSDT'))
    a = ap.parse_args()
    sym_dir = Path(a.data)
    print(f"[STUDY-016B ROLLING] Load {sym_dir}")
    df = load_aggtrades(sym_dir)
    print(f"  rows: {len(df):,} | span: {(df.ts_ms.max()-df.ts_ms.min())/3600000:.2f}h")

    # === SESSION TABLE ===
    print("\n" + "="*90)
    print("PER-SESSION (UTC partition)")
    print("="*90)
    print(f"{'Session':<8} | {'n_trades':>9} | {'TPS':>6} | {'buy_ratio':>9} | {'EV10_60s%':>9} | {'p95|R60|bps':>11}")
    print("-"*90)
    sess = session_stats(df)
    for name, _h0, _h1 in SESSIONS:
        s = sess.get(name)
        if s:
            print(f"{name:<8} | {s['n_trades']:>9,} | {s['tps']:>6.2f} | {s['buy_ratio']:>9.4f} | "
                  f"{s['EV10_60s_pct']:>9.3f} | {s['p95_abs_R60_bps']:>11.2f}")
        else:
            print(f"{name:<8} | no data")

    # === 6H WINDOW TABLE ===
    print("\n" + "="*90)
    print("ROLLING 6H WINDOWS (data sejauh ini)")
    print("="*90)
    t_min = df['ts_ms'].min()
    t_max = df['ts_ms'].max()
    print(f"{'Window start':<26} | {'n':>7} | {'TPS':>6} | {'buy_r':>6} | {'EV10%':>6} | {'EV20%':>6} | {'p95|R60|':>8} | {'med|R60|':>8} | {'RV_ann':>6}")
    print("-"*90)
    windows = []
    w_start = t_min
    while w_start < t_max:
        w_end = w_start + 6 * 3600 * 1000
        s = window_stats(df, w_start, w_end)
        if s:
            print(f"{s['start']:<26} | {s['n_trades']:>7,} | {s['tps']:>6.2f} | {s['buy_ratio']:>6.3f} | "
                  f"{s['EV10_60s_pct']:>6.2f} | {s['EV20_60s_pct']:>6.2f} | {s['p95_abs_R60_bps']:>8.2f} | "
                  f"{s['median_abs_R60_bps']:>8.3f} | {s['rv_ann_pct']:>6.1f}")
            windows.append(s)
        w_start = w_end

    # === SAVE (append) ===
    out_file = ROOT / 'STUDY-016B_ROLLING.json'
    payload = {
        'generated': str(pd.Timestamp.now(tz='UTC')),
        'agg_rows': int(len(df)),
        'span_hours': round((t_max - t_min) / 3600000, 2),
        'sessions': sess,
        'windows_6h': windows,
        'note': 'INTERIM — bukan keputusan final. Final = STUDY-016B_ECONOMIC.json setelah 72h.',
    }
    if out_file.exists():
        old = json.load(open(out_file))
        old.setdefault('history', []).append(payload)
        json.dump(old, open(out_file, 'w'), indent=2, default=str)
    else:
        json.dump({'history': [payload]}, open(out_file, 'w'), indent=2, default=str)

    # === INTERIM INSIGHT ===
    print("\n" + "="*90)
    active = [s for s in sess.values() if s]
    if active:
        best = max(active, key=lambda x: x.get('EV10_60s_pct', 0))
        print(f"INTERIM: sesi paling aktif (EV10 tertinggi): {best}")
    print("Catatan: interim observation only — keputusan final menunggu 72h.")
    print(f"Saved -> {out_file}")

if __name__ == '__main__':
    main()