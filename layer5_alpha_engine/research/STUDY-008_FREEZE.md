# STUDY-008 — Relative Participation (FREEZE)

**Status:** FROZEN — lihat per komponen di bawah
**Date Frozen:** 2026-09-01
**Parent:** STUDY-008 Phase A → Phase B → C (temporal + diagnostic)

---

## Per-Komponen Status

### ΔVOL_share_1d — **REJECTED (REDUNDANT)**
- **Alasan:** Double-sort vs Price RS gagal. Conditional pada Price RS neutral, spread → -0.031%. Tidak ada incremental information di luar STUDY-006. Hanya proxy momentum.

### ΔOI_share_7d — **FROZEN: INCONCLUSIVE / REGIME-EMERGENT**
- **Status taxonomy:** **Emergent Conditional Feature** (bukan Alpha Candidate)
- **Karakterisasi:**
  - Relative OI participation continuation (Q5 > Q1, arah konsisten)
  - Absent/flat di 2024 (+0.02% non-overlap)
  - Material positif di 2025 (+0.96%) dan 2026 (+1.03%) [non-overlap]
  - Terkuat di LOW dispersion regime (+0.32%)
  - Independent dari price momentum (double-sort PASS)
  - Fee robust (positif sampai 16 bps di TEST)
- **Bukan deployable alpha.** Tapi juga bukan failed hypothesis.
- **Keputusan:** FREEZE. Jangan reject. Jangan lanjut optimasi. Jangan post-hoc hypothesis mining (mengapa 2025 bagus).

---

## Framework Update (IMPORTANT — dari research lead)

**Overlapping forward returns berbahaya untuk temporal diagnostics.**

Regel:
- **Discovery statistics** → boleh pakai seluruh observations (descriptive power).
- **Temporal robustness / significance / independence diagnostics** → WAJIB pakai non-overlapping ATAU HAC-aware methodology.

Alasan: R72 → observasi berdekatan berbagi sebagian besar future-return window → sample tidak independent → estimasi bisa bias (mis. 2024 yang terlihat -0.61% reversed, padahal sebenarnya +0.02% flat setelah non-overlap).

**Ini mencegah interpretasi salah seperti reversal-2024 terulang lagi.**

---

## Revisit Protocol

ΔOI_share_7d akan diuji ulang sebagai **conditional portfolio feature** apabila (di masa depan) beberapa family independen menunjuk kondisi yang sama:
- Price RS, dispersion, volatility, liquidity, volume participation

Jika beberapa family independen menunjuk kondisi yang sama → ada alasan kuat untuk kembali ke OI-share dalam konteks portfolio integration.
