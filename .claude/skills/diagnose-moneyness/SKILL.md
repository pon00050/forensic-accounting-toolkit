---
name: diagnose-moneyness
description: Diagnose extreme moneyness cases — checks pykrx adjusted/unadjusted prices, queries DART for CB filings and corporate actions, and produces a verdict (split artifact vs genuine ITM vs data error)
user-invocable: true
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob, Agent, WebSearch
---

Diagnose extreme moneyness outliers from an issuance dilution screen run. Automates the investigation loop: query DART for the original CB filing, check pykrx for adjusted vs unadjusted prices, search for corporate actions, and produce a verdict.

## Arguments

- No argument: Auto-detect from the most recent `issuance_dilution_scores.csv` in kr-derivatives
- `corp_code=XXXXXXXX`: Diagnose a single corp_code
- `ticker=XXXXXX`: Diagnose a single ticker
- `threshold=N`: Override the moneyness threshold (default: 10)

## Environment

All Python commands MUST use these wrappers to avoid Windows encoding issues:

```bash
# Always set encoding for Python output
cd /c/Users/pon00/Projects/krff-shell && PYTHONIOENCODING=utf-8 uv run python -c "..."

# Always read .env with explicit encoding
from pathlib import Path
api_key = None
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    if line.startswith('DART_API_KEY=') or line.startswith('OPENDART_API_KEY='):
        api_key = line.split('=', 1)[1].strip()
        break
```

**Never print Korean characters directly** — they cause `UnicodeEncodeError` on Windows cp1252. Use ASCII labels or strip Korean text before printing.

## Steps

### Step 1 — Identify extreme cases

If no specific corp_code/ticker given, load the scores CSV:

```python
import pandas as pd

scores = pd.read_csv('C:/Users/pon00/Projects/kr-derivatives/issuance_dilution_scores.csv')
extreme = scores[scores['moneyness'] > THRESHOLD]
print(f'Extreme rows: {len(extreme)}')
print(f'Unique corp_codes: {extreme["corp_code"].nunique()}')

# Show top 10 by moneyness
for _, row in extreme.nlargest(10, 'moneyness').iterrows():
    print(f'  corp_code={str(int(row["corp_code"])).zfill(8)} S={row["S"]:.0f} K={row["K"]:.0f} moneyness={row["moneyness"]:.1f}x')
```

### Step 2 — For each corp_code, query DART CB filings

```python
import os, requests
from pathlib import Path

api_key = None
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    if line.startswith('DART_API_KEY=') or line.startswith('OPENDART_API_KEY='):
        api_key = line.split('=', 1)[1].strip()
        break

# CB disclosures
r = requests.get('https://opendart.fss.or.kr/api/cvbdIsDecsn.json', params={
    'crtfc_key': api_key,
    'corp_code': CORP_CODE,
    'bgn_de': '20140101',
    'end_de': '20261231',
})
data = r.json()
for item in data.get('list', []):
    print(f'  cv_prc={item.get("cv_prc")} bd_fta={item.get("bd_fta")}')
```

### Step 3 — Query DART for corporate actions (consolidations, capital reductions)

```python
# General disclosure search — filter for corporate action keywords
r = requests.get('https://opendart.fss.or.kr/api/list.json', params={
    'crtfc_key': api_key,
    'corp_code': CORP_CODE,
    'bgn_de': '20140101',
    'end_de': '20261231',
    'page_count': '100',
})
data = r.json()
# Filter for corporate action disclosures
keywords = ['감자', '병합', '분할', '액면']  # reduction, consolidation, split, par value
for item in data.get('list', []):
    title = item.get('report_nm', '')
    if any(kw in title for kw in keywords):
        # Print without Korean to avoid encoding errors
        print(f'  rcept_no={item.get("rcept_no")} rcept_dt={item.get("rcept_dt")} type=CORPORATE_ACTION')
```

### Step 4 — Check pykrx adjusted vs unadjusted

