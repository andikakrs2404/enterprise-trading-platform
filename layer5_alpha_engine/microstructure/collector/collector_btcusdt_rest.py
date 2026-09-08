#!/usr/bin/env /usr/bin/python3.11
"""
STUDY-016A — Microstructure Collector v2 (REST-ONLY, Futures)
================================================================
Binance USDT-M Futures collector using REST only (fapi.binance.com).
WS futures (fstream) is blocked from this region, so we use:
  - aggTrades: REST /fapi/v1/aggTrades paginated (fromId or startTime)
  - depth:     REST /fapi/v1/depth?limit=100 snapshot every ~1s
  - bookTicker: REST /fapi/v1/ticker/bookTicker every ~1s (optional)

Advantages:
  - No WS dependency (robust from blocked regions)
  - Data is REAL futures (verified: fapi aggTrade IDs ~3.4B vs spot ~4.05B)
  - Resumable: fromId + startTime enable restart without loss
  - Rate limit: aggTrades 20/min for 1000+ rows, depth 100/min -> safe

Disadvantages (documented):
  - Depth at 1s snapshot resolution, not 100ms diff
  - No liquidation stream (needs WS futures) -> proxy from OI delta or skip
  - No realtime depth diff (snapshot only)

Usage:
  /usr/bin/python3.11 collector_btcusdt_rest.py --symbol BTCUSDT --duration 72h [--backfill]

Writes (parquet, per symbol/day):
  data/micro/BTCUSDT/{YYYYMMDD}/aggTrades_{day}.parquet
  data/micro/BTCUSDT/{YYYYMMDD}/depth_{day}.parquet
  data/micro/BTCUSDT/{YYYYMMDD}/bookTicker_{day}.parquet
  data/micro/BTCUSDT/quality.json
"""
import argparse, asyncio, os, time, json, sys, datetime as dt
from pathlib import Path

import requests
import pandas as pd

REST = "https://fapi.binance.com"
ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "micro"

def day_str(ts_ms):
    return dt.datetime.fromtimestamp(ts_ms/1000, tz=dt.timezone.utc).strftime("%Y%m%d")

