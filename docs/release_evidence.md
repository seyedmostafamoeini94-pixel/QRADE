# QRADE Release Evidence Template

Use this template for each release candidate and final release.

## Current Validation Snapshot

- Snapshot date: 2026-06-03
- Release ZIP path/name: `dist/Qrade-v1.0.0.zip`
- Static tests: `25 passed, 0 failed`
- Package readiness: `18 PASS, 14 WARN, 0 FAIL`
- ZIP builder validation: `5 PASS, 0 WARN, 0 FAIL`
- Clean-profile QGIS ZIP install: passed
- Evidence status: validation snapshot only; official QGIS repository readiness is not complete.

### Current Publication Blockers

- `metadata.txt` still has TODO placeholders for email, homepage, repository, and tracker.
- Final GitHub URLs and maintainer email are not yet set.
- QGIS 4 final compatibility statement still needs final manual confirmation before claiming full QGIS 4 support.
- Local working folder may contain generated `Result/` and `__pycache__/` warning items; these are excluded from the release ZIP.
- WebGIS support is currently a static report/data bundle, not a full interactive web map.
- BIM support is automatic tabular/template/BCF deliverables, not IFC editing or BIM model authoring.
- Smart Assistant is rule-based QA/QC support, not AI/ML.

## Current Feature And Output Inventory

### Main QRADE outputs

- `landcover.gpkg`
- `runout.gpkg`
- `risk_assessment.gpkg`
- `summary.json`
- `summary.csv`

### QA/QC outputs

- `qa_qc/qrade_qa_qc_report.html`
- `qa_qc/qrade_qa_qc_report.json`
- `qa_qc/qrade_qa_qc_report.csv`

### BIM outputs

- `qrade_bim_risk.csv`
- `qrade_bim_risk.json`
- `qrade_ifc_guid_mapping_template.csv`
- `bcf_issues/qrade_rockfall_risk_issues.bcfzip` when High/Critical risk features exist
- `bcf_issues/README_no_high_risk_issues.txt` for no-high-risk runs

### WebGIS outputs

- `web_report/index.html`
- `web_report/data/summary.json`
- `web_report/data/summary.csv`
- `web_report/data/qrade_bim_risk.json`
- `web_report/data/qrade_bim_risk.csv`
- `web_report/data/risk_assessment.geojson`
- `web_report/data/landcover.geojson`
- `web_report/data/runout.geojson`

### Smart Assistant UI features

- opens QA/QC report;
- opens WebGIS report;
- opens selected output folder;
- includes Temporal Probability Estimator;
- opens BIM-ready CSV;
- opens IFC GUID mapping template;
- opens BCF issues folder;
- opens Risk Assessment Values Editor.

### Risk Assessment Values Editor evidence

- loads default table;
- loads manual template;
- locks `classification`;
- validates values;
- saves custom CSV under `risk_tables/`;
- saved CSV can be selected manually in Processing manual/custom table mode.

## BIM-Ready Export Verification Snapshot

- Evidence type: runtime output verification
- Current BIM support: tabular BIM-ready export only; not IFC or BCF export.
- Main generated outputs existed:
  - `landcover.gpkg`
  - `runout.gpkg`
  - `risk_assessment.gpkg`
  - `summary.json`
  - `summary.csv`
  - `qrade_bim_risk.csv`
  - `qrade_bim_risk.json`
- `summary.json` reported:
  - `feature_count`: 1123
  - `non_null_risk_total_count`: 1123
  - `null_risk_total_count`: 0
  - `max_risk_total`: 0.78
- BIM export verification:
  - `qrade_bim_risk.json` records: 1123
  - `qrade_bim_risk.csv` rows: 1124 including header
  - `ifc_guid` values are blank as expected
  - `asset_id` uses `QRADE-<qrade_id>`
  - `energy_max_kj` is calculated from `energy_max_j / 1000`
  - `recommended_action` is populated
  - `bcf_priority` is populated
- Example BIM priority counts:
  - Critical: 1
  - High: 14
  - Medium: 119
  - Low: 27
  - Info: 962
- Example BIM category counts:
  - Building: 713
  - Transport: 285
  - LandUse: 81
  - Other: 44

## IFC GUID Mapping Template Verification Snapshot

