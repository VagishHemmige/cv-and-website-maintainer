# Read-only checks for the supported academic YAML adapter, not a render/layout test.
args <- commandArgs(trailingOnly = TRUE)
if (!length(args) %in% c(1L, 2L)) stop("Usage: Rscript validate.R DATA_DIRECTORY [BIBLIOGRAPHY_PATH | --no-bibliography]")
if (!requireNamespace("yaml", quietly = TRUE)) stop("The yaml package is required")
root <- normalizePath(args[[1]], mustWork = TRUE)
files <- c("abstracts", "appointments", "certifications", "education", "grants",
           "honors", "memberships", "mentoring", "projects", "service", "talks",
           "teaching", "training")
if (file.exists(file.path(root, "media.yml"))) files <- c(files, "media")
errors <- character(); warnings <- character(); records <- list()
diagnostics <- list(); context <- ""; fatal_context <- FALSE
hex <- function(x) paste(as.character(charToRaw(enc2utf8(x))), collapse = "")
err <- function(x) {
  errors <<- c(errors, x)
  diagnostics[[length(diagnostics) + 1L]] <<- list(message = x, context = context, fatal = fatal_context)
}
warn <- function(x) warnings <<- c(warnings, x)
scalar <- function(x) is.character(x) && length(x) == 1L && !is.na(x) && nzchar(trimws(x))
text_sequence <- function(x) {
  (is.list(x) && is.null(names(x)) && all(vapply(x, scalar, logical(1)))) ||
    (is.character(x) && length(x) > 0L && all(!is.na(x) & nzchar(trimws(x))))
}
valid_date <- function(x, present = FALSE, full = FALSE) {
  if (!scalar(x)) return(FALSE)
  if (identical(x, "present")) return(present && !full)
  if (!grepl("^[0-9]{4}(-[0-9]{1,2}(-[0-9]{1,2})?)?$", x)) return(FALSE)
  p <- as.integer(strsplit(x, "-", fixed = TRUE)[[1]])
  if (p[1] < 1L || (full && length(p) != 3L)) return(FALSE)
  if (length(p) >= 2L && (p[2] < 1L || p[2] > 12L)) return(FALSE)
  if (length(p) == 3L) {
    canonical <- sprintf("%04d-%02d-%02d", p[1], p[2], p[3])
    d <- suppressWarnings(tryCatch(as.Date(canonical), error = function(e) as.Date(NA)))
    if (is.na(d) || !identical(format(d, "%Y-%m-%d"), canonical)) return(FALSE)
  }
  TRUE
}
warn_date_format <- function(x, label) {
  if (!valid_date(x, present = TRUE) || identical(x, "present")) return(invisible(NULL))
  p <- as.integer(strsplit(x, "-", fixed = TRUE)[[1]])
  canonical <- paste(c(sprintf("%04d", p[1]), if (length(p) >= 2L) sprintf("%02d", p[-1])), collapse = "-")
  if (!identical(x, canonical))
    warn(paste(label, "date is not zero-padded; suggested", canonical,
               "at the same precision; review before changing source"))
}
date_bounds <- function(x) {
  p <- as.integer(strsplit(x, "-", fixed = TRUE)[[1]])
  if (length(p) == 1L) return(c(sprintf("%04d-01-01", p[1]), sprintf("%04d-12-31", p[1])))
  if (length(p) == 2L) {
    first <- as.Date(sprintf("%04d-%02d-01", p[1], p[2]))
    return(as.character(c(first, seq(first, by = "month", length.out = 2)[2] - 1)))
  }
  rep(sprintf("%04d-%02d-%02d", p[1], p[2], p[3]), 2)
}
required <- list(
  education = c("id", "institution", "degree", "degree_date", "start_date"),
  training = c("id", "institution", "role", "start_date"),
  appointments = c("id", "title", "institution", "start_date"),
  certifications = c("id", "title", "board", "specialty", "start_date"),
  memberships = c("id", "society", "start_date"),
  honors = c("id", "title", "institution", "date"),
  service = c("id", "category", "role", "start_date"),
  grants = c("id", "sponsor", "title", "role", "start_date"),
  abstracts = c("title", "authors", "meeting", "date", "type"),
  talks = c("title", "role", "venue", "date", "category"),
  teaching = c("title", "venue"),
  mentoring = c("name", "status"),
  projects = c("title", "theme", "description", "status"),
  media = c("id", "section", "title")
)
for (f in files) {
  path <- file.path(root, paste0(f, ".yml"))
  context <- paste0("file:", f); fatal_context <- TRUE
  x <- tryCatch({
    input <- rawToChar(readBin(path, "raw", n = file.info(path)$size))
    Encoding(input) <- "UTF-8"
    yaml::yaml.load(input, eval.expr = FALSE, handlers = list(seq = as.list))
  }, error = function(e) { err(paste(f, conditionMessage(e))); NULL })
  if (!is.list(x) || !is.null(names(x))) { err(paste(f, "must be a sequence")); next }
  records[[f]] <- x
  file_context <- paste(as.character(serialize(x, NULL, version = 2)), collapse = "")
  ids <- character(); signatures <- character()
  for (i in seq_along(x)) {
    r <- x[[i]]; label <- paste0(f, "[", i, "]")
    context <- paste(as.character(serialize(r, NULL, version = 2)), collapse = ""); fatal_context <- TRUE
    if (!is.list(r) || is.null(names(r)) || anyDuplicated(names(r))) {
      err(paste(label, "must be a mapping with unique keys")); next
    }
    fatal_context <- FALSE
    for (key in required[[f]]) if (!scalar(r[[key]])) err(paste(label, "requires nonblank scalar", key))
    if (!is.null(r$id)) {
      if (!scalar(r$id)) err(paste(label, "id must be text")) else ids <- c(ids, r$id)
    }
    optional_text <- c("title", "institution", "city", "state", "location", "date_text",
                       "degree", "board", "specialty", "society", "program", "sponsor",
                       "award_number", "currency", "venue", "meeting", "award", "pdf",
                       "link", "slides", "target", "description", "unit", "activity",
                       "name", "years", "current", "text", "theme", "site", "repo")
    for (key in intersect(optional_text, names(r))) if (!is.null(r[[key]]) && !scalar(r[[key]]))
      err(paste(label, key, "must be nonblank scalar text or null"))
    if (f != "mentoring" && !is.null(r$role) && !scalar(r$role)) err(paste(label, "role must be scalar text"))
    if (f == "mentoring") for (key in c("role", "level")) if (!is.null(r[[key]]) &&
        !scalar(r[[key]]) && !text_sequence(r[[key]])) err(paste(label, "invalid", key))
    for (key in intersect(c("mentees", "methods", "projects", "manuscripts", "certificates", "cv_sections"), names(r))) {
      value <- r[[key]]
      # yaml may simplify a sequence to a vector, but a scalar is not a sequence.
      if (!is.null(value) && !(is.list(value) && is.null(names(value)) &&
          all(vapply(value, scalar, logical(1)))) && !(is.character(value) && length(value) > 1L &&
          all(!is.na(value) & nzchar(trimws(value))))) err(paste(label, key, "must be a sequence of text"))
    }
    enum <- switch(f,
      abstracts = list(type = c("oral", "poster"), scope = c("international", "national", "regional", "local")),
      talks = list(category = c("invited", "conference", "grand_rounds", "teaching")),
      service = list(category = c("extramural", "intramural")),
      mentoring = list(status = c("Active", "Former")),
      projects = list(status = c("active", "completed", "paused")),
      media = list(section = c("writing", "printed_news", "video_news", "podcast")), list())
    for (key in names(enum)) if (!is.null(r[[key]]) && (!scalar(r[[key]]) || !r[[key]] %in% enum[[key]]))
      err(paste(label, "invalid", key))
    if (f == "media") {
      if (scalar(r$id) && !grepl("^[a-z][a-z0-9-]*$", r$id)) err(paste(label, "invalid stable id"))
      for (key in c("outlet", "description", "url")) if (!is.null(r[[key]]) && !scalar(r[[key]]))
        err(paste(label, key, "must be text or null"))
      if (!is.null(r$url) && scalar(r$url) && !grepl("^https://[^[:space:]]+$", r$url))
        err(paste(label, "url must be HTTPS without whitespace"))
      if (is.null(r$url) && is.null(r$embed)) err(paste(label, "requires url or embed"))
      if (!is.null(r$embed)) {
        e <- r$embed
        patterns <- c(youtube = "^https://www[.]youtube[.]com/embed/[A-Za-z0-9_-]+$",
                      apple_podcasts = "^https://embed[.]podcasts[.]apple[.]com/[^[:space:]]+$",
                      libsyn = "^https://html5-player[.]libsyn[.]com/embed/[^[:space:]]+$")
        if (!is.list(e) || is.null(names(e)) || anyDuplicated(names(e)) ||
            !setequal(names(e), c("provider", "src")) || !scalar(e$provider) ||
            !e$provider %in% names(patterns) || !scalar(e$src)) {
          err(paste(label, "embed requires supported provider and src only"))
        } else if (!grepl(patterns[[e$provider]], e$src)) err(paste(label, "embed src does not match provider"))
      }
    }
    if (f == "service" && scalar(r$category)) {
      keys <- if (r$category == "extramural") "venue" else c("activity", "institution")
      for (key in keys) if (!scalar(r[[key]])) err(paste(label, "requires nonblank scalar", key))
    }
    if (f == "grants" && (!is.numeric(r$total_support) || length(r$total_support) != 1L ||
        is.na(r$total_support) || !is.finite(r$total_support) || r$total_support < 0))
      err(paste(label, "total_support must be a nonnegative number"))
    if (!is.null(r$authors_truncated) && (!is.logical(r$authors_truncated) || length(r$authors_truncated) != 1L))
      err(paste(label, "authors_truncated must be boolean"))
    for (key in intersect(c("date", "start_date", "end_date", "degree_date"), names(r))) {
      if (is.null(r[[key]])) next
      if (!valid_date(r[[key]], present = key == "end_date",
                      full = f %in% c("abstracts", "talks") && key == "date"))
        err(paste(label, key, "invalid date/precision"))
      else warn_date_format(r[[key]], paste(label, key))
    }
    if (valid_date(r$start_date) && valid_date(r$end_date) &&
        date_bounds(r$start_date)[1] > date_bounds(r$end_date)[2])
      err(paste(label, "start_date is after end_date"))
    if (f == "teaching") {
      if (!is.list(r$dates) || !is.null(names(r$dates)) || !length(r$dates) ||
          !all(vapply(r$dates, valid_date, logical(1), full = TRUE))) {
        err(paste(label, "dates must be a nonempty sequence of full calendar dates"))
      } else {
        for (j in seq_along(r$dates))
          warn_date_format(r$dates[[j]], paste0(label, " dates[", j, "]"))
      }
      if (anyDuplicated(unlist(r$dates))) warn(paste(label, "duplicate teaching session dates"))
    }
    fields <- c("title", "name", "meeting", "venue", "role", "activity", "institution", "society", "date", "start_date", "url")
    signatures <- c(signatures, paste(vapply(fields, function(key) paste(r[[key]], collapse = "/"), character(1)), collapse = "|"))
  }
  context <- file_context; fatal_context <- FALSE
  if (anyDuplicated(ids)) err(paste(f, "duplicate ids"))
  if (anyDuplicated(signatures)) warn(paste(f, "possible duplicate records; inspect manually"))
}
project_titles <- vapply(records$projects, function(r) if (scalar(r$title)) r$title else "", character(1))
mentee_names <- vapply(records$mentoring, function(r) if (scalar(r$name)) r$name else "", character(1))
bibpath <- if (length(args) == 1L) file.path(root, "publications.bib") else if (
  identical(args[[2]], "--no-bibliography")) NULL else args[[2]]
