# QRADE QGIS Runtime Test Log

Use this template to record real QGIS runtime evidence for QRADE releases and compatibility claims.

## Test Session

- Test date:
- Tester:
- Operating system:
- QGIS version:
- Qt version:
- Python version:
- GDAL version:
- QRADE version:

## Install Method

- Installed plugin folder:
- ZIP install:
- ZIP path/name:
- Clean QGIS profile used: yes/no
- Notes:

## Plugin Loading Result

- Appears in Plugin Manager: pass/fail/not tested
- Toolbar/menu action appears: pass/fail/not tested
- Processing provider appears: pass/fail/not tested
- QRADE algorithm opens: pass/fail/not tested
- Screenshots/log files:
- Notes:

## Test Dataset Details

- Kinetic-energy raster path:
- Kinetic-energy raster CRS:
- QGIS project CRS:
- Land-cover mode:
- Risk table mode:
- Temporal probability mode:
- Output folder:
- Test extent/location:
- Notes:

## Test Cases

## Current Full Runtime Verification Targets

For current release candidates, verify these target areas before making compatibility or publication claims:

- successful QRADE run produces LandCover, Runout, Risk Assessment, summary files, QA/QC reports, BIM outputs, BCF export/empty-case README, and static WebGIS report/data bundle;
- Smart Assistant opens QA/QC report, WebGIS report, output folder, BIM-ready CSV, IFC GUID mapping template, and BCF issues folder;
- Risk Assessment Values Editor loads default/manual/custom tables, locks `classification`, validates values, saves custom CSV under `risk_tables/`, and saved CSV can be selected in Processing manual/custom table mode;
- Temporal Probability Estimator calculates expected values and warnings;
- Processing temporal probability validation blocks invalid inputs and records diagnostics;
- static tests show `25 passed, 0 failed`;
- package readiness has `0 FAIL`;
- ZIP validation has `5 PASS, 0 WARN, 0 FAIL`;
- current BIM support remains deliverable/export based, not IFC editing/model authoring;
- current WebGIS support remains static report/data bundle only.

### 1. Plugin Load Test

- Status: pass/fail/not tested
- Expected result: QRADE loads without Python errors and appears in Plugin Manager, toolbar/menu, and Processing Toolbox.
- Observed result:
- Screenshots/log files:
- Notes:

### 2. Manual Mode Valid Run

- Status: pass/fail/not tested
- Expected result: Manual mode accepts a valid vector/GeoPackage layer with lowercase `classification`, completes processing, and writes selected outputs.
- Observed result:
- Screenshots/log files:
- Notes:

### 3. Manual Mode Missing File Negative Test

- Status: pass/fail/not tested
- Expected result: QRADE stops early with a clear message requiring a valid manual land-cover vector/GeoPackage.
- Observed result:
- Screenshots/log files:
- Notes:

### 4. Auto OSM Small Extent Run

- Status: pass/fail/not tested
- Expected result: With QuickOSM enabled, internet available, and a projected project CRS, QRADE downloads OSM data for a small extent and completes processing.
- Observed result:
- Screenshots/log files:
- Notes:

### 5. CRS Mismatch Negative Test

- Status: pass/fail/not tested
- Expected result: QRADE stops early when project CRS and kinetic-energy raster CRS do not match.
- Observed result:
- Screenshots/log files:
- Notes:

### 6. All Outputs Disabled Negative Test

- Status: pass/fail/not tested
- Expected result: QRADE stops early with a message requiring at least one output: LandCover, Risk Assessment, or Runout.
- Observed result:
- Screenshots/log files:
- Notes:

### 7. Summary Files Check

- Status: pass/fail/not tested
- Expected result: Successful runs write `summary.json` and `summary.csv` in the timestamped output folder.
- Observed result:
- Screenshots/log files:
- Notes:

### 8. BIM-Ready Export Check

- Status: pass
- Expected result: Successful runs write `qrade_bim_risk.csv` and `qrade_bim_risk.json` in the timestamped output folder as BIM-ready tabular exports, not IFC or BCF files.
- Observed result: Runtime verification found `qrade_bim_risk.json` with 1123 records and `qrade_bim_risk.csv` with 1124 rows including the header. `ifc_guid` values were blank as expected, `asset_id` used `QRADE-<qrade_id>`, `energy_max_kj` was calculated from `energy_max_j / 1000`, and `recommended_action` plus `bcf_priority` were populated.
- Screenshots/log files:
- Notes: Example priority counts were Critical 1, High 14, Medium 119, Low 27, Info 962. Example category counts were Building 713, Transport 285, LandUse 81, Other 44.