- Evidence type: runtime output verification.
- Current support: ready-to-fill CSV mapping template only; no IFC editing, IFC property-set writing, IFC model generation, or BIM dependency.
- `qrade_ifc_guid_mapping_template.csv` existed in the timestamped output folder.
- The file was generated automatically with the QRADE run after the final risk assessment and BIM-ready export.
- Row count matched the final risk-assessment feature count plus header.
- `ifc_guid` values were blank as expected.
- `asset_id` values used `QRADE-<qrade_id>`.
- `bcf_priority` and `recommended_action` values were populated from `risk_total`.
- QA/QC output inventory checked that `qrade_ifc_guid_mapping_template.csv` existed.
- QA/QC reported blank IFC GUID values as `INFO`, not an error, because the template is intended for later manual BIM/IFC mapping.

## BCF Issue Export Verification Snapshot

- Evidence type: runtime output verification.
- Current support: simple file-based BCF issue export only; no IFC editing, IFC model generation, IFC property-set writing, IfcOpenShell dependency, or external BIM dependency.
- `bcf_issues/qrade_rockfall_risk_issues.bcfzip` existed in the timestamped output folder when High/Critical risk features existed.
- The BCF issue package was generated automatically with the QRADE run.
- BCF issue selection rule: `risk_total >= 0.50`.
- BCF ZIP structure was verified to contain:
  - `bcf.version`;
  - one folder per issue/topic UUID;
  - one `markup.bcf` file per issue folder.
- Tested dataset issue counts:
  - Total issues: 15
  - Critical: 1
  - High: 14
- Each issue included:
  - title;
  - priority;
  - `qrade_id`;
  - `asset_id`;
  - classification;
  - risk values;
  - `energy_max_kj`;
  - recommended action;
  - centroid coordinates where available;
  - note about future IFC GUID mapping using `qrade_ifc_guid_mapping_template.csv`.
- QA/QC output inventory checked `bcf_issues/qrade_rockfall_risk_issues.bcfzip`.
- Empty-case behavior: if no High/Critical risk features exist, QRADE writes `bcf_issues/README_no_high_risk_issues.txt`.
- Current BCF export does not include viewpoints or snapshots.

## WebGIS Report Verification Snapshot

- Evidence type: runtime output verification
- Current WebGIS support: static report/data bundle only; interactive map view is planned later.
- `web_report/data/` existed.
- WebGIS data files existed:
  - `summary.json`
  - `summary.csv`
  - `qrade_bim_risk.json`
  - `qrade_bim_risk.csv`
  - `risk_assessment.geojson`
  - `landcover.geojson`
  - `runout.geojson`
- `web_report/index.html` existed.
- `index.html` opened locally in a browser.
- The report displayed:
  - run information;
  - summary cards;
  - classification counts;
  - top 10 risk features;
  - BIM/action summary;
  - data file links;
  - map-view-planned placeholder.
- GeoJSON files are EPSG:4326/CRS84 suitable for future web map use.

## Smart QA/QC Report Verification Snapshot

- Evidence type: runtime output verification
- Current Smart QA/QC support: rule-based QA/QC report generation only; no AI/ML, API, cloud, LLM, or Ollama feature.
- `qa_qc/` folder existed.
- QA/QC report files existed:
  - `qrade_qa_qc_report.json`
  - `qrade_qa_qc_report.csv`
  - `qrade_qa_qc_report.html`
- `qrade_qa_qc_report.html` opened locally in a browser.
- Report included:
  - overall status;
  - severity counts;
  - output inventory;
  - classification checks;
  - BIM checks;
  - WebGIS checks;
  - temporal probability checks.
- Smart Assistant UI Phase 1 is implemented as a separate toolbar/menu dialog.

## Smart Assistant UI Verification Snapshot

