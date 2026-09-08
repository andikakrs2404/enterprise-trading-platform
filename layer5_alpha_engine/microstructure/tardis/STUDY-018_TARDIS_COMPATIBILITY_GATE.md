# STUDY-018 — TARDIS COMPATIBILITY GATE (preregistered)

**Status:** ACTIVE (verifier built, sample downloading)
**Tujuan:** Menjawab deterministik: *"Apakah data Tardis dapat masuk ke pipeline
kita (replay → feature → cost → OOS) tanpa merusak reproducibility?"*
**Bukan:** alpha discovery. Verifier TIDAK mencari signal.

---

## Prinsip

Jangan bayar Tardis sebelum kompatibilitas terbukti. Ambil sample GRATIS
(hari pertama bulan, tanpa API key), jalankan gate, baru putuskan.

## Gate Checklist

| # | Check | Kriteria PASS |
|---|-------|---------------|
| 1 | Schema audit | Semua field inti ada (timestamp, localTimestamp, id, price, amount, side / is_snapshot) |
| 2 | Timestamp integrity | Sorted (atau OOO rate minimal), duplicate rate rendah, span wajar |
| 3 | Latency fields | localTimestamp - timestamp terukur (mean/median/p95/p99), neg% wajar |
| 4 | Trade normalization | Tardis trade → CanonicalEvent (ts, price, qty, side) → bisa masuk replay_engine |
| 5 | L2 reconstruction | snapshot + incremental → book valid: best bid/ask, spread positif, depth |
| 6 | Replay determinism | 2× replay identik (sorted keys sama) |
| 7 | Data quality | coverage, duplicate, OOO, gap |

## Acceptance Criteria

```
TARDIS_COMPATIBILITY = PASS (hanya jika semua fundamental PASS)
  Schema:              PASS
  Timestamp integrity: PASS
  Trade normalization: PASS
  L2 reconstruction:   PASS
  Replay integration:  PASS
  Replay determinism:  PASS
  Latency fields:      PASS
  Data quality:        PASS
PASS → layak evaluasi subscription (masih perlu full audit data sebelum beli)
NO-GO → jangan beli subscription; cari alternatif (Binance L2, collector lanjutan)
```

## Non-Goals (larangan)

- ❌ Tidak mencari alpha dalam sample
- ❌ Tidak mengevaluasi profitability signal
- ❌ Tidak mengubah pipeline demi data
- ❌ Tidak membayar subscription sebelum PASS

## File

- `tardis_sample_fetcher.py` — download sample gratis
- `tardis_compat_gate.py` — verifier gate
- Output: `STUDY-018_TARDIS_COMPAT.json`

## Note (koreksi kalimat laporan)

> "Tardis adalah opsi **paling praktis yang saat ini teridentifikasi** untuk
> memperoleh historical granular L2 yang siap diresearch; Binance juga memiliki
> historical L2 mechanisms dengan coverage/access constraints."

Bukan "satu-satunya cara" — research log harus tetap falsifiable.