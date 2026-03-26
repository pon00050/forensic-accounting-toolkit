# XB-002: SEIBRO API Returns resultCode=99

**Status**: DEFERRED — revisit end of April 2026
**Discovered**: krff-shell (day 4+ of testing)
**Fix location**: External — 공공데이터포털 is revising the dataset/API
**Contact**: 공공데이터 문의 1566-0025 / KSD 051-519-1420

---

## Problem

SEIBRO API for CB repricing data returns `resultCode=99`. API key is registered but the providing agency (KSD) is not cooperating with data.go.kr to activate access for dataset 15001145.

## Timeline

- **2026-03-05**: API key registered on data.go.kr
- **2026-03-09**: Still `resultCode=99` (day 4 business). Documented as KI-012.
- **2026-03-16**: Test calls confirm both StockSvc endpoints still return `resultCode=99`. FSC bond API (same key) works fine — confirms key is valid, problem is dataset-specific.
- **2026-03-16**: Called 공공데이터 문의 (1566-0025). They confirmed the 기관 (KSD) is not cooperating. A revised dataset/API is planned for launch **by end of April 2026 at the latest**.

## Impact

- Blocks CB repricing Flags 1-2 in krff-shell Phase 2 CB/BW analysis
- Blocks `repricing_coercion_score` in kr-derivatives (Phase 2 feature, currently stubbed)
- Blocks 2 statistical tests: `survival_repricing.py`, `permutation_repricing_peak.py`
- DART cannot replace SEIBRO for these specific signals

## Action

**No action until end of April 2026.** The revised API/dataset should launch by then. When it does:

1. Check data.go.kr for the new/revised dataset (may have a new dataset ID replacing 15001145)
2. Update `extract_seibro_repricing.py` endpoints if the API schema changed
3. Run the activation runbook in KI-012 (KNOWN_ISSUES.md)
4. Re-run `repricing_coercion_score` implementation in kr-derivatives

Do NOT spend time calling KSD (051-519-1420) — the issue is on their end and 공공데이터포털 is handling it.
