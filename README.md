# QRADE

## Overview

QRADE (Risk Assessment for Damage and Exposure) is a QGIS Processing plugin for rockfall risk assessment. It combines kinetic-energy raster data with land-cover or exposed-element information to support practical GIS-based screening, mapping, reporting, and review of rockfall risk.

QRADE generates GIS layers, summary files, QA/QC reports, an interactive risk dashboard, and BIM-oriented deliverables in a timestamped result folder.

## Methodology

QRADE is based on the IMIRILAND methodology for landslides in mountainous areas. The workflow supports semi-quantitative and quantitative assessments depending on data availability. It evaluates risk components in a modular way, including hazard intensity and extent, exposure, vulnerability, temporal probability, and the value of the elements at risk.

## Requirements

- QGIS 3.16+ is declared in `metadata.txt`.
- QGIS Processing and GDAL Processing providers must be available.
- QuickOSM is required for Auto land-cover generation from OpenStreetMap data.
- Auto land-cover mode requires internet access and availability of the Overpass API.
- Manual land-cover mode can be used offline with suitable local vector data.
- Manual land-cover data must include a lowercase `classification` field whose values match the selected risk-value table.
- QPROTO is recommended for generating the kinetic-energy raster, but QRADE can use suitable kinetic-energy raster outputs from other rockfall hazard-analysis tools.

## Installation

1. Copy or keep the plugin folder in a QGIS profile plugin directory, for example:
   `QGIS4/profiles/default/python/plugins/Qrade`
2. Start or restart QGIS.
3. Enable QRADE in the QGIS Plugin Manager.
4. Open QRADE from the toolbar/menu or from the Processing Toolbox.

## Basic Workflow

1. Prepare a kinetic-energy raster in joules.
2. Choose the land-cover source: Auto OSM or Manual land-cover.
3. Choose Default or Manual risk-value table mode.
4. Set temporal probability mode.
5. Select an output folder.
6. Choose which optional GIS layers to save.
7. Run QRADE.
8. Review the generated layers, dashboard, QA/QC report, BIM deliverables, and manifest in the timestamped result folder.

## Inputs

- `Land Cover Source`: Auto OSM generation or a manual land-cover vector layer.
- `Extent`: analysis area used for processing and, in Auto mode, for querying OpenStreetMap data.
- `Risk Assessment Values`: default packaged table or a user-selected custom CSV.
- `Area Type and Buildings Typology`: contextual setting used for exposed-element and built-environment assumptions.
- `Kinetic Energy raster (J)`: rockfall kinetic-energy raster.
- `Temporal Probability of Occurrence`: time-independent, frequency-based, or manual temporal probability setting.
- `Output Folder`: parent folder where QRADE creates a timestamped result folder.
- Optional GIS layer outputs: LandCover, Risk Assessment, and Runout layers.

Reports, QA/QC files, BIM deliverables, summary files, and the output manifest are generated automatically.

## Outputs

QRADE writes outputs into an organized timestamped result folder:

```text
QRADE_Result_TIMESTAMP/
|-- gis/
|   |-- landcover.gpkg
|   |-- runout.gpkg
|   `-- risk_assessment.gpkg
|-- summary/
|   |-- summary.json
|   `-- summary.csv
|-- bim/
|   |-- qrade_bim_risk.csv
|   |-- qrade_bim_risk.json
|   |-- qrade_ifc_guid_mapping_template.csv
|   `-- bcf_issues/
|       |-- qrade_rockfall_risk_issues.bcfzip
|       `-- README_no_high_risk_issues.txt
|-- reports/
|   |-- qa_qc/
|   |   |-- qrade_qa_qc_report.html
|   |   |-- qrade_qa_qc_report.json
|   |   `-- qrade_qa_qc_report.csv
|   `-- web_report/
|       |-- index.html
|       |-- data/
|       `-- assets/
|-- risk_tables/
`-- qrade_output_manifest.json
```

Final outputs include:

- Runout layer
- LandCover layer
- Risk Assessment layer
- Summary JSON/CSV
- Interactive Risk Dashboard
- QA/QC report
- BIM-ready CSV/JSON
- IFC GUID mapping template
- BCF issue package for High/Critical features, or a no-high-risk README
- `qrade_output_manifest.json`

## Smart Assistant

The QRADE Smart Assistant helps review generated QRADE result folders and open related deliverables.

Before running QRADE:

- Edit Risk Assessment Values

After running QRADE:

- Select QRADE Result Folder

Reports:

- Open Interactive Risk Dashboard
- Open QA/QC Report

BIM Deliverables:

- Open BIM-ready CSV
- Open IFC GUID Mapping Template
- Open BCF Issues Folder

## Risk Assessment Values

Default mode uses the packaged table:

- `Input/classification_table.csv`

Manual mode uses a user-selected custom CSV. The Risk Assessment Values Editor opens the manual template:

- `Templates/classification_table_manual.csv`

Custom tables are saved in the user QGIS settings directory, not inside the packaged plugin `Input/` or `Templates/` folders. Packaged default and manual template CSV files should not be edited directly.

When a manual/custom table is used in a QRADE run, the selected CSV is copied into the result folder under `risk_tables/` so the values used for the analysis can be reviewed later.

## Documentation and Training Data

Bundled plugin help is provided in:

- `help/qrade_help.html`

Additional resources:

- QRADE documentation: https://github.com/seyedmostafamoeini94-pixel/QRADE#readme
- Example training dataset: https://github.com/seyedmostafamoeini94-pixel/QRADE/tree/main/training_dataset

## License

QRADE is licensed under GPL-3.0-or-later. See `LICENSE`.

## Credits And Funding

The methodology was developed under the scientific supervision of Marta Castelli. QRADE was designed and implemented by Seyedmostafa Moeini, with technical support from Stefano Campus.

The development of QRADE was partially supported by PNRR (Piano Nazionale di Ripresa e Resilienza).

## Contact

- [seyedmostafa.moeini@polito.it](mailto:seyedmostafa.moeini@polito.it)
- [marta.castelli@polito.it](mailto:marta.castelli@polito.it)
