# QRADE Testing Checklist

Use this checklist for baseline tests, release checks, and regression testing.

## Baseline Test Record

Record:

- QGIS version;
- operating system;
- QRADE/plugin version;
- project CRS;
- kinetic-energy raster CRS;
- input raster path;
- land-cover mode: Auto OSM or Manual;
- risk-table mode: default or manual CSV;
- temporal-probability mode;
- selected output folder;
- save options selected;
- screenshots of the QRADE dialog before running;
- Processing log and QGIS Log Messages;
- screenshots of generated layers and attribute tables.

Suggested naming:

- `baseline_YYYY-MM-DD_qrade_VERSION_qgisVERSION_mode_crs`
- `backup_YYYY-MM-DD_before_STEP`
- `test_YYYY-MM-DD_case_short-description`

## Manual Mode Tests

- Manual mode with no manual file selected.
- Manual mode with a valid GeoPackage/vector file and lowercase `classification`.
- Manual mode with missing `classification` field.
- Manual mode with an unmatched classification value.
- Manual mode with project CRS matching raster CRS.

## Auto OSM Mode Tests

- QuickOSM installed and enabled.
- QuickOSM missing or disabled, if practical.
- Small extent with expected OSM features.
- Geographic project CRS blocked before buffering.
- Overpass/network failure behavior.
- Reduced extent after Overpass timeout.

## CRS Tests

- Project CRS equals kinetic-energy raster CRS.
- Project CRS differs from kinetic-energy raster CRS.
- Kinetic-energy raster CRS invalid or missing.
- Auto OSM mode with projected CRS in linear units.
- Auto OSM mode with geographic CRS.

## Classification Table Tests

- Default classification table.
- Manual classification table.
- Manual table missing a required column.
- Manual table with duplicate `classification` value.
- Manual table missing `Other`.
- Manual table with an empty `classification` value.
- Manual table with inconsistent column counts.

## Output Tests

- Normal project/workspace output folder.
- Output folder inside plugin folder warning.
- Invalid output path.
- Unwritable output folder.
- All save checkboxes off.
- Confirm timestamped output folder is created.
- Confirm expected filenames are preserved:
  - `landcover.gpkg`
  - `runout.gpkg`
  - `risk_assessment.gpkg`

## Result Checks

- LandCover layer loads.
- Runout layer loads.
- Risk Assessment layer loads.
- LandCover style is applied.
- Runout style is applied.
- RiskAssessment style is applied.
- Expected fields exist in `risk_assessment.gpkg`.
- `risk_total` exists.
- No unexpected null values after the classification-table join.
- `Other` class, if present, joins without causing null risk fields.

## Evidence To Save

- Processing log text.
- QGIS Log Messages text.
- Output folder listing.
- Screenshots of map canvas and layer panel.
- Attribute table screenshots for output layers.
- Any traceback or warning message.
