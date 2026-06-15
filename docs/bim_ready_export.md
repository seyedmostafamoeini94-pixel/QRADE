# QRADE BIM-Ready Risk Export

## Overview

QRADE writes BIM-ready, asset-management-friendly tabular risk exports for each completed run. These files summarize the final risk-assessment features in a format that can support asset registers, infrastructure BIM workflows, design coordination, and future BIM-related export tools.

This is a tabular export only. It does not create, modify, or validate an IFC model, and it is not a BCF export.

## Output files

The BIM-ready export files are written into the same timestamped output folder as the other QRADE outputs:

- `qrade_bim_risk.csv`
- `qrade_bim_risk.json`
- `qrade_ifc_guid_mapping_template.csv`

The BIM risk CSV file provides a flat table for spreadsheets, asset registers, and data exchange. The JSON file stores the same records with metadata about the QRADE run.

The IFC GUID mapping template is a separate ready-to-fill CSV table for linking QRADE assets to BIM/IFC elements after the QRADE run.

After selecting a QRADE output folder, the `QRADE Smart Assistant` dialog can open the BIM-ready CSV, IFC GUID mapping template, and BCF issues folder directly.

## Field definitions

- `qrade_id`: QRADE feature identifier. Uses an existing `qrade_id` field when available; otherwise uses the source feature id.
- `asset_id`: Asset-register-friendly identifier generated as `QRADE-<qrade_id>`.
- `ifc_guid`: Blank placeholder for future mapping to IFC element GUIDs.
- `bim_category`: Broad BIM/asset category derived from the QRADE classification.
- `classification`: QRADE land-cover or exposed-element classification.
- `risk_total`: Final total risk value from the QRADE risk assessment.
- `risk_physical`: Physical risk component.
- `risk_social`: Social risk component.
- `energy_max_j`: Maximum kinetic energy value in joules, when available.
- `energy_max_kj`: Maximum kinetic energy value converted to kilojoules, when available.
- `temporal_probability`: Temporal probability value used for the run.
- `recommended_action`: Suggested review action derived from `risk_total`.
- `bcf_priority`: Priority label derived from `risk_total` for future coordination workflows.
- `assessment_date`: Run timestamp or assessment date from the QRADE run metadata.
- `source_layer_feature_id`: Feature id from the final risk-assessment layer.

## BIM/asset-management use cases

The export can support:

- asset-register review of exposed infrastructure and land-use features;
- tabular risk screening for owners, operators, or engineering teams;
- linking QRADE risk results to external BIM or asset-management records;
- design coordination where risk items need to be reviewed alongside other project data;
- preparation for later BCF or IFC export workflows.

## IFC GUID mapping note

`ifc_guid` is intentionally blank until the user maps QRADE risk-assessment features to IFC elements. This avoids implying a verified relationship between GIS features and BIM objects before that mapping has been completed.

Users can fill or join `ifc_guid` externally when a reliable relationship exists between QRADE features and IFC element GUIDs.

## IFC GUID mapping template

QRADE also writes `qrade_ifc_guid_mapping_template.csv` automatically into each timestamped output folder. The template has one row per final risk-assessment feature and is intended for BIM or asset-management users who want to manually map QRADE assets to IFC elements later.

The template does not edit IFC files, does not write IFC property sets, and does not require IfcOpenShell or other BIM software dependencies.

### Mapping template fields

- `qrade_id`: QRADE feature identifier. Uses an existing `qrade_id` field when available; otherwise uses the source feature id.
- `asset_id`: Asset-register-friendly identifier generated as `QRADE-<qrade_id>`.
- `classification`: QRADE land-cover or exposed-element classification.
- `risk_total`: Final total risk value from the QRADE risk assessment.
- `risk_physical`: Physical risk component.
- `risk_social`: Social risk component.
- `energy_max_j`: Maximum kinetic energy value in joules, when available.
- `energy_max_kj`: Maximum kinetic energy value converted to kilojoules, when available.
- `bcf_priority`: Priority label derived from `risk_total` for future coordination workflows.
- `recommended_action`: Suggested review action derived from `risk_total`.
- `ifc_guid`: Blank field for the user to fill after mapping a QRADE feature to an IFC element.
- `bim_element_name`: Optional BIM element name entered by the user.
- `bim_element_type`: Optional BIM element type entered by the user.
- `mapping_method`: Mapping method, currently initialized as `manual`.
- `mapping_confidence`: Optional user-entered confidence value for the mapping.
- `mapping_notes`: Notes for the BIM/asset-management reviewer.

