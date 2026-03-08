#!/usr/bin/env Rscript
#
# Pairwise Meta-Analysis Pipeline
#
# Runs a complete meta-analysis for one outcome from an Excel file:
#   1. Read data from the specified sheet
#   2. Fit random-effects and fixed-effect models
#   3. Generate forest plot (PDF + PNG)
#   4. Generate funnel plot (PDF + PNG)
#   5. Run leave-one-out sensitivity analysis
#   6. Test for publication bias (Egger's test)
#   7. Write summary, detailed results CSV, and structured JSON

library(meta)
library(metafor)
library(readxl)
library(optparse)
library(jsonlite)

# --- Command-line arguments ---
option_list <- list(
  make_option("--input", type = "character", help = "Path to Excel file"),
  make_option("--sheet", type = "character", help = "Sheet name for this outcome"),
  make_option("--measure", type = "character", help = "Effect measure: HR, RR, OR, RD, MD, SMD"),
  make_option("--data-type", type = "character", help = "Data type: pre or raw"),
  make_option("--full-name", type = "character", default = "", help = "Full outcome name for titles"),
  make_option("--output-dir", type = "character", help = "Output directory"),
  make_option("--output-format", type = "character", default = "both",
              help = "Output format: text, json, or both (default: both)")
)

opt <- parse_args(OptionParser(option_list = option_list))

# Validate required arguments
if (is.null(opt$input) || is.null(opt$sheet) || is.null(opt$measure) ||
    is.null(opt[["data-type"]]) || is.null(opt[["output-dir"]])) {
  stop("Missing required arguments. Run with --help for usage.")
}

input_file    <- opt$input
sheet_name    <- opt$sheet
measure       <- toupper(opt$measure)
data_type     <- tolower(opt[["data-type"]])
full_name     <- ifelse(opt[["full-name"]] == "", sheet_name, opt[["full-name"]])
output_dir    <- opt[["output-dir"]]
output_format <- tolower(opt[["output-format"]])

# Create output directory
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

cat(sprintf("=== Meta-Analysis: %s (%s) ===\n", full_name, measure))
cat(sprintf("Data type: %s\n", data_type))
cat(sprintf("Input: %s, Sheet: %s\n", input_file, sheet_name))

# --- Read data ---
dat <- as.data.frame(read_excel(input_file, sheet = sheet_name))

# Clean column names (lowercase, trim whitespace)
names(dat) <- trimws(tolower(names(dat)))

# Create study label
if ("study" %in% names(dat) && "year" %in% names(dat)) {
  dat$studlab <- paste(dat$study, dat$year)
  dat$year_num <- as.integer(dat$year)
} else if ("study" %in% names(dat)) {
  dat$studlab <- dat$study
  dat$year_num <- NA_integer_
} else {
  stop("No 'study' column found in the data.")
}

cat(sprintf("Studies found: %d\n", nrow(dat)))

if (nrow(dat) < 2) {
  warning("Fewer than 2 studies. Cannot perform meta-analysis.")
  skip_msg <- sprintf("SKIPPED: %s - fewer than 2 studies (%d found).", full_name, nrow(dat))
  writeLines(skip_msg, file.path(output_dir, "summary.txt"))
  if (output_format %in% c("json", "both")) {
    write(toJSON(list(error = skip_msg, outcome_name = sheet_name, n_studies = nrow(dat)),
                 auto_unbox = TRUE, pretty = TRUE),
          file.path(output_dir, "results.json"))
  }
  quit(status = 0)
}

# --- Determine if ratio measure ---
is_ratio <- measure %in% c("HR", "RR", "OR")

