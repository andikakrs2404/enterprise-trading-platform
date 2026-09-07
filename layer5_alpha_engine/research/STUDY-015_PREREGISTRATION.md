# STUDY-015 — Dispersion & RS Directionality (MECHANISM STUDY)

**Status:** PRE-REGISTERED
**Date:** 2026-09-07
**Parent:** STUDY-014 supporting evidence (dispersion berbeda 2024 vs 2026)
**Tipe:** RESEARCH/MECHANISM study — BUKAN alpha discovery, BUKAN strategy mining

---

## Pertanyaan

Apakah perubahan dispersion MEND AHUI dan MENJELASKAN perubahan
RS directionality?

**BUKAN:** dispersion HIGH → long Q5 (itu strategy mining)
**TAPI:** Dispersion(t) → RS behavior(t+24/48/72h)

---

## 4 Test (dikunci ex-ante)

### 1. LEVEL
Apakah RS spread berbeda ketika dispersion tinggi vs rendah?
- Split dispersion: LOW/MID/HIGH (ternaries, predefined — bukan threshold dicari)

### 2. CHANGE
Apakah Δdispersion memprediksi perubahan RS?
- dispersion rising → behavior?
- dispersion falling → behavior?
- (lagged, bukan contemporaneous)

### 3. PERSISTENCE
Apakah regime dispersion bertahan?
- Autocorrelation / state duration
- Jika berubah tiap jam → tidak berguna ekonomis

### 4. INDEPENDENT VALIDATION
Cross-check dengan feature independen (tidak dipakai definisikan dispersion):
- Apakah feature independen menampakkan struktur serupa (RS reversal→continuation)?

---

## DECOMPOSITION (wajib)
Pecah RS spread menjadi Q5 return, Q1 return, Q5-Q1. Kondisikan terhadap dispersion.

### Scenario A (true momentum interaction)
High dispersion: Q5 ↑↑, Q1 ↓ → benar momentum-dispersion
### Scenario B (Q1 collapse)
High dispersion: Q5 ~0, Q1 ↓↓ → "RS continuation" hanya Q1 collapse, bukan Q5 strength

---

## HARD RULES
- Lagged dispersion (24/48/72h), bukan contemporaneous
- Predefined bins/quantiles, TIDAK "cari threshold terbaik"
- Horizon ditentukan SEBELUM melihat hasil
- Semua temporal validation non-overlap/HAC

---

## GATE (hard stop jika gagal)
PASS mekanistik HANYA jika:
- (A) dispersion/state MEND AHUI RS (lagged)
- (B) hubungan muncul di TRAIN dan VAL
- (C) TEST konsisten
- (D) tidak hanya berasal dari Q1 atau Q5 (harus kedua sisi / jelas)
- (E) tidak hilang saat non-overlap/HAC
- (F) tidak bergantung pada satu threshold

Jika dispersion tidak memberi hubungan robust setelah lag, non-overlap,
temporal validation, dan independent cross-check → **HENTIKAN PROGRAM**.

Kesimpulan saat itu: dataset mengandung conditional historical patterns,
tapi TIDAK ada mechanism cukup stabil untuk dieksploitasi sebagai alpha.
