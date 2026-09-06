# EDGE_RESEARCH_MAP — Katalog Edge Family & Status

**Version:** 1.0 | **Date:** 2026-09-01 | **Owner:** Research Desk

Setiap edge family dievaluasi terhadap pipeline standar (PHASE A phenomenon → PHASE B pre-registered → validation). Hanya family yang lulus Phase A yang boleh masuk Phase B.

---

## ⛔ DISCOVERY FASE — SELESAI (CUTOFF di STUDY-011B)

**Tanggal:** 2026-09-04

Semua single-feature discovery diuji (11 studi). Hasil agregat:
- **Tidak ada feature yang menjadi deployable alpha standalone.**
- Cross-sectional anomalies 2-20bps, rapuh vs 8-16bps fee.
- Meta-pattern: banyak feature = representasi Relative Strength / regime-switching / multiple-testing artifact.
- Relatif bertahan lebih baik (RS, OI_share) tapi tidak cukup untuk fee.

**FROZEN FEATURES (input portfolio layer):**
- Price RS (STUDY-006) — VALIDATED FEATURE
- ΔOI_share_7d (STUDY-008) — Emergent Conditional Feature

**BUKA FASE BARU: PORTFOLIO CONSTRUCTION & ECONOMIC VIABILITY (STUDY-012)** — berhenti feature mining.

## Roadmap (fase baru)

```
DISCOVERY (selesai) ──▶ FROZEN FEATURES
                              │
                              ▼
                    PORTFOLIO RESEARCH
                    ├── Selection
                    ├── Weighting
                    └── Sizing
                              ▼
                        Regime / Exposure
                              ▼
                        NET PORTFOLIO
                              ▼
                         OOS VALIDATION
```

---

## Katalog Family

### ✅ 1. Compression Breakout / Momentum (STUDY-001)
- **Status:** INCONCLUSIVE (Track A) / FAILED OOS (Track B)
- **Arsip:** `research/STUDY-001_archive.md`
- **Temuan mekanisme:** Impulse singkat (1-8 bar) → flow exhaustion → reversal (12-24 bar). MFE/MAE simetris. Asymmetry tidak exploitable setelah 8bps.
- **Keputusan:** FROZEN. Tidak boleh dioptimasi ulang tanpa data baru + study ID baru.
- **Lesson:** Momentum pada horizon pendek ada, tapi tidak bertahan net biaya. Konsisten literatur flow/exhaustion.

### 🔄 2. Trend Pullback
- **Status:** Hipotesis baru (BUKAN utak-atik Edge 1 lama)
- **Pipeline:** PHASE A phenomenon discovery belum dijalankan
- **Catatan:** Versi awal pernah gagal → diperlakukan sebagai hipotesis baru terpisah
- **Feature:** return, EMA slope, ADX, volume

### ⬜ 3. Mean Reversion
- **Status:** Kandidat (counter-hypothesis terhadap momentum)
- **Mekanisme:** deviation dari equilibrium → revert
- **Feature:** z-score, VWAP distance, EMA distance, BB deviation
- **Pitfall:** Jangan RSI<30→LONG langsung. Definisikan deviation event → ukur forward return.

### ❌ 4. Funding Dislocation (STUDY-003/004/005)
- **Status:** REJECTED AFTER OOS
- **Arsip:** `research/STUDY-003_FUNDING_OI_PHASE_A.json`, `STUDY-004_PHASE_B.json`, `STUDY-005_OOS.json`
- **Post-mortem:** `docs/FAILURE_CASE_001.md`
- **Temuan:** FUND_LOW+OI_LOW+HIGH_VOL → PASS in-sample (Phase B), tapi **regime inversion di OOS** (TEST: -0.74%, 3/14 positive)
- **Penyebab:** Non-stationary — vol-return correlation flip +0.03→-0.05, state prevalence 10.4%→0.8%, BTC $87k→$69k
- **Keputusan:** FROZEN REJECTED. Bukan overfitting, ini regime change.

### ⬜ 5. OI Dislocation
- **Status:** Kandidat berikutnya
- **Mekanisme:** ΔOI + price → continuation / liquidation / exhaustion
- **Feature:** `oi_return = ΔOI/OI`, kombinasi dengan price return
- **Data tersedia:** metrics OI ✅

### ⬜ 6. Funding × OI State Space
- **Status:** Paling menarik (Positioning regime)
- **Mekanisme:** kombinasi funding & OI state → forward return surface
- **Matrix:** OI↑/OI↓ × Funding+/Funding− × Price↑/Price↓

