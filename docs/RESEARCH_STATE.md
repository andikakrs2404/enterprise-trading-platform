# RESEARCH_STATE.md — Status Terbaru (compact)

**Update:** 2026-09-04 | **Fase:** Portfolio Construction & Economic Viability

---

## CURRENT PHASE
**STUDY-012 — Portfolio Construction & Economic Viability** (aktif)
- Commit reference: `9c198cb`
- State: SELECTION REJECTED. WEIGHTING SELESAI — semua skema FAIL gate.

## SELECTION RESULT (ringkas)
- Q5 RS vs universe: hanya menang di TEST (+59 vs +11 bps gross), NEGATIF TRAIN/VAL.
- Breadth 68% TEST vs 38% TRAIN → epoch-dependent.
- Turnover ~1.5x → hancurkan edge.
- **VERDICT: SELECTION REJECTED/NOT CONFIRMED** (freeze, jangan re-examine)

## WEIGHTING RESULT (ringkas)
- 5 skema (ew, rank, vol, invvol, capped): SEMUA FAIL gate
  (TRAIN/VAL net@12 negatif; hanya TEST positif atau nol).
- Weighting effect kecil (+7-11 bps) vs selection effect (-11 bps) → weighting
  tidak bisa memperbaiki underlying information yang lemah.
- Exposure diagnostic: % return dari Q5 flips sign (EW -22% vs rank +26%)
  → tidak ada allocation skill robust.
- **VERDICT SEMENTARA: WEIGHTING TIDAK MENAMBAH NILAI — epoch dependence persists**
- Detail: `run_study012_weighting.py` + `STUDY-012_WEIGHTING.json`

## NEXT
- Sizing/Exposure (pertanyaan terakhir) → setelah itu keputusan: portfolio layer
  mampu atau tidak mengubah frozen features menjadi economic edge.

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