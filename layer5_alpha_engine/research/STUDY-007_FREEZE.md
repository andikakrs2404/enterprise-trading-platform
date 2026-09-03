# STUDY-007 — Portfolio Integration (FREEZE)

**Status:** PORTFOLIO CONTRIBUTION NOT CONFIRMED
**Date Frozen:** 2026-09-01
**Parent:** STUDY-006 (VALIDATED FEATURE)
**Related:** STUDY-007 reanalysis (R24 horizon aligned)

---

## ✓ FREEZE / IMMUTABLE

### Apa yang Diuji
Apakah Cross-Sectional RS memberi incremental information di atas hypothetical baselines (trend-follow, mean-reversion)?

### Definisi yang Dikunci (pre-frozen)
- RSweight: `w = 0.5 + 0.5 × rs_rank`, arah baseline dipertahankan
- RS_Standalone: long top 50%, short bottom 50%
- FEE: 8 bps round-trip
- Rebalance: setiap 24 bar (R24 aligned)

---

## Hasil (Immutable)

### Portfolio Metrics (R24, net 8bps)
| Portfolio | Sharpe | MaxDD | Mean/day |
|-----------|--------|-------|----------|
| B1_Trend | -0.45 | -0.791 | -0.073% |
| B2_MeanRev | +0.48 | -0.473 | +0.077% |
| B1+RSweight | -0.41 | -0.664 | -0.050% |
| B2+RSweight | +0.49 | -0.384 | +0.059% |
| RS_Standalone | +0.08 | -0.297 | +0.003% |

### Incremental Value
| Baseline → +RS | ΔSharpe | ΔMaxDD | Corr |
|----------------|---------|--------|------|
| B1 → B1+RS | +0.04 | +0.126 | 0.994 |
| B2 → B2+RS | +0.01 | +0.089 | 0.994 |

### Fee Sensitivity
B2_MeanRev (best baseline): +0.48 @ 0bps → **-0.02 @ 8bps** → -0.27 @ 12bps
RS_Standalone: +0.08 @ 0bps → **-2.03 @ 8bps** → -3.08 @ 12bps

---

## Kesimpulan

```unknown
RS INFORMATIONAL VALUE:
  Corr(RS, baseline) = 0.994 → TIDAK orthogonal
  ΔSharpe < 0.05 → tidak material
  RS standalone Sharpe ~0 → tidak ada edge sendiri

PORTFOLIO CONTRIBUTION:
  MaxDD reduction nyata (+9-13pp) → tapi di ekosistem yang sudah fee-sensitive
  Tidak menambah Sharpe secara material

BOTTLENECK SEBENARNYA:
  Bukan kurangnya filter/scoring
  Tapi baseline edge sendiri terlalu tipis untuk survive fee
  Seluruh ekosistem (trend/momentum/reversion) fee-sensitive di crypto perps
```

---

## Status Akhir STUDY-006/007

```
STUDY-006: VALIDATED FEATURE (level 2/4)
  ✅ Fenomena ada, temporal stabil, dispersion structure real
  ❌ Tidak layak standalone alpha (net-after-cost fail)

STUDY-007: PORTFOLIO CONTRIBUTION NOT CONFIRMED (level 3/4)
  ❌ Incremental information tidak terbukti
  ❌ Corr terlalu tinggi (0.994)
  ❌ Sharpe uplift tidak material

RS remains: VALIDATED FEATURE
RS does NOT qualify as: Standalone Edge / Portfolio Alpha Contributor

NEXT: Family baru — cari fenomena dengan gross edge >> transaction cost
```
