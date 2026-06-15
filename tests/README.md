# QRADE Static Tests

These tests are lightweight packaging and consistency checks. They use only the Python standard library and do not import QGIS.

Run from the plugin root:

```bash
python tests/test_static_checks.py
```

On Windows, if `python` is not on `PATH`, use:

```bash
py tests/test_static_checks.py
```

The static tests check required files, metadata fields, CSV table consistency, style field names, common path regressions, mojibake markers, and Python syntax.

These tests do not replace QGIS runtime testing. Runtime checks should follow:

```text
docs/testing_checklist.md
```
