#!/usr/bin/env Rscript
#
# Read the Outcomes sheet from a meta-analysis Excel file and print as JSON.
# Usage: Rscript read_outcomes.R <excel-file>
#

library(readxl)
library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 1) {
  cat("Usage: Rscript read_outcomes.R <excel-file>\n", file = stderr())
  quit(status = 1)
}

excel_file <- args[1]

# Get all sheet names
all_sheets <- excel_sheets(excel_file)

# Find "Outcomes" sheet (case-insensitive)
outcomes_idx <- which(tolower(all_sheets) == "outcomes")

if (length(outcomes_idx) == 0) {
  result <- list(
    error = "No 'Outcomes' sheet found",
    available_sheets = all_sheets,
    outcomes = list()
  )
  cat(toJSON(result, auto_unbox = TRUE, pretty = TRUE))
  quit(status = 1)
}

outcomes_sheet <- all_sheets[outcomes_idx[1]]
dat <- as.data.frame(read_excel(excel_file, sheet = outcomes_sheet))

# Normalize column names
names(dat) <- trimws(tolower(names(dat)))

outcomes <- list()
for (i in 1:nrow(dat)) {
  entry <- list(
    name      = as.character(dat$name[i]),
    full_name = as.character(dat$full_name[i]),
    measure   = as.character(dat$measure[i]),
    data_type = as.character(dat$data_type[i])
  )
  outcomes <- c(outcomes, list(entry))
}

result <- list(
  outcomes   = outcomes,
  all_sheets = all_sheets
)

cat(toJSON(result, auto_unbox = TRUE, pretty = TRUE))
