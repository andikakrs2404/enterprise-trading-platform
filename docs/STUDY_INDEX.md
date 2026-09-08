# STUDY_INDEX.md — Lokasi Seluruh Dokumen Studi

**Gunakan ini untuk menemukan file. Detail studi TIDAK di memory agent —
baca dari file ini.**

Lokasi dasar: `layer5_alpha_engine/research/` (scripts + JSON)
Dokumentasi kebijakan: `docs/`

---

## STATUS RINGKAS (FINAL — program CLOSED)

| Study | Status | Dokumen kunci |
|-------|--------|---------------|
| STUDY-001 | FROZEN (INCONCLUSIVE) | `STUDY-001_archive.md` |
| STUDY-001-MECH | FROZEN (EXPLORATORY) | `STUDY-001_mechanism.json` |
| STUDY-002 | OBSERVED PHENOMENON (archived) | `STUDY-002_FUNDING_OI_PHASE_A.json` |
| STUDY-003 | REJECTED | `STUDY-003_FUNDING_OI_PHASE_A.json` |
| STUDY-004 | REJECTED (Phase B pass, OOS fail) | `STUDY-004_PREREGISTRATION.md`, `STUDY-004_PHASE_B.json` |
| STUDY-005 | REJECTED (regime inversion) | `STUDY-005_OOS.json`, `docs/FAILURE_CASE_001.md` |
| STUDY-006 | **VALIDATED FEATURE** (Price RS) | `STUDY-006_CROSS_SECTIONAL_RS.json`, `STUDY-006_PHASE_B.json`, `STUDY-006_FREEZE.md` |
| STUDY-007 | NOT CONFIRMED + POSTMORTEM | `STUDY-007_PORTFOLIO_INTEGRATION.json`, `STUDY-007_REANALYSIS.json`, `STUDY-007_POSTMORTEM.md` |
| STUDY-008 | VOL rejected, **OI_share_7d EMERGENT** | `STUDY-008_PARTICIPATION_PHASE_A.json`, `STUDY-008_PHASE_B.json`, `STUDY-008C_*.json`, `STUDY-008_FREEZE.md` |
| STUDY-009 | REJECTED (proxy + arah berubah) | `STUDY-009_VOLREGIME.json`, `run_study009_reanalysis.py` |
| STUDY-010 | REJECTED (OI_growth obs) | `STUDY-010_CS_FLOW.json`, `STUDY-010_FREEZE.md` |
| STUDY-011 | REJECTED | `STUDY-011_PREREGISTRATION.md`, `STUDY-011_MARKET_STRUCTURE.json` |
| STUDY-011B | REJECTED (illusion) | `STUDY-011B_CONTEXT_ENGINE.json`, `STUDY-011B_FAILURE.md` |
| STUDY-012 | REJECTED (portfolio layer falsified) | `STUDY-012_FREEZE.md`, `STUDY-012_SELECTION.json`, `STUDY-012_WEIGHTING.json`, `STUDY-012_SIZING_2025.json` |
| STUDY-013 | INCONCLUSIVE (RS regime-dependent obs) | `STUDY-013_REGIME.json` |
| STUDY-013B | ROBUSTNESS FAILURE | `STUDY-013B_ROBUSTNESS.json` |
| STUDY-014 | SUPPORTING EVIDENCE (distribusi berbeda) | `STUDY-014_DISTRIBUTION.json` |
| STUDY-015 | REJECTED (hard stop) | `STUDY-015_PREREGISTRATION.md`, `STUDY-015_MECHANISM.json` |

## PROGRAM BARU — MICROSTRUCTURE SCALPING (016-022)

| Study | Topik | Status |
|-------|-------|--------|
| STUDY-016 | Data & Protocol | **PREREGISTERED** — `STUDY-016_PROTOCOL.md` |
| STUDY-017 | Trade Flow Phenomena | PLANNED |
| STUDY-018 | Order Book Phenomena | PLANNED |
| STUDY-019 | Event Interaction | PLANNED |
| STUDY-020 | Execution Reality | PLANNED |
| STUDY-021 | Strategy Construction | PLANNED |
| STUDY-022 | Replay/Backtest | PLANNED |

## RUN SCRIPTS (jika perlu re-run)
- STUDY-006: `run_study006_cross_sectional.py`, `run_study006_phaseB.py`
- STUDY-007: `run_study007_portfolio_integration.py`, `run_study007_reanalysis.py`
- STUDY-008: `run_study008_participation.py`, `run_study008_phaseB.py`, `run_study008C_*.py`
- STUDY-009: `run_study009_volregime.py`, `run_study009_reanalysis.py`
- STUDY-010: `run_study010_flow.py`
- STUDY-011: `run_study011_market_structure.py`, `run_study011B_context.py`
- STUDY-012: `run_study012_selection.py`, `run_study012_weighting.py`, `run_study012_sizing.py`
- STUDY-013/013B: `run_study013_regime.py`, `run_study013B_robustness.py`
- STUDY-014: `run_study014_distribution.py`
- STUDY-015: `run_study015_mechanism.py`

## DATA (frozen — snapshot riset 2024-2026)
- `/home/rtk/Bot-Multi-Edge-metrics/data/klines/*.parquet` (39 symbols 1h)
- `/home/rtk/Bot-Multi-Edge-metrics/data/metrics/*.parquet` (OI, ratio)
- `/home/rtk/Bot-Multi-Edge-metrics/data/funding/*.parquet`
- Total: ~211MB, Juli 2024 – Agustus 2026

## POLICIES & KESIMPULAN
- `docs/RESEARCH_EXECUTIVE_SUMMARY.md` — kesimpulan eksekutif (scoped, no deployable alpha)
- `docs/QUANT_RESEARCH_PLAYBOOK.md` — **methodology reusable (9 bagian + hard-stop)** ⭐
- `docs/RESEARCH_STATE.md` — status terbaru saja (PROGRAM CLOSED)
- `docs/CORE_MEMORY.md` — aturan permanen (guardrails)
- `docs/EDGE_RESEARCH_MAP.md` — roadmap + katalog family
- `docs/EDGE_RESEARCH_PLAYBOOK.md` — framework 14-step (legacy)
- `docs/FAILURE_CASE_001.md` — failure case Funding/OI

## REOPENING CRITERIA (jangan dibuka tanpa ini)
1. Data material baru (mis. 2027+)
2. Microstructure lebih kaya (tick/order-flow/liquidation)
3. Hipotesis kausal baru yang genuine (preregistered, failure criteria di muka)