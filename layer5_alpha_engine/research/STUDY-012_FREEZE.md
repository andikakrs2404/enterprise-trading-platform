# STUDY-012 — FREEZE (Portfolio Construction & Economic Viability)

**Status:** FROZEN — CLOSED (all sub-questions FAIL)
**Date:** 2026-09-05

---

## Sub-results

| Sub-question | Verdict |
|---|---|
| Selection (Q5 RS vs universe) | REJECTED — epoch-dependent only (TEST positive only) |
| Weighting (5 schemes) | REJECTED — all fail gate; weight effect +7-8bps insufficient |
| Sizing (conditional exposure) | REJECTED — identical to Q5 EW |

## Penutupan Formal

Portfolio construction bukan sumber edge utama:
- Selection justru merugikan (-11.3 bps full-sample)
- Weighting effect (+7-8 bps) terlalu kecil mengkompensasi
- Semua skema gagal konsistensi TRAIN/VAL/TEST
- Sinyal berada di noise floor (flips sign antar konstruksi)

## Temuan Struktural (observasi, bukan hipotesis tervalidasi)

RS spread flips arah per tahun:
- 2024: -0.33% (reversal)
- 2025: -0.04% (flat)
- 2026: +0.40% (continuation)

**Observasi ini bukan bukti RS regime-specific — itu hipotesis baru yang harus diuji.**
(Di-preregister sebagai STUDY-013)
