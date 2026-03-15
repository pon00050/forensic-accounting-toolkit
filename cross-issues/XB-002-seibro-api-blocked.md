# XB-002: SEIBRO API Returns resultCode=99

**Status**: ACTIVE (non-critical for current phase)
**Discovered**: kr-forensic-finance (day 4+ of testing)
**Fix location**: External — requires KSD approval
**Contact**: KSD 051-519-1420 (별도이용허락 required)

---

## Problem

SEIBRO API for CB repricing data returns `resultCode=99`. API key is registered but needs separate usage authorization from KSD (Korea Securities Depository).

## Impact

- Blocks CB repricing Flags 1-2 in kr-forensic-finance Phase 2 CB/BW analysis
- Blocks `repricing_coercion_score` in kr-derivatives (Phase 2 feature, currently stubbed)
- DART cannot replace SEIBRO for these specific signals

## Action

Call KSD at 051-519-1420 to request 별도이용허락 (separate usage authorization).
