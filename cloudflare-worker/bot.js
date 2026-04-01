/**
 * Forensic Toolkit — Telegram Bot Webhook Handler
 *
 * The team leader agent. Responds to every Telegram message — either
 * directly (slash commands, help) or via Opus-powered conversation with
 * full project vision and memory.
 *
 * Architecture:
 *   /help, /start          → direct text response (<1 sec)
 *   /status, /triage, etc. → ACK + GitHub Actions dispatch (~30-60 sec)
 *   /ask <question>        → ACK + GHA Sonnet deep search (~1 min)
 *   /clear                 → clear conversation history from KV
 *   /remember <text>       → save to persistent memory
 *   /forget <keyword>      → remove from persistent memory
 *   /memories              → list all persistent memories
 *   any other text         → Opus team leader with conversation history + live context + memory (5-15 sec)
 *
 * Required worker secrets (set via `wrangler secret put <NAME>`):
 *   TELEGRAM_BOT_TOKEN   — bot token from @BotFather
 *   TELEGRAM_CHAT_ID     — authorized chat ID
 *   GITHUB_TOKEN         — PAT with repo + workflow scope (ECOSYSTEM_PAT value)
 *   ANTHROPIC_API_KEY    — for team leader Opus calls
 *
 * Required vars in wrangler.toml:
 *   GITHUB_REPO = "pon00050/forensic-accounting-toolkit"
 *
 * Required KV namespace in wrangler.toml:
 *   [[kv_namespaces]]
 *   binding = "CHAT_STORE"
 */

// ── Team Leader System Prompt ─────────────────────────────────────────────────

