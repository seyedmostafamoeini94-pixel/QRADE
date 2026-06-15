# QRADE Risk Assessment Values Editor

## Overview

The QRADE Risk Assessment Values Editor is a Smart Assistant tool for creating validated custom risk assessment value CSV files. It helps users inspect, edit, validate, and save QRADE risk-value tables without manually editing packaged CSV files.

The editor does not replace the QRADE Processing dialog. After saving a custom CSV, users still select it in the Processing dialog using manual/custom risk-value table mode.

## How to open the editor

Open:

```text
QRADE Smart Assistant > Edit Risk Assessment Values
```

The editor dialog is titled:

```text
QRADE Risk Assessment Values Editor
```

## Loading tables

The editor can load:

- default table: `Input/classification_table.csv`;
- manual template: `Templates/classification_table_manual.csv`;
- an existing custom CSV selected by the user.

The packaged default and template CSV files are read-only references in this workflow. They are loaded for viewing/editing in the dialog, but edits are saved to a new custom CSV file.

## Editing rules

- The `classification` column is locked/read-only.
- Numeric risk-value cells are editable.
- Numeric values should be between `0` and `1`.
- Custom edits are saved to a new CSV file.
- Packaged default/template CSV files are never overwritten.

The first version intentionally prevents accidental editing of class names. Advanced class editing may be considered later after validation and workflow testing.

## Validation checks

The editor validates:

- required columns exist;
- no duplicate `classification` values;
- no empty `classification` values;
- `Other` class exists;
- required numeric values are present;
- required numeric values are valid numbers;
- numeric values are within `0..1`;
- unexpected extra columns trigger a warning;
- non-zero numeric values in the `Other` row trigger a warning.

Validation results use:

- `PASS`
- `WARNING`
- `CRITICAL`

Critical errors block saving. Warnings require confirmation before saving.

## Saving custom CSV files

When a QRADE output folder is selected in the Smart Assistant, the editor saves custom CSV files under:

```text
risk_tables/
```

inside that output folder. If no selected output folder is available, the editor asks the user to choose a folder.

Suggested filename pattern:

```text
qrade_risk_values_custom_<timestamp>.csv
```

If a timestamped filename already exists, the editor creates a unique filename. The packaged files `Input/classification_table.csv` and `Templates/classification_table_manual.csv` are never overwritten.

## Using the saved CSV in QRADE Processing

After saving a custom CSV:

1. Open the QRADE Processing algorithm.
2. Choose manual/custom risk-value table mode.
3. Select the saved `qrade_risk_values_custom_<timestamp>.csv`.
4. Run QRADE normally.

The editor prepares the custom table; it does not automatically update Processing parameters in the current version.

## Runtime verification evidence

Runtime verification recorded:

- editor opened from the Smart Assistant;
- default table loaded;
- manual template loaded;
- existing custom CSV loading path was available;
- `classification` column was locked/read-only;
- numeric cell editing worked;
- validation detected invalid numeric and out-of-range values;
- save was blocked when critical validation errors existed;
- save with warnings required confirmation;
- valid custom CSV saved under `risk_tables/`;
- saved CSV could be selected in QRADE Processing manual/custom table mode.

## What the editor does not do

The editor does not:

- run the QRADE Processing algorithm;
- change the QRADE risk formula;
- overwrite packaged default/template CSV files;
- automatically set Processing dialog parameters;
- use AI, ML, APIs, cloud services, LLMs, Ollama, or external services.

## Current limitations

- Users manually select the saved custom CSV in the Processing dialog.
- The `classification` column is locked in the first version.
- The editor does not yet store the last saved custom table path in QGIS settings.
- The editor does not yet write a metadata JSON sidecar for custom tables.

## Planned improvements

- Store the last saved custom table path in QGIS settings.
- Optionally add a Processing option for the last Smart Assistant custom table if safe.
- Add changed-cell summaries.
- Add optional metadata JSON sidecar files for custom tables.
