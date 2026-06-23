# Meta-Analysis Visualization Agent

An agent-assisted prototype for performing pairwise meta-analysis from structured Excel data. The system combines a skill-oriented analytic architecture, a FastAPI web service, a containerized R runtime, and interactive D3.js visualizations to help researchers run and inspect standard meta-analysis workflows through natural-language requests.

This project was developed as a feasibility prototype for supporting systematic reviews and meta-analyses (SRMAs), where researchers often need to prepare datasets, choose statistical models, assess heterogeneity, run sensitivity analyses, interpret results, and produce publication-ready visualizations.

## Overview

Systematic reviews and meta-analyses are central to evidence-based medicine, but the technical workflow often requires familiarity with statistical programming environments such as R and packages such as `meta` and `metafor`. This project explores whether a coding agent can reduce that programming burden while preserving transparency and reproducibility.

The prototype works as follows:

1. A researcher uploads a structured Excel file containing study-level outcome data.
2. The researcher submits a natural-language analysis request.
3. An orchestrator agent loads the project `meta-analysis` skill and follows its workflow.
4. The agent inspects the data, writes tailored R analysis code, runs it in Docker, debugs errors, and produces analysis artifacts.
5. The backend streams agent progress to the browser.
6. The frontend renders `final.json` as interactive forest plots, funnel plots, sensitivity analyses, and summary views.

The current implementation focuses on pairwise meta-analysis (PMA).

## Key Features

- Natural-language requests for pairwise meta-analysis
- Skill-guided agent workflow for data inspection, model fitting, plotting, and JSON assembly
- Support for pre-calculated effect sizes and raw binary event counts
- R-based statistical computation using `meta` and `metafor`
- Dockerized R runtime for reproducible execution
- Interactive D3.js forest plots, funnel plots, leave-one-out sensitivity plots, and summaries
- Downloadable analysis artifacts, including generated R scripts, plots, `final.json`, and complete run archives
- Server-sent events (SSE) for real-time agent progress updates

## Architecture

```text
User
  |
  | Upload Excel + submit natural-language request
  v
FastAPI backend
  |
  | Creates session/request run directory
  | Streams agent events via SSE
  v
Orchestrator agent
  |
  | Loads project skill
  | Inspects data
  | Writes and runs R code
  v
Dockerized R runtime
  |
  | meta / metafor analysis
  | PNG, PDF, JSON outputs
  v
final.json
  |
  v
D3.js frontend visualizations
```

The backend is intentionally thin. Most analytical logic is expressed in the project skill under `skills/meta-analysis/`, where domain-specific workflow instructions, data-format references, statistical guidance, Docker runtime files, and R snippets are kept together.

## Skill-Oriented Analytic Design

The core idea is to organize domain knowledge for meta-analysis as a reusable agent skill. The skill is a lightweight directory centered on a Markdown specification:

```text
skills/meta-analysis/
├── SKILL.md
├── references/
│   ├── analysis_guide.md
│   ├── data_format.md
│   └── final_json_schema.md
├── scripts/
│   └── docker/
│       └── Dockerfile
└── snippets/
    ├── fit_metabin.R
    ├── fit_metagen.R
    ├── output_json.R
    ├── plots.R
    ├── read_excel.R
    └── read_outcomes.R
```

`SKILL.md` defines the analysis workflow. The agent is instructed to inspect the uploaded data, select the appropriate analysis approach, write R code, execute it in the containerized runtime, debug failures, and assemble the final visualization-ready output.

The supporting references define:

- expected Excel input format
- statistical method guidance
- the required `final.json` schema used by the frontend

The R snippets are examples for common operations. They are not complete scripts; the agent uses them as references when writing run-specific analysis code.

## Repository Layout

```text
app/
  agent/          Agent orchestration and message logging
  models/         Pydantic schemas and final.json models
  routers/        FastAPI routes for upload, chat, health, and run artifacts
  services/       Excel parsing and artifact helpers
  static/         Browser UI, CSS, D3 visualization code

skills/
  meta-analysis/  Agent skill specification, references, snippets, and R Docker image

runs/             Generated runtime outputs, ignored by git
uploads/          Uploaded Excel files, ignored by git
```

## Requirements

