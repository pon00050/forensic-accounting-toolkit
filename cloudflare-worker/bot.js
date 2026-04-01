/**
 * Forensic Toolkit — Telegram Bot Webhook Handler
 *
 * Replaces the GitHub Actions cron polling loop with an instant webhook.
 * Telegram POSTs here the moment a message arrives; this worker responds
 * to Telegram within milliseconds and dispatches GitHub Actions for heavy work.
 *
 * Latency comparison:
 *   Before (cron poll): 30–90 min to see any response
 *   After  (webhook):   <1 sec for /help; ~30–60 sec for heavy commands
 *
 * Required worker secrets (set via `wrangler secret put <NAME>`):
 *   TELEGRAM_BOT_TOKEN   — your bot token from @BotFather
 *   TELEGRAM_CHAT_ID     — the authorized chat ID (only this chat is processed)
 *   GITHUB_TOKEN         — a PAT with repo + workflow scope (use ECOSYSTEM_PAT value)
 *
 * Required var in wrangler.toml:
 *   GITHUB_REPO = "pon00050/forensic-accounting-toolkit"
 */

const HELP_TEXT = `*Forensic Toolkit Agent Team*

Commands:
/status — latest ecosystem health score
/triage — run triage scan (~2 min)
/test — run all 11 repo test suites (~10 min)
/work — dispatch next P0/P1 fix immediately
/orchestrate — full coordinator run + auto-dispatch (~5 min)
/approve <repo/PR> — merge an autofix PR
/reject <repo/PR> — close an autofix PR
/errors — show recent workflow failures
/help — this message`;

// ── Telegram helpers ──────────────────────────────────────────────────────────

async function tgSend(env, chat_id, text) {
  await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id,
        text,
        parse_mode: "Markdown",
        disable_web_page_preview: true,
      }),
    }
  );
}

// ── GitHub helpers ────────────────────────────────────────────────────────────

/**
 * Dispatch a workflow via workflow_dispatch.
 * Returns true on HTTP 204 (accepted), false otherwise.
 */
async function ghDispatch(env, workflow, inputs = {}) {
  const resp = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        "Content-Type": "application/json",
        "User-Agent": "forensic-toolkit-bot/1.0",
      },
      body: JSON.stringify({ ref: "master", inputs }),
    }
  );
  return resp.status === 204;
}

// ── Main handler ──────────────────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    // Health check (GET)
    if (request.method !== "POST") {
      return new Response("Forensic Toolkit Bot — webhook active", { status: 200 });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("bad request", { status: 400 });
    }

    const msg = body.message || body.edited_message || {};
    const chat_id = String(msg.chat?.id ?? "");
    const text = (msg.text ?? "").trim();

    // Security: only process the authorized chat
    if (chat_id !== String(env.TELEGRAM_CHAT_ID)) {
      return new Response("ok"); // silently ignore
    }
    if (!text.startsWith("/")) {
      return new Response("ok"); // not a command
    }

    const parts = text.split(/\s+/);
    const cmd = parts[0].split("@")[0].toLowerCase(); // strip bot mention
    const args = parts.slice(1).join(" ");

    // ── /help: handled directly — no GitHub Actions needed ───────────────────
    if (cmd === "/help" || cmd === "/start") {
      await tgSend(env, chat_id, HELP_TEXT);
      return new Response("ok");
    }

    // ── All other commands: send ACK immediately, then dispatch GitHub Actions ─
    // The dispatched job (process-command in telegram-bot.yml) sends the real
    // result back via a separate Telegram message when it completes.
    const ACK = {
      "/status":     "Fetching status...",
      "/triage":     "Triage started. Results in ~2 min.",
      "/test":       "Tests running across 11 repos. Results in ~10 min.",
      "/orchestrate":"Orchestrator started. Full report in ~5 min.",
      "/work":       "Looking for top AI task...",
      "/errors":     "Fetching recent failures...",
    };

    const ack = ACK[cmd] ?? `Processing \`${cmd}\`...`;
    await tgSend(env, chat_id, ack);

    // Dispatch telegram-bot.yml in process-command mode with the full context
    const ok = await ghDispatch(env, "telegram-bot.yml", {
      command: cmd,
      args,
      chat_id,
    });

    if (!ok) {
      await tgSend(
        env,
        chat_id,
        "⚠️ GitHub Actions dispatch failed. Check Actions tab."
      );
    }

    return new Response("ok");
  },
};
