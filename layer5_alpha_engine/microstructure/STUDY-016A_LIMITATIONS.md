# STUDY-016A — Known Limitations & Data Quality Notes (LIVE)

**Date:** 2026-09-08 | **Status:** Collector 72h running (proc_a5192fe58cbe)

## Format Verification (semua PASS)

| Data | Format | Status |
|------|--------|--------|
| aggTrades | ✅ `agg_id, price, qty, nq, first_id, last_id, ts_ms(exchange), is_buyer_maker, ts` | PASS |
| depth | ✅ Full book 100 level: `last_update_id, E, T, bids, asks, recv_ms(collector), ts` | PASS |
| bookTicker | ✅ `bidPrice, bidQty, askPrice, askQty, time, lastUpdateId, recv_ms` | PASS |

**Timestamp dual**: setiap record punya exchange_ts (`ts_ms`/`E`/`time`) + collector_ts (`recv_ms`) → collector_delay = recv_ms - exchange_ts bisa dihitung.

**Trade side**: `is_buyer_maker` (field `m` Binance) tersimpan → aggressive buy/sell langsung, tanpa Lee-Ready.

## Known Limitations (dokumentasi jujur)

### 1. Depth @~3.6s (bukan 1s) — LO RESOLUTION
- **Expected**: 1 snapshot/s (interval depth_interval=1.0)
- **Actual**: median delta 3.6s (185 rows / 610s span)
- **Cause**: main loop `time.sleep(3.0)` untuk aggTrades rate limit — depth fetch menunggu loop
- **Impact**: 
  - STUDY-017 (trade flow): ACCEPTABLE — aggTrades event-level, depth hanya konteks
  - STUDY-018/019 (queue/microprice): TIDAK CUKUP — butuh data lebih granular
- **Fix untuk fase berikutnya**: pisahkan depth loop (thread/async) dari aggTrades loop, atau kurangi sleep
- **Keputusan**: JANGAN diperbaiki sekarang — collector sedang jalan 72h (user instruction)

### 2. Spread BTC futures sangat ketat (0.0127 bps)
- spread ~$0.1 di harga ~$78.8k = 0.0127 bps
- Ini wajar untuk BTCUSDT (market paling liquid)
- **Implikasi untuk STUDY-017+**: spread bukan bottleneck utama untuk BTC; sinyal >1.3 bps spread sudah net-potential. TAPI ini di luar fee.

### 3. aggTrades zero-gap verified
- completeness 100% (5,406 rows, 0 gaps, 0 missing)
- avg 6.75 trades/s (saat ini market sepi — bisa lebih tinggi saat volatile)

## Coverage Estimates (72h)
- aggTrades: 72h × 3600 × ~7-40 tps = 1.8–10 juta rows
- depth: 72h × 3600 / 3.6s = ~72k snapshots
- bookTicker: ~72k rows
- Total: 2–10 GB parquet

## Status per Stream (untuk STUDY-017+)
- [x] aggTrades: ACCEPTABLE (event-level, zero-gap)
- [~] depth: ACCEPTABLE untuk pilot, TIDAK cukup untuk queue dynamics
- [x] bookTicker: ACCEPTABLE
- [ ] liquidation stream: TIDAK TERSEDIA (futures WS blocked) — perlu proxy (OI delta) atau skip

## Action Items (SETELAH 72h)
1. Generate full quality report (spread distribution lengkap)
2. Evaluasi coverage gate
3. STUDY-017 design (trade flow phenomena — signed volume, buy/sell imbalance, trade intensity, volume burst)
4. Untuk STUDY-018/019: evaluasi kebutuhan depth granularity lebih tinggi (solusi: extract depth dari WS spot? TIDAK — spot ≠ futures. Opsi: Binance futures data dari penyedia pihak ketiga, atau terima limitasi)