### ❌ 7b. STUDY-007 — Portfolio Integration (RS incremental value test)
- **Status:** PORTFOLIO CONTRIBUTION NOT CONFIRMED
- **Hasil:** Corr(RS,baseline)=0.994 (terlalu tinggi, tidak orthogonal). ΔSharpe < 0.05 (tidak material). RS standalone Sharpe ~0.
- **Fee sensitivity:** B2_MeanRev (best baseline) saja negatif di 8bps. Seluruh baseline fee-sensitive.
- **Kesimpulan:** RS tetap VALIDATED FEATURE tetapi TIDAK layak jadi portfolio alpha contributor. Bottleneck: belum ada baseline edge cukup besar untuk survive fee.
- **Keputusan:** FREEZE. Jangan Phase C scoring/optimization. Pindah family baru.
- **Type:** Feature / Factor (BUKAN edge)
- **Direction:** Continuation
- **Primary horizon:** R24–R48
- **Gross spread:** +14.8 bps (HIGH-disp: +19.7bps, LOW-disp: +9.9bps)
- **Dispersion effect:** Positif (amplifikasi HIGH dispersion)
- **Temporal stability:** PASS (2024: +0.055%, 2025: +0.040%, 2026: +0.385%)
- **Symbol stability:** 56% (22/39) — marginal
- **Net-after-cost:** FAIL (gross 14.8bps < fee 16-24bps)
- **Standalone alpha:** REJECTED
- **Portfolio role:** CANDIDATE (untuk Portfolio Integration Study)
- **Status taxonomy:** VALIDATED FEATURE (level 2 dari 4)
- **Arsip:** `research/STUDY-006_CROSS_SECTIONAL_RS.json`, `STUDY-006_PHASE_B.json`
- **Keputusan:** FREEZE. Jangan Phase C scoring optimization. Jangan sebut "edge".
- **Pelajaran:** predictive power ada tapi terlalu kecil untuk membayar turnover → kandidat untuk ranking/weighting posisi edge lain, bukan entry signal.

### ✅ 8. Relative Participation / OI Leadership (STUDY-008)
- **Status:** ΔOI_share_7d = FROZEN INCONCLUSIVE (regime-emergent). ΔVOL_share_1d = REJECTED (redundant)
- **Temuan:** ΔOI_share_7d = continuation signal, independent dari Price RS, terkuat LOW dispersion, absent 2024 (+0.02%) → material 2025-26 (+0.96%/+1.03%) [non-overlap]
- **Taxonomy:** Emergent Conditional Feature (BUKAN alpha)
- **Revisit:** hanya jika beberapa family independen menunjuk kondisi yang sama → portfolio integration
- **Arsip:** `STUDY-008_PARTICIPATION_PHASE_A.json`, `STUDY-008_PHASE_B.json`, `STUDY-008C_TEMPORAL.json`, `STUDY-008C_DIAGNOSTIC.json`, `STUDY-008_FREEZE.md`

### ✅ 9. Volatility Regime Change (STUDY-009)
- **Status:** REJECTED. Vol change = proxy momentum (double-sort hilang), arah berubah 3x (2024 contraction, 2025 flat, 2026 expansion), non-overlap tidak konsisten.
- **Reanalysis kunci:** "edge muncul 2026" → ternyata "arah fenomena berubah 3 era". Pentingnya non-overlap diakui.
- **Arsip:** `STUDY-009_VOLREGIME.json`, `run_study009_reanalysis.py`

### ⬜ 10. Cross-Sectional Flow (STUDY-010)
- **Status:** REJECTED. VOL_growth & OI_growth.
- **OI_growth:** independen dari Price RS (corr 0.044) tapi temporal INCONSISTENT + net≤0 di 12bps. Observasi: potensi REVERSAL di Price RS neutral (bukan feature).
- **Volume:** lemah, proxy sebagian.
- **Arsip:** `STUDY-010_CS_FLOW.json`, `STUDY-010_FREEZE.md`
- **Insight:** independen ≠ berguna. Cross-sectional anomalies 2-20bps, rapuh vs fee.

### 🔄 11. Market Structure (STUDY-011 + 011B)
- **Status:** STUDY-011 REJECTED (tidak ada market-structure alpha standalone). STUDY-011B REJECTED (breadth belum valid sebagai context engine — multiple-testing illusion).
- **Breadth:** observasi RS-specific, JANGAN dijadikan feature/regime.
- **Catatan penting:** STUDY-011B membuktikan framework valid — temuan +0.434% dibunuh setelah validation (cross-check OI_share gagal).
- **Arsip:** `STUDY-011_MARKET_STRUCTURE.json`, `STUDY-011B_CONTEXT_ENGINE.json`, `STUDY-011B_FAILURE.md`

### ⬜ 12. Portfolio Construction & Economic Viability (STUDY-012 — FASE BARU)
- **Status:** PREREGISTERED — fase portfolio research dimulai
- **3 pertanyaan:** Selection, Weighting, Sizing/Exposure
- **Baseline:** Price RS (frozen), bukan random
- **Starting point:** STUDY-007 POST-MORTEM
- **Arsip:** `STUDY-012_PREREGISTRATION.md`, `STUDY-007_POSTMORTEM.md`

### ⬜ 13. Liquidation Cascade
- **Status:** Kandidat (butuh data liquidation memadai)

---

## Pipeline Progress Tracking

| Family | RAW | CONTRACT | FEATURE | EVENT | FWD | MECH | PRE-REG | TRAIN | VAL | TEST | MTC | COST | ROBUST | VERDICT |
|--------|-----|----------|---------|-------|-----|------|---------|-------|-----|------|-----|------|--------|---------|
| Compression (S001) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | FROZEN |
| Trend Pullback | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Mean Reversion | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Funding Dislocation | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| OI Dislocation | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Funding×OI State | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
