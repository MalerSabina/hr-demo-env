# README — hr-demo-env

Fictitious HR demo: Snowflake DWH + 2 Tableau dashboards + Claude chat agent. No real PII, no secrets in repo.

## Prerequisites

- Python 3.12+ (see `requirements.txt`; `requirements-snowflake.txt` for Snowflake backend)
- Node.js 18+ with `npx` — required for Tableau MCP server (`npx -v` to verify)

## Setup

```bash
cd hr-demo-env
python3 -m hr_demo_env.generator --seed 42   # builds data/*.csv + data/dev.db
```

## Run locally

```bash
PYTHONPATH=src python3 -m hr_demo_env.generator --seed 42
echo '{"tool":"turnover_by_dept","args":{"start":"2025-01-01","end":"2025-12-31"}}' \
  | HR_DB=data/dev.db python3 mcp/server.py
```

## Run with Docker

```bash
docker build -t hr-demo-env .
docker run --rm -v "$PWD/data:/app/data" hr-demo-env
```

## Test

```bash
PYTHONPATH=src python3 -m pytest tests/ -q
```

## Snowflake connection (you run this — keys never enter chat or repo)

```bash
cp .env.example .env   # fill values LOCALLY; .env is gitignored
# PAT (you already have one): set SNOWFLAKE_PAT in .env, nothing else auth-related needed.
# Alternatives (documented in .env.example): key-pair via SNOWFLAKE_PRIVATE_KEY_PATH, or password fallback.
pip install -r requirements-snowflake.txt
HR_BACKEND=snowflake python3 scripts/smoke_snowflake.py
```

Load (writes only to SNOWFLAKE_DATABASE.SNOWFLAKE_SCHEMA; aborts if HR tables hold data unless --allow-overwrite):
HR_BACKEND=snowflake python3 scripts/load_snowflake.py --confirm 'USER$SABINA_MALER.HR_DEMO'
Query live: `HR_BACKEND=snowflake PYTHONPATH=src
python3 -m hr_demo_env.agent "turnover by department last quarter?"`.
The MCP server takes the same path (`--backend snowflake`), inheriting env
from the MCP host — `.mcp.json` carries no secrets.

## Tableau (guided, manual)

1. Load with `scripts/load_snowflake.py` (see Snowflake section above); Tableau reads the loaded HR_DEMO tables.
2. Connect Tableau → Snowflake → create stored extract → build the 2 dashboard specs:
   - **Attendance Anomaly**: late arrivals, missing punches, overtime by dept/month.
   - **Retention & Turnover Risk**: exit rate by dept/tenure, hires vs exits trend.

### Tableau MCP server (Claude metadata access)

Requires Node.js 18+ (`npx -v` to verify). Credentials via `.env` only — never commit:

```bash
cp .env.example .env # fill TABLEAU_* locally; .env gitignored
npx -y @tableau/mcp-server@latest # manual check; Claude starts it via .mcp.json
```
