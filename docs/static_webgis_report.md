# QRADE Static WebGIS Report

## Overview

QRADE writes a static WebGIS-style report and data bundle into each timestamped output folder. The current report is intended for offline-friendly review, QA, and communication of run results.

The current WebGIS support is a static report and data bundle only. It is not yet an interactive web map.

## Output folder structure

The report is written inside the timestamped output folder:

```text
web_report/
  index.html
  data/
    summary.json
    summary.csv
    qrade_bim_risk.json
    qrade_bim_risk.csv
    risk_assessment.geojson
    landcover.geojson
    runout.geojson
```

## How to open the report

Open `web_report/index.html` in a browser from the timestamped output folder. The HTML embeds summary and BIM/action values directly during generation, so it does not need browser-side `fetch()` requests to display the report tables and cards.

No server, API key, cloud service, or internet connection is required for the current static report.

## What the report includes

The current report includes:

- run information;
- summary cards;
- classification counts;
- top 10 risk features;
- BIM/action summary when BIM export data is available;
- links to exported data files;
- a map placeholder for a planned future interactive map phase.

## Data files included

The report data bundle includes:

- `web_report/data/summary.json`
- `web_report/data/summary.csv`
- `web_report/data/qrade_bim_risk.json`
- `web_report/data/qrade_bim_risk.csv`
- `web_report/data/risk_assessment.geojson`
- `web_report/data/landcover.geojson`
- `web_report/data/runout.geojson`

## GeoJSON CRS note

The GeoJSON files are exported in EPSG:4326/CRS84 for future web map use. The export does not modify the original QRADE GeoPackage outputs.

## Current limitations

- The report is static and does not yet include an interactive map.
- No Leaflet, OpenLayers, MapLibre, basemap, or chart library is included yet.
- Very large GeoJSON files may be slower to open or inspect in a browser.
- Results depend on input data quality, exposed-element classification quality, and risk assumptions.
- The report supports QA and communication, but it does not replace technical interpretation.

## Planned future WebGIS improvements

Planned improvements include:

- an interactive local map view;
- layer toggles for Risk Assessment, LandCover, and Runout;
- highlighted top-risk features;
- simple charts for classifications and priority counts;
- optional geometry simplification controls for large study areas.
