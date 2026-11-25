# REGENESIS AI — Industrial Circular Economy Platform

A FastAPI + SQLAlchemy platform for industrial by-product listings, factory profiles, matching, material guidance, environmental estimates and a marketplace workflow.

> **Production status:** this repository is a deployable MVP / release candidate, not a fully validated live B2B exchange. Before commercial launch, complete the launch gates in `PRODUCTION_READINESS_AR.md` (factory verification, legal terms, privacy, email verification, monitoring, backup/restore, payment/contract workflow and industrial validation). Never present demo records or estimates as real transactions or certified environmental results.

## Quick start (Windows PowerShell)

```powershell
cd ReGenesis_AI_Professional_MVP
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a private `SECRET_KEY` in `.env` (at least 32 characters). For a clean marketplace database keep `SEED_DEMO_DATA=false`. To populate clearly synthetic demo examples for a presentation only, set `SEED_DEMO_DATA=true` before first startup.

```powershell
python app.py
```

Open `http://127.0.0.1:8000`, API docs at `/docs`, and health at `/api/health`.

## AI and internet search

- Local text model: install Ollama, pull `qwen3:4b`, and set `OLLAMA_ENABLED=true`.
- Local vision model: pull `qwen2.5vl:3b` and use the image-analysis endpoints.
- Public industrial-asset lookup: `GET /api/v1/advisor/industrial-assets?country_code=EGY&sector=manufacturing&year=2025&limit=25` queries the public Climate TRACE API (beta) without a search API key. It returns emissions asset records, not verified factory leads or contact details.
- Live general web search: configure either `WEB_SEARCH_PROVIDER=tavily` + `TAVILY_API_KEY`, or `WEB_SEARCH_PROVIDER=brave` + `BRAVE_SEARCH_API_KEY`; then set `WEB_SEARCH_ENABLED=true`.
- The advisor automatically searches the web for factory/company/current-information queries. `POST /api/v1/advisor/web-search` is also available.
- A cloud-hosted website cannot reach Ollama running on a developer's laptop. For a public service, deploy Ollama on a secured server/GPU host or connect an approved hosted inference endpoint. Do not expose Ollama's port publicly.

Web search results are external leads, not verified factory records. The assistant must show source URLs and users must independently confirm specifications, availability, contacts and legal status.

## Factory / facility data import

A CSV template is in `datasets/factories_template.csv`; data source notes and known limitations are in `datasets/README.md`.

```powershell
python scripts/import_factories.py path\to\facilities.csv --dry-run
python scripts/import_factories.py path\to\facilities.csv
```

The importer deduplicates by exact facility name and always imports records as **unverified**. It does not infer waste streams, buying demand, capacities or contacts. Do not bulk-copy a directory unless its terms permit your intended commercial use.

## Database and deployment

- Local development: SQLite.
- Production: PostgreSQL. Configure `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `ENVIRONMENT=production`, and `SEED_DEMO_DATA=false`.
- Docker Compose (API + PostgreSQL): `docker compose up --build -d` after setting `POSTGRES_PASSWORD` and `SECRET_KEY` in `.env`.
- Docker Compose with self-hosted local AI models: set `OLLAMA_ENABLED=true` and run `docker compose --profile ai up --build -d`; the first run downloads Qwen models and may take time/storage. Ollama is not exposed on a public host port.
- Render blueprint: `render.yaml`; set the allowed frontend domain in `CORS_ORIGINS` and add the chosen web-search key if enabled.
- Persistent uploads and database backups must be configured for the selected hosting provider. The container filesystem is not a backup strategy.

## Tests

```powershell
python -m pytest backend/tests/test_platform.py -v
python -m compileall -q backend scripts
```

## Important engineering boundaries

1. A facility directory entry does not mean that facility has a confirmed waste stream or wants to buy waste.
2. A material photo can support preliminary visual classification only; it cannot certify polymer grade, purity, contamination, chemical composition or safety.
3. Carbon/ESG values are indicative until factors, system boundaries, data quality and methodology are documented and independently reviewed.
4. A match is a lead for human review, not a technical approval or binding commercial offer.
5. Keep API keys, database credentials and JWT secrets outside source control.
