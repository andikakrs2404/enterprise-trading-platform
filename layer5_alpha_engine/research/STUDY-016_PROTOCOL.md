# STUDY-016 — Microstructure Data & Scalping Protocol

**Status:** PRE-REGISTERED (PROTOCOL ONLY)
**Date:** 2026-09-07
**Principle:** Data + protocol study. Boleh mengumpulkan data, mengevaluasi kualitas,
menentukan infrastructure. **BELUM BOLEH mencari feature yang profitable.**

---

## 0. Meta-Rule

> Hermes menjalankan tugas: "Uji hipotesis X menggunakan protocol Y.
> Jangan mengubah horizon, threshold, universe, split, atau cost model
> berdasarkan hasil."
>
> Hermes = falsification engine. Bukan optimizer yang mencari sesuatu
> untuk terlihat profitable.

---

## 1. Scope Studi

### Yang dilakukan
- Tentukan exchange, data source, resolusi
- Evaluasi trades vs aggTrades, L2 depth, liquidation stream
- Desain timestamp sync, gap detection, storage format
- Bangun replay engine skeleton + cost model (fee, slippage, latency)
- Validasi kualitas data: completeness, continuity, timestamp drift
- Definisikan event definition, horizon, methodology
- Hard-stop gates

### Yang TIDAK dilakukan
- Tidak mencari feature profitable
- Tidak menghitung return
- Tidak menghubungkan data dengan sinyal apapun
- Tidak optimasi apapun

---

## 2. Exchange & Data Source

### Primary: Binance Futures (USDT-M)
- **Alasan:** liquidity terbesar, API stabil, historical data tersedia
- **Pair utama:** BTCUSDT, ETHUSDT, SOLUSDT (mulai 3 dulu, bukan 39)

### Data Categories

| # | Tipe | Source | Format | Resolusi |
|---|------|--------|--------|----------|
| 1 | **AggTrades** | REST: `/fapi/v1/aggTrades` | {p,q,isBuyerMaker,firstId,lastId,T} | per-trade, ~ms |
| 2 | **L2 Orderbook (depth@best)** | REST: `/fapi/v1/depth` or `depth@100ms/500ms/1s` | {bids[], asks[]} | snapshot @ 100ms/1s |
| 3 | **Liquidations** | WS: `<symbol>@forceOrder` | {s,p,q,S,o,T} | per-event |
| 4 | **OI changes** | REST: `/fapi/v1/openInterest` or WS `!ticker@arr` | OI delta per interval | 1s–5s |
| 5 | **Funding rate** | REST: `/fapi/v1/fundingRate` | funding rate | per 8h (auxiliary) |
| 6 | **Klines (OHLCV)** | REST: `/fapi/v1/klines` | OHLCV | 1m (auxiliary) |

### Trades vs AggTrades — Keputusan
- **AggTrades** dipakai sebagai primary (sudah aggregated, API rate lebih hemat)
- **Full trades** (`/fapi/v1/trades`) hanya untuk validasi aggrTrade completeness
- AggTrade fields: `firstTradeId`..`lastTradeId` memungkinkan rekonstruksi trade count

### L2 Orderbook — Snapshot vs Incremental
- **Snapshot (REST depth@100ms/1s)** dipakai sebagai primary — lebih sederhana, gap-able
- **Incremental (WS depth@100ms)** = lebih akurat tapi gap/missing lebih sulit diperbaiki
- **Pendekatan:** snapshot @ 1s untuk Phase A; incremental @ 100ms hanya jika snapshot tidak cukup (dinilai di STUDY-016)

### Liquidation Stream
- Binance WS `<SYMBOL>@forceOrder` — real-time, per-event
- Historical: **tidak ada REST endpoint historis** → hanya mulai collection dari sekarang
- **Fallback historical:** estimasi dari funding rate changes + price spikes (proxy, bukan ground truth)

---

## 3. Data Collection Infrastructure

### Pipeline Architecture
```
Binance REST/WS
     │
     ├── aggTrades (REST batch, resumable)
     ├── depth@1s   (REST snapshot, resumable) 
     ├── liq stream  (WS, continuous write)
     ├── OI @1s     (REST, periodic)
     └── klines @1m  (REST batch)
     │
     ▼
Data Store (parquet, partitioned by symbol + date)
     │
     ▼
Gap Detector (run after each collection window)
     │
     ▼
Quality Report (completeness %, timestamp drift, gaps logged)
```

### Collection Targets (Phase A)
| Item | Target | Acceptable |
|------|--------|-----------|
| aggTrades | 100% | ≥95% |
| depth@1s | 100% snapshots | ≥90% |
| liquidations | best-effort (WS only) | logged, gaps expected |
| OI | 100% @1s | ≥95% |
| klines | 100% @1m | ≥98% |

