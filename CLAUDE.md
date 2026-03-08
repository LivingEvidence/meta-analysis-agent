# Meta-Analysis Visualization Agent

## Project Overview
Agent-assisted meta-analysis system for systematic reviews. Researchers upload Excel data, submit natural-language requests, and Claude Code skills drive R-based meta-analyses in Docker, producing interactive D3.js visualizations.

## Tech Stack
- Backend: FastAPI (Python 3.11+)
- Agent: Claude Agent SDK with project skills
- Statistics: R via Docker (meta, metafor packages)
- Frontend: Vanilla JS + D3.js (CDN), single-page app
- Theme: Yale/Mayo blue (#00356b)

## Directory Layout
- `app/` — FastAPI application (routers, models, agent, services, static)
- `skills/meta-analysis/` — Skill definition, R scripts, Docker
- `runs/` — Runtime output artifacts (gitignored)
- `uploads/` — User-uploaded files (gitignored)

## Running
```bash
uv sync
docker build -t meta-analysis-r skills/meta-analysis/scripts/docker/
uv run uvicorn app.main:app --reload
```

## Conventions
- The backend should keep agent configuration minimal and rely on project skills for workflow logic
- Claude Code runs with `cwd` at the project root so project settings and skills can be discovered
- R scripts output JSON + PNG + PDF
- SSE streaming for real-time agent updates to frontend
