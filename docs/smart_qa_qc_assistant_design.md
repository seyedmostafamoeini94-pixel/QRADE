# QRADE Smart QA/QC Assistant Design

## Overview

The Smart QA/QC Assistant is a professional rule-based quality-assurance and quality-control system for QRADE. Phase 1 report generation is implemented; stronger diagnostics and a separate Smart Assistant UI remain planned.

This feature is not AI, not machine learning, not an LLM, and not a cloud/API service. It is a deterministic expert QA/QC assistant based on transparent checks and thresholds.

## Feature Definition

The planned assistant should:

- run automatically after QRADE processing;
- evaluate input quality and methodological consistency;
- inspect classifications, temporal probability settings, risk outputs, BIM exports, and WebGIS outputs;
- produce user-readable warnings, errors, and recommendations;
- support transparent reporting and release evidence;
- not replace expert judgement.

The assistant should help users find issues and document assumptions. It should not change risk calculations or silently modify outputs.

## Planned Output Files

The assistant should write reports into a `qa_qc/` folder inside the timestamped output folder:

```text
qa_qc/
  qrade_qa_qc_report.html
  qrade_qa_qc_report.json
  qrade_qa_qc_report.csv
```

Use lowercase `qrade_...` filenames for consistency with existing QRADE exports.

## Severity Levels

Planned severity levels:

- `PASS`: check passed.
- `INFO`: useful information or non-problematic context.
- `WARNING`: issue or assumption that needs user review.
- `CRITICAL`: serious issue that may invalidate interpretation.
- `BLOCKED`: optional level for checks that should stop processing earlier.

## QA/QC Check Groups

### A. Input Checks

- Kinetic-energy raster exists and is valid.
- Raster CRS is valid.
- Project CRS is valid.
- Project CRS matches raster CRS.
- Auto OSM mode uses a projected CRS.
- Manual land-cover file exists when Manual mode is selected.
- Manual land-cover has a lowercase `classification` field.
- Classification table exists and has required columns.
- Output folder exists and is writable.
- At least one main output is selected.

### B. Classification Checks

- No null or empty `classification` values.
- All land-cover classification values exist in the classification table.
- Count of `Other`.
- Percentage of `Other`.
- High-risk features classified as `Other`.
- Rare classes with very low counts.
- Classification counts summary.
- Suspicious classes where useful, without overclaiming.

### C. Temporal Probability QA

- Manual probability is between 0 and 1.
- Frequency-based `N` is an integer and `N >= 0`.
- Observation period is greater than 0.
- Assessment/design time window is greater than 0.
- `N = 0` should not silently imply zero hazard.
- `N < 5` warning.
- `N < 10` caution.
- Observation period less than 5 years warning.
- Assessment/design time window greater than observation period warning.
- Assessment/design time window greater than 2 times observation period strong warning.
- `P_t > 0.95` saturation warning.
- `P_t > 0.99` almost time-independent warning.

Derived temporal diagnostics:

- `temporal_lambda_per_year`
- `temporal_expected_events`
- `temporal_equivalent_return_period_years`
- `temporal_probability_quality`
- `temporal_probability_warnings`

### D. Risk And Output Checks

- Risk assessment feature count.
- Null `risk_total` count.
- Min, max, mean, and sum `risk_total`.
- Top-risk feature exists.
- Features with high energy but zero risk, if detectable.
- Output files created:
  - `landcover.gpkg`
  - `runout.gpkg`
  - `risk_assessment.gpkg`
  - `summary.json`
  - `summary.csv`
  - `qrade_bim_risk.csv`
  - `qrade_bim_risk.json`
  - `web_report/index.html`
  - `web_report/data/*.geojson`
- Feature counts match between risk layer, summary, BIM export, and WebGIS GeoJSON where possible.

### E. BIM Checks

- BIM CSV/JSON files exist.
- BIM record count equals risk feature count.
- `ifc_guid` is blank at the current stage and should be filled later if BIM mapping is required.
- High/critical risk features are present in BIM export.
- Future checks for IFC GUID mapping and BCF issue export.

### F. WebGIS Checks

- `web_report/index.html` exists.
- `web_report/data/` exists.
- GeoJSON files exist.
- GeoJSON CRS is EPSG:4326/CRS84.
- Report is static and not yet an interactive map.

## Report Structure

The QA/QC report should include:

- run metadata;
- overall QA/QC status;
- score or summary counts by severity;
- check table;
- recommendations;
- temporal probability diagnostics;
- classification diagnostics;
- output inventory;
- known limitations.

## JSON Schema Concept

The JSON report should use a structured top-level object with:

- `metadata`
- `overall_status`
- `checks`
- `warnings`
- `recommendations`
- `temporal_probability_diagnostics`
- `classification_diagnostics`
- `output_inventory`

Each check should include stable identifiers and enough context for automated review or future report rendering.

## CSV Report Concept

The CSV report should contain one row per check:

- `check_id`
- `group`
- `severity`
- `status`
- `message`
- `recommendation`
- `related_file`
- `related_field`
- `related_count`

## HTML Report Concept

The HTML report should be a readable QA dashboard with:

- severity badges;
- summary cards;
- temporal probability section;
- classification section;
- output checks section;
- recommendations and limitations.

The report should be static and offline-friendly.

## Implementation Phases

1. Phase 1: write QA/QC JSON/CSV/HTML after each run using available summaries and output files. Implemented.
2. Phase 2: add stronger temporal probability diagnostics before and after calculation.
3. Phase 3: add classification review suggestions.
4. Phase 4: connect to future BIM mapping and BCF checks.
5. Phase 5: add a separate toolbar/menu Smart Assistant UI for opening reports and simple QA/QC utilities.

## Current Scope Boundary

The Smart QA/QC Assistant should remain rule-based and transparent. It should not be presented as AI/ML and should not add API, cloud, LLM, Ollama, or external-service dependencies.
