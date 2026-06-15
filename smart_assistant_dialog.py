# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-or-later

"""
QRADE - Risk Assessment for Damage and Exposure

QGIS Processing plugin for rockfall risk assessment based on the
IMIRILAND methodology for landslides in mountainous areas.

Methodology under the scientific supervision of Marta Castelli.
Designed and implemented by Seyedmostafa Moeini, with technical
support from Stefano Campus.
"""

__author__ = "Seyedmostafa Moeini"
__copyright__ = "Copyright (C) 2026 Seyedmostafa Moeini"
__license__ = "GPL-2.0-or-later"

import os
import json

from qgis.PyQt.QtCore import QCoreApplication, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class QRADEAssistantDialog(QDialog):
    """Small rule-based helper dialog for opening QRADE reports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_output_folder = None
        self.setWindowTitle(QCoreApplication.translate("QRADE", "QRADE Smart Assistant"))
        self.resize(680, 620)
        self._build_ui()
        self._set_status("Select a QRADE result folder to inspect available reports and deliverables.")

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("<b>QRADE Smart Assistant</b>")
        layout.addWidget(title)

        before_title = QLabel("<b>Before running QRADE</b>")
        layout.addWidget(before_title)

        self.edit_risk_values_button = QPushButton("Edit Risk Assessment Values")
        layout.addWidget(self.edit_risk_values_button)

        risk_values_help = QLabel(
            "Create a custom risk-value CSV before running QRADE. The classification column is locked. "
            "Edit numeric values only, save the CSV, then select it in the Processing dialog when using "
            "Manual risk-value table mode."
        )
        risk_values_help.setWordWrap(True)
        layout.addWidget(risk_values_help)

        after_title = QLabel("<b>After running QRADE</b>")
        layout.addWidget(after_title)

        self.select_folder_button = QPushButton("Select QRADE Result Folder")
        layout.addWidget(self.select_folder_button)

        reports_title = QLabel("<b>Reports</b>")
        layout.addWidget(reports_title)

        reports_button_layout = QHBoxLayout()
        self.open_webgis_button = QPushButton("Open Interactive Risk Dashboard")
        self.open_qa_qc_button = QPushButton("Open QA/QC Report")

        reports_button_layout.addWidget(self.open_webgis_button)
        reports_button_layout.addWidget(self.open_qa_qc_button)
        layout.addLayout(reports_button_layout)

        bim_title = QLabel("<b>BIM Deliverables</b>")
        layout.addWidget(bim_title)

        bim_button_layout = QHBoxLayout()
        self.open_bim_csv_button = QPushButton("Open BIM-ready CSV")
        self.open_ifc_mapping_button = QPushButton("Open IFC GUID Mapping Template")
        self.open_bcf_folder_button = QPushButton("Open BCF Issues Folder")

        bim_button_layout.addWidget(self.open_bim_csv_button)
        bim_button_layout.addWidget(self.open_ifc_mapping_button)
        bim_button_layout.addWidget(self.open_bcf_folder_button)
        layout.addLayout(bim_button_layout)

        self.status_area = QTextEdit()
        self.status_area.setReadOnly(True)
        layout.addWidget(self.status_area)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.select_folder_button.clicked.connect(self.select_output_folder)
        self.open_qa_qc_button.clicked.connect(self.open_qa_qc_report)
        self.open_webgis_button.clicked.connect(self.open_webgis_report)
        self.edit_risk_values_button.clicked.connect(self.open_risk_values_editor)
        self.open_bim_csv_button.clicked.connect(self.open_bim_ready_csv)
        self.open_ifc_mapping_button.clicked.connect(self.open_ifc_guid_mapping_template)
        self.open_bcf_folder_button.clicked.connect(self.open_bcf_issues_folder)

    def _set_status(self, message):
        self.status_area.setPlainText(message)

    def _append_status(self, message):
        current = self.status_area.toPlainText()
        self.status_area.setPlainText(f"{current}\n{message}" if current else message)

    def _show_message(self, title, message):
        self._append_status(message)
        QMessageBox.information(self, title, message)

    def _path(self, *parts):
        if not self.selected_output_folder:
            return None
        return os.path.join(self.selected_output_folder, *parts)

    def _read_manifest(self):
        manifest_path = self._path("qrade_output_manifest.json")
        if not manifest_path or not os.path.exists(manifest_path):
            return None
        try:
            with open(manifest_path, "r", encoding="utf-8") as manifest_file:
                data = json.load(manifest_file)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _manifest_artifact_path(self, section, key):
        manifest = self._read_manifest()
        artifacts = manifest.get("artifacts", {}) if manifest else {}
        section_data = artifacts.get(section, {})
        if isinstance(section_data, dict):
            relative_path = section_data.get(key)
        elif key is None:
            relative_path = section_data
        else:
            relative_path = None
        if not relative_path or not self.selected_output_folder:
            return None
        return os.path.join(self.selected_output_folder, relative_path.replace("/", os.sep))

    def _artifact_candidates(self, section, key, organized_parts, legacy_parts):
        candidates = []
        manifest_path = self._manifest_artifact_path(section, key)
        if manifest_path:
            candidates.append(manifest_path)
        if organized_parts:
            candidates.append(self._path(*organized_parts))
        if legacy_parts:
            candidates.append(self._path(*legacy_parts))

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            normalized = os.path.abspath(candidate)
            if normalized not in seen:
                seen.add(normalized)
                unique_candidates.append(candidate)
        return unique_candidates

    def _resolve_artifact(self, section, key, organized_parts, legacy_parts, expect_dir=False):
        candidates = self._artifact_candidates(section, key, organized_parts, legacy_parts)
        exists = os.path.isdir if expect_dir else os.path.exists
        for candidate in candidates:
            if exists(candidate):
                return candidate
        return candidates[0] if candidates else None

    def _is_qrade_output_folder(self, folder_path):
        if not folder_path:
            return False
        markers = [
            os.path.join(folder_path, "qrade_output_manifest.json"),
            os.path.join(folder_path, "summary", "summary.json"),
            os.path.join(folder_path, "reports", "qa_qc", "qrade_qa_qc_report.html"),
            os.path.join(folder_path, "reports", "web_report", "index.html"),
            os.path.join(folder_path, "bim", "qrade_bim_risk.csv"),
            os.path.join(folder_path, "bim", "qrade_ifc_guid_mapping_template.csv"),
            os.path.join(folder_path, "bim", "bcf_issues"),
            os.path.join(folder_path, "summary.json"),
            os.path.join(folder_path, "qa_qc", "qrade_qa_qc_report.html"),
            os.path.join(folder_path, "web_report", "index.html"),
            os.path.join(folder_path, "qrade_bim_risk.csv"),
            os.path.join(folder_path, "qrade_ifc_guid_mapping_template.csv"),
            os.path.join(folder_path, "bcf_issues"),
        ]
        return any(os.path.exists(path) for path in markers)

    def _update_folder_status(self):
        if not self.selected_output_folder:
            self._set_status("No QRADE output folder selected.")
            return

        summary_path = self._resolve_artifact("summary", "json", ("summary", "summary.json"), ("summary.json",))
        qa_qc_path = self._resolve_artifact(
            "reports",
            "qa_qc_html",
            ("reports", "qa_qc", "qrade_qa_qc_report.html"),
            ("qa_qc", "qrade_qa_qc_report.html"),
        )
        webgis_path = self._resolve_artifact(
            "reports",
            "web_report",
            ("reports", "web_report", "index.html"),
            ("web_report", "index.html"),
        )
        bim_csv_path = self._resolve_artifact("bim", "risk_csv", ("bim", "qrade_bim_risk.csv"), ("qrade_bim_risk.csv",))
        ifc_mapping_path = self._resolve_artifact(
            "bim",
            "ifc_guid_mapping_template",
            ("bim", "qrade_ifc_guid_mapping_template.csv"),
            ("qrade_ifc_guid_mapping_template.csv",),
        )
        bcf_folder_path = self._resolve_artifact("bim", "bcf_issues", ("bim", "bcf_issues"), ("bcf_issues",), expect_dir=True)
        bcf_zip_path = self._resolve_artifact(
            "bim",
            "bcfzip",
            ("bim", "bcf_issues", "qrade_rockfall_risk_issues.bcfzip"),
            ("bcf_issues", "qrade_rockfall_risk_issues.bcfzip"),
        )
        bcf_readme_path = self._resolve_artifact(
            "bim",
            "bcf_empty_case_readme",
            ("bim", "bcf_issues", "README_no_high_risk_issues.txt"),
            ("bcf_issues", "README_no_high_risk_issues.txt"),
        )

        lines = [
            f"Selected folder: {self.selected_output_folder}",
            "",
            f"summary.json: {'found' if os.path.exists(summary_path) else 'missing'}",
            f"QA/QC report: {'found' if os.path.exists(qa_qc_path) else 'missing'}",
            f"WebGIS report: {'found' if os.path.exists(webgis_path) else 'missing'}",
            f"BIM-ready CSV: {'found' if os.path.exists(bim_csv_path) else 'missing'}",
            f"IFC GUID mapping template: {'found' if os.path.exists(ifc_mapping_path) else 'missing'}",
            f"BCF issues folder: {'found' if os.path.isdir(bcf_folder_path) else 'missing'}",
        ]
        if os.path.exists(bcf_zip_path):
            lines.append("BCF issue package: found")
        elif os.path.exists(bcf_readme_path):
            lines.append("BCF issue package: no High/Critical issues generated; README found")
        else:
            lines.append("BCF issue package: missing")
        self._set_status("\n".join(lines))

    def select_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select QRADE Output Folder",
            self.selected_output_folder or "",
        )
        if not folder_path:
            return

        self.selected_output_folder = folder_path
        self._update_folder_status()
        if not self._is_qrade_output_folder(folder_path):
            self._show_message(
                "QRADE Smart Assistant",
                "The selected folder does not look like a QRADE output folder. "
                "Expected qrade_output_manifest.json, summary/summary.json, reports/qa_qc, reports/web_report, or legacy flat outputs.",
            )

    def _open_path(self, path, label, expect_dir=False):
        if not self.selected_output_folder:
            self._show_message("QRADE Smart Assistant", "Select a QRADE output folder first.")
            return

        exists = os.path.isdir if expect_dir else os.path.exists
        if not path or not exists(path):
            self._show_message("QRADE Smart Assistant", f"{label} was not found:\n{path}")
            return

        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self._show_message("QRADE Smart Assistant", f"Could not open {label}:\n{path}")
        else:
            self._append_status(f"Opened {label}: {path}")

    def _open_file(self, relative_parts, label):
        self._open_path(self._path(*relative_parts), label)

    def _open_folder(self, relative_parts, label):
        self._open_path(self._path(*relative_parts), label, expect_dir=True)

    def open_qa_qc_report(self):
        path = self._resolve_artifact(
            "reports",
            "qa_qc_html",
            ("reports", "qa_qc", "qrade_qa_qc_report.html"),
            ("qa_qc", "qrade_qa_qc_report.html"),
        )
        self._open_path(path, "QA/QC report")

    def open_webgis_report(self):
        path = self._resolve_artifact(
            "reports",
            "web_report",
            ("reports", "web_report", "index.html"),
            ("web_report", "index.html"),
        )
        self._open_path(path, "WebGIS report")

    def open_risk_values_editor(self):
        try:
            from .risk_values_editor_dialog import QRADERiskValuesEditorDialog
        except Exception:
            from risk_values_editor_dialog import QRADERiskValuesEditorDialog

        dialog = QRADERiskValuesEditorDialog(
            self,
            output_folder=self.selected_output_folder,
        )
        if hasattr(dialog, "exec"):
            dialog.exec()
        else:
            dialog.exec_()

    def open_bim_ready_csv(self):
        path = self._resolve_artifact("bim", "risk_csv", ("bim", "qrade_bim_risk.csv"), ("qrade_bim_risk.csv",))
        self._open_path(path, "BIM-ready CSV")

    def open_ifc_guid_mapping_template(self):
        path = self._resolve_artifact(
            "bim",
            "ifc_guid_mapping_template",
            ("bim", "qrade_ifc_guid_mapping_template.csv"),
            ("qrade_ifc_guid_mapping_template.csv",),
        )
        self._open_path(path, "IFC GUID mapping template")

    def open_bcf_issues_folder(self):
        bcf_folder_path = self._resolve_artifact("bim", "bcf_issues", ("bim", "bcf_issues"), ("bcf_issues",), expect_dir=True)
        bcf_zip_path = self._resolve_artifact(
            "bim",
            "bcfzip",
            ("bim", "bcf_issues", "qrade_rockfall_risk_issues.bcfzip"),
            ("bcf_issues", "qrade_rockfall_risk_issues.bcfzip"),
        )
        bcf_readme_path = self._resolve_artifact(
            "bim",
            "bcf_empty_case_readme",
            ("bim", "bcf_issues", "README_no_high_risk_issues.txt"),
            ("bcf_issues", "README_no_high_risk_issues.txt"),
        )

        if bcf_folder_path and os.path.isdir(bcf_folder_path):
            if os.path.exists(bcf_zip_path):
                self._append_status(f"BCF issue package found: {bcf_zip_path}")
            elif os.path.exists(bcf_readme_path):
                self._append_status(
                    "No High/Critical BCF issues were generated; empty-case README found: "
                    f"{bcf_readme_path}"
                )
        self._open_path(bcf_folder_path, "BCF issues folder", expect_dir=True)
