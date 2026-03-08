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

Run pairwise meta-analysis on clinical trial data stored in Excel (.xlsx) files,
producing forest plots, funnel plots, heterogeneity statistics, sensitivity
analysis, and publication bias tests.

## Workflow

### Step 1: Ensure Docker Environment

The R environment runs inside Docker for reproducibility. Build the image if it
doesn't exist yet:

```bash
docker build -t meta-analysis-r <this-skill-path>/scripts/docker/
```

If Docker isn't running, ask the user to start it. Don't try to install R locally.

### Step 2: Discover Available Outcomes

Read the "Outcomes" sheet from the Excel file to see what's available:

```bash
docker run --rm -v "<excel-dir>":/data -v "<this-skill-path>/scripts/R":/scripts \
  meta-analysis-r Rscript /scripts/read_outcomes.R /data/<excel-filename>
```

This outputs JSON with each outcome's name, full_name, measure, and data_type.

### Step 3: Run the Analysis

For each selected outcome, run the R analysis inside Docker:

```bash
docker run --rm \
  -v "<excel-dir>":/data/input:ro \
  -v "<this-skill-path>/scripts/R":/scripts:ro \
  -v "<output-dir>":/data/output \
  meta-analysis-r \
  Rscript /scripts/run_pairwise_meta_analysis.R \
    --input "/data/input/<excel-filename>" \
    --sheet "<outcome-name>" \
    --measure "<measure>" \
    --data-type "<data-type>" \
    --full-name "<full-name>" \
    --output-dir "/data/output" \
    --output-format "json"
```

The `--output-format json` flag produces structured JSON output in addition to
standard text summaries and plots.

### Step 4: Present Results

After each outcome's analysis completes, read the results.json and present
the key findings:

1. **Pooled effect estimate** — point estimate, 95% CI, p-value
2. **Heterogeneity** — I², tau², Q statistic, prediction interval
3. **Forest plot** — interactive D3.js visualization from JSON data
4. **Funnel plot** — interactive D3.js visualization
5. **Sensitivity analysis** — leave-one-out results
6. **Publication bias** — Egger's test

### Step 5: Compile Output

Use the writer subagent to:
1. Assemble all outcome results into `final.json`
2. Generate `report.Rmd` for reproducibility

## Excel File Structure

See `references/data_format.md` for the complete specification.

## Statistical Methods

See `references/analysis_guide.md` for details on the statistical methods.

## Output Files

Each outcome produces:
```
figures/<outcome>/
├── forest_plot.png       # Forest plot (PNG for web display)
├── forest_plot.pdf       # Forest plot (PDF for publication)
├── funnel_plot.png       # Funnel plot
├── funnel_plot.pdf
├── sensitivity_plot.png  # Leave-one-out sensitivity analysis
├── sensitivity_plot.pdf
├── results.json          # Structured analysis results
├── summary.txt           # Human-readable summary
└── results.csv           # Study-level numerical results
```

Final outputs:
```
final.json                # Combined JSON for all outcomes (D3.js visualization)
report.Rmd                # Reproducible R Markdown report
```

## Edge Cases

- **Fewer than 2 studies**: Skip the outcome, warn the user
- **Fewer than 10 studies**: Run analysis but note Egger's test unreliability
- **Missing Outcomes sheet**: Ask for manual specification
- **Scale detection**: Auto log-transforms ratio measures on natural scale
- **Zero events**: Applies 0.5 continuity correction