### Storage Format
- **Parquet** (per symbol per day per data type)
- Directory: `data/micro/{symbol}/{date}/{type}.parquet`
- Timestamps: **UTC milliseconds** (consistent across all sources)
- Compression: zstd (default parquet)

### Timestamp Synchronization
- All timestamps standardized to **Binance server time (ms)**
- Record: `local_receive_time` alongside `server_time` for latency measurement
- Max allowed drift: **500ms** between server and local; log if exceeded
- Cross-source sync: align aggTrades and depth@1s timestamps using nearest-neighbor (±500ms)

### Data Loss & Gap Detection
Run after each collection window:
```
For each symbol/day:
  1. Count expected aggTrade IDs (firstId..lastId per batch)
  2. Count actual rows → completeness %
  3. Timestamp gap check: any gap > 2s flagged as gap
  4. Depth snapshot count vs expected (1 per second)
  5. Generate quality report: JSON per symbol/day
```
Quality gate: if completeness < 90% for any symbol/day, flag but don't block.
Report is the deliverable of STUDY-016.

---

## 4. Replay Engine (Skeleton — STUDY-016 only defines, not builds)

### Purpose
Replay historical data as if streaming, to simulate execution environment.

### Requirements
- Feed aggTrades + depth snapshots in chronological order
- Maintain simulated orderbook state between depth snapshots
- Track: simulated local clock, simulated network latency
- Output: timestamped events = [{ts, event_type, state_snapshot}]

### Design Note (for STUDY-016 only)
- Replay engine is a deliverable of STUDY-016, not STUDY-017
- V0: simple sequential reader (no true streaming)
- V1 (STUDY-022): true event-driven replay with simulated latency

---

## 5. Cost Model

### Transaction Cost Components

| Component | BTCUSDT | ETHUSDT | SOLUSDT | Notes |
|-----------|---------|---------|---------|-------|
| Taker fee | 0.040% | 0.040% | 0.040% | Binance standard (no BNB) |
| Maker fee | 0.020% | 0.020% | 0.020% | Limit order |
| Avg spread | 0.01 bps | 0.02 bps | 0.03 bps | Measured, not assumed |
| Avg slippage | 0.1-0.5 bps | 0.2-0.8 bps | 0.3-1.0 bps | Size-dependent: 0.1-1 BTC notional |
| Latency impact | 0.1-0.3 bps | 0.1-0.5 bps | 0.2-0.7 bps | 10-50ms avg for REST, 5-15ms WS |

### Round-Trip Cost Scenarios

| Scenario | Fee | Spread | Slippage | Total RT |
|----------|-----|--------|----------|----------|
| Best (taker+limit) | 6 bps | 0.5 bps | 0.5 bps | **7 bps** |
| Typical taker | 8 bps | 1.0 bps | 1.0 bps | **10 bps** |
| Worst realistic | 8 bps | 2.0 bps | 2.0 bps | **12 bps** |

**Economic gate:** gross edge must exceed WORST realistic cost (12 bps), not best-case.

### Slippage Model (V0 — conservative)
- Assume taker order hits visible depth only
- Slippage = `order_size / depth_at_level × price_distance`
- Conservative: use **WORST observed spread** for that hour, not average
- V1 (STUDY-022): use actual orderbook replay for realistic fill

### Latency Model
- REST API call: 50-200ms round-trip (measured)
- WS message: 5-15ms (measured)
- **Critical for scalping:** 15s horizon at 100ms latency = 150 price ticks → latency impact negligible
- **But:** 5s horizon at 200ms latency = 5 price ticks → latency is 4% of horizon
- Measure: log local_receive_time for every API call

---

## 6. Target Horizons

| Horizon | Period | Granularity | Why |
|---------|--------|-------------|-----|
| **R5s** | 5 seconds | tick-level | Ultra short-term, most noise |
| **R15s** | 15 seconds | tick-level | Short-term signal test |
| **R30s** | 30 seconds | tick-level | Sweet spot candidate |
| **R1m** | 1 minute | tick-level | Medium scalp |
| **R3m** | 3 minutes | tick-level | Longer scalp / trade management |
| **R5m** | 5 minutes | tick-level | Upper bound scalp |

**Horizon definition:**
- Return = mid-price at T+horizon − mid-price at T
- Mid-price = (best_bid + best_ask) / 2 at trigger time
- NOT last trade price (avoid trade-price noise)

---

## 7. Event Definition

### What constitutes an "event"?
An event = a timestamp where a microstructure condition is met.
Events must be **sparse enough** to be tradeable (not every tick).

