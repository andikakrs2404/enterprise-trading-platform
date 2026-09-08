# DATA STRATEGY — Historical Microstructure Data Evaluation

**Date:** 2026-09-08 | **Decision:** Ivan — evaluasi Tardis.dev vs Binance Public vs collector sendiri

---

## 1. Ringkasan Keputusan

**Collector 72h TETAP JALAN** — sebagai validasi pipeline internal (latency, quality tools,
replay engine, cost calibration). **BUKAN** sebagai satu-satunya sumber historical research.

Setelah 72h, kita punya dual-track data:

```
DATA
      │
      ├── OUR LIVE COLLECTOR (BTCUSDT 72h, real-time validated)
      │
      └── HISTORICAL DATA (Tardis / Binance)
              │
      ┌───────┴────────┐
      │                │
  2024-01 ──────┐      │
  2024-07 ──────┤      │
  2025-01 ──────┼── cross-period validation
  2025-07 ──────┤      │
  2026-01 ──────┤      │
  2026-07 ──────┘      │
                       ↓
             SAME REPLAY ENGINE → SAME FEATURE ENGINE → SAME STUDY PROTOCOL
```

## 2. Evaluasi Opsi Data

### A. Tardis.dev — RECOMMENDED untuk STUDY-018/019
| Fitur | Status |
|-------|--------|
| Tick-by-tick trades (with side) | ✅ |
| Incremental L2 order book updates | ✅ (full-depth) |
| Order book snapshots top 25 / top 5 | ✅ |
| Liquidations | ✅ |
| Funding / OI / mark / index price | ✅ (derivative ticker) |
| Historical replay (reconstruction) | ✅ (client-side full book reconstruction) |
| Binance USDT-M Futures | ✅ |
| Exchange native format via API | ✅ |

**Schema cocok dengan pipeline kita:**
- trade: `{timestamp, localTimestamp, id, price, amount, side}` — side = aggressor langsung
- book_change: `{timestamp, localTimestamp, is_snapshot, side, price, amount}`
- timestamp + localTimestamp = latency measurement built-in

**Cocok untuk:** STUDY-018 (order book phenomena — L2 imbalance, microprice, queue dynamics),
STUDY-019 (event interaction), STUDY-020 (execution reality — book walk dengan depth granular).

**Pricing:** Solo/Academic/Pro/Business subscription. "Perpetuals" data plan.
No discounts, no one-off purchases. Free trial available.

### B. Binance Public Data (data.binance.vision) — GRATIS, TAPI TERBATAS
| Data | Tersedia? |
|------|-----------|
| Futures aggTrades | ✅ (via /fapi/v1/aggTrades — sudah kita pakai) |
| Futures klines | ✅ |
| Futures depth (L2 incremental) | ❌ TIDAK ADA di public data |
| Liquidations | ❌ |
| OI/funding historical | ❌ (hanya endpoint real-time) |

**Kesimpulan:** Bagus untuk trade-level backfill (gratis), TIDAK cukup untuk order book research.

### C. Collector Sendiri — VALIDASI + LIVE
| Kekuatan | Keterbatasan |
|----------|--------------|
| Kontrol penuh format | Depth @3.6s (tidak cukup untuk queue) |
| Zero-gap aggTrades | Hanya 72h |
| Latency terukur | Single exchange |
| Multi-symbol siap | Belum cukup historical |

**Peran:** validasi pipeline, live data ke depan, backup.

## 3. Tabel Keputusan Praktis

| Kebutuhan | Sumber Terbaik | Biaya | Waktu |
|-----------|---------------|-------|-------|
| Trade-flow (STUDY-017) | Collector 72h + Binance aggTrades gratis | $0 | Siap |
| L2 imbalance/microprice (STUDY-018) | **Tardis** | $$$ | Setup ~1 hari |
| Queue dynamics (STUDY-018 lanjutan) | **Tardis** | $$$ | Setup ~1 hari |
| Liquidations | **Tardis** | $$$ | Setup ~1 hari |
| Cross-period 2024-2026 | **Tardis** | $$$ | Download per bulan |
| Execution sim Slippage | **Tardis** (book walk) | $$$ | Setup ~1 hari |
| Live going forward | Collector kita | $0 | Sudah jalan |

## 4. Rekomendasi

1. **Collector 72h: biarkan selesai** (validasi pipeline — sedang berjalan).
2. **Untuk STUDY-017 (trade flow): gunakan data sendiri + Binance gratis** — tidak perlu
   bayar, aggTrades sudah cukup.
3. **Untuk STUDY-018+ (order book): evaluasi Tardis Perpetuals plan** — ini satu-satunya
   cara mendapat L2 granular historical yang kita butuhkan.
4. **Cek kompatibilitas dulu sebelum bayar:** ambil free trial / sample data, verifikasi
   schema langsung dengan replay_engine kita. (Jangan bayar sebelum ini.)
5. **Pertimbangkan Akademik:** jika ada akses akademik, Solo/Academic plan bisa lebih murah.

## 5. Langkah Berikut

- [ ] Collector 72h selesai → quality report → STUDY-016B final
- [ ] STUDY-017 jalan (data sendiri, gratis)
- [ ] Jika STUDY-017 PASS: ambil Tardis sample (free) → verifikasi dengan replay_engine
- [ ] Jika verifikasi OK: subscribe Perpetuals → download 2024-2026 titik bulan
- [ ] STUDY-018 dengan L2 granular + cross-period validation