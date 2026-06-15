# Contributing To QRADE

QRADE is under active development and is being prepared for GitHub and eventual QGIS plugin repository publication.

## Local Development Setup

1. Clone or copy the QRADE plugin folder.
2. Place or symlink it into your QGIS profile plugins directory, for example:
   `QGIS4/profiles/default/python/plugins/Qrade`
3. Start QGIS and enable QRADE in the Plugin Manager.
4. Open QRADE from the toolbar/menu or Processing Toolbox.
5. Reload or restart QGIS after code changes.

## Recommended Workflow

- Make one small change at a time.
- Test the change in QGIS before continuing.
- Back up or commit after each successful step.
- Keep test notes with QGIS version, input data, output folder, screenshots, and Processing logs.

## Coding Guidelines

- Keep QGIS 3.x and QGIS 4.x compatibility in mind.
- Keep Manual land-cover mode offline-capable.
- Keep QuickOSM optional and limited to Auto OSM mode.
- Avoid hardcoded user-specific paths.
- Avoid writing generated outputs inside the plugin package by default when possible.
- Use clear `QgsProcessingException` messages for user-fixable problems.
- Do not change risk formulas without documenting the methodology and reason.
- Keep patches focused; avoid unrelated refactors.

## Dependency Policy

- No mandatory API keys.
- No mandatory cloud AI, LLM, or paid-service dependencies.
- No bundled large ML models.
- Future ML work, if added, must be optional, offline, lightweight, and mainly focused on exposed-element classification.

## Reporting Issues

Please include:

- QGIS version and whether QGIS 3.x or QGIS 4.x is used;
- operating system;
- QRADE version;
- full Processing log;
- full traceback or error message;
- project CRS and kinetic-energy raster CRS;
- input raster path or description;
- land-cover mode: Auto OSM or Manual;
- risk-table mode: default or manual CSV;
- temporal-probability mode;
- selected output folder;
- screenshots of the QRADE dialog, layer panel, and outputs when useful.

## Pull Request Checklist

- The change is focused and easy to review.
- QGIS was restarted or the plugin was reloaded before testing.
- Manual/offline mode still works or is not affected.
- Auto OSM mode still treats QuickOSM as optional.
- No new mandatory API keys, cloud services, or paid dependencies were added.
- Risk formulas were not changed, or methodology documentation was updated.
- `README.md` or `CHANGELOG.md` was updated if user-facing behavior changed.
- Relevant QGIS logs, screenshots, or test notes are attached to the PR.
