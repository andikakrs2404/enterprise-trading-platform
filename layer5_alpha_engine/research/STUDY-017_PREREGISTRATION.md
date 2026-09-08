# STUDY-017 — Trade Flow Phenomena (PREREGISTRATION)

**Status:** PREREGISTERED, EXECUTION LOCKED until STUDY-016B final verdict
**Date:** 2026-09-08
**Depends on:** STUDY-016B final economic baseline (GO/NO-GO)
**Principle:** Hermes = falsification engine, bukan optimizer. Jangan ubah horizon/threshold
berdasarkan hasil. Jika threshold gagal, STOP — jangan rescue spec.

---

## 1. Hypothesis

**H0:** Trade flow phenomena (signed volume, imbalance, intensity, burst) tidak
memiliki hubungan forward-hipotetik yang cukup kuat untuk membayar biaya transaksi
(fee 8bps + spread + slippage) pada BTCUSDT futures.

**H1:** Tertentu trade flow states mendahului (t+5s s/d t+180s) return yang cukup
besar secara ekonomi, konsisten di TRAIN/VAL, tidak hilang dengan non-overlap/HAC.

## 2. Data & Price Series

Source: STUDY-016A aggTrades BTCUSDT (zero-gap, zero-gap verified)
Price: 1s bar (last trade per second), tadi dihitung di STUDY-016B

## 3. Feature Definitions (4 families, KUNCI)

### Family A — Signed Volume
```python
# Lee-Ready simplified: m = is_buyer_maker
aggressive_buy  = qty * (1 - m)
aggressive_sell = qty * m
# signed: positive = net buying pressure
signed_volume = aggressive_buy - aggressive_sell  # per window
# window sizes (non-overlap, setiap horizon)
# 5s, 15s, 30s, 60s, 180s
```

### Family B — Trade Imbalance
```python
# buy_ratio: fraction of volume on buy side
buy_ratio = aggressive_buy.sum() / (aggressive_buy.sum() + aggressive_sell.sum())
# window: [t-60s, t] untuk mengukur imbalance STATE saat ini
# return diukur: [t, t+5s], [t, t+15s], ..., [t, t+180s]
```

### Family C — Trade Intensity
```python
# density: seberapa aktif market pada t
trades_per_second = len(trades_in_window) / window_seconds
volume_per_second = qty.sum() / window_seconds
# window: [t-30s, t]
```

### Family D — Burst Events (binary)
```python
# threshold: volume > rolling p95
# atau trade_count > rolling p95
# window: 60s rolling
burst = volume_60s > volume_60s_p95
```

**Kunci:** Threshold D (p95) ditentukan dari TRAIN ONLY, diterapkan ke VAL/TEST.
Tidak ada threshold tuning di VAL/TEST.

## 4. Horizons & Targets (DIKUNCI)

Semua horizon WAJIB dilaporkan. Tidak ada horizon boleh dipilih.

| Horizon | Target |
|---------|--------|
| R5s | forward return 5 detik (bps) |
| R15s | forward return 15 detik |
| R30s | forward return 30 detik |
| R60s | forward return 60 detik |
| R180s | forward return 180 detik |

## 5. Measurement

Untuk setiap feature × horizon:
- Spearman correlation (rank-based, robust)
- Return spread: per-tercile/high-low (Q3-Q1 atau top/bottom 30%)
- Sign test: fraction of non-overlap windows dengan arah benar

## 6. Data Splits (DIKUNCI dari data aggregator)

Jika 72h data ≤ 3 hari:
- **TRAIN:** hari 1-2 (atau earliest 70%)
- **TEST:** hari 3 (atau latest 30%)
- **VAL:** HOLD (jika data cukup, split 70/15/15; jika tidak, hanya TRAIN/TEST)

Jika 72h data = ~3 hari (expected):
- TRAIN: 0-48h (50,000+ bars)
- TEST: 48-72h (25,000+ bars)

## 7. Hard Gates (DIKUNCI)

Gate A: **Semua horizon** harus dilaporkan (tidak ada cherry-pick).

Gate B: Train / Validation / Test. Tidak ada threshold tuning menggunakan TEST.

Gate C: Economic gate.
  - Laporkan: gross edge, spread, fees, estimated slippage, net edge
  - net edge > 0 pada fee 8bps untuk trade-flow phenomenon, bukan hanya pemenang

Gate D: Event frequency. Minimum 10% bungkus covered untuk family binary (burst).
  Jika burst coverage < 10% → family burst ditolak.

Gate E: Family-level decision per horizon.
  - PASS: konsisten di TRAIN dan TEST, net edge > 0, frequency > 10%
  - FAIL: salah satu conditions tidak terpenuhi
  - Tidak rescue spec

Gate F: Final verdict per family.
  - Jika semua horizon FAIL → family REJECTED
  - Jika ada horizon PASS tapi tidak konsisten → INCONCLUSIVE
  - Jika semua horizon PASS → HYPOTHESIS SUPPORTED

## 8. Final Decision (Setelah semua gates)

Jika SEMUA family FAIL:
  → TRADE-FLOW RESEARCH STOP
  → Negative finding documented
  → Evaluasi: apakah masalahnya di feature, atau di distribusi return?

Jika minimal satu family PASS:
  → Lanjut ke STUDY-018 (order book phenomena) dengan dataset yang sama
  → Record mechanism yang survive untuk STUDY-019 (event interaction)

## 9. Prohibition

❌ Jangan menambah family selain A/B/C/D
❌ Jangan mengubah threshold berdasarkan hasil
❌ Jangan mengganti horizon berdasarkan hasil
❌ Jangan menambah feature engineering
❌ Jangan rescue spec (jika gagal, STOP)