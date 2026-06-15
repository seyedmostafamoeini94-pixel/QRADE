"""Lightweight static checks for QRADE.

Run from the plugin root with:
    python tests/test_static_checks.py

These checks use only the Python standard library and do not import QGIS.
"""

from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "metadata.txt",
    "__init__.py",
    "qrade_plugin.py",
    "qrade_provider.py",
    "qrade_algorithm.py",
    "smart_assistant_dialog.py",
    "risk_values_editor_dialog.py",
    "Input/classification_table.csv",
    "Templates/classification_table_manual.csv",
    "Styles/Classification2.qml",
    "Styles/RiskAssessment.qml",
    "Styles/Runout.qml",
    "help/qrade_help.html",
]

REQUIRED_METADATA_FIELDS = [
    "name",
    "description",
    "version",
    "qgisMinimumVersion",
    "qgisMaximumVersion",
    "author",
    "about",
    "license",
    "hasProcessingProvider",
]

REQUIRED_RISK_COLUMNS = [
    "classification",
    "exposure_physical",
    "exposure_social",
    "worth_physical",
    "worth_social",
    "phy_vul_sub_kj_lt50",
    "phy_vul_sub_kj_50_150",
    "phy_vul_sub_kj_150_250",
    "phy_vul_sub_kj_250_400",
    "phy_vul_sub_kj_400_550",
    "phy_vul_sub_kj_gt550",
    "soc_vul_sub_kj_lt50",
    "soc_vul_sub_kj_50_150",
    "soc_vul_sub_kj_150_250",
    "soc_vul_sub_kj_250_400",
    "soc_vul_sub_kj_400_550",
    "soc_vul_sub_kj_gt550",
    "phy_vul_urb_kj_lt50",
    "phy_vul_urb_kj_50_150",
    "phy_vul_urb_kj_150_250",
    "phy_vul_urb_kj_250_400",
    "phy_vul_urb_kj_400_550",
    "phy_vul_urb_kj_gt550",
    "soc_vul_urb_kj_lt50",
    "soc_vul_urb_kj_50_150",
    "soc_vul_urb_kj_150_250",
    "soc_vul_urb_kj_250_400",
    "soc_vul_urb_kj_400_550",
    "soc_vul_urb_kj_gt550",
]

PYTHON_FILES = [
    "__init__.py",
    "qrade_plugin.py",
    "qrade_provider.py",
    "qrade_algorithm.py",
    "smart_assistant_dialog.py",
    "risk_values_editor_dialog.py",
]


class StaticChecks:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes: list[str] = []

    def pass_(self, message: str) -> None:
        self.passes.append(message)
        print(f"PASS: {message}")

    def fail(self, message: str) -> None:
        self.failures.append(message)
        print(f"FAIL: {message}")

    def check(self, condition: bool, pass_message: str, fail_message: str) -> None:
        if condition:
            self.pass_(pass_message)
        else:
            self.fail(fail_message)


def read_text(relative_path: str) -> str:
    return (PLUGIN_ROOT / relative_path).read_text(encoding="utf-8")


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


def read_csv(relative_path: str) -> tuple[list[str], list[list[str]]]:
    with (PLUGIN_ROOT / relative_path).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def check_required_files(checks: StaticChecks) -> None:
    missing = [path for path in REQUIRED_FILES if not (PLUGIN_ROOT / path).exists()]
    checks.check(not missing, "required package files exist", f"missing required files: {', '.join(missing)}")


def check_metadata(checks: StaticChecks) -> None:
    text = read_text("metadata.txt")
    metadata = parse_metadata(text)
    missing = [field for field in REQUIRED_METADATA_FIELDS if field not in metadata]
    checks.check(not missing, "metadata contains important fields", f"metadata missing fields: {', '.join(missing)}")
    checks.check(
        "YOUR_LINK_TO_USER_MANUAL" not in text,
        "metadata has no old fake manual placeholder",
        "metadata still contains old fake manual placeholder YOUR_LINK_TO_USER_MANUAL",
    )


def check_csv_file(checks: StaticChecks, relative_path: str, expected_header: list[str] | None = None) -> list[str]:
    header, rows = read_csv(relative_path)
    checks.check(bool(header), f"{relative_path} has a header", f"{relative_path} is empty")
    if not header:
        return []

    checks.check(
        expected_header is None or header == expected_header,
        f"{relative_path} header matches expected schema",
        f"{relative_path} header does not match expected schema",
    )

    bad_rows = [index for index, row in enumerate(rows, start=2) if len(row) != len(header)]
    checks.check(
        not bad_rows,
        f"{relative_path} rows match header column count",
        f"{relative_path} rows with wrong column count: {bad_rows}",
    )

    missing_columns = [column for column in REQUIRED_RISK_COLUMNS if column not in header]
    checks.check(
        not missing_columns,
        f"{relative_path} contains required risk columns",
        f"{relative_path} missing risk columns: {', '.join(missing_columns)}",
    )

    if "classification" not in header:
        checks.fail(f"{relative_path} missing classification column")
        return header

    classification_index = header.index("classification")
    values = [row[classification_index].strip() for row in rows if len(row) > classification_index]
    duplicates = sorted({value for value in values if value and values.count(value) > 1})
    empty_values = [index for index, value in enumerate(values, start=2) if not value]
    other_rows = [row for row in rows if len(row) > classification_index and row[classification_index].strip() == "Other"]

    checks.check(not empty_values, f"{relative_path} has no empty classifications", f"{relative_path} empty classifications on rows: {empty_values}")
    checks.check(not duplicates, f"{relative_path} has no duplicate classifications", f"{relative_path} duplicate classifications: {', '.join(duplicates)}")
    checks.check(len(other_rows) == 1, f"{relative_path} contains Other exactly once", f"{relative_path} Other count is {len(other_rows)}")
    if other_rows:
        numeric_values = [
            value.strip()
            for index, value in enumerate(other_rows[0])
            if index != classification_index and header[index] != "fid"
        ]
        non_zero_other_values = [value for value in numeric_values if value not in {"0", "0.0", "0.00"}]
        checks.check(
            not non_zero_other_values,
            f"{relative_path} Other row risk values are zero",
            f"{relative_path} Other row has non-zero risk values: {', '.join(non_zero_other_values)}",
        )
    return header


def check_csv_tables(checks: StaticChecks) -> None:
    default_header = check_csv_file(checks, "Input/classification_table.csv")
    check_csv_file(checks, "Templates/classification_table_manual.csv", expected_header=default_header)
    default_text = read_text("Input/classification_table.csv")
    manual_text = read_text("Templates/classification_table_manual.csv")
    checks.check(
        default_text == manual_text,
        "manual template CSV matches approved default CSV exactly",
        "Templates/classification_table_manual.csv differs from Input/classification_table.csv",
    )


def check_classification_style(checks: StaticChecks) -> None:
    text = read_text("Styles/Classification2.qml")
    checks.check(
        'attr="classification"' in text,
        "Classification2.qml renderer uses lowercase classification",
        'Classification2.qml does not contain attr="classification"',
    )
    checks.check(
        'attr="Classification"' not in text,
        "Classification2.qml does not use uppercase Classification renderer attr",
        'Classification2.qml still contains attr="Classification"',
    )


def check_algorithm_text(checks: StaticChecks) -> None:
    text = read_text("qrade_algorithm.py")
    forbidden_snippets = [
        "os.path.join(base_dir, 'templates')",
        'os.path.join(base_dir, "templates")',
        "landcover_template.gpkg",
        'href="../qrade_bim_risk.csv"',
        'href="../qrade_ifc_guid_mapping_template.csv"',
        'href="../bcf_issues/"',
        'Time-independent mode sets temporal probability to 1.0; review whether this assumption is appropriate.',
        'Rule-based QA/QC report. This is not AI/ML and does not replace expert judgement.',
        'It is a transparent rule-based QA/QC report, not AI/ML.',
        '<span style="color:#008000; font-weight:bold;">QRADE completed successfully.</span>',
        'Open Interactive Risk Dashboard</a>',
        'Help file not found at:',
        'Add <code>help/qrade_help.html</code> inside the plugin folder.',
        '<h2>QRADE</h2>',
    ]
    found = [snippet for snippet in forbidden_snippets if snippet in text]
    checks.check(not found, "algorithm has no removed template path references", f"algorithm still contains: {', '.join(found)}")

    required_output_snippets = [
        'QRADE_Result_{timestamp}',
        "gis/landcover.gpkg",
        "summary/summary.json",
        "bim/qrade_bim_risk.csv",
        "reports/web_report/index.html",
        'href="../../bim/qrade_bim_risk.csv"',
        'href="../../bim/qrade_ifc_guid_mapping_template.csv"',
        'href="../../bim/bcf_issues/"',
        "temporal_probability_quality = 'TIME_INDEPENDENT'",
        "acceptable_temporal_qualities = ('ACCEPTABLE', 'TIME_INDEPENDENT', 'NOT_APPLICABLE')",
        'bcf_zip_exists_for_inventory or (',
        'elif bcf_readme_exists_for_inventory:',
        'overflow-wrap: anywhere',
        '<div class="table-wrap">',
        '<table class="checks-table">',
        '<col style="width:20%">',
        'Optional GIS layer outputs',
        'Automatic outputs: Reports, QA/QC files, BIM deliverables, summary files,',
        'output_options_note.setMetadata',
        "QgsProcessingOutputHtml('InteractiveRiskDashboard', 'Interactive Risk Dashboard')",
        "results['InteractiveRiskDashboard'] = web_index_path",
        'QRADE completed successfully.\\n',
        'Interactive Risk Dashboard: {web_index_path}\\n',
        'Open the QRADE Smart Assistant to review the generated dashboard, QA/QC report,',
        'QRADE (Risk Assessment for Damage and Exposure) is a QGIS Processing algorithm for rockfall risk assessment.',
        'The QuickOSM plugin is required when using Auto land-cover generation from OpenStreetMap data.',
        'link User Manual',
        'link training dataset',
        'seyedmostafa.moeini@polito.it',
        'marta.castelli@polito.it',
    ]
    missing_output_snippets = [snippet for snippet in required_output_snippets if snippet not in text]
    checks.check(
        not missing_output_snippets,
        "algorithm contains organized output path markers",
        f"algorithm missing organized output path markers: {', '.join(missing_output_snippets)}",
    )
    checks.check(
        "'web_report_index': os.path.join(paths['web_report_dir'], 'index.html'),\n        })\n        paths.update({\n            'web_report_summary_json': os.path.join(paths['web_report_data_dir'], 'summary.json')," in text,
        "algorithm finalizes web_report_data_dir before deriving Web report data file paths",
        "algorithm may derive Web report data file paths before web_report_data_dir exists",
    )

    mojibake_markers = ["â", "Î", "Ï", "Ã", "�"]
    found_markers = [marker for marker in mojibake_markers if marker in text]
    checks.check(not found_markers, "algorithm has no common mojibake markers", f"algorithm contains mojibake markers: {', '.join(found_markers)}")


def check_risk_table_workflow_markers(checks: StaticChecks) -> None:
    editor_text = read_text("risk_values_editor_dialog.py")
    algorithm_text = read_text("qrade_algorithm.py")
    assistant_text = read_text("smart_assistant_dialog.py")

    editor_required = [
        "SYSTEM_COLUMNS = [",
        "'fid'",
        "QgsApplication.qgisSettingsDirPath()",
        "Manual template loaded. Edit numeric values",
        "self._load_csv(self.manual_template_path, 'manual risk-value template')",
        "Open Custom CSV",
        "Save Custom CSV",
        "Reset to Manual Template",
        "Open Custom Tables Folder",
        "reset_to_manual_template",
        "Missing required official QRADE class: Other",
        "_is_packaged_table_folder",
        "os.path.join(QgsApplication.qgisSettingsDirPath(), 'QRADE', 'risk_tables')",
    ]
    missing_editor = [snippet for snippet in editor_required if snippet not in editor_text]
    checks.check(
        not missing_editor,
        "risk values editor uses QGIS profile library and reset workflow markers",
        f"risk values editor missing workflow markers: {', '.join(missing_editor)}",
    )
    checks.check(
        "allowed_columns = set(self.REQUIRED_COLUMNS) | set(self.SYSTEM_COLUMNS)" in editor_text
        and "column_index == classification_index or column_index in system_column_indexes" in editor_text,
        "risk values editor treats fid as an allowed locked system column",
        "risk values editor does not clearly allow and lock system columns such as fid",
    )
    checks.check(
        "os.path.join(self.output_folder, 'risk_tables')" not in editor_text,
        "risk values editor no longer defaults custom saves to selected output folder",
        "risk values editor still defaults custom saves to selected output folder",
    )
    removed_editor_text = [
        "Load Default Table",
        "Load Manual Template",
        "Open Existing Custom Table",
        "Save As Custom CSV",
        "Open Saved Folder",
    ]
    found_removed_editor_text = [snippet for snippet in removed_editor_text if snippet in editor_text]
    checks.check(
        not found_removed_editor_text,
        "risk values editor removed superseded table workflow buttons",
        f"risk values editor still contains removed button text: {', '.join(found_removed_editor_text)}",
    )

    algorithm_required = [
        "_copy_used_risk_value_table",
        "qrade_risk_values_used_{timestamp}.csv",
        "risk_value_table_source_path",
        "risk_value_table_copied_to",
        "risk_value_table_copied_relative_path",
        "used_risk_value_table",
        "source_risk_value_table",
        "Manual risk-value table mode is selected. First open the Smart Assistant",
        "defaultValue=''",
    ]
    missing_algorithm = [snippet for snippet in algorithm_required if snippet not in algorithm_text]
    checks.check(
        not missing_algorithm,
        "algorithm records manual/custom risk table traceability markers",
        f"algorithm missing risk table traceability markers: {', '.join(missing_algorithm)}",
    )
    checks.check(
        "defaultValue=default_manual_csv" not in algorithm_text
        and "manual_table_default = os.path.join(templates_dir, \"classification_table_manual.csv\")" not in algorithm_text,
        "manual risk-value CSV parameter is not prefilled with packaged template",
        "manual risk-value CSV parameter still falls back to or pre-fills the packaged template",
    )

    assistant_required = [
        "Before running QRADE",
        "Edit Risk Assessment Values",
        "Create a custom risk-value CSV before running QRADE",
        "After running QRADE",
        "Select QRADE Result Folder",
        "Reports",
        "Open Interactive Risk Dashboard",
        "Open QA/QC Report",
        "BIM Deliverables",
        "Open BIM-ready CSV",
        "Open IFC GUID Mapping Template",
        "Open BCF Issues Folder",
    ]
    missing_assistant = [snippet for snippet in assistant_required if snippet not in assistant_text]
    checks.check(
        not missing_assistant,
        "Smart Assistant contains organized pre-run, report, and BIM section labels",
        f"Smart Assistant missing section/button labels: {', '.join(missing_assistant)}",
    )
    removed_assistant_text = [
        "Rule-based QA/QC helper for reviewing QRADE outputs",
        "This is not AI/ML and does not replace expert judgement",
        "This assistant is rule-based QA/QC, not AI/ML",
        "Open Latest QA/QC Report",
        "Open Latest WebGIS Report",
        "Open Output Folder",
        "Temporal Probability Estimator",
    ]
    found_removed_assistant_text = [snippet for snippet in removed_assistant_text if snippet in assistant_text]
    checks.check(
        not found_removed_assistant_text,
        "Smart Assistant removed legacy AI/ML text, latest labels, and removed tools",
        f"Smart Assistant still contains removed text: {', '.join(found_removed_assistant_text)}",
    )
    checks.check(
        "The packaged default and manual template CSV files are never overwritten." not in editor_text,
        "risk values editor removed packaged-table overwrite sentence",
        "risk values editor still contains packaged-table overwrite sentence",
    )


def check_python_parse(checks: StaticChecks) -> None:
    for relative_path in PYTHON_FILES:
        try:
            ast.parse(read_text(relative_path), filename=relative_path)
        except SyntaxError as error:
            checks.fail(f"{relative_path} does not parse: {error}")
        else:
            checks.pass_(f"{relative_path} parses with ast")


def main() -> int:
    checks = StaticChecks()
    check_required_files(checks)
    check_metadata(checks)
    check_csv_tables(checks)
    check_classification_style(checks)
    check_algorithm_text(checks)
    check_risk_table_workflow_markers(checks)
    check_python_parse(checks)

    print()
    print(f"Summary: {len(checks.passes)} passed, {len(checks.failures)} failed")
    return 1 if checks.failures else 0


if __name__ == "__main__":
    sys.exit(main())
