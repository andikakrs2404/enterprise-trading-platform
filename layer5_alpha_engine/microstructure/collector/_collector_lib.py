#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016A — Microstructure Collector: Binance Futures BTCUSDT
================================================================
Collect realtime aggTrades + depth snapshot stream + bookTicker for BTCUSDT
on Binance USDT-M Futures, write to parquet, detect gaps, heartbeat.

Writes to:
  data/micro/BTCUSDT/{YYYYMMDD}/aggTrades_YYYYMMDD.parquet
  data/micro/BTCUSDT/{YYYYMMDD}/depth_YYYYMMDD.parquet
  data/micro/BTCUSDT/{YYYYMMDD}/bookTicker_YYYYMMDD.parquet

Run:  /usr/bin/python3.11 collector_btcusdt.py --duration 72h --symbol BTCUSDT
"""
import argparse, os, time, json, sys, datetime as dt
from pathlib import Path

import requests
import websockets  # needs python websockets lib (check install)
import pandas as pd

# Binance Futures REST + WS endpoints
REST = "https://fapi.binance.com"
WS_BASE = "wss://fstream.binance.com/ws"

ROOT = Path(__file__).resolve().parent.parent.parent  # layer5_alpha_engine/
DATA = ROOT / "data" / "micro"

def today_str():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")

class AggTradeCollector:
    def __init__(self, symbol, outdir, batch=2000):
        self.symbol = symbol
        self.outdir = Path(outdir)
        self.batch = batch
        self.rows = []
        self.last_id = None
        self.start_ts = None

    def collect_batch(self):
        """Fetch one aggTrades REST batch, newest-first or from last_id."""
        url = f"{REST}/fapi/v1/aggTrades?symbol={self.symbol}&limit={self.batch}"
        if self.last_id:
            url += f"&fromId={self.last_id+1}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        arr = r.json()
        if not arr:
            return False
        self.rows.extend(arr)
        self.last_id = arr[-1]['a']  # agg trade id
        if self.start_ts is None:
            self.start_ts = arr[0]['T']
        return True

    def flush(self, force=False):
        """Write rows to parquet for current day, splitting per minute batch."""
        if not self.rows:
            return
        df = pd.DataFrame(self.rows)
        # Normalize columns
        colmap = {'a':'agg_id','p':'price','q':'qty','f':'first_id','l':'last_id','T':'ts_ms','m':'is_buyer_maker'}
        df = df.rename(columns=colmap)
        df['ts'] = pd.to_datetime(df['ts_ms'], unit='ms', utc=True)
        # write to today's file
        day = today_str()
        d = self.outdir / self.symbol / day
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"aggTrades_{day}.parquet"
        if f.exists():
            old = pd.read_parquet(f)
            df = pd.concat([old, df], ignore_index=True)
        df = df.sort_values('ts_ms')
        df.to_parquet(f, index=False)
        self.stats = {'rows': len(df)}
        self.rows = []
        return df

    def gap_check(self):
        """Report aggTrade id gaps in current buffer."""
        if len(self.rows) < 2:
            return 0
        ids = [r['a'] for r in self.rows]
        gaps = sum(1 for a,b in zip(ids, ids[1:]) if b != a+1)
        return gaps