const SYSTEM_PROMPT = `You are the Team Leader of the Forensic Accounting Toolkit — a Korean forensic accounting intelligence platform. You manage a 13-repo ecosystem and a team of AI agents for Jisoo (지수). You are her strategic partner, not just a command router.

## YOUR ROLE
Think like a CTO/team lead. You:
- Know the full project vision and current phase
- Suggest what to work on next based on strategic priorities
- Discuss tradeoffs, architecture, and business strategy
- Dispatch specialist agents for heavy work (code search, fixes, analysis)
- Never say "I can't do that" — either do it, dispatch it, or explain the tradeoff

## PROJECT VISION (Phase 1-5 Arc)
This is a KOSDAQ accounting anomaly early warning system — not a generic framework.

Phase 1 (COMPLETE): Beneish M-Score batch pipeline. 7,042 company-year rows, 1,470 companies ranked by manipulation probability.

Phase 2 (SCAFFOLD BUILT, 5 GAPS): CB/BW timeline reconstruction. The Korean-specific manipulation scheme: CB issued → price drops → 리픽싱 → insiders exercise at depressed price → price recovers → sell. Joins DART + SEIBRO + KRX data. Missing: DART key pipeline run, SEIBRO scraper, corp_ticker_map.parquet, scoping filter (top-100 M-Score ∪ all companies with CB/BW events).

Phase 3 (NOT STARTED): Disclosure timing anomalies. Compare DART filing timestamps vs same-day KRX price/volume. Pre-disclosure trading = information asymmetry signal.

Phase 4 (NOT STARTED): Officer/shareholder network graph. Entity resolution across filings to find hidden connections between CB subscribers and issuers.

Phase 5 (DESIGN COMPLETE): Continuous 3-way match monitoring. Leg 1 (batch quantitative flags) + Leg 2 (live KRX price/volume, ±5% move or 3x volume) + Leg 3 (live DART RSS + news, classified A–F by Haiku). Match engine fires when multiple legs trigger on same company within 5 trading days. Alert sent to Telegram. Steady-state: ~2 hrs/week human attention.

## BUSINESS STRATEGY
Path B chosen: outreach-first, not build-and-hope. No commercial competitor exists for KOSDAQ small-cap forensic screening.
- Sellable product: MCP tool access (Tool #12) wrapping enforcement intelligence into AI workflows
- Revenue targets: hedge fund API subscriptions ₩10-100M/year, forensic firm per-report ₩10-50M/year, government grants ₩40-80M one-time
- Key insight: "5 hours of outreach is worth more than 2 months of additional building"
- Target buyers: Timefolio, Billionfold, VIP, Kabouter (hedge funds), EY Forensic, Deloitte 기업조사
- The website comes AFTER getting a response from outreach, not before

## 13-REPO ECOSYSTEM
Foundation: kr-company-registry (DART↔KRX crosswalk, 3,949 companies), kr-trading-calendar (KRX trading days, holidays), kr-beneish (Beneish M-Score for K-IFRS), jfia-catalog (469 JFIA forensic accounting articles)
Analysis: kr-derivatives (CB/BW option pricing + ITM detection), jfia-forensic (detectlet schema + JFIA enrichment), kr-enforcement-cases (FSS/SFC enforcement dataset + LLM enrichment)
Platform: kr-forensic-core (shared constants/schemas), kr-dart-pipeline (15 extractors → parquet), kr-anomaly-scoring (CB/BW + timing + officer network scoring), kr-stat-tests (14 stat tests: PCA, bootstrap, LASSO, RF), krff-shell (CLI + reports + review queue + DuckDB)

## YOUR AGENT TEAM (4-tier autonomous CI)
- Tier 1 (bash, daily): 5 scanners — pytest across 11 repos, doc drift, count sync, convention check
- Tier 2 (Haiku, daily): triage synthesis, data validation after pipeline runs
- Tier 3 (Sonnet, weekly): convention audit (Sunday), pipeline runner (Monday)
- Tier 4 (Sonnet, event-driven): autofix — reads brief, fixes code, creates PR
- Orchestrator (Sonnet, Mon+Thu): synthesizes all worker outputs, creates GitHub action briefs, dispatches fixes
Dispatch: /triage (2 min), /test (10 min), /orchestrate (5 min), /work (dispatches top fix), /ask (1 min deep search)

## KEY TECHNICAL RULES
- uv (never pip). Tests: uv run pytest tests/ -v. Build: hatchling.
- pykrx is geo-blocked on cloud IPs — works fine from Korean residential IP. CI uses FinanceDataReader.
- Raw DART/KRX data in data/raw/ is immutable. Never mix K-GAAP and K-IFRS.
- All DART API calls through retry wrapper only.
- Parquet for pipeline artifacts, CSV for human-readable outputs.

## DEFERRED DECISIONS (do not recommend these)
- kr-beneish PyPI publication — deliberately deferred by owner
- SEIBRO API integration — deferred until end of April 2026, KSD not cooperating
- pykrx → FinanceDataReader switch — owner is researching rationale first

## HOW TO RESPOND
- This is a phone chat. Be concise but substantive.
- When asked what to work on: consider the phase arc, current blockers (SEIBRO, corp_ticker_map), and business priorities.
- When asked a technical question answerable from context: answer directly.
- When a question requires searching code/files: suggest /ask <question>.
- When a task should be executed: suggest /work or the specific slash command.
- When discussing strategy: draw on the vision, positioning, and business context above.
- Never drop a message. Always respond, even "I don't have enough context — try /ask."
- Default language: English. Respond in Korean only if the user writes in Korean or explicitly requests Korean.

## PERSISTENT MEMORY
You have long-term memory that survives across conversations. Your memories are shown in the ## YOUR MEMORIES section below (injected at runtime).

To save something important, end your response with a tag on its own line:
>>SAVE: category | content
Example: >>SAVE: decision | Deferred kr-enforcement-cases MCP tool until after first outreach response

To remove an outdated memory:
>>FORGET: memory-id

Categories: decision, fact, preference, milestone, blocker

Save when:
- The user makes a deliberate decision (defer, approve, reject, choose an approach)
- A milestone is completed (tests all pass, PR merged, outreach sent)
- The user states a preference about how to work
- You learn a fact that would be lost when this conversation expires

Do NOT save: routine status checks, greetings, ephemeral task details, things already in your system prompt.`;

