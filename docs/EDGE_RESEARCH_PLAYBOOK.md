# EDGE_RESEARCH_PLAYBOOK — Enterprise Multi-Edge Research Framework

**Version:** 1.0
**Date:** 2026-09-01
**Owner:** Research Desk (andika)
**Status:** ACTIVE

> **Mandat:** Hermes bukan "pencari strategi". Hermes adalah **research engine yang
> menguji keluarga mekanisme secara sistematis**. Setiap hipotesis harus melewati
> pipeline standar, di-pre-register, dan divalidasi anti-snooping.

---

## 1. Prinsip Inti

### Jangan membaca indikator secara standalone
OI naik ≠ bullish. Funding ekstrem ≠ otomatis top/bottom.
Selalu baca secara **simultan**: Price + OI + Funding + Volume.

### Jangan optimasi entry dulu
Setiap edge family dimulai dengan **Phase A — Phenomenon Discovery**,
bukan langsung "Strategy v1". Ukur forward return dulu, baru pre-register.

### Multi-testing correction wajib
Setiap eksplorasi bucket/quantile harus diverifikasi FDR/Bonferroni/Holm.
Sweet spot yang ditemukan setelah melihat data = data-snooping.

### 4 baseline minimum untuk perbandingan
Setiap claim edge butuh perbandingan dengan baseline: unconditional,
random timestamps, same-volatility, matched conditions.

---

## 2. Data Contract (Layer 1 — Market Data)

**Referensi praktis utama:** CCXT unified API.

### Data contract standar per symbol:
```
timestamp
symbol
open / high / low / close / volume   (OHLCV)
open_interest                            (fetchOpenInterestHistory)
funding_rate                             (fetchFundingRateHistory)
mark_price
index_price
```

Dalam pipeline ini, data contract tersedia dari `Bot-Multi-Edge-metrics`:
- `klines_1h.parquet`  → OHLCV
- `metrics_1h.parquet` → OI, long/short, taker vol
- `funding_1h.parquet` → funding_rate, mark_price

### Transformasi data (Layer 2 — Feature):
| Feature | Definisi | Sumber |
|---------|----------|--------|
| `oi_change_pct` | ΔOI/OI (%) | metrics |
| `funding_rate` | raw funding | funding |
| `funding_percentile` | percentile dalam symbol | funding (hitung) |
| `funding_zscore` | (x-μ)/σ dalam symbol | funding (hitung) |
| `volume_zscore` | (vol-μ)/σ rolling | klines (hitung) |
| `price_return` | forward return horizon | klines (hitung) |
| `adx` | ADX(14) | klines (hitung) |
| `atr_ratio` | ATR(14)/ATR(100) | klines (hitung) |
| `bb_width` | Bollinger width | klines (hitung) |

---

## 3. Pipeline Standar Research (semua edge family)

```
RAW DATA
   ↓
DATA CONTRACT (normalize, align timestamp)
   ↓
FEATURE ENGINEERING (atomic features, no look-ahead)
   ↓
EVENT DEFINITION (setup & trigger, DIKUNCI)
   ↓
FORWARD RETURN (1/3/6/12/24 bar, gross)
   ↓
MECHANISM TEST (Phase A: phenomenon discovery)
   ↓
PRE-REGISTERED HYPOTHESIS (Phase B: freeze definisi)
   ↓
TRAIN  (60%)
   ↓
VALIDATION (20%)
   ↓
TEST (20%)
   ↓
MTC (FDR/Bonferroni/Holm)
   ↓
COST (8bps round-trip)
   ↓
ROBUSTNESS (symbol, regime, per-window stability)
   ↓
VERDICT (INCONCLUSIVE / HYPOTHESIS_SUPPORTED / ROBUST_CANDIDATE / PRODUCTION_CANDIDATE)
```

---

## 4. Edge Family Taxonomy

### A. Momentum / Trend
**Mekanisme:** harga bergerak → berlanjut
**Feature:** return, EMA slope, ADX, ATR, volume, OI delta
**Contoh:** breakout, trend continuation, pullback, momentum acceleration, volatility expansion
**Status:** STUDY-001 diluar konteks (COMPRESSION INCONCLUSIVE). Trend pullback = hipotesis baru (bukan utak-atik Edge 1).

