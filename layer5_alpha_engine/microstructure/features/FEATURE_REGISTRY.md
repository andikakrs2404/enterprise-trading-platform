# FEATURE REGISTRY — Microstructure Program (STUDY-016+)
# =======================================================
# Pelajaran STUDY-001..015: jangan biarkan feature liar.
# Setiap feature TERCATAT di registry ini sebelum diuji.
# Feature yang tidak ada di registry TIDAK BOLEH dilaporkan.
#
# Kolom: id | name | formula | parameters | first_study | status
# Status: DRAFT (defined, belum diuji) | TESTED | REJECTED | SUPPORTED | ACTIVE

## STUDY-017 — Trade Flow Phenomena (4 family, dikunci)

### Family A — Signed Volume
TF001 | signed_volume_5s   | sum(qty*(1-m)) - sum(qty*m) over 5s   | window=5s   | STUDY-017 | DRAFT
TF002 | signed_volume_15s  | same, window 15s                      | window=15s  | STUDY-017 | DRAFT
TF003 | signed_volume_30s  | same, window 30s                      | window=30s  | STUDY-017 | DRAFT

### Family B — Trade Imbalance
TF010 | buy_ratio_60s      | buy_vol / (buy_vol + sell_vol) over 60s | window=60s | STUDY-017 | DRAFT
TF011 | buy_ratio_5s       | same, window 5s                        | window=5s   | STUDY-017 | DRAFT

### Family C — Trade Intensity
TF020 | trades_per_sec_30s | n_trades / 30 over 30s                | window=30s  | STUDY-017 | DRAFT
TF021 | volume_per_sec_30s | qty.sum / 30 over 30s                 | window=30s  | STUDY-017 | DRAFT

### Family D — Burst Events (binary)
TF030 | burst_volume_p95_60s  | volume_60s > rolling p95(volume_60s) | window=60s, p95 | STUDY-017 | DRAFT
TF031 | burst_count_p95_60s   | n_trades_60s > rolling p95          | window=60s, p95 | STUDY-017 | DRAFT

## Reserved: STUDY-018 (order book) — TF1xx; STUDY-019 (event interaction) — TF2xx

## Aturan
# 1. Feature ID sekali dipakai, tidak pernah reuse untuk definisi berbeda.
# 2. Parameter (window, threshold) dikunci di DRAFT — tidak boleh diubah setelah melihat hasil.
# 3. Threshold dari TRAIN only; VAL/TEST hanya evaluasi.
# 4. Semua feature harus punya formula eksplisit (bukan "ML finds it").