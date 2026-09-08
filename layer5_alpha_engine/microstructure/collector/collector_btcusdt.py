#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016A — Microstructure Collector: Binance Futures BTCUSDT
================================================================
Collect realtime via WebSocket + REST snapshot for BTCUSDT on Binance USDT-M
Futures. AggTrades + depth diff stream + periodic full-depth snapshot.

Design (STUDY-016 protocol section 4):
  - aggTrades: REST backfill + WS live (primary stream)
  - depth: WS <symbol>@depth@100ms (incremental) + REST depths@1s snapshot every 60s
  - Reconstruction: snapshot (every 60s) + incremental diffs between snapshots
  - Storage: parquet per symbol/day/type
  - Gap detection: trade_id continuity (aggTrades), U/u/pu chain (depth)

Usage:
  /usr/bin/python3.11 collector_btcusdt.py --duration 72h --symbol BTCUSDT

Writes:
  data/micro/BTCUSDT/{YYYYMMDD}/aggTrades_YYYYMMDD.parquet
  data/micro/BTCUSDT/{YYYYMMDD}/depthdiff_YYYYMMDD.parquet
  data/micro/BTCUSDT/{YYYYMMDD}/bookSnapshot_YYYYMMDD.parquet
  data/micro/BTCUSDT/{YYYYMMDD}/quality.json
