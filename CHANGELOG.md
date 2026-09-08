# Changelog

## 0.4.2 — 2026-09-08

- Fixing bug with shadowing import in path resolution

## 0.4.1 — 2026-09-07

- Fixing bug with relative paths
- Fixing COCOMO bug

## 0.4.0 — 2026-09-07

- Added coupling calculations using `nx.descendants`
- Added FTE effort estimation using COCOMO
- Added a `--min` and `--max` flag to add to pre-commit hooks

## 0.3.0 — 2026-09-04

- Separated graph construction from plotting.
- Added Maintainability Index in the 'analytics'

## 0.2.5 — 2026-08-25

Fixing erroneous Halstead metrics.

## 0.2.4 — 2026-08-20

Tidying up the README.md

### Fixed
- Polishing `README.md`

## 0.2.3 — 2026-08-19

Fixed path on Windows

### Fixed
- `Path(s.origin).as_posix()` is needed everywhere so that paths are consistent in the JSON
- also added 'utf-8' in the creation of the HTML

## 0.2.2 — 2026-08-19

Fixed typo

### Fixed
- Fixed typo in `.read_text()`

## 0.2.1 — 2026-08-19

Fixed bug with `utf-8` encoding 

### Fixed
- Fixed the encoding related bug in reading text files


## 0.2.0 — 2026-08-19

Adding a new metric

### Added
- Introduced another important Halstead metric in the report: Comprehension Time (h)
- Updated the assets to reflect the above

### Fixed
- Fixed the non-rendering images in PyPI

## 0.1.0 — 2026-08-19

Initial release.

- Halstead metrics, McCabe cyclomatic complexity and the Coleman-Oman maintainability index, per module.
- Package-level maintainability score, weighted by Katz centrality and module size.
- Interactive dependency graph (`--plot`), nodes coloured by maintainability.
- JSON output (`--json`) with per-module detail and aggregate analytics.
- `--include-only` / `--exclude` filtering, and `--absolute` to keep full paths.

