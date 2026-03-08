---
name: meta-analysis
description: >
  Run pairwise meta-analysis on clinical trial data from Excel files (.xlsx).
  Use this skill whenever the user wants to perform meta-analysis, forest plots,
  funnel plots, heterogeneity assessment, sensitivity analysis, or publication
  bias testing on clinical outcomes data. Also trigger when the user mentions
  systematic review data analysis, pooled effect estimates, or meta-analytic
  methods like random-effects models. The skill handles both pre-calculated
  effect sizes and raw binary event count data. It uses R (via Docker) with
  the `meta` and `metafor` packages for statistical computation.
---

# Pairwise Meta-Analysis

You are a coding agent. Your job is to understand the data, write appropriate R
code, run it in the Docker environment, debug any errors, and produce a
`final.json` that the frontend can render as interactive visualizations.

**Do not use the R snippets as ready-to-run scripts.** They are references
showing how individual pieces work. You write the actual R code based on what
you observe in the data.

---

## Docker Environment

**Image:** `meta-analysis-r`
**Available R packages:** `meta`, `metafor`, `readxl`, `jsonlite`, `optparse`

### Running R code in Docker

Write your R script to the output directory, then execute it:

```bash
docker run --rm \
  -v "<absolute-excel-dir>":/data/input:ro \
  -v "<absolute-output-dir>":/workspace \
  meta-analysis-r \
  Rscript /workspace/analysis.R
```

Mount conventions:
- Excel file directory → `/data/input/` (read-only)
- Run output directory → `/workspace/` (read-write: write scripts here, read results here)

**Always use absolute paths for volume mounts.**

---

## Step-by-Step Workflow

### 1. Ensure the Docker image exists

```bash
docker images meta-analysis-r --format "{{.Repository}}"
# If not present:
docker build -t meta-analysis-r <skill-path>/scripts/docker/
```

### 2. Discover available outcomes

Write and run a short R script to read the Outcomes sheet:

```bash
docker run --rm \
  -v "<excel-dir>":/data/input:ro \
  -v "<output-dir>":/workspace \
  meta-analysis-r \
  Rscript /scripts/read_outcomes.R /data/input/<filename>
```

Reference: `snippets/read_outcomes.R`

If there is no Outcomes sheet, inspect the Excel sheet names and ask the user
which sheets to analyse, or infer from the user's request.

### 3. Inspect the data before writing analysis code

For each outcome to analyse, **first inspect the actual data**:
- Column names (they may differ from the spec)
- Data types and any obviously wrong values
- Number of studies
- Presence of zero-event rows

Write a short diagnostic R script to print column names and the first few rows.
This prevents column-mismatch errors downstream.

### 4. Write tailored R analysis code

Based on what you observed:

- Use `snippets/fit_metabin.R` as reference for raw binary data (`data_type = "raw"`)
- Use `snippets/fit_metagen.R` as reference for pre-calculated effect sizes (`data_type = "pre"`)
- Use `snippets/plots.R` as reference for forest / funnel / sensitivity plots
- Use `snippets/output_json.R` as reference for building the results JSON

**Write a single R script per outcome** (e.g. `analysis_OS.R`) that:
1. Reads and cleans the data
2. Fits the model
3. Generates plots
4. Writes `results.json` to `/workspace/figures/<outcome>/`

Save the script itself to the output directory so it's reproducible.

### 5. Run the script and handle errors

```bash
docker run --rm \
  -v "<excel-dir>":/data/input:ro \
  -v "<output-dir>":/workspace \
  meta-analysis-r \
  Rscript /workspace/analysis_OS.R 2>&1
```

If the exit code is non-zero:
- Read stderr carefully
- Diagnose the root cause (column not found, wrong data type, insufficient studies, etc.)
- Fix the R script
- Re-run

Common errors and fixes:
| Error | Fix |
|---|---|
| `object 'xxx' not found` | Column name mismatch — inspect actual names and adapt |
| `non-numeric argument` | Coerce with `as.numeric()` / `as.integer()` |
| `less than 2 studies` | Skip this outcome, write a placeholder entry in final.json |
| Package error | The image has `meta`, `metafor`, `readxl`, `jsonlite` — no others |

### 6. Assemble final.json

After all outcomes are processed, assemble `final.json` in the output directory.
Follow the schema in `references/final_json_schema.md` **exactly**.

Key points:
- All effect estimates (`effect`, `ci_lower`, `ci_upper`) must be on the **natural scale** for ratio measures — i.e. HR=0.72, not log(HR)=-0.33
- Include `session_id` and `request_id` from the run context provided in the prompt
- Outcomes that were skipped (< 2 studies) should still appear with `"studies": []` and `"pooled_random": null`, with an `"interpretation"` explaining why

---

## Output Structure

All outputs go in the run output directory provided in the prompt:

```
<output-dir>/
├── analysis_OS.R             # R script you wrote
├── analysis_PFS.R
├── figures/
│   ├── OS/
│   │   ├── forest_plot.png
│   │   ├── forest_plot.pdf
│   │   ├── funnel_plot.png
│   │   ├── funnel_plot.pdf
│   │   ├── sensitivity_plot.png
│   │   ├── sensitivity_plot.pdf
│   │   └── results.json
│   └── PFS/
│       └── ...
└── final.json                # Combined JSON for all outcomes (required)
```

---

## Reference Documents

- `snippets/read_outcomes.R` — reading the Outcomes index sheet
- `snippets/read_excel.R` — reading and normalizing a data sheet
- `snippets/fit_metabin.R` — fitting a model with raw binary data
- `snippets/fit_metagen.R` — fitting a model with pre-calculated effect sizes
- `snippets/plots.R` — generating forest / funnel / sensitivity plots
- `snippets/output_json.R` — assembling results.json per outcome
- `references/final_json_schema.md` — **required output schema for final.json**
- `references/analysis_guide.md` — statistical method details
- `references/data_format.md` — Excel file format specification
