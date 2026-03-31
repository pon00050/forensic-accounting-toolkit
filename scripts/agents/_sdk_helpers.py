"""
Shared SDK helpers for all forensic-accounting-toolkit agent scripts.

Provides:
- load_context(): load CONTEXT.md for prompt cache prefix
- write_scratchpad(): write JSON to _scratchpad/ with timestamp
- read_scratchpad(): read a scratchpad file if it exists
- collect_text(): collect text from claude_agent_sdk message stream
- run_agent(): run an SDK agent with retry on failure (Principle #12)
- generate_task_id(): UUID4 short identifier for task-notification envelopes
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────

AGENTS_DIR = Path(__file__).parent
SCRATCHPAD = Path(os.environ.get("GITHUB_WORKSPACE", ".")) / "_scratchpad"


def load_context() -> str:
    """Load CONTEXT.md — the static prefix shared by all agents for prompt caching."""
    context_path = AGENTS_DIR / "CONTEXT.md"
    if not context_path.exists():
        raise FileNotFoundError(f"CONTEXT.md not found at {context_path}")
    return context_path.read_text(encoding="utf-8")


def generate_task_id() -> str:
    """Generate a short UUID4 task identifier for <task-notification> envelopes (MM#8)."""
    return "TASK-" + str(uuid.uuid4())[:8].upper()


# ── Scratchpad I/O ─────────────────────────────────────────────────────────────

def write_scratchpad(filename: str, data: dict[str, Any]) -> Path:
    """Write JSON data to _scratchpad/<filename> with auto-timestamp."""
    SCRATCHPAD.mkdir(parents=True, exist_ok=True)
    path = SCRATCHPAD / filename
    data.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[scratchpad] wrote {path}", file=sys.stderr)
    return path


def read_scratchpad(filename: str) -> dict[str, Any] | None:
    """Read a scratchpad file; returns None if it doesn't exist."""
    path = SCRATCHPAD / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _append_task_notification(
    task_id: str,
    agent_name: str,
    status: str,
    summary: str,
    token_usage: dict | None = None,
) -> None:
    """
    Append a <task-notification> audit entry to task-notifications.jsonl (MM#8).

    Each line is a JSON record. The XML envelope format matches the coordinator
    protocol: task-id, status, summary, token-usage.
    """
    SCRATCHPAD.mkdir(parents=True, exist_ok=True)
    log_path = SCRATCHPAD / "task-notifications.jsonl"

    entry = {
        "task_id": task_id,
        "agent": agent_name,
        "status": status,  # "complete" | "failed" | "retried"
        "summary": summary[:300],
        "token_usage": token_usage or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "envelope": (
            f'<task-notification task-id="{task_id}" agent="{agent_name}" '
            f'status="{status}" summary="{summary[:120].replace(chr(34), chr(39))}" />'
        ),
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[task-notification] {entry['envelope']}", file=sys.stderr)


# ── Message stream handling ────────────────────────────────────────────────────

def collect_text(messages: list) -> str:
    """Extract all text content from a list of SDK messages."""
    parts = []
    for msg in messages:
        if hasattr(msg, "content"):
            for block in msg.content if isinstance(msg.content, list) else [msg.content]:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif isinstance(block, str):
                    parts.append(block)
    return "\n".join(parts)


def _extract_token_usage(messages: list) -> dict:
    """Best-effort extraction of token usage from SDK messages."""
    for msg in reversed(messages):
        usage = getattr(msg, "usage", None)
        if usage:
            return {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
                "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
            }
    return {}


# ── Agent runner with retry (Principle #12) ───────────────────────────────────

async def run_agent(
    prompt: str,
    options,  # ClaudeAgentOptions
    *,
    max_retries: int = 1,
    escalation_context: str = "",
    agent_name: str = "",
) -> list:
    """
    Run an SDK agent and retry once on failure (Principle #12: continue failed workers).

    On first failure: sends a correction prompt with error context.
    On second failure: writes escalation.md and re-raises.

    Writes a <task-notification> entry to task-notifications.jsonl on completion
    or failure (MM#8 audit trail).

    Returns the list of messages from the successful run.
    """
    from claude_agent_sdk import ClaudeSDKClient  # type: ignore

    task_id = generate_task_id()
    # Derive agent name from caller if not provided
    if not agent_name:
        agent_name = os.path.basename(
            sys._getframe(1).f_globals.get("__file__", "unknown")
        ).replace(".py", "")

    messages: list = []
    last_error: Exception | None = None

    async with ClaudeSDKClient(options=options) as client:
        for attempt in range(max_retries + 1):
            try:
                messages = []
                await client.query(prompt if attempt == 0 else _correction_prompt(last_error, escalation_context))
                async for msg in client.receive_response():
                    messages.append(msg)
                    # Print text to stdout for workflow logs
                    if hasattr(msg, "content"):
                        content = msg.content
                        if isinstance(content, list):
                            for block in content:
                                if hasattr(block, "text"):
                                    print(block.text, end="", flush=True)
                        elif hasattr(content, "text"):
                            print(content.text, end="", flush=True)

                text_summary = collect_text(messages)[:200]
                token_usage = _extract_token_usage(messages)

                if attempt > 0:
                    _append_task_notification(task_id, agent_name, "retried-complete", text_summary, token_usage)
                else:
                    _append_task_notification(task_id, agent_name, "complete", text_summary, token_usage)

                return messages

            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    print(f"\n[retry] attempt {attempt + 1} failed: {exc}", file=sys.stderr)
                    print("[retry] continuing with same worker (Principle #12)", file=sys.stderr)
                    _append_task_notification(task_id, agent_name, "retried", str(exc)[:200])
                    continue
                # All retries exhausted — write escalation
                _append_task_notification(task_id, agent_name, "failed", str(exc)[:200])
                _write_escalation(last_error, escalation_context)
                raise

    return messages  # unreachable but satisfies type checker


def _correction_prompt(error: Exception | None, context: str) -> str:
    return (
        f"Your previous attempt failed with error: {error}\n"
        f"The error context you already have is valuable — do not start over.\n"
        f"Try a different approach to accomplish the same goal.\n"
        + (f"\nAdditional context: {context}\n" if context else "")
        + "If this attempt also fails, write a report to _scratchpad/escalation.md "
        "describing what you tried and why it failed, then stop."
    )


def _write_escalation(error: Exception, context: str) -> None:
    SCRATCHPAD.mkdir(parents=True, exist_ok=True)
    path = SCRATCHPAD / "escalation.md"
    content = (
        f"# Escalation — {datetime.now(timezone.utc).isoformat()}\n\n"
        f"## Error\n```\n{error}\n```\n\n"
        f"## Context\n{context or 'No additional context.'}\n\n"
        "## Required Action\nHuman review needed. The autonomous agent exhausted retries.\n"
    )
    path.write_text(content, encoding="utf-8")
    print(f"[escalation] written to {path}", file=sys.stderr)
