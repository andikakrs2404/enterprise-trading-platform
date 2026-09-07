# STUDY-013 — RS Regime Directionality (ex-ante state → continuation/reversal/flat)

**Status:** PRE-REGISTERED — definisi regime dikunci SEBELUM eksekusi
**Date:** 2026-09-05
**Parent:** STUDY-012 structural finding (RS spread per year flips sign)
**Tipe:** Bukan alpha discovery. Bukan portfolio construction. Bukan new feature.
Tapi: apakah arah RS (sign) dapat diprediksi dari measurable market state?

---

## Pertanyaan Tunggal

**H0:** Arah RS (continuation vs reversal) tidak dapat diprediksi dari
measurable market state sebelumnya. Perubahan epoch hanyalah noise.

**H1:** Ada market state yang dapat diukur ex-ante yang menentukan apakah
RS berperilaku continuation, reversal, atau flat.

---

## Aturan Keras

1. **TIDAK BOLEH menggunakan label post-hoc** ("2024=bull", "2025=transition").
   Semua state harus diukur dari data timestamp-by-timestamp.
2. **Definisi regime dikunci SEBELUM eksekusi.** Tidak boleh dipilih
   setelah melihat hasil.
3. **State dikalkulasi HANYA dari data MASA LALU** (lagged). Tidak ada
   forward-looking leakage.
4. **Discovery boleh full sample.** Semua temporal robustness/significance
   menggunakan non-overlapping atau HAC.
5. **Failure criteria:**
   - (A) Net RS spread di condition == 0 atau tidak signifikan → FAIL
   - (B) Tidak konsisten split TRAIN/VAL/TEST → FAIL
   - (C) Condition hanya aktif <10% waktu → INCONCLUSIVE (sample kecil)
   - (D) Net spread tidak survive 12bps fee → INSUFFICIENT

---

## 3 Candidate Regime States (dikunci ex-ante)

### State 1: MARKET BREADTH (measurable)
- **Definisi:** % altcoin yang ret24 > 0 pada setiap timestamp
- **Lag:** 24 jam (menggunakan breadth T-24 jam sebelumnya)
- **Split:** LOW (<median), HIGH (>median)
- **Rationale:** rendah breadth = banyak alt turun = momentum lemah = reversal?

### State 2: CROSS-SECTIONAL DISPERSION (measurable)
- **Definisi:** std(ret24) antar semua simbol pada setiap timestamp
- **Lag:** 24 jam
- **Split:** LOW (<median), HIGH (>median)
- **Rationale:** high dispersion = pasar tidak seragam = RS lebih informatif?

### State 3: INDEX TREND (measurable)
- **Definisi:** slope rata-rata ret24 (mean alt return, 24h)
- **Lag:** 24 jam
- **Split:** NEGATIVE (mean<0), POSITIVE (mean>0)
- **Rationale:** pasar sedang naik vs turun → RS berbeda?

---

## Evaluasi per State

Untuk setiap state (breadth, dispersion, index_trend):
1. Conditional RS spread (R24): Q5-Q1 di state LOW vs HIGH
2. Per year: apakah arah konsisten?
3. Per split (TRAIN/VAL/TEST): apakah konsisten?
4. Net @ 12 bps
5. Coverage: berapa % waktu state aktif?
6. Breadth per state: berapa % simbol Q5>Q1?
7. Interaction: apakah state + RS = informasi yang lebih besar dari RS saja?

---

## Jika H1 TIDAK didukung (H0 dipertahankan)
→ Program riset ini kemungkinan besar selesai.
Kesimpulan: dataset 2024-2026 tidak mengandung exploitable edge
yang diprediksi secara sistematis dari market state.

## Jika H1 didukung
→ Bukanalpha lagi — ini REGIME ENGINE yang menjelaskan kapan RS aktif.
Tetap harus diuji OOS. Minimal menunggu data 2027 untuk validasi.
