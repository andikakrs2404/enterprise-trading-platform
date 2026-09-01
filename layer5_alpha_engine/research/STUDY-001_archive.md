# STUDY-001 — Compression Breakout Research (ARCHIVE)

**Status:** `FROZEN`
**Date Closed:** 2026-09-01
**Framework Version:** P1.7 v2.1
**Copyright/Rule:** Hasil ini TIDAK boleh dioptimasi ulang, dibuka kembali, atau dihidupkan
dengan threshold baru, tanpa *data independen baru* dan *study ID baru*.

---

## Executive Summary

**Outcome:** No deployable alpha identified.

Dua hipotesis diuji:
- **Track A** — Compression Breakout → **INCONCLUSIVE**
- **Track B** — Trend Continuation After Volatility Expansion → **FAILED OOS**

Tidak ada hipotesis yang menunjukkan:
- Net profitability stabil
- Cross-window stability
- Statistical robustness
- Economic significance setelah biaya

**Universe:** BTC, ETH, SOL, BNB, XRP (replication: 39 simbol)
**Timeframe:** 1H
**Periode:** 2024-07 → 2026-08

---

## Framework Controls (diterapkan)

### Data Controls
- Per-symbol temporal split
- No look-ahead (ADX/OI diukur dari bar sebelum trigger)
- OI lagged, Funding lagged

### Statistical Controls
- Train / Validation / Test (60/20/20 per-symbol temporal)
- Permutation testing
- Effect size reporting
- Multiple-testing correction: **Bonferroni, Holm, FDR**

### Execution Controls
- Fee = 8bps (round-trip)
- Gross vs Net reporting

### Robustness Controls
- Long vs Short separation
- Symbol stability
- Regime analysis
- ADX analysis

---

## Track A — Compression Breakout

**Hypothesis:** Compression breakout produces positive expectancy.

| Metric | Result |
|--------|--------|
| Gross | Marginally positive |
| Net | Negative or near zero |
| OOS | Not stable |
| Symbol Stability | Weak |
| Regime Stability | Weak |
| Statistical Significance | Not demonstrated |

**Final Verdict:** `INCONCLUSIVE`

**Reason:** Evidence insufficient to support deployment. Further optimization
prohibited under this study ID.

---

## Track B — Pre-Registered Hypothesis

**Hypothesis:** Trend continuation after volatility expansion.

**Conditions (frozen before testing):**
- Compression setup
- Breakout trigger
- Volume surge > 1.3
- ADX > 35
- OI > 0

**Results:**
- **Net Expectancy (OOS):** Negative
- **Statistical Significance:** Not demonstrated
- **Symbol Stability:** Not demonstrated

**Final Verdict:** `FAILED OOS`

**Reason:** Performance deteriorates outside training data. No evidence of durable
alpha. Further threshold optimization prohibited under this study ID.

---

## ADX Investigation

**Observation:** Local peak detected at ADX ≈ 39–44.

| Correction | p-value |
|-----------|---------|
| Raw | 0.0146 |
| FDR | 0.102 |
| Bonferroni | 0.102 |

**Conclusion:** Sweet spot not confirmed. Most likely explanation: exploration
artifact or insufficient evidence.

**Status:** `DO NOT TRADE` · `DO NOT OPTIMIZE` · `DO NOT REOPEN`
without new independent data.

---

## Mechanism Findings (nilai penelitian tertinggi)

### Return Decay
MFE/MAE profile menunjukkan: edge (jika ada) hidup sangat singkat (~1–6 bar),
kemudian memudar pada 12–24 bar.

**Interpretation:** Evidence suggests **short-term impulse** rather than persistent
trend continuation.

**Research Value:** Memotivasi studi masa depan pada:
- time-to-peak
- return decay
- MFE profile
- MAE profile
- optimal holding horizon

Tanpa menggunakan studi ini sebagai bukti alpha.

---

## Replication Plan (Prioritas 2)

**Objective:** Bukan alpha discovery. Menguji stabilitas temuan negatif.

**Expansion:** Universe 5 → 39 simbol.

**Success Criterion:** Jika universe diperluas menghasilkan PF ≈ 1 dan net
expectancy ≤ 0, maka tingkat keyakinan penolakan meningkat substansial.

---

## Replication Results (39 Symbol Full Universe)

| Window | n | Gross | Net | PF | tstat | p |
|--------|---|-------|-----|----|----|-----|
| TRAIN | 357 | +0.227% | +0.147% | 1.373 | 2.429 | 0.015 |
| VAL | 180 | +0.015% | -0.065% | 0.840 | 0.183 | 0.854 |
| TEST | 267 | -0.017% | -0.097% | 0.783 | -0.231 | 0.818 |
| **OOS** | 447 | — | **-0.084%** | **0.805** | — | 0.940 |

**Kesimpulan replikasi:** TRAIN positif (PF 1.37, p=0.015) TETAPI OOS net negatif
(PF 0.805, p=0.94). Kesimpulan negatif **terkonfirmasi robust** di 39 simbol.

MFE/MAE decay profile terkonfirmasi di universe luas:
`1bar MFE+0.47/MAE-0.37 → 24bar MFE+2.74/MAE-2.68`
→ MFE dan MAE simetris (tidak ada asimetri yang bisa dieksploitasi holding).

---

## Closure Statement

- [x] Research completed.
- [x] No production deployment approved.
- [x] No further optimization authorized under STUDY-001.
- [ ] Future work must be registered under a **new study identifier**.

---

## Koordinat File Data

| File | Isi |
|------|-----|
| `research_manifest.json` | Keputusan dua track, pre-registration |
| `research_freeze_document.json` | Freeze protocol (Prioritas 1) |
| `anti_data_snooping.json` | Temporal split, MTC, ADX curve |
| `track_b_trend_continuation.json` | Hasil Track B (5 simbol) |
| `replication_39symbol.json` | Replication study (39 simbol) |
| `adx_quantile_study.json` | ADX quantile/decile study |
