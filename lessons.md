# Lessons

Rules learned from operational mistakes. Loaded at session start via hook.
Append new lessons via `/done` or manually. Keep each lesson to 1-2 lines.

---

- **Board items are claims, not ground truth.** Always cross-reference board Todo items against filesystem evidence (reports/, commits, ECOSYSTEM.md checked items) before recommending them as next tasks. (Learned: 2026-03-15, "Run 2" was stale but triage echoed it)
- **DART has two separate APIs.** OpenDartReader (JSON) = filing metadata only. dart-fss = actual document HTML/PDF content. Don't use OpenDartReader to fetch disclosure text.
- **pykrx is geo-blocked on cloud IPs.** Use FinanceDataReader (NAVER Finance backend) instead on any VPS or cloud environment.
- **Check downstream before changing shared interfaces.** krff-shell consumes ALL foundation libraries. Run its tests before declaring any foundation library change done.
- **GitHub portfolio must be live before sending hedge fund InMails.** Confirm github.com/pon00050 shows the repos. kr-enforcement-cases v1.0.0 published March 17 — check others.
- **SEIBRO API is being revised.** Do not attempt integration until end of April 2026.
- **G1 grant is deferred to 2027.** Do not reopen. Decision made March 23, 2026.
- **DOC DRIFT checks need scoped targets and meta-reference exclusions.** Grepping `$BASE/*/` picks up unrelated sibling projects. Backtick-quoted occurrences of a pattern name (e.g., `` `kr-forensic-finance` `` in documentation *about* the check) are false positives. Always scope to `ALL_REPOS` and exclude backtick/quoted references. (Learned: 2026-03-26, first DOC DRIFT scan flagged hub CLAUDE.md and non-ecosystem repos)
- **Background agents from previous sessions cannot edit sibling repos.** When spawning agents that need to write files outside the primary working directory, they will be blocked by permissions. Do the edits directly in the main session instead. (Learned: 2026-03-26, Waves 2-4 agents all blocked on Edit/Write outside the hub)
