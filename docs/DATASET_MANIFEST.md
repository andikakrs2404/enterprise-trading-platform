# DATASET_MANIFEST — Freeze Snapshot Riset Alpha (2024-2026)

**Status:** FROZEN — dataset ini dipakai untuk seluruh studi STUDY-001..015
**Date:** 2026-09-07
**Lokasi:** `/home/rtk/Bot-Multi-Edge-metrics/data/`

---

## Isi

| Direktori | Jumlah | Isi | Periode |
|-----------|--------|-----|---------|
| `klines/` | 39 simbol | OHLCV 1h (`*.klines_1h.parquet`) | Jul 2024 – Agu 2026 |
| `metrics/` | 42 file | Open Interest, long/short ratio (`*.metrics_1h.parquet`) | Jul 2024 – Agu 2026 |
| `funding/` | 39 file | funding_rate, mark_price (`*.funding_1h.parquet`) | Jul 2024 – Agu 2026 |

**Total:** ~211 MB

## Simbol (39)
AAVEUSDT, ADAUSDT, APTUSDT, ... WIFUSDT, XRPUSDT (39 altcoin perpetual futures)

## Catatan

- Dataset ini FROZEN untuk program riset alpha (STUDY-001..015).
- Semua kesimpulan program berlaku untuk dataset ini saja (scoped).
- Jangan menambah/merubah data untuk studi baru tanpa eksplisit
  menandai sebagai dataset berbeda.
- Reopening riset membutuhkan data material baru (2027+) atau
  microstructure yang lebih kaya (tick/order-flow) — lihat
  `docs/RESEARCH_EXECUTIVE_SUMMARY.md`.

## Interpreter
- Riset real-data: `/usr/bin/python3.11` (numpy/pandas/pyarrow)
- Default `python3` TANPA numpy — jangan dipakai untuk riset