- Python 3.11+
- `uv`
- Docker
- An Anthropic/Claude-compatible agent environment for `claude-agent-sdk`

The R environment is built as a Docker image and includes:

- `meta`
- `metafor`
- `readxl`
- `jsonlite`
- `dplyr`
- `rmarkdown`
- `optparse`

## Setup

Install Python dependencies:

```bash
uv sync
```

Build the R analysis image:

```bash
docker build -t meta-analysis-r skills/meta-analysis/scripts/docker/
```

Or with Docker Compose:

```bash
docker compose build r-env
```

Create a local environment file from the example:

```bash
cp .env.example .env
```

Then edit `.env` and fill in the required Anthropic API or Foundry credentials for your environment. The example file also defines runtime paths, the Docker image name, and agent turn limits.

## Running the App

Start the FastAPI server:

```bash
uv run uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## Input Data Format

The uploaded Excel file should contain an `Outcomes` sheet and one sheet per outcome.

The `Outcomes` sheet indexes the available analyses:

| Column | Description | Example |
| --- | --- | --- |
| `name` | Outcome sheet name | `OS` |
| `full_name` | Full outcome label | `Overall Survival` |
| `measure` | Effect measure | `HR`, `RR`, `OR`, `RD`, `MD`, `SMD` |
| `data_type` | Input data type | `pre` or `raw` |

For pre-calculated effect sizes (`data_type = "pre"`), outcome sheets typically include:

| Column | Description |
| --- | --- |
| `study` | Study identifier |
| `year` | Publication year |
| `sm` | Summary measure |
| `lower` | Lower 95% CI |
| `upper` | Upper 95% CI |
| `treatment` | Treatment arm |
| `control` | Control arm |

For raw binary event counts (`data_type = "raw"`), outcome sheets typically include:

| Column | Description |
| --- | --- |
| `study` | Study identifier |
| `year` | Publication year |
| `Et` | Events in treatment group |
| `Nt` | Total in treatment group |
| `Ec` | Events in control group |
| `Nc` | Total in control group |
| `treatment` | Treatment arm |
| `control` | Control arm |

See `skills/meta-analysis/references/data_format.md` for the full specification.

## Outputs

Each request creates a run directory:

```text
runs/<session_id>/<request_id>/
├── analysis_*.R
├── figures/
│   └── <outcome>/
│       ├── forest_plot.png
│       ├── forest_plot.pdf
│       ├── funnel_plot.png
│       ├── funnel_plot.pdf
│       ├── sensitivity_plot.png
│       ├── sensitivity_plot.pdf
│       └── results.json
├── logs/
│   └── agent.log
└── final.json
```

`final.json` is the main frontend contract. It contains study-level estimates, pooled fixed-effect and random-effects estimates, heterogeneity statistics, publication-bias results where available, leave-one-out sensitivity results, and plain-language interpretation fields.

The browser UI can download:

- `final.json`
- generated report artifacts when available
- the complete run directory as a `.zip`

## Interactive Visualization

The frontend renders analysis results using D3.js. Available views include:

- forest plot with study-level weights and pooled random-effects estimate
- funnel plot for visual assessment of small-study effects
- leave-one-out sensitivity plot
- structured summary of pooled effect, confidence interval, p-value, heterogeneity, and study count

These views are driven entirely by `final.json`, so generated outputs can be inspected independently of the agent conversation.

## Prototype Evaluation Context

This system was developed as a feasibility prototype for an agent-assisted SRMA workflow. The motivating case study is an ongoing systematic review dataset on treatments for metastatic castration-resistant prostate cancer (mCRPC), including multiple clinical trials and outcome measures.

The prototype is intended to test whether a skill-guided coding agent can:

- generate executable R workflows
- reproduce standard pairwise meta-analysis outputs
- reduce the need for manual programming
- support interpretation through interactive visualization
- preserve analysis artifacts for independent verification and reuse

## Current Limitations

- The current system assumes that structured study data have already been prepared in Excel format.
- More complex SRMA tasks, such as data extraction from publications and advanced multi-step evidence synthesis workflows, are outside the current prototype.
- Agent-driven analytical correctness requires further evaluation across larger and more diverse datasets.
- Future evaluation should include workflow completion rate, correctness of generated R code, and structured expert usability ratings.

## License

See `LICENSE`.