### How BIM users can use it

1. Open `qrade_ifc_guid_mapping_template.csv` in a spreadsheet, asset register, or BIM coordination workflow.
2. Review each `asset_id`, classification, risk value, action, and priority.
3. Locate the corresponding BIM/IFC element in the external BIM model or asset database.
4. Fill `ifc_guid` and optional BIM element fields when the mapping is reliable.
5. Use the completed table as input for later coordination, asset-register review, or future BCF issue export workflows.

The template supports later BCF issue export by preserving QRADE risk/action fields alongside user-supplied IFC GUID mappings. It is not itself a BCF file.

## BCF issue export

QRADE writes a simple file-based BCF issue export automatically after each successful risk assessment. This supports BIM coordination and review workflows for high-risk QRADE features without editing IFC files or requiring external BIM software during the QRADE run.

### Output files

When High or Critical risk features exist, QRADE writes:

```text
bcf_issues/
  qrade_rockfall_risk_issues.bcfzip
```

When no High or Critical risk features exist, QRADE writes:

```text
bcf_issues/
  README_no_high_risk_issues.txt
```

### High/Critical selection rule

BCF issues are created only for features with:

```text
risk_total >= 0.50
```

This corresponds to the existing BIM priority thresholds:

- `risk_total >= 0.75`: Critical
- `risk_total >= 0.50`: High

### Issue contents

Each BCF issue includes:

- title in the form `QRADE <priority> rockfall risk - <asset_id>`;
- priority (`Critical` or `High`);
- `qrade_id`;
- `asset_id`;
- classification;
- `risk_total`, `risk_physical`, and `risk_social`;
- `energy_max_kj`;
- recommended action;
- centroid coordinates in the layer CRS where geometry is available;
- note that IFC GUID mapping can be added later using `qrade_ifc_guid_mapping_template.csv`.

### Folder/ZIP structure

The generated `.bcfzip` uses a minimal BCF-style ZIP structure:

```text
bcf.version
<topic-uuid>/
  markup.bcf
<topic-uuid>/
  markup.bcf
```

There is one topic folder per exported QRADE issue. This first version does not include BCF viewpoints or snapshots.

### Relationship to IFC GUID mapping

The BCF issue export can be used before IFC GUID mapping is complete because the issue text includes QRADE asset identifiers and risk values. Filling `qrade_ifc_guid_mapping_template.csv` later can improve BIM element linking and support stronger future coordination workflows.

The BCF export is not IFC editing, does not create IFC models, and does not write IFC property sets.

## Recommended action and BCF priority logic

QRADE derives `recommended_action` and `bcf_priority` from `risk_total` using these thresholds:

| Risk total | Recommended action | BCF priority |
| --- | --- | --- |
| `risk_total >= 0.75` | Immediate review / mitigation planning | Critical |
| `risk_total >= 0.50` | Detailed engineering review | High |
| `risk_total >= 0.25` | Monitor and review | Medium |
| `risk_total > 0` | Low priority monitoring | Low |
| `risk_total == 0 or null` | No action from current assessment | Info |

These fields support review and prioritization. They do not replace technical interpretation, engineering judgement, or formal decision-making.

## Current limitations

- The export is tabular only and is not an IFC model.
- The BIM risk export and mapping template are tabular files; the BCF export is a simple file-based issue package.
- BCF export does not currently include viewpoints or snapshots.
- `ifc_guid` is blank unless mapped externally.
- The IFC GUID mapping template must be completed and verified by the user before it is used for BIM coordination.
- `bim_category` is derived from QRADE classification using simple category rules.
- Action and priority labels are screening aids derived from `risk_total`.
- Output quality depends on the kinetic-energy raster, classification quality, and risk-value assumptions.

## Planned future BIM improvements

Potential future improvements include:

- user-assisted mapping between QRADE features and IFC element GUIDs;
- BCF-ready issue export based on selected high-risk records;
- optional IFC/GeoBIM exchange support after the tabular workflow is validated;
- clearer documentation examples for asset-register workflows.