"""
import argparse, asyncio, os, time, json, sys, datetime as dt, signal
from pathlib import Path

try:
    import requests
    import websockets
    import pandas as pd
    HAVE_DEPS = True
except ImportError as e:
    HAVE_DEPS = False
    print(f"MISSING DEP: {e}", file=sys.stderr)
    print("Install: /usr/bin/python3.11 -m pip install requests websockets pandas pyarrow", file=sys.stderr)

REST = "https://fapi.binance.com"
# NOTE: fstream.binance.com times out from this region; data-stream.binance.vision works.
WS_BASE = "wss://data-stream.binance.vision/stream?streams="

ROOT = Path(__file__).resolve().parent.parent.parent  # layer5_alpha_engine/
DATA = ROOT / "data" / "micro"

def day_str(ts_ms):
    return dt.datetime.fromtimestamp(ts_ms/1000, tz=dt.timezone.utc).strftime("%Y%m%d")

class BookState:
    """Maintains a full orderbook via snapshot + incremental diffs."""
    def __init__(self, symbol):
        self.symbol = symbol
        self.bids = {}   # price_str -> qty
        self.asks = {}
        self.last_update_id = 0
        self.has_snapshot = False
        self.reset_count = 0

    def apply_snapshot(self, snap):
        self.bids = {str(float(p)): float(q) for p, q in snap['bids'] if float(q) > 0}
        self.asks = {str(float(p)): float(q) for p, q in snap['asks'] if float(q) > 0}
        self.last_update_id = snap['lastUpdateId']
        self.has_snapshot = True

    def apply_diff(self, diff):
        """Apply a depth diff event. Check U/u chain. Return True if applied, False if invalid."""
        if not self.has_snapshot:
            return False  # need snapshot first
        if diff['U'] > self.last_update_id + 1:
            # gap: need re-sync snapshot
            self.has_snapshot = False
            return False
        for side, key in [('b', self.bids), ('a', self.asks)]:
            for p, q in diff[side]:
                if float(q) == 0:
                    key.pop(str(float(p)), None)
                else:
                    key[str(float(p))] = float(q)
        self.last_update_id = diff['u']
        return True

    def top(self, n=5):
        """Top n bid/ask levels."""
        bids = sorted(self.bids.items(), key=lambda x: -float(x[0]))[:n]
        asks = sorted(self.asks.items(), key=lambda x: float(x[0]))[:n]
        return bids, asks

class Collector:
    def __init__(self, symbol, duration_h=72, depth_snapshot_interval_s=60):
        self.symbol = symbol
        self.duration = duration_h * 3600
        self.depth_interval = depth_snapshot_interval_s
        self.book = BookState(symbol)
        # buffers
        self.aggtrades = []      # list of dicts
        self.depthdiff = []
        self.snapshots = []
        self.agg_last_id = None
        self.agg_gaps = []
        self.depth_chain_fail = 0
        self.stats = {'agg_rows':0,'depthdiff_rows':0,'snapshots':0,'agg_gaps':0,
                      'depth_chain_fail':0,'start_ts':None,'end_ts':None}
        self.running = True

    # ---------- storage helpers ----------
    def _write(self, typ, rows, cols_map, time_col='ts_ms'):
        if not rows:
            return
        df = pd.DataFrame(rows)
        if df.empty:
            return
        df = df.rename(columns=cols_map)
        # determine time col: prefer explicit server time, fallback recv_ms
        tc = time_col if time_col in df.columns else ('recv_ms' if 'recv_ms' in df.columns else None)
        if tc is not None:
            df['ts'] = pd.to_datetime(df[tc], unit='ms', utc=True)
        else:
            df['ts'] = pd.NaT
        # day partition from first row's server ts (or recv)
        first_ts = rows[0].get('T') or rows[0].get('E') or rows[0].get('recv_ms') or 0
        d = DATA / self.symbol / day_str(first_ts)
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{typ}_{day_str(first_ts)}.parquet"
        try:
            if f.exists():
                old = pd.read_parquet(f)
                df = pd.concat([old, df], ignore_index=True)
            df.sort_values('ts').to_parquet(f, index=False)
        except Exception as e:
            print(f"  [write err {typ}] {e}", file=sys.stderr)
        rows.clear()

    def flush(self):
        """Write all buffers and update stats."""
        self._write('aggTrades', self.aggtrades,
                    {'a':'agg_id','p':'price','q':'qty','f':'first_id','l':'last_id',
                     'T':'ts_ms','m':'is_buyer_maker'})
        self._write('depthdiff', self.depthdiff,
                    {'e':'event','E':'event_ts','s':'symbol','U':'u0','u':'u1',
                     'pu':'prev_u','b':'bids','a':'asks'}, time_col='E')
        self._write('bookSnapshot', self.snapshots,
                    {'lastUpdateId':'last_update_id','b':'bids','a':'asks'})

    # ---------- exchange REST ----------
    def rest_agg_trades_backfill(self, backfill_minutes=5):
        """Backfill aggTrades via REST to catch up any WS gap at start."""
        url = f"{REST}/fapi/v1/aggTrades?symbol={self.symbol}&limit=1000"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            arr = r.json()
            if arr:
                for t in arr:
                    self.aggtrades.append(t)
                    self.agg_last_id = t['a']
        except Exception as e:
            print(f"  [agg backfill err] {e}", file=sys.stderr)

    def rest_depth_snapshot(self):
        """Full orderbook snapshot via REST depth (limit=100)."""
        url = f"{REST}/fapi/v1/depth?symbol={self.symbol}&limit=100"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            snap = r.json()
            snap['ts_ms'] = int(time.time()*1000)
            self.snapshots.append(snap)
            self.book.apply_snapshot(snap)
            self.stats['snapshots'] += 1
        except Exception as e:
            print(f"  [snapshot err] {e}", file=sys.stderr)

    # ---------- WS handlers ----------
    async def handle_depth(self):
        """Subscribe to <symbol>@depth@100ms incremental stream."""
        stream = f"{self.symbol.lower()}@depth@100ms"
        uri = WS_BASE + stream
        while self.running:
            try:
                async with websockets.connect(uri) as ws:
                    while self.running:
                        raw = json.loads(await ws.recv())
                        msg = raw.get('data', raw)  # unbundle combined stream
                        msg['recv_ms'] = int(time.time()*1000)
                        if self.book.has_snapshot:
                            ok = self.book.apply_diff(msg)
                            if ok:
                                self.depthdiff.append(msg)
                                self.stats['depthdiff_rows'] += 1
                            else:
                                self.depth_chain_fail += 1
                        # else: will sync on next snapshot
            except Exception as e:
                print(f"  [depth ws err] {e}", file=sys.stderr)
                await asyncio.sleep(2)

    async def handle_aggtrades(self):
        """Subscribe to <symbol>@aggTrade live stream."""
        stream = f"{self.symbol.lower()}@aggTrade"
        uri = WS_BASE + stream
        while self.running:
            try:
                async with websockets.connect(uri) as ws:
                    while self.running:
                        raw = json.loads(await ws.recv())
                        msg = raw.get('data', raw)  # unbundle combined stream
                        rec = {'a':msg['a'],'p':msg['p'],'q':msg['q'],
                               'f':msg['f'],'l':msg['l'],'T':msg['T'],'m':msg['m']}
                        rec['recv_ms'] = int(time.time()*1000)
                        # gap check on agg_id continuity
                        if self.agg_last_id is not None and rec['a'] != self.agg_last_id + 1:
                            self.stats['agg_gaps'] += 1
                            self.agg_gaps.append((self.agg_last_id, rec['a'], int(rec['T'])))
                        self.agg_last_id = rec['a']
                        self.aggtrades.append(rec)
                        self.stats['agg_rows'] += 1
            except Exception as e:
                print(f"  [agg ws err] {e}", file=sys.stderr)
                await asyncio.sleep(2)

    async def run(self):
        if not HAVE_DEPS:
            return
        self.stats['start_ts'] = int(time.time()*1000)
        print(f"[STUDY-016A] Start {self.symbol} collect {self.duration}s")
        self.rest_depth_snapshot()  # initial snapshot
        self.rest_agg_trades_backfill()

        # depth snapshot timer + flush timer
        last_snap = time.time()
        last_flush = time.time()
        start = time.time()

        tasks = [
            asyncio.create_task(self.handle_aggtrades()),
            asyncio.create_task(self.handle_depth()),
        ]
        loop = asyncio.get_event_loop()
        try:
            while time.time() - start < self.duration:
                await asyncio.sleep(1)
                now = time.time()
                if now - last_snap >= self.depth_interval:
                    self.rest_depth_snapshot()
                    last_snap = now
                    # report heartbeat every snapshot
                    hb = {'t': int(now), 'agg': self.stats['agg_rows'],
                          'dd': self.stats['depthdiff_rows'],
                          'snap': self.stats['snapshots'],
                          'agg_gaps': self.stats['agg_gaps']}
                    print(f"  HB {hb}")
                if now - last_flush >= 60:
                    self.flush()
                    last_flush = now
        finally:
            for t in tasks:
                t.cancel()
            self.flush()
            self.stats['end_ts'] = int(time.time()*1000)
            self.write_quality_report()

    def write_quality_report(self):
        d = DATA / self.symbol
        d.mkdir(parents=True, exist_ok=True)
        gaps_summary = [{'from_id':a,'to_id':b,'ts_ms':t} for a,b,t in self.agg_gaps[:50]]
        report = {
            'study':'STUDY-016A', 'symbol':self.symbol,
            'start_ts':self.stats['start_ts'], 'end_ts':self.stats['end_ts'],
            'duration_sec': (self.stats['end_ts']-self.stats['start_ts'])/1000 if self.stats['end_ts'] else None,
            'agg_rows': self.stats['agg_rows'],
            'depthdiff_rows': self.stats['depthdiff_rows'],
            'snapshots': self.stats['snapshots'],
            'agg_gaps': self.stats['agg_gaps'],
            'depth_chain_fail': self.depth_chain_fail,
            'agg_gap_samples': gaps_summary,
            'coverage_pct': None,  # filled by quality.py after day complete
        }
        with open(d / 'quality.json','w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[STUDY-016A] Quality report -> {d/'quality.json'}")
        print(f"  agg={self.stats['agg_rows']} depthdiff={self.stats['depthdiff_rows']} snap={self.stats['snapshots']} aggregate_gaps={self.stats['agg_gaps']}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default='BTCUSDT')
    ap.add_argument('--duration', default='72h')
    ap.add_argument('--snapshot-interval', type=int, default=60)
    a = ap.parse_args()
    if a.duration.endswith('h'):
        dur_h = int(a.duration.rstrip('h'))
    elif a.duration.endswith('s'):
        dur_h = int(a.duration.rstrip('s')) / 3600.0  # fractional hour for smoke test
    else:
        dur_h = int(a.duration)
    print(f"Collector: {a.symbol}, {dur_h}h, snapshot {a.snapshot_interval}s")

    def handler(sig, frame):
        print("\n[STUDY-016A] SIGTERM — flushing and exiting...")
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, handler)

    c = Collector(a.symbol, duration_h=dur_h, depth_snapshot_interval_s=a.snapshot_interval)
    asyncio.run(c.run())

if __name__ == '__main__':
    main()