bib <- if (!is.null(bibpath) && file.exists(bibpath)) {
  input <- rawToChar(readBin(bibpath, "raw", n = file.info(bibpath)$size))
  Encoding(input) <- "UTF-8"; input
} else NULL
for (r in records$mentoring) {
  for (title in unlist(r$projects)) if (!title %in% project_titles) warn(paste("Unmatched project:", title))
  for (key in unlist(r$manuscripts)) {
    if (is.null(bib)) warn("BibTeX unavailable; manuscript key checks incomplete")
    else if (!grepl(paste0("{", key, ","), bib, fixed = TRUE)) warn(paste("Unmatched citation key:", key))
  }
}
for (r in records$abstracts) for (name in unlist(r$mentees))
  if (!name %in% mentee_names) warn(paste("Unmatched mentee:", name))
cat("AR_VALIDATION_V1\n")
for (d in diagnostics) cat(paste("AR_ERROR", if (d$fatal) "fatal" else "record", hex(d$message), d$context, sep = "\t"), "\n", sep = "")
cat("AR_VALIDATION_END\t", length(diagnostics), "\n", sep = "")
for (x in unique(warnings)) cat("WARNING:", x, "\n")
for (x in unique(errors)) cat("ERROR:", x, "\n")
cat(length(records), "files checked;", length(unique(errors)), "errors;", length(unique(warnings)), "warnings\n")
if (length(errors)) quit(status = 1L)

