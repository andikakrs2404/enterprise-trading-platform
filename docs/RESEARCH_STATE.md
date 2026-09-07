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

## TEMUAN STRUKTURAL — STUDY-013 (commit `a5834e8`, PARTIAL SUPPORT H1)

**RS Regime Directionality: H1 PARTIALLY DIDUKUNG — pertama kali lolos semua gates.**

Interaction (unconditional RS = +14.8 bps):
- Breadth: LOW +0.6 bps → HIGH **+28.5 bps** (delta +27.9)
- Trend: NEG -0.2 bps → POS **+29.7 bps** (delta +29.9)
- Dispersion: LOW +6.9 → HIGH +22.8 (VAL gagal: -8.3 → perlu investigation)

Per-year HIGH breadth: 2024 +5.0 | 2025 +24.7 | 2026 +53.6 (SEMUA POSITIF)
Per-year POS trend: 2024 +6.8 | 2025 +26.0 | 2026 +54.4 (SEMUA POSITIF)
Per-split HIGH breadth: TRAIN +15.3 | VAL +18.2 | TEST +77.6 (SEMUA POSITIF)

Caveat: TEST 4-5x TRAIN → magnitude masih epoch-dependent
Status: H1 PARTIAL — OBSERVASI PERLU EX-ANTE VALIDATION (STUDY-013B?)
Detail: `run_study013_regime.py` + `STUDY-013_REGIME.json`

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