# --- Fit meta-analysis model ---
if (data_type == "pre") {
  # Pre-calculated effect sizes
  lower_col <- if ("lower" %in% names(dat)) "lower" else if ("lowerci" %in% names(dat)) "lowerci" else NULL
  upper_col <- if ("upper" %in% names(dat)) "upper" else if ("upperci" %in% names(dat)) "upperci" else NULL
  if (!("sm" %in% names(dat)) || is.null(lower_col) || is.null(upper_col)) {
    stop("Pre-calculated data requires 'sm', 'lower'/'lowerci', 'upper'/'upperci' columns.")
  }

  te    <- as.numeric(dat$sm)
  lower <- as.numeric(dat[[lower_col]])
  upper <- as.numeric(dat[[upper_col]])

  # Auto-detect scale for ratio measures
  if (is_ratio && all(te > 0, na.rm = TRUE) && all(lower > 0, na.rm = TRUE)) {
    cat("Detected natural scale for ratio measure -- applying log-transform.\n")
    te    <- log(te)
    lower <- log(lower)
    upper <- log(upper)
  }

  # Back-calculate SE from CI
  se <- (upper - lower) / (2 * qnorm(0.975))

  m <- metagen(
    TE       = te,
    seTE     = se,
    studlab  = dat$studlab,
    sm       = measure,
    method.tau = "REML",
    method.random.ci = if (nrow(dat) >= 5) "HK" else "classic",
    prediction = TRUE
  )

} else if (data_type == "raw") {
  if (!all(c("et", "nt", "ec", "nc") %in% names(dat))) {
    stop("Raw data requires 'Et', 'Nt', 'Ec', 'Nc' columns.")
  }

  m <- metabin(
    event.e  = as.integer(dat$et),
    n.e      = as.integer(dat$nt),
    event.c  = as.integer(dat$ec),
    n.c      = as.integer(dat$nc),
    studlab  = dat$studlab,
    sm       = measure,
    method   = "MH",
    method.tau = "REML",
    method.random.ci = if (nrow(dat) >= 5) "HK" else "classic",
    prediction = TRUE
  )

  # Extract TE and seTE for JSON output
  te <- m$TE
  se <- m$seTE

} else {
  stop(sprintf("Unknown data_type: '%s'. Expected 'pre' or 'raw'.", data_type))
}

# --- Forest Plot (PDF + PNG) ---
cat("Generating forest plot...\n")
plot_height <- max(6, nrow(dat) * 0.5 + 3)

pdf(file.path(output_dir, "forest_plot.pdf"), width = 12, height = plot_height)
forest(m,
       sortvar = if ("year" %in% names(dat)) dat$year else NULL,
       prediction = TRUE,
       print.tau2 = TRUE,
       print.I2 = TRUE,
       leftcols = c("studlab"),
       leftlabs = c("Study"),
       main = sprintf("%s - Forest Plot", full_name))
dev.off()

png(file.path(output_dir, "forest_plot.png"), width = 1200, height = plot_height * 100, res = 100)
forest(m,
       sortvar = if ("year" %in% names(dat)) dat$year else NULL,
       prediction = TRUE,
       print.tau2 = TRUE,
       print.I2 = TRUE,
       leftcols = c("studlab"),
       leftlabs = c("Study"),
       main = sprintf("%s - Forest Plot", full_name))
dev.off()

# --- Funnel Plot (PDF + PNG) ---
cat("Generating funnel plot...\n")
pdf(file.path(output_dir, "funnel_plot.pdf"), width = 8, height = 7)
funnel(m, main = sprintf("%s - Funnel Plot", full_name))
dev.off()

png(file.path(output_dir, "funnel_plot.png"), width = 800, height = 700, res = 100)
funnel(m, main = sprintf("%s - Funnel Plot", full_name))
dev.off()

# --- Sensitivity Analysis (Leave-One-Out) ---
cat("Running leave-one-out sensitivity analysis...\n")

loo <- metainf(m, pooled = "random")

pdf(file.path(output_dir, "sensitivity_plot.pdf"), width = 10, height = plot_height)
forest(loo, main = sprintf("%s - Leave-One-Out Analysis", full_name))
dev.off()

png(file.path(output_dir, "sensitivity_plot.png"), width = 1000, height = plot_height * 100, res = 100)
forest(loo, main = sprintf("%s - Leave-One-Out Analysis", full_name))
dev.off()

# --- Publication Bias ---
cat("Testing for publication bias...\n")

bias_result <- NULL
bias_note   <- ""

if (nrow(dat) >= 3) {
  tryCatch({
    bias_result <- metabias(m, method.bias = "Egger", k.min = 3)
    if (nrow(dat) < 10) {
      bias_note <- sprintf("Only %d studies - Egger's test may be unreliable with < 10 studies.", nrow(dat))
    }
  }, error = function(e) {
    bias_note <<- sprintf("Publication bias test failed: %s", e$message)
  })
} else {
  bias_note <- "Too few studies (< 3) to test for publication bias."
}

