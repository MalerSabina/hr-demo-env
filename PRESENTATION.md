# HR Demo — Presentation Brief

Everything you need to present this assignment: story, architecture, tech,
demo flow, prompt engineering, human-in-the-loop, tests, evidence, and Q&A.

## 1. The One-Minute Pitch

We built an end-to-end HR analytics product on **fictitious data**: a Snowflake
data warehouse, two Tableau Cloud dashboards, and a chat agent that answers
HR questions grounded in the same metrics the dashboards show. Same numbers
everywhere — warehouse, dashboards, chat — reproducible from one seed (`42`).

## 2. Problem → Solution

| Problem | Our answer |
|---|---|
| HR leaders can't see turnover risk or attendance strain per department | 2 dashboards: Attendance Anomaly + Retention & Turnover Risk |
| Ad-hoc questions ("which dept has highest turnover?") need an analyst | Chat agent answers from live metrics, cites its source |
| Demos need cloud creds, break in CI, leak PII | Seeded fictitious data; SQLite mirror runs everything with zero credentials |
| "Whose number is right?" (dashboard vs chat) | One logical model, two backends; documented freshness rule (§7) |

## 3. Architecture

```
[generator.py --seed 42] ──► [CSVs + SQLite dev.db]      (local, R7)
        │  (same model)
        ▼
[Snowflake TEST_SANDBOX.ASSIGNMENT_SABINA] ──extract──► [Tableau: 2 dashboards]
        ▲
[metrics.py] ◄──SQL── (either backend)
        ▲
[mcp/server.py --tools] ──► [agent.py] ──► user
```

- **R1/R3** Snowflake DDL (`sql/snowflake_ddl.sql`) is canonical; the SQLite
  schema in `generator.py` mirrors it table for table.
- **R4** Tableau reads a stored extract of the Snowflake tables.
- **R5** `metrics.py` implements the 3 metric functions; `mcp/server.py`
  exposes them (+ `list_databases`) over stdio, matching `mcp/tools.json`.
- **R6** `agent.py` routes NL questions to metric calls and answers with
  `sources[]` citations; refuses out-of-scope (e.g. salaries).
- **R7** Everything runs on SQLite with no credentials — CI, tests, local dev.

## 4. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Warehouse (prod) | Snowflake (account `PLA72994`, Azure East US 2) | Mandated target; elastic, shares/extracts |
| Dev mirror | SQLite file `data/dev.db` | Zero-creds parity, tests, CI |
| BI | Tableau Cloud + stored extract | 2 dashboards, data-driven alerts, Pulse-ready |
| Agent/MCP | Python stdlib only (`mcp/server.py`) | No dependency risk; JSON-RPC + MCP protocol |
| Snowflake backend | `snowflake-connector-python` + `cryptography` | PAT auth (verified), key-pair/PW fallback |
| Tableau metadata | Node 18 + `@tableau/mcp-server` | Claude queries workbook/view metadata |
| Packaging | Docker (`Dockerfile`), `pytest` suite | Reproducible build + green suite |

Secrets live only in local `.env` (gitignored) — never in repo, chat, or logs.

## 5. Data (fictitious, seed 42, ~2 years)

| Table | Rows | Notes |
|---|---|---|
| departments | 8 | Engineering, Sales, Support, Marketing, Finance, HR, Operations, Data |
| roles | 24 | 3 per dept (e.g. "Engineer (Data)") |
| employees | 300 | 288 active, 12 exits; manager = earliest hire per dept |
| attendance | 83,272 | Daily punches; anomalies: late >09:30, missing punch, overtime |
| leaves | 895 | vacation / sick / unpaid |
| lifecycle_events | 460 | promotion / raise / transfer (+ VARIANT details in Snowflake) |
| **Total** | **84,959** | Generator is deterministic: same seed → identical dataset |

## 6. The Two Dashboards (Tableau workbook `HR_Analytics_Demo`)

**Attendance Anomaly** — overtime by dept (bar), monthly attendance trend
(Oct 9,752 … Dec 4,402), late clock-ins by dept. Answers: burnout risk,
punctuality patterns, pipeline health.

**Retention & Turnover Risk** — active headcount by dept (Data 44, Sales 39,
Marketing 37, HR 36, Engineering 35, Finance 34, Operations 33, Support 30 =
288), exits by dept (12 total), hires over time (Dec-2024 peak 21 → Oct-2026 7).
Answers: attrition hotspots, hiring-vs-exits balance.

