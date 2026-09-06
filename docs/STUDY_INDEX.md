# STUDY_INDEX.md — Lokasi Seluruh Dokumen Studi

**Gunakan ini untuk menemukan file. Detail studi TIDAK di memory agent —
baca dari file ini.**

Lokasi dasar: `layer5_alpha_engine/research/` (scripts + JSON)
Dokumentasi kebijakan: `docs/`

---

## STATUS RINGKAS

| Study | Status | Dokumen kunci |
|-------|--------|---------------|
| STUDY-001 | FROZEN (INCONCLUSIVE) | `STUDY-001_archive.md` |
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
| STUDY-012 | **ACTIVE — PREREGISTERED** | `STUDY-012_PREREGISTRATION.md` |

## RUN SCRIPTS (jika perlu re-run)
- STUDY-006: `run_study006_cross_sectional.py`, `run_study006_phaseB.py`
- STUDY-007: `run_study007_portfolio_integration.py`, `run_study007_reanalysis.py`
- STUDY-008: `run_study008_participation.py`, `run_study008_phaseB.py`, `run_study008C_*.py`
- STUDY-009: `run_study009_volregime.py`, `run_study009_reanalysis.py`
- STUDY-010: `run_study010_flow.py`
- STUDY-011: `run_study011_market_structure.py`, `run_study011B_context.py`

## DATA
- `/home/rtk/Bot-Multi-Edge-metrics/data/klines/*.parquet` (39 symbols 1h)
- `/home/rtk/Bot-Multi-Edge-metrics/data/metrics/*.parquet` (OI, ratio)
- `/home/rtk/Bot-Multi-Edge-metrics/data/funding/*.parquet`

## POLICIES
- `docs/EDGE_RESEARCH_MAP.md` — roadmap + katalog family
- `docs/EDGE_RESEARCH_PLAYBOOK.md` — framework 14-step
- `docs/CORE_MEMORY.md` — aturan permanen (guardrails)
- `docs/RESEARCH_STATE.md` — status terbaru saja
- `docs/FAILURE_CASE_001.md` — failure case Funding/OI