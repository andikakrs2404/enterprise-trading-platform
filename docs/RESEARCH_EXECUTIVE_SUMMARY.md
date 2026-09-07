# RESEARCH_EXECUTIVE_SUMMARY — Program Riset Alpha Layer 5

**Status:** CLOSED | **Date:** 2026-09-07 | **Owner:** Research Desk (andika)

---

## Headline

> **No deployable alpha was identified under the tested universe, horizon,
> feature families, portfolio constructions, and realistic transaction costs.**

Kesimpulan ini SCOPED pada ruang eksperimen yang benar-benar diuji — bukan
klaim absolut bahwa "dataset tidak mengandung alpha."

---

## Objective & Dataset

- **Tujuan:** Mencari alpha cross-sectional pada crypto perpetual futures yang
  robust terhadap waktu, konstruksi portfolio, dan biaya transaksi realistis.
- **Dataset:** 39 simbol perpetual futures (altcoin), OHLCV 1h + OI + funding,
  periode Juli 2024 – Agustus 2026 (~18.9k bar/simbol).
- **Universe:** Cross-sectional ranking antar altcoin (long/short/basket).
- **Biaya:** 8/12/16 bps round-trip (realistis untuk perp futures).

## Research Framework

- Phase A (phenomenon discovery) → Phase B (pre-registered hypothesis) → OOS.
- Freeze definitions ex-ante; larang post-hoc optimization.
- Temporal split TRAIN/VAL/TEST per timeline (60/20/20).
- Non-overlap/HAC wajib untuk forward-return temporal diagnostics.
- Double-sort vs Price RS untuk menguji informasi inkremental.
- Coverage gate, per-symbol breadth, sign test, dispersion layer.
- Net-after-cost (8/12/16 bps) sebagai gate, bukan appendix.
- Hard-stop: preregistered failure criteria → hentikan branch, jangan rescue.

## Timeline STUDY-001 → STUDY-015

| Study | Topik | Verdict |
|-------|-------|---------|
| 001 | Compression Breakout | INCONCLUSIVE (frozen) |
| 001-M | Mechanism (MFE/MAE) | EXPLORATORY, frozen |
| 002-005 | Funding/OI (absolute & state) | REJECTED (regime inversion OOS) |
| 006 | Cross-sectional Price RS | VALIDATED FEATURE (bukan edge) |
| 007 | RS portfolio integration | NOT CONFIRMED (+ postmortem) |
| 008 | Relative participation (VOL/OI share) | VOL redundant; OI_share_7d emergent |
| 009 | Volatility regime change | REJECTED (proxy + arah berubah) |
| 010 | Cross-sectional flow (OI/vol growth) | REJECTED (unstable + cost fail) |
| 011 + 011B | Market structure + breadth context | REJECTED (breadth = illusion) |
| 012 | Portfolio construction (sel/weight/sizing) | REJECTED (portfolio layer falsified) |
| 013 + 013B | RS regime directionality + robustness | INCONCLUSIVE (robustness failure) |
| 014 | Distribusi 2024 vs 2026 | SUPPORTING (distribusi berbeda) |
| 015 | Dispersion → RS mechanism | REJECTED (hard stop) |

## Major Hypotheses Tested

1. Momentum/breakout continuation (Compression) — gagal OOS.
2. Funding/OI rendah → return positif — valid in-sample, regime inversion OOS.
3. Cross-sectional relative strength (24h momentum) — validated feature,
   tapi net negative setelah fee 8bps (standalone).
4. Portfolio construction dapat mengekstrak alpha dari RS — falsified
   (selection/weighting/sizing semua gagal gate).
5. Participation/flow (OI share, volume share, OI growth) — redundant atau
   temporal-unstable.
6. Market structure (leadership/breadth/rotation) sebagai alpha standalone —
   gagal; sebagai context engine — gagal cross-check.
7. Volatility regime change cross-sectional — proxy momentum.
8. **RS directionality diprediksi keadaan pasar (regime-dependent)** — observasi
   kuat (STUDY-014: distribusi berbeda secara statistik), tetapi mekanisme
   ex-ante TIDAK berhasil diidentifikasi (STUDY-015: dispersion gagal dengan
   lag, non-overlap, persistence, independent cross-check).

## Major Findings

- Cross-sectional anomaly pada data ini umumnya 2-20 bps — rapuh terhadap
  biaya 8-16 bps.
- Banyak feature ternyata representasi berbeda dari relative strength
  (proxy momentum), hilang saat double-sort.
- Pola berulang: TEST bagus / TRAIN-VAL buruk = epoch-dependence, bukan
  bukti edge. Performa TEST yang sangat bagus TIDAK cukup sebagai bukti.
- 2024 vs 2026 berasal dari distribusi yang berbeda (dispersion p<0.0001,
  skewness p=0.012, RS spread p=0.027) — breadth & mean return TIDAK berbeda.
- Dispersion TIDAK mendahului RS directionality (lagged, non-overlap, gate A
  gagal), autocorrelation rendah (0.31), high-state tidak persisten
  (median run 1-2 periode).

## What Survived vs What Was Rejected

**Survived (observasi, BUKAN edge deployable):**
- Price RS: informasi kondisional historis — validated feature, tanpa edge
  standalone/portfolio yang tervalidasi.
- ΔOI_share_7d: emergent/inconclusive feature (independen dari RS,
  fee-robust, muncul 2025+; tapi temporal consistency belum cukup).
- RS directionality tampak epoch-dependent — tanpa mekanisme ex-ante robust.

**Rejected (falsified dengan framework ketat):**
- Funding/OI absolut · Volatility change · Cross-sectional flow ·
  Market structure/breadth context · Portfolio construction ·
  Dispersion mechanism.

## Economic Viability

- Semua kandidat edge yang ditemukan: gross 2-20 bps pada horizon utama.
- Biaya realistis: 8-16 bps round-trip → mayoritas net negatif atau zero.
- Turnover tinggi (1.5-3x/rebalance untuk rank-based) memperparah friction.
- **Bottleneck: belum ada fenomena dengan gross edge >> transaction cost.**

## Final Conclusion

Dalam ruang hipotesis yang diuji (universe 39 altcoin perps, horizon
intraday-multi-hari, keluarga feature price/OI/funding/vol/flow/structure,
portfolio construction, dan biaya 8-16 bps), **tidak ada dominan alpha yang
bertahan terhadap validasi temporal, non-overlap, dan biaya realistis.**

Nilai program bukan pada strategi yang ditemukan (tidak ada yang deployable),
melainkan pada **peta falsifikasi**: keluarga hipotesis mana yang sudah mati
secara bersih dan tidak perlu diulang.

## What Would Justify Reopening

Hanya jika salah satu kondisi terpenuhi (bukan "coba lagi dengan tweak"):

1. **Data material baru:** observasi OOS 2027+ untuk menguji kembali
   ΔOI_share_7d dan RS-regime-dependence secara sah.
2. **Microstructure lebih kaya:** tick/order-flow/liquidation data untuk
   mendeteksi flow sejati (bukan proxy OI/volume 1h).
3. **Hipotesis kausal baru yang genuine:** mekanisme yang bukan varian dari
   momentum/participation/flow yang sudah difalsifikasi; harus preregistered
   dengan failure criteria di muka.

---

*Dokumen ini adalah ringkasan eksekutif. Detail lengkap per studi:*
*`docs/STUDY_INDEX.md` (indeks) · `docs/RESEARCH_STATE.md` (status) ·*
*`docs/EDGE_RESEARCH_MAP.md` (katalog) · `layer5_alpha_engine/research/` (data).*