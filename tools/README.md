# QRADE Development Tools

These scripts are read-only or packaging helpers that use only the Python standard library.

Run static checks:

```bash
py tests/test_static_checks.py
```

Run package readiness checks:

```bash
py tools/check_package_readiness.py
```

Build a test ZIP:

```bash
py tools/build_plugin_zip.py
```

The ZIP is written to `dist/` and contains the plugin folder as the archive root.

The generated ZIP is not automatically ready for official QGIS repository publication. Before publication, replace metadata TODO values, decide the large-file policy, remove generated/cached files from the package, and document QGIS runtime testing.

Record release-candidate evidence with `docs/release_evidence.md`.
