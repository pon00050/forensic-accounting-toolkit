"""
ask_agent.py — Sonnet SDK agent: codebase research Q&A.

Receives a natural language question from the user (via Telegram) and
searches across all 13 ecosystem repos to provide a researched answer.
Sends the answer directly back to Telegram.

Triggered by:
- /ask <question> via Telegram (explicit command)
- Any message ending with ? via Telegram (auto-detected)

Policy:
- Read-only: never writes to files, never commits
- Budget-capped to prevent runaway costs
- Answers in plain text suitable for Telegram (no markdown code fences)
"""

import asyncio
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _sdk_helpers import load_context, write_scratchpad, run_agent, collect_text  # noqa: E402

# ── Policy bundle ─────────────────────────────────────────────────────────────

POLICY = {
    "tool_policy": "Read + Glob + Grep + Bash (read-only) — research codebase to answer questions",
    "model_policy": "claude-sonnet-4-6 — natural language Q&A requires Sonnet reasoning",
    "permission_policy": "bypassPermissions — read-only exploration; no filesystem writes",
    "isolation_policy": "worker-session — stateless Q&A; no side effects",
    "budget_usd": 0.50,
    "max_turns": 15,
}

# ── System prompt ─────────────────────────────────────────────────────────────

ASK_SYSTEM_SUFFIX = f"""
## Your Role: Codebase Research Assistant

You are answering a question about the forensic-accounting-toolkit ecosystem.
You have READ-ONLY access to all 13 repos. Do NOT write files, commit, or run
any command that modifies state.

Policy: {json.dumps(POLICY, indent=2)}

## Available Repos

All ecosystem repos are cloned at `$WORKSPACE/_deps/<repo-name>/`. Hub root is
at `$WORKSPACE/`. The hub contains CLAUDE.md, AGENT_ARCHITECTURE.md,
Multi_Agents_Orchestration.md, WORKFLOW.md, knowledge/ (NOT available — gitignored),
lessons.md, and cross-issues/.

Key files to check for design decisions:
- `$WORKSPACE/CLAUDE.md` — ecosystem conventions and architecture
- `$WORKSPACE/AGENT_ARCHITECTURE.md` — agent system design
- `$WORKSPACE/lessons.md` — lessons learned (operational rules)
- `$WORKSPACE/_deps/<repo>/CLAUDE.md` — per-repo architecture
- `$WORKSPACE/_deps/<repo>/docs/` — per-repo documentation

## Important Limitation

`knowledge/` is gitignored and NOT available on CI. If the answer likely lives
in knowledge/ (business strategy, regulatory analysis, buyer research), say so
explicitly so the user can check it locally.

## Answer Format

- Plain text only — this goes to Telegram, NOT a terminal
- No markdown code fences (``` blocks) — use plain indentation instead
- Maximum 3000 characters total
- If the answer is longer, summarize and say "more details at <file path>"
- Lead with the direct answer, then supporting evidence
- Cite specific file paths when referencing code or docs

No preamble. No "I'll research that for you!" Just the answer.
"""

# ── Telegram helpers ──────────────────────────────────────────────────────────

def _tg_send(token: str, chat_id: str, text: str) -> None:
    """Send a message to Telegram. Splits if > 4000 chars."""
    chunk_size = 4000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    for chunk in chunks:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }).encode()
        try:
            with urllib.request.urlopen(
                urllib.request.Request(
                    f"https://api.telegram.org/bot{token}/sendMessage", data
                ), timeout=15
            ) as r:
                print(f"[tg] sent chunk OK (status={r.status})", file=sys.stderr)
        except Exception as e:
            # Retry without markdown parse_mode (in case formatting chars cause issues)
            try:
                data_plain = urllib.parse.urlencode({
                    "chat_id": chat_id, "text": chunk,
                    "disable_web_page_preview": "true",
                }).encode()
                with urllib.request.urlopen(
                    urllib.request.Request(
                        f"https://api.telegram.org/bot{token}/sendMessage", data_plain
                    ), timeout=15
                ):
                    print("[tg] sent chunk (plain fallback)", file=sys.stderr)
            except Exception as e2:
                print(f"[tg] send failed: {e} / {e2}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    question = os.environ.get("ASK_QUESTION", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    workspace = os.environ.get("GITHUB_WORKSPACE", ".")

    if not question:
        print("[ask] No question provided (ASK_QUESTION env var empty)", file=sys.stderr)
        if tg_token and tg_chat:
            _tg_send(tg_token, tg_chat, "No question received. Try: /ask <your question>")
        return

    # Inject workspace path into system suffix
    system_suffix = ASK_SYSTEM_SUFFIX.replace("$WORKSPACE", workspace)

    static_context = load_context()

    task_prompt = (
        f"## Question from user\n\n{question}\n\n"
        "Research this question using the available files and tools. "
        "Give a direct, specific answer. Cite file paths for evidence."
    )

    from claude_agent_sdk import ClaudeAgentOptions  # type: ignore

    options = ClaudeAgentOptions(
        system_prompt=static_context + system_suffix,
        allowed_tools=["Read", "Glob", "Grep", "Bash"],
        permission_mode="bypassPermissions",
        max_turns=POLICY["max_turns"],
        max_budget_usd=POLICY["budget_usd"],
        model="claude-sonnet-4-6",
        cwd=workspace,
    )

    print(f"[ask] Running ask agent for: {question[:80]}", file=sys.stderr)
    messages = await run_agent(
        task_prompt,
        options,
        escalation_context=f"Ask agent failed for question: {question[:200]}",
        agent_name="ask_agent",
    )

    answer = collect_text(messages).strip()

    # Write to scratchpad for audit
    write_scratchpad("ask-result.json", {
        "question": question,
        "answer": answer[:2000],
        "answer_length": len(answer),
    })

    # Send answer to Telegram
    if tg_token and tg_chat:
        if answer:
            _tg_send(tg_token, tg_chat, answer)
        else:
            _tg_send(tg_token, tg_chat, "No answer produced. Check workflow logs.")
    else:
        print(f"\n[ask] ANSWER:\n{answer}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