### 8A. IFC GUID Mapping Template Check

- Status: pass
- Expected result: Successful runs write `qrade_ifc_guid_mapping_template.csv` in the timestamped output folder as a ready-to-fill mapping table, not an IFC model or IFC editing operation.
- Observed result: `qrade_ifc_guid_mapping_template.csv` existed and was generated automatically with the QRADE run. Row count matched the final risk-assessment feature count plus header. `ifc_guid` values were blank as expected, `asset_id` used `QRADE-<qrade_id>`, and `bcf_priority` plus `recommended_action` were populated.
- Screenshots/log files:
- Notes: QA/QC output inventory checked the file exists. QA/QC reported blank IFC GUID values as `INFO`, not an error, because the mapping template is meant to be completed manually after BIM/IFC review. No IFC library, BIM dependency, IFC editing, property-set writing, or model generation is involved.

### 8B. BCF Issue Export Check

- Status: pass
- Expected result: Successful runs write `bcf_issues/qrade_rockfall_risk_issues.bcfzip` when High/Critical risk features exist, using `risk_total >= 0.50` as the issue selection rule. If no High/Critical features exist, QRADE writes `bcf_issues/README_no_high_risk_issues.txt`.
- Observed result: `bcf_issues/qrade_rockfall_risk_issues.bcfzip` existed and was generated automatically with the QRADE run. The ZIP contained `bcf.version`, one folder per issue/topic UUID, and one `markup.bcf` per issue folder. The tested dataset produced 15 issues: 1 Critical and 14 High.
- Screenshots/log files:
- Notes: Each issue included title, priority, `qrade_id`, `asset_id`, classification, risk values, `energy_max_kj`, recommended action, centroid coordinates where available, and a note about future IFC GUID mapping. QA/QC output inventory checked the BCF file. Current BCF support is simple file-based issue export without viewpoints, snapshots, IFC editing, IFC model generation, or external BIM dependencies.

### 9. WebGIS Static Report Check

- Status: pass
- Expected result: Successful runs write `web_report/data/` with copied summary/BIM files, EPSG:4326/CRS84 GeoJSON files, and a static `web_report/index.html` report.
- Observed result: `web_report/data/` existed with `summary.json`, `summary.csv`, `qrade_bim_risk.json`, `qrade_bim_risk.csv`, `risk_assessment.geojson`, `landcover.geojson`, and `runout.geojson`. `web_report/index.html` existed and opened locally in a browser.
- Screenshots/log files:
- Notes: The report displayed run information, summary cards, classification counts, top 10 risk features, BIM/action summary, data file links, and a map-view-planned placeholder. Current WebGIS support is static report/data bundle only; no interactive map is included yet.

### 10. AI/ML Roadmap Note

- Status: informational
- Expected result: Current QRADE output should not include ML training export files.
- Observed result: ML training export was removed from the current roadmap. QRADE does not currently include AI/ML prediction, model training, ML dependencies, APIs, cloud services, LLMs, or Ollama features.
- Screenshots/log files:
- Notes: A future Smart QA/QC Assistant is planned for input quality, classification consistency, temporal probability settings, and output consistency checks. It should not be presented as ML.

### 11. Smart QA/QC Report Check

- Status: pass
- Expected result: Successful runs write `qa_qc/qrade_qa_qc_report.json`, `qa_qc/qrade_qa_qc_report.csv`, and `qa_qc/qrade_qa_qc_report.html`.
- Observed result: `qa_qc/` existed with all expected QA/QC report files. The HTML report opened locally and included overall status, severity counts, output inventory, classification checks, BIM checks, WebGIS checks, and temporal probability checks.
- Screenshots/log files:
- Notes: Current Smart QA/QC support is rule-based report generation and a basic report-opening UI. It is not AI/ML and does not replace expert interpretation.

### 12. Smart Assistant UI Check

- Status: pass
- Expected result: The `QRADE Smart Assistant` toolbar/menu action opens a separate dialog outside the Processing algorithm dialog.
- Observed result: New toolbar/menu action appeared. Dialog opened successfully after the close-button compatibility hotfix. Output folder selection worked. QA/QC report opened, WebGIS report opened, selected output folder opened, and BIM deliverable buttons appeared.
- Screenshots/log files:
- Notes: The UI detected `qrade_bim_risk.csv`, `qrade_ifc_guid_mapping_template.csv`, and `bcf_issues/` in the selected output folder. `Open BIM-ready CSV` opened the BIM CSV or showed a clear message if missing. `Open IFC GUID Mapping Template` opened the mapping CSV or showed a clear message if missing. `Open BCF Issues Folder` opened the folder or showed a clear message if missing, and status indicated whether a BCF package or no-high-risk README was found. The UI uses compatibility-safe PyQt widgets where possible. No Processing algorithm behavior changed.