# --- Extract leave-one-out data ---
loo_data <- list()
if (!is.null(loo)) {
  # metainf returns a meta object; extract from its data
  loo_studlabs <- loo$studlab
  loo_te <- loo$TE
  loo_lower <- loo$lower
  loo_upper <- loo$upper

  if (!is.null(loo_studlabs) && length(loo_studlabs) > 0) {
    for (i in seq_along(loo_studlabs)) {
      # Skip the "Pooled estimate" row
      if (grepl("Pooled|Overall", loo_studlabs[i], ignore.case = TRUE)) next
      entry <- list(
        excluded_study = loo_studlabs[i],
        effect = if (is_ratio) exp(loo_te[i]) else loo_te[i],
        ci_lower = if (is_ratio) exp(loo_lower[i]) else loo_lower[i],
        ci_upper = if (is_ratio) exp(loo_upper[i]) else loo_upper[i]
      )
      loo_data <- c(loo_data, list(entry))
    }
  }
}

# --- Write Summary (text) ---
if (output_format %in% c("text", "both")) {
  cat("Writing results summary...\n")

  sink(file.path(output_dir, "summary.txt"))

  cat(sprintf("META-ANALYSIS RESULTS: %s\n", full_name))
  cat(sprintf("Effect measure: %s\n", measure))
  cat(sprintf("Number of studies: %d\n", m$k))
  cat(sprintf("Model: Random-effects (REML)\n"))
  if (nrow(dat) >= 5) cat("Knapp-Hartung adjustment: Yes\n")
  cat(paste(rep("=", 60), collapse = ""), "\n\n")

  cat("RANDOM-EFFECTS MODEL\n")
  if (is_ratio) {
    cat(sprintf("  Pooled %s: %.4f (95%% CI: %.4f to %.4f)\n",
                measure, exp(m$TE.random), exp(m$lower.random), exp(m$upper.random)))
  } else {
    cat(sprintf("  Pooled %s: %.4f (95%% CI: %.4f to %.4f)\n",
                measure, m$TE.random, m$lower.random, m$upper.random))
  }
  cat(sprintf("  z = %.4f, p = %.6f\n", m$zval.random, m$pval.random))
  cat("\n")

  cat("FIXED-EFFECT MODEL (Common-effect)\n")
  if (is_ratio) {
    cat(sprintf("  Pooled %s: %.4f (95%% CI: %.4f to %.4f)\n",
                measure, exp(m$TE.common), exp(m$lower.common), exp(m$upper.common)))
  } else {
    cat(sprintf("  Pooled %s: %.4f (95%% CI: %.4f to %.4f)\n",
                measure, m$TE.common, m$lower.common, m$upper.common))
  }
  cat(sprintf("  z = %.4f, p = %.6f\n", m$zval.common, m$pval.common))
  cat("\n")

  cat("HETEROGENEITY\n")
  cat(sprintf("  tau^2 = %.4f\n", m$tau2))
  cat(sprintf("  I^2   = %.1f%%\n", m$I2))
  cat(sprintf("  H     = %.2f\n", if (is.list(m$H)) m$H$TE else m$H))
  cat(sprintf("  Q     = %.4f, df = %d, p = %.6f\n", m$Q, m$df.Q, m$pval.Q))

  if (!is.null(m$lower.predict)) {
    if (is_ratio) {
      cat(sprintf("  Prediction interval: %.4f to %.4f\n",
                  exp(m$lower.predict), exp(m$upper.predict)))
    } else {
      cat(sprintf("  Prediction interval: %.4f to %.4f\n",
                  m$lower.predict, m$upper.predict))
    }
  }
  cat("\n")

  cat("PUBLICATION BIAS\n")
  if (!is.null(bias_result)) {
    bias_pval <- bias_result$pval
    bias_stat <- bias_result$statistic
    if (!is.null(bias_pval) && length(bias_pval) > 0 && !is.na(bias_pval)) {
      cat(sprintf("  Egger's test: t = %.4f, p = %.6f\n", bias_stat, bias_pval))
      if (bias_pval < 0.10) {
        cat("  => Significant asymmetry detected (p < 0.10)\n")
      } else {
        cat("  => No significant asymmetry detected\n")
      }
    } else {
      cat("  Egger's test: could not extract results\n")
    }
  }
  if (bias_note != "") cat(sprintf("  %s\n", bias_note))
  cat("\n")

  cat("SENSITIVITY ANALYSIS (Leave-One-Out)\n")
  cat("  See sensitivity_plot.pdf for visual results.\n")

  sink()
}

