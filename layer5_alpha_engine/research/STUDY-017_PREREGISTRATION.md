# STUDY-017 — Trade Flow Phenomena (PREREGISTRATION — FROZEN)

**Status:** FROZEN (preregistered, execution locked until STUDY-016B final verdict)
**Date:** 2026-09-08 (v2 — diperbarui dengan definisi lengkap)
**Depends on:** STUDY-016B final economic baseline (GO/NO-GO)
**Principle:** Hermes = falsification engine, bukan optimizer. Jika gate gagal → STOP, tidak ada rescue spec.

---

## 1. Hypothesis

**H0:** Trade flow phenomena tidak memiliki hubungan dengan forward return yang
cukup kuat untuk membayar biaya transaksi (fee 8bps + spread ~0.1bps + slippage)
pada BTCUSDT futures dalam horizon 5-180s.

**H1:** Kondisi trade flow tertentu mendahului return yang cukup besar secara
ekonomi, konsisten TRAIN/VAL/TEST, tidak hilang dengan non-overlap/HAC.

## 2. Data & Definisi

- **Source:** STUDY-016A aggTrades BTCUSDT (futures, zero-gap)
- **Price series:** 1s bar, last trade price per second
- **Trade side:** dari `is_buyer_maker` (m):
  - `aggressive_buy = qty × (1 - m)` (buyer taker)
  - `aggressive_sell = qty × m` (seller taker)

## 3. Feature Definitions — 4 Family (FROZEN, tidak bisa diubah)

### Family A — Signed Volume
| ID | Feature | Formula |
|----|---------|---------|
| TF001 | signed_volume_5s | Σ(buy_vol - sell_vol) window 5s |
| TF002 | signed_volume_15s | Σ(buy_vol - sell_vol) window 15s |
| TF003 | signed_volume_30s | Σ(buy_vol - sell_vol) window 30s |

### Family B — Trade Imbalance
| ID | Feature | Formula |
|----|---------|---------|
| TF010 | imbalance_5s | (buy_vol - sell_vol) / (buy_vol + sell_vol) window 5s |
| TF011 | imbalance_15s | same, window 15s |
| TF012 | imbalance_30s | same, window 30s |

### Family C — Trade Intensity
| ID | Feature | Formula |
|----|---------|---------|
| TF020 | trades_per_sec_30s | n_trades / 30s |
| TF021 | volume_per_sec_30s | Σqty / 30s |
| TF022 | volume_accel_30s | Δ(volume_per_sec) antara 2 window 30s berurutan |

### Family D — Burst Events (binary)
| ID | Feature | Formula |
|----|---------|---------|
| TF030 | volume_burst_p95 | volume_60s > rolling p95 (volume_60s) — TRAIN only |
| TF031 | aggressor_burst_p95 | |signed_volume_60s| > rolling p95(|signed|) — TRAIN only |
| TF032 | trade_burst_p95 | n_trades_60s > rolling p95 — TRAIN only |

**Threshold p95 dihitung dari TRAIN ONLY**, diterapkan ke VAL/TEST.

## 4. Horizon & Target (FROZEN)

**Semua horizon WAJIB dilaporkan — tidak boleh cherry-pick.**

| Horizon | Target |
|---------|--------|
| R5s | forward return 5s (bps) |
| R15s | forward return 15s |
| R30s | forward return 30s |
| R60s | forward return 60s |
| R180s | forward return 180s |

## 5. Split Methodology (FROZEN)

Dari data 72h:
- **TRAIN:** 48 jam pertama (default; jika data kurang, 70% earliest)
- **VAL:** 12 jam berikutnya (15% middle)
- **TEST:** 12 jam terakhir (15% latest)

Jika data < 48h: hanya TRAIN/TEST (70/30), VAL = skip, dicatat sebagai limitasi.

## 6. Cost Model (FROZEN, dari cost_model.py)

| Komponen | Nilai |
|----------|-------|
| Taker fee RT | 8.0 bps |
| Maker fee RT | 4.0 bps |
| Spread | diukur dari depth (BTC ~0.013 bps) |
| Slippage | dihitung dari book walk (execution_simulator) |
| Latency | ~47ms depth / ~270ms ticker (diukur) |

Net edge = gross edge − (fee + spread + slippage + latency penalty)

## 7. Hard Gates (FROZEN)

**Gate A — Semua horizon dilaporkan.** Tidak cherry-pick.
**Gate B — TRAIN/VAL/TEST.** Tidak ada tuning memakai TEST.
**Gate C — Economic gate.** Net edge > 0 setelah fee 8bps + cost realistis.
  Dilaporkan: gross, spread, fees, slippage, net — sejak hari pertama.
**Gate D — Event frequency.** Binary features (burst) wajib coverage ≥ 10%.
  Jika burst coverage < 10% → family D ditolak.
**Gate E — Family-level decision per horizon:**
  - PASS: konsisten TRAIN & TEST, net edge > 0, freq ≥ 10%
  - FAIL: salah satu tidak terpenuhi → REJECTED (no rescue)
**Gate F — Final verdict per family:**
  - Semua horizon FAIL → family REJECTED
  - Sebagian PASS → INCONCLUSIVE
  - Semua PASS → HYPOTHESIS SUPPORTED (untuk family itu)

## 8. Threshold & Parameter (BEBAS DARI HASIL)

Semua sudah dikunci di FEATURE_REGISTRY.md (TF001-TF032).
**TIDAK ADA parameter yang bisa diubah setelah melihat hasil.**

## 9. Prohibition

❌ Jangan menambah family selain A/B/C/D
❌ Jangan mengubah threshold/horizon/cost berdasarkan hasil
❌ Jangan rescue spec yang gagal
❌ Jangan gunakan TEST untuk tuning

## 10. What Happens After

- Semua family FAIL → **TRADE-FLOW DISCOVERY STOP** → temuan negatif didokumentasikan
- ≥1 family PASS → lanjut STUDY-018 (order book) dengan dataset yang sama
- Hasil per family dicatat di FEATURE_REGISTRY (status updated)