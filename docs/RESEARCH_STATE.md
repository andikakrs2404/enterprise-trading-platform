# RESEARCH_STATE.md — Status Terbaru (compact)

**Update:** 2026-09-07 | **Fase:** PROGRAM DITUTUP (hard stop STUDY-015)

---

## PROGRAM STATUS — FINAL
**NO DEPLOYABLE ALPHA FOUND.** Program riset ditutup secara formal.

Hard-stop rule (preregistered STUDY-015) terpenuhi: dispersion tidak
menghasilkan hubungan robust setelah lag, non-overlap, temporal validation.

## KESIMPULAN AKHIR
Dataset crypto perps 2024-2026 yang digunakan:
- Mengandung berbagai **conditional historical patterns**
- **TIDAK mengandung mechanism yang cukup stabil** untuk dieksploitasi sebagai alpha.
- Cross-sectional anomalies umumnya 2-20 bps, rapuh vs 8-16 bps fee.

## HASIL PER STUDI (final)
| Study | Status |
|---|---|
| 001 | FROZEN (INCONCLUSIVE) |
| 002-005 | REJECTED (Funding/OI regime inversion) |
| 006 | VALIDATED FEATURE (Price RS — bukan edge) |
| 007 | NOT CONFIRMED + POSTMORTEM |
| 008 | VOL redundant, OI_share_7d Emergent |
| 009 | REJECTED (proxy + arah berubah) |
| 010 | REJECTED (OI_growth unstable) |
| 011 | REJECTED (market structure) |
| 011B | REJECTED (breadth context illusion) |
| 012 | REJECTED (portfolio construction) |
| 013 | INCONCLUSIVE (RS regime-dependent obs) |
| 013B | ROBUSTNESS FAILURE (definisi rapuh) |
| 014 | SUPPORTING EVIDENCE (distribusi berbeda) |
| 015 | REJECTED (dispersion mechanism FAIL) |

## YANG DIFALSIFIKASI (jangan diulang)
- Funding/OI absolut, volatility change, cross-sectional flow
- Market structure standalone, breadth context universal
- Portfolio weighting/sizing
- Single-feature discovery (semua family)
- **Dispersion sebagai regime driver RS (STUDY-015)**

## OBSERVASI YANG BERTAHAN (bukan edge)
- Price RS (STUDY-006): validated feature, conditional
- ΔOI_share_7d (STUDY-008): emergent conditional feature
- RS directionality flips antar era (STUDY-013/014): didukung distribusi
  berbeda, tapi mekanisme TIDAK teridentifikasi (STUDY-015 gagal)

## POTENSI RISET MASA DEPAN (hanya jika data baru)
- Data 2027+ untuk OOS validation observasi yang bertahan
- Tick/order-flow data (untuk deteksi flow sejati)
- Funding/OI regime dengan data lebih panjang
- **Tidak ada jalur lanjutan di dataset saat ini**