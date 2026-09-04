# STUDY-011 — Market Structure (BTC → ETH → Alt) PREREGISTRATION

**Status:** PRE-REGISTERED — hipotesis & failure criteria dikunci ex-ante
**Date:** 2026-09-01
**Parent:** Program riset — family yang BENAR-BENAR berbeda secara konsep
**Tujuan:** Menangkap informasi dari hubungan ANTAR KELOMPOK aset, bukan atribut individual coin.

---

## Kenapa Ini Berbeda dari Semua Study Sebelumnya
Semua STUDY-001..010 beroperasi di layer: **atribut individual coin**
(price rank, OI rank, volume rank, volatility, funding, participation).
Market Structure berbeda: **hubungan antar kelompok aset** dan
dominance/leadership shift — jauh lebih orthogonal terhadap Price RS.

## Kandidat Fitur Market Structure (dikunci ex-ante)
1. **BTC momentum leadership** — BTC ret_24h > median universe?
   (risk-on/risk-off signal untuk alt)
2. **ETH vs BTC relative strength** — ETH/ret vs BTC/ret
3. **Alt breadth** — berapa % altcoin di atas 20d moving average (naik/turun)
4. **Alt breadth change** — Δ breadth (breadth expansion/contraction)
5. **Dominance shift** — BTC dominance (relative share) naik/turun
6. **Capital rotation** — perbandingan momentum BTC vs ETH vs Alt basket

Semua di-test sebagai **market-state conditional variable** terhadap forward
return universe (bukan hanya single coin).

## H0 / H1
```
H0: Market structure factors TIDAK menambah informasi di luar
    cross-sectional Price RS individual coins.
H1: Market structure memberi incremental info — timing/regime signal
    yang menambah/mengurang eksposur semua alt secara simultan.
```

## Framework Rules (seperti study sebelumnya)
1. Discovery full sample; temporal non-overlap/HAC (aturan STUDY-008)
2. Temporal split per symbol 60/20/20
3. Double-sort vs Price RS bila relevan
4. Regime interaction (LOW/HIGH dispersion)
5. Net after 8/12/16 bps
6. Lapor Q1 & Q5 terpisah, bukan hanya spread

## Failure Criteria (ex-ante)
REJECT jika:
- (A) Tidak ada incremental info (double-sort hilang)
- (B) Arah berubah antar era tanpa mekanisme struktural kuat
- (C) Temporal evidence non-overlap tidak konsisten
- (D) Net ≤ 0 di 12 bps (economically not viable)

## Pertanyaan Kunci yang Dijawab
- Apakah ketika BTC memimpin (risk-on), alt secara sistematis outperform?
- Apakah alt breadth expansion memprediksi continuation vs reversal?
- Apakah dominance shift menandakan regime switch?

## Konteks Program Lebih Luas
Jika STUDY-011 juga gagal → pertanyaan besar:
**Apakah sumber edge utama ada di signal discovery (single feature),
atau di portfolio construction, sizing, dan regime timing DI ATAS
feature-feature yang sudah ada?**
Ini pertanyaan yang jauh lebih menarik daripada mencari indikator ke-11
yang menghasilkan spread 3 bps.