### B. Mean Reversion
**Mekanisme:** harga menyimpang dari equilibrium → kembali
**Feature:** z-score, distance from VWAP, distance from EMA, Bollinger deviation, RSI
**Catatan:** Jangan RSI<30→LONG langsung. Definisikan deviation event, ukur forward return.
**Status:** Kandidat counter-hypothesis terhadap momentum yang gagal.

### C. Funding Dislocation
**Mekanisme:** posisi crowded di satu arah → harga mean-revert
**Feature:** funding percentile, funding z-score, ΔFunding
**Hypothesis contoh:**
- extreme positive funding + crowded long → return negatif/mean-revert
- extreme negative funding + crowded short → return positif

**Normalisasi WAJIB:** jangan `funding > 0.05%` mentah. Gunakan **percentile/z-score dalam symbol** karena distribusi funding BTC ≠ altcoin.

### D. OI Dislocation
**Mekanisme:** perubahan OI + price → continuation/liquidation/exhaustion
**Feature:** `oi_return = ΔOI/OI`, dikombinasikan dengan price return:
```
price ↑ + OI ↑  (long building  → continuation?)
price ↑ + OI ↓  (short covering → ?
price ↓ + OI ↑  (short building → ?
price ↓ + OI ↓  (long liquidation→ ?
```
**Ukur dulu:** E[R(t+1)], E[R(t+3)], E[R(t+6)], E[R(t+12)], E[R(t+24)]
**Jangan langsung trading** — tentukan mekanismenya dulu.

### E. Funding + OI State Space (palings menarik)
Daripada Funding strategy dan OI strategy terpisah, bangun **state space**:
```
            OI ↓           OI ↑
Funding + ┌────────────┬────────────┐
Funding - └────────────┴────────────┘
```
Plus dimensi price return → positioning regime, bukan indikator tunggal.

### F. Cross-sectional Relative Strength
**Mekanisme:** relatif strength antar symbol
**Keunggulan:** tidak bergantung pada prediksi absolute market direction.

### G. Liquidation Cascade
**Mekanisme:** cascade liquidation → momentum/vanish
**Catatan:** butuh definisi event & data liquidation yang memadai, agar tidak jadi proxy noise.

---

## 5. Funding/OI Study — Phase A Protocol (Next up)

**Jangan mulai dari threshold arbitrary** (`funding > 0.05%`, `OI > +1%`).
Mulai dari **distribusi**:

Per symbol hitung:
1. Funding percentile
2. Funding z-score
3. ΔFunding
4. OI percentile
5. ΔOI
6. Price return
7. Volume z-score

Kemudian buat **matrix Funding × OI** dan **forward-return surface E[R|state]**.
Baru setelah fenomenanya terlihat, **pre-register hypothesis**.

---

## 6. Failure Modes & Leakage Checklist

- [ ] **Look-ahead:** feature dihitung dari bar yang sama dgn trigger? (harus lag)
- [ ] **OI/funding standalone:** sekali baca tidak cukup, kombinasi wajib
- [ ] **Sweet-spot post-hoc:** bucket dipilih setelah melihat hasil? → MTC wajib
- [ ] **Universe bias:** hanya 5 simbol? → perluas utk replication
- [ ] **Temporal split salah:** split by index gabungan, bukan per-symbol → WAJIB per-symbol
- [ ] **Biaya diabaikan:** gross positif tapi net negatif setelah 8bps → lapor kedua
- [ ] **Per-symbol kecil:** n<10 per bucket → ci lebar, jangan simpulkan
- [ ] **Alpha palsu:** MFE besar + MAE besar ≠ tradable edge (bisa volatility expansion)

---

## 7. Verdict Definitions (4-level)

| Status | Definisi |
|--------|----------|
| **INCONCLUSIVE** | Belum cukup bukti. Bukan reject, bukan support. Freeze. |
| **HYPOTHESIS_SUPPORTED** | Fenomena ada (Phase A), tapi belum robustness penuh. |
| **ROBUST_CANDIDATE** | Survive OOS + MTC + symbol/regime stability + net PF>1.2. |
| **PRODUCTION_CANDIDATE** | Implementable execution, capacity assessed, monitoring plan. |

---

## 8. Referensi

- CCXT unified API: `fetchFundingRateHistory`, `fetchOpenInterestHistory`
- Market data & funding docs (exchange-specific: Binance USDT-M futures)
- Literatur 2026: momentum & reversal coexistence, horizon pendek — flow vs residual component
  → relevan dgn temuan STUDY-001 (initial continuation → exhaustion → reversal)