Both verified live via MCP (`get-view-data` + `get-view-image`).

## 7. Live Demo Script (5 minutes, in this order)

```bash
# 1. Data is real and reproducible (10s)
PYTHONPATH=src .venv/bin/python -m hr_demo_env.generator --seed 42

# 2. Tests green (10s)
PYTHONPATH=src .venv/bin/python -m pytest tests/ -q   # 30 passed

# 3. Agent answers, grounded (30s each)
PYTHONPATH=src HR_DB=data/dev.db .venv/bin/python -m hr_demo_env.agent \
  "Which department had the most overtime last year?"
# → "Overtime by department (2025): … Most: Operations (351)."

PYTHONPATH=src HR_DB=data/dev.db .venv/bin/python -m hr_demo_env.agent \
  "Compare turnover in Engineering and Sales."
# → just the two depts + highest/lowest.

PYTHONPATH=src HR_DB=data/dev.db .venv/bin/python -m hr_demo_env.agent \
  "What is the average salary in Engineering?"
# → refused (guardrail).  ← pause here, this gets questions.
```

Then open the two Tableau dashboard links (section 2 of
`DELIVERABLES_SUMMARY.html`) and show the same numbers in the charts.

## 8. Where the Agent Is Integrated in the Flow

1. **Metrics layer** — `metrics.py` is shared: the MCP server and the agent
   call the same functions, so chat answers and tool results can't diverge.
2. **MCP server** — `mcp/server.py` exposes the metrics to any MCP host
   (Claude). Per-call warehouse/database override, validated against the
   allow-list; errors return `{"ok": false}` with the message, never secrets.
3. **Chat agent** — `agent.py` (`answer_question`) is the NL front door:
   route → metric call → templated answer + `sources[]`. An optional
   `llm_client.generate(prompt)` polishes wording only; metrics and sources
   survive LLM failure by design.
4. **Tableau metadata loop** — the same Claude session that serves the agent
   queries the Tableau MCP (views, data, images) to verify dashboards show the
   same numbers the agent cites. That verification is logged in EVIDENCE.md.

## 9. Where the Human Is in the Loop

| # | Breakpoint | Trigger | On deny |
|---|---|---|---|
| H1 | Destructive ops | `rm -rf`, drop schema/table, repo delete | Do the safe alternative, log it |
| H2 | Snowflake load | `load_snowflake.py` needs `--confirm DATABASE.SCHEMA` + explicit `--allow-overwrite` to clear tables | Stay on SQLite (R7) |
| H3 | Tableau publish | Publishing extract/dashboards, sharing, alert creation | Keep local `.twbx`, log plan |

Plus: salary/PII questions are refused by the agent (guardrail, tested), and
billing/warehouse spend is fenced by the max-3-warehouses allow-list. No
autonomous agents run in this project (assessed, none needed); no model
fine-tuning (adaptation: none).

## 10. Prompt & Context Engineering (the core of your Q&A)

There is **no LLM call in the default path** — a deliberate choice. The
"prompt" is `SYSTEM_PROMPT.md` + deterministic routing code; the "context" is
exactly the metric rows for the question asked. Explain it in three layers:

**Layer 1 — Routing (no LLM, reproducible).**
Keyword router maps question → tool: turnover-family words (`turnover,
attrition, resign, quit, leaving, left, exit, departed, churn`), headcount
family, anomaly family, leave family, database-listing family. Deterministic:
same question → same tool → same answer. Demo-proof (no LLM flakiness on stage).

**Layer 2 — Context shaping (the interesting part).**
- `_resolve_range`: "last year" → prior calendar year, "last quarter" → prior
  quarter, "this year"/YTD, default quarter-to-date. The resolved span is
  printed in every answer ("Turnover by department (2025):") — the model
  never silently answers a different period than asked.