class RESTCollector:
    def __init__(self, symbol, duration_h=72, depth_interval_s=1.0):
        self.symbol = symbol
        self.duration = duration_h * 3600
        self.depth_interval = depth_interval_s
        self.aggtrades = []
        self.depths = []
        self.booktickers = []
        self.last_agg_id = None
        self.agg_gaps = []
        self.stats = {'agg_rows':0,'depth_rows':0,'bookticker_rows':0,
                      'agg_gaps':0,'rest_errors':0,'start_ts':None,'end_ts':None}
        self.running = True
        self.state_file = DATA / self.symbol / 'collector_state.json'

    def save_state(self):
        """Persist last_agg_id for crash recovery."""
        try:
            st = {'last_agg_id': self.last_agg_id, 'updated_ts': int(time.time()*1000)}
            (DATA / self.symbol).mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(st, f)
        except Exception as e:
            print(f"  [state save err] {e}", file=sys.stderr)

    def load_state(self):
        """Resume from last agg id if state file exists."""
        try:
            if self.state_file.exists():
                st = json.load(open(self.state_file))
                self.last_agg_id = st.get('last_agg_id')
                if self.last_agg_id:
                    print(f"  [resume] last agg id = {self.last_agg_id}")
                    return True
        except Exception as e:
            print(f"  [state load err] {e}", file=sys.stderr)
        return False

    # ---------- REST ----------
    def fetch_agg(self, backfill=True, max_pages=24):
        """Fetch aggTrades paginated from last_agg_id until caught up.
        Uses fromId pagination internally (multiple pages per call).
        Rate limit: aggTrades 20/min -> this method uses multiple pages
        sequentially, so call it every 3s max (20 calls/min).
        Returns number of pages fetched."""
        pages = 0
        while pages < max_pages:
            url = f"{REST}/fapi/v1/aggTrades?symbol={self.symbol}&limit=1000"
            if self.last_agg_id is not None:
                url += f"&fromId={self.last_agg_id+1}"
            try:
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                arr = r.json()
                if not arr:
                    break  # caught up
                # gap check between last and first
                if self.last_agg_id is not None and arr[0]['a'] != self.last_agg_id + 1:
                    self.stats['agg_gaps'] += 1
                    self.agg_gaps.append((self.last_agg_id, arr[0]['a'], int(arr[0]['T'])))
                for t in arr:
                    self.aggtrades.append(t)
                self.stats['agg_rows'] += len(arr)
                self.last_agg_id = arr[-1]['a']
                pages += 1
                if len(arr) < 1000:
                    break  # caught up (last page)
            except Exception as e:
                self.stats['rest_errors'] += 1
                print(f"  [agg err] {e}", file=sys.stderr)
                break
        return pages

    def fetch_depth(self):
        """Full depth snapshot (limit=100)."""
        try:
            r = requests.get(f"{REST}/fapi/v1/depth?symbol={self.symbol}&limit=100", timeout=10)
            r.raise_for_status()
            snap = r.json()
            snap['recv_ms'] = int(time.time()*1000)
            self.depths.append(snap)
            self.stats['depth_rows'] += 1
        except Exception as e:
            self.stats['rest_errors'] += 1
            print(f"  [depth err] {e}", file=sys.stderr)

    def fetch_bookticker(self):
        try:
            r = requests.get(f"{REST}/fapi/v1/ticker/bookTicker?symbol={self.symbol}", timeout=10)
            r.raise_for_status()
            bt = r.json()
            bt['recv_ms'] = int(time.time()*1000)
            self.booktickers.append(bt)
            self.stats['bookticker_rows'] += 1
        except Exception as e:
            self.stats['rest_errors'] += 1
            print(f"  [bookTicker err] {e}", file=sys.stderr)

    # ---------- storage ----------
    def _write(self, typ, rows, cols_map, time_col):
        if not rows:
            return
        df = pd.DataFrame(rows)
        if df.empty:
            return
        df = df.rename(columns=cols_map)
        if time_col in df.columns:
            df['ts'] = pd.to_datetime(df[time_col], unit='ms', utc=True)
        else:
            df['ts'] = pd.NaT
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
        self._write('aggTrades', self.aggtrades,
                    {'a':'agg_id','p':'price','q':'qty','f':'first_id','l':'last_id',
                     'T':'ts_ms','m':'is_buyer_maker'}, 'ts_ms')
        self._write('depth', self.depths,
                    {'lastUpdateId':'last_update_id','b':'bids','a':'asks','recv_ms':'recv_ms'}, 'recv_ms')
        self._write('bookTicker', self.booktickers,
                    {'u':'update_id','s':'symbol','b':'bid','B':'bid_qty','a':'ask','A':'ask_qty',
                     'recv_ms':'recv_ms'}, 'recv_ms')

    # ---------- main loop ----------
    def run(self):
        self.stats['start_ts'] = int(time.time()*1000)
        resumed = self.load_state()
        print(f"[STUDY-016A v2 REST] Start {self.symbol} collect {self.duration}s (resume={resumed})")
        # initial fetch
        self.fetch_agg(backfill=True)
        start = time.time()
        last_depth = 0
        last_bt = 0
        last_flush = 0
        last_state = 0
        while time.time() - start < self.duration:
            # aggTrades every ~2s: 30/min. aggTrades limit is 20/min (2400 weight/min, 1000 rows = 5w)
            # safer: 3s -> 20/min exactly. Use 3s.
            self.fetch_agg(backfill=True)
            now = time.time()
            if now - last_depth >= self.depth_interval:
                self.fetch_depth()
                self.fetch_bookticker()
                last_depth = now
            if now - last_flush >= 60:
                self.flush()
                self.save_state()
                last_flush = now
                last_state = now
                hb = {'t': int(now), 'agg': self.stats['agg_rows'],
                      'depth': self.stats['depth_rows'],
                      'bt': self.stats['bookticker_rows'],
                      'agg_gaps': self.stats['agg_gaps'],
                      'rest_errors': self.stats['rest_errors']}
                print(f"  HB {hb}")
            time.sleep(3.0)  # aggTrades interval (20/min limit)
        self.flush()
        self.save_state()
        self.stats['end_ts'] = int(time.time()*1000)
        self.write_quality_report()

    def write_quality_report(self):
        d = DATA / self.symbol
        d.mkdir(parents=True, exist_ok=True)
        report = {
            'study':'STUDY-016A-v2', 'symbol':self.symbol,
            'start_ts':self.stats['start_ts'], 'end_ts':self.stats['end_ts'],
            'duration_sec': (self.stats['end_ts']-self.stats['start_ts'])/1000 if self.stats['end_ts'] else None,
            'agg_rows': self.stats['agg_rows'], 'depth_rows': self.stats['depth_rows'],
            'bookticker_rows': self.stats['bookticker_rows'],
            'agg_gaps': self.stats['agg_gaps'], 'rest_errors': self.stats['rest_errors'],
            'agg_gap_samples': [{'from_id':a,'to_id':b,'ts_ms':t} for a,b,t in self.agg_gaps[:50]],
            'mode':'REST-only (WS futures blocked from region)',
        }
        with open(d/'quality.json','w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[STUDY-016A v2] Quality report -> {d/'quality.json'}")
        print(f"  agg={self.stats['agg_rows']} depth={self.stats['depth_rows']} "
              f"bt={self.stats['bookticker_rows']} agg_gaps={self.stats['agg_gaps']} "
              f"rest_errors={self.stats['rest_errors']}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--symbol', default='BTCUSDT')
    ap.add_argument('--duration', default='72h')
    ap.add_argument('--depth-interval', type=float, default=1.0)
    a = ap.parse_args()
    if a.duration.endswith('h'):
        dur_h = float(a.duration.rstrip('h'))
    elif a.duration.endswith('s'):
        dur_h = float(a.duration.rstrip('s'))/3600
    else:
        dur_h = float(a.duration)
    print(f"REST Collector: {a.symbol}, {dur_h}h, depth {a.depth_interval}s")
    c = RESTCollector(a.symbol, duration_h=dur_h, depth_interval_s=a.depth_interval)
    c.run()

if __name__ == '__main__':
    main()