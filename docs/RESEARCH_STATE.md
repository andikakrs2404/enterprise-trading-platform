# RESEARCH_STATE.md — Status Terbaru (compact)

**Update:** 2026-09-06 | **Fase:** PROGRAM STATUS — NO DEPLOYABLE ALPHA

---

## PROGRAM STATUS
**No deployable alpha found.** Tapi program BERHASIL memfalsifikasi banyak
hipotesis yang biasanya menjadi "cerita favorit" di crypto quant.
Ruang pencarian berkurang drastis.

## STUDY STATUS (terakhir)
- STUDY-013: Interesting Observation (RS conditional sign flips per epoch)
- STUDY-013B: Robustness Failure (VAL fragility, rolling percentile gagal)
- STUDY-012: Portfolio layer REJECTED (selection/weighting/sizing semua gagal)
- STUDY-011+011B: Market structure / breadth context REJECTED

## SURVIVING HYPOTHESIS (satu-satunya yang layak dikejar)
Relative Strength bersifat regime-dependent (reversal ↔ continuation),
tetapi mekanisme regime tersebut BELUM berhasil diidentifikasi secara robust.

## SATU PERTANYAAN YANG MASIH LAYAK
**Apa yang membuat RS berubah dari reversal (2024) menjadi continuation (2026)?**

Bukan "indikator apa yang mengaktifkan RS?" — itu pertanyaan feature mining.
Tapi: "apakah 2024 dan 2026 berasal dari distribusi pasar yang BERBEDA?"

Kandidat (belum diuji, hanya observasi):
- Cross-sectional dispersion level (lebih rendah 2026 vs 2024)
- Alt average return (2024 +0.28%, 2025 -0.17%, 2026 -0.05%)
- Kondisi market yang lebih fundamental (bull/bear multi-bulan)

## YANG SUDAH DIFALSIFIKASI (jangan diulang)
- Funding/OI absolut
- Volatility change
- Cross-sectional flow
- Market structure standalone
- Portfolio weighting/sizing
- Breadth context engine universal
- Single-feature discovery (semua family)
- Threshold optimization
- Feature engineering baru

## YANG BELUM BOLEH DILANJUTKAN
- Feature baru apapun
- Weighting/sizing baru
- Portfolio tricks
- "Optimization" dari STUDY-013

## FROZEN FEATURES (input jika ada riset lanjutan)
- Price RS (STUDY-006) — validated feature
- ΔOI_share_7d (STUDY-008) — emergent conditional
- RS regime-dependent observation (STUDY-013) — interesting but NOT validated