# STUDY-016 — Microstructure Scalping Research Protocol (PREREGISTRATION)

**Status:** PRE-REGISTERED (PROTOCOL) — BELUM ada data
**Date:** 2026-09-07
**Parent:** Program alpha ditutup (STUDY-001..015) → arah baru: microstructure scalping
**Tipe:** Research protocol + data collection spec. BUKAN strategy coding.

---

## 1. Pertanyaan Riset

> Bisakah informasi order-flow / microstructure memprediksi arah harga
> crypto futures beberapa detik–menit ke depan, SETELAH biaya transaksi?

**BUKAN:** "Strategi scalping apa yang profitable?"
**TAPI:** "Apa yang sebenarnya terjadi pada order book sebelum short-term
price move?"

Horizon: R5s / R15s / R30s / R1m / R3m / R5m
(berubah dari 1h→R24 ke detik→menit — masalah yang berbeda)

---

## 2. Data Minimum yang Harus Dikumpulkan

### Target: 2-5 market paling liquid (mulai BTCUSDT, ETHUSDT, SOL)

| Kategori | Kolom | Resolusi |
|----------|-------|----------|
| **Trades (aggTrades)** | price, qty, time, isBuyerMaker (aggressor side) | per trade / 100ms bucket |
| **L2 Orderbook (depth@best/l2)** | bids/asks levels, timestamps | snapshot 100ms–1s |
| **Liquidations** | price, qty, side (long/short), time | per event |
| **OI changes** | OI per 1s/5s bucket (dari delta) | 1s–5s |
| **Price/volume** | tick price, volume profile | per trade |

**Belum tentu perlu semua dari awal** — mulai dengan aggTrades + depth.

### Derived microstructure features (final list)
- **Trade flow:** aggressive buy vol, aggressive sell vol, buy/sell imbalance,
  trade intensity, trade size distribution, signed volume, burst detection
- **Order book:** bid/ask imbalance, depth imbalance, spread, microprice,
  book slope, liquidity depletion/replenishment, queue imbalance
- **Event flow:** liquidation bursts, volume acceleration, OI changes HF,
  aggressive sweep, spread widening, liquidity withdrawal

---

## 3. Pipeline Arah

```
MARKET DATA (aggTrades + depth + liq)
   → Feature Factory (microstructure features, rolling windows)
   → Phenomenon Discovery (X terjadi → Y cenderung terjadi dalam t+15-30s)
   → Statistical Validation (non-overlap/HAC, temporal stability)
   → Execution Engine sim (spread + slippage + fee + latency)
   → NET EDGE? → EXECUTE / SKIP
```

---

## 4. Cost Model (sejak hari pertama — bukan appendix)

| Komponen | Estimasi (Binance futures) |
|----------|---------------------------|
| Fee taker | 4-5 bps (0.04-0.05%) |
| Fee maker | 2 bps (0.02%) |
| Spread | ~0.5-1 bps BTC, 1-2 bps ETH/SOL |
| Slippage | tergantung size vs depth |
| **Total round-trip (taker)** | **~9-12 bps** |
| **Total round-trip (maker)** | **~4-6 bps** |

Economic gate: gross edge > total cost + safety margin.

Contoh: gross +7bps - fee 4bps - slip 3bps = 0 → **mati, langsung**. Tidak perlu ML.

---

## 5. Hard Gates (preregistered, SEBELUM signal diuji)

Fenomena layak Phase B (strategy) HANYA jika memenuhi SEMUA:
- [ ] Out-of-sample (TRAIN/VAL/TEST atau walk-forward)
- [ ] Temporal stability (konsisten lintas periode)
- [ ] Cross-symbol (BTC → ETH → SOL → lebih)
- [ ] Non-overlap/HAC untuk forward returns
- [ ] Directional consistency (tidak flip sign)
- [ ] Sufficient event frequency (bisa ditrade real)
- [ ] **Gross edge > realistic cost** (bukan net nol)
- [ ] Survives latency/slippage assumptions

Phase: A (discovery) → B (strategy) → C (exec sim) → D (paper) → E (live kecil).

---

## 6. Larangan (dari pelajaran STUDY-001..015)

- ❌ Tidak mencari threshold terbaik setelah melihat hasil
- ❌ Tidak ML untuk "menyelamatkan" signal yang gagal economic gate
- ❌ Tidak ensemble dari signal gagal
- ❌ Tidak pindah horizon untuk membuat hasil bagus
- ❌ Tidak 39 altcoin sekaligus — mulai 2-5 liquid
- ❌ Tidak menyebut "edge" sebelum Phase C (execution sim) lolos

---

## 7. Deliverables Minggu Ini

1. ✅ Protocol ini (STUDY-016 preregistration)
2. Data collection: desain pipeline download aggTrades + depth (python,
   via CCXT/Binance WS/REST), storage format (parquet), incremental
3. Pilot: kumpulkan 1-3 hari data BTCUSDT aggTrades (minimal)
4. Feature factory v0 + phenomenon discovery skeleton
5. Cost model validation (spread/slippage observasi)

---

## 8. Reopening/Scoping Note

Program alpha (STUDY-001..015) tetap CLOSED di dataset 1h/OI/funding.
STUDY-016 adalah **program baru** dengan kelas data baru — tidak
mengubah kesimpulan program lama. Git tetap source of truth.