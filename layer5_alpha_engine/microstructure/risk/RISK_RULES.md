# RISK RULES — Microstructure Scalping (pre-live, dikunci)
# ==========================================================
# Berlaku UNTUK SEMUA fase: paper trading, small live, scale.
# Ini bukan saran — ini constraint yang TIDAK BOLEH dilanggar.

## 1. Simbol (dikunci)
- BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT — hanya 4, sangat liquid
- Tidak ada simbol lain sampai 4 ini terbukti (atau program ditutup)

## 2. Exposure
- Maksimal 1 posisi per simbol pada satu waktu
- Maksimal 2 posisi simultan di seluruh portofolio (4 simbol)
- Tidak ada averaging down. Tidak ada martingale. Tidak ada grid.

## 3. Holding
- Maksimal holding time: 5 MENIT
- Jika tidak keluar dalam 5 menit → forced exit (kill switch)
- Alasan: edge microstructure (jika ada) adalah short-horizon; posisi >5m
  masuk ke domain yang sudah difalsifikasi (STUDY-001..015)

## 4. Stop Loss
- Hard stop: 2×ATR (dari timeframe yang relevan) atau 30 bps, mana lebih ketat
- Trailing stop setelah profit > 20 bps (lock in)
- Stop loss TIDAK BOLEH dihapus/dilonggarkan saat drawdown

## 5. Daily Loss Limit
- Maksimum daily loss: 1% dari equity
- Jika tercapai → STOP trading hari itu (kill switch)
- Tidak ada "balas dendam" (revenge trading)

## 6. Kill Switch
- Aktif SELALU (24/7)
- Trip conditions:
  a. Daily loss > 1%
  b. Posisi > 5 menit
  c. Latency > 500ms (network issue)
  d. Error API > 5 berturut-turut
  e. Equity drawdown > 3% dari peak (mingguan)
- Setelah trip: tutup semua posisi, halt trading, alert manual review

## 7. Leverage
- Maksimal 5× (awal), 2× (fase validasi)
- Tidak ada leverage dinamis/otomatis

## 8. Ukuran Posisi
- Risk per trade: maksimal 0.25% equity (dengan SL 30bps → ukuran terkendali)
- Volume maksimal per order: 5% dari depth level 1 (tidak menggerakkan market)

## 9. Anti-Manual-Override
- Semua rule di atas TIDAK BISA di-override manual dalam mode auto
- Satu-satunya override: STOP SEMUA (kill everything)

## 10. Governance
- Fraksi ini dikunci di preregistration; perubahan = studi baru + persetujuan eksplisit