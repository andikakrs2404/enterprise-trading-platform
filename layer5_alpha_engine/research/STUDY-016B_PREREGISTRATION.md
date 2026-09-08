# STUDY-016B — Economic Feasibility Baseline (PREREGISTRATION)

**Status:** PRE-REGISTERED (sebelum signal discovery)
**Date:** 2026-09-08
**Parent:** STUDY-016A PASS (conditional) — trade-flow GO, orderbook WAIT
**Pertanyaan:** Apakah distribusi return 5–180 detik cukup besar untuk dibayar
setelah biaya (fee + spread + slippage)? Jika tidak → stop sebelum buang waktu.

---

## Konteks

Semua alpha microstructure mati di biaya jika move yang ingin diprediksi < cost.
Urutan yang benar: ukur dulu distribution of the thing to predict, SEBELUM
membangun feature apa pun.

## Horizon (dikunci)

R5s, R15s, R30s, R60s, R180s — semuanya WAJIB dilaporkan (Gate A).
Tidak ada horizon yang boleh dipilih setelah melihat hasil.

## Data

- Source: aggTrades BTCUSDT (STUDY-016A, futures, zero-gap verified)
- Price series: 1s bar dari trade price (last trade per detik)
- Return: forward overlap R_h(t) = P(t+h)/P(t) - 1
- Supplementary: non-overlap grid per horizon sbg sanity check (HAC)

## Output per horizon

| Stat | Makna |
|------|-------|
| median \|R\| | move tipikal |
| p75 / p90 / p95 / p99 \|R\| | ekor distribusi |
| mean \|R\|, std | |
| skewness R | arah bias |
| median R (signed) | drift |

## Cost Model (dikunci)

- Fee taker round-trip: **8 bps** (4 bps/side, Binance futures)
- Fee maker round-trip: **4 bps** (2 bps/side)
- Spread BTC: ~0.013 bps (dari STUDY-016A, jangan diulang)
- Slippage: estimasi dari depth (impact) — fase ini pakai spread/2 sbg konservatif

## Gate Ekonomi (dikunci SEBELUM hasil)

- **G1 (feasibility dasar):** median \|R_h\| ≥ 8 bps (fee taker RT) →
  horizon layak dieksplorasi tanpa syarat akurasi super.
- **G2 (opportunity):** p90 \|R_h\| ≥ 16 bps (2× fee) → ada event besar.
- **G3 (breadth):** jumlah observasi per horizon ≥ 1000 (bukan event langka).
- **VERDICT:** per-horizon layak/tidak; rekomendasi horizon family utk STUDY-017.

## Aturan Anti-Bias

- Semua horizon dilaporkan, bukan hanya yang bagus.
- Tidak ada threshold tuning.
- Kesimpulan SCOPED: "dalam data 72h BTCUSDT", bukan klaim universal.
- Jika median |R| < fee untuk semua horizon → STOP trade-flow discovery,
  dokumentasikan sebagai temuan negatif, evaluasi ulang program.

## Status

- [ ] Data 72h selesai dikumpulkan (collector running)
- [ ] Distribusi dihitung
- [ ] Verdict ekonomi dikeluarkan