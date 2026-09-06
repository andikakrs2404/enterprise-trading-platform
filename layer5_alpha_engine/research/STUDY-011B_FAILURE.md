# STUDY-011B — Failure Case Documentation

**Date:** 2026-09-04
**Parent:** STUDY-011B Context Engine Validation
**Status:** REJECTED — breadth bukan context engine universal

---

## Temuan yang Dihancurkan

STUDY-011 menemukan: breadth Q5 → RS spread +0.434% (aggregate)
→ terlihat menjanjikan, 4x baseline.

STUDY-011B membuktikan:
- **2024 breadth HIGH → RS spread -0.353%** (NEGATIF — arah terbalik)
- **OI_share_7d tidak diperkuat breadth** — justru lebih kuat di breadth LOW
- **Training window breadth interaction ≈ nol** (+0.06%), TEST ekstrem (+2.52%)
- **Coverage hanya 15% timestamps** → ekspurse rendah, sample kecil

## Penyebab Ilusi
1. **Multiple testing** — setelah banyak eksperimen, sesuatu pasti terlihat bagus
2. **TEST window anomaly** — angka besar ditopang oleh 15% waktu
3. **Tidak di-cross-check** dengan feature independen lain (OI_share)

## Pelajaran Framework
Setiap temuan context/conditional yang menarik setelah banyak eksperimen
**WAJIB di-cross-check dengan feature independen lain**. Jika tidak
mengaktifkan feature lain, kemungkinan besar multiple-testing artifact.