- Evidence type: runtime UI verification
- New `QRADE Smart Assistant` toolbar/menu action appeared.
- Dialog opened after replacing `QDialogButtonBox.Close` with a compatibility-safe `QPushButton` close button.
- Output folder selection worked.
- QA/QC report opened from the selected output folder.
- WebGIS report opened from the selected output folder.
- Selected output folder opened in the system file explorer.
- BIM-ready CSV was detected in the selected output folder.
- IFC GUID mapping template was detected in the selected output folder.
- `bcf_issues/` folder was detected in the selected output folder.
- `Open BIM-ready CSV` opened `qrade_bim_risk.csv`; if missing, the dialog shows a clear message.
- `Open IFC GUID Mapping Template` opened `qrade_ifc_guid_mapping_template.csv`; if missing, the dialog shows a clear message.
- `Open BCF Issues Folder` opened `bcf_issues/`; if missing, the dialog shows a clear message. The status area reports whether a BCF package or no-high-risk README was found.
- Temporal Probability Estimator appeared in the Smart Assistant dialog.
- Risk Assessment Values Editor opened from the Smart Assistant using `Edit Risk Assessment Values`.
- Default table loaded from `Input/classification_table.csv`.
- Manual template loaded from `Templates/classification_table_manual.csv`.
- Existing custom CSV loading path was available.
- `classification` column was locked/read-only.
- Numeric cell editing worked.
- Validation detected invalid numeric and out-of-range values.
- Save was blocked when critical validation errors existed.
- Save with warnings required confirmation.
- Valid custom CSV saved under `risk_tables/`.
- Saved CSV could be selected in QRADE Processing manual/custom table mode.
- Test case `N=0`, `Tobs=10`, `Tr=50` produced `P_t=0` with a zero-event warning.
- Test case `N=1`, `Tobs=1`, `Tr=50` produced saturated probability close to 1 with multiple warnings.
- Test case `N=3`, `Tobs=30`, `Tr=10` produced approximately lambda = 0.1/year, expected events = 1, equivalent return period = 10 years, and `P_t = 0.6321`.
- Test case `N=12`, `Tobs=30`, `Tr=10` produced approximately lambda = 0.4/year, expected events = 4, equivalent return period = 2.5 years, and `P_t = 0.9817`.
- Estimator is advisory only and does not change main algorithm parameters automatically.
- No Processing algorithm behavior changed.
- BIM buttons open existing deliverables only; they do not edit IFC/BIM files.
- Current UI is rule-based QA/QC support only; no AI/ML, API, cloud, LLM, or Ollama feature.

## Temporal Probability Validation Verification Snapshot

- Evidence type: runtime Processing validation evidence.
- Current support: main Processing algorithm validation and diagnostics only; the risk formula was not changed.
- Helper implemented in Step 44: `_evaluate_temporal_probability(...)`.
- Valid frequency case:
  - Inputs: `N=3`, `Tobs=30`, `Tr=10`.
  - Expected/observed diagnostics: lambda approximately 0.1/year, expected events approximately 1, equivalent return period approximately 10 years, and `P_t` approximately 0.6321.
  - Run accepted and diagnostics were recorded in summary metadata.
- Saturated frequency case:
  - Inputs: `N=1`, `Tobs=1`, `Tr=50`.
  - Expected/observed result: saturated `P_t` close to 1 with warnings for limited record, short observation period, strong extrapolation, and near time-independent behavior.
- Zero-event case:
  - Inputs: `N=0`, `Tobs=10`, `Tr=50`.
  - Expected/observed result: `P_t=0` with warning that zero observed events should not silently imply zero hazard.
- Invalid event-count case:
  - Inputs: `N=3.5`, `Tobs=30`, `Tr=10`.
  - Expected/observed result: Processing stopped with a clear error requiring integer `N`.
- Invalid observation-period case:
  - Input: `Tobs=0`.
  - Expected/observed result: Processing stopped with a clear error requiring `Tobs > 0`.
- Invalid assessment/design-window case:
  - Input: `Tr=0`.
  - Expected/observed result: Processing stopped with a clear error requiring `Tr > 0`.
- Manual valid case:
  - Input: manual temporal probability `P_t=0.5`.
  - Expected/observed result: run accepted and metadata recorded the manual temporal probability value.
- Manual invalid case:
  - Input: manual temporal probability outside `0..1`.
  - Expected/observed result: Processing stopped with a clear error requiring a probability between 0 and 1.
- Summary metadata now records:
  - `temporal_lambda_per_year`;
  - `temporal_expected_events`;
  - `temporal_equivalent_return_period_years`;
  - `temporal_probability_quality`;
  - `temporal_probability_warnings`.
- QA/QC diagnostics include temporal probability quality and warnings.
- These diagnostics support review of assumptions and do not replace expert judgement.

## AI/ML Roadmap Note