- Department grounding: whole-word match against the live `departments`
  table (regex `\b`, so "HR" doesn't match "through"). "Compare X and Y"
  filters to X and Y and reports highest + lowest.
- Anomaly rows carry `dept` (JOIN in `metrics.py`), so "overtime by
  department" ranks departments instead of dumping a blob. Agent-side limit
  5000 (vs MCP default 50) so rankings cover the whole window.
- Refusal is a first-class output: `refused: true` + one suggested answerable
  question, tested for salary probes and vague questions.

**Layer 3 — LLM hook (wiring point, not active).**
`llm_client.generate(prompt)` receives `User asked / Metric results / cite:`
and may reword only. Contract: metrics and `sources[]` are never rewritten by
the model; on LLM failure the template answer returns with a note. If asked
"why not full LLM tool-calling": determinism for the demo, zero API cost, and
the router already covers the dashboard-scoped question space; the hook exists
if the question space outgrows keywords.

## 11. Tests (30 passed)

| File | What it proves |
|---|---|
| `test_hr_demo.py` (7) | Deterministic generator, headcount > 0, turnover shape, anomaly types, bad-range rejection, manifest↔registry match, agent answers + refuses |
| `test_db.py` | SQLite default, Snowflake missing-env errors, PAT wiring, warehouse allow-list, dotenv precedence |
| `test_loader.py` | `--confirm` gate aborts before connecting; DDL comment stripping (7 statements) |
| `test_agent_nl.py` (8) | Date resolution (last year/quarter/QTD), "left"→turnover, overtime-by-dept names a dept, compare filters depts, rows carry dept, salary refused |

Run: `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q`.

## 12. Evidence (what was verified live, with results)

- Snowflake smoke: `version=10.41.101, databases=7, tables_in_schema=6`.
- Load: 84,959 rows across 6 tables; read-audit of all 7 DBs found no other
  HR data (`SNOWFLAKE_LEARNING_DB`, `SNOWFLAKE_INTELLIGENCE`, `LIFESCIENCE_CO`
  are metadata-only shells — probed read-only, nothing used).
- Dashboard 1: monthly volumes Oct 9,752 … Dec 4,402 via `get-view-data`;
  layout via `get-view-image`.
- Dashboard 2: headcount Data 44 … Support 30 (= 288); exits 12; hires curve;
  agent `get_headcount` = 288 matches Tableau sum.
- Phase 3: overtime Q&A (24 late / 4 missing / 22 overtime in sample), turnover
  (Support highest 0.031), salary refusal. Post-improvement battery re-verified
  on real data (overtime-2025 → Operations 351; late-QTD → Data 144).
- `EVIDENCE.md` holds the full decision log; `PLAN.md` tracks M1–M5.

## 13. Freshness & Alerts Status (say this before anyone asks)

- Dashboards read a stored extract (snapshot) — new Snowflake rows appear
  after extract refresh (runbook `TABLEAU_GUIDE.md` §7; daily schedule
  recommended). The agent reads Snowflake live, so intraday it can be fresher
  than the dashboards — compare timestamps first when numbers differ.
- Alerts are specified, not yet created (owner UI click-through):
  exit-rate > 0.05, overtime > 2× average, headcount drop > 5, weekly digest
  (`TABLEAU_GUIDE.md` §8).

## 14. Q&A Cheat Sheet

- *"Why keyword router instead of an LLM?"* → Determinism on stage, zero API
  cost/latency, covers the dashboard-scoped space; LLM hook exists for polish.
- *"Why both Snowflake and SQLite?"* → Snowflake is the mandated prod DWH;
  SQLite gives credential-free dev/CI with the identical model.
- *"Is the data real?"* → No — seeded fictitious (seed 42), `example.invalid`
  emails, no PII; reproducible by design.
- *"Who can see what?"* → Role `TEST_ROLE_SABINA` reads everywhere relevant,
  writes only `TEST_SANDBOX.ASSIGNMENT_SABINA`; reviewers are Viewers.
- *"Did the demo burn Snowflake credits?"* → Our session: seconds of warehouse
  time (cents). The $5 email is under investigation — role can't see billing
  views; checking the email's account locator next.
- *"Salary questions?"* → Refused by design, tested. The schema has salary, the
  agent never exposes individuals.
- *"What breaks if data grows 100×?"* → Generator scales linearly; extract
  refresh window grows (still fine at this shape); agent's 5000-row window
  would need server-side aggregation (`GROUP BY dept` in SQL) — known next step.
- *"SQLite or Snowflake SQL differences?"* → `db.py` translates `?`→`%s`;
  one `_Conn` wrapper, same `metrics.py` both backends.