# --- Write detailed CSV ---
if (data_type == "pre") {
  results_df <- data.frame(
    study   = dat$studlab,
    te      = te,
    se      = se,
    weight  = m$w.random / sum(m$w.random) * 100,
    stringsAsFactors = FALSE
  )
  if (is_ratio) {
    results_df$effect   <- exp(te)
    results_df$ci_lower <- exp(te - 1.96 * se)
    results_df$ci_upper <- exp(te + 1.96 * se)
  } else {
    results_df$effect   <- te
    results_df$ci_lower <- te - 1.96 * se
    results_df$ci_upper <- te + 1.96 * se
  }
} else {
  results_df <- data.frame(
    study    = dat$studlab,
    Et       = dat$et,
    Nt       = dat$nt,
    Ec       = dat$ec,
    Nc       = dat$nc,
    weight   = m$w.random / sum(m$w.random) * 100,
    stringsAsFactors = FALSE
  )
  # Add effect sizes
  if (is_ratio) {
    results_df$effect   <- exp(te)
    results_df$ci_lower <- exp(te - 1.96 * se)
    results_df$ci_upper <- exp(te + 1.96 * se)
  } else {
    results_df$effect   <- te
    results_df$ci_lower <- te - 1.96 * se
    results_df$ci_upper <- te + 1.96 * se
  }
}

write.csv(results_df, file.path(output_dir, "results.csv"), row.names = FALSE)

# --- Write JSON output ---
if (output_format %in% c("json", "both")) {
  cat("Writing JSON results...\n")

  # Build studies array
  studies <- list()
  for (i in 1:nrow(results_df)) {
    study_entry <- list(
      study    = results_df$study[i],
      year     = if (!is.null(dat$year_num)) dat$year_num[i] else NULL,
      effect   = results_df$effect[i],
      ci_lower = results_df$ci_lower[i],
      ci_upper = results_df$ci_upper[i],
      weight   = round(results_df$weight[i], 2),
      se       = if ("se" %in% names(results_df)) results_df$se[i] else se[i]
    )
    if (data_type == "raw") {
      study_entry$et <- as.integer(dat$et[i])
      study_entry$nt <- as.integer(dat$nt[i])
      study_entry$ec <- as.integer(dat$ec[i])
      study_entry$nc <- as.integer(dat$nc[i])
    }
    studies <- c(studies, list(study_entry))
  }

  # Build publication bias object
  pub_bias <- list(method = "Egger", statistic = NULL, p_value = NULL, note = NULL)
  if (!is.null(bias_result)) {
    pub_bias$statistic <- bias_result$statistic
    pub_bias$p_value   <- bias_result$pval
  }
  if (bias_note != "") pub_bias$note <- bias_note

  # Build prediction interval
  pred_lower <- NULL
  pred_upper <- NULL
  if (!is.null(m$lower.predict)) {
    pred_lower <- if (is_ratio) exp(m$lower.predict) else m$lower.predict
    pred_upper <- if (is_ratio) exp(m$upper.predict) else m$upper.predict
  }

  # Build the complete JSON structure
  result_json <- list(
    outcome_name = sheet_name,
    full_name    = full_name,
    measure      = measure,
    data_type    = data_type,
    is_ratio     = is_ratio,
    n_studies    = as.integer(m$k),
    studies      = studies,
    pooled_random = list(
      model    = "random",
      effect   = if (is_ratio) exp(m$TE.random) else m$TE.random,
      ci_lower = if (is_ratio) exp(m$lower.random) else m$lower.random,
      ci_upper = if (is_ratio) exp(m$upper.random) else m$upper.random,
      z_value  = m$zval.random,
      p_value  = m$pval.random
    ),
    pooled_fixed = list(
      model    = "fixed",
      effect   = if (is_ratio) exp(m$TE.common) else m$TE.common,
      ci_lower = if (is_ratio) exp(m$lower.common) else m$lower.common,
      ci_upper = if (is_ratio) exp(m$upper.common) else m$upper.common,
      z_value  = m$zval.common,
      p_value  = m$pval.common
    ),
    heterogeneity = list(
      tau2         = m$tau2,
      i2           = m$I2,
      q_statistic  = m$Q,
      q_df         = as.integer(m$df.Q),
      q_pvalue     = m$pval.Q,
      prediction_lower = pred_lower,
      prediction_upper = pred_upper
    ),
    publication_bias = pub_bias,
    leave_one_out    = loo_data,
    figures = list(
      forest_plot      = "forest_plot.png",
      funnel_plot      = "funnel_plot.png",
      sensitivity_plot = "sensitivity_plot.png"
    )
  )

  write(toJSON(result_json, auto_unbox = TRUE, pretty = TRUE, na = "null"),
        file.path(output_dir, "results.json"))
}

cat(sprintf("\nDone! Results saved to: %s\n", output_dir))
