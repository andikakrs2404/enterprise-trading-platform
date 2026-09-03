# STUDY-009 — Volatility Regime Change (Cross-Sectional) PREREGISTRATION

**Status:** PRE-REGISTERED — definisi & failure criteria dikunci SEBELUM eksekusi
**Date:** 2026-09-01
**Parent:** Natural extension dari STUDY-008 (dispersion = conditional variable)
**Tujuan:** Discovery fenomena (NON-ALPHA), bukan mencari strategi

---

## Tujuan Riset
Menguji apakah PERUBAHAN volafatility itu sendiri (bukan level, bukan breakout)
memiliki informasi cross-sectional → forward return.

## Definisi Volatility Change (dikunci ex-ante, tanpa threshold optimization)
- **Short-term vol (σ_s):** std dev of 1h returns over last 6 bars (6h)
- **Baseline vol (σ_b):** std dev of 1h returns over last 168 bars (7d)
- **Vol ratio:** `r = σ_s / σ_b` — perubahan relatif (expansion/contraction)
- **Normalisasi cross-sectional:** `rank(pct=True)` per timestamp →
  `vol_change_rank` (bukan threshold arbitrary)
- **TIDAK:** memilih threshold berdasarkan return, no config optimization

## Hipotesis Discovery (deskriptif)
- Q1 (vol contraction) vs Q5 (vol expansion) → R24 / R48 / R72
- Lihat Q1 dan Q5 TERPISAH (bukan hanya spread)
- Cek monotonicity, symbol breadth, dispersion interaction

## Framework Rules (WAJIB dari awal)
1. **Discovery** boleh pakai full sample.
2. **Semua temporal robustness/significance** pakai NON-OVERLAP ATAU HAC-aware.
   (aturan dari STUDY-008 — bukan diagnostic tambahan setelah hasil, tapi bagian desain)
3. **Temporal split** per symbol TRAIN/VAL/TEST (60/20/20).
   Jangan memilih horizon terbaik setelah melihat hasil.
4. **Independence (double-sort):**
   - vs Price RS (STUDY-006)
   - vs market dispersion
   - vs ΔOI_share_7d (frozen, STUDY-008) — kalau relevan
5. **Regime interaction:** LOW vs HIGH dispersion (definisi sudah tersedia,
   jangan buat conditional signal baru berdasarkan hasil).
6. **Cost:** net after 8 / 12 / 16 bps. Bukan hanya gross spread.

---

## FAILURE CRITERIA (dikunci ex-ante)
Tidak boleh disebut candidate feature hanya karena Q5−Q1 positif.

### Gagal (REJECTED) jika EITHER:
- (A) Tidak ada directional consistency lintas temporal split
      (sign berubah antara TRAIN/VAL/TEST)
- (B) Tidak ada temporal evidence (non-overlap sample tidak konsisten)
- (C) Breadth lemah (< 55% symbol mendukung, sign-consistent)
- (D) Tidak ada incremental information (double-sort vs Price RS gagal —
      hanya proxy momentum)
- (E) Net-after-cost ≤ 0 di 12 bps (economically not viable)

### Lolos sementara (CANDIDATE FEATURE) jika SEMUA:
- Directional consistency ✅ (sign konsisten di TRAIN/VAL/TEST)
- Temporal evidence ✅ (non-overlap konsisten)
- Breadth ✅ (≥ 55% symbol, sign-consistent)
- Independent ✅ (double-sort vs Price RS pass)
- Economically viable ✅ (net > 0 di 12 bps)

## Verdict Levels (4-level)
- INCONCLUSIVE → HYPOTHESIS_SUPPORTED → ROBUST_CANDIDATE → PRODUCTION_CANDIDATE

## Target Akhir (bukan sekadar spread positif)
Menemukan ROBUST, INCREMENTAL, ECONOMICALLY VIABLE edge.
Skeptis terhadap "statistically positive" tapi "economically useless".

## Urutan Studi
STUDY-009 (Vol Regime) → STUDY-010 (CS Flow) → STUDY-011 (Market Structure)
Lalu cek konvergensi → beri kesempatan revisit ΔOI_share_7d secara sah.