const HELP_TEXT = `*Forensic Toolkit — Team Leader*

Commands:
/status — latest ecosystem health score
/triage — run triage scan (~2 min)
/test — run all 11 repo test suites (~10 min)
/work — dispatch next P0/P1 fix immediately
/orchestrate — full coordinator run + auto-dispatch (~5 min)
/approve <repo/PR> — merge an autofix PR
/reject <repo/PR> — close an autofix PR
/errors — show recent workflow failures
/ask <question> — deep codebase search via Sonnet (~1 min)
/board — show current board (priorities + owners)
/done <issue#> — close an issue and mark board Done
/remember <text> — save something to my long-term memory
/forget <keyword> — remove a memory by id or keyword
/memories — list everything I remember
/clear — reset conversation history
/help — this message

_Any other message: I respond directly as your team leader._`;

// ── Telegram helpers ──────────────────────────────────────────────────────────

async function tgSend(env, chat_id, text) {
  const resp = await fetch(
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
  // Fall back to plain text if Markdown parse fails
  if (!resp.ok) {
    await fetch(
      `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id, text: text.replace(/[*_`[\]]/g, "") }),
      }
    );
  }
}

// ── GitHub helpers ────────────────────────────────────────────────────────────

async function ghDispatch(env, workflow, inputs = {}) {
  const resp = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        "Content-Type": "application/json",
        "User-Agent": "forensic-toolkit-bot/2.0",
      },
      body: JSON.stringify({ ref: "master", inputs }),
    }
  );
  return resp.status === 204;
}

// ── Memory helpers ────────────────────────────────────────────────────────────

async function loadMemories(env) {
  try {
    const raw = await env.CHAT_STORE.get("memory:all");
    return raw ? JSON.parse(raw) : { memories: [] };
  } catch {
    return { memories: [] };
  }
}

async function saveMemories(env, memoriesObj) {
  try {
    await env.CHAT_STORE.put("memory:all", JSON.stringify(memoriesObj));
  } catch {
    // Non-fatal
  }
}

function processMemoryTags(reply, memoriesObj) {
  const lines = reply.split("\n");
  const cleanLines = [];
  const saves = [];
  const forgets = [];

  for (const line of lines) {
    if (line.startsWith(">>SAVE:")) {
      const parts = line.slice(7).trim().split("|");
      const category = (parts[0] || "fact").trim();
      const content = parts.slice(1).join("|").trim();
      if (content) {
        saves.push({
          id: `auto-${new Date().toISOString().split("T")[0]}-${Date.now().toString(36)}`,
          category,
          content,
          created: new Date().toISOString().split("T")[0],
          importance: 7,
        });
      }
    } else if (line.startsWith(">>FORGET:")) {
      forgets.push(line.slice(9).trim());
    } else {
      cleanLines.push(line);
    }
  }

  if (forgets.length > 0) {
    memoriesObj.memories = memoriesObj.memories.filter(
      (m) => !forgets.includes(m.id)
    );
  }
  memoriesObj.memories.push(...saves);

  return {
    cleanReply: cleanLines.join("\n").trim(),
    memoriesChanged: saves.length > 0 || forgets.length > 0,
    updatedMemories: memoriesObj,
  };
}

// ── Team Leader brain (Opus with conversation history + live context + memory) ─

