# EDGE_RESEARCH_MAP — Katalog Edge Family & Status

**Version:** 1.0 | **Date:** 2026-09-01 | **Owner:** Research Desk

Setiap edge family dievaluasi terhadap pipeline standar (PHASE A phenomenon → PHASE B pre-registered → validation). Hanya family yang lulus Phase A yang boleh masuk Phase B.

---

## Katalog Family

### ✅ 1. Compression Breakout / Momentum (STUDY-001)
- **Status:** INCONCLUSIVE (Track A) / FAILED OOS (Track B)
- **Arsip:** `research/STUDY-001_archive.md`
- **Temuan mekanisme:** Impulse singkat (1-8 bar) → flow exhaustion → reversal (12-24 bar). MFE/MAE simetris. Asymmetry tidak exploitable setelah 8bps.
- **Keputusan:** FROZEN. Tidak boleh dioptimasi ulang tanpa data baru + study ID baru.
- **Lesson:** Momentum pada horizon pendek ada, tapi tidak bertahan net biaya. Konsisten literatur flow/exhaustion.

### 🔄 2. Trend Pullback
- **Status:** Hipotesis baru (BUKAN utak-atik Edge 1 lama)
- **Pipeline:** PHASE A phenomenon discovery belum dijalankan
- **Catatan:** Versi awal pernah gagal → diperlakukan sebagai hipotesis baru terpisah
- **Feature:** return, EMA slope, ADX, volume

### ⬜ 3. Mean Reversion
- **Status:** Kandidat (counter-hypothesis terhadap momentum)
- **Mekanisme:** deviation dari equilibrium → revert
- **Feature:** z-score, VWAP distance, EMA distance, BB deviation
- **Pitfall:** Jangan RSI<30→LONG langsung. Definisikan deviation event → ukur forward return.

### ⬜ 4. Funding Dislocation (NEXT UP)
- **Status:** **Fase A — phenomenon discovery (belum dimulai eksekusi)**
- **Mekanisme:** crowded positioning → mean-revert
- **Normalisasi:** funding percentile/z-score per symbol (bukan raw threshold)
- **Data tersedia:** funding_1h.parquet ✅

### ⬜ 5. OI Dislocation
- **Status:** Kandidat berikutnya
- **Mekanisme:** ΔOI + price → continuation / liquidation / exhaustion
- **Feature:** `oi_return = ΔOI/OI`, kombinasi dengan price return
- **Data tersedia:** metrics OI ✅

### ⬜ 6. Funding × OI State Space
- **Status:** Paling menarik (Positioning regime)
- **Mekanisme:** kombinasi funding & OI state → forward return surface
- **Matrix:** OI↑/OI↓ × Funding+/Funding− × Price↑/Price↓

### ⬜ 7. Cross-sectional Relative Strength
- **Status:** Kandidat
- **Mekanisme:** relatif strength antar symbol
- **Keunggulan:** tidak butuh prediksi absolute direction

### ⬜ 8. Liquidation Cascade
- **Status:** Kandidat (butuh data liquidation memadai)
- **Mekanisme:** cascade → momentum/vanish
- **Pitfall:** definisi event harus jelas, jangan jadi proxy noise

---

## Pipeline Progress Tracking

| Family | RAW | CONTRACT | FEATURE | EVENT | FWD | MECH | PRE-REG | TRAIN | VAL | TEST | MTC | COST | ROBUST | VERDICT |
|--------|-----|----------|---------|-------|-----|------|---------|-------|-----|------|-----|------|--------|---------|
| Compression (S001) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | FROZEN |
| Trend Pullback | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Mean Reversion | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Funding Dislocation | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| OI Dislocation | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Funding×OI State | ✅ | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
