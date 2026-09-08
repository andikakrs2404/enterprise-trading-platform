#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016X — Replay Engine (microstructure)
============================================
Deterministic chronological replay of collected parquet data.

Pipeline: Raw Data -> Replay 1x/10x/100x -> Feature Engine -> Signal Engine

Determinism: every stream sorted by (event_ts, tiebreaker); merged timeline
stable across runs (heapq.merge with explicit stream order). Same input
data -> same event sequence, always.

Storage layout supported (multi-symbol ready):
  data/micro/<SYMBOL>/<YYYYMMDD>/aggTrades_*.parquet
  data/micro/<SYMBOL>/<YYYYMMDD>/depth_*.parquet
  data/micro/<SYMBOL>/<YYYYMMDD>/bookTicker_*.parquet

Usage:
    from replay_engine import ReplayEngine
    r = ReplayEngine("data/micro/BTCUSDT")
    for ev_type, ts_ms, rec in r.iter_events(start_ts=..., end_ts=...):
        ...
    r.replay(speed=100.0, on_event=handler)   # paced replay
"""
import heapq
from pathlib import Path
import pandas as pd
import numpy as np

# Tie-break order at identical millisecond: book update, then ticker, then trade.
_STREAM_ORDER = {"depth": 0, "ticker": 1, "trade": 2}


class ReplayEngine:
    def __init__(self, symbol_dir):
        self.symbol_dir = Path(symbol_dir)
        self.trades = None
        self.depths = None
        self.tickers = None
        self._load()

    # ---------- loading ----------
    def _load(self):
        files = sorted(self.symbol_dir.glob("*/aggTrades_*.parquet"))
        if files:
            df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
            df = df.sort_values(["ts_ms", "agg_id"]).reset_index(drop=True)
            df["event_ts"] = df["ts_ms"].astype(np.int64)
            self.trades = df

        files = sorted(self.symbol_dir.glob("*/depth_*.parquet"))
        if files:
            df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
            df = df.sort_values(["recv_ms", "last_update_id"]).reset_index(drop=True)
            df["event_ts"] = df["recv_ms"].astype(np.int64)
            self.depths = df

        files = sorted(self.symbol_dir.glob("*/bookTicker_*.parquet"))
        if files:
            df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
            df = df.sort_values(["recv_ms"]).reset_index(drop=True)
            df["event_ts"] = df["recv_ms"].astype(np.int64)
            self.tickers = df

    # ---------- stream iterators ----------
    def _iter_trades(self, start_ts, end_ts):
        if self.trades is None:
            return
        sub = self.trades
        if start_ts is not None:
            sub = sub[sub.event_ts >= start_ts]
        if end_ts is not None:
            sub = sub[sub.event_ts <= end_ts]
        for row in sub.itertuples(index=False):
            yield ("trade", int(row.event_ts), row)

    def _iter_depths(self, start_ts, end_ts):
        if self.depths is None:
            return
        sub = self.depths
        if start_ts is not None:
            sub = sub[sub.event_ts >= start_ts]
        if end_ts is not None:
            sub = sub[sub.event_ts <= end_ts]
        for row in sub.itertuples(index=False):
            yield ("depth", int(row.event_ts), row)

    def _iter_tickers(self, start_ts, end_ts):
        if self.tickers is None:
            return
        sub = self.tickers
        if start_ts is not None:
            sub = sub[sub.event_ts >= start_ts]
        if end_ts is not None:
            sub = sub[sub.event_ts <= end_ts]
        for row in sub.itertuples(index=False):
            yield ("ticker", int(row.event_ts), row)

    # ---------- merged timeline ----------
    def iter_events(self, start_ts=None, end_ts=None, streams=("trade", "depth", "ticker")):
        """Yield (event_type, ts_ms, record) in deterministic chronological order."""
        gens = []
        if "depth" in streams and self.depths is not None:
            gens.append(self._iter_depths(start_ts, end_ts))
        if "ticker" in streams and self.tickers is not None:
            gens.append(self._iter_tickers(start_ts, end_ts))
        if "trade" in streams and self.trades is not None:
            gens.append(self._iter_trades(start_ts, end_ts))
        if not gens:
            return
        yield from heapq.merge(*gens, key=lambda x: (x[1], _STREAM_ORDER[x[0]]))

    # ---------- paced replay ----------
    def replay(self, speed=None, on_event=None, start_ts=None, end_ts=None,
               streams=("trade", "depth", "ticker")):
        """Replay events.
        speed=None -> as fast as possible (research/backtest mode)
        speed=1.0  -> real-time pacing; 10.0 / 100.0 -> faster.
        on_event(ev_type, ts_ms, rec) callback for feature/signal engines.
        """
        import time as _time
        prev = None
        for ev, ts, rec in self.iter_events(start_ts, end_ts, streams):
            if on_event is not None:
                on_event(ev, ts, rec)
            if speed is not None and prev is not None:
                dt_s = (ts - prev) / 1000.0 / speed
                if dt_s > 0:
                    _time.sleep(min(dt_s, 0.2))
            prev = ts

    # ---------- vectorized access (fast path for feature engines) ----------
    def trade_array(self):
        """Numpy structured array of trades: ts_ms, price, qty, side(1=buy aggressor)."""
        if self.trades is None:
            return None
        t = self.trades
        side = (~t["is_buyer_maker"].astype(bool)).astype(np.int8)  # m=False -> buyer taker -> buy aggressor
        arr = np.empty(len(t), dtype=[("ts_ms", "i8"), ("price", "f8"),
                                      ("qty", "f8"), ("side", "i1")])
        arr["ts_ms"] = t["ts_ms"].values
        arr["price"] = t["price"].values.astype(float)
        arr["qty"] = t["qty"].values.astype(float)
        arr["side"] = side
        return arr

    def price_series_1s(self, field="price"):
        """1s last-price series (the canonical price series for return labels)."""
        if self.trades is None:
            return None
        s = pd.Series(self.trades[field].values.astype(float),
                      index=pd.to_datetime(self.trades["ts_ms"], unit="ms", utc=True))
        return s.resample("1s").last().dropna()

    # ---------- info ----------
    def summary(self):
        out = {"symbol_dir": str(self.symbol_dir),
               "trades": 0 if self.trades is None else len(self.trades),
               "depth": 0 if self.depths is None else len(self.depths),
               "tickers": 0 if self.tickers is None else len(self.tickers)}
        if self.trades is not None:
            out["trade_ts_range"] = [int(self.trades.ts_ms.min()), int(self.trades.ts_ms.max())]
        if self.depths is not None:
            out["depth_ts_range"] = [int(self.depths.recv_ms.min()), int(self.depths.recv_ms.max())]
        return out


if __name__ == "__main__":
    import sys, json
    d = sys.argv[1] if len(sys.argv) > 1 else "data/micro/BTCUSDT"
    r = ReplayEngine(d)
    print(json.dumps(r.summary(), indent=2, default=str))
    # determinism check: two passes produce identical event count + first/last
    ev1 = list(r.iter_events())
    ev2 = list(r.iter_events())
    same = (len(ev1) == len(ev2)) and (ev1[0][:2] == ev2[0][:2]) and (ev1[-1][:2] == ev2[-1][:2])
    print(f"events: {len(ev1)} | deterministic: {same} | first={ev1[0][:2]} last={ev1[-1][:2]}")