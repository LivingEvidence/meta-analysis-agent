#!/usr/bin/env Rscript
#
# SNIPPET: Read one outcome sheet from an Excel file and normalize it.
#
# This is a REFERENCE snippet. Adapt column detection to the actual data
# you observe — do not assume the columns will always match exactly.
#

library(readxl)

excel_file <- "/data/input/study.xlsx"  # replace with actual path
sheet_name <- "OS"                      # replace with actual sheet name

dat <- as.data.frame(read_excel(excel_file, sheet = sheet_name))

# Normalize column names: lowercase + trim whitespace
names(dat) <- trimws(tolower(names(dat)))

# Inspect what we got before assuming column names
cat("Columns found:", paste(names(dat), collapse = ", "), "\n")
cat("Rows:", nrow(dat), "\n")
cat("First few rows:\n")
print(head(dat, 3))

# Build study label — check which columns actually exist
if ("study" %in% names(dat) && "year" %in% names(dat)) {
  dat$studlab <- paste(dat$study, dat$year)
  dat$year_num <- as.integer(dat$year)
} else if ("study" %in% names(dat)) {
  dat$studlab <- dat$study
  dat$year_num <- NA_integer_
} else {
  # Adapt to whatever identifier column exists
  stop("No 'study' column found. Available columns: ", paste(names(dat), collapse = ", "))
}

# Remove rows where studlab is NA or empty
dat <- dat[!is.na(dat$studlab) & nchar(trimws(dat$studlab)) > 0, ]

cat("Studies after cleaning:", nrow(dat), "\n")
