# STUDY-008C — ΔOI_share_7d Temporal Stability Investigation

**Status:** INVESTIGATION (bukan validasi alpha, bukan rejection)
**Date:** 2026-09-01
**Parent:** STUDY-008 Phase B (INCONCLUSIVE)
**Kandidat:** ΔOI_share_7d → R72, independent dari Price RS (double-sort PASS)

---

## Preregistered Hypotheses (dikunci ex-ante)

**H1 — Monotonic improvement:**
Apakah edge (Q5-Q1 spread R72) meningkat monoton dari waktu ke waktu?
Split: per-bulan atau per quarter.
Jika monoton naik → structural change.
Jika fluktuatif → noise-dominated.

**H2 — Symbol concentration:**
Apakah edge terkonsentrasi pada beberapa simbol?
Metrik: leave-one-symbol-out.
Jika drop banyak → edge tidak robust.

**H3 — Dispersion conditional:**
Apakah edge hanya muncul di LOW dispersion?
(Sesuai temuan Phase A: participation works better di pasar tenang)

**H4 — Period emergence:**
Apakah edge hanya muncul setelah 2025?
Split: 2024 vs 2025+.

---

## Yang TIDAK dilakukan
- Tidak mencari threshold baru
- Tidak mencari horizon lain
- Tidak menambah filter
- Tidak scoring optimization

## Target Output
Deskriptif — memahami KARAKTER edge, bukan mengoptimalkannya.
