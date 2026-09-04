# STUDY-010 — Cross-Sectional Flow (FREEZE)

**Status:** FREEZE — lihat per kandidat
**Date:** 2026-09-01
**Parent:** STUDY-010 preregistered (H0 flow=proxy, double-sort core)

---

## Per-Kandidat Status

### VOL_growth_rank — **REJECTED**
- Conditional spread (Price RS neutral) = +0.05% (lemah)
- Correlation w/ Price RS = 0.144 (moderat)
- Tidak menunjukkan independence kuat maupun economic viability

### OI_growth_rank — **REJECTED (dengan observasi)**
- Independence: corr 0.044 (rendah) — BUKAN momentum proxy
- Double-sort pada Price RS netral: **spread -0.14% (REVERSED)**
  → setelah kontrol momentum, OI growth tinggi → return RENDAH
- Temporal: **INCONSISTENT** (train -0.071%, test +0.238%)
- Cost: net ≤ 0 di 12 bps (TEST)
- **Alasan reject:** temporal instability + economic non-viability
  (bukan karena redundant dengan Price RS)

### Status Observasi (bukan feature, bukan alpha)
```
"Potential REVERSAL behavior after OI growth, observable only
 when Price RS is neutral."
```
Dicatat sebagai **fenomena/observasi**, bukan feature candidate.
Karakter regime belum jelas, temporal tidak stabil.

---

## Insight Metodologis
- **Independen ≠ berguna.** OI growth independen dari momentum, tapi
  independen saja tidak cukup — harus temporal stable + economically viable.
- Cross-sectional anomalies di data ini umumnya 2-20 bps, rapuh terhadap
  8-16 bps biaya.
- Hipotesis awal "flow = momentum terselubung" TIDAK sepenuhnya terbukti:
  OI growth cukup independen. Tapi independen bukan jaminan value.

## Revisit
TIDAK masuk kategori Emergent Conditional Feature (berbeda dari ΔOI_share_7d
karena lack temporal stability + cost viability + clear regime character).
