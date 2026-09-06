# RESEARCH_STATE.md — Status Terbaru (compact)

**Update:** 2026-09-04 | **Fase:** Portfolio Construction & Economic Viability

---

## CURRENT PHASE
**STUDY-012 — Portfolio Construction & Economic Viability** (aktif)
- Commit reference: `55dd83b` (selection selesai)
- State: SELECTION SELESAI — hasil menuju REJECTED (lihat ringkas di bawah)

## SELECTION RESULT (ringkas)
- Q5 RS vs universe: hanya menang di TEST (+59 vs +11 bps gross),
  NEGATIF di TRAIN (-8 vs +5) dan VAL (-39).
- Breadth: 68% TEST vs 38% TRAIN → epoch-dependent, bukan skill konsisten.
- Turnover ~1.5x/rebalance → hancurkan edge kecil.
- **Verdict sementara: SELECTION TIDAK konsisten — lanjut ke Weighting utk konfirmasi**
- Detail: `run_study012_selection.py` + `STUDY-012_SELECTION.json`

## CURRENT HYPOTHESIS
Can portfolio selection, weighting, sizing, and exposure transform
weak frozen signals into economically viable portfolio-level edge?

## FROZEN FEATURES (input)
- **Price RS** — validated feature, not standalone alpha (STUDY-006)
- **ΔOI_share_7d** — emergent conditional feature, inconclusive (STUDY-008)
- (VOL-share = redundant, jangan dipakai)

## REJECTED (jangan dibuka tanpa hipotesis baru eksplisit)
- Compression breakout (STUDY-001, INCONCLUSIVE)
- Funding/OI absolute (STUDY-002-005, regime inversion)
- RS portfolio integration (STUDY-007, NOT CONFIRMED — postmortem ada)
- Relative participation VOL (STUDY-008A, redundant)
- Volatility regime change (STUDY-009, proxy + arah berubah)
- Cross-sectional flow (STUDY-010, unstable + cost fail)
- Market structure / breadth context (STUDY-011+011B, illusion)

## NEXT (urutan eksekusi STUDY-012)
1. Selection — apakah pemilihan Q5 RS konsisten lebih baik dari equal-weight universe?
2. Weighting — equal vs rank vs vol-scaled vs inverse-vol vs capped (preregistered, no tuning)
3. Sizing/Exposure — eksposur hanya saat signal kuat + state sesuai (rule ex-ante)
4. Net portfolio → OOS validation

## PENDING / OBSERVATION
- ΔOI_share_7d: "emergent conditional feature" — hanya direvisit jika beberapa
  family independen konvergen ke kondisi yang sama (revisit protocol STUDY-008).
- OI_growth reversal (STUDY-010): observasi, bukan feature.
- Breadth RS-specific (STUDY-011B): observasi, jangan dijadikan regime.