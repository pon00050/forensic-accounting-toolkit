# XB-001: Split-Adjusted Prices Needed in price_volume.parquet

**Status**: RESOLVED (2026-03-15, commit `9b99bfb`)
**Discovered**: 2026-03-15 (kr-derivatives Run 1)
**Resolved**: 2026-03-15 — split-adjusted prices implemented in `extract_price_volume.py`
**Source**: `../kr-derivatives/reports/first_run_lessons.md`
**Fix location**: `../kr-forensic-finance/02_Pipeline/extract_price_volume.py`
**Detailed plan**: `../kr-derivatives/reports/second_run_prep.md` (Change 1)

---

## Problem

`price_volume.parquet` contains unadjusted prices. Stock splits are not reflected, causing false signals in kr-derivatives:

- Ticker 224060 shows moneyness 334x with single-day price drops of -78% and -89% (stock split artifacts)
- 254 rows with moneyness >10x are almost certainly contaminated
- Overall flag rate is 49.3% (should be <35% after fix)

## Impact

- **kr-derivatives Run 2 is blocked** until this is fixed
- Clean forensic signal (moneyness 1.0–2.0, ~657 cases) is unaffected and defensible today
- Contaminated tail (>5x, 527 rows) makes aggregate statistics unreliable

## Recommended Fix

Use pykrx `stock.get_market_ohlcv_by_date` with `adjusted=True` flag in `extract_price_volume.py`.

## Verification

After fix, moneyness >10x count should drop from 254 to <20.
