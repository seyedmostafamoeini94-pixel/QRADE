"""Read-only QRADE package readiness checker.

Run from the plugin root with:
    python tools/check_package_readiness.py

On Windows, if python is not on PATH:
    py tools/check_package_readiness.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
LARGE_FILE_THRESHOLD_MB = 5
LARGE_FILE_THRESHOLD_BYTES = LARGE_FILE_THRESHOLD_MB * 1024 * 1024

REQUIRED_ROOT_FILES = [
    "metadata.txt",
    "__init__.py",
    "qrade_plugin.py",
    "qrade_provider.py",
    "qrade_algorithm.py",
]

REQUIRED_RESOURCE_FOLDERS = [
    "Input",
    "Templates",
    "Styles",
    "help",
]

COMMON_DOC_FILES = [
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
]

USUALLY_EXCLUDED_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "Result",
}

USUALLY_EXCLUDED_SUFFIXES = {
    ".pyc",
}

TIMESTAMP_FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
QRADE_RESULT_FOLDER_RE = re.compile(r"^QRADE_Result_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.passes: list[str] = []

    def pass_(self, message: str) -> None:
        self.passes.append(message)
        print(f"PASS: {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"WARN: {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"FAIL: {message}")


def relative(path: Path) -> str:
    return path.relative_to(PLUGIN_ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#") or line.startswith("["):
            continue
        if line[0].isspace() and current_key:
            metadata[current_key] = (metadata[current_key] + "\n" + line.strip()).strip()
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            current_key = key.strip()
            metadata[current_key] = value.strip()
    return metadata


def scan_files() -> list[Path]:
    return [path for path in PLUGIN_ROOT.rglob("*") if path.is_file()]


def check_required_items(report: Report) -> None:
    for item in REQUIRED_ROOT_FILES:
        path = PLUGIN_ROOT / item
        if path.is_file():
            report.pass_(f"required root file exists: {item}")
        else:
            report.fail(f"missing required root file: {item}")

    for item in REQUIRED_RESOURCE_FOLDERS:
        path = PLUGIN_ROOT / item
        if path.is_dir():
            report.pass_(f"required resource folder exists: {item}/")
        else:
            report.fail(f"missing required resource folder: {item}/")


def check_common_docs(report: Report) -> None:
    for item in COMMON_DOC_FILES:
        path = PLUGIN_ROOT / item
        if path.is_file():
            report.pass_(f"repository file exists: {item}")
        else:
            report.warn(f"repository file missing before publication: {item}")


def check_excluded_items(report: Report, files: list[Path]) -> None:
    seen_paths: set[str] = set()
    for path in PLUGIN_ROOT.rglob("*"):
        rel = relative(path)
        if path.name in USUALLY_EXCLUDED_NAMES:
            seen_paths.add(rel + ("/" if path.is_dir() else ""))
        elif path.is_file() and path.suffix in USUALLY_EXCLUDED_SUFFIXES:
            seen_paths.add(rel)
        elif path.is_dir() and (TIMESTAMP_FOLDER_RE.match(path.name) or QRADE_RESULT_FOLDER_RE.match(path.name)):
            seen_paths.add(rel + "/")

    if seen_paths:
        for rel in sorted(seen_paths):
            report.warn(f"usually exclude from release package: {rel}")
    else:
        report.pass_("no obvious cache/generated output folders detected")

    large_files = [path for path in files if path.stat().st_size > LARGE_FILE_THRESHOLD_BYTES]
    if large_files:
        for path in sorted(large_files):
            size_mb = path.stat().st_size / (1024 * 1024)
            report.warn(f"large file above {LARGE_FILE_THRESHOLD_MB} MB: {relative(path)} ({size_mb:.2f} MB)")
    else:
        report.pass_(f"no files above {LARGE_FILE_THRESHOLD_MB} MB")


def check_package_size(report: Report, files: list[Path]) -> None:
    total_bytes = sum(path.stat().st_size for path in files)
    total_mb = total_bytes / (1024 * 1024)
    report.pass_(f"total package size estimate: {total_mb:.2f} MB across {len(files)} files")
    if total_mb > 20:
        report.warn("package is larger than 20 MB; review bundled manuals, rasters, and sample data before QGIS repository upload")


def check_metadata(report: Report) -> None:
    metadata_path = PLUGIN_ROOT / "metadata.txt"
    if not metadata_path.is_file():
        report.fail("metadata.txt missing; cannot check publication metadata")
        return

    text = read_text(metadata_path)
    metadata = parse_metadata(text)

    if "TODO:" in text:
        report.warn("metadata.txt contains TODO placeholders")
    else:
        report.pass_("metadata.txt has no TODO placeholders")

    if "YOUR_LINK_TO_USER_MANUAL" in text or "YOUR_LINK_TO_USER_MANUAL.pdf" in text:
        report.warn("metadata.txt contains old fake manual URL placeholder")
    else:
        report.pass_("metadata.txt has no old fake manual URL placeholder")

    for key in ("homepage", "repository", "tracker", "email"):
        value = metadata.get(key, "").strip()
        if not value or value.startswith("TODO"):
            report.warn(f"metadata field needs final value before publication: {key}")
        else:
            report.pass_(f"metadata field has publication value: {key}")

    if metadata.get("qgisMaximumVersion") == "4.99":
        report.warn("qgisMaximumVersion=4.99 is set; document QGIS 4 runtime testing before publication")


def check_quickosm_note(report: Report) -> None:
    combined_text = ""
    for item in ("README.md", "metadata.txt"):
        path = PLUGIN_ROOT / item
        if path.is_file():
            combined_text += "\n" + read_text(path).lower()

    required_terms = ("quickosm", "auto osm", "internet")
    missing = [term for term in required_terms if term not in combined_text]
    if missing:
        report.warn("README/metadata should clearly mention QuickOSM, Auto OSM, and internet requirements")
    else:
        report.pass_("QuickOSM/Auto OSM/internet requirements are documented")


def check_test_docs(report: Report) -> None:
    if (PLUGIN_ROOT / "tests/test_static_checks.py").is_file():
        report.pass_("static test script exists: tests/test_static_checks.py")
    else:
        report.warn("static test script missing: tests/test_static_checks.py")

    if (PLUGIN_ROOT / "docs/testing_checklist.md").is_file():
        report.pass_("runtime testing checklist exists: docs/testing_checklist.md")
    else:
        report.warn("runtime testing checklist missing: docs/testing_checklist.md")


def main() -> int:
    print(f"QRADE package readiness check: {PLUGIN_ROOT}")
    print()

    report = Report()
    files = scan_files()

    check_required_items(report)
    check_common_docs(report)
    check_excluded_items(report, files)
    check_package_size(report, files)
    check_metadata(report)
    check_quickosm_note(report)
    check_test_docs(report)

    print()
    print(f"Summary: {len(report.passes)} PASS, {len(report.warnings)} WARN, {len(report.failures)} FAIL")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
