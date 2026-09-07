# QUANT_RESEARCH_PLAYBOOK — Reusable Research Methodology

**Owner:** Research Desk | **Source:** 15 studi (STUDY-001..015), 2024-2026 crypto perps
**Tujuan:** Knowledge yang reusable untuk program riset alpha berikutnya.
Ini BUKAN history — ini protokol.

---

## 0. Prinsip Dasar

> **Discovery ≠ validation. Statistical significance ≠ economic viability.**
> "Interesting" bukan "validated".

Setiap hipotesis harus punya: H0/H1 eksplisit, definisi dikunci ex-ante,
failure criteria yang bisa menggagalkannya, dan biaya transaksi realistis.

---

## 1. Discovery

- Discovery boleh full sample, TAPI hasilnya dilabel **"Observed Phenomenon
  (Unregistered)"** — bukan alpha, bukan hypothesis.
- **Jangan memilih threshold/horizon berdasarkan TEST.** Definisi dikunci
  sebelum eksekusi. Threshold optimization setelah melihat return = data mining.
- State space deskriptif (quantile/percentile), bukan threshold arbitrary.
- Jangan perketat regime di Phase A untuk "mencari performa" — itu
  memverifikasi fenomena, bukan mencari performa.

## 2. Validation

- **Temporal split TRAIN/VAL/TEST** (60/20/20, per timeline, konsisten antar simbol).
- **Non-overlap WAJIB untuk forward-return temporal diagnostics.**
  Overlapping forward returns mendistorsi temporal evidence — "reversal"
  antar era bisa jadi artifact overlap. (Pelajaran STUDY-008.)
- HAC-aware methodology ketika non-overlap tidak praktis.
- **Cross-symbol breadth**: % simbol yang mendukung, bukan hanya pooled mean.
- **Q1/Q5 decomposition**: lihat Q1 dan Q5 terpisah, bukan hanya spread
  Q5-Q1. Spread bisa artefak mixing periode arah berbeda.
- **Sign stability > magnitude.** Magnitude yang hanya muncul di satu epoch
  bukan bukti. Tanda yang konsisten lintas TRAIN/VAL/TEST adalah bukti awal.
- **Double-sort vs Price RS** untuk incremental information: jika feature
  hilang saat dikontrol Price RS → proxy momentum → redundant.
- Per-symbol consistency + leave-one-symbol-out untuk breadth coverage.
- Dispersion layer (std/IQR/MAD per state) wajib dilaporkan.

## 3. Economic Gate

- **Gross return tidak cukup.** Selalu evaluasi 8/12/16 bps (atau cost model
  yang relevan). Net-after-cost adalah GATE, bukan appendix.
- **Turnover harus dihitung** (Σ|Δw| per rebalance) dan dikali fee.
- Edge tipis 2-20 bps hampir selalu mati oleh fee 8-16 bps → target adalah
  fenomena dengan gross edge >> transaction cost.
- Jika net@12bps negatif di TRAIN/VAL → reject, apapun TEST-nya.

## 4. Multiple-Testing Protection

- Setelah banyak eksperimen, sesuatu pasti terlihat bagus secara kebetulan.
- **Conditional discoveries WAJIB divalidasi** (bukan langsung dipercaya).
- **Context engine (regime/conditional) WAJIB diuji pada feature independen.**
  Jika hanya memperkuat feature yang memunculkannya → kemungkinan besar
  multiple-testing artifact. (Pelajaran STUDY-011B.)
- Jangan mengubah observasi menjadi hypothesis tanpa preregistration.
- Multiple-testing correction (FDR/Bonferroni) ketika banyak hipotesis.

## 5. Portfolio Research

- **Selection, weighting, sizing adalah hipotesis TERPISAH.** Jangan campur.
- Portfolio construction **TIDAK otomatis menyelamatkan weak signals.**
  (STUDY-012: selection -11bps, weighting +7-8bps, sizing 0 — semua gagal gate.)
- **Strong baseline wajib** (mis. Price RS sederhana), bukan random portfolio.
- Decomposition: selection effect + weighting effect + interaction.
- Jika return-dari-subset flip sign antar konstruksi → sinyal di noise floor.
- Rebalance align dengan efek horizon (jangan rebalance tiap bar untuk
  efek R24-R48); turnover eksplisit.

## 6. Regime Research

- **Regime harus didefinisikan ex-ante** dari data timestamp-by-timestamp,
  bukan diberi nama setelah melihat return ("2024=bull" = look-ahead narrative).
- Lagged state (bukan contemporaneous): state(t) → behavior(t+k).
- **Rolling/real-time implementability wajib** (rolling percentile, bukan
  global median). Global median = properti seluruh sampel, tidak tersedia
  di deployment.
- **Historical regime explanation ≠ predictive regime model.** Distribusi
  berbeda antar era (STUDY-014) tidak membuktikan prediktabilitas ex-ante
  (STUDY-015 gagal).
- Preregistered gate: semua split positif + net@12 positive + no single-era
  + no threshold-dependence + non-overlap.

## 7. Hard-Stop Discipline ⭐

> **When a preregistered hard gate fails, stop the branch instead of
> searching for a rescue specification.**

- Failure criteria ditulis SEBELUM eksekusi dan dipatuhi SETELAH hasil.
- "Gagal" bukan alasan untuk tweak threshold/horizon/definisi → itu spiral
  optimization.
- Menutup branch dengan bersih lebih bernilai daripada menyelamatkan
  hipotesis dengan rescue spec.
- Kegagalan beruntun dengan framework ketat = framework bekerja (membunuh
  hipotesis cepat), bukan framework jelek.

## 8. Taxonomy & Labeling

- PHENOMENON → VALIDATED FEATURE → PORTFOLIO CONTRIBUTION → EDGE.
- "Jangan menyebut edge dulu."
- Phase A ≠ Phase B ≠ OOS.
- Label "Unconfirmed" bukan "Rejected" jika bukti tidak cukup (bukan
  kontra-bukti).
- Negative findings WAJIB dilaporkan.

## 9. Checklist Final (sebelum klaim apa pun)

- [ ] H0/H1 eksplisit + failure criteria ex-ante
- [ ] Definisi dikunci sebelum eksekusi
- [ ] Non-overlap/HAC untuk temporal
- [ ] TRAIN/VAL/TEST konsisten tanda
- [ ] Breadth (per-symbol) memadai
- [ ] Q1/Q5 decomposition (bukan hanya spread)
- [ ] Double-sort vs Price RS (incremental info)
- [ ] Net after 8/12/16 bps positif (bukan gross)
- [ ] Turnover dihitung
- [ ] Context/conditional: cross-check feature independen
- [ ] Regime: ex-ante, lagged, rolling-implementable
- [ ] Multiple-testing correction jika relevan
- [ ] Tidak ada threshold/horizon yang dipilih dari TEST

---

*Playbook ini adalah hasil langsung dari 15 studi (2024-2026). Setiap aturan
berasal dari satu atau lebih falsifikasi nyata. Lihat STUDY_INDEX.md untuk
detail per studi.*