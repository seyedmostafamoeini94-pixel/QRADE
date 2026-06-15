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

import csv
import os
from datetime import datetime

from qgis.PyQt.QtCore import QCoreApplication, QUrl, Qt
from qgis.PyQt.QtGui import QColor, QDesktopServices
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from qgis.core import QgsApplication


class QRADERiskValuesEditorDialog(QDialog):
    """Editor for creating validated custom QRADE risk-value CSV tables."""

    SYSTEM_COLUMNS = [
        'fid',
    ]

    REQUIRED_COLUMNS = [
        'classification',
        'exposure_physical',
        'exposure_social',
        'worth_physical',
        'worth_social',
        'phy_vul_sub_kj_lt50',
        'phy_vul_sub_kj_50_150',
        'phy_vul_sub_kj_150_250',
        'phy_vul_sub_kj_250_400',
        'phy_vul_sub_kj_400_550',
        'phy_vul_sub_kj_gt550',
        'soc_vul_sub_kj_lt50',
        'soc_vul_sub_kj_50_150',
        'soc_vul_sub_kj_150_250',
        'soc_vul_sub_kj_250_400',
        'soc_vul_sub_kj_400_550',
        'soc_vul_sub_kj_gt550',
        'phy_vul_urb_kj_lt50',
        'phy_vul_urb_kj_50_150',
        'phy_vul_urb_kj_150_250',
        'phy_vul_urb_kj_400_550',
        'phy_vul_urb_kj_250_400',
        'phy_vul_urb_kj_gt550',
        'soc_vul_urb_kj_lt50',
        'soc_vul_urb_kj_50_150',
        'soc_vul_urb_kj_150_250',
        'soc_vul_urb_kj_250_400',
        'soc_vul_urb_kj_400_550',
        'soc_vul_urb_kj_gt550',
    ]

    def __init__(self, parent=None, output_folder=None):
        super().__init__(parent)
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_table_path = os.path.join(self.plugin_dir, 'Input', 'classification_table.csv')
        self.manual_template_path = os.path.join(self.plugin_dir, 'Templates', 'classification_table_manual.csv')
        self.output_folder = output_folder
        self.current_csv_path = None
        self.last_saved_csv_path = None
        self.last_validation = None

        self.setWindowTitle(QCoreApplication.translate('QRADE', 'QRADE Risk Assessment Values Editor'))
        self.resize(1000, 700)
        self._build_ui()
        self._load_csv(self.manual_template_path, 'manual risk-value template')
        self._set_status(
            'Manual template loaded. Edit numeric values, save a custom CSV, then select that saved CSV '
            'in the QRADE Processing dialog when using Manual risk-value table mode.'
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel('<b>QRADE Risk Assessment Values Editor</b>')
        layout.addWidget(title)

        description = QLabel(
            'Edit numeric QRADE risk assessment values and save a validated custom CSV.'
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        button_layout = QHBoxLayout()
        self.open_custom_button = QPushButton('Open Custom CSV')
        self.validate_button = QPushButton('Validate Table')
        self.save_button = QPushButton('Save Custom CSV')
        self.reset_button = QPushButton('Reset to Manual Template')
        self.open_custom_tables_folder_button = QPushButton('Open Custom Tables Folder')

        button_layout.addWidget(self.open_custom_button)
        button_layout.addWidget(self.validate_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.open_custom_tables_folder_button)
        layout.addLayout(button_layout)

        self.table_widget = QTableWidget()
        layout.addWidget(self.table_widget, 1)

        self.status_area = QTextEdit()
        self.status_area.setReadOnly(True)
        layout.addWidget(self.status_area)

        close_button = QPushButton('Close')
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.open_custom_button.clicked.connect(self.open_custom_csv)
        self.validate_button.clicked.connect(self.validate_table)
        self.save_button.clicked.connect(self.save_custom_csv)
        self.reset_button.clicked.connect(self.reset_to_manual_template)
        self.open_custom_tables_folder_button.clicked.connect(self.open_custom_tables_folder)

    def _editable_flag(self):
        try:
            return Qt.ItemFlag.ItemIsEditable
        except AttributeError:
            return Qt.ItemIsEditable

    def _set_status(self, message):
        self.status_area.setPlainText(message)

    def _append_status(self, message):
        current = self.status_area.toPlainText()
        self.status_area.setPlainText(f'{current}\n{message}' if current else message)

    def _show_message(self, title, message):
        self._append_status(message)
        QMessageBox.information(self, title, message)

    def _confirm_warning_save(self, message):
        box = QMessageBox(self)
        box.setWindowTitle('QRADE Risk Assessment Values Editor')
        box.setText(message)
        try:
            accept_role = QMessageBox.ButtonRole.AcceptRole
            reject_role = QMessageBox.ButtonRole.RejectRole
        except AttributeError:
            accept_role = QMessageBox.AcceptRole
            reject_role = QMessageBox.RejectRole
        save_button = box.addButton('Save Anyway', accept_role)
        box.addButton('Cancel', reject_role)
        if hasattr(box, 'exec'):
            box.exec()
        else:
            box.exec_()
        return box.clickedButton() == save_button

    def reset_to_manual_template(self):
        self._load_csv(self.manual_template_path, 'manual risk-value template')
        self.last_saved_csv_path = None
        self.validate_table()
        self._append_status(
            'Packaged manual template reloaded. '
            'The template file was not modified.'
        )

    def open_custom_csv(self):
        csv_path, _ = QFileDialog.getOpenFileName(
            self,
            'Open Custom Risk Table CSV',
            self._user_risk_table_library_dir(),
            'CSV Files (*.csv);;All Files (*.*)',
        )
        if csv_path:
            self._load_csv(csv_path, 'custom risk-value table')
            self.validate_table()

    def _load_csv(self, csv_path, label):
        if not csv_path or not os.path.exists(csv_path):
            self._show_message('QRADE Risk Assessment Values Editor', f'Could not find {label}:\n{csv_path}')
            return

        try:
            with open(csv_path, newline='', encoding='utf-8-sig') as csv_file:
                reader = csv.reader(csv_file)
                rows = list(reader)
        except Exception as e:
            self._show_message('QRADE Risk Assessment Values Editor', f'Could not read CSV file:\n{csv_path}\n{e}')
            return

        if not rows:
            self.table_widget.clear()
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.current_csv_path = csv_path
            self._set_status(f'Loaded empty CSV file: {csv_path}')
            return

        header = rows[0]
        data_rows = rows[1:]
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(header))
        self.table_widget.setRowCount(len(data_rows))
        self.table_widget.setHorizontalHeaderLabels(header)

        classification_index = header.index('classification') if 'classification' in header else -1
        system_column_indexes = {
            index for index, column_name in enumerate(header)
            if column_name in self.SYSTEM_COLUMNS
        }
        editable_flag = self._editable_flag()
        locked_color = QColor(242, 242, 242)

        for row_index, row in enumerate(data_rows):
            for column_index, _column_name in enumerate(header):
                value = row[column_index] if column_index < len(row) else ''
                item = QTableWidgetItem(value)
                if column_index == classification_index or column_index in system_column_indexes:
                    item.setFlags(item.flags() & ~editable_flag)
                    item.setBackground(locked_color)
                    item.setToolTip('System columns and classification names are locked in this editor version.')
                self.table_widget.setItem(row_index, column_index, item)

        try:
            self.table_widget.resizeColumnsToContents()
        except Exception:
            pass

        self.current_csv_path = csv_path
        self.last_validation = None
        self._set_status(
            f'Loaded {label}: {csv_path}\n'
            f'Rows: {len(data_rows)}; columns: {len(header)}\n'
            'Classification column is locked when present.'
        )

    def _table_data(self):
        headers = []
        for column_index in range(self.table_widget.columnCount()):
            header_item = self.table_widget.horizontalHeaderItem(column_index)
            headers.append(header_item.text().strip() if header_item else '')

        rows = []
        for row_index in range(self.table_widget.rowCount()):
            row = []
            for column_index in range(self.table_widget.columnCount()):
                item = self.table_widget.item(row_index, column_index)
                row.append(item.text().strip() if item else '')
            rows.append(row)
        return headers, rows

    def validate_table(self):
        result = self._validate_table_data()
        self.last_validation = result
        lines = [f'Validation severity: {result["severity"]}', '']
        lines.extend(f'{severity}: {message}' for severity, message in result['messages'])
        self._set_status('\n'.join(lines))
        return result

    def _validate_table_data(self):
        headers, rows = self._table_data()
        messages = []
        critical_count = 0
        warning_count = 0

        def add(severity, message):
            nonlocal critical_count, warning_count
            messages.append((severity, message))
            if severity == 'CRITICAL':
                critical_count += 1
            elif severity == 'WARNING':
                warning_count += 1

        if not headers:
            add('CRITICAL', 'No table is loaded.')
            return {'severity': 'CRITICAL', 'messages': messages}

        missing_columns = [column for column in self.REQUIRED_COLUMNS if column not in headers]
        if missing_columns:
            add('CRITICAL', 'Missing required column(s): ' + ', '.join(missing_columns))

        allowed_columns = set(self.REQUIRED_COLUMNS) | set(self.SYSTEM_COLUMNS)
        extra_columns = [column for column in headers if column and column not in allowed_columns]
        if extra_columns:
            add('WARNING', 'Unexpected extra column(s): ' + ', '.join(extra_columns))

        if not rows:
            add('CRITICAL', 'Table must contain at least one data row.')
        elif len(rows) < 2:
            add('WARNING', 'Table has very few rows; confirm this is intentional.')

        header_index = {name: index for index, name in enumerate(headers)}
        classification_index = header_index.get('classification')
        classifications = []
        other_row = None

        if classification_index is not None:
            for row_number, row in enumerate(rows, start=2):
                classification = row[classification_index].strip() if classification_index < len(row) else ''
                if not classification:
                    add('CRITICAL', f'Empty classification value on row {row_number}.')
                else:
                    classifications.append(classification)
                    if classification == 'Other':
                        other_row = row
            duplicates = sorted({value for value in classifications if classifications.count(value) > 1})
            if duplicates:
                add('CRITICAL', 'Duplicate classification value(s): ' + ', '.join(duplicates))
            if 'Other' not in classifications:
                add(
                    'CRITICAL',
                    'Missing required official QRADE class: Other. '
                    'Click Reset to Manual Template or open a complete custom table, then save a new custom CSV.'
                )

        numeric_columns = [column for column in self.REQUIRED_COLUMNS if column != 'classification' and column in header_index]
        for row_number, row in enumerate(rows, start=2):
            for column in numeric_columns:
                column_index = header_index[column]
                value = row[column_index].strip() if column_index < len(row) else ''
                if value == '':
                    add('CRITICAL', f'Empty numeric value at row {row_number}, column {column}.')
                    continue
                try:
                    numeric_value = float(value)
                except Exception:
                    add('CRITICAL', f'Invalid numeric value at row {row_number}, column {column}: {value}')
                    continue
                if numeric_value < 0 or numeric_value > 1:
                    add('CRITICAL', f'Numeric value outside 0..1 at row {row_number}, column {column}: {value}')

        if other_row is not None:
            non_zero_other = []
            for column in numeric_columns:
                column_index = header_index[column]
                value = other_row[column_index].strip() if column_index < len(other_row) else ''
                try:
                    if float(value) != 0:
                        non_zero_other.append(column)
                except Exception:
                    pass
            if non_zero_other:
                add('WARNING', 'Other row has non-zero value(s): ' + ', '.join(non_zero_other))

        if critical_count:
            severity = 'CRITICAL'
        elif warning_count:
            severity = 'WARNING'
        else:
            severity = 'PASS'
            add('PASS', 'Table passed validation.')

        return {'severity': severity, 'messages': messages}

    def save_custom_csv(self):
        validation = self.validate_table()
        if validation['severity'] == 'CRITICAL':
            self._show_message(
                'QRADE Risk Assessment Values Editor',
                'Cannot save custom CSV because validation has CRITICAL errors.'
            )
            return
        if validation['severity'] == 'WARNING':
            if not self._confirm_warning_save(
                'Validation has WARNING items. Save the custom CSV anyway?'
            ):
                self._append_status('Save cancelled by user.')
                return

        save_folder = self._default_save_folder()
        if not save_folder:
            self._append_status('Save cancelled: no folder selected.')
            return

        try:
            os.makedirs(save_folder, exist_ok=True)
        except Exception as e:
            self._show_message('QRADE Risk Assessment Values Editor', f'Could not create save folder:\n{save_folder}\n{e}')
            return

        target_path = self._unique_custom_csv_path(save_folder)
        if self._is_packaged_table_path(target_path) or self._is_packaged_table_folder(save_folder):
            self._show_message(
                'QRADE Risk Assessment Values Editor',
                'Custom risk tables cannot be saved inside packaged Input/ or Templates/ folders.'
            )
            return

        headers, rows = self._table_data()
        try:
            with open(target_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(headers)
                writer.writerows(rows)
        except Exception as e:
            self._show_message('QRADE Risk Assessment Values Editor', f'Could not save custom CSV:\n{target_path}\n{e}')
            return

        self.last_saved_csv_path = target_path
        self._set_status(
            f'Custom risk-value CSV saved:\n{target_path}\n\n'
            'Select this CSV in the QRADE Processing dialog Manual Classification Table field.'
        )

    def _default_save_folder(self):
        return self._user_risk_table_library_dir()

    def _user_risk_table_library_dir(self):
        return os.path.join(QgsApplication.qgisSettingsDirPath(), 'QRADE', 'risk_tables')

    def _unique_custom_csv_path(self, folder_path):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        base_name = f'qrade_risk_values_custom_{timestamp}'
        candidate = os.path.join(folder_path, f'{base_name}.csv')
        suffix = 1
        while os.path.exists(candidate):
            candidate = os.path.join(folder_path, f'{base_name}_{suffix}.csv')
            suffix += 1
        return candidate

    def _is_packaged_table_path(self, path):
        normalized = os.path.abspath(path)
        packaged_paths = {
            os.path.abspath(self.default_table_path),
            os.path.abspath(self.manual_template_path),
        }
        return normalized in packaged_paths

    def _is_packaged_table_folder(self, folder_path):
        normalized = os.path.abspath(folder_path)
        packaged_folders = {
            os.path.abspath(os.path.join(self.plugin_dir, 'Input')),
            os.path.abspath(os.path.join(self.plugin_dir, 'Templates')),
        }
        return normalized in packaged_folders

    def open_custom_tables_folder(self):
        folder_path = self._user_risk_table_library_dir()
        try:
            os.makedirs(folder_path, exist_ok=True)
        except Exception as e:
            self._show_message('QRADE Risk Assessment Values Editor', f'Could not create custom tables folder:\n{folder_path}\n{e}')
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path)):
            self._show_message('QRADE Risk Assessment Values Editor', f'Could not open custom tables folder:\n{folder_path}')
        else:
            self._append_status(f'Opened custom tables folder: {folder_path}')
