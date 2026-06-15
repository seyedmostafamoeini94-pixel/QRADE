# QRADE Metadata Publication Checklist

Use this checklist before publishing QRADE to the QGIS plugin repository. This document records what must be finalized later; it does not replace runtime testing or package validation.

## metadata.txt Fields To Finalize

- [ ] Maintainer email is real, monitored, and suitable for public release.
- [ ] Homepage URL points to the final public project or documentation page.
- [ ] Repository URL points to the final public source repository.
- [ ] Issue tracker URL points to the final public issue tracker.
- [ ] Manual or documentation URL points to final user documentation.
- [ ] License value is final and matches the bundled `LICENSE` file.
- [ ] `qgisMinimumVersion` and `qgisMaximumVersion` are intentional for the release.
- [ ] QGIS 3.x runtime evidence is documented.
- [ ] QGIS 4.x runtime evidence is documented if `qgisMaximumVersion=4.99` remains.
- [ ] QuickOSM dependency wording clearly states that it is required only for Auto OSM mode.
- [ ] Plugin description and about text have received final review.
- [ ] Tags and category have received final review.
- [ ] Version number is final for the release package and GitHub tag.

## Do not publish until these are resolved

- [ ] No TODO placeholders remain in `metadata.txt`.
- [ ] Maintainer email and all metadata URLs are real.
- [ ] Clean ZIP install test has passed in a clean QGIS profile.
- [ ] Runtime evidence is documented.
- [ ] Static tests have passed.
- [ ] Package readiness check has 0 FAIL.
- [ ] Release ZIP excludes `Result/`, `__pycache__/`, `*.pyc`, `dist/`, and generated outputs.

## Notes For Final Review

- Do not invent placeholder URLs or email addresses for publication.
- Keep the core plugin free, offline-capable in Manual mode, and usable without API keys.
- Do not claim QGIS 4 compatibility unless runtime testing supports it.
- Record accepted warnings in the release evidence notes.
