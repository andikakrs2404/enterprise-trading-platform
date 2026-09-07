# RESEARCH_STATE.md — Status Terbaru (compact)

**Update:** 2026-09-04 | **Fase:** Portfolio Construction & Economic Viability

---

## CURRENT PHASE
**STUDY-012 — Portfolio Construction & Economic Viability** (SELESAI FORMAL)
- Commit reference: `0c1b71a`
- State: Selection REJECTED → Weighting FAIL gate → Sizing TIDAK menambah → **PORTFOLIO LAYER FALSIFIED**

## SELECTION RESULT (ringkas)
- Q5 RS vs universe: hanya menang TEST (+59 vs +11 bps gross), NEGATIF TRAIN/VAL.
- **VERDICT: SELECTION REJECTED** (epoch-dependent, turnover tinggi)

## WEIGHTING RESULT (ringkas)
- 5 skema (ew, rank, vol, invvol, capped): SEMUA FAIL gate.
- Selection effect -11.3 bps | Weighting effect +7-8 bps | Interaction 0.
- Exposure: return-dari-Q5 flip sign antar skema → sinyal ≈ noise floor.
- **VERDICT: WEIGHTING TIDAK MENAMBAH NILAI EKONOMIS**

## SIZING RESULT (ringkas)
- Conditional exposure (rs>0.8 + ret24>median) = TIDAK berbeda dari Q5 EW → no improvement.
- **VERDICT: SIZING TIDAK MENYELAMATKAN**

## PENUTUPAN PORTFOLIO LAYER
Selection + Weighting + Sizing SEMUA TIDAK menghasilkan economic edge robust.
**Kesimpulan kumulatif: Portfolio construction bukan sumber edge utama.**

## TEMUAN STRUKTURAL 2025 (paling menarik — investigasi)
- RS spread per tahun: 2024 **-0.33% (REVERSAL)** | 2025 **-0.04% (flat)** | 2026 **+0.40% (continuation)**
- 2024 = alt bull (avg R24 +0.28%), 2026 = mild bear (-0.05%), 2025 = transition.
- Dispersion menurun: 0.032 → 0.025 → 0.022.
- **Hipotesis baru: RS BUKAN alpha universal — regime-specific. Reversal di alt-bull, continuation di mild-bear.**
- Detail: `run_study012_sizing.py` + `STUDY-012_SIZING_2025.json`

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