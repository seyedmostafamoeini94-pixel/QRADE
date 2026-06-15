# QRADE Known Limitations

This document records current limitations and assumptions for QRADE. It is intended to support transparent testing, publication preparation, and responsible interpretation of results.

## Current Status

QRADE is under active development and is being prepared for GitHub and eventual QGIS plugin repository publication. The plugin has improved validation and packaging checks, but runtime evidence should still be recorded before making compatibility or publication claims.

## CRS Requirements

The current workflow requires the QGIS project CRS to match the kinetic-energy raster CRS. QRADE checks this early and stops if they differ.

Auto OSM mode also requires a projected CRS in linear units because roads and railways are buffered using map units. A geographic CRS such as EPSG:4326 is not suitable for that buffering step.

## Auto OSM Limitations

Auto OSM mode depends on:

- the QuickOSM plugin;
- internet access;
- Overpass API availability;
- suitable OpenStreetMap coverage for the selected extent.

These requirements apply only to Auto OSM mode. Overpass timeouts, rate limits, incomplete OSM tagging, or very large extents can affect results.

## Offline/Manual Workflow

Manual land-cover mode is the offline-capable workflow. It can be used without QuickOSM, internet access, API keys, or cloud services when the user provides suitable local input data.

Manual land-cover input must contain a lowercase `classification` field. Classification values must match the selected risk/classification table.

Risk assessment value tables can be prepared as CSV files or created with the Smart Assistant Risk Assessment Values Editor. The editor saves custom CSVs without overwriting packaged defaults, but users still manually select the saved CSV in the Processing dialog. Automatic last-table mode is planned for a later phase.

## Input Data Assumptions

QRADE outputs are only as reliable as the input kinetic-energy raster, project CRS, land-cover/exposed-element classification, and risk-value table.

Users should verify:

- kinetic-energy raster units and CRS;
- raster resolution and spatial alignment;
- land-cover classification quality;
- suitability of exposure, worth, and vulnerability values;
- completeness of classified exposed elements in the study area.

## Risk Methodology Limitations

Risk values and vulnerability assumptions are methodology-dependent. They should be reviewed by qualified users before engineering, planning, emergency-management, or investment decisions.

Changing exposure, worth, vulnerability, or temporal-probability assumptions can materially change results.

Temporal probability diagnostics and warnings improve input review and stability checks, but they do not replace expert judgement or site-specific hazard interpretation.

## Output Interpretation

QRADE produces LandCover, Runout, Risk Assessment, `summary.json`, `summary.csv`, `qrade_bim_risk.csv`, `qrade_bim_risk.json`, and `qrade_ifc_guid_mapping_template.csv` outputs. The summary files support reporting and QA/QC, but they do not replace technical interpretation by a qualified user.

Current BIM support is limited to BIM-ready tabular risk exports, an IFC GUID mapping template, and simple file-based BCF issue export for High/Critical risk features. QRADE does not currently create or edit IFC models or write IFC property sets. BCF export does not yet include viewpoints or snapshots.

Current WebGIS support is limited to a static report and data bundle. Interactive mapping is planned for a later phase.

QRADE does not currently include AI/ML prediction, model training, or ML training export. The rule-based Smart QA/QC report supports review of warnings and output consistency, but it does not replace expert interpretation. The separate toolbar/menu Smart Assistant UI opens reports, BIM deliverables, and output folders and includes an advisory Temporal Probability Estimator. Its BIM buttons open existing deliverables only; they do not edit BIM/IFC files. It does not automatically update Processing parameters; advanced pre-run checks are planned.

Risk maps should be interpreted together with input data quality, hazard-model assumptions, local context, and uncertainty.

## QGIS Version Compatibility

`metadata.txt` currently allows installation up to QGIS 4.99 while QGIS 4 testing is in progress. Full QGIS 4 compatibility should only be claimed after runtime tests are completed and documented in `docs/qgis_runtime_test_log.md`.

## Packaging/Publication Limitations

Before official publication:

- metadata TODO placeholders must be replaced with real homepage, repository, tracker, and email values;
- QGIS 4 runtime evidence must be documented if QGIS 4 compatibility is claimed;
- generated outputs and caches must be excluded from release ZIPs;
- training/sample data and large manuals may need a separate distribution policy;
- final documentation URLs should be confirmed.

## Planned Improvements

Planned improvements include:

- result report/dashboard;
- interactive WebGIS map view;
- BIM-ready export examples and mapping guidance;
- BCF issue export;
- Smart QA/QC Assistant for input, classification, temporal probability, and output checks;
- improved documentation and examples.
