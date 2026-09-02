# Failure Case #001 — Funding + OI + Volatility Dislocation

**Status:** REJECTED AFTER OOS
**Date:** 2026-09-01
**Studies:** STUDY-003 (Discovery) → STUDY-004 (Phase B) → STUDY-005 (OOS)

---

## Apa Yang Terlihat Menjanjikan (STUDY-003/004)

Kandidat: `FUND_LOW + OI_LOW + HIGH_VOL → E[R24] ≈ +0.32%`

**Mekanisme ekonomi yang masuk akal:**
"Crowded longs + high leverage = reversal. Uncrowded + volatile = slow repricing upward."

**Bukti cross-symbol:** 27/39 (69%) symbol positif
**Sign test:** p=0.001
**Temporal stability:** First half +0.22%, Second half +0.09% (same sign)
**Dispersion:** std paling rendah di antara semua state
**Net-after-cost:** +15.9bps net pada 8bps fee, CI tidak menyentuh 0
**Baseline comparison:** HIGH_VOL only = -0.022% → kombinasi material lebih baik

Hampir semua slide presentasi quant akan lolos.

---

## Kenapa Mati di OOS (STUDY-005)

### Penyebab Utama: Regime Inversion

| Window | State E[R24] | Baseline | Lift | % Pos Sym |
|--------|-------------|----------|------|-----------|
| TRAIN | +0.341% | +0.108% | +0.23% | 76.9% |
| VAL | +0.486% | -0.165% | +0.65% | 81.8% |
| TEST | **-0.735%** | -0.035% | **-0.70%** | 21.4% |

**Lift berubah dari +0.65% menjadi -0.70%.** Ini bukan decay, ini **inversion**.

### Struktur Pasar Berubah

**1. Volatility-return correlation FLIP:**
- TRAIN: rv~R24 = +0.033 (high vol → positive return)
- TEST: rv~R24 = **-0.053** (high vol → negative return)

**2. Volatility regime shift:**
- TRAIN: HIGH_VOL R24 = +0.17%
- TEST: HIGH_VOL R24 = **-0.35%**
- TEST: LOW_VOL R24 = **+0.11%** (kebalikan total dari TRAIN)

**3. State almost disappeared:**
- TRAIN: 10.4% of all data triggered state
- VAL: 4.1%
- TEST: **0.8%** (n=1,796 — terlalu kecil untuk significance apapun)

**4. BTC price regime shift:**
- TRAIN: BTC median $87k (post-halving bull)
- VAL: BTC median $111k (bull market peak)
- TEST: BTC median **$69k** (bear/correction)

**5. OI distribution shift:**
- TRAIN: OI percentile mean = 0.32 (condensed di low)
- TEST: OI percentile mean = **0.71** (condensed di high)

---

## Pelajaran Metodologis

### 1. Preregistered validation (Phase B) bukan OOS protection
STUDY-004 PASS semua (H1-H5). Tapi STUDY-005 GAGAL total.
**Artinya:** validasi in-sample, seberapa rigor sekalipun, tidak menggantikan temporal OOS.

### 2. State prevalence shift = warning sign
State turun dari 10.4% → 0.8%. Kandidat yang semakin jarang di periode baru → kemungkinan non-stationary.

### 3. Correlation structure shift = regime change
Ketika korelasi rv~R24 berubah dari +0.03 menjadi -0.05, hubungan fundamental sudah berubah.
**Periksa korelasi structure per window** sebagai early warning.

### 4. Market regime (BTC level) menentukan
Semua state sebelumnya diuji saat bull market ($87-111k). OOS di bear market ($69k).
Funding/OI dynamics mungkin berbeda di bull vs bear — ini **bukan edge universal**.

### 5. Dispersion yang rendah bukan jaminan
Di TRAIN, std=0.32 (paling rendah). Di TEST, std meledak (karena reversal).

---

## Status Akhir

```
STUDY-003: Phase A Discovery → Observed Phenomenon
STUDY-004: Phase B Preregistered → Validated In-Sample
STUDY-005: OOS Temporal Split → FAILED (regime inversion)
STATUS: REJECTED — Not Generalizable
TIDAK DIBUKA LAGI.
```

---

## Relevansi untuk Riset Mendatang

Ketika mengeksplorasi family edge baru:
1. **Cek korelasi structure shift per window** sebagai early warning non-stationarity
2. **State prevalence** harus konsisten lintas period — jika menurun drastis, signal mungkin regime-dependent
3. **Market regime (BTC level, vol regime)** harus dipertimbangkan sebagai confounder
4. **Jangan terkecoh** temporal stability + cross-symbol — keduanya bisa berubah di OOS yang benar
