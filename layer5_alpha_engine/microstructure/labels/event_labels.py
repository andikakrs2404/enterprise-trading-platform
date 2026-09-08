#!/usr/bin/env /usr/bin/python3.11
"""
Event Labeling Framework — target yang diprediksi (dikunci, terpusat)
======================================================================
Tentukan label SEBELUM feature discovery. Label tidak berubah-ubah per studi.

Label didefinisikan pada 1s price series (last trade per second).

Label set (dikunci untuk seluruh program microstructure):
  - R5s, R15s, R30s, R60s, R180s   (forward return bps)
  - CLS_10: moev 10 bps dalam horizon
  - CLS_20: move 20 bps dalam horizon

Semua fungsi deterministik: input price series -> output label series.
"""
import numpy as np
import pandas as pd

HORIZONS_S = [5, 15, 30, 60, 180]
LABEL_NAMES = {h: f"R{h}s" for h in HORIZONS_S}


def forward_returns(price_1s: pd.Series, horizons=HORIZONS_S) -> pd.DataFrame:
    """Overlapping forward returns (bps) for each horizon.

    price_1s: pd.Series indexed by datetime, 1s grid (may have NaNs).
    Returns DataFrame with columns R5s, R15s, ..., indexed like input.
    """
    p = price_1s.values.astype(float)
    base_idx = price_1s.index
    out = {}
    for h in horizons:
        r = np.full(len(p), np.nan)
        r[:-h] = (p[h:] / p[:-h] - 1.0) * 10000
        out[f"R{h}s"] = r
    df = pd.DataFrame(out, index=base_idx)
    return df


def event_labels(price_1s: pd.Series, thresholds_bps=(10.0, 20.0),
                 horizons=(15, 30, 60)) -> pd.DataFrame:
    """Classification labels: apakah harga bergerak > threshold dalam horizon.

    Returns columns: EV_10_15s, EV_20_15s, ... (1 = move exceeds threshold)
    Label dihitung dari |forward return| > threshold.
    """
    fr = forward_returns(price_1s, horizons)
    out = {}
    for h in horizons:
        col = f"R{h}s"
        for th in thresholds_bps:
            out[f"EV_{int(th)}_{h}s"] = (fr[col].abs() > th).astype(int)
    return pd.DataFrame(out, index=price_1s.index)


def label_stats(labels: pd.DataFrame) -> dict:
    """Ringkasan distribusi label (event frequency per label)."""
    stats = {}
    for col in labels.columns:
        s = labels[col]
        if s.dtype.kind in "iuf":
            if s.nunique() <= 3:  # binary class label
                stats[col] = {"positive_rate": round(float(s.mean()), 4),
                              "n": int(s.notna().sum())}
            else:  # continuous return
                stats[col] = {"median_abs_bps": round(float(s.abs().median()), 3),
                              "p90_abs_bps": round(float(s.abs().quantile(0.90)), 3),
                              "p95_abs_bps": round(float(s.abs().quantile(0.95)), 3),
                              "n": int(s.notna().sum())}
    return stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "replay"))
    from pathlib import Path
    from replay_engine import ReplayEngine
    d = sys.argv[1] if len(sys.argv) > 1 else "data/micro/BTCUSDT"
    r = ReplayEngine(d)
    px = r.price_series_1s()
    print(f"price points: {len(px)}")
    fr = forward_returns(px)
    print("=== forward returns (bps) ===")
    print(fr.describe().loc[["mean", "std", "50%", "90%", "95%"]].round(3).to_string())
    ev = event_labels(px)
    print("\n=== event labels ===")
    print(label_stats(ev))