```python
from pykrx import stock

# Map corp_code to ticker via the ticker map
import pandas as pd
tm = pd.read_parquet('C:/Users/pon00/Projects/kr-derivatives/data/input/corp_ticker_map.parquet')
tm['corp_code'] = tm['corp_code'].astype(str).str.zfill(8)
ticker_row = tm[tm['corp_code'] == CORP_CODE]
ticker = ticker_row['ticker'].iloc[0] if not ticker_row.empty else None

if ticker:
    # Fetch adjusted and unadjusted for the board_date
    adj = stock.get_market_ohlcv_by_date(DATE, DATE, ticker, adjusted=True)
    unadj = stock.get_market_ohlcv_by_date(DATE, DATE, ticker, adjusted=False)

    s_adj = int(adj.iloc[0, 3]) if not adj.empty else None
    s_unadj = int(unadj.iloc[0, 3]) if not unadj.empty else None

    print(f'  S_adjusted={s_adj} S_unadjusted={s_unadj}')
    if s_adj and s_unadj:
        ratio = s_adj / s_unadj
        print(f'  Adjustment ratio: {ratio:.1f}x')
        print(f'  True moneyness (unadj): {s_unadj / K:.2f}')
```

**Important:** pykrx 1.0.51 has broken `adjusted=False` (returns empty). Check the installed version first:
```python
import pykrx; print(pykrx.__version__)
```
If version < 1.2.0, warn that unadjusted prices are unavailable and the diagnosis is incomplete.

### Step 5 — Check for price discontinuities in the adjusted series

```python
pv = pd.read_parquet('C:/Users/pon00/Projects/kr-derivatives/data/input/price_volume.parquet')
t = pv[pv['ticker'] == ticker].sort_values('date').copy()
t['pct'] = t['close'].pct_change()
big_jumps = t[t['pct'].abs() > 0.5]
if len(big_jumps) > 0:
    print(f'  Price discontinuities (>50% single-day):')
    for _, row in big_jumps.iterrows():
        print(f'    {row["date"]}  close={int(row["close"])}  change={row["pct"]:+.1%}')
else:
    print(f'  No >50% discontinuities found in adjusted series')
```

### Step 6 — Produce verdict

For each investigated case, classify as one of:

| Verdict | Criteria |
|---------|----------|
| **SPLIT_ARTIFACT** | DART shows corporate action (감자/병합) AND adjustment ratio explains the moneyness |
| **LIKELY_SPLIT_ARTIFACT** | No DART corporate action found, but price discontinuities >50% exist AND moneyness is economically implausible (>20x) |
| **GENUINE_ITM** | Unadjusted price confirms moneyness >1.0, no corporate actions found |
| **DATA_ERROR** | DART cv_prc doesn't match parquet exercise_price, or other data inconsistency |
| **INCONCLUSIVE** | Unadjusted prices unavailable (pykrx broken), no DART corporate action data, cannot determine |

## Output Format

```
=== Moneyness Diagnosis ===

Investigated: X corp_codes (Y rows with moneyness > THRESHOLD)

Verdicts:
  SPLIT_ARTIFACT:        N cases — adjustment ratio confirmed via DART
  LIKELY_SPLIT_ARTIFACT: N cases — discontinuities present, economically implausible
  GENUINE_ITM:           N cases — confirmed in-the-money at issuance
  DATA_ERROR:            N cases — filing data mismatch
  INCONCLUSIVE:          N cases — insufficient data

Top cases:
  [corp_code] [ticker] moneyness=[X]x → [VERDICT] (ratio=[R]x, [evidence])
  ...

Recommendation:
  [Based on verdicts, state whether the denomination mismatch hypothesis holds
   and what the expected flag rate would be after correction]
```

## Rules

- **Read-only.** Do NOT fix code or data. This is a diagnostic tool.
- **Always use PYTHONIOENCODING=utf-8** for all Python invocations.
- **Never print raw Korean text** — extract only numeric/date fields from DART responses.
- **Run from krff-shell directory** (has pykrx and DART API key in .env).
- **Limit to 10 corp_codes per run** to avoid DART API rate limits. If more than 10, diagnose the top 10 by moneyness and extrapolate.
- **If pykrx `adjusted=False` returns empty**, note the version and mark as INCONCLUSIVE. Do not guess.
