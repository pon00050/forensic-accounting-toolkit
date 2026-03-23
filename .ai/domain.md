# domain.md — Forensic Accounting & Korean Capital Markets

## What This Project Does
Screens Korean listed companies for earnings manipulation and dilution risk.
Primary signals: Beneish M-score (IFRS-adapted), CB/BW dilution patterns, FSS enforcement history.
Output: scored company list with fraud probability, enforcement case context, dilution flags.

## Korean Accounting Standards
- **K-IFRS**: Korean adoption of IFRS. 상장사 required since 2011.
- **K-GAAP**: Older standard. Some unlisted companies still use it. Do not mix with K-IFRS.
- **CSM (Contractual Service Margin)**: IFRS17 insurance contract margin — key for kr-insurance-data.
- **K-ICS**: Korean Insurance Capital Standard (= Korean Solvency II).

## Key Data Sources (by authority)

| Source | What | API? |
|--------|------|------|
| DART (opendart.fss.or.kr) | Corporate filings (사업보고서, 감사보고서) | Yes (free) |
| KRX (data.krx.co.kr) | Market price, split history | Yes (free) |
| FSS enforcement DB | 제재 decisions | Web scrape |
| SEIBRO (seibro.or.kr) | CB/BW issuance history | Manual / API pending |
| FnGuide | Premium fundamentals | Paid subscription |

Data source priority: DART > KRX > FSS > SEIBRO > FnGuide.

## Beneish M-Score (Korean Adaptation)
Original 8-variable model by Daniel Beneish (1999). Key adjustments for Korea:
- DSRI (Days Sales Receivable Index): receivable management differs in 계열사 groups
- GMI (Gross Margin Index): margins compressed by 대형마트 buyer power in retail
- AQI (Asset Quality Index): intangible assets treated differently under K-IFRS vs US GAAP
- Threshold: M > -1.78 flags manipulation risk. Calibrated for Korean IFRS: M > -2.22 (less sensitive).

## Dilution Screening Logic
1. Identify CB/BW issuances from SEIBRO or DART
2. Cross-reference with stock price performance before/after
3. Flag: multiple CB tranches within 18 months, conversion at >10% discount to market
4. KOSDAQ companies are higher risk than KOSPI (less regulatory scrutiny)

## FSS Enforcement Cases (kr-enforcement-cases)
240 FSS/SFC enforcement decisions scraped and categorized.
Categories: 분식회계, 불공정거래, 공시위반, 내부자거래.
Use as context enrichment: if target company has prior enforcement, flag prominently.

## Ecosystem Status (as of March 17, 2026)
All repos published on GitHub under github.com/pon00050:
- kr-enforcement-cases v1.0.0 (March 17)
- kr-beneish, kr-derivatives, kr-trading-calendar, jfia-forensic, jfia-catalog (March 15)
Run 4 complete: 33.1% flag rate across KOSDAQ sample.

## Business Model
Target clients: quantitative hedge funds, activist investors, savings banks doing credit risk.
Pitch: API subscription for dilution + manipulation screening. 10-30M KRW/year per client.
Primary targets: Timefolio, Billionfold, VIP Asset Management.
LinkedIn InMail is the primary outreach channel. Personalize for each fund's strategy.
