# STUDY-006 — Cross-Sectional Relative Strength (FREEZE)

**Status:** VALIDATED FEATURE — NOT STANDALONE ALPHA
**Date Frozen:** 2026-09-01
**Parent:** STUDY-006 Phase A (discovery) → Phase B (preregistered validation)
**Related:** STUDY-007 (Portfolio Integration) berjalan INDEPENDEN — tidak boleh mengubah definisi ini.

---

## ✓ FREEZE / IMMUTABLE — Tidak Bisa Diubah

### Definisi yang Dikunci
| Komponen | Definisi |
|----------|----------|
| **Momentum** | `ret_24h` (close pct_change 24 bar) |
| **Ranking** | Cross-sectional `rank(pct=True)` per timestamp |
| **Q5** | Top 20% rank |
| **Q1** | Bottom 20% rank |
| **Dispersion** | Cross-sectional 90–10 percentile spread of ret_24h per timestamp |
| **Disp threshold** | HIGH = spread > median global (frozen ex-ante = 0.0498) |
| **Fee** | 8 bps round-trip |

**TIDAK BOLEH:** threshold optimasi, filter atas, regime tightening, scoring optimization, perubahan horizon.

---

## Hasil Preregistered (Immutable)

| Hipotesis | Hasil | Verdict |
|-----------|-------|---------|
| H1: Q5-Q1 spread > 0 | +14.8 bps | ✅ PASS |
| H2: HIGH-disp > LOW-disp | +19.7 vs +9.9 bps | ✅ PASS |
| H3: Temporal stability | 2024 +0.055% / 2025 +0.040% / 2026 +0.385% | ✅ PASS |
| H4: Symbol stability | 22/39 (56%) | ✅ PASS (marginal) |
| H5: Net-after-cost | gross 14.8 < fee 16-24 bps | ❌ FAIL |
| H6: Effect decay | puncak R24–R48, R72 melemah | — |

---

## Kesimpulan

```unknown
Type:             Feature / Factor (BUKAN edge)
Direction:        Continuation
Primary horizon:  R24–R48
Gross spread:     +14.8 bps (HIGH-disp +19.7, LOW-disp +9.9)
Dispersion:       amplifikasi positif
Standalone alpha: REJECTED (net FAIL)
Portfolio role:   CANDIDATE (untuk STUDY-007)
Taxonomy level:   2 dari 4 (PHENOMENON → VALIDATED FEATURE → PORTFOLIO CONTRIBUTION → EDGE)
```

**Jangan menyebut "edge".** STUDY-006 berada di level 2: **VALIDATED FEATURE.**

---

## Independency Guardrail

- STUDY-007 berjalan dengan spesifikasi weighting yang SUDAH dibekukan di kode:
  - RSweight: `w = 0.5 + 0.5 × rs_rank` (linear), arah baseline dipertahankan
  - RS_Standalone: long top 50%, short bottom 50%, equal-weight
  - FEE = 8bps
- **Hasil STUDY-007 TIDAK boleh mengubah definisi/freeze STUDY-006.**
- Evaluasi STUDY-007 = incremental information (Sharpe, MaxDD, turnover, net PnL, corr), bukan memilih konfigurasi baru.
