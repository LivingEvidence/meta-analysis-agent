#!/usr/bin/env Rscript
#
# Generate a reproducible R Markdown report from meta-analysis results.
#
# Usage: Rscript generate_report.R --input <excel-file> --results-dir <dir> --output <report.Rmd>
#
# Reads results.json files from the results directory and generates an Rmd
# that reproduces the full analysis when knitted.

library(jsonlite)
library(optparse)

option_list <- list(
  make_option("--input", type = "character", help = "Path to the original Excel file"),
  make_option("--results-dir", type = "character", help = "Directory containing outcome result folders"),
  make_option("--output", type = "character", default = "report.Rmd", help = "Output Rmd file path")
)

opt <- parse_args(OptionParser(option_list = option_list))

if (is.null(opt$input) || is.null(opt[["results-dir"]])) {
  stop("Missing required arguments. Use --help for usage.")
}

excel_file  <- opt$input
results_dir <- opt[["results-dir"]]
output_file <- opt$output

# Find all results.json files
result_files <- list.files(results_dir, pattern = "results\\.json$", recursive = TRUE, full.names = TRUE)

if (length(result_files) == 0) {
  stop("No results.json files found in ", results_dir)
}

# Load all results
outcomes <- lapply(result_files, function(f) fromJSON(f, simplifyVector = FALSE))

# --- Generate Rmd content ---
rmd <- c(
  "---",
  "title: \"Meta-Analysis Report\"",
  sprintf("date: \"%s\"", Sys.Date()),
  "output:",
  "  html_document:",
  "    toc: true",
  "    toc_float: true",
  "    theme: cosmo",
  "---",
  "",
  "```{r setup, include=FALSE}",
  "knitr::opts_chunk$set(echo = TRUE, warning = FALSE, message = FALSE)",
  "library(meta)",
  "library(metafor)",
  "library(readxl)",
  "```",
  "",
  "# Overview",
  "",
  sprintf("This report presents the results of a pairwise meta-analysis of %d outcome(s).", length(outcomes)),
  sprintf("Source data: `%s`", basename(excel_file)),
  ""
)

for (outcome in outcomes) {
  name      <- outcome$outcome_name
  full_name <- outcome$full_name
  measure_  <- outcome$measure
  dtype     <- outcome$data_type
  is_ratio  <- measure_ %in% c("HR", "RR", "OR")

  rmd <- c(rmd,
    sprintf("# %s (%s)", full_name, measure_),
    "",
    sprintf("```{r %s}", name),
    sprintf('dat <- as.data.frame(read_excel("%s", sheet = "%s"))', excel_file, name),
    "names(dat) <- trimws(tolower(names(dat)))",
    ""
  )

  if (dtype == "pre") {
    rmd <- c(rmd,
      "# Create study labels",
      'dat$studlab <- paste(dat$study, dat$year)',
      "",
      "te <- as.numeric(dat$sm)",
      'lower_col <- if ("lower" %in% names(dat)) "lower" else "lowerci"',
      'upper_col <- if ("upper" %in% names(dat)) "upper" else "upperci"',
      "lower <- as.numeric(dat[[lower_col]])",
      "upper <- as.numeric(dat[[upper_col]])",
      ""
    )
    if (is_ratio) {
      rmd <- c(rmd,
        "# Log-transform if on natural scale",
        "if (all(te > 0, na.rm = TRUE) && all(lower > 0, na.rm = TRUE)) {",
        "  te <- log(te); lower <- log(lower); upper <- log(upper)",
        "}",
        ""
      )
    }
    rmd <- c(rmd,
      "se <- (upper - lower) / (2 * qnorm(0.975))",
      "",
      sprintf('m <- metagen(TE = te, seTE = se, studlab = dat$studlab, sm = "%s",', measure_),
      '  method.tau = "REML",',
      sprintf('  method.random.ci = if (nrow(dat) >= 5) "HK" else "classic",'),
      "  prediction = TRUE)",
      ""
    )
  } else {
    rmd <- c(rmd,
      'dat$studlab <- paste(dat$study, dat$year)',
      "",
      sprintf('m <- metabin(event.e = as.integer(dat$et), n.e = as.integer(dat$nt),'),
      "  event.c = as.integer(dat$ec), n.c = as.integer(dat$nc),",
      sprintf('  studlab = dat$studlab, sm = "%s", method = "MH",', measure_),
      '  method.tau = "REML",',
      '  method.random.ci = if (nrow(dat) >= 5) "HK" else "classic",',
      "  prediction = TRUE)",
      ""
    )
  }

  rmd <- c(rmd,
    "summary(m)",
    "```",
    "",
    sprintf("## Forest Plot - %s", full_name),
    "",
    sprintf("```{r forest_%s, fig.width=12, fig.height=max(6, nrow(dat)*0.5+3)}", name),
    sprintf('forest(m, prediction = TRUE, print.tau2 = TRUE, print.I2 = TRUE, main = "%s")', full_name),
    "```",
    "",
    sprintf("## Funnel Plot - %s", full_name),
    "",
    sprintf("```{r funnel_%s, fig.width=8, fig.height=7}", name),
    sprintf('funnel(m, main = "%s - Funnel Plot")', full_name),
    "```",
    "",
    sprintf("## Sensitivity Analysis - %s", full_name),
    "",
    sprintf("```{r sensitivity_%s, fig.width=10, fig.height=max(6, nrow(dat)*0.5+3)}", name),
    'loo <- metainf(m, pooled = "random")',
    sprintf('forest(loo, main = "%s - Leave-One-Out")', full_name),
    "```",
    "",
    sprintf("## Publication Bias - %s", full_name),
    "",
    sprintf("```{r bias_%s}", name),
    "if (m$k >= 3) {",
    '  tryCatch(print(metabias(m, method.bias = "Egger", k.min = 3)),',
    '           error = function(e) cat("Test failed:", e$message, "\\n"))',
    '  if (m$k < 10) cat("Note: Egger test may be unreliable with < 10 studies.\\n")',
    '} else { cat("Too few studies for bias test.\\n") }',
    "```",
    "",
    "---",
    ""
  )
}

rmd <- c(rmd,
  "# Session Info",
  "",
  "```{r}",
  "sessionInfo()",
  "```"
)

writeLines(rmd, output_file)
cat(sprintf("Report generated: %s\n", output_file))
