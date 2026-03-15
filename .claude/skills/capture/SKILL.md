---
name: capture
description: Capture a content-worthy moment — writes structured record to content/captures/
user-invocable: true
disable-model-invocation: false
allowed-tools: Read, Write, Glob, Grep
---

Capture a content-worthy technical moment as a structured record. The argument `$ARGUMENTS` is the title (e.g., `/capture DART crDecsn.json endpoint discovery`).

## Steps

1. **Parse the title.** If `$ARGUMENTS` is provided, use it as the capture title. If empty, ask what to capture.

2. **Generate filename.** Create a slug from the title:
   - Lowercase, hyphens for spaces, strip special characters
   - Filename: `content/captures/YYYY-MM-DD-{slug}.md` (use today's date)

3. **Check for duplicates.** Glob `content/captures/*{slug-keywords}*` to avoid creating near-duplicate captures. If a similar capture exists, ask whether to update it or create a new one.

4. **Gather context.** Review the current conversation for:
   - What was being worked on (repos, files, commands)
   - What went wrong or was surprising
   - What metrics changed (before → after)
   - What was discovered or learned
   - Error messages, API responses, code snippets worth preserving

5. **Classify the type:**
   - `case-study`: A problem was investigated and resolved with a clear arc
   - `explainer`: A complex topic was broken down and understood
   - `insight`: A non-obvious discovery or pattern was identified
   - `war-story`: A debugging or investigation sequence with twists

6. **Write the capture file** with this structure:

   ```markdown
   ---
   title: "{title}"
   date: YYYY-MM-DD
   status: raw
   type: {case-study | explainer | insight | war-story}
   repos: [repos involved]
   tags: [relevant tags]
   ---

   ## What happened
   {1-3 paragraph summary of the event}

   ## Why it matters
   {Why an external audience would care — what's generalizable}

   ## Technical detail
   {Error messages, metrics, API responses, code paths — the raw evidence}

   ## Narrative arc
   - Setup: {what we were trying to do}
   - Conflict: {what went wrong or was surprising}
   - Resolution: {how we solved it}
   - Lesson: {the takeaway}
   ```

7. **Append to ideas.md.** Add a one-line cross-reference entry to `content/ideas.md`:
   ```
   - {title} (captured: YYYY-MM-DD → captures/{filename})
   ```

8. **Report.** Show the filename and a 2-line summary of what was captured.

## Rules

- Keep captures concise but complete — 200-400 lines max
- Include specific numbers (metrics before/after, error codes, line numbers)
- Reference source files by path for traceability
- Do NOT polish prose — raw capture, editorial comes later in `drafts/`
- Do NOT auto-capture without human confirmation
- Identify repos involved from file paths and git context, list in frontmatter