### 12A. Risk Assessment Values Editor Check

- Status: pass
- Expected result: The `Edit Risk Assessment Values` Smart Assistant button opens `QRADE Risk Assessment Values Editor`; packaged default/template CSV files can be loaded as read-only references and edits are saved as a custom CSV.
- Observed result: Editor opened from the Smart Assistant. Default table loaded from `Input/classification_table.csv`. Manual template loaded from `Templates/classification_table_manual.csv`. Existing custom CSV loading path was available. The `classification` column was locked/read-only, numeric cell editing worked, validation detected invalid numeric and out-of-range values, save was blocked on critical validation errors, and save with warnings required confirmation.
- Screenshots/log files:
- Notes: A valid custom CSV was saved under `risk_tables/` and could be selected in QRADE Processing manual/custom table mode. Packaged default/template CSV files were not overwritten. No Processing algorithm behavior changed.

### 13. Temporal Probability Estimator Check

- Status: pass
- Expected result: The Smart Assistant Temporal Probability Estimator calculates frequency-based temporal probability using the homogeneous Poisson formula and displays warnings for weak or saturated inputs.
- Observed result: Smart Assistant opened and the Temporal Probability Estimator appeared. `N=0`, `Tobs=10`, `Tr=50` produced `P_t=0` with a zero-event warning. `N=1`, `Tobs=1`, `Tr=50` produced saturated probability close to 1 with multiple warnings. `N=3`, `Tobs=30`, `Tr=10` produced approximately lambda = 0.1/year, expected events = 1, equivalent return period = 10 years, and `P_t = 0.6321`. `N=12`, `Tobs=30`, `Tr=10` produced approximately lambda = 0.4/year, expected events = 4, equivalent return period = 2.5 years, and `P_t = 0.9817`.
- Screenshots/log files:
- Notes: The estimator is advisory only and does not change main algorithm parameters automatically.

### 14. Processing Temporal Probability Validation Check

- Status: pass
- Expected result: The main QRADE Processing algorithm validates temporal probability inputs, records diagnostics in summary metadata, and reports temporal quality/warnings in QA/QC diagnostics without changing the risk formula.
- Observed result: Valid frequency case `N=3`, `Tobs=30`, `Tr=10` was accepted and produced approximately lambda = 0.1/year, expected events = 1, equivalent return period = 10 years, and `P_t = 0.6321`. Saturated case `N=1`, `Tobs=1`, `Tr=50` produced saturated `P_t` close to 1 with warnings. Zero-event case `N=0`, `Tobs=10`, `Tr=50` produced `P_t=0` with a warning that zero observed events should not silently imply zero hazard.
- Screenshots/log files:
- Notes: Invalid event count `N=3.5` stopped with a clear integer-`N` Processing error. `Tobs=0` stopped with a clear `Tobs > 0` error. `Tr=0` stopped with a clear `Tr > 0` error. Manual `P_t=0.5` was accepted and recorded in metadata. Manual values outside `0..1` stopped with a clear probability-range error. Summary metadata includes `temporal_lambda_per_year`, `temporal_expected_events`, `temporal_equivalent_return_period_years`, `temporal_probability_quality`, and `temporal_probability_warnings`.

### 15. Clean ZIP Install Test

- Status: pass
- Expected result: `dist/Qrade-v1.0.0.zip` installs into a clean QGIS profile and QRADE loads from the installed ZIP copy.
- Observed result: Clean-profile ZIP install test completed successfully. Exact QGIS, Qt, GDAL, Python, and operating-system details should be filled in manually when available.
- Screenshots/log files:
- Notes: Keep detailed runtime fields above for the user to complete with the exact test environment.

## Known Warnings

- Metadata TODOs:
- QuickOSM/internet required only for Auto OSM mode:
- Manual mode offline-capable:
- QGIS 4 compatibility still being tested unless all relevant tests above pass:
- Other warnings:

## Final Compatibility Statement

TODO: Write the final compatibility statement only after runtime tests are completed and evidence is saved.

Suggested format:

```text
QRADE <version> was tested on QGIS <version> / Qt <version> / GDAL <version> on <OS>. Manual mode <passed/failed>. Auto OSM mode <passed/failed/not tested>. Known limitations: <summary>.
```
