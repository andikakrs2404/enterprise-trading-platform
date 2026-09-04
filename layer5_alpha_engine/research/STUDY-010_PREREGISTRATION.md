# STUDY-010 — Cross-Sectional Flow PREREGISTRATION

**Status:** PRE-REGISTERED — H0/H1 & failure criteria dikunci SEBELUM eksekusi
**Date:** 2026-09-01
**Parent:** STUDY-008 (relative participation), STUDY-009 (vol regime, rejected)
**Tujuan:** Apakah flow signal membawa informasi yang TIDAK dijelaskan Price RS?

---

## Logo Meta-Pattern (dari seluruh program)
Banyak feature cross-sectional = cara berbeda mengukur "pemenang vs pecundang
relatif". Saat dikontrol Price RS, edge hilang (STUDY-006 price RS, STUDY-008
VOL_share, STUDY-009 vol change semua momentum proxy).

## Pertanyaan Riset (jauh lebih kuat dari "ranking OI growth")
**Apakah flow bergerak LEBIH DULU daripada price?**
Bukan: "apakah flow bergerak bersama price?"
Jika flow prediktif hanya karena bergerak bersamaan → proxy momentum.
Jika flow prediktif lebih dulu (leading) → informasi baru.

## H0 / H1 (hard, preregistered)
```
H0: Flow hanyalah proxy dari Price RS.
    Setelah Price RS dikontrol, tidak ada sisa informasi.
H1: Flow mengandung informasi yang tetap ada setelah Price RS dikontrol.
```
**Double-sort BUKAN diagnostic tambahan — bagian inti studi.**

## Kandidat Flow (dikunci)
- **OI growth rank** — ΔOI over 24h, rank per timestamp
- **Volume growth rank** — Δvolume over 24h, rank per timestamp
- (Akan dicek juga persistence 1d/3d/7d seperti STUDY-008)

## Framework Rules (WAJIB)
1. **Discovery** full sample; **temporal** = non-overlap / HAC (aturan STUDY-008)
2. **Temporal split** per symbol 60/20/20
3. **Double-sort sejak awal:** Price RS = Q3 (netral), lalu flow Q1→Q5.
   Kalau conditional spread hilang → langsung reject.
4. **Regime interaction** LOW/HIGH dispersion (definisi tersedia)
5. **Cost** net 8/12/16 bps

---

## FAILURE CRITERIA (ex-ante — langsung reject jika salah satu)

### A: Conditional spread ≈ 0 setelah kontrol Price RS
Double-sort: flow spread pada Price RS netral (Q3) ≈ 0 → momentum proxy.

### B: Arah berubah antar era tanpa penjelasan struktural kuat
Misal: 2024 positif, 2025 negatif, 2026 positif tanpa mekanisme jelas
→ regime-switching, bukan stable signal.

### C: Temporal evidence gagal (non-overlap tidak konsisten)

### D: Economically not viable (net ≤ 0 di 12 bps di TEST)

---

## Metodologi Tahapan
- **Tahap 1:** flow vs future return (discovery)
- **Tahap 2:** flow vs Price RS correlation (Spearman + quintile overlap)
  — early warning momentum terselubung
- **Tahap 3:** double-sort sejak awal
- **Tahap 4:** temporal + non-overlap + cost

## Target Akhir
Menemukan ROBUST, INCREMENTAL, ECONOMICALLY VIABLE edge.
Jika flow juga runtuh ke momentum proxy → memperkuat meta-pattern:
**Dalam data crypto perps 2024-2026, sebagian besar cross-sectional anomaly
hanyalah representasi berbeda dari Relative Strength.**

## Urutan
STUDY-010 (Flow) → STUDY-011 (Market Structure) → cek konvergensi.
