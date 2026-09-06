# STUDY-012 — Portfolio Construction & Economic Viability PREREGISTRATION

**Status:** PRE-REGISTERED — H0/H1 & baseline dikunci ex-ante
**Date:** 2026-09-04
**Parent:** POST-mortem STUDY-007, END of single-feature discovery (STUDY-011B cutoff)
**Tujuan:** Apakah kombinasi + selection + sizing dapat menghasilkan economic edge
        dari feature yang terlalu lemah secara individual.

---

## Konteks
11 studi menunjukkan single feature ≠ necessarily alpha.
Bahkan feature dengan spread, independence, regime interaction  tetap bisa mati
karena temporal instability, overlap, multiple testing, redundancy, transaction cost.
**Sekarang uji hipotesis: kombinasi + selection + sizing menghasilkan edge.**

## H0 / H1 (preregistered, keras)
```
H0: Tidak ada portfolio construction yang menghasilkan peningkatan
    risk-adjusted NET performance yang ROBUST dibanding baseline,
    setelah accounting untuk turnover + cost.
H1: Portfolio construction menggunakan feature FROZEN dapat mengubah
    weak standalone signals menjadi portfolio-level edge yang
    economically viable.
```

## Baseline (harus kuat, bukan random)
- buy/short berdasarkan **Price RS** dengan construction sederhana
- Membandingkan terhadap portfolio random TIDAK cukup.
- Baseline = equal-weight top-Q5 Price RS (long) + short bottom-Q5 (atau long-only)

---

## Tiga Pertanyaan Terpisah (jangan dicampur → optimization swamp)

### 1. SELECTION
Apakah portfolio memilih Q5 RS secara konsisten lebih baik daripada
equal-weight universe?
- Bukan mencari feature baru (Price RS sudah validated)
- Ukur: hit rate, mean-VS-universe, coverage

### 2. WEIGHTING (paling menarik)
Bandingkan secara preregistered (TANPA tuning parameter berdasar TEST):
- **equal weight**
- **rank weight** (linear ∝ rank)
- **volatility-scaled** (1/σ)
- **inverse-volatility**
- **capped rank weight** (memberi bobot, tapi cap exposure max per asset)

Pertanyaan: apakah sebagian besar "alpha" yang hilang sebenarnya berasal
dari portfolio construction yang buruk?

### 3. EXPOSURE / SIZING (mungkin paling penting)
Gross edge 5-20 bps per event → mungkin tidak cukup untuk unconditional trading.
Tapi kalau exposure hanya diambil saat:
- signal kuat (top-Q5)
- dispersion/market state sesuai (definisi ex-ante)
- liquidity cukup
maka economics mungkin berubah.
**Activation rule DITENTUKAN ex-ante, bukan dicari dari hasil.**

---

## Framework Rules (seperti biasa)
1. Temporal split per symbol 60/20/20 (TRAIN/VAL/TEST)
2. Temporal evidence NON-OVERLAP / HAC (aturan STUDY-008)
3. Turnover dieksplisitkan + dihitung cost
4. Cost 8/12/16 bps; slippage awareness
5. Compare terhadap baseline kuat, bukan random
6. Report net, Sharpe, MaxDD, turnover, breadth

## FAILURE CRITERIA (ex-ante)
REJECT jika:
- (A) Tidak ada portfolio construction yang > baseline net (setelah cost)
- (B) Improvement hanya di TEST (TRAIN/VAL tidak konsisten)
- (C) Turnover tidak realistis (> compatible dengan horizon)
- (D) Net ≤ 0 di 12 bps (economically not viable)

---

## Starting Point
- **STUDY-007 POST-MORTEM** (yang sudah dibuat) sebagai diagnosis awal
- Feature frozen yang boleh dipakai: **Price RS** (primary), **ΔOI_share_7d** (secondary, frozen)
- Horizon: R24 (primary, align STUDY-006 peak)

## Anti-Optimization Guardrail
- Tidak ada grid search parameter.
- Semua weighting scheme di-test SEBAGAI TUJUAN, bukan dipilih terbaik lalu dipromote.
- Bandingkan SEMUA secara adil dengan baseline yang sama.

## Prinsip Yang Dijaga
- Jangan anggap kegagalan 11 studi = bukti portfolio layer PASTI berhasil.
- Portfolio layer adalah hipotesis BARU; bisa juga false hope.
- Jika setelah selection + weighting + sizing + exposure + realistic cost + OOS
  masih tidak survive → kesimpulan kuat: **dataset ini tidak mengandung
  exploitable edge yang cukup besar utk horizon & universe yang ditarget.**
  Dan itu adalah endpoint riset yang SANGAT bernilai.
