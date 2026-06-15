# QRADE Release Checklist

Use this checklist before creating a GitHub release or QGIS plugin repository ZIP.

## Before Packaging

1. Run static tests:
   `py tests/test_static_checks.py`
2. Run the package readiness checker:
   `py tools/check_package_readiness.py`
3. Run QGIS runtime tests using `docs/testing_checklist.md`.
4. Test both Manual land-cover mode and Auto OSM mode where practical.
5. Remove generated outputs and caches from the release ZIP.
6. Complete `docs/metadata_publication_checklist.md` and replace metadata TODO values with real URLs and maintainer email.
7. Decide the large-file policy for the bundled PDF manual and training raster.
8. Verify the license matches `metadata.txt`.
9. Verify QGIS 3 and QGIS 4 compatibility claims are supported by actual runtime tests.
10. Confirm the plugin remains free, offline-capable in Manual mode, and usable without API keys.

## Normally Excluded From Release ZIP

- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `Result/`
- timestamped output folders such as `2026-06-01_12-30-00/`
- local virtual environments
- local IDE settings, unless intentionally tracked
- generated baseline or backup folders

## Large File Review

Review files larger than 5 MB before packaging. Decide whether they should be:

- included in the plugin ZIP;
- moved to documentation;
- published as separate sample data;
- excluded from the QGIS repository upload.

Current candidates may include the bundled PDF manual and training raster.

## Evidence To Save For Each Release

- QGIS version and operating system.
- QRADE version.
- Static test output.
- Package readiness checker output.
- Processing log from Manual mode test.
- Processing log from Auto OSM mode test, if applicable.
- Output folder listing.
- Screenshots of generated LandCover, Runout, and Risk Assessment layers.
- Notes on any warnings accepted for the release.

## Current Feature Verification Items

- Smart Assistant UI opens and can open QA/QC report, WebGIS report, output folder, BIM-ready CSV, IFC GUID mapping template, and BCF issues folder.
- Risk Assessment Values Editor opens, loads default/manual tables, locks `classification`, validates values, and saves a custom CSV under `risk_tables/`.
- QA/QC reports are generated as HTML, JSON, and CSV.
- BIM outputs are generated: BIM CSV/JSON, IFC GUID mapping template, and BCF issue package or no-high-risk README.
- Static WebGIS report opens and data bundle files exist.
- Temporal Probability Estimator works in the Smart Assistant.
- Processing temporal probability validation accepts valid inputs, blocks invalid inputs, and records diagnostics.
- Release ZIP excludes generated outputs and caches.

## Suggested Release Naming

- Git tag: `v1.0.0`
- Release title: `QRADE 1.0.0`
- Test evidence folder: `release_evidence_YYYY-MM-DD_v1.0.0`
- Release candidate ZIP: `QRADE_v1.0.0_rc1.zip`
- Final ZIP: `QRADE_v1.0.0.zip`
