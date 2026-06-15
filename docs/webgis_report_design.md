# QRADE Static WebGIS Report Design

## Overview

The first QRADE WebGIS/reporting feature should be a static, offline-friendly report generated into each timestamped output folder. The report should be opened from `web_report/index.html` in a browser, with no server, API key, cloud service, or paid dependency required.

This document is design only. It does not define an implemented feature yet.

## Intended First Version

The first version should:

- generate a `web_report/` folder inside the timestamped QRADE output folder;
- work by opening `web_report/index.html` in a browser;
- avoid any required server backend;
- avoid API keys and cloud services;
- use exported GeoJSON files and existing QRADE summary files;
- keep styling and scripting local to the exported report folder;
- remain useful without internet access.

If Leaflet is used later, the official plugin package should avoid mandatory internet CDNs. Leaflet JavaScript/CSS assets should either be bundled locally where license-compatible or copied into the report assets folder during export. Any optional online basemap should be disabled by default or clearly documented as internet-dependent.

## Proposed Output Structure

```text
<timestamped_output_folder>/
  web_report/
    index.html
    data/
      summary.json
      risk_assessment.geojson
      landcover.geojson
      runout.geojson
      qrade_bim_risk.json        optional, if available
    assets/
      app.js
      style.css
      leaflet/                   optional local Leaflet assets if included later
```

## Proposed Map Layers

The report should expose these layer groups:

- Risk Assessment
- LandCover
- Runout
- optional top-risk markers or highlighted features in a later phase

Layer toggles should allow users to turn layers on and off. The initial view can be fitted to the Risk Assessment or Runout extent.

## Dashboard Elements

The dashboard should be driven by `summary.json` and optional BIM export data. Proposed elements:

- feature count;
- max risk total;
- mean risk total;
- sum risk total;
- classification counts;
- BCF priority/action counts if `qrade_bim_risk.json` exists;
- top 10 risk features.

These values are for QA, reporting, and screening. They should not replace technical interpretation of QRADE outputs.

## Risk Feature Popups

Risk Assessment feature popups should include:

- `qrade_id`
- `classification`
- `risk_total`
- `risk_physical`
- `risk_social`
- `energy_max`
- `recommended_action` if available later
- `bcf_priority` if available later

Popup content should be concise and readable. Missing optional fields should be shown as blank or omitted rather than causing report failure.

## Chart Ideas

The first implementation should stay simple and avoid heavy chart libraries unless clearly needed. Candidate visualizations:

- classification count bar chart;
- risk priority count chart from BIM export priority values;
- top-risk feature table.

Simple HTML tables and lightweight custom JavaScript may be enough for the first release. Charts can be added after the data export and map display are stable.

## Data Conversion Approach

The report generator should:

- use QGIS Processing to export GeoPackage layers to GeoJSON;
- export web map GeoJSON in WGS84 / EPSG:4326 for browser display;
- copy `summary.json` into `web_report/data/`;
- optionally copy `qrade_bim_risk.json` into `web_report/data/` if it exists;
- keep geometry simplification optional for a later phase;
- warn users that large study areas can create large GeoJSON files and slower browser rendering.

The initial design should not require PostGIS, Mapbox, MapLibre, OpenLayers, server backends, APIs, or external web services.

## Implementation Constraints

- No API keys.
- No external web services required.
- No mandatory internet CDNs for official plugin packaging.
- No server backend required for the first version.
- Local file opening should work where browser security permits.
- If local file restrictions appear in some browsers, users can open the report through a simple local server, but the first goal remains a static/offline report.
- The report must not change QRADE risk calculations or existing GeoPackage/summary/BIM outputs.

## Development Phases

1. Phase 1: export GeoJSON files and copy summary files.
2. Phase 2: generate basic `index.html` with a Leaflet map and layer toggles.
3. Phase 3: add summary cards and a top-risk feature table.
4. Phase 4: add simple charts.
5. Phase 5: optional advanced WebGIS, PostGIS, or MapLibre exploration later.

Phase 5 is explicitly out of scope for the first static report. It should remain optional and should not create a required cloud, API, or paid-service dependency.

## Testing Checklist

- [ ] `web_report/` folder exists in the timestamped output folder.
- [ ] `web_report/index.html` opens in a browser.
- [ ] `web_report/data/risk_assessment.geojson` exists.
- [ ] `web_report/data/landcover.geojson` exists when LandCover output is selected.
- [ ] `web_report/data/runout.geojson` exists when Runout output is selected.
- [ ] GeoJSON files use WGS84 / EPSG:4326 for web map display.
- [ ] Risk Assessment layer loads on the map.
- [ ] LandCover layer loads on the map when available.
- [ ] Runout layer loads on the map when available.
- [ ] Summary cards match values from `summary.json`.
- [ ] Top-risk table matches `summary.json`.
- [ ] Optional BIM priority/action counts match `qrade_bim_risk.json` when present.
- [ ] Report remains usable without an internet connection, except for any explicitly optional online basemap.
