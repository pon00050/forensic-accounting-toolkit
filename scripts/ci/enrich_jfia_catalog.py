#!/usr/bin/env python3
"""
jfia-catalog enrichment pipeline.

For articles missing abstract or keywords:
  1. Download the article PDF from S3 (url is in pdf_url field)
  2. Extract text from the first 3 pages via pdfplumber
  3. Ask Sonnet to return the verbatim abstract and keywords from the paper text
  4. Write back to jfia_catalog.json if Sonnet found real content

Rules:
  - Never overwrite existing non-empty abstract or non-empty keywords
  - If Sonnet cannot find an abstract in the PDF text, the field stays ""
  - All changes are append-only to missing fields
  - Hard cost cap: BUDGET_USD (default $3.00)
  - Prioritisation order: missing both > missing abstract only > missing keywords only

Environment variables (set by workflow):
  ANTHROPIC_API_KEY  — required
  MAX_ARTICLES       — cap on articles processed per run (default 60)
  DRY_RUN            — "true" to log without writing (default "false")
  PRIORITY           — "both" | "abstract" | "keywords" (default "both")
  GITHUB_WORKSPACE   — path prefix for _jfia-catalog/ and _scratchpad/

Dependencies: pip install pdfplumber requests anthropic
"""
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import anthropic
import pdfplumber
import requests

# ── configuration ────────────────────────────────────────────────────────────

WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", "."))
CATALOG_PATH = WORKSPACE / "_jfia-catalog" / "jfia_catalog.json"
SCRATCHPAD = WORKSPACE / "_scratchpad"

