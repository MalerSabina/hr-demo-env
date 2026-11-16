# PLAN.md — hr-demo-env

## M1 — DWH schema + generator (Phase 1)

- [x] `sql/snowflake_ddl.sql` covers R1 entities → AC: one table per DATABASE.md entity, FKs declared.
- [x] `generator.py` seeded, ≥2y span, ~300 employees → AC: same seed → identical row counts; no real PII.
- [x] SQLite load path → AC: `python -m hr_demo_env.generator --seed 42` builds `data/dev.db` with all 6 tables.

## M2 — Tableau layer (Phase 2)

- [x] Extract guide in README/Tableau section → AC: steps from Snowflake → extract → refresh.
- [x] Dashboard specs for the 2 dashboards (metrics, dimensions, filters) → AC: each spec names R4 metrics implementable from schema.

## M3 — Agent + MCP (Phase 3)

- [x] `mcp/tools.json` + `mcp/server.py` dispatch to metric functions → AC: manifest names match registry; smoke test calls each tool.
- [x] `agent.py` grounded Q&A + `SYSTEM_PROMPT.md` → AC: answers cite metric source; out-of-scope refused.
- [x] Dockerfile + requirements + scope files → AC: `docker build` succeeds; `.mcp.json` has only `hr-demo-env`.

## M4 — Verify

- [x] `pytest` green → AC: all smoke tests pass, logged in EVIDENCE.md.
- [x] EVIDENCE.md complete → AC: every decision has a reason; every verify step has command → result.

Status: M1–M4 COMPLETE 2026-11-16 — Phase 1 Snowflake load 84,959 rows verified (tables_in_schema=6); Phase 2 both dashboards live & verified (Attendance c83822a6…, Retention e64fb413…); Phase 3 agent live-verified (grounded + refusal); 22/22 pytest green.

## M5 — NL routing + runbooks (improvement 1–3, 2026-11-16)

- [x] Date-aware routing (`last year/quarter`, YTD, QTD) + dept filtering/compare + per-dept anomaly ranking → AC: battery on real data correct, salary still refused.
- [x] `tests/test_agent_nl.py` (8 tests) + `SYSTEM_PROMPT.md` synced → AC: **30/30 pytest green**.
- [x] Freshness runbook (`TABLEAU_GUIDE.md` §7) + alerts plan (§8) → AC: refresh path, lag rule, 3 alert definitions documented.
- [x] `DELIVERABLES_SUMMARY.html` share status + freshness note → AC: no stale claims.

Status: M1–M5 COMPLETE 2026-11-16 — suite 30/30; open items are UI-side only (extract schedule, 3 alerts) + `git push` (needs user token).
