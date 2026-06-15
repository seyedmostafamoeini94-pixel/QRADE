# QRADE Risk Assessment Values Editor Design

## Overview

The QRADE Risk Assessment Values Editor is a planned Smart Assistant tool for viewing, validating, editing, and saving custom QRADE risk assessment value tables.

The editor should reduce mistakes caused by manual CSV editing while keeping the Processing algorithm workflow unchanged. It does not replace the QRADE Processing dialog and does not change the risk formula.

Packaged default tables remain read-only reference files. User edits are saved as custom CSV files that can be selected later in the QRADE Processing dialog using manual/custom risk-value table mode.

Phase 1 is implemented. The current editor opens from the Smart Assistant, loads default/template/custom CSV files, locks the `classification` column, validates values, and saves custom CSV files.

## Feature Definition

The editor should:

- open from the QRADE Smart Assistant;
- display QRADE risk assessment values in a table view;
- allow editing of numeric risk-value cells;
- protect classification names from accidental edits in the first version;
- validate the table before saving;
- save a valid custom CSV table to a user-controlled location;
- keep plugin default CSV files unchanged.

The first version should be local and offline. It must not use AI, ML, APIs, cloud services, LLMs, Ollama, or external services.

## First-Version UI

Smart Assistant button:

- `Edit Risk Assessment Values`

Editor dialog title:

- `QRADE Risk Assessment Values Editor`

Main UI elements:

- table view of risk assessment values;
- status and validation panel;
- clear note that default packaged tables are read-only references.

Buttons:

- `Load Default Table`
- `Load Manual Template`
- `Open Existing Custom Table`
- `Validate Table`
- `Save As Custom CSV`
- `Open Saved Folder`
- `Close`

## User Workflow

1. Open the QRADE Smart Assistant.
2. Click `Edit Risk Assessment Values`.
3. Load the default table, manual template, or an existing custom table.
4. Edit numeric risk-value cells.
5. Run validation.
6. Save a validated custom CSV.
7. In the QRADE Processing dialog, choose manual/custom risk-value table mode and select the saved CSV.

This keeps the editor as a preparation tool and keeps the Processing algorithm responsible for running the assessment.

## Table Behavior

First-version behavior:

- lock the `classification` column as read-only;
- allow editing of numeric risk-value cells;
- prevent accidental editing of class names;
- preserve the required column order where possible;
- allow sorting/filtering only if it does not risk changing saved content incorrectly.

Future advanced behavior can optionally support class editing, but that should not be included in the first implementation.

## Validation Rules

Critical validation checks:

- required columns exist;
- no missing required columns;
- no duplicate `classification` values;
- no empty `classification` values;
- `Other` class exists;
- required numeric cells are not empty;
- numeric cells contain valid numbers;
- numeric values are between 0 and 1 inclusive;
- row count is reasonable and greater than zero.

Warnings:

- unexpected extra columns are present;
- `Other` class has non-zero values;
- unusually small or unusually large row count;
- values changed from the loaded reference table, if changed-cell tracking is added later.

The validation panel should summarize results using:

- `PASS`
- `WARNING`
- `CRITICAL`

## Save Behavior

The editor must not overwrite:

- `Input/classification_table.csv`
- `Templates/classification_table_manual.csv`

Custom CSV files should be saved to:

- a user-selected folder; or
- the selected QRADE output folder under `risk_tables/` if a Smart Assistant output folder is available.

If no safe default folder is available, the editor should ask the user to choose a folder.

Suggested filename:

```text
qrade_risk_values_custom_<timestamp>.csv
```

Optional future metadata sidecar:

```text
qrade_risk_values_custom_<timestamp>.json
```

The metadata JSON could record source table, save timestamp, validation status, and changed-cell count in a future phase.

## Error Prevention

The editor should:

- validate before save;
- block saving when critical validation errors exist;
- allow saving with warnings only after clear user confirmation;
- show a validation summary before save;
- show changed-cell count if feasible in a later phase;
- clearly identify invalid rows and columns where possible.

## Integration Plan

Phase 1: Implemented.

- add Smart Assistant button and editor dialog;
- load default/manual/custom CSV tables;
- edit numeric values;
- validate table;
- save valid custom CSV;
- user manually selects saved CSV in the Processing dialog.

Phase 2:

- store the last saved custom table path in QGIS settings.

Phase 3:

- consider a Processing option such as `Last Smart Assistant custom table` if safe and useful.

Phase 2 and Phase 3 should not be implemented until Phase 1 is stable and runtime-tested.

## Likely Files For Implementation

Likely files:

- new `risk_values_editor_dialog.py`
- `smart_assistant_dialog.py`
- documentation/help/README updates

Avoid modifying `qrade_algorithm.py` in the first implementation unless a later integration phase requires it.

## Scope Boundaries

- Do not change the risk formula.
- Do not overwrite packaged default CSV files.
- Do not add AI, ML, API, cloud, LLM, Ollama, or external services.
- Do not make the editor responsible for running QRADE.
- Do not implement advanced class editing in the first version.