MAX_ARTICLES = int(os.environ.get("MAX_ARTICLES", "60"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
PRIORITY = os.environ.get("PRIORITY", "both")  # "both" | "abstract" | "keywords"

BUDGET_USD = 3.00
# Sonnet 4.6 pricing (per token)
COST_INPUT = 3e-6
COST_OUTPUT = 15e-6

PDF_TIMEOUT_SEC = 30
PDF_MAX_PAGES = 3       # abstract always appears in first 2 pages
TEXT_CHAR_LIMIT = 6000  # ~1500 tokens; more than enough for abstract extraction

RATE_LIMIT_PAUSE = 0.4  # seconds between Sonnet calls

# ── LLM prompt ───────────────────────────────────────────────────────────────

EXTRACT_PROMPT = """\
You are processing an academic paper from the Journal of Forensic & Investigative Accounting (JFIA).

Paper title: {title}
Authors: {authors}

The following text was extracted from the first pages of the PDF:
<paper_text>
{text}
</paper_text>

Your task: extract the following from the paper text above (verbatim — do not paraphrase or summarise):

1. abstract — The paper's abstract exactly as written. If no abstract is present in the text, return null.
2. keywords — Keywords as listed in the paper (look for "Keywords:", "Key Words:", "Index Terms:", etc.).
   Return as a JSON array of strings. If no keywords section exists, return null.

Respond with ONLY valid JSON, no markdown fences, no commentary:
{{"abstract": "<verbatim abstract text>" or null, "keywords": ["keyword1", ...] or null}}"""

# ── helpers ───────────────────────────────────────────────────────────────────


def download_pdf_text(pdf_url: str) -> Optional[str]:
    """Download a PDF from S3 and return extracted text from the first pages."""
    try:
        resp = requests.get(pdf_url, timeout=PDF_TIMEOUT_SEC, stream=True)
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            for chunk in resp.iter_content(chunk_size=16384):
                fh.write(chunk)
            tmp_path = Path(fh.name)

        pages_text: list[str] = []
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages[:PDF_MAX_PAGES]:
                t = page.extract_text()
                if t and t.strip():
                    pages_text.append(t.strip())

        tmp_path.unlink(missing_ok=True)

        combined = "\n\n".join(pages_text)
        return combined if combined.strip() else None

    except requests.exceptions.RequestException as e:
        print(f"    PDF download failed ({type(e).__name__}): {e}")
        return None
    except Exception as e:
        print(f"    PDF parse failed ({type(e).__name__}): {e}")
        return None


def extract_with_sonnet(
    client: anthropic.Anthropic,
    title: str,
    authors: list[str],
    text: str,
) -> tuple[Optional[str], Optional[list[str]], dict]:
    """
    Call Sonnet to extract abstract and keywords from paper text.
    Returns (abstract_or_None, keywords_or_None, usage_dict).
    """
    prompt = EXTRACT_PROMPT.format(
        title=title,
        authors=", ".join(authors) if authors else "Unknown",
        text=text[:TEXT_CHAR_LIMIT],
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = {
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    raw = msg.content[0].text.strip()

    # Strip markdown code fences if the model included them despite instructions
    if raw.startswith("```"):
        inner = raw.split("```", 2)
        raw = inner[1].lstrip("json").strip() if len(inner) >= 2 else raw

    parsed = json.loads(raw)
    abstract: Optional[str] = parsed.get("abstract")
    keywords: Optional[list] = parsed.get("keywords")

    # Sanitise: reject empty strings / empty lists returned as "found"
    if isinstance(abstract, str) and not abstract.strip():
        abstract = None
    if isinstance(keywords, list) and len(keywords) == 0:
        keywords = None

    return abstract, keywords, usage


def article_needs_work(article: dict) -> tuple[bool, bool]:
    """Return (needs_abstract, needs_keywords) for an article."""
    needs_abstract = not article.get("abstract", "").strip()
    needs_keywords = not article.get("keywords")  # [] or None
    return needs_abstract, needs_keywords


def priority_key(needs_abstract: bool, needs_keywords: bool) -> int:
    """Sorting key: lower = higher priority."""
    if PRIORITY == "abstract":
        return 0 if needs_abstract else 1
    if PRIORITY == "keywords":
        return 0 if needs_keywords else 1
    # "both": missing both first, then abstract-only, then keywords-only
    return 0 if (needs_abstract and needs_keywords) else (1 if needs_abstract else 2)


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    SCRATCHPAD.mkdir(exist_ok=True)

    if not CATALOG_PATH.exists():
        print(f"ERROR: catalog not found at {CATALOG_PATH}")
        sys.exit(1)

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    total_articles = catalog.get("total_articles", 0)

    # Build work queue
    work_queue: list[tuple[dict, dict, bool, bool]] = []   # (issue, article, na, nk)
    for issue in catalog["issues"]:
        for article in issue["articles"]:
            na, nk = article_needs_work(article)
            if (na or nk) and article.get("pdf_url"):
                work_queue.append((issue, article, na, nk))

    # Sort by priority, then cap
    work_queue.sort(key=lambda x: priority_key(x[2], x[3]))
    total_needing_work = len(work_queue)
    work_queue = work_queue[:MAX_ARTICLES]

    print(
        f"Catalog: {total_articles} articles total\n"
        f"Need enrichment: {total_needing_work} (cap: {MAX_ARTICLES}, "
        f"priority: '{PRIORITY}', dry_run: {DRY_RUN})"
    )

    if DRY_RUN:
        print("\nDRY RUN — first 15 articles that would be processed:")
        for _, article, na, nk in work_queue[:15]:
            flags = ("abstract" if na else "") + (" keywords" if nk else "")
            print(f"  [{flags.strip()}] {article['title'][:65]}")
        print(f"\n(Total would process: {len(work_queue)})")
        # Write dry-run result so workflow can report it
        (SCRATCHPAD / "jfia-enrich-result.json").write_text(
            json.dumps({
                "dry_run": True,
                "would_process": len(work_queue),
                "total_needing_enrichment": total_needing_work,
                "enriched": 0,
            }, indent=2)
        )
        return

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    enriched_count = 0
    abstracts_added = 0
    keywords_added = 0
    failed_count = 0
    no_data_count = 0
    total_cost = 0.0
    results: list[dict] = []

    for i, (issue, article, needs_abstract, needs_keywords) in enumerate(work_queue, 1):
        if total_cost >= BUDGET_USD:
            print(f"\nBudget cap ${BUDGET_USD:.2f} reached — stopping at article {i - 1}")
            break

        title = article["title"]
        print(
            f"[{i}/{len(work_queue)}] "
            f"{'[abstract+keywords]' if (needs_abstract and needs_keywords) else ('[abstract]' if needs_abstract else '[keywords]')} "
            f"{title[:60]}"
        )

        # Step 1: download + extract PDF text
        text = download_pdf_text(article["pdf_url"])
        if not text:
            print("    → skipped (PDF unavailable or empty)")
            failed_count += 1
            results.append({"title": title, "status": "pdf_failed"})
            continue

        # Step 2: LLM extraction
        try:
            abstract, keywords, usage = extract_with_sonnet(
                client, title, article.get("authors", []), text
            )
        except json.JSONDecodeError as e:
            print(f"    → LLM returned invalid JSON: {e}")
            failed_count += 1
            results.append({"title": title, "status": "llm_json_error"})
            continue
        except Exception as e:
            print(f"    → LLM call failed: {e}")
            failed_count += 1
            results.append({"title": title, "status": "llm_error", "error": str(e)[:100]})
            continue

        cost = usage["input_tokens"] * COST_INPUT + usage["output_tokens"] * COST_OUTPUT
        total_cost += cost

        # Step 3: write back (append-only — never overwrite existing content)
        ab_added = False
        kw_added = False
        if needs_abstract and abstract:
            article["abstract"] = abstract
            ab_added = True
            abstracts_added += 1
        if needs_keywords and keywords:
            article["keywords"] = keywords
            kw_added = True
            keywords_added += 1

        if ab_added or kw_added:
            enriched_count += 1
            status = "enriched"
            print(
                f"    → enriched "
                f"({'abstract' if ab_added else ''}{'+'if ab_added and kw_added else ''}{'keywords' if kw_added else ''}) "
                f"| ${cost:.4f} | total ${total_cost:.4f}"
            )
        else:
            no_data_count += 1
            status = "no_data_found"
            print(f"    → no extractable data in PDF | ${cost:.4f}")

        results.append({
            "title": title,
            "status": status,
            "abstract_added": ab_added,
            "keywords_added": kw_added,
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "cost_usd": round(cost, 6),
        })

        time.sleep(RATE_LIMIT_PAUSE)

    # Write enriched catalog back
    if enriched_count > 0:
        CATALOG_PATH.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nWrote enriched catalog: {enriched_count} articles updated")
    else:
        print("\nNo articles enriched — catalog unchanged")

    # Summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "enriched": enriched_count,
        "abstracts_added": abstracts_added,
        "keywords_added": keywords_added,
        "failed": failed_count,
        "no_data_found": no_data_count,
        "total_cost_usd": round(total_cost, 4),
        "budget_usd": BUDGET_USD,
        "articles_processed": min(i, len(work_queue)),
        "total_needing_enrichment": total_needing_work,
        "results": results,
    }
    (SCRATCHPAD / "jfia-enrich-result.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(
        f"\n{'='*50}\n"
        f"Enriched:        {enriched_count}\n"
        f"  Abstracts:     {abstracts_added}\n"
        f"  Keywords:      {keywords_added}\n"
        f"PDF failures:    {failed_count}\n"
        f"No data in PDF:  {no_data_count}\n"
        f"Total API cost:  ${total_cost:.4f}\n"
        f"{'='*50}"
    )


if __name__ == "__main__":
    main()