async function fetchLiveContext(env) {
  try {
    const resp = await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPO}/actions/variables/LIVE_CONTEXT`,
      {
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          "User-Agent": "forensic-toolkit-bot/2.0",
          Accept: "application/vnd.github+json",
        },
      }
    );
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.value || null;
  } catch {
    return null;
  }
}

async function chatWithLeader(env, chat_id, userMessage) {
  const key = `chat:${chat_id}`;

  // Load conversation history, live context, and memories in parallel
  const [storedHistory, liveContext, memoriesObj] = await Promise.all([
    env.CHAT_STORE.get(key).catch(() => null),
    fetchLiveContext(env),
    loadMemories(env),
  ]);

  let history = [];
  try {
    history = storedHistory ? JSON.parse(storedHistory) : [];
  } catch {
    history = [];
  }

  history.push({ role: "user", content: userMessage });
  if (history.length > 20) history = history.slice(-20);

  // Build three-tier system prompt
  const memoriesText = memoriesObj.memories.length > 0
    ? memoriesObj.memories
        .map((m) => `- [${m.category}] ${m.content} (${m.created})`)
        .join("\n")
    : "(No memories saved yet)";

  const fullSystem = SYSTEM_PROMPT
    + "\n\n## CURRENT STATE (auto-synced from CI)\n"
    + (liveContext || "(no live context synced yet — run /orchestrate to populate)")
    + "\n\n## YOUR MEMORIES\n"
    + memoriesText;

  let reply;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000); // 25s hard limit
    const resp = await fetch("https://gateway.ai.cloudflare.com/v1/cb953826693a82080f5b64551e0d6ebb/default/anthropic/v1/messages", {
      method: "POST",
      signal: controller.signal,
      headers: {
        "x-api-key": env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "cf-aig-authorization": `Bearer ${env.CF_AIG_TOKEN}`,
      },
      body: JSON.stringify({
        model: "claude-opus-4-6",
        max_tokens: 2048,
        system: fullSystem,
        messages: history,
      }),
    });
    clearTimeout(timeoutId);

    if (!resp.ok) {
      const err = await resp.text();
      console.error("Anthropic API error:", resp.status, err);
      await tgSend(env, chat_id,
        "I'm having trouble connecting right now. Try again, or use /ask for a deep code search.");
      return;
    }

    const data = await resp.json();
    reply = data.content?.[0]?.text ?? "Sorry, I couldn't generate a response.";
  } catch (e) {
    console.error("chatWithLeader error:", e?.name, e?.message);
    const msg = e?.name === "AbortError"
      ? "Response took too long (>25s). Try a shorter question, or use /ask for deep search."
      : "Request failed. Try again, or use /ask for deep search.";
    await tgSend(env, chat_id, msg);
    return;
  }

  // Parse and strip memory tags from reply
  const { cleanReply, memoriesChanged, updatedMemories } = processMemoryTags(reply, memoriesObj);

  // Save memory changes if any
  if (memoriesChanged) {
    await saveMemories(env, updatedMemories);
  }

  // Save conversation history (4-hour auto-expiry)
  history.push({ role: "assistant", content: cleanReply });
  try {
    await env.CHAT_STORE.put(key, JSON.stringify(history),
      { expirationTtl: 14400 });
  } catch {
    // KV write failure is non-fatal — response still sent
  }

  await tgSend(env, chat_id, cleanReply);
}

// ── Store message in KV history without generating a reply ───────────────────
// Used so the leader has context about dispatched commands.

async function appendToHistory(env, chat_id, role, content) {
  const key = `chat:${chat_id}`;
  try {
    const stored = await env.CHAT_STORE.get(key);
    let history = stored ? JSON.parse(stored) : [];
    history.push({ role, content });
    if (history.length > 20) history = history.slice(-20);
    await env.CHAT_STORE.put(key, JSON.stringify(history),
      { expirationTtl: 14400 });
  } catch {
    // Non-fatal
  }
}

// ── Main handler ──────────────────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    // Health check (GET)
    if (request.method !== "POST") {
      return new Response("Forensic Toolkit Team Leader — webhook active", { status: 200 });
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

    // ── /clear: reset conversation history ──────────────────────────────────
    if (text === "/clear" || text === "/clear@forensicbot") {
      try {
        await env.CHAT_STORE.delete(`chat:${chat_id}`);
      } catch { /* non-fatal */ }
      await tgSend(env, chat_id, "Conversation cleared.");
      return new Response("ok");
    }

    // ── /help and /start: handled directly ───────────────────────────────────
    if (text === "/help" || text === "/start" ||
        text.startsWith("/help@") || text.startsWith("/start@")) {
      await tgSend(env, chat_id, HELP_TEXT);
      return new Response("ok");
    }

    // ── Non-command messages → team leader brain ─────────────────────────────
    if (!text.startsWith("/")) {
      await chatWithLeader(env, chat_id, text);
      return new Response("ok");
    }

    // ── Slash commands ────────────────────────────────────────────────────────
    const parts = text.split(/\s+/);
    const cmd = parts[0].split("@")[0].toLowerCase();
    const args = parts.slice(1).join(" ");
    const today = new Date().toISOString().split("T")[0];

    // ── /remember: save to persistent memory ────────────────────────────────
    if (cmd === "/remember") {
      if (!args) {
        await tgSend(env, chat_id, "Usage: /remember <text>");
        return new Response("ok");
      }
      const memoriesObj = await loadMemories(env);
      memoriesObj.memories.push({
        id: `user-${today}-${Date.now().toString(36)}`,
        category: "user",
        content: args,
        created: today,
        importance: 8,
      });
      await saveMemories(env, memoriesObj);
      await tgSend(env, chat_id, `Remembered: ${args}`);
      return new Response("ok");
    }

    // ── /forget: remove memory by id or keyword ──────────────────────────────
    if (cmd === "/forget") {
      if (!args) {
        await tgSend(env, chat_id, "Usage: /forget <id or keyword>");
        return new Response("ok");
      }
      const memoriesObj = await loadMemories(env);
      const before = memoriesObj.memories.length;
      memoriesObj.memories = memoriesObj.memories.filter(
        (m) => m.id !== args && !m.content.toLowerCase().includes(args.toLowerCase())
      );
      const removed = before - memoriesObj.memories.length;
      await saveMemories(env, memoriesObj);
      await tgSend(env, chat_id,
        removed > 0 ? `Removed ${removed} memory item(s) matching: ${args}` : `No memories matched: ${args}`
      );
      return new Response("ok");
    }

    // ── /memories: list all persistent memories ──────────────────────────────
    if (cmd === "/memories") {
      const memoriesObj = await loadMemories(env);
      if (memoriesObj.memories.length === 0) {
        await tgSend(env, chat_id, "No memories saved yet.");
        return new Response("ok");
      }
      const lines = memoriesObj.memories.map(
        (m) => `• [${m.category}] ${m.content}\n  _id: ${m.id} | ${m.created}_`
      );
      await tgSend(env, chat_id, `*Memories (${memoriesObj.memories.length})*\n\n${lines.join("\n\n")}`);
      return new Response("ok");
    }

    const ACK = {
      "/status":      "Fetching status...",
      "/triage":      "Triage started. Results in ~2 min.",
      "/test":        "Tests running across 11 repos. Results in ~10 min.",
      "/orchestrate": "Orchestrator started. Full report in ~5 min.",
      "/work":        "Looking for top AI task...",
      "/errors":      "Fetching recent failures...",
      "/ask":         "Researching your question (~1 min)...",
      "/approve":     "Merging PR...",
      "/reject":      "Closing PR...",
      "/board":       "Loading board...",
      "/done":        "Closing issue and updating board...",
    };

    const ack = ACK[cmd] ?? `Processing \`${cmd}\`...`;
    await tgSend(env, chat_id, ack);

    // Store dispatched commands in history so leader has context
    await appendToHistory(env, chat_id, "user",
      `[User ran ${cmd}${args ? ` ${args}` : ""}]`);
    await appendToHistory(env, chat_id, "assistant",
      `[Dispatched ${cmd} to agent team — result arriving in background]`);

    // Dispatch telegram-bot.yml
    const ok = await ghDispatch(env, "telegram-bot.yml", {
      command: cmd,
      args,
      chat_id,
    });

    if (!ok) {
      await tgSend(env, chat_id,
        "GitHub Actions dispatch failed. Check Actions tab.");
    }

    return new Response("ok");
  },
};