- ML training export was removed from the current QRADE roadmap.
- Current QRADE outputs do not include `ml_training/` files.
- QRADE does not currently include AI/ML prediction, model training, ML dependencies, APIs, cloud services, LLMs, or Ollama features.
- QRADE includes a rule-based Smart QA/QC report and a basic Smart Assistant UI. It should not be presented as ML.

## Release Information

- Release version:
- Date:
- ZIP path/name:
- ZIP size:
- Git commit/tag:
- Prepared by:

## Automated Checks

- Static test command: `py tests/test_static_checks.py`
- Static test result:
- Package readiness command: `py tools/check_package_readiness.py`
- Package readiness result:
- ZIP structure inspection result:
- Detailed QGIS runtime evidence log: `docs/qgis_runtime_test_log.md`
- Required plugin files present:
- Excluded generated/cache files absent:

## Test Environment

- QGIS version tested:
- QGIS build/commit if available:
- Qt version:
- GDAL version:
- Python version:
- Operating system:
- Clean QGIS profile used: yes/no

## Installation Test

- Install method: install from ZIP in clean QGIS profile
- ZIP selected:
- Plugin Manager enable result:
- Plugin Manager metadata screenshot saved: yes/no
- Processing provider/toolbox screenshot saved: yes/no
- Toolbar/menu action visible: yes/no

## Baseline Run Evidence

- Test dataset:
- Project CRS:
- Kinetic-energy raster CRS:
- Output folder:
- Processing log saved: yes/no
- QGIS Log Messages saved: yes/no
- Output folder listing saved: yes/no
- Map/layer screenshot saved: yes/no

## Manual Mode Test

- Manual land-cover file:
- Manual `classification` field present: yes/no
- Risk table mode:
- Temporal probability mode:
- Result: pass/fail
- Notes/errors:

## Auto OSM Mode Test

- QuickOSM installed/enabled: yes/no
- Internet/Overpass available: yes/no
- Extent tested:
- Project CRS projected: yes/no
- Result: pass/fail/not tested
- Notes/errors:

## Negative Tests

- CRS mismatch blocked with clear message: pass/fail
- Geographic CRS blocked for Auto OSM: pass/fail
- Missing manual land-cover file blocked: pass/fail
- Bad classification table blocked: pass/fail
- All save checkboxes off blocked: pass/fail

## Output Checks

- `landcover.gpkg` created: yes/no/not selected
- `runout.gpkg` created: yes/no/not selected
- `risk_assessment.gpkg` created: yes/no/not selected
- `summary.json` created: yes/no
- `summary.csv` created: yes/no
- `qrade_bim_risk.csv` created: yes/no
- `qrade_bim_risk.json` created: yes/no
- `qrade_ifc_guid_mapping_template.csv` created: yes/no
- `bcf_issues/qrade_rockfall_risk_issues.bcfzip` created: yes/no/not needed
- `bcf_issues/README_no_high_risk_issues.txt` created: yes/no/not needed
- `web_report/index.html` created: yes/no
- `web_report/data/` files created: yes/no
- `qa_qc/qrade_qa_qc_report.html` created: yes/no
- `qa_qc/qrade_qa_qc_report.json` created: yes/no
- `qa_qc/qrade_qa_qc_report.csv` created: yes/no
- LandCover style applied: yes/no
- Runout style applied: yes/no
- RiskAssessment style applied: yes/no
- `risk_total` field exists: yes/no
- Unexpected nulls after join: yes/no

## Known Warnings And Limitations

- Metadata TODOs: email, homepage, repository, and tracker still need final values before publication.
- QGIS 4 compatibility evidence: not yet finalized; document QGIS 4 runtime testing before claiming full QGIS 4 support.
- Large file/data policy:
- Final documentation URL: not yet finalized.
- QuickOSM/Overpass limitations: Auto OSM mode requires QuickOSM, internet access, and Overpass API availability.
- Other known issues:

## Publication Blockers

- [ ] Replace metadata TODO email/homepage/repository/tracker.
- [ ] Document QGIS 4 runtime testing if `qgisMaximumVersion=4.99` remains.
- [ ] Decide official package policy for large sample data and manuals.
- [ ] Confirm final documentation/manual URL.
- [ ] Confirm license and citation information.

## Sign-Off

- Technical check completed by:
- Runtime test completed by:
- Documentation checked by:
- Approved for release: yes/no
- Date:
