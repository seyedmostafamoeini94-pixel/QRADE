"""Build a QRADE plugin ZIP for testing.

Run from the plugin root with:
    python tools/build_plugin_zip.py

On Windows, if python is not on PATH:
    py tools/build_plugin_zip.py
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_FOLDER_NAME = PLUGIN_ROOT.name
DIST_DIR = PLUGIN_ROOT / "dist"
LARGE_FILE_THRESHOLD_MB = 5
LARGE_FILE_THRESHOLD_BYTES = LARGE_FILE_THRESHOLD_MB * 1024 * 1024
LARGE_ZIP_WARNING_MB = 20
LARGE_ZIP_WARNING_BYTES = LARGE_ZIP_WARNING_MB * 1024 * 1024

REQUIRED_FILES = [
    "metadata.txt",
    "__init__.py",
    "qrade_plugin.py",
    "qrade_provider.py",
    "qrade_algorithm.py",
]

REQUIRED_ZIP_FILES = [
    "metadata.txt",
    "__init__.py",
    "qrade_plugin.py",
    "qrade_provider.py",
    "qrade_algorithm.py",
    "Input/classification_table.csv",
    "Templates/classification_table_manual.csv",
    "Styles/Classification2.qml",
    "Styles/RiskAssessment.qml",
    "Styles/Runout.qml",
    "help/qrade_help.html",
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    "dist",
    "docs",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "Result",
    "Results",
    "tests",
    "tools",
    "training dataset",
}

EXCLUDED_FILE_SUFFIXES = {
    ".pyc",
    ".tmp",
    ".bak",
    ".log",
}

EXCLUDED_FILE_NAMES = {
    ".gitignore",
    "CONTRIBUTING.md",
    ".DS_Store",
    "Thumbs.db",
}

TIMESTAMP_FOLDER_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
QRADE_RESULT_FOLDER_RE = re.compile(r"^QRADE_Result_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


class ValidationReport:
    def __init__(self) -> None:
        self.passes: list[str] = []
        self.warnings: list[str] = []
        self.failures: list[str] = []

    def pass_(self, message: str) -> None:
        self.passes.append(message)
        print(f"PASS: {message}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"WARN: {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"FAIL: {message}")


def parse_metadata_version() -> str:
    metadata_path = PLUGIN_ROOT / "metadata.txt"
    if not metadata_path.is_file():
        raise RuntimeError("metadata.txt is missing; cannot determine plugin version")

    for line in metadata_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("version="):
            version = line.split("=", 1)[1].strip()
            if version:
                return version
    raise RuntimeError("metadata.txt does not contain a version value")


def metadata_contains_todo() -> bool:
    metadata_path = PLUGIN_ROOT / "metadata.txt"
    if not metadata_path.is_file():
        return False
    return "TODO:" in metadata_path.read_text(encoding="utf-8", errors="replace")


def relative(path: Path) -> Path:
    return path.relative_to(PLUGIN_ROOT)


def is_generated_timestamp_folder(path: Path) -> bool:
    return path.is_dir() and (
        TIMESTAMP_FOLDER_RE.match(path.name) is not None
        or QRADE_RESULT_FOLDER_RE.match(path.name) is not None
    )


def should_exclude(path: Path) -> tuple[bool, str | None]:
    rel = relative(path)
    parts = rel.parts

    for part in parts:
        if part in EXCLUDED_DIR_NAMES:
            return True, part

    current = PLUGIN_ROOT
    for part in parts[:-1]:
        current = current / part
        if is_generated_timestamp_folder(current):
            return True, "timestamped output folder"

    if path.is_file():
        if path.name in EXCLUDED_FILE_NAMES:
            return True, path.name
        if path.name.startswith("~$"):
            return True, "~$ temporary file"
        if path.suffix in EXCLUDED_FILE_SUFFIXES:
            return True, path.suffix

    return False, None


def collect_files() -> tuple[list[Path], list[tuple[Path, str]]]:
    included: list[Path] = []
    excluded: list[tuple[Path, str]] = []

    for path in sorted(PLUGIN_ROOT.rglob("*")):
        if path.is_dir():
            continue
        exclude, reason = should_exclude(path)
        if exclude:
            excluded.append((path, reason or "excluded"))
        else:
            included.append(path)

    return included, excluded


def check_required_files() -> None:
    missing = [item for item in REQUIRED_FILES if not (PLUGIN_ROOT / item).is_file()]
    if missing:
        raise RuntimeError("missing required plugin files: " + ", ".join(missing))


def print_large_file_warnings(files: list[Path]) -> None:
    for path in files:
        size = path.stat().st_size
        if size > LARGE_FILE_THRESHOLD_BYTES:
            size_mb = size / (1024 * 1024)
            print(f"WARN: large file included: {relative(path).as_posix()} ({size_mb:.2f} MB)")


def build_zip(zip_path: Path, files: list[Path]) -> int:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive_name = Path(PLUGIN_FOLDER_NAME) / relative(path)
            archive.write(path, archive_name.as_posix())
    return len(files)


def validate_zip_structure(zip_path: Path, plugin_folder_name: str) -> bool:
    print()
    print("Validating ZIP structure...")
    report = ValidationReport()

    if not zip_path.is_file():
        report.fail(f"ZIP file does not exist: {zip_path}")
        print(f"Validation summary: {len(report.passes)} PASS, {len(report.warnings)} WARN, {len(report.failures)} FAIL")
        return False

    report.pass_(f"ZIP exists: {zip_path}")

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()

    if not names:
        report.fail("ZIP is empty")
        print(f"Validation summary: {len(report.passes)} PASS, {len(report.warnings)} WARN, {len(report.failures)} FAIL")
        return False

    top_levels = sorted({name.split("/", 1)[0] for name in names if name})
    if len(top_levels) == 1:
        report.pass_(f"ZIP has one top-level folder: {top_levels[0]}")
    else:
        report.fail("ZIP must have exactly one top-level folder; found: " + ", ".join(top_levels))

    if top_levels == [plugin_folder_name]:
        report.pass_(f"top-level folder matches plugin folder name: {plugin_folder_name}")
    else:
        report.fail(f"top-level folder must be {plugin_folder_name}/")

    name_set = set(names)
    missing = [
        f"{plugin_folder_name}/{relative_file}"
        for relative_file in REQUIRED_ZIP_FILES
        if f"{plugin_folder_name}/{relative_file}" not in name_set
    ]
    if missing:
        report.fail("missing required ZIP entries: " + ", ".join(missing))
    else:
        report.pass_("all required plugin entries are present")

    suspicious_entries: list[str] = []
    for name in names:
        parts = name.split("/")
        if any(part in {
            ".git",
            ".github",
            "dist",
            "docs",
            "__pycache__",
            "Result",
            "Results",
            "tests",
            "tools",
            "training dataset",
        } for part in parts):
            suspicious_entries.append(name)
        elif name.endswith((".pyc", ".tmp", ".bak", ".log")):
            suspicious_entries.append(name)
        elif Path(name).name in EXCLUDED_FILE_NAMES:
            suspicious_entries.append(name)
        elif any(TIMESTAMP_FOLDER_RE.match(part) or QRADE_RESULT_FOLDER_RE.match(part) for part in parts):
            suspicious_entries.append(name)

    if suspicious_entries:
        report.fail("excluded/generated entries found in ZIP: " + ", ".join(suspicious_entries))
    else:
        report.pass_("no excluded/generated entries found in ZIP")

    print(f"Validation summary: {len(report.passes)} PASS, {len(report.warnings)} WARN, {len(report.failures)} FAIL")
    return not report.failures


def main() -> int:
    print("QRADE release ZIP builder")
    print(f"Plugin root: {PLUGIN_ROOT}")
    print("Recommended before packaging: py tools/check_package_readiness.py")
    print()

    try:
        check_required_files()
        version = parse_metadata_version()
    except RuntimeError as error:
        print(f"FAIL: {error}")
        return 1

    if metadata_contains_todo():
        print("WARN: metadata.txt contains TODO placeholders; replace them before official publication.")

    included, excluded = collect_files()
    print_large_file_warnings(included)

    DIST_DIR.mkdir(exist_ok=True)
    zip_path = DIST_DIR / f"{PLUGIN_FOLDER_NAME}-v{version}.zip"
    included_count = build_zip(zip_path, included)

    zip_size = zip_path.stat().st_size
    zip_size_mb = zip_size / (1024 * 1024)
    excluded_categories = sorted({reason for _, reason in excluded})

    print()
    print(f"ZIP written: {zip_path}")
    print(f"ZIP size: {zip_size_mb:.2f} MB")
    print(f"Files included: {included_count}")
    print(f"Files excluded: {len(excluded)}")
    print("Excluded categories: " + (", ".join(excluded_categories) if excluded_categories else "none"))

    if zip_size > LARGE_ZIP_WARNING_BYTES:
        print(f"WARN: ZIP is larger than {LARGE_ZIP_WARNING_MB} MB.")
        print("WARN: Training data or large documentation may need to move outside the official QGIS repository package later.")

    zip_is_valid = validate_zip_structure(zip_path, PLUGIN_FOLDER_NAME)

    print()
    print("Next steps:")
    print("- Test ZIP install in a clean QGIS profile.")
    print("- Replace metadata TODO values.")
    print("- Decide large file policy for the PDF manual and training raster.")
    print("- Run: py tests/test_static_checks.py")
    print("- Run: py tools/check_package_readiness.py")
    return 0 if zip_is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
