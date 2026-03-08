#!/usr/bin/env Rscript
#
# SNIPPET: Assemble results.json for one outcome, following final_json_schema.md.
#
# Assumes the following variables are already defined:
#   m           — fitted meta object (from metabin or metagen)
#   loo         — metainf leave-one-out object
#   dat         — cleaned data frame with studlab, year_num columns
#   measure     — effect measure string, e.g. "HR"
#   is_ratio    — logical
#   sheet_name  — short outcome name, e.g. "OS"
#   full_name   — full outcome name, e.g. "Overall Survival"
#   data_type   — "pre" or "raw"
#   output_dir  — directory to write results.json
#   bias_result — metabias result or NULL
#   bias_note   — string note about bias test
#
# All effect estimates are reported on the NATURAL scale (not log).
# This is what the frontend expects per final_json_schema.md.
#

library(jsonlite)
library(meta)

to_natural <- function(x) if (is_ratio) exp(x) else x

# --- Study-level results ---
studies <- lapply(seq_len(nrow(dat)), function(i) {
  entry <- list(
    study    = dat$studlab[i],
    year     = if (!is.na(dat$year_num[i])) as.integer(dat$year_num[i]) else NULL,
    effect   = to_natural(m$TE[i]),
    ci_lower = to_natural(m$TE[i] - 1.96 * m$seTE[i]),
    ci_upper = to_natural(m$TE[i] + 1.96 * m$seTE[i]),
    weight   = round(m$w.random[i] / sum(m$w.random) * 100, 2),
    se       = m$seTE[i]   # always on log scale for ratio, raw for absolute
  )
  # For raw data, also include event counts if present
  if (data_type == "raw") {
    if ("et" %in% names(dat)) entry$et <- as.integer(dat$et[i])
    if ("nt" %in% names(dat)) entry$nt <- as.integer(dat$nt[i])
    if ("ec" %in% names(dat)) entry$ec <- as.integer(dat$ec[i])
    if ("nc" %in% names(dat)) entry$nc <- as.integer(dat$nc[i])
  }
  entry
})

# --- Pooled estimates ---
pooled_random <- list(
  model    = "random",
  effect   = to_natural(m$TE.random),
  ci_lower = to_natural(m$lower.random),
  ci_upper = to_natural(m$upper.random),
  z_value  = m$zval.random,
  p_value  = m$pval.random
)

pooled_fixed <- list(
  model    = "fixed",
  effect   = to_natural(m$TE.common),
  ci_lower = to_natural(m$lower.common),
  ci_upper = to_natural(m$upper.common),
  z_value  = m$zval.common,
  p_value  = m$pval.common
)

# --- Heterogeneity ---
heterogeneity <- list(
  tau2             = m$tau2,
  i2               = m$I2,
  q_statistic      = m$Q,
  q_df             = as.integer(m$df.Q),
  q_pvalue         = m$pval.Q,
  prediction_lower = if (!is.null(m$lower.predict)) to_natural(m$lower.predict) else NULL,
  prediction_upper = if (!is.null(m$upper.predict)) to_natural(m$upper.predict) else NULL
)

# --- Publication Bias ---
pub_bias <- list(method = "Egger", statistic = NULL, p_value = NULL, note = NULL)
if (!is.null(bias_result)) {
  pub_bias$statistic <- bias_result$statistic
  pub_bias$p_value   <- bias_result$pval
}
if (nchar(bias_note) > 0) pub_bias$note <- bias_note

# --- Leave-One-Out ---
loo_data <- list()
if (!is.null(loo) && !is.null(loo$studlab)) {
  for (i in seq_along(loo$studlab)) {
    if (grepl("Pooled|Overall", loo$studlab[i], ignore.case = TRUE)) next
    loo_data <- c(loo_data, list(list(
      excluded_study = loo$studlab[i],
      effect   = to_natural(loo$TE[i]),
      ci_lower = to_natural(loo$lower[i]),
      ci_upper = to_natural(loo$upper[i])
    )))
  }
}

# --- Assemble and write ---
result <- list(
  outcome_name     = sheet_name,
  full_name        = full_name,
  measure          = measure,
  data_type        = data_type,
  is_ratio         = is_ratio,
  n_studies        = as.integer(m$k),
  studies          = studies,
  pooled_random    = pooled_random,
  pooled_fixed     = pooled_fixed,
  heterogeneity    = heterogeneity,
  publication_bias = pub_bias,
  leave_one_out    = loo_data,
  figures = list(
    forest_plot      = "forest_plot.png",
    funnel_plot      = "funnel_plot.png",
    sensitivity_plot = "sensitivity_plot.png"
  )
)

out_path <- file.path(output_dir, "results.json")
write(toJSON(result, auto_unbox = TRUE, pretty = TRUE, na = "null"), out_path)
cat("Results written to:", out_path, "\n")
