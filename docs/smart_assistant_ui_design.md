# QRADE Smart Assistant UI Design

## Overview

The QRADE Smart Assistant UI is a separate toolbar/menu dialog for opening recent QRADE reports, reviewing last-run outputs, and estimating temporal probability. The Phase 1 dialog and Temporal Probability mini-calculator are implemented.

The Smart Assistant is a rule-based QA/QC helper. It is not AI, not machine learning, not an LLM, and not connected to APIs, cloud services, Ollama, or external services. It supports user review and does not replace expert interpretation.

## UI Concept

- Separate QRADE toolbar/menu dialog. Implemented in Phase 1.
- Dialog title: `QRADE Smart Assistant`.
- Short description: rule-based QA/QC assistant.
- Works alongside the Processing algorithm instead of changing the Processing dialog.
- Helps users find and open the latest generated QA/QC and WebGIS reports.
- Uses compatibility-safe PyQt widgets where possible for QGIS 3/QGIS 4 environments.
- Temporal probability mini-calculator is implemented for transparent parameter checking.

## First UI Version

The first UI version includes:

- button: `Open Latest QA/QC Report`;
- button: `Open Latest WebGIS Report`;
- button: `Open Latest Output Folder`;
- button: `Select QRADE Output Folder`;
- button: `Edit Risk Assessment Values`;
- BIM deliverable buttons:
  - `Open BIM-ready CSV`;
  - `Open IFC GUID Mapping Template`;
  - `Open BCF Issues Folder`;
- Temporal Probability mini-calculator;
- short note: current assistant is rule-based QA/QC, not AI/ML.

Last-run summary, classification guidance, advanced BIM links, deeper BIM validation, and pre-run checks remain planned future phases.

### BIM Deliverable Buttons

Implemented BIM deliverable buttons open existing files or folders from the selected QRADE output folder:

- `Open BIM-ready CSV`: opens `qrade_bim_risk.csv`.
- `Open IFC GUID Mapping Template`: opens `qrade_ifc_guid_mapping_template.csv`.
- `Open BCF Issues Folder`: opens `bcf_issues/`.

The dialog reports whether the BIM-ready CSV, IFC GUID mapping template, and `bcf_issues/` folder are found when a user selects an output folder. These buttons do not edit BIM/IFC files or generate BIM outputs; they only open deliverables already written by QRADE.

### Temporal Probability Mini-Calculator

Inputs:

- Number of events `N`;
- Observation period `Tobs` in years;
- Assessment/design time window `Tr` in years;
- Calculate button.

Outputs:

- `lambda = N / Tobs`;
- expected events `lambda * Tr`;
- equivalent return period `1 / lambda`;
- temporal probability `P_t = 1 - exp(-lambda * Tr)`;
- warnings based on stability rules.

## Future UI Tabs Or Sections

Potential sections:

- Last Run QA/QC;
- Temporal Probability;
- Classification Guidance;
- Risk Assessment Values Editor; implemented as a custom CSV editor;
- Output Links;
- BIM/WebGIS Links;
- Pre-run Project Checks.

## Latest Output Folder Detection

The UI should locate the latest QRADE output folder using a conservative order:

1. Prefer a stored last output folder path if added later.
2. Search likely output folders if known.
3. Recognize QRADE output folders containing `summary.json`, `qa_qc/`, or `web_report/index.html`.
4. If no folder is found, ask the user to select a QRADE output folder.

The detection logic should not scan large unrelated directories without user control.

## Open-Button Behavior

- `Open Latest QA/QC Report`: open `qa_qc/qrade_qa_qc_report.html` if found.
- `Open Latest WebGIS Report`: open `web_report/index.html` if found.
- `Open Latest Output Folder`: open the latest output folder in the file explorer.
- `Open BIM-ready CSV`: open `qrade_bim_risk.csv` if found.
- `Open IFC GUID Mapping Template`: open `qrade_ifc_guid_mapping_template.csv` if found.
- `Open BCF Issues Folder`: open `bcf_issues/` if found.
- If no output folder or report is found, show a clear message and offer manual folder selection.

## Temporal Probability Warning Rules

The mini-calculator should apply these rule-based checks:

- `N` must be an integer and `N >= 0`;
- `Tobs > 0`;
- `Tr > 0`;
- `N = 0` should not silently imply zero hazard;
- `N < 5` indicates a very limited event record;
- `N < 10` indicates a small event record;
- `Tobs < 5` indicates a very short observation period;
- `Tr > Tobs` triggers an extrapolation warning;
- `Tr > 2*Tobs` triggers a strong extrapolation warning;
- `P_t > 0.95` triggers a saturation warning;
- `P_t > 0.99` triggers an almost time-independent warning.

## Implementation Plan

1. Phase 1: add toolbar/menu action and basic PyQt dialog. Implemented.
2. Phase 2: add Temporal Probability mini-calculator. Implemented.
3. Phase 3: add BIM deliverable open buttons. Implemented.
4. Phase 4: add Risk Assessment Values Editor for validated custom CSV creation. Implemented.
5. Phase 5: add Last Run QA/QC summary.
6. Phase 6: add classification guidance and accepted class list.
7. Phase 7: add future pre-run project checks.

## Likely Files To Touch During Implementation

- `qrade_plugin.py`
- possible new `smart_assistant_dialog.py`
- possible resources/icons if already available

Avoid changing the Processing algorithm unless needed for last-output-folder tracking.

## Scope Boundaries

- Do not present the assistant as AI/ML.
- Do not add API, cloud, LLM, Ollama, or external-service dependencies.
- Do not change risk calculations or land-cover classification logic.
- Do not replace expert judgement or site-specific technical review.
