# Changelog

All notable changes to QRADE will be documented in this file.

The format is based on Keep a Changelog, and this project uses semantic versioning where practical.

## [Unreleased]

### Changed

- Fixed plugin path casing for the `Templates/` folder.
- Added conservative `Other` class handling to packaged classification tables.
- Improved Manual land-cover validation when no valid vector file is selected.
- Added early classification-table CSV validation.
- Added land-cover classification value checks before joining CSV values.
- Added CRS safety checks for raster/project CRS mismatch and geographic CRS in Auto OSM mode.
- Added output-folder validation and warning for writing inside the plugin directory.
- Cleaned user-facing encoding/mojibake artifacts in Python strings.
- Improved `metadata.txt` for GitHub and QGIS repository preparation.

## [1.0.0]

### Added

- Initial development release placeholder for the QRADE rockfall risk assessment workflow.
