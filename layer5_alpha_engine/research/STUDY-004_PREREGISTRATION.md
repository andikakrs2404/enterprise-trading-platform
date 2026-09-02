# STUDY-004 — Phase B PREREGISTRATION (Funding/OI Dislocation kandidat)

**Preregistered:** 2026-09-01
**Parent:** STUDY-003 (Phase A phenomenon discovery)
**Status:** PRE-REGISTERED — definisi dikunci SEBELUM testing
**Mode:** Verification (BUKAN strategy optimization)

> Aturan emas: Phase B menjawab "apakah fenomena ini benar-benar ada?",
> BUKAN "bagaimana memonetisasinya?". Tidak ada threshold/TP/SL/leverage search.

---

## Hipotesis yang DI-PRE-REGISTER (hanya 1 kombinasi, sempit)

**H1 — Drift positif:**
State `FUND_LOW + OI_LOW + HIGH_VOL` memiliki `E[R24] > 0` DAN lebih tinggi dari baseline.

**H2 — Driver utama vol (klarifikasi critical):**
Apakah `HIGH_VOL` SAJA sudah cukup menghasilkan drift ke R24?
- Jika `HIGH_VOL only` ≈ `FUND_LOW+OI_LOW+HIGH_VOL` → funding/OI adalah PENUMPANG
- Jika `FUND_LOW+OI_LOW+HIGH_VOL` >> `HIGH_VOL only` dan juga >> `FUND_LOW+OI_LOW+LOW_VOL` → funding/OI punya peran

**H3 — Temporal stability:**
`E[R24] > 0` di KEDUA split (First Half & Second Half).

**H4 — Cross-symbol:**
Efek muncul di >60% symbol (bukan hanya rata-rata positif).

**H5 — Net after cost:**
Net expectancy > 0 pada biaya 8bps, 10bps, 12bps round-trip (entry+exit).

---

## Definisi State (dikunci, TANPA optimasi)

| Komponen | Definisi (dari STUDY-003) |
|----------|---------------------------|
| **FUND_LOW** | funding_rate percentile per symbol < 0.33 (cross-sectional) |
| **OI_LOW** | sum_open_interest percentile per symbol < 0.33 (cross-sectional) |
| **HIGH_VOL** | rolling 100-bar realized vol symbol > median global |
| **R24** | (close[t+24]/close[t] - 1) × 100% |

**Exit rule:** Tinjau R di horizon 1/3/6/12/24 (descriptive), TANPA memilih yang terbaik.

---

## Protokol Testing (dikunci)

1. **Temporal split per symbol:** 60% train / 20% val / 20% test (bukan random, berbasis timestamp)
2. **Baselines wajib (4 minimum):** unconditional, random timestamp, same-vol (HIGH_VOL only), matched conditions
3. **Net-after-cost:** 8/10/12 bps round-trip, entry+exit
4. **MTC eksplisit:** karena hanya 1 hipotesis H1, MTC default langsung signifikan; H4 (symbol-level) pakai sign test
5. **Label:** jangan sebut "edge" — "preregistered hypothesis validation"

---

## Bukan Yang Dilakukan

- ✖ Tidak mencari threshold optimal funding/OI/vol
- ✖ Tidak TP/SL optimization
- ✖ Tidak leverage/position sizing
- ✖ Tidak memilih horizon "terbaik" untuk exit
- ✖ Tidak MTC mencoba-coba banyak state

---

## Dokumentasi

- State, definisi, protokol DAHULU → testing
- Hasil dicatat apa adanya (positif/negatif, tanpa cherry-pick)
- Jika gagal → freeze, tanpa forcib optimize