| Event Category | Example | Min gap | Frequency target |
|----------------|---------|---------|-----------------|
| Trade flow | Buy/sell imbalance > 2σ | 30s | 50-200/day |
| Orderbook | Bid depth > ask depth × 2 | 30s | 50-200/day |
| Liquidation | Liquidation burst (>3 in 60s) | 5min | 5-20/day |
| Combined | Aggressive buy + ask depletion | 30s | 10-50/day |

### Non-Overlap Rule
- Forward returns at adjacent timestamps overlap → use non-overlap grid
- Non-overlap interval = horizon itself (e.g., R15s → events min 15s apart)
- **Exception:** event-frequency check (frequency analysis) uses full sample

### HAC (Heteroscedasticity-Autocorrelation Consistent)
- When non-overlap sample is too small (< 200 events), use HAC (Newey-West)
- Report both: non-overlap and HAC-corrected

---

## 8. Train / Validation / Test Boundaries

### Timeline Structure

| Split | Period | Purpose |
|-------|--------|---------|
| **TRAIN** | Months 1-6 | Phenomenon discovery |
| **VAL** | Months 7-9 | Confirmation |
| **TEST** | Months 10-12+ | Final evaluation |

**Note:** For STUDY-016, we are collecting data NOW. Collection starts ~Sep 2026.
- If we collect 6 months: TRAIN = Sep-Nov 2026, VAL = Dec 2026-Jan 2027, TEST = Feb 2027+
- If we collect less, proportionally adjust splits

### Walk-Forward Alternative
If temporal split is too short (<3 months per split):
- Use rolling 3-month windows with 1-month step
- Report: number of windows where phenomenon holds

---

## 9. Hard-Stop Gates (PREREGISTERED — tidak boleh diubah)

A phenomenon proceeds to STUDY-017 (trade flow) or STUDY-018 (orderbook)
ONLY if ALL gates pass. No exceptions.

### Gate A: Event Frequency
- ≥ 50 events per month in TRAIN
- Reason: too few events = not tradeable, even if statistically significant

### Gate B: Directional Consistency
- Sign of median return at event time is same in TRAIN, VAL, and TEST
- If TRAIN positive, VAL must be ≥ 0, TEST must be ≥ 0 (or statistically indistinguishable from zero)
- No sign flip allowed

### Gate C: Gross Edge vs Cost
- **Median gross return at event > 12 bps** (worst realistic round-trip)
- This is an absolute bar. 5 bps gross = dead, even if p < 0.001
- Source: STUDY-001–015 lesson — 2-20 bps gross is killed by 8-16 bps cost

### Gate D: Temporal Stability
- Non-overlap sample returns: sign must be consistent across time windows
- HAC p-value < 0.10 (at minimum) if sample is small
- Report: per-month breakdown

### Gate E: Cross-Symbol Consistency
- Test on at least 2 symbols (BTC + ETH minimum)
- If phenomenon only works on 1 symbol → suspect illiquidity artifact
- Breadth: ≥ 2/3 symbols show same sign

### Gate F: Execution Feasibility (from STUDY-020, but preliminary check here)
- Event time → entry time: latency < 10% of horizon (e.g., R15s → latency < 1.5s)
- If latency is too large relative to horizon → phenomenon is not executable → FAIL

---

## 10. Deliverables STUDY-016

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | This protocol (STUDY-016_PROTOCOL.md) | ✅ PREREGISTERED |
| 2 | Exchange + data source selection (documented) | TBC |
| 3 | Data collection pipeline (aggTrades + depth, resumable) | TBC |
| 4 | Gap detection + quality report script | TBC |
| 5 | Replay engine V0 (sequential reader) | TBC |
| 6 | Cost model validation (measure real spread/slippage) | TBC |
| 7 | Data quality report: completeness, gaps, drift | TBC |
| 8 | **No signal analysis** — that's STUDY-017+ | BANNED |

---

## 11. Program Roadmap (for reference — not to be changed based on results)

```
STUDY-016  Data & Protocol      → "Can we collect and validate data?"
STUDY-017  Trade Flow Phenomena  → "Does aggressive flow predict short-term moves?"
STUDY-018  Order Book Phenomena  → "Does book imbalance predict short-term moves?"
STUDY-019  Event Interaction     → "Do combined events predict better than individual?"
STUDY-020  Execution Reality     → "Can we actually trade it after all costs?"
STUDY-021  Strategy Construction → "Can we turn a surviving phenomenon into a strategy?"
STUDY-022  Replay/Backtest       → "Does it work in realistic execution simulation?"
→ Paper Trading → Small Live → Scale
```

**Each study is gated by the previous.** No skipping.

---

*Protocol v1.0 — 2026-09-07*
*Program alpha (STUDY-001–015) tetap CLOSED. STUDY-016 adalah program baru,
kelas data baru. Kesimpulan lama tidak berubah.*
