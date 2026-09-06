# STUDY-007 POST-MORTEM — Mengapa RS Portfolio Feature Gagal?

**Parent:** STUDY-007 (frozen: NOT CONFIRMED)
**Date:** 2026-09-04
**Tujuan:** Mengidentifikasi penyebab spesifik kegagalan RS sebagai portfolio alpha
        — bukan untuk rescue, tapi untuk belajar

---

## Data FACTS dari STUDY-007

### Parameter yang dipakai
- Rebalance: per jam (24 bar = 1 hari → salah, karena STUDY-006 peak di R24-R48)
- Cost: 8 bps round-trip
- Weighting: RSweight = 0.5 + 0.5×rs_rank (linear)
- RS_Standalone: long top 50%, short bottom 50%, equal weight
- Baselines: B1_Trend (EMA crossover), B2_MeanRev (Bollinger band)

### Hasil (reanalysis R24 horizon)
```
B1_Trend:       Sharpe -0.45, MaxDD -79%, mean -0.073%/day
B2_MeanRev:     Sharpe +0.48, MaxDD -47%, mean +0.077%/day ← best
B1+RSweight:    Sharpe -0.41, MaxDD -66%, mean -0.050%/day
B2+RSweight:    Sharpe +0.49, MaxDD -38%, mean +0.059%/day
RS_Standalone:  Sharpe +0.08, MaxDD -30%, mean +0.003%/day

Incremental value:
  B1→B1+RS: ΔSharpe +0.04, ΔMaxDD +0.13
  B2→B2+RS: ΔSharpe +0.01, ΔMaxDD +0.09
  Corr: 0.994 (hampir identik)
```

---

## Penyebab Gagal (diagnosis ex-post)

### 1. Baseline Terlalu Lemah (BOTTLENECK UTAMA)
B2_MeanRev = baseline terbaik pun hanya Sharpe +0.48 di R24 (gross),
dan **negatif di 8bps net** (-0.02%).
Feature tambahan tidak bisa memperbaiki baseline yang sendirinya tidak viable.

**Insight:** "Jika baseline tidak menghasilkan uang, maka weighting/perbaikan
apsilusion — hanya bisa mengoptimalkan distribusi returns yang sudah negatif."

### 2. Signal Dilution (Corr 0.994)
RSweight ≈ hampir identik baseline (Corr 0.994).
Artinya: linear combination yang 0.5+0.5×rs_rank pada dasarnya adalah versi
yang sedikit berbeda dari baseline, bukan informasi baru.

**Insight:** Weighting linear tidak cukup untuk menghasilkan diversifikasi
informasi. Perlu non-linear mapping atau state-conditional allocation.

### 3. Turnover Terlalu Tinggi (walaupun sudah R24)
Rebalancing setiap R24 dengan equal-weight long/short = turnover yang masih
signifikan (diperkirakan 30-60% per horizon).

**Insight:** 8 bps fee × 2 arah = 16 bps per rebalance. Kalau turnover
2-3x per bulan → 32-48 bps/month friction. Untuk spread 10-15 bps,
ini menghancurkan seluruh edge.

### 4. Horizon Mismatch
STUDY-006 menemukan peak effect di R24-R48.
Tapi STUDY-007 rebalance setiap jam → banyak sinyal yang overlap dan
menambah noise + turnover tanpa memberi informasi tambahan.

**Insight:** Rebalancing frequency harus align dengan horizon effect.
Jika effect R24-R48, rebalance TIDAK LEBIH SERING dari R24.

### 5. Equal Weight 50/50 Short-Long = Arbitrer
Shorting di crypto perps mahal (funding, slippage).
Equal weight long 50% + short 50% = kedua sisi ada fee + friction.
Jika edge di kedua sisi tidak simetris, short side bisa menghancurkan.

**Insight:** Long-only mungkin lebih viable dari long-short untuk edge kecil
(di mana short side fee lebih besar dari long side).

---

## Post-Mortem Verdict

```
STUDY-007 bukan "RS gagal sebagai feature."
Tapi:
  - Baseline terlalu lemah → fee menghancurkan
  - Weighting tidak menambah informasi (linear)
  - Turnover terlalu tinggi
  - Horizon mismatch
  - Long-short simetris tidak tepat untuk edge kecil

IMPLIKASI UNTUK STUDY-012:
  - Pilih baseline yang lebih kuat (bukan just RS individual)
  - Rebalance harus match horizon effect
  - Coba long-only vs long-short
  - Ukur turnover secara explicit
  - Hanya mulai portfolio construction jika baseline bisa survive fee
```
