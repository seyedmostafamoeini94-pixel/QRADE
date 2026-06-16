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
import csv
import html
import json
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
import math
import xml.etree.ElementTree as ET

from qgis import gui, processing
from qgis.PyQt.QtCore import QUrl, Qt
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget
from qgis.core import (
    Qgis,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingMultiStepFeedback,
    QgsProcessingUtils,
    QgsProcessingOutputHtml,
    QgsProcessingOutputString,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsFeatureRequest,
    QgsProject,
    QgsVectorLayer,
)


class QRADEAlgorithmDialog(
    gui.QgsProcessingAlgorithmDialogBase,
    gui.QgsProcessingParametersGenerator,
    gui.QgsProcessingContextGenerator,
):
    """Custom Processing dialog with dynamic show/hide behavior."""

    _INPUT_PARAMETER_ORDER = [
        'landcover_source',
        'landcover_manual',
        'extent',
        'risk_value_mode',
        'classification_table_manual',
        'area_type',
        'mean_energy',
        'temporal_mode',
        'number_of_events',
        'time_span_years',
        'return_period_years',
        'temporal_probability_manual',
        'output_folder',
        'save_landcover',
        'save_riskassessment',
        'save_runout',
    ]

    def __init__(self, algorithm, parent=None):
        super().__init__(
            parent,
            flags=Qt.WindowFlags(),
            mode=gui.QgsProcessingAlgorithmDialogBase.DialogMode.Single,
        )
        self._context = QgsProcessingContext()
        self._context.setProject(QgsProject.instance())

        self._wrappers = {}
        self._rows = {}
        self.setAlgorithm(algorithm)
        self.setModal(True)

        self._panel = gui.QgsPanelWidget()
        self._panel.setLayout(self._build_dialog())
        self.setMainWidget(self._panel)

        self._refresh_visibility()

    def _build_dialog(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        widget_context = gui.QgsProcessingParameterWidgetContext()
        try:
            widget_context.setProject(QgsProject.instance())
        except Exception:
            pass

        try:
            from qgis.utils import iface
            if iface is not None:
                widget_context.setMapCanvas(iface.mapCanvas())
                widget_context.setActiveLayer(iface.activeLayer())
        except Exception:
            pass

        for name in self._INPUT_PARAMETER_ORDER:
            param = self.algorithm().parameterDefinition(name)
            if param is None:
                continue

            wrapper = gui.QgsGui.processingGuiRegistry().createParameterWidgetWrapper(
                param,
                gui.QgsProcessingGui.WidgetType.Standard
            )
            if wrapper is None:
                continue

            wrapper.setDialog(self)
            wrapper.setWidgetContext(widget_context)
            wrapper.registerProcessingContextGenerator(self)
            wrapper.registerProcessingParametersGenerator(self)

            label = wrapper.createWrappedLabel()
            widget = wrapper.createWrappedWidget(self._context)

            default_value = param.defaultValue()
            if default_value is not None:
                try:
                    wrapper.setParameterValue(default_value, self._context)
                except Exception:
                    pass

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            if label is not None:
                try:
                    label.setText(label.text().replace(' [optional]', ''))
                except Exception:
                    pass
                label.setMinimumWidth(260)
                row_layout.addWidget(label)

            if widget is not None:
                row_layout.addWidget(widget, 1)

            layout.addWidget(row_widget)

            self._wrappers[name] = wrapper
            self._rows[name] = row_widget

            try:
                wrapper.widgetValueHasChanged.connect(self._on_parameter_changed)
            except Exception:
                pass

        all_wrappers = list(self._wrappers.values())
        for wrapper in all_wrappers:
            try:
                wrapper.postInitialize(all_wrappers)
            except Exception:
                pass
        layout.addStretch(1)
        return layout

    def _on_parameter_changed(self, *args, **kwargs):
        self._refresh_visibility()

    def _enum_index(self, name):
        wrapper = self._wrappers.get(name)
        if wrapper is None:
            return 0
        value = wrapper.parameterValue()
        if isinstance(value, list):
            return int(value[0]) if value else 0
        try:
            return int(value)
        except Exception:
            return 0

    def _set_row_visible(self, name, visible):
        row = self._rows.get(name)
        if row is not None:
            row.setVisible(bool(visible))

    def _refresh_visibility(self):
        landcover_source = self._enum_index('landcover_source')
        risk_value_mode = self._enum_index('risk_value_mode')
        temporal_mode = self._enum_index('temporal_mode')

        self._set_row_visible('landcover_manual', landcover_source == 1)
        self._set_row_visible('extent', landcover_source == 0)

        self._set_row_visible('classification_table_manual', risk_value_mode == 1)

        auto_temporal = temporal_mode == 1
        manual_temporal = temporal_mode == 2

        self._set_row_visible('number_of_events', auto_temporal)
        self._set_row_visible('time_span_years', auto_temporal)
        self._set_row_visible('return_period_years', auto_temporal)
        self._set_row_visible('temporal_probability_manual', manual_temporal)

    def setParameters(self, parameters):
        for name, value in (parameters or {}).items():
            wrapper = self._wrappers.get(name)
            if wrapper is None:
                continue
            try:
                wrapper.setParameterValue(value, self._context)
            except Exception:
                pass
        self._refresh_visibility()

    def createProcessingParameters(self, flags=gui.QgsProcessingParametersGenerator.Flags()):
        parameters = {}
        for name, wrapper in self._wrappers.items():
            value = wrapper.parameterValue()
            if value is None:
                continue

            if flags & gui.QgsProcessingParametersGenerator.Flag.SkipDefaultValueParameters:
                param = self.algorithm().parameterDefinition(name)
                if param is not None and value == param.defaultValue():
                    continue

            parameters[name] = value
        return parameters

    def processingContext(self):
        return self._context

    def createFeedback(self):
        try:
            return super().createFeedback()
        except Exception:
            try:
                return gui.QgsProcessingAlgorithmDialogBase.createFeedback(self)
            except Exception:
                return QgsProcessingFeedback()

    def _switch_to_log_tab(self):
        for method_name in ('showLog', 'openLog', 'setLogVisible'):
            method = getattr(self, method_name, None)
            if callable(method):
                try:
                    if method_name == 'setLogVisible':
                        method(True)
                    else:
                        method()
                    return
                except Exception:
                    pass

        try:
            for tab in self.findChildren(QTabWidget):
                for i in range(tab.count()):
                    if 'log' in tab.tabText(i).lower():
                        tab.setCurrentIndex(i)
                        return
        except Exception:
            pass

    def runAlgorithm(self):
        self._switch_to_log_tab()

        try:
            parameters = self.createProcessingParameters()
            ok, message = self.algorithm().checkParameterValues(parameters, self._context)
            if not ok:
                self.messageBar().pushMessage(
                    'Invalid parameters',
                    message,
                    level=Qgis.MessageLevel.Warning,
                )
                return

            feedback = self.createFeedback()
            results = processing.run(
                self.algorithm(),
                parameters,
                context=self._context,
                feedback=feedback,
            )
            self.setResults(results)
            self._switch_to_log_tab()

            out_folder = results.get('OutputFolder', '')
            success_message = f'Finished successfully. Results saved in: {out_folder}' if out_folder else 'Finished successfully.'
            self.messageBar().pushMessage(
                'QRADE',
                success_message,
                level=Qgis.MessageLevel.Success,
            )
        except Exception as e:
            self._switch_to_log_tab()
            self.messageBar().pushMessage(
                'QRADE',
                str(e),
                level=Qgis.MessageLevel.Critical,
            )

class QRADEAlgorithm(QgsProcessingAlgorithm):

    _REQUIRED_CLASSIFICATION_TABLE_COLUMNS = [
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
        'phy_vul_urb_kj_250_400',
        'phy_vul_urb_kj_400_550',
        'phy_vul_urb_kj_gt550',
        'soc_vul_urb_kj_lt50',
        'soc_vul_urb_kj_50_150',
        'soc_vul_urb_kj_150_250',
        'soc_vul_urb_kj_250_400',
        'soc_vul_urb_kj_400_550',
        'soc_vul_urb_kj_gt550',
    ]

    def _validate_classification_table(self, csv_path):
        if not csv_path:
            raise QgsProcessingException('Classification table path is empty.')
        if not os.path.exists(csv_path):
            raise QgsProcessingException(f'Classification table not found: {csv_path}')

        try:
            with open(csv_path, newline='', encoding='utf-8-sig') as csv_file:
                reader = csv.reader(csv_file)
                try:
                    header = next(reader)
                except StopIteration:
                    raise QgsProcessingException(f'Classification table is empty: {csv_path}')

                missing_columns = [
                    column for column in self._REQUIRED_CLASSIFICATION_TABLE_COLUMNS
                    if column not in header
                ]
                if missing_columns:
                    raise QgsProcessingException(
                        'Classification table is missing required column(s): '
                        + ', '.join(missing_columns)
                    )

                expected_columns = len(header)
                classification_index = header.index('classification')
                values = set()
                duplicates = set()
                data_rows = 0

                for line_number, row in enumerate(reader, start=2):
                    data_rows += 1
                    if len(row) != expected_columns:
                        raise QgsProcessingException(
                            f'Classification table row {line_number} has {len(row)} columns '
                            f'but header has {expected_columns}.'
                        )

                    classification_value = row[classification_index].strip()
                    if not classification_value:
                        raise QgsProcessingException(
                            f'Classification table contains an empty classification value on line {line_number}.'
                        )
                    if classification_value in values:
                        duplicates.add(classification_value)
                    values.add(classification_value)

        except QgsProcessingException:
            raise
        except Exception as e:
            raise QgsProcessingException(f'Could not read classification table: {csv_path}\n{e}')

        if data_rows == 0:
            raise QgsProcessingException(f'Classification table must contain at least one data row: {csv_path}')
        if duplicates:
            raise QgsProcessingException(
                'Classification table contains duplicate classification value(s): '
                + ', '.join(sorted(duplicates))
            )

        return values

    def _validate_landcover_classification_values(self, landcover_output, context, table_values):
        layer = landcover_output if hasattr(landcover_output, 'getFeatures') else None
        if layer is None:
            layer = QgsProcessingUtils.mapLayerFromString(str(landcover_output), context)
        if layer is None or not layer.isValid():
            layer = QgsVectorLayer(str(landcover_output), 'LandCoverForValidation', 'ogr')
        if layer is None or not layer.isValid():
            raise QgsProcessingException('Could not validate land-cover classification values before joining the classification table.')

        classification_index = layer.fields().indexOf('classification')
        if classification_index < 0:
            raise QgsProcessingException("Land-cover layer is missing the required field: 'classification'.")

        landcover_values = set()
        # Use the field-name overload for QGIS 3/4 binding compatibility.
        request = QgsFeatureRequest().setSubsetOfAttributes(['classification'], layer.fields())
        for feature in layer.getFeatures(request):
            value = feature[classification_index]
            if value is None or str(value).strip() == '':
                raise QgsProcessingException('Land-cover layer contains empty/null classification values.')
            landcover_values.add(str(value).strip())

        missing_values = sorted(landcover_values - set(table_values))
        if missing_values:
            raise QgsProcessingException(
                'Classification table is missing values required by the land-cover layer: '
                + ', '.join(missing_values)
                + '. Open the Risk Assessment Values Editor, reset to the manual template, '
                'save a new custom CSV, and select it in Manual table mode.'
            )

    def _validate_crs_assumptions(self, mean_energy_layer, landcover_source, feedback):
        if mean_energy_layer is None or not mean_energy_layer.isValid():
            raise QgsProcessingException(
                'The kinetic-energy raster is not valid. Please select a valid kinetic-energy raster before running QRADE.'
            )

        raster_crs = mean_energy_layer.crs()
        if not raster_crs.isValid():
            raise QgsProcessingException(
                'The kinetic-energy raster has no valid CRS. Please assign a valid projected CRS before running QRADE.'
            )

        project_crs = QgsProject.instance().crs()
        if not project_crs.isValid():
            raise QgsProcessingException(
                'The QGIS project CRS is not valid. Please set the project CRS to match the kinetic-energy raster CRS.'
            )

        project_authid = project_crs.authid() or project_crs.description()
        raster_authid = raster_crs.authid() or raster_crs.description()
        if project_crs != raster_crs:
            raise QgsProcessingException(
                f'QRADE currently requires the QGIS project CRS to match the kinetic-energy raster CRS. '
                f'Project CRS: {project_authid}; raster CRS: {raster_authid}. '
                'Please set the project CRS to the raster CRS and run again.'
            )

        if landcover_source == 0 and project_crs.isGeographic():
            raise QgsProcessingException(
                'Auto OSM mode requires a projected CRS in linear units. '
                'The current project CRS is geographic; road buffering would be invalid.'
            )

        feedback.pushInfo(
            f'CRS check passed: project CRS matches kinetic-energy raster CRS ({project_authid}).'
        )

    def _validate_output_folder(self, output_folder, feedback):
        if not output_folder:
            raise QgsProcessingException('Please select an output folder.')

        normalized_folder = os.path.abspath(os.path.expandvars(os.path.expanduser(output_folder)))

        try:
            os.makedirs(normalized_folder, exist_ok=True)
        except Exception as e:
            raise QgsProcessingException(f'Could not create output folder: {normalized_folder}\n{e}')

        if not os.path.isdir(normalized_folder):
            raise QgsProcessingException(f'The selected output path is not a folder: {normalized_folder}')

        test_file_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                prefix='qrade_write_test_',
                suffix='.tmp',
                dir=normalized_folder,
                delete=False,
                encoding='utf-8'
            ) as test_file:
                test_file_path = test_file.name
                test_file.write('QRADE output folder write test')
        except Exception as e:
            raise QgsProcessingException(f'QRADE cannot write to the selected output folder: {normalized_folder}\n{e}')
        finally:
            if test_file_path and os.path.exists(test_file_path):
                try:
                    os.remove(test_file_path)
                except Exception as e:
                    raise QgsProcessingException(
                        f'QRADE can create files in the selected output folder but could not remove a temporary test file: {test_file_path}\n{e}'
                    )

        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        try:
            inside_plugin_dir = os.path.commonpath([plugin_dir, normalized_folder]) == plugin_dir
        except Exception:
            inside_plugin_dir = False

        if inside_plugin_dir:
            warning_message = (
                'The selected output folder is inside the installed QRADE plugin directory. '
                'For normal use, choose a project or workspace folder outside the plugin installation path.'
            )
            try:
                feedback.pushWarning(warning_message)
            except Exception:
                feedback.pushInfo(warning_message)

        return normalized_folder

    def _get_output_paths(self, run_output_folder):
        root = run_output_folder
        paths = {
            'root': root,
            'gis_dir': os.path.join(root, 'gis'),
            'summary_dir': os.path.join(root, 'summary'),
            'bim_dir': os.path.join(root, 'bim'),
            'reports_dir': os.path.join(root, 'reports'),
            'risk_tables_dir': os.path.join(root, 'risk_tables'),
            'manifest_path': os.path.join(root, 'qrade_output_manifest.json'),
        }
        paths.update({
            'bcf_dir': os.path.join(paths['bim_dir'], 'bcf_issues'),
            'qa_qc_dir': os.path.join(paths['reports_dir'], 'qa_qc'),
            'web_report_dir': os.path.join(paths['reports_dir'], 'web_report'),
        })
        paths.update({
            'web_report_data_dir': os.path.join(paths['web_report_dir'], 'data'),
            'web_report_assets_dir': os.path.join(paths['web_report_dir'], 'assets'),
            'landcover_gpkg': os.path.join(paths['gis_dir'], 'landcover.gpkg'),
            'runout_gpkg': os.path.join(paths['gis_dir'], 'runout.gpkg'),
            'risk_assessment_gpkg': os.path.join(paths['gis_dir'], 'risk_assessment.gpkg'),
            'summary_json': os.path.join(paths['summary_dir'], 'summary.json'),
            'summary_csv': os.path.join(paths['summary_dir'], 'summary.csv'),
            'bim_csv': os.path.join(paths['bim_dir'], 'qrade_bim_risk.csv'),
            'bim_json': os.path.join(paths['bim_dir'], 'qrade_bim_risk.json'),
            'ifc_guid_template_csv': os.path.join(paths['bim_dir'], 'qrade_ifc_guid_mapping_template.csv'),
            'bcf_zip': os.path.join(paths['bcf_dir'], 'qrade_rockfall_risk_issues.bcfzip'),
            'bcf_readme': os.path.join(paths['bcf_dir'], 'README_no_high_risk_issues.txt'),
            'qa_qc_html': os.path.join(paths['qa_qc_dir'], 'qrade_qa_qc_report.html'),
            'qa_qc_json': os.path.join(paths['qa_qc_dir'], 'qrade_qa_qc_report.json'),
            'qa_qc_csv': os.path.join(paths['qa_qc_dir'], 'qrade_qa_qc_report.csv'),
            'web_report_index': os.path.join(paths['web_report_dir'], 'index.html'),
        })
        paths.update({
            'web_report_summary_json': os.path.join(paths['web_report_data_dir'], 'summary.json'),
            'web_report_summary_csv': os.path.join(paths['web_report_data_dir'], 'summary.csv'),
            'web_report_bim_json': os.path.join(paths['web_report_data_dir'], 'qrade_bim_risk.json'),
            'web_report_bim_csv': os.path.join(paths['web_report_data_dir'], 'qrade_bim_risk.csv'),
            'web_report_risk_geojson': os.path.join(paths['web_report_data_dir'], 'risk_assessment.geojson'),
            'web_report_landcover_geojson': os.path.join(paths['web_report_data_dir'], 'landcover.geojson'),
            'web_report_runout_geojson': os.path.join(paths['web_report_data_dir'], 'runout.geojson'),
            'web_report_icon': os.path.join(paths['web_report_assets_dir'], 'icon.png'),
        })
        return paths

    def _create_output_structure(self, run_output_folder):
        paths = self._get_output_paths(run_output_folder)
        for key in (
            'root',
            'gis_dir',
            'summary_dir',
            'bim_dir',
            'bcf_dir',
            'reports_dir',
            'qa_qc_dir',
            'web_report_dir',
            'web_report_data_dir',
            'web_report_assets_dir',
            'risk_tables_dir',
        ):
            os.makedirs(paths[key], exist_ok=True)
        return paths

    def _write_output_manifest(self, output_paths, run_metadata, feedback):
        root = output_paths['root']

        def rel(path):
            return os.path.relpath(path, root).replace(os.sep, '/')

        manifest = {
            'schema_version': '1.0',
            'generated_by': 'QRADE',
            'result_root': root,
            'created': run_metadata.get('timestamp'),
            'compatibility_note': (
                'QRADE Smart Assistant supports this organized structure and older flat result folders.'
            ),
            'artifacts': {
                'gis': {
                    'landcover': rel(output_paths['landcover_gpkg']),
                    'runout': rel(output_paths['runout_gpkg']),
                    'risk_assessment': rel(output_paths['risk_assessment_gpkg']),
                },
                'summary': {
                    'json': rel(output_paths['summary_json']),
                    'csv': rel(output_paths['summary_csv']),
                },
                'bim': {
                    'risk_csv': rel(output_paths['bim_csv']),
                    'risk_json': rel(output_paths['bim_json']),
                    'ifc_guid_mapping_template': rel(output_paths['ifc_guid_template_csv']),
                    'bcf_issues': rel(output_paths['bcf_dir']),
                    'bcfzip': rel(output_paths['bcf_zip']),
                    'bcf_empty_case_readme': rel(output_paths['bcf_readme']),
                },
                'reports': {
                    'qa_qc_html': rel(output_paths['qa_qc_html']),
                    'qa_qc_json': rel(output_paths['qa_qc_json']),
                    'qa_qc_csv': rel(output_paths['qa_qc_csv']),
                    'web_report': rel(output_paths['web_report_index']),
                    'web_report_data': rel(output_paths['web_report_data_dir']),
                    'web_report_assets': rel(output_paths['web_report_assets_dir']),
                },
                'risk_tables': {
                    'folder': rel(output_paths['risk_tables_dir']),
                    'used_risk_value_table': run_metadata.get('risk_value_table_copied_relative_path'),
                    'source_risk_value_table': run_metadata.get('risk_value_table_source_path'),
                },
            },
        }

        try:
            with open(output_paths['manifest_path'], 'w', encoding='utf-8') as manifest_file:
                json.dump(manifest, manifest_file, indent=2, sort_keys=True)
        except Exception as e:
            raise QgsProcessingException(f'Could not write QRADE output manifest: {output_paths["manifest_path"]}\n{e}')

        feedback.pushInfo(f'QRADE output manifest written: {output_paths["manifest_path"]}')
        return output_paths['manifest_path']

    def _copy_used_risk_value_table(self, class_table_path, output_paths, timestamp, feedback):
        if not class_table_path or not os.path.exists(class_table_path):
            raise QgsProcessingException(f'Could not copy used risk-value table; source not found: {class_table_path}')

        destination_path = os.path.join(output_paths['risk_tables_dir'], f'qrade_risk_values_used_{timestamp}.csv')
        try:
            os.makedirs(output_paths['risk_tables_dir'], exist_ok=True)
            shutil.copy2(class_table_path, destination_path)
        except Exception as e:
            raise QgsProcessingException(f'Could not copy used risk-value table to: {destination_path}\n{e}')

        relative_path = os.path.relpath(destination_path, output_paths['root']).replace(os.sep, '/')
        feedback.pushInfo(f'Used risk-value table copied: {destination_path}')
        return destination_path, relative_path

    def _evaluate_temporal_probability(
        self,
        temporal_mode,
        manual_probability,
        event_count,
        observation_years,
        assessment_years,
        feedback
    ):
        mode_labels = {
            0: 'Time-Independent',
            1: 'Auto (Frequency-Based model)',
            2: 'Manual (Case-specific Volume-Based model)',
        }
        mode_label = mode_labels.get(temporal_mode)
        if mode_label is None:
            raise QgsProcessingException('Invalid temporal probability mode selected.')

        warnings = []
        low_quality = False

        def push_warning(message):
            if hasattr(feedback, 'pushWarning'):
                feedback.pushWarning(message)
            else:
                feedback.pushInfo(f'Warning: {message}')

        def add_warning(message, low=False):
            nonlocal low_quality
            warnings.append(message)
            if low:
                low_quality = True

        def require_finite_number(value, label):
            if value is None:
                raise QgsProcessingException(f'{label} is required.')
            try:
                number = float(value)
            except Exception:
                raise QgsProcessingException(f'{label} must be numeric.')
            if not math.isfinite(number):
                raise QgsProcessingException(f'{label} must be a finite number.')
            return number

        lambda_per_year = None
        expected_events = None
        equivalent_return_period_years = None

        if temporal_mode == 0:
            temporal_probability_value = 1.0

        elif temporal_mode == 1:
            event_count_number = require_finite_number(
                event_count,
                'Auto mode: number of recorded events (N)'
            )
            if not event_count_number.is_integer():
                raise QgsProcessingException('Auto mode: number of recorded events (N) must be an integer value.')
            if event_count_number < 0:
                raise QgsProcessingException('Auto mode: number of recorded events (N) must be >= 0.')
            event_count_int = int(event_count_number)

            observation_years = require_finite_number(
                observation_years,
                'Auto mode: observation period (Tobs)'
            )
            assessment_years = require_finite_number(
                assessment_years,
                'Auto mode: assessment time window (Tr)'
            )
            if observation_years <= 0:
                raise QgsProcessingException('Auto mode: observation period (Tobs) must be > 0 years.')
            if assessment_years <= 0:
                raise QgsProcessingException('Auto mode: assessment time window (Tr) must be > 0 years.')

            lambda_per_year = event_count_int / observation_years
            expected_events = lambda_per_year * assessment_years
            if lambda_per_year > 0:
                equivalent_return_period_years = 1.0 / lambda_per_year
            temporal_probability_value = 1.0 - math.exp(-lambda_per_year * assessment_years)
            temporal_probability_value = max(0.0, min(1.0, temporal_probability_value))

            if event_count_int == 0:
                add_warning(
                    'Zero recorded events should not silently imply zero hazard; consider a manual probability or scenario-based estimate.',
                    low=True
                )
            elif event_count_int < 5:
                add_warning('Very limited event record: N < 5.', low=True)
            elif event_count_int < 10:
                add_warning('Small event record: N < 10.')

            if observation_years < 5:
                add_warning('Very short observation period: Tobs < 5 years.', low=True)
            if assessment_years > 2 * observation_years:
                add_warning('Strong extrapolation warning: Tr > 2*Tobs.', low=True)
            elif assessment_years > observation_years:
                add_warning('Assessment time window exceeds observation period: Tr > Tobs.')

        elif temporal_mode == 2:
            temporal_probability_value = require_finite_number(
                manual_probability,
                'Manual mode: temporal probability P'
            )
            if temporal_probability_value < 0 or temporal_probability_value > 1:
                raise QgsProcessingException('Manual mode: temporal probability P must be between 0 and 1.')

        if temporal_mode != 0 and temporal_probability_value > 0.99:
            add_warning('Temporal probability is greater than 0.99 and behaves almost time-independent.', low=True)
        elif temporal_mode != 0 and temporal_probability_value > 0.95:
            add_warning('Temporal probability is greater than 0.95; review whether probability saturation is expected.')

        if temporal_mode == 0:
            temporal_probability_quality = 'TIME_INDEPENDENT'
        elif low_quality:
            temporal_probability_quality = 'LOW'
        elif warnings:
            temporal_probability_quality = 'CAUTION'
        else:
            temporal_probability_quality = 'ACCEPTABLE'

        diagnostics = {
            'temporal_probability_mode': mode_label,
            'temporal_probability_value': temporal_probability_value,
            'temporal_lambda_per_year': lambda_per_year,
            'temporal_expected_events': expected_events,
            'temporal_equivalent_return_period_years': equivalent_return_period_years,
            'temporal_probability_quality': temporal_probability_quality,
            'temporal_probability_warnings': warnings,
        }

        feedback.pushInfo(f'Temporal probability mode: {mode_label}')
        if lambda_per_year is not None:
            feedback.pushInfo(f'Temporal lambda: {lambda_per_year:.6g} 1/year')
            feedback.pushInfo(f'Temporal expected events: {expected_events:.6g}')
            if equivalent_return_period_years is None:
                feedback.pushInfo('Temporal equivalent return period: not available')
            else:
                feedback.pushInfo(f'Temporal equivalent return period: {equivalent_return_period_years:.6g} years')
        feedback.pushInfo(f'Temporal probability P_t: {temporal_probability_value:.6g}')
        feedback.pushInfo(f'Temporal probability quality: {temporal_probability_quality}')
        for warning in warnings:
            push_warning(f'Temporal probability warning: {warning}')

        return temporal_probability_value, diagnostics

    def _filter_risk_assessment_positive_energy(self, risk_layer_or_path, output_destination, context, feedback):
        feedback.pushInfo('Filtering Risk Assessment layer to features with energy_max > 0...')

        layer = risk_layer_or_path if hasattr(risk_layer_or_path, 'getFeatures') else None
        if layer is None:
            layer = QgsProcessingUtils.mapLayerFromString(str(risk_layer_or_path), context)
        if layer is None or not layer.isValid():
            layer = QgsVectorLayer(str(risk_layer_or_path), 'RiskAssessmentBeforeEnergyFilter', 'ogr')
        if layer is None or not layer.isValid():
            raise QgsProcessingException('Could not load the Risk Assessment layer before energy filtering.')

        field_names = [field.name() for field in layer.fields()]
        if 'energy_max' not in field_names:
            raise QgsProcessingException(
                'Could not filter Risk Assessment layer: required field energy_max was not found.'
            )

        def layer_count(vector_layer):
            count = vector_layer.featureCount()
            if count is not None and count >= 0:
                return int(count)
            return sum(1 for _ in vector_layer.getFeatures())

        original_count = layer_count(layer)
        expression = '"energy_max" IS NOT NULL AND "energy_max" > 0'
        filtered_output = processing.run(
            'native:extractbyexpression',
            {
                'INPUT': layer,
                'EXPRESSION': expression,
                'OUTPUT': output_destination,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        filtered_layer = QgsProcessingUtils.mapLayerFromString(str(filtered_output['OUTPUT']), context)
        if filtered_layer is None or not filtered_layer.isValid():
            filtered_layer = QgsVectorLayer(str(filtered_output['OUTPUT']), 'RiskAssessmentAfterEnergyFilter', 'ogr')
        if filtered_layer is None or not filtered_layer.isValid():
            raise QgsProcessingException('Could not load the filtered Risk Assessment layer.')

        filtered_count = layer_count(filtered_layer)
        removed_count = original_count - filtered_count
        feedback.pushInfo(
            'Risk Assessment energy filter: '
            f'kept {filtered_count} of {original_count} features; '
            f'removed {removed_count} features with null or zero energy_max.'
        )
        if filtered_count == 0:
            warning = (
                'No features have positive energy_max. Risk Assessment output will be empty. '
                'Check the kinetic-energy raster, runout overlap, and input extent.'
            )
            if hasattr(feedback, 'pushWarning'):
                feedback.pushWarning(warning)
            else:
                feedback.pushInfo(f'Warning: {warning}')

        return {
            'OUTPUT': filtered_output['OUTPUT'],
            'original_count': original_count,
            'filtered_count': filtered_count,
            'removed_count': removed_count,
            'expression': expression,
        }

    def _write_result_summary(self, risk_layer_or_path, output_paths, run_metadata, feedback):
        feedback.pushInfo('Writing QRADE result summary...')

        layer = risk_layer_or_path if hasattr(risk_layer_or_path, 'getFeatures') else None
        if layer is None:
            layer = QgsProcessingUtils.mapLayerFromString(str(risk_layer_or_path), QgsProcessingContext())
        if layer is None or not layer.isValid():
            layer = QgsVectorLayer(str(risk_layer_or_path), 'RiskAssessmentForSummary', 'ogr')
        if layer is None or not layer.isValid():
            raise QgsProcessingException('Could not load the final Risk Assessment layer for summary export.')

        field_names = [field.name() for field in layer.fields()]

        def field_value(feature, field_name):
            return feature[field_name] if field_name in field_names else None

        def simple_value(value):
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return str(value)

        def number_or_none(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except Exception:
                return None

        risk_total_values = []
        classification_counts = {}
        top_features = []
        feature_count = 0
        null_risk_total_count = 0
        max_risk_physical = None
        max_risk_social = None

        for feature in layer.getFeatures():
            feature_count += 1

            classification = field_value(feature, 'classification')
            classification_text = str(classification).strip() if classification is not None else ''
            if classification_text:
                classification_counts[classification_text] = classification_counts.get(classification_text, 0) + 1

            risk_total = number_or_none(field_value(feature, 'risk_total'))
            risk_physical = number_or_none(field_value(feature, 'risk_physical'))
            risk_social = number_or_none(field_value(feature, 'risk_social'))
            energy_max = number_or_none(field_value(feature, 'energy_max'))

            if risk_total is None:
                null_risk_total_count += 1
            else:
                risk_total_values.append(risk_total)

            if risk_physical is not None:
                max_risk_physical = risk_physical if max_risk_physical is None else max(max_risk_physical, risk_physical)
            if risk_social is not None:
                max_risk_social = risk_social if max_risk_social is None else max(max_risk_social, risk_social)

            top_features.append({
                'qrade_id': simple_value(field_value(feature, 'fid')) if 'fid' in field_names else feature.id(),
                'feature_id': feature.id(),
                'classification': simple_value(classification_text) if classification_text else None,
                'energy_max': energy_max,
                'risk_physical': risk_physical,
                'risk_social': risk_social,
                'risk_total': risk_total,
            })

        non_null_risk_total_count = len(risk_total_values)
        sum_risk_total = sum(risk_total_values) if risk_total_values else 0.0
        mean_risk_total = (sum_risk_total / non_null_risk_total_count) if non_null_risk_total_count else None

        statistics = {
            'feature_count': feature_count,
            'non_null_risk_total_count': non_null_risk_total_count,
            'null_risk_total_count': null_risk_total_count,
            'min_risk_total': min(risk_total_values) if risk_total_values else None,
            'max_risk_total': max(risk_total_values) if risk_total_values else None,
            'mean_risk_total': mean_risk_total,
            'sum_risk_total': sum_risk_total,
            'max_risk_physical': max_risk_physical,
            'max_risk_social': max_risk_social,
            'classification_counts': dict(sorted(classification_counts.items())),
            'top_10_by_risk_total': sorted(
                top_features,
                key=lambda item: item['risk_total'] if item['risk_total'] is not None else float('-inf'),
                reverse=True
            )[:10],
        }

        summary = {
            'metadata': run_metadata,
            'statistics': statistics,
        }

        summary_json_path = output_paths['summary_json']
        summary_csv_path = output_paths['summary_csv']

        try:
            with open(summary_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(summary, json_file, indent=2, sort_keys=True)

            with open(summary_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(['key', 'value'])
                for key, value in run_metadata.items():
                    writer.writerow([f'metadata:{key}', value])
                for key, value in statistics.items():
                    if key in ('classification_counts', 'top_10_by_risk_total'):
                        continue
                    writer.writerow([f'statistic:{key}', value])
                for classification, count in statistics['classification_counts'].items():
                    writer.writerow([f'classification_count:{classification}', count])
                for index, item in enumerate(statistics['top_10_by_risk_total'], start=1):
                    writer.writerow([
                        f'top_risk_feature:{index}',
                        json.dumps(item, sort_keys=True)
                    ])
        except Exception as e:
            raise QgsProcessingException(f'Could not write QRADE result summary files in: {output_paths["summary_dir"]}\n{e}')

        feedback.pushInfo(f'Summary written: {summary_json_path}')
        feedback.pushInfo(f'Summary CSV written: {summary_csv_path}')
        return summary_json_path, summary_csv_path

    def _recommended_action_for_risk(self, risk_total):
        if risk_total is None:
            return 'No action from current assessment'
        if risk_total >= 0.75:
            return 'Immediate review / mitigation planning'
        if risk_total >= 0.50:
            return 'Detailed engineering review'
        if risk_total >= 0.25:
            return 'Monitor and review'
        if risk_total > 0:
            return 'Low priority monitoring'
        return 'No action from current assessment'

    def _bcf_priority_for_risk(self, risk_total):
        if risk_total is None:
            return 'Info'
        if risk_total >= 0.75:
            return 'Critical'
        if risk_total >= 0.50:
            return 'High'
        if risk_total >= 0.25:
            return 'Medium'
        if risk_total > 0:
            return 'Low'
        return 'Info'

    def _write_bim_ready_export(self, risk_layer_or_path, output_paths, run_metadata, feedback):
        feedback.pushInfo('Writing BIM-ready QRADE risk export...')

        layer = risk_layer_or_path if hasattr(risk_layer_or_path, 'getFeatures') else None
        if layer is None:
            layer = QgsProcessingUtils.mapLayerFromString(str(risk_layer_or_path), QgsProcessingContext())
        if layer is None or not layer.isValid():
            layer = QgsVectorLayer(str(risk_layer_or_path), 'RiskAssessmentForBimExport', 'ogr')
        if layer is None or not layer.isValid():
            raise QgsProcessingException('Could not load the final Risk Assessment layer for BIM-ready export.')

        field_names = [field.name() for field in layer.fields()]
        export_fields = [
            'qrade_id',
            'asset_id',
            'ifc_guid',
            'bim_category',
            'classification',
            'risk_total',
            'risk_physical',
            'risk_social',
            'energy_max_j',
            'energy_max_kj',
            'temporal_probability',
            'recommended_action',
            'bcf_priority',
            'assessment_date',
            'source_layer_feature_id',
        ]

        def field_value(feature, field_name):
            return feature[field_name] if field_name in field_names else None

        def simple_value(value):
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return str(value)

        def number_or_none(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except Exception:
                return None

        def bim_category_for(classification):
            text = str(classification or '').strip().lower()
            if not text:
                return ''
            if text == 'other':
                return 'Other'
            if 'railway' in text:
                return 'Railway'
            if 'road' in text:
                return 'Transport'
            building_terms = (
                'building',
                'house',
                'accommodation',
                'tourism',
                'community',
                'public services',
                'education',
                'health',
                'manufacturing',
                'utility',
                'mixed-use',
                'offices',
                'business',
                'religious',
                'cultural heritage',
                'commercial',
                'retail',
                'government',
                'farm buildings',
            )
            if any(term in text for term in building_terms):
                return 'Building'
            landuse_terms = (
                'agriculture',
                'grassland',
                'meadows',
                'recreation',
                'gathering',
                'parking area',
            )
            if any(term in text for term in landuse_terms):
                return 'LandUse'
            return 'Other'

        def recommended_action_for(risk_total):
            return self._recommended_action_for_risk(risk_total)

        def bcf_priority_for(risk_total):
            return self._bcf_priority_for_risk(risk_total)

        assessment_date = (
            run_metadata.get('timestamp')
            or run_metadata.get('assessment_date')
            or run_metadata.get('run_timestamp')
            or ''
        )
        temporal_probability = run_metadata.get('temporal_probability_value', '')

        records = []
        for feature in layer.getFeatures():
            qrade_id = field_value(feature, 'qrade_id')
            if qrade_id is None or qrade_id == '':
                qrade_id = feature.id()
            qrade_id = simple_value(qrade_id)

            classification = simple_value(field_value(feature, 'classification'))
            risk_total = number_or_none(field_value(feature, 'risk_total'))
            risk_physical = number_or_none(field_value(feature, 'risk_physical'))
            risk_social = number_or_none(field_value(feature, 'risk_social'))
            energy_max_j = number_or_none(field_value(feature, 'energy_max'))
            energy_max_kj = (energy_max_j / 1000.0) if energy_max_j is not None else None

            records.append({
                'qrade_id': qrade_id,
                'asset_id': f'QRADE-{qrade_id}',
                'ifc_guid': '',
                'bim_category': bim_category_for(classification),
                'classification': classification or '',
                'risk_total': risk_total,
                'risk_physical': risk_physical,
                'risk_social': risk_social,
                'energy_max_j': energy_max_j,
                'energy_max_kj': energy_max_kj,
                'temporal_probability': temporal_probability,
                'recommended_action': recommended_action_for(risk_total),
                'bcf_priority': bcf_priority_for(risk_total),
                'assessment_date': assessment_date,
                'source_layer_feature_id': feature.id(),
            })

        bim_csv_path = output_paths['bim_csv']
        bim_json_path = output_paths['bim_json']
        metadata = {
            'plugin_name': run_metadata.get('plugin_name', 'QRADE'),
            'algorithm_id': run_metadata.get('algorithm_id', 'qrade:qrade_risk_v3'),
            'run_timestamp': run_metadata.get('timestamp', ''),
            'output_folder': output_paths['root'],
            'ifc_guid_note': 'IFC GUIDs are blank unless mapped externally.',
            'export_note': 'This is a BIM-ready tabular export, not an IFC model.',
        }

        try:
            with open(bim_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=export_fields)
                writer.writeheader()
                writer.writerows(records)

            with open(bim_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(
                    {
                        'metadata': metadata,
                        'records': records,
                    },
                    json_file,
                    indent=2,
                    sort_keys=True
                )
        except Exception as e:
            raise QgsProcessingException(f'Could not write BIM-ready QRADE risk export files in: {output_paths["bim_dir"]}\n{e}')

        feedback.pushInfo(f'BIM-ready CSV written: {bim_csv_path}')
        feedback.pushInfo(f'BIM-ready JSON written: {bim_json_path}')
        return bim_csv_path, bim_json_path

    def _write_ifc_guid_mapping_template(self, risk_layer_or_path, output_paths, run_metadata, feedback):
        feedback.pushInfo('Writing IFC GUID mapping template...')

        layer = risk_layer_or_path if hasattr(risk_layer_or_path, 'getFeatures') else None
        if layer is None:
            layer = QgsProcessingUtils.mapLayerFromString(str(risk_layer_or_path), QgsProcessingContext())
        if layer is None or not layer.isValid():
            layer = QgsVectorLayer(str(risk_layer_or_path), 'RiskAssessmentForIfcGuidMapping', 'ogr')
        if layer is None or not layer.isValid():
            raise QgsProcessingException('Could not load the final Risk Assessment layer for IFC GUID mapping template export.')

        field_names = [field.name() for field in layer.fields()]
        template_fields = [
            'qrade_id',
            'asset_id',
            'classification',
            'risk_total',
            'risk_physical',
            'risk_social',
            'energy_max_j',
            'energy_max_kj',
            'bcf_priority',
            'recommended_action',
            'ifc_guid',
            'bim_element_name',
            'bim_element_type',
            'mapping_method',
            'mapping_confidence',
            'mapping_notes',
        ]

        def field_value(feature, field_name):
            return feature[field_name] if field_name in field_names else None

        def simple_value(value):
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return str(value)

        def number_or_none(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except Exception:
                return None

        records = []
        for feature in layer.getFeatures():
            qrade_id = field_value(feature, 'qrade_id')
            if qrade_id is None or qrade_id == '':
                qrade_id = feature.id()
            qrade_id = simple_value(qrade_id)

            risk_total = number_or_none(field_value(feature, 'risk_total'))
            risk_physical = number_or_none(field_value(feature, 'risk_physical'))
            risk_social = number_or_none(field_value(feature, 'risk_social'))
            energy_max_j = number_or_none(field_value(feature, 'energy_max'))
            energy_max_kj = (energy_max_j / 1000.0) if energy_max_j is not None else None

            records.append({
                'qrade_id': qrade_id,
                'asset_id': f'QRADE-{qrade_id}',
                'classification': simple_value(field_value(feature, 'classification')) or '',
                'risk_total': risk_total,
                'risk_physical': risk_physical,
                'risk_social': risk_social,
                'energy_max_j': energy_max_j,
                'energy_max_kj': energy_max_kj,
                'bcf_priority': self._bcf_priority_for_risk(risk_total),
                'recommended_action': self._recommended_action_for_risk(risk_total),
                'ifc_guid': '',
                'bim_element_name': '',
                'bim_element_type': '',
                'mapping_method': 'manual',
                'mapping_confidence': '',
                'mapping_notes': 'Fill IFC GUID after BIM/IFC review',
            })

        template_path = output_paths['ifc_guid_template_csv']
        try:
            with open(template_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=template_fields)
                writer.writeheader()
                writer.writerows(records)
        except Exception as e:
            raise QgsProcessingException(f'Could not write IFC GUID mapping template: {template_path}\n{e}')

        feedback.pushInfo(f'IFC GUID mapping template written: {template_path}')
        return template_path

    def _write_bcf_issue_export(self, risk_layer_or_path, output_paths, run_metadata, feedback):
        feedback.pushInfo('Writing BCF issue export for high-risk QRADE features...')

        layer = risk_layer_or_path if hasattr(risk_layer_or_path, 'getFeatures') else None
        if layer is None:
            layer = QgsProcessingUtils.mapLayerFromString(str(risk_layer_or_path), QgsProcessingContext())
        if layer is None or not layer.isValid():
            layer = QgsVectorLayer(str(risk_layer_or_path), 'RiskAssessmentForBcfIssues', 'ogr')
        if layer is None or not layer.isValid():
            raise QgsProcessingException('Could not load the final Risk Assessment layer for BCF issue export.')

        bcf_dir = output_paths['bcf_dir']
        bcf_zip_path = output_paths['bcf_zip']
        no_issues_readme_path = output_paths['bcf_readme']

        field_names = [field.name() for field in layer.fields()]
        layer_crs = layer.crs()
        layer_crs_authid = layer_crs.authid() if layer_crs and layer_crs.isValid() else ''

        def field_value(feature, field_name):
            return feature[field_name] if field_name in field_names else None

        def simple_value(value):
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            return str(value)

        def number_or_none(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except Exception:
                return None

        def display_value(value):
            if value is None:
                return ''
            if isinstance(value, float):
                return f'{value:.6g}'
            return str(value)

        def creation_date():
            timestamp_text = str(run_metadata.get('timestamp') or '').strip()
            if timestamp_text:
                try:
                    parsed = datetime.strptime(timestamp_text, '%Y-%m-%d_%H-%M-%S')
                    return parsed.replace(microsecond=0).isoformat() + 'Z'
                except Exception:
                    pass
            return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

        def centroid_text(feature):
            try:
                if not feature.hasGeometry():
                    return ''
                geometry = feature.geometry()
                if geometry is None or geometry.isEmpty():
                    return ''
                centroid = geometry.centroid()
                if centroid is None or centroid.isEmpty():
                    return ''
                point = centroid.asPoint()
                crs_label = f' ({layer_crs_authid})' if layer_crs_authid else ''
                return f'centroid_x_y{crs_label}: {point.x():.6f}, {point.y():.6f}'
            except Exception:
                return ''

        def xml_bytes(root):
            return ET.tostring(root, encoding='utf-8', xml_declaration=True)

        def issue_markup(issue):
            root = ET.Element('Markup')
            topic = ET.SubElement(
                root,
                'Topic',
                {
                    'Guid': issue['topic_guid'],
                    'TopicType': 'Issue',
                    'TopicStatus': 'Open',
                }
            )
            ET.SubElement(topic, 'Title').text = issue['title']
            ET.SubElement(topic, 'Priority').text = issue['priority']
            ET.SubElement(topic, 'CreationDate').text = issue['creation_date']
            ET.SubElement(topic, 'CreationAuthor').text = 'QRADE'
            ET.SubElement(topic, 'Description').text = issue['description']

            comment = ET.SubElement(root, 'Comment', {'Guid': str(uuid.uuid4())})
            ET.SubElement(comment, 'Date').text = issue['creation_date']
            ET.SubElement(comment, 'Author').text = 'QRADE'
            ET.SubElement(comment, 'Comment').text = issue['description']
            ET.SubElement(comment, 'Topic', {'Guid': issue['topic_guid']})
            return xml_bytes(root)

        issues = []
        created_at = creation_date()
        for feature in layer.getFeatures():
            risk_total = number_or_none(field_value(feature, 'risk_total'))
            if risk_total is None or risk_total < 0.50:
                continue

            qrade_id = field_value(feature, 'qrade_id')
            if qrade_id is None or qrade_id == '':
                qrade_id = feature.id()
            qrade_id = simple_value(qrade_id)
            asset_id = f'QRADE-{qrade_id}'
            classification = simple_value(field_value(feature, 'classification')) or ''
            risk_physical = number_or_none(field_value(feature, 'risk_physical'))
            risk_social = number_or_none(field_value(feature, 'risk_social'))
            energy_max_j = number_or_none(field_value(feature, 'energy_max'))
            energy_max_kj = (energy_max_j / 1000.0) if energy_max_j is not None else None
            priority = self._bcf_priority_for_risk(risk_total)
            recommended_action = self._recommended_action_for_risk(risk_total)
            centroid = centroid_text(feature)

            description_lines = [
                f'QRADE high-risk rockfall issue generated from the risk-assessment layer.',
                f'qrade_id: {display_value(qrade_id)}',
                f'asset_id: {asset_id}',
                f'classification: {classification}',
                f'risk_total: {display_value(risk_total)}',
                f'risk_physical: {display_value(risk_physical)}',
                f'risk_social: {display_value(risk_social)}',
                f'energy_max_kj: {display_value(energy_max_kj)}',
                f'recommended_action: {recommended_action}',
                'IFC GUID mapping may be added later using qrade_ifc_guid_mapping_template.csv.',
            ]
            if centroid:
                description_lines.append(centroid)

            issues.append({
                'topic_guid': str(uuid.uuid4()),
                'title': f'QRADE {priority} rockfall risk - {asset_id}',
                'priority': priority,
                'creation_date': created_at,
                'description': '\n'.join(description_lines),
            })

        try:
            os.makedirs(bcf_dir, exist_ok=True)
            if not issues:
                with open(no_issues_readme_path, 'w', encoding='utf-8') as readme_file:
                    readme_file.write(
                        'No High/Critical QRADE rockfall risk features were found for BCF issue export.\n'
                        'BCF issues are generated for features with risk_total >= 0.50.\n'
                    )
                feedback.pushInfo('No High/Critical risk features found; no BCF issue package needed.')
                return {
                    'bcf_dir': bcf_dir,
                    'bcf_zip': bcf_zip_path,
                    'bcf_readme': no_issues_readme_path,
                    'bcf_issue_count': 0,
                }

            version_root = ET.Element('Version', {'VersionId': '2.1', 'DetailedVersion': '2.1'})
            with zipfile.ZipFile(bcf_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as bcf_zip:
                bcf_zip.writestr('bcf.version', xml_bytes(version_root))
                for issue in issues:
                    bcf_zip.writestr(
                        f'{issue["topic_guid"]}/markup.bcf',
                        issue_markup(issue)
                    )
        except Exception as e:
            raise QgsProcessingException(f'Could not write BCF issue export in: {bcf_dir}\n{e}')

        feedback.pushInfo(f'BCF issue export written: {bcf_zip_path}')
        return {
            'bcf_dir': bcf_dir,
            'bcf_zip': bcf_zip_path,
            'bcf_readme': no_issues_readme_path,
            'bcf_issue_count': len(issues),
        }

    def _write_webgis_data_bundle(
        self,
        output_paths,
        layer_paths_or_outputs,
        summary_paths,
        bim_paths,
        context,
        feedback
    ):
        feedback.pushInfo('Preparing WebGIS report data bundle...')

        data_dir = output_paths['web_report_data_dir']

        def warn(message):
            if hasattr(feedback, 'pushWarning'):
                feedback.pushWarning(message)
            else:
                feedback.pushInfo(f'Warning: {message}')

        def copy_optional(source_path, destination_name):
            if not source_path or not os.path.exists(source_path):
                warn(f'WebGIS data bundle source file not found, skipping: {source_path}')
                return None
            destination_path = os.path.join(data_dir, destination_name)
            try:
                shutil.copy2(source_path, destination_path)
            except Exception as e:
                raise QgsProcessingException(
                    f'Could not copy WebGIS data bundle file to: {destination_path}\n{e}'
                )
            return destination_path

        def layer_for_export(layer_name, layer_source):
            layer = layer_source if hasattr(layer_source, 'getFeatures') else None
            if layer is None:
                layer = QgsProcessingUtils.mapLayerFromString(str(layer_source), context)
            if layer is None or not layer.isValid():
                layer = QgsVectorLayer(str(layer_source), f'QRADEWebGIS_{layer_name}', 'ogr')
            if layer is None or not layer.isValid():
                raise QgsProcessingException(
                    f'Could not load {layer_name} layer for WebGIS GeoJSON export.'
                )
            return layer

        def export_geojson(layer_name, layer_source, destination_name):
            layer = layer_for_export(layer_name, layer_source)
            destination_path = os.path.join(data_dir, destination_name)
            feedback.pushInfo(f'Exporting WebGIS GeoJSON: {destination_path}')
            try:
                processing.run(
                    'native:reprojectlayer',
                    {
                        'INPUT': layer,
                        'TARGET_CRS': 'EPSG:4326',
                        'OPERATION': None,
                        'OUTPUT': destination_path,
                    },
                    context=context,
                    feedback=feedback,
                    is_child_algorithm=True
                )
            except Exception as e:
                raise QgsProcessingException(
                    f'Could not export {layer_name} to EPSG:4326 GeoJSON: {destination_path}\n{e}'
                )
            if not os.path.exists(destination_path):
                raise QgsProcessingException(
                    f'WebGIS GeoJSON export did not create expected file: {destination_path}'
                )
            return destination_path

        try:
            os.makedirs(data_dir, exist_ok=True)

            copy_optional(summary_paths.get('summary_json'), 'summary.json')
            copy_optional(summary_paths.get('summary_csv'), 'summary.csv')
            copy_optional(bim_paths.get('bim_json'), 'qrade_bim_risk.json')
            copy_optional(bim_paths.get('bim_csv'), 'qrade_bim_risk.csv')

            export_geojson(
                'Risk Assessment',
                layer_paths_or_outputs.get('risk_assessment'),
                'risk_assessment.geojson'
            )
            export_geojson(
                'LandCover',
                layer_paths_or_outputs.get('landcover'),
                'landcover.geojson'
            )
            export_geojson(
                'Runout',
                layer_paths_or_outputs.get('runout'),
                'runout.geojson'
            )
        except QgsProcessingException:
            raise
        except Exception as e:
            raise QgsProcessingException(f'Could not write WebGIS report data bundle in: {data_dir}\n{e}')

        feedback.pushInfo(f'WebGIS data written: {data_dir}')
        return data_dir

    def _write_webgis_index_html(self, output_paths, web_data_dir, feedback):
        feedback.pushInfo('Writing QRADE WebGIS report HTML...')

        web_report_dir = output_paths['web_report_dir']
        index_html_path = output_paths['web_report_index']
        summary_path = os.path.join(web_data_dir, 'summary.json')
        bim_path = os.path.join(web_data_dir, 'qrade_bim_risk.json')
        risk_geojson_path = os.path.join(web_data_dir, 'risk_assessment.geojson')
        landcover_geojson_path = os.path.join(web_data_dir, 'landcover.geojson')
        runout_geojson_path = os.path.join(web_data_dir, 'runout.geojson')
        assets_dir = output_paths['web_report_assets_dir']
        logo_markup = '<div class="report-logo-fallback">QRADE</div>'

        def warn(message):
            if hasattr(feedback, 'pushWarning'):
                feedback.pushWarning(message)
            else:
                feedback.pushInfo(f'Warning: {message}')

        icon_source_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if os.path.exists(icon_source_path):
            try:
                os.makedirs(assets_dir, exist_ok=True)
                shutil.copy2(icon_source_path, output_paths['web_report_icon'])
                logo_markup = '<img class="report-logo" src="assets/icon.png" alt="QRADE logo">'
            except Exception as e:
                warn(f'Could not copy QRADE report logo; using fallback text mark.\n{e}')

        def load_json(path, label):
            if not os.path.exists(path):
                warn(f'{label} not found for WebGIS report HTML: {path}')
                return None
            try:
                with open(path, 'r', encoding='utf-8') as json_file:
                    return json.load(json_file)
            except Exception as e:
                warn(f'Could not read {label} for WebGIS report HTML: {path}\n{e}')
                return None

        def empty_feature_collection():
            return {'type': 'FeatureCollection', 'features': []}

        def load_geojson(path, label):
            data = load_json(path, label)
            if not isinstance(data, dict):
                return empty_feature_collection(), f'{label} was missing or unreadable.'
            if data.get('type') != 'FeatureCollection' or not isinstance(data.get('features'), list):
                warn(f'{label} is not a valid GeoJSON FeatureCollection: {path}')
                return empty_feature_collection(), f'{label} was not a valid GeoJSON FeatureCollection.'
            return data, None

        def text(value):
            if value is None:
                return ''
            return html.escape(str(value))

        def number_text(value):
            if value is None or value == '':
                return ''
            if isinstance(value, float):
                return f'{value:.6g}'
            return text(value)

        def number_or_none(value):
            try:
                if value is None or value == '':
                    return None
                number = float(value)
                if number != number:
                    return None
                return number
            except (TypeError, ValueError):
                return None

        def table_rows(items):
            rows = []
            for key, value in items:
                rows.append(f'<tr><td>{text(key)}</td><td>{text(value)}</td></tr>')
            return '\n'.join(rows) if rows else '<tr><td colspan="2">No data available</td></tr>'

        def js_json(value):
            return json.dumps(value, ensure_ascii=False).replace('</', '<\\/')

        def feature_risk_total(feature):
            if not isinstance(feature, dict):
                return None
            properties = feature.get('properties')
            if not isinstance(properties, dict):
                return None
            return number_or_none(properties.get('risk_total'))

        def feature_property_number(feature, field_name):
            if not isinstance(feature, dict):
                return None
            properties = feature.get('properties')
            if not isinstance(properties, dict):
                return None
            return number_or_none(properties.get(field_name))

        def update_bounds_from_coordinates(bounds, coordinates):
            if not isinstance(coordinates, list):
                return bounds
            if (
                len(coordinates) >= 2
                and isinstance(coordinates[0], (int, float))
                and isinstance(coordinates[1], (int, float))
            ):
                lon = float(coordinates[0])
                lat = float(coordinates[1])
                if -180 <= lon <= 180 and -90 <= lat <= 90:
                    west, south, east, north = bounds
                    return (
                        min(west, lon),
                        min(south, lat),
                        max(east, lon),
                        max(north, lat),
                    )
                return bounds
            for item in coordinates:
                bounds = update_bounds_from_coordinates(bounds, item)
            return bounds

        def update_bounds_from_geometry(bounds, geometry):
            if not isinstance(geometry, dict):
                return bounds
            if geometry.get('type') == 'GeometryCollection':
                for child_geometry in geometry.get('geometries') or []:
                    bounds = update_bounds_from_geometry(bounds, child_geometry)
                return bounds
            return update_bounds_from_coordinates(bounds, geometry.get('coordinates'))

        def geojson_bounds(geojson):
            bounds = (180.0, 90.0, -180.0, -90.0)
            for feature in geojson.get('features', []) if isinstance(geojson, dict) else []:
                if isinstance(feature, dict):
                    bounds = update_bounds_from_geometry(bounds, feature.get('geometry'))
            west, south, east, north = bounds
            if west <= east and south <= north:
                return [[south, west], [north, east]]
            return None

        def valid_bounds(bounds):
            if not bounds:
                return False
            try:
                south, west = bounds[0]
                north, east = bounds[1]
                return south <= north and west <= east
            except (TypeError, ValueError, IndexError):
                return False

        summary = load_json(summary_path, 'summary.json')
        bim_export = load_json(bim_path, 'qrade_bim_risk.json')
        risk_geojson, risk_geojson_warning = load_geojson(risk_geojson_path, 'risk_assessment.geojson')
        landcover_geojson, landcover_geojson_warning = load_geojson(landcover_geojson_path, 'landcover.geojson')
        runout_geojson, runout_geojson_warning = load_geojson(runout_geojson_path, 'runout.geojson')

        metadata = summary.get('metadata', {}) if isinstance(summary, dict) else {}
        statistics = summary.get('statistics', {}) if isinstance(summary, dict) else {}
        warnings = []
        if summary is None:
            warnings.append('summary.json was missing or unreadable. Dashboard summary values are limited.')
        for geojson_warning in (risk_geojson_warning, landcover_geojson_warning, runout_geojson_warning):
            if geojson_warning:
                warnings.append(geojson_warning)

        risk_features = risk_geojson.get('features', []) if isinstance(risk_geojson, dict) else []
        risk_class_definitions = [
            ('0.00', 'No calculated risk: 0.00', '#808080'),
            ('0.00 - 0.25', 'Low risk: 0.00 - 0.25', '#ffe600'),
            ('0.25 - 0.50', 'Moderate risk: 0.25 - 0.50', '#ff8c00'),
            ('0.50 - 0.75', 'High risk: 0.50 - 0.75', '#ff2b2b'),
            ('0.75 - 1.00', 'Critical risk: 0.75 - 1.00', '#d7191c'),
        ]
        risk_class_counts = {risk_range: 0 for risk_range, _, _ in risk_class_definitions}

        def qgis_risk_class_range(risk_total):
            value = risk_total if risk_total is not None else 0.0
            if value <= 0:
                return '0.00'
            if value < 0.25:
                return '0.00 - 0.25'
            if value < 0.50:
                return '0.25 - 0.50'
            if value < 0.75:
                return '0.50 - 0.75'
            return '0.75 - 1.00'

        non_zero_risk_count = 0
        high_critical_count = 0
        for feature in risk_features:
            risk_total = feature_risk_total(feature)
            risk_class_counts[qgis_risk_class_range(risk_total)] += 1
            if risk_total is None:
                continue
            if risk_total > 0:
                non_zero_risk_count += 1
            if risk_total >= 0.50:
                high_critical_count += 1

        qrade_landcover_bounds = geojson_bounds(landcover_geojson)
        qrade_risk_bounds = geojson_bounds(risk_geojson)
        qrade_runout_bounds = geojson_bounds(runout_geojson)

        qrade_analysis_bounds = qrade_landcover_bounds
        qrade_analysis_bounds_source = 'LandCover'
        if not valid_bounds(qrade_analysis_bounds):
            qrade_analysis_bounds = qrade_risk_bounds
            qrade_analysis_bounds_source = 'Risk Assessment'
        if not valid_bounds(qrade_analysis_bounds):
            qrade_analysis_bounds = qrade_runout_bounds
            qrade_analysis_bounds_source = 'Runout'
        if not valid_bounds(qrade_analysis_bounds):
            qrade_analysis_bounds = None
            qrade_analysis_bounds_source = 'Default world view'
            warnings.append('No valid GeoJSON extent was available. The map will start from a default world view.')

        classification_counts = statistics.get('classification_counts', {})
        if not isinstance(classification_counts, dict):
            classification_counts = {}
        priority_counts = {}
        category_counts = {}
        if isinstance(bim_export, dict):
            records = bim_export.get('records', [])
            if isinstance(records, list):
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    priority = str(record.get('bcf_priority') or '').strip()
                    category = str(record.get('bim_category') or '').strip()
                    if priority:
                        priority_counts[priority] = priority_counts.get(priority, 0) + 1
                    if category:
                        category_counts[category] = category_counts.get(category, 0) + 1
        elif os.path.exists(bim_path):
            warnings.append('qrade_bim_risk.json was unreadable. BIM/action summary is unavailable.')

        cards = [
            ('Features at risk', non_zero_risk_count),
            ('High/Critical risk features', high_critical_count),
            ('Max total risk', statistics.get('max_risk_total')),
            ('Temporal probability', metadata.get('temporal_probability_value')),
        ]
        card_html = '\n'.join(
            f'<div class="card"><span>{text(label)}</span><strong>{number_text(value)}</strong></div>'
            for label, value in cards
        )

        classification_rows = table_rows(sorted(classification_counts.items()))
        risk_class_rows = '\n'.join(
            '<tr>'
            f'<td><span class="table-swatch" style="background:{text(color)}"></span>{text(risk_range)}</td>'
            f'<td>{text(label)}</td>'
            f'<td>{text(risk_class_counts.get(risk_range, 0))}</td>'
            '</tr>'
            for risk_range, label, color in risk_class_definitions
        )
        official_landcover_classes = [
            ('Residential apartment building', '#b00020'),
            ('House', '#ff1a1a'),
            ('Accommodation / Tourism', '#ff4d4d'),
            ('Community & public services', '#f5a3a3'),
            ('Education facilities', '#7a1fd1'),
            ('Health facilities', '#fff200'),
            ('Industrial building/ Manufacturing', '#c26b2b'),
            ('Energy / Utility building', '#4b45c8'),
            ('Parking Building', '#d99122'),
            ('Mixed-use buildings', '#8b4a13'),
            ('Offices / Business centers', '#d640b7'),
            ('Religious / Cultural heritage', '#ff8c00'),
            ('Commercial / Retail', '#4b255f'),
            ('Public administration / Government', '#59c9ad'),
            ('Paved road', '#666666'),
            ('Unpaved road', '#ffc266'),
            ('Railway', '#d85883'),
            ('Recreation / Gathering areas', '#249b23'),
            ('Livestock / Farm buildings', '#e5ff00'),
            ('Productive agriculture', '#54d338'),
            ('Grassland and meadows', '#8be34a'),
            ('Parking area', '#8a006f'),
            ('Ruin', '#d9d9d9'),
            ('Other', '#000000'),
        ]
        official_landcover_labels = [label for label, _ in official_landcover_classes]
        landcover_legend_html = '\n'.join(
            f'<div><span class="table-swatch" style="background:{text(color)}"></span>{text(label)}</div>'
            for label, color in official_landcover_classes
        )
        all_classifications = set()
        all_classifications.update(official_landcover_labels)
        all_classifications.update(str(key).strip() for key in classification_counts.keys() if str(key).strip())
        for geojson in (risk_geojson, landcover_geojson):
            for feature in geojson.get('features', []) if isinstance(geojson, dict) else []:
                properties = feature.get('properties') if isinstance(feature, dict) else {}
                classification = properties.get('classification') if isinstance(properties, dict) else None
                if classification is not None and str(classification).strip():
                    all_classifications.add(str(classification).strip())
        all_classifications = sorted(all_classifications)
        priority_rows = table_rows(sorted(priority_counts.items())) if priority_counts else '<tr><td colspan="2">No BIM priority data available</td></tr>'
        category_rows = table_rows(sorted(category_counts.items())) if category_counts else '<tr><td colspan="2">No BIM category data available</td></tr>'

        top_rows = []
        ranked_features = sorted(
            (feature for feature in risk_features if isinstance(feature, dict)),
            key=lambda feature: (
                feature_risk_total(feature) if feature_risk_total(feature) is not None else -float('inf'),
                feature_property_number(feature, 'energy_max') if feature_property_number(feature, 'energy_max') is not None else -float('inf'),
            ),
            reverse=True
        )
        for index, feature in enumerate(ranked_features, start=1):
            properties = feature.get('properties') if isinstance(feature, dict) else {}
            if not isinstance(properties, dict):
                continue
            qrade_id = (
                properties.get('qrade_id')
                or properties.get('fid')
                or properties.get('id')
                or properties.get('source_layer_feature_id')
            )
            top_rows.append(
                '<tr>'
                f'<td>{index}</td>'
                f'<td>{text(qrade_id)}</td>'
                f'<td>{text(properties.get("classification"))}</td>'
                f'<td>{number_text(properties.get("risk_total"))}</td>'
                f'<td>{number_text(properties.get("risk_physical"))}</td>'
                f'<td>{number_text(properties.get("risk_social"))}</td>'
                f'<td>{number_text(properties.get("energy_max"))}</td>'
                f'<td><button class="small-button zoom-risk-row" data-qrade-id="{text(qrade_id)}">Zoom</button></td>'
                '</tr>'
            )
        top_rows_html = '\n'.join(top_rows) if top_rows else '<tr><td colspan="8">No ranked risk feature data available</td></tr>'

        metadata_items = [
            ('Run timestamp', metadata.get('timestamp')),
            ('Project CRS', metadata.get('project_crs_authid')),
            ('Raster CRS', metadata.get('mean_energy_raster_crs_authid')),
            ('Raster source', metadata.get('mean_energy_raster_source')),
            ('Output folder', metadata.get('output_folder')),
        ]
        run_info_rows = table_rows(metadata_items)
        warning_html = ''
        if warnings:
            warning_items = ''.join(f'<li>{text(message)}</li>' for message in warnings)
            warning_html = f'<section class="panel warning"><h2>Warnings</h2><ul>{warning_items}</ul></section>'
        run_badge_html = ''
        if metadata.get('timestamp'):
            run_badge_html = f'<span class="run-badge">Run: {text(metadata.get("timestamp"))}</span>'

        html_template = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QRADE Interactive Risk Report</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
body {{
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  color: #1f2933;
  background: #eef2f5;
}}
header {{
  padding: 24px 30px;
  background: linear-gradient(135deg, #17313b 0%, #254a43 58%, #1f6b4f 100%);
  color: #ffffff;
}}
.report-header {{
  max-width: 1500px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 18px;
}}
.report-logo,
.report-logo-fallback {{
  width: 68px;
  height: 68px;
  flex: 0 0 auto;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid rgba(255,255,255,0.55);
  box-shadow: 0 10px 24px rgba(0,0,0,0.18);
}}
.report-logo {{
  object-fit: contain;
  padding: 6px;
}}
.report-logo-fallback {{
  display: flex;
  align-items: center;
  justify-content: center;
  color: #17313b;
  font-weight: bold;
  font-size: 15px;
  letter-spacing: 0.04em;
}}
.report-title-block {{
  min-width: 0;
}}
.report-title-block h1 {{
  margin-bottom: 6px;
  font-size: 30px;
}}
.report-title-block p {{
  margin: 0;
  color: #dcebe7;
}}
.run-badge {{
  display: inline-block;
  margin-top: 10px;
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(255,255,255,0.14);
  color: #ffffff;
  font-size: 12px;
}}
main {{
  max-width: 1500px;
  margin: 0 auto;
  padding: 18px;
  --ranked-feature-row-height: 22px;
  --ranked-feature-visible-rows: 20;
}}
h1, h2 {{
  margin: 0 0 12px 0;
}}
.panel {{
  margin-bottom: 16px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid #d8dee4;
}}
#map {{
  width: 100%;
  height: 600px;
  min-height: 600px;
  max-height: 600px;
  border: 1px solid #aeb8c2;
  border: 2px solid #4b5563;
  background: #eef3f6;
  overflow: hidden;
  position: relative;
  contain: layout paint;
}}
.map-wrapper {{
  position: relative;
  overflow: hidden;
  width: 100%;
  height: 600px;
  max-height: 600px;
}}
.map-layout {{
  display: grid;
  grid-template-columns: minmax(280px, 30%) minmax(0, 70%);
  gap: 16px;
  align-items: stretch;
}}
.map-side {{
  padding: 14px;
  border: 1px solid #d8dee4;
  background: #f8fafc;
}}
.map-main {{
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  height: 100%;
  align-self: stretch;
}}
.control-group {{
  margin-bottom: 14px;
}}
.control-title {{
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: bold;
  color: #263238;
}}
.basemap-options label {{
  display: block;
  margin: 5px 0;
  font-weight: normal;
}}
.legend-panel {{
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #d8dee4;
}}
.legend-heading {{
  margin-top: 16px;
  padding-top: 12px;
  border-top: 2px solid #cbd5e1;
  color: #263238;
  font-weight: bold;
  font-size: 15px;
}}
.legend-panel h3 {{
  margin: 0 0 8px 0;
  font-size: 14px;
}}
.legend-list {{
  max-height: 210px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.45;
}}
.landcover-legend-list {{
  max-height: none;
  overflow: visible;
}}
.legend-list div {{
  margin: 4px 0;
}}
.map-source-row {{
  margin-top: 8px;
  color: #52616b;
  font-size: 12px;
}}
.map-source-row a {{
  color: #0b66c3;
}}
.ranked-features-panel {{
  margin-top: 10px;
  padding: 12px;
  border: 1px solid #d8dee4;
  background: #f8fafc;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}}
.ranked-features-panel h2 {{
  margin-bottom: 8px;
  font-size: 17px;
}}
.ranked-features-table-wrap {{
  flex: 0 1 auto;
  min-height: 0;
  max-height: calc((var(--ranked-feature-row-height) * var(--ranked-feature-visible-rows)) + 32px);
  overflow-y: auto;
  overflow-x: auto;
}}
.ranked-features-panel table {{
  background: #ffffff;
}}
.ranked-features-panel th,
.ranked-features-panel td {{
  padding: 3px 6px;
  font-size: 12px;
  line-height: 1.2;
}}
.ranked-features-panel .small-button {{
  padding: 3px 6px;
}}
.leaflet-container img {{
  max-width: none !important;
  max-height: none !important;
}}
.leaflet-container {{
  overflow: hidden;
  position: relative;
}}
.leaflet-pane,
.leaflet-tile-pane,
.leaflet-overlay-pane,
.leaflet-shadow-pane,
.leaflet-marker-pane,
.leaflet-tooltip-pane,
.leaflet-popup-pane,
.leaflet-map-pane {{
  position: absolute;
  left: 0;
  top: 0;
}}
.leaflet-map-pane,
.leaflet-tile,
.leaflet-marker-icon,
.leaflet-marker-shadow,
.leaflet-control {{
  position: absolute;
}}
.leaflet-tile {{
  width: 256px;
  height: 256px;
  max-width: none !important;
  max-height: none !important;
}}
.leaflet-control-container {{
  position: absolute;
  inset: 0;
  pointer-events: none;
}}
.leaflet-control {{
  pointer-events: auto;
  z-index: 800;
}}
.leaflet-top,
.leaflet-bottom {{
  position: absolute;
  z-index: 1000;
  pointer-events: none;
}}
.leaflet-top {{
  top: 0;
}}
.leaflet-bottom {{
  bottom: 0;
}}
.leaflet-left {{
  left: 0;
}}
.leaflet-right {{
  right: 0;
}}
.leaflet-top .leaflet-control {{
  margin-top: 10px;
}}
.leaflet-bottom .leaflet-control {{
  margin-bottom: 10px;
}}
.leaflet-left .leaflet-control {{
  margin-left: 10px;
}}
.leaflet-right .leaflet-control {{
  margin-right: 10px;
}}
.leaflet-popup,
.leaflet-tooltip {{
  position: absolute;
}}
.leaflet-popup-pane {{
  z-index: 1000 !important;
}}
.leaflet-popup {{
  z-index: 1001 !important;
}}
.leaflet-popup-content-wrapper,
.leaflet-popup-tip {{
  background: #ffffff !important;
  opacity: 1 !important;
  border: 1px solid #b8c2cc;
  box-shadow: 0 6px 18px rgba(0,0,0,0.25);
}}
.leaflet-popup-content {{
  background: #ffffff;
  color: #111827;
  opacity: 1;
}}
.qrade-popup,
.qrade-popup table,
.qrade-popup th,
.qrade-popup td {{
  background-color: #ffffff;
  opacity: 1;
}}
.qrade-popup {{
  color: #111827;
}}
.qrade-popup strong {{
  display: block;
  margin-bottom: 6px;
  color: #111827;
}}
.qrade-popup table {{
  width: 100%;
  border-collapse: collapse;
}}
.qrade-popup th,
.qrade-popup td {{
  padding: 4px 6px;
  border: 1px solid #d0d7de;
  color: #111827;
  text-align: left;
}}
.qrade-popup th {{
  font-weight: bold;
}}
.summary-row {{
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}}
.cards {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
}}
.card {{
  padding: 12px;
  border: 1px solid #d8dee4;
  background: #f8fafc;
}}
.card span {{
  display: block;
  margin-bottom: 8px;
  color: #52616b;
  font-size: 13px;
}}
.card strong {{
  display: block;
  font-size: 19px;
}}
.summary-actions {{
  margin-top: 16px;
}}
.qa-button {{
  display: inline-block;
  padding: 13px 20px;
  border-radius: 10px;
  color: #ffffff;
  background: linear-gradient(135deg, #15803d 0%, #22c55e 100%);
  font-weight: bold;
  text-decoration: none;
  box-shadow: 0 8px 18px rgba(21,128,61,0.25);
}}
.qa-button:hover {{
  color: #ffffff;
  background: linear-gradient(135deg, #166534 0%, #16a34a 100%);
}}
.details-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}}
table {{
  width: 100%;
  border-collapse: collapse;
}}
th, td {{
  padding: 7px;
  border: 1px solid #d8dee4;
  text-align: left;
  vertical-align: top;
  font-size: 13px;
}}
th {{
  background: #eef2f5;
}}
a {{
  color: #0b66c3;
}}
.placeholder {{
  padding: 18px;
  border: 1px dashed #8a99a8;
  background: #f8fafc;
}}
.warning {{
  border-color: #d97706;
  background: #fff7ed;
}}
.note {{
  color: #52616b;
}}
.map-toolbar {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  margin: 10px 0 12px 0;
}}
.view-switcher {{
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 0 0 14px 0;
}}
.view-button {{
  flex: 1 1 100%;
  min-height: 54px;
  padding: 13px 18px;
  border-radius: 10px;
  border: 2px solid transparent;
  color: #ffffff;
  font-weight: bold;
  font-size: 15px;
  box-shadow: 0 8px 18px rgba(15,23,42,0.18);
}}
.view-button-red {{
  background: linear-gradient(135deg, #991b1b 0%, #ef4444 100%);
}}
.view-button-blue {{
  background: linear-gradient(135deg, #1d4ed8 0%, #38bdf8 100%);
}}
.view-button.active {{
  border-color: #ffffff;
  outline: 3px solid rgba(15,23,42,0.28);
}}
label {{
  display: block;
  font-size: 13px;
  font-weight: bold;
}}
select, button {{
  margin-top: 6px;
  padding: 7px 9px;
  border: 1px solid #aeb8c2;
  background: #ffffff;
}}
button {{
  cursor: pointer;
}}
.button-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}}
.small-button {{
  padding: 4px 7px;
  margin: 0;
}}
.legend {{
  background: #ffffff;
  padding: 10px;
  border: 1px solid #aeb8c2;
  line-height: 1.5;
}}
.legend span {{
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 6px;
  vertical-align: middle;
}}
.table-swatch {{
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-right: 6px;
  border: 1px solid #64748b;
  vertical-align: middle;
}}
.map-warning {{
  display: none;
  padding: 10px;
  border: 1px solid #d97706;
  background: #fff7ed;
  margin-bottom: 10px;
}}
.status-list {{
  margin: 0;
  padding-left: 18px;
}}
.status-list li {{
  margin-bottom: 4px;
}}
.inline-warning {{
  display: none;
  margin-top: 10px;
  padding: 9px;
  border: 1px solid #d97706;
  background: #fff7ed;
}}
@media (max-width: 980px) {{
  .map-layout {{
    grid-template-columns: 1fr;
  }}
  .report-header {{
    align-items: flex-start;
  }}
  .report-title-block h1 {{
    font-size: 24px;
  }}
  .report-logo,
  .report-logo-fallback {{
    width: 56px;
    height: 56px;
    border-radius: 13px;
  }}
  #map {{
    height: 560px;
    min-height: 560px;
    max-height: 560px;
  }}
  .map-wrapper {{
    height: 560px;
    max-height: 560px;
  }}
  .map-main {{
    display: flex;
    flex-direction: column;
    height: auto;
  }}
  .ranked-features-panel {{
    flex: 0 0 auto;
  }}
  .ranked-features-table-wrap {{
    flex: 0 1 auto;
    max-height: min(calc((var(--ranked-feature-row-height) * var(--ranked-feature-visible-rows)) + 32px), 45vh);
  }}
}}
@media print {{
  #map {{
    height: 560px !important;
    min-height: 560px !important;
    max-height: 560px !important;
    overflow: hidden !important;
    page-break-inside: avoid;
  }}
  .map-wrapper,
  .leaflet-container {{
    height: 560px !important;
    max-height: 560px !important;
    overflow: hidden !important;
    page-break-inside: avoid;
  }}
}}
</style>
</head>
<body>
<header>
  <div class="report-header">
    __LOGO_MARKUP__
    <div class="report-title-block">
      <h1>QRADE Interactive Risk Report</h1>
      <p>Interactive dashboard generated from QRADE output data.</p>
      __RUN_BADGE__
    </div>
  </div>
</header>
<main>
__WARNING_HTML__
<section class="panel">
  <h2>Executive Summary</h2>
  <div class="cards">__CARD_HTML__</div>
  <div class="summary-actions"><a class="qa-button" href="../qa_qc/qrade_qa_qc_report.html">Open QA/QC report</a></div>
</section>

<section class="panel">
  <h2>Interactive Map</h2>
  <div id="leafletWarning" class="map-warning">Leaflet or the online basemap did not load. Dashboard tables and data links remain available below.</div>
  <div class="map-layout">
    <aside class="map-side">
      <div class="view-switcher">
        <button id="runoutRiskView" class="view-button view-button-red active">Risk Assessment View</button>
        <button id="landcoverView" class="view-button view-button-blue">LandCover View</button>
      </div>
      <div class="control-group">
        <p class="control-title">Map Status</p>
        <ul class="status-list">
          <li>Runout bounds: <strong id="runoutBoundsText">Not available</strong></li>
          <li>LandCover features loaded: <strong id="landcoverLoadedCount">0</strong></li>
          <li>Total Risk Assessment features: <strong id="riskLoadedCount">0</strong></li>
          <li>Current filtered Risk features: <strong id="riskFilteredCount">0</strong></li>
        </ul>
        <div id="layerStatusWarning" class="inline-warning"></div>
      </div>
      <div class="control-group basemap-options">
        <p class="control-title">Basemap</p>
        <label><input type="radio" name="basemapChoice" value="osm" checked> Standard OpenStreetMap</label>
        <label><input type="radio" name="basemapChoice" value="topo"> OpenTopoMap</label>
      </div>
      <div class="control-group">
        <label for="priorityFilter">Risk class</label>
        <select id="priorityFilter">
          <option value="All">All</option>
          <option value="Zero">No calculated risk: 0.00</option>
          <option value="Low">Low risk: 0.00 - 0.25</option>
          <option value="Moderate">Moderate risk: 0.25 - 0.50</option>
          <option value="High">High risk: 0.50 - 0.75</option>
          <option value="Critical">Critical risk: 0.75 - 1.00</option>
          <option value="HighCritical">High/Critical risk: &gt;= 0.50</option>
        </select>
      </div>
      <div class="control-group">
        <label for="classificationFilter">Classification of features</label>
        <select id="classificationFilter">
          <option value="All">All</option>
        </select>
      </div>
      <div class="control-group">
        <button id="resetFilters">Reset filters</button>
      </div>
      <div class="legend-heading">Map Legends</div>
      <div class="legend-panel">
        <h3>Risk Assessment Legend</h3>
        <div class="legend-list">
          <div><span class="table-swatch" style="background:#808080"></span>No calculated risk: 0.00</div>
          <div><span class="table-swatch" style="background:#ffe600"></span>Low risk: 0.00 - 0.25</div>
          <div><span class="table-swatch" style="background:#ff8c00"></span>Moderate risk: 0.25 - 0.50</div>
          <div><span class="table-swatch" style="background:#ff2b2b"></span>High risk: 0.50 - 0.75</div>
          <div><span class="table-swatch" style="background:#d7191c"></span>Critical risk: 0.75 - 1.00</div>
        </div>
      </div>
      <div class="legend-panel">
        <h3>LandCover Legend</h3>
        <div class="legend-list landcover-legend-list">
          __LANDCOVER_LEGEND_ROWS__
        </div>
      </div>
    </aside>
    <div class="map-main">
      <div class="map-wrapper"><div id="map"></div></div>
      <div class="map-source-row">
        Sources: <a href="https://leafletjs.com/">Leaflet</a> |
        <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> |
        <a href="https://opentopomap.org/about">OpenTopoMap</a> |
        QRADE generated output data
      </div>
      <div class="ranked-features-panel">
        <h2>Features Ranked by Risk Score (Highest to Lowest)</h2>
        <div class="ranked-features-table-wrap">
          <table>
          <thead><tr><th>Rank</th><th>QRADE ID</th><th>Classification</th><th>Risk total</th><th>Risk physical</th><th>Risk social</th><th>Energy max</th><th>Map</th></tr></thead>
          <tbody>__TOP_ROWS_HTML__</tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
  <p class="note">Basemap tiles require internet access. QRADE result layers are embedded in this report.</p>
</section>

<div class="details-grid">
  <section class="panel">
  <h2>Risk Class Counts</h2>
  <table>
  <thead><tr><th>Range</th><th>Class</th><th>Count</th></tr></thead>
  <tbody>__RISK_CLASS_ROWS__</tbody>
  </table>
  </section>

  <section class="panel">
  <h2>Classification Counts</h2>
  <table>
  <thead><tr><th>Classification</th><th>Count</th></tr></thead>
  <tbody>__CLASSIFICATION_ROWS__</tbody>
  </table>
  </section>

  <section class="panel">
    <h2>BIM / BCF Summary</h2>
    <h3>BCF Priority Counts</h3>
    <table><thead><tr><th>Priority</th><th>Count</th></tr></thead><tbody>__PRIORITY_ROWS__</tbody></table>
    <h3>BIM Category Counts</h3>
    <table><thead><tr><th>Category</th><th>Count</th></tr></thead><tbody>__CATEGORY_ROWS__</tbody></table>
    <ul>
      <li><a href="../../bim/qrade_bim_risk.csv">Open BIM-ready CSV</a></li>
      <li><a href="../../bim/qrade_ifc_guid_mapping_template.csv">Open IFC GUID mapping template</a></li>
      <li><a href="../../bim/bcf_issues/">Open BCF issues folder</a></li>
    </ul>
  </section>

  <section class="panel">
  <h2>Run Information</h2>
  <table><tbody>__RUN_INFO_ROWS__</tbody></table>
  </section>

  <section class="panel">
  <h2>Data Files</h2>
  <ul>
  <li><a href="data/risk_assessment.geojson">data/risk_assessment.geojson</a></li>
  <li><a href="data/landcover.geojson">data/landcover.geojson</a></li>
  <li><a href="data/runout.geojson">data/runout.geojson</a></li>
  <li><a href="data/summary.json">data/summary.json</a></li>
  <li><a href="data/summary.csv">data/summary.csv</a></li>
  <li><a href="data/qrade_bim_risk.json">data/qrade_bim_risk.json</a></li>
  <li><a href="data/qrade_bim_risk.csv">data/qrade_bim_risk.csv</a></li>
  </ul>
  </section>
</div>

<section class="panel">
<h2>Notes And Limitations</h2>
<ul>
<li>Risk Assessment, Runout, and LandCover layers are exported as GeoJSON in EPSG:4326/CRS84 for browser display.</li>
<li>OpenStreetMap and OpenTopoMap basemap tiles require internet access and are provided by third-party tile services.</li>
<li>If Leaflet CDN or basemap tiles are unavailable, dashboard sections and local data links remain useful.</li>
<li>Results depend on input data quality, classification quality, and risk assumptions.</li>
<li>This dashboard supports QA and communication, but it does not replace technical interpretation.</li>
</ul>
</section>
</main>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const riskData = __RISK_GEOJSON__;
const landcoverData = __LANDCOVER_GEOJSON__;
const runoutData = __RUNOUT_GEOJSON__;
const bimExport = __BIM_JSON__;
const summaryFeatureCount = __SUMMARY_FEATURE_COUNT__;
const qradeAnalysisBounds = __ANALYSIS_BOUNDS__;
const qradeLandcoverBounds = __LANDCOVER_BOUNDS__;
const qradeRiskBounds = __RISK_BOUNDS__;
const qradeRunoutBounds = __RUNOUT_BOUNDS__;
const qradeAnalysisBoundsSource = '__EXTENT_SOURCE__';
const landcoverClassColors = __LANDCOVER_CLASS_COLORS__;

function valueText(value) {{
  return value === null || value === undefined || value === '' ? '' : String(value);
}}
function normalizedText(value) {{
  return valueText(value).trim().toLowerCase();
}}
function escapeHtml(value) {{
  return valueText(value).replace(/[&<>"']/g, character => ({{
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }}[character]));
}}
function numeric(value) {{
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}}
function riskClassKey(riskTotal) {{
  const value = numeric(riskTotal);
  if (value === null || value <= 0) return 'Zero';
  if (value < 0.25) return 'Low';
  if (value < 0.50) return 'Moderate';
  if (value < 0.75) return 'High';
  return 'Critical';
}}
function riskClassLabel(riskTotal) {{
  return {{
    Zero: 'No calculated risk: 0.00',
    Low: 'Low risk: 0.00 - 0.25',
    Moderate: 'Moderate risk: 0.25 - 0.50',
    High: 'High risk: 0.50 - 0.75',
    Critical: 'Critical risk: 0.75 - 1.00'
  }}[riskClassKey(riskTotal)];
}}
function riskClassRange(riskTotal) {{
  return {{
    Zero: '0.00',
    Low: '0.00 - 0.25',
    Moderate: '0.25 - 0.50',
    High: '0.50 - 0.75',
    Critical: '0.75 - 1.00'
  }}[riskClassKey(riskTotal)];
}}
function riskColorForValue(riskTotal) {{
  return {{
    Zero: '#808080',
    Low: '#ffe600',
    Moderate: '#ff8c00',
    High: '#ff2b2b',
    Critical: '#d7191c'
  }}[riskClassKey(riskTotal)] || '#808080';
}}
function isHighCriticalRisk(riskTotal) {{
  const value = numeric(riskTotal);
  return value !== null && value >= 0.50;
}}
function props(feature) {{
  return feature && feature.properties ? feature.properties : {{}};
}}
function qradeId(properties) {{
  return valueText(properties.qrade_id || properties.fid || properties.id || properties.source_layer_feature_id);
}}
function featureRiskTotal(feature) {{
  return numeric(props(feature).risk_total);
}}
function bimRecords() {{
  return bimExport && Array.isArray(bimExport.records) ? bimExport.records : [];
}}
function featureCount(data) {{
  return data && Array.isArray(data.features) ? data.features.length : 0;
}}
function riskFeatures() {{
  return riskData && Array.isArray(riskData.features) ? riskData.features : [];
}}
function landcoverFeatures() {{
  return landcoverData && Array.isArray(landcoverData.features) ? landcoverData.features : [];
}}
function nonZeroRiskFeatures() {{
  return riskFeatures().filter(feature => numeric(props(feature).risk_total) > 0);
}}
function setText(id, value) {{
  const element = document.getElementById(id);
  if (element) element.textContent = valueText(value);
}}
function boundsText(bounds) {{
  if (!Array.isArray(bounds) || bounds.length !== 2) return 'Not available';
  try {{
    const south = Number(bounds[0][0]).toFixed(6);
    const west = Number(bounds[0][1]).toFixed(6);
    const north = Number(bounds[1][0]).toFixed(6);
    const east = Number(bounds[1][1]).toFixed(6);
    return 'S ' + south + ', W ' + west + ', N ' + north + ', E ' + east;
  }} catch (error) {{
    return 'Not available';
  }}
}}
function showMapWarning(message) {{
  const warning = document.getElementById('leafletWarning');
  if (!warning) return;
  warning.textContent = message;
  warning.style.display = 'block';
}}
function bringLayerToFront(layer) {{
  try {{
    if (layer && typeof layer.bringToFront === 'function') {{
      layer.bringToFront();
    }} else if (layer && typeof layer.eachLayer === 'function') {{
      layer.eachLayer(child => {{
        if (child && typeof child.bringToFront === 'function') child.bringToFront();
      }});
    }}
  }} catch (error) {{}}
}}
const bimByQradeId = new Map();
bimRecords().forEach(record => {{
  const id = valueText(record.qrade_id);
  if (id) bimByQradeId.set(id, record);
}});

function popupTable(title, items) {{
  const rows = items.map(([key, value]) => '<tr><th>' + escapeHtml(key) + '</th><td>' + escapeHtml(value) + '</td></tr>').join('');
  return '<div class="qrade-popup"><strong>' + escapeHtml(title) + '</strong><table>' + rows + '</table></div>';
}}
function riskPopup(feature) {{
  const p = props(feature);
  const id = qradeId(p);
  const bim = bimByQradeId.get(id) || {{}};
  return popupTable('Risk Assessment', [
    ['qrade_id', id],
    ['risk_total', p.risk_total],
    ['risk_class', riskClassLabel(p.risk_total)],
    ['classification', p.classification],
    ['energy_max', p.energy_max || p.energy_max_j || p.energy_max_kj],
    ['risk_physical', p.risk_physical],
    ['risk_social', p.risk_social],
    ['bcf_priority', bim.bcf_priority],
    ['recommended_action', bim.recommended_action]
  ]);
}}
function landcoverPopup(feature) {{
  const p = props(feature);
  return popupTable('LandCover', [
    ['classification', p.classification],
    ['qrade_id', qradeId(p)]
  ]);
}}
function genericPopup(title, feature) {{
  const p = props(feature);
  const entries = Object.keys(p).slice(0, 12).map(key => [key, p[key]]);
  return popupTable(title, entries.length ? entries : [['Attributes', 'No attributes available']]);
}}
function landcoverStyle(feature) {{
  const classification = valueText(props(feature).classification);
  const fillColor = landcoverClassColors[classification] || landcoverClassColors.Other || '#000000';
  return {{
    color: fillColor,
    weight: 1,
    fillColor: fillColor,
    fillOpacity: 0.18,
    opacity: 0.70
  }};
}}

function initDashboard() {{
  setText('riskLoadedCount', riskFeatures().length);
  setText('landcoverLoadedCount', featureCount(landcoverData));
  setText('runoutLoadedCount', featureCount(runoutData));
  setText('riskFilteredCount', riskFeatures().length);
  setText('runoutBoundsText', boundsText(qradeRunoutBounds));

  if (typeof L === 'undefined') {{
    document.getElementById('leafletWarning').style.display = 'block';
    return;
  }}

  const map = L.map('map', {{
    preferCanvas: true,
    minZoom: 2,
    maxZoom: 19,
    maxBoundsViscosity: 0.7
  }}).setView([0, 0], 2);
  map.createPane('landcoverPane');
  map.getPane('landcoverPane').style.zIndex = 430;
  map.createPane('riskPane');
  map.getPane('riskPane').style.zIndex = 430;
  map.createPane('runoutPane');
  map.getPane('runoutPane').style.zIndex = 410;
  map.getPane('popupPane').style.zIndex = 1000;

  const openTopo = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 17,
    attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap (CC-BY-SA)'
  }});
  const osm = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }});
  let activeBasemap = osm;
  osm.on('tileerror', () => showMapWarning('OpenStreetMap tiles did not load. QRADE result layers remain embedded in this report.'));
  openTopo.on('tileerror', () => showMapWarning('OpenTopoMap tiles did not load. QRADE result layers remain embedded in this report.'));
  osm.addTo(map);

  const riskLayerGroup = L.layerGroup().addTo(map);
  let currentRiskLayer = null;
  let riskFeatureLayers = new Map();
  let currentView = 'risk';

  const runoutLayer = L.geoJSON(runoutData, {{
    pane: 'runoutPane',
    style: {{
      color: '#ff0000',
      weight: 4,
      fillColor: '#ff0000',
      fillOpacity: 0.08,
      opacity: 0.95
    }},
    onEachFeature: (feature, layer) => layer.bindPopup(genericPopup('Runout', feature))
  }}).addTo(map);

  const landcoverLayerGroup = L.layerGroup();
  let currentLandcoverLayer = null;

  function riskStyle(feature) {{
    const riskTotal = featureRiskTotal(feature);
    const classKey = riskClassKey(riskTotal);
    const isHigh = classKey === 'Critical' || classKey === 'High';
    const isModerate = classKey === 'Moderate';
    const isZero = classKey === 'Zero';
    return {{
      color: riskColorForValue(riskTotal),
      weight: isHigh ? 3 : (isModerate ? 2 : 1.5),
      fillColor: riskColorForValue(riskTotal),
      fillOpacity: isZero ? 0.08 : (isHigh ? 0.42 : 0.30),
      opacity: isZero ? 0.55 : 0.90
    }};
  }}

  function riskMatchesFilters(feature) {{
    const priorityFilter = document.getElementById('priorityFilter').value;
    const classificationFilter = document.getElementById('classificationFilter').value;
    const p = props(feature);
    const classKey = riskClassKey(p.risk_total);
    const classification = normalizedText(p.classification);
    if (priorityFilter === 'HighCritical' && !isHighCriticalRisk(p.risk_total)) return false;
    if (priorityFilter !== 'All' && priorityFilter !== 'HighCritical' && classKey !== priorityFilter) return false;
    if (classificationFilter !== 'All' && classification !== normalizedText(classificationFilter)) return false;
    return true;
  }}

  function filteredRiskFeatures() {{
    return riskFeatures().filter(riskMatchesFilters);
  }}
  function landcoverMatchesFilters(feature) {{
    const classificationFilter = document.getElementById('classificationFilter').value;
    const classification = normalizedText(props(feature).classification);
    return classificationFilter === 'All' || classification === normalizedText(classificationFilter);
  }}
  function filteredLandcoverFeatures() {{
    return landcoverFeatures().filter(landcoverMatchesFilters);
  }}

  function rebuildRiskLayer() {{
    riskLayerGroup.clearLayers();
    riskFeatureLayers = new Map();
    const filtered = filteredRiskFeatures();
    currentRiskLayer = L.geoJSON({{
      type: 'FeatureCollection',
      features: filtered
    }}, {{
      pane: 'riskPane',
      style: riskStyle,
      onEachFeature: (feature, layer) => {{
        layer.bindPopup(riskPopup(feature));
        const id = qradeId(props(feature));
        if (id) riskFeatureLayers.set(id, layer);
      }}
    }});
    riskLayerGroup.addLayer(currentRiskLayer);
    updateLayerStatus(filtered.length);
  }}
  function rebuildLandcoverLayer() {{
    landcoverLayerGroup.clearLayers();
    const filtered = filteredLandcoverFeatures();
    currentLandcoverLayer = L.geoJSON({{
      type: 'FeatureCollection',
      features: filtered
    }}, {{
      pane: 'landcoverPane',
      style: landcoverStyle,
      onEachFeature: (feature, layer) => layer.bindPopup(landcoverPopup(feature))
    }});
    landcoverLayerGroup.addLayer(currentLandcoverLayer);
  }}

  function updateLayerStatus(filteredRiskCount) {{
    const riskCount = riskFeatures().length;
    const landcoverCount = featureCount(landcoverData);
    const runoutCount = featureCount(runoutData);
    setText('riskLoadedCount', riskCount);
    setText('landcoverLoadedCount', landcoverCount);
    setText('runoutLoadedCount', runoutCount);
    setText('riskFilteredCount', filteredRiskCount);
    const messages = [];
    if (riskCount === 0) messages.push('Risk Assessment GeoJSON has zero features.');
    if (landcoverCount === 0) messages.push('LandCover GeoJSON has zero features.');
    if (runoutCount === 0) messages.push('Runout GeoJSON has zero features.');
    const expected = numeric(summaryFeatureCount);
    if (expected !== null && expected !== riskCount) {{
      messages.push('summary.json feature count (' + expected + ') differs from embedded Risk Assessment GeoJSON feature count (' + riskCount + '). Check that files come from the same output folder.');
    }}
    const warning = document.getElementById('layerStatusWarning');
    if (warning) {{
      warning.style.display = messages.length ? 'block' : 'none';
      warning.innerHTML = messages.map(message => '<div>' + message + '</div>').join('');
    }}
  }}

  const classificationSelect = document.getElementById('classificationFilter');
  const allKnownClassifications = __ALL_CLASSIFICATIONS__;
  function populateClassificationOptions(values) {{
    while (classificationSelect.options.length > 1) {{
      classificationSelect.remove(1);
    }}
    values.forEach(classification => {{
      const option = document.createElement('option');
      option.value = classification;
      option.textContent = classification;
      classificationSelect.appendChild(option);
    }});
  }}
  populateClassificationOptions(allKnownClassifications);

  rebuildRiskLayer();
  rebuildLandcoverLayer();

  function latLngBoundsFromArray(boundsArray) {{
    if (!Array.isArray(boundsArray) || boundsArray.length !== 2) return null;
    try {{
      const bounds = L.latLngBounds(boundsArray);
      return bounds && bounds.isValid() ? bounds : null;
    }} catch (error) {{
      return null;
    }}
  }}
  function fitLayer(layer) {{
    try {{
      bringLayerToFront(layer);
      const bounds = layer.getBounds();
      if (bounds && bounds.isValid()) map.fitBounds(bounds, {{ padding: [20, 20] }});
    }} catch (error) {{}}
  }}
  function ensureLayerVisible(layer) {{
    try {{
      if (layer && !map.hasLayer(layer)) layer.addTo(map);
    }} catch (error) {{}}
  }}
  function hideLayer(layer) {{
    try {{
      if (layer && map.hasLayer(layer)) map.removeLayer(layer);
    }} catch (error) {{}}
  }}
  const analysisBounds = latLngBoundsFromArray(qradeAnalysisBounds);
  const runoutBounds = latLngBoundsFromArray(qradeRunoutBounds);
  const landcoverBounds = latLngBoundsFromArray(qradeLandcoverBounds);
  const riskBounds = latLngBoundsFromArray(qradeRiskBounds);
  function fitFirstAvailable(boundsList, warningText) {{
    for (const bounds of boundsList) {{
      if (bounds) {{
        map.fitBounds(bounds, {{ padding: [30, 30], maxZoom: 15 }});
        return;
      }}
    }}
    showMapWarning(warningText);
    map.setView([0, 0], 2);
  }}
  function fitRunoutView() {{
    fitFirstAvailable([runoutBounds, analysisBounds, riskBounds], 'No valid Runout, analysis, or Risk extent was available. The map is using a default world view.');
  }}
  function fitLandcoverView() {{
    fitFirstAvailable([landcoverBounds, analysisBounds, runoutBounds, riskBounds], 'No valid LandCover, analysis, Runout, or Risk extent was available. The map is using a default world view.');
  }}
  function setViewButtons(activeView) {{
    document.getElementById('runoutRiskView').classList.toggle('active', activeView === 'risk');
    document.getElementById('landcoverView').classList.toggle('active', activeView === 'landcover');
  }}
  function setFilterState() {{
    const riskMode = currentView === 'risk';
    document.getElementById('priorityFilter').disabled = !riskMode;
    setText('riskFilteredCount', riskMode ? filteredRiskFeatures().length : 'Risk Assessment hidden in LandCover View');
  }}
  function activateRunoutRiskView(zoom) {{
    currentView = 'risk';
    setViewButtons(currentView);
    rebuildRiskLayer();
    ensureLayerVisible(riskLayerGroup);
    ensureLayerVisible(runoutLayer);
    hideLayer(landcoverLayerGroup);
    setFilterState();
    bringLayerToFront(runoutLayer);
    bringLayerToFront(currentRiskLayer);
    if (zoom) fitRunoutView();
  }}
  function activateLandcoverView(zoom) {{
    currentView = 'landcover';
    setViewButtons(currentView);
    rebuildLandcoverLayer();
    hideLayer(riskLayerGroup);
    ensureLayerVisible(landcoverLayerGroup);
    ensureLayerVisible(runoutLayer);
    setFilterState();
    bringLayerToFront(runoutLayer);
    bringLayerToFront(currentLandcoverLayer);
    if (zoom) fitLandcoverView();
  }}
  document.getElementById('priorityFilter').addEventListener('change', () => {{
    if (currentView !== 'risk') return;
    rebuildRiskLayer();
    setFilterState();
    bringLayerToFront(currentRiskLayer);
  }});
  classificationSelect.addEventListener('change', () => {{
    if (currentView === 'risk') {{
      rebuildRiskLayer();
      setFilterState();
      bringLayerToFront(currentRiskLayer);
    }} else {{
      rebuildLandcoverLayer();
      bringLayerToFront(currentLandcoverLayer);
    }}
  }});
  document.getElementById('runoutRiskView').addEventListener('click', () => activateRunoutRiskView(true));
  document.getElementById('landcoverView').addEventListener('click', () => activateLandcoverView(true));
  document.querySelectorAll('input[name="basemapChoice"]').forEach(input => {{
    input.addEventListener('change', () => {{
      try {{
        if (activeBasemap && map.hasLayer(activeBasemap)) map.removeLayer(activeBasemap);
        activeBasemap = input.value === 'topo' ? openTopo : osm;
        activeBasemap.addTo(map);
      }} catch (error) {{
        showMapWarning('Could not switch basemap. QRADE result layers remain available.');
      }}
    }});
  }});
  document.getElementById('resetFilters').addEventListener('click', () => {{
    if (currentView === 'landcover') {{
      classificationSelect.value = 'All';
      activateLandcoverView(true);
      return;
    }}
    document.getElementById('priorityFilter').value = 'All';
    classificationSelect.value = 'All';
    activateRunoutRiskView(true);
  }});
  document.querySelectorAll('.zoom-risk-row').forEach(button => {{
    button.addEventListener('click', () => {{
      document.getElementById('priorityFilter').value = 'All';
      classificationSelect.value = 'All';
      activateRunoutRiskView(false);
      const id = button.getAttribute('data-qrade-id');
      const layer = riskFeatureLayers.get(id);
      if (layer) {{
        bringLayerToFront(layer);
        fitLayer(layer);
        layer.openPopup();
      }}
    }});
  }});

  activateRunoutRiskView(false);
  map.on('overlayadd', () => {{
    bringLayerToFront(runoutLayer);
    bringLayerToFront(currentRiskLayer);
  }});
  map.invalidateSize(true);
  setTimeout(() => {{
    map.invalidateSize(true);
    bringLayerToFront(runoutLayer);
    bringLayerToFront(currentRiskLayer);
  }}, 250);
  setTimeout(() => {{
    map.invalidateSize(true);
    fitRunoutView();
    bringLayerToFront(runoutLayer);
    bringLayerToFront(currentRiskLayer);
  }}, 1000);
}}

document.addEventListener('DOMContentLoaded', () => {{
  try {{
    initDashboard();
  }} catch (error) {{
    const warning = document.getElementById('leafletWarning');
    warning.textContent = 'Interactive map initialization failed. Dashboard sections and data links remain available. ' + error;
    warning.style.display = 'block';
  }}
}});
</script>
</body>
</html>
"""

        html_content = (
            html_template.replace('{{', '{').replace('}}', '}')
            .replace('__WARNING_HTML__', warning_html)
            .replace('__LOGO_MARKUP__', logo_markup)
            .replace('__RUN_BADGE__', run_badge_html)
            .replace('__RUN_INFO_ROWS__', run_info_rows)
            .replace('__CARD_HTML__', card_html)
            .replace('__PRIORITY_ROWS__', priority_rows)
            .replace('__CATEGORY_ROWS__', category_rows)
            .replace('__RISK_CLASS_ROWS__', risk_class_rows)
            .replace('__LANDCOVER_LEGEND_ROWS__', landcover_legend_html)
            .replace('__TOP_ROWS_HTML__', top_rows_html)
            .replace('__CLASSIFICATION_ROWS__', classification_rows)
            .replace('__RISK_GEOJSON__', js_json(risk_geojson))
            .replace('__LANDCOVER_GEOJSON__', js_json(landcover_geojson))
            .replace('__RUNOUT_GEOJSON__', js_json(runout_geojson))
            .replace('__BIM_JSON__', js_json(bim_export if isinstance(bim_export, dict) else {}))
            .replace('__SUMMARY_FEATURE_COUNT__', js_json(statistics.get('feature_count')))
            .replace('__ANALYSIS_BOUNDS__', js_json(qrade_analysis_bounds))
            .replace('__LANDCOVER_BOUNDS__', js_json(qrade_landcover_bounds))
            .replace('__RISK_BOUNDS__', js_json(qrade_risk_bounds))
            .replace('__RUNOUT_BOUNDS__', js_json(qrade_runout_bounds))
            .replace('__ALL_CLASSIFICATIONS__', js_json(all_classifications))
            .replace('__LANDCOVER_CLASS_COLORS__', js_json(dict(official_landcover_classes)))
            .replace('__EXTENT_SOURCE__', text(qrade_analysis_bounds_source))
        )

        try:
            os.makedirs(web_report_dir, exist_ok=True)
            with open(index_html_path, 'w', encoding='utf-8') as html_file:
                html_file.write(html_content)
        except Exception as e:
            raise QgsProcessingException(f'Could not write QRADE WebGIS report HTML: {index_html_path}\n{e}')

        feedback.pushInfo(f'WebGIS report written: {index_html_path}')
        return index_html_path

    def _write_qa_qc_report(self, output_paths, run_metadata, summary_paths, bim_paths, webgis_paths, feedback):
        feedback.pushInfo('Writing QRADE Smart QA/QC report...')

        qa_qc_dir = output_paths['qa_qc_dir']
        json_path = output_paths['qa_qc_json']
        csv_path = output_paths['qa_qc_csv']
        html_path = output_paths['qa_qc_html']

        checks = []
        recommendations = []
        output_inventory = {}
        diagnostics = {
            'temporal_probability_diagnostics': {},
            'classification_diagnostics': {},
            'bim_diagnostics': {},
            'webgis_diagnostics': {},
        }

        def read_json(path):
            if not path or not os.path.exists(path):
                return None, 'file does not exist'
            try:
                with open(path, 'r', encoding='utf-8') as json_file:
                    return json.load(json_file), None
            except Exception as e:
                return None, str(e)

        def count_geojson_features(path):
            data, error = read_json(path)
            if error:
                return None, error
            features = data.get('features') if isinstance(data, dict) else None
            if isinstance(features, list):
                return len(features), None
            return None, 'GeoJSON features array not found'

        def add_recommendation(text_value):
            if text_value and text_value not in recommendations:
                recommendations.append(text_value)

        def add_check(
            check_id,
            group,
            severity,
            status,
            message,
            recommendation='',
            related_file='',
            related_field='',
            related_count=''
        ):
            checks.append({
                'check_id': check_id,
                'group': group,
                'severity': severity,
                'status': status,
                'message': message,
                'recommendation': recommendation,
                'related_file': related_file,
                'related_field': related_field,
                'related_count': related_count,
            })
            if recommendation and severity in ('WARNING', 'CRITICAL'):
                add_recommendation(recommendation)

        def inventory_file(key, path, required=True, group='Output inventory'):
            exists = bool(path and os.path.exists(path))
            output_inventory[key] = {
                'path': path,
                'exists': exists,
                'size_bytes': os.path.getsize(path) if exists else None,
            }
            if exists:
                add_check(
                    f'output_{key}',
                    group,
                    'PASS',
                    'PASS',
                    f'Output file exists: {key}',
                    related_file=path
                )
            elif required:
                add_check(
                    f'output_{key}',
                    group,
                    'CRITICAL',
                    'CRITICAL',
                    f'Required output file is missing: {key}',
                    'Review the processing log and rerun QRADE if needed.',
                    related_file=path
                )
            else:
                add_check(
                    f'output_{key}',
                    group,
                    'INFO',
                    'INFO',
                    f'Output file not selected or not required: {key}',
                    related_file=path
                )

        summary_json_path = summary_paths.get('summary_json')
        summary_csv_path = summary_paths.get('summary_csv')
        bim_json_path = bim_paths.get('bim_json')
        bim_csv_path = bim_paths.get('bim_csv')
        ifc_mapping_template_path = bim_paths.get('ifc_mapping_template')
        bcf_zip_path = bim_paths.get('bcf_zip')
        bcf_readme_path = bim_paths.get('bcf_readme')
        expected_bcf_issue_count = bim_paths.get('bcf_issue_count')
        try:
            expected_bcf_issue_count_for_inventory = int(expected_bcf_issue_count)
        except Exception:
            expected_bcf_issue_count_for_inventory = None
        bcf_zip_exists_for_inventory = bool(bcf_zip_path and os.path.exists(bcf_zip_path))
        bcf_readme_exists_for_inventory = bool(bcf_readme_path and os.path.exists(bcf_readme_path))
        web_data_dir = webgis_paths.get('web_data_dir')
        web_index_path = webgis_paths.get('index_html')

        inventory_file('gis/landcover.gpkg', output_paths['landcover_gpkg'], bool(run_metadata.get('save_landcover')))
        inventory_file('gis/runout.gpkg', output_paths['runout_gpkg'], bool(run_metadata.get('save_runout')))
        inventory_file('gis/risk_assessment.gpkg', output_paths['risk_assessment_gpkg'], bool(run_metadata.get('save_riskassessment')))
        inventory_file('summary/summary.json', summary_json_path, True)
        inventory_file('summary/summary.csv', summary_csv_path, True)
        inventory_file('bim/qrade_bim_risk.csv', bim_csv_path, True)
        inventory_file('bim/qrade_bim_risk.json', bim_json_path, True)
        inventory_file('bim/qrade_ifc_guid_mapping_template.csv', ifc_mapping_template_path, True, 'BIM')
        if bcf_zip_exists_for_inventory or (
            expected_bcf_issue_count_for_inventory is not None
            and expected_bcf_issue_count_for_inventory > 0
        ):
            inventory_file('bim/bcf_issues/qrade_rockfall_risk_issues.bcfzip', bcf_zip_path, False, 'BIM')
        elif bcf_readme_exists_for_inventory:
            inventory_file('bim/bcf_issues/README_no_high_risk_issues.txt', bcf_readme_path, False, 'BIM')
        inventory_file('reports/web_report/index.html', web_index_path, True, 'WebGIS')
        inventory_file('reports/web_report/data/risk_assessment.geojson', output_paths['web_report_risk_geojson'], True, 'WebGIS')
        inventory_file('reports/web_report/data/landcover.geojson', output_paths['web_report_landcover_geojson'], True, 'WebGIS')
        inventory_file('reports/web_report/data/runout.geojson', output_paths['web_report_runout_geojson'], True, 'WebGIS')

        if run_metadata.get('risk_assessment_energy_filter_applied'):
            before_filter = run_metadata.get('risk_assessment_features_before_energy_filter')
            after_filter = run_metadata.get('risk_assessment_features_after_energy_filter')
            removed_filter = run_metadata.get('risk_assessment_features_removed_no_energy')
            add_check(
                'risk_assessment_positive_energy_filter',
                'Risk',
                'INFO',
                'INFO',
                (
                    'Risk Assessment output was filtered to features with positive energy_max. '
                    f'Kept {after_filter} of {before_filter} feature(s); '
                    f'removed {removed_filter} feature(s) with null or zero energy_max.'
                ),
                related_field='energy_max',
                related_count=after_filter
            )

        summary, summary_error = read_json(summary_json_path)
        statistics = {}
        feature_count = None
        if summary_error:
            add_check(
                'summary_json_readable',
                'Summary',
                'CRITICAL',
                'CRITICAL',
                f'Could not read summary.json: {summary_error}',
                'Review summary export and rerun QRADE if needed.',
                related_file=summary_json_path
            )
        else:
            add_check('summary_json_readable', 'Summary', 'PASS', 'PASS', 'summary.json is readable.', related_file=summary_json_path)
            statistics = summary.get('statistics', {}) if isinstance(summary, dict) else {}
            feature_count = statistics.get('feature_count')
            null_risk_total_count = statistics.get('null_risk_total_count')
            max_risk_total = statistics.get('max_risk_total')
            classification_counts = statistics.get('classification_counts', {})
            top_features = statistics.get('top_10_by_risk_total', [])

            if isinstance(feature_count, (int, float)) and feature_count > 0:
                add_check('summary_feature_count', 'Summary', 'PASS', 'PASS', f'Risk feature count is {feature_count}.', related_count=feature_count)
            else:
                add_check('summary_feature_count', 'Summary', 'CRITICAL', 'CRITICAL', 'Risk feature count is zero or missing.', 'Confirm the run produced risk-assessment features.', related_count=feature_count)

            if null_risk_total_count == 0:
                add_check('risk_total_null_count', 'Risk', 'PASS', 'PASS', 'No null risk_total values were reported.', related_field='risk_total', related_count=0)
            else:
                severity = 'CRITICAL' if isinstance(null_risk_total_count, (int, float)) and null_risk_total_count > 10 else 'WARNING'
                add_check(
                    'risk_total_null_count',
                    'Risk',
                    severity,
                    severity,
                    f'Null risk_total values reported: {null_risk_total_count}',
                    'Inspect classification joins, vulnerability fields, and risk-value table consistency.',
                    related_field='risk_total',
                    related_count=null_risk_total_count
                )

            if max_risk_total is None:
                add_check('max_risk_total_recorded', 'Risk', 'WARNING', 'WARNING', 'max_risk_total is missing.', 'Review summary statistics.', related_field='risk_total')
            else:
                add_check('max_risk_total_recorded', 'Risk', 'PASS', 'PASS', f'max_risk_total recorded: {max_risk_total}', related_field='risk_total', related_count=max_risk_total)
                try:
                    if float(max_risk_total) >= 0.75:
                        add_check(
                            'critical_risk_present',
                            'Risk',
                            'INFO',
                            'INFO',
                            'At least one feature has risk_total >= 0.75.',
                            'Review top-risk features and mitigation priorities.',
                            related_field='risk_total',
                            related_count=max_risk_total
                        )
                except Exception:
                    pass

            if isinstance(classification_counts, dict) and classification_counts:
                add_check('classification_counts_present', 'Classification', 'PASS', 'PASS', 'Classification counts are available.')
                other_count = classification_counts.get('Other', 0)
                other_percentage = (float(other_count) / float(feature_count) * 100.0) if feature_count else 0.0
                diagnostics['classification_diagnostics'] = {
                    'classification_counts': classification_counts,
                    'other_count': other_count,
                    'other_percentage': other_percentage,
                }
                if other_count > 0:
                    add_check(
                        'classification_other_count',
                        'Classification',
                        'WARNING',
                        'WARNING',
                        f'Features classified as Other: {other_count}',
                        'Review Other features and reclassify where appropriate.',
                        related_field='classification',
                        related_count=other_count
                    )
                else:
                    add_check('classification_other_count', 'Classification', 'PASS', 'PASS', 'No Other classifications were reported.', related_field='classification', related_count=0)
                if other_percentage > 5.0:
                    add_check(
                        'classification_other_percentage',
                        'Classification',
                        'WARNING',
                        'WARNING',
                        f'Other classifications exceed 5%: {other_percentage:.2f}%',
                        'Review classification rules or manual inputs before using results for decisions.',
                        related_field='classification',
                        related_count=f'{other_percentage:.2f}%'
                    )
            else:
                add_check('classification_counts_present', 'Classification', 'WARNING', 'WARNING', 'Classification counts are missing.', 'Review summary export.', related_field='classification')

            if isinstance(top_features, list) and top_features:
                add_check('top_risk_features_present', 'Risk', 'PASS', 'PASS', 'Top-risk feature list is available.', related_count=len(top_features))
            else:
                add_check('top_risk_features_present', 'Risk', 'WARNING', 'WARNING', 'Top-risk feature list is missing or empty.', 'Review summary export and risk layer.', related_count=0)

        temporal_value = run_metadata.get('temporal_probability_value')
        temporal_diagnostics = {
            'temporal_probability_mode': run_metadata.get('temporal_probability_mode'),
            'temporal_probability_value': temporal_value,
            'temporal_lambda_per_year': run_metadata.get('temporal_lambda_per_year'),
            'temporal_expected_events': run_metadata.get('temporal_expected_events'),
            'temporal_equivalent_return_period_years': run_metadata.get('temporal_equivalent_return_period_years'),
            'temporal_probability_quality': run_metadata.get('temporal_probability_quality'),
            'temporal_probability_warnings': run_metadata.get('temporal_probability_warnings') or [],
        }
        diagnostics['temporal_probability_diagnostics'] = temporal_diagnostics
        add_check('temporal_probability_mode_recorded', 'Temporal probability', 'INFO', 'INFO', f"Temporal probability mode: {temporal_diagnostics.get('temporal_probability_mode')}")
        temporal_quality = temporal_diagnostics.get('temporal_probability_quality')
        is_time_independent_temporal = (
            temporal_quality == 'TIME_INDEPENDENT'
            or temporal_diagnostics.get('temporal_probability_mode') == 'Time-Independent'
        )
        if temporal_quality:
            acceptable_temporal_qualities = ('ACCEPTABLE', 'TIME_INDEPENDENT', 'NOT_APPLICABLE')
            quality_severity = 'PASS' if temporal_quality in acceptable_temporal_qualities else 'WARNING'
            add_check(
                'temporal_probability_quality',
                'Temporal probability',
                quality_severity,
                temporal_quality,
                f'Temporal probability quality: {temporal_quality}',
                'Review temporal probability diagnostics and assumptions.' if quality_severity == 'WARNING' else '',
                related_field='temporal_probability'
            )
        temporal_warnings = temporal_diagnostics.get('temporal_probability_warnings') or []
        if temporal_warnings:
            add_check(
                'temporal_probability_warnings',
                'Temporal probability',
                'WARNING',
                'WARNING',
                '; '.join(str(item) for item in temporal_warnings),
                'Review temporal probability inputs before decision-making.',
                related_field='temporal_probability',
                related_count=len(temporal_warnings)
            )
        if temporal_value is not None:
            try:
                temporal_float = float(temporal_value)
                add_check('temporal_probability_value_recorded', 'Temporal probability', 'PASS', 'PASS', f'Temporal probability value: {temporal_float:.6g}', related_field='temporal_probability', related_count=temporal_float)
                if not is_time_independent_temporal and temporal_float > 0.99:
                    add_check(
                        'temporal_probability_near_time_independent',
                        'Temporal probability',
                        'WARNING',
                        'WARNING',
                        'Temporal probability is greater than 0.99 and behaves almost time-independent.',
                        'Review temporal probability assumptions.',
                        related_field='temporal_probability',
                        related_count=temporal_float
                    )
                elif not is_time_independent_temporal and temporal_float > 0.95:
                    add_check(
                        'temporal_probability_saturation',
                        'Temporal probability',
                        'WARNING',
                        'WARNING',
                        'Temporal probability is greater than 0.95.',
                        'Review whether probability saturation is expected.',
                        related_field='temporal_probability',
                        related_count=temporal_float
                    )
            except Exception:
                add_check('temporal_probability_value_recorded', 'Temporal probability', 'WARNING', 'WARNING', f'Temporal probability value is not numeric: {temporal_value}', 'Review temporal probability settings.', related_field='temporal_probability')

        bim_export, bim_error = read_json(bim_json_path)
        if bim_error:
            add_check('bim_json_readable', 'BIM', 'WARNING', 'WARNING', f'Could not read BIM JSON: {bim_error}', 'Review BIM-ready export files.', related_file=bim_json_path)
        else:
            add_check('bim_json_readable', 'BIM', 'PASS', 'PASS', 'BIM JSON is readable.', related_file=bim_json_path)
            records = bim_export.get('records', []) if isinstance(bim_export, dict) else []
            record_count = len(records) if isinstance(records, list) else None
            if feature_count is not None and record_count == feature_count:
                add_check('bim_record_count_matches_summary', 'BIM', 'PASS', 'PASS', 'BIM record count matches summary feature count.', related_count=record_count)
            else:
                add_check('bim_record_count_matches_summary', 'BIM', 'WARNING', 'WARNING', f'BIM record count ({record_count}) does not match summary feature count ({feature_count}).', 'Compare risk layer and BIM export.', related_count=record_count)
            blank_ifc_count = 0
            priority_counts = {}
            if isinstance(records, list):
                for record in records:
                    if not isinstance(record, dict):
                        continue
                    if not str(record.get('ifc_guid') or '').strip():
                        blank_ifc_count += 1
                    priority = str(record.get('bcf_priority') or '').strip()
                    if priority:
                        priority_counts[priority] = priority_counts.get(priority, 0) + 1
            high_critical_count = priority_counts.get('High', 0) + priority_counts.get('Critical', 0)
            diagnostics['bim_diagnostics'] = {
                'record_count': record_count,
                'blank_ifc_guid_count': blank_ifc_count,
                'bcf_priority_counts': priority_counts,
                'high_critical_priority_count': high_critical_count,
            }
            add_check('bim_ifc_guid_blank_count', 'BIM', 'INFO', 'INFO', f'Blank IFC GUID values: {blank_ifc_count}. This is expected until external BIM mapping is added.', related_field='ifc_guid', related_count=blank_ifc_count)
            if high_critical_count > 0:
                add_check('bim_high_critical_priorities', 'BIM', 'INFO', 'INFO', f'High/Critical BIM priority records: {high_critical_count}', 'Review high-priority records for BIM coordination.', related_field='bcf_priority', related_count=high_critical_count)
            if expected_bcf_issue_count is None:
                expected_bcf_issue_count = high_critical_count

        if ifc_mapping_template_path and os.path.exists(ifc_mapping_template_path):
            try:
                mapping_row_count = 0
                blank_mapping_guid_count = 0
                with open(ifc_mapping_template_path, newline='', encoding='utf-8') as csv_file:
                    reader = csv.DictReader(csv_file)
                    for row in reader:
                        mapping_row_count += 1
                        if not str(row.get('ifc_guid') or '').strip():
                            blank_mapping_guid_count += 1
                add_check(
                    'ifc_guid_mapping_template_blank_guid_count',
                    'BIM',
                    'INFO',
                    'INFO',
                    f'Blank IFC GUID values in mapping template: {blank_mapping_guid_count}. This is expected until manual BIM/IFC mapping is completed.',
                    related_file=ifc_mapping_template_path,
                    related_field='ifc_guid',
                    related_count=blank_mapping_guid_count
                )
                diagnostics['bim_diagnostics']['ifc_guid_mapping_template_row_count'] = mapping_row_count
                diagnostics['bim_diagnostics']['ifc_guid_mapping_template_blank_guid_count'] = blank_mapping_guid_count
            except Exception as e:
                add_check(
                    'ifc_guid_mapping_template_readable',
                    'BIM',
                    'WARNING',
                    'WARNING',
                    f'Could not inspect IFC GUID mapping template: {e}',
                    'Review the mapping template CSV.',
                    related_file=ifc_mapping_template_path
                )

        try:
            expected_bcf_issue_count_value = int(expected_bcf_issue_count)
        except Exception:
            expected_bcf_issue_count_value = None
        bcf_zip_exists = bool(bcf_zip_path and os.path.exists(bcf_zip_path))
        bcf_readme_exists = bool(bcf_readme_path and os.path.exists(bcf_readme_path))
        if expected_bcf_issue_count_value is not None and expected_bcf_issue_count_value > 0:
            if bcf_zip_exists:
                add_check(
                    'bcf_issue_export_created',
                    'BIM',
                    'PASS',
                    'PASS',
                    f'BCF issue package exists for {expected_bcf_issue_count_value} High/Critical risk feature(s).',
                    related_file=bcf_zip_path,
                    related_count=expected_bcf_issue_count_value
                )
            else:
                add_check(
                    'bcf_issue_export_created',
                    'BIM',
                    'WARNING',
                    'WARNING',
                    f'High/Critical risk features were found ({expected_bcf_issue_count_value}) but the BCF issue package is missing.',
                    'Review BCF issue export generation and rerun QRADE if needed.',
                    related_file=bcf_zip_path,
                    related_count=expected_bcf_issue_count_value
                )
        elif expected_bcf_issue_count_value == 0:
            if bcf_readme_exists:
                add_check(
                    'bcf_issue_export_empty_case',
                    'BIM',
                    'PASS',
                    'PASS',
                    'No High/Critical risk features were found; empty-case BCF README exists.',
                    related_file=bcf_readme_path,
                    related_count=0
                )
            else:
                add_check(
                    'bcf_issue_export_empty_case',
                    'BIM',
                    'INFO',
                    'INFO',
                    'No High/Critical risk features were found; no BCF issue package was needed.',
                    related_count=0
                )
        diagnostics['bim_diagnostics']['bcf_issue_count'] = expected_bcf_issue_count_value
        diagnostics['bim_diagnostics']['bcf_issue_package_exists'] = bcf_zip_exists
        diagnostics['bim_diagnostics']['bcf_empty_case_readme_exists'] = bcf_readme_exists

        risk_geojson_path = os.path.join(web_data_dir, 'risk_assessment.geojson') if web_data_dir else ''
        risk_geojson_count, risk_geojson_error = count_geojson_features(risk_geojson_path)
        diagnostics['webgis_diagnostics'] = {
            'risk_assessment_geojson_feature_count': risk_geojson_count,
            'risk_assessment_geojson_error': risk_geojson_error,
        }
        if risk_geojson_error:
            add_check('webgis_risk_geojson_count', 'WebGIS', 'WARNING', 'WARNING', f'Could not count risk GeoJSON features: {risk_geojson_error}', 'Review WebGIS data bundle.', related_file=risk_geojson_path)
        elif feature_count is not None and risk_geojson_count != feature_count:
            add_check('webgis_risk_geojson_count', 'WebGIS', 'WARNING', 'WARNING', f'Risk GeoJSON feature count ({risk_geojson_count}) does not match summary feature count ({feature_count}).', 'Compare WebGIS GeoJSON and risk assessment output.', related_file=risk_geojson_path, related_count=risk_geojson_count)
        else:
            add_check('webgis_risk_geojson_count', 'WebGIS', 'PASS', 'PASS', 'Risk GeoJSON feature count matches summary feature count.', related_file=risk_geojson_path, related_count=risk_geojson_count)

        severity_counts = {severity: 0 for severity in ('PASS', 'INFO', 'WARNING', 'CRITICAL')}
        for check in checks:
            severity = check.get('severity', 'INFO')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if severity_counts.get('CRITICAL', 0):
            overall_status = 'CRITICAL'
        elif severity_counts.get('WARNING', 0):
            overall_status = 'WARNING'
        else:
            overall_status = 'PASS'

        report = {
            'metadata': run_metadata,
            'overall_status': overall_status,
            'severity_counts': severity_counts,
            'checks': checks,
            'recommendations': recommendations,
            'output_inventory': output_inventory,
            'diagnostics': diagnostics,
        }

        def cell(value):
            return html.escape('' if value is None else str(value))

        check_rows = '\n'.join(
            '<tr>'
            f'<td>{cell(check.get("check_id"))}</td>'
            f'<td>{cell(check.get("group"))}</td>'
            f'<td><span class="badge {cell(check.get("severity"))}">{cell(check.get("severity"))}</span></td>'
            f'<td>{cell(check.get("status"))}</td>'
            f'<td>{cell(check.get("message"))}</td>'
            f'<td>{cell(check.get("recommendation"))}</td>'
            '</tr>'
            for check in checks
        )
        recommendation_items = ''.join(f'<li>{cell(item)}</li>' for item in recommendations) or '<li>No recommendations generated.</li>'
        inventory_rows = '\n'.join(
            '<tr>'
            f'<td>{cell(key)}</td>'
            f'<td>{cell(item.get("exists"))}</td>'
            f'<td>{cell(item.get("path"))}</td>'
            f'<td>{cell(item.get("size_bytes"))}</td>'
            '</tr>'
            for key, item in output_inventory.items()
        )
        severity_cards = '\n'.join(
            f'<div class="card"><span>{cell(key)}</span><strong>{cell(value)}</strong></div>'
            for key, value in severity_counts.items()
        )
        diagnostics_html = cell(json.dumps(diagnostics, indent=2, sort_keys=True))

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>QRADE Smart QA/QC Report</title>
<style>
body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; color: #1f2933; background: #f5f7fa; }}
header {{ padding: 24px 32px; background: #263238; color: #fff; }}
main {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
section {{ margin-bottom: 24px; padding: 18px; background: #fff; border: 1px solid #d8dee4; }}
table {{ width: 100%; border-collapse: collapse; }}
table {{ table-layout: fixed; }}
th, td {{ padding: 8px; border: 1px solid #d8dee4; text-align: left; vertical-align: top; overflow-wrap: anywhere; word-break: break-word; }}
th {{ background: #eef2f5; }}
.table-wrap {{ width: 100%; overflow-x: auto; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }}
.card {{ padding: 14px; border: 1px solid #d8dee4; background: #f8fafc; }}
.card span {{ display: block; margin-bottom: 8px; color: #52616b; font-size: 13px; }}
.card strong {{ display: block; font-size: 22px; }}
.badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-weight: bold; }}
.PASS {{ background: #dcfce7; color: #166534; }}
.INFO {{ background: #dbeafe; color: #1e40af; }}
.WARNING {{ background: #fef3c7; color: #92400e; }}
.CRITICAL {{ background: #fee2e2; color: #991b1b; }}
pre {{ white-space: pre-wrap; background: #f8fafc; padding: 12px; border: 1px solid #d8dee4; }}
</style>
</head>
<body>
<header>
<h1>QRADE Smart QA/QC Report</h1>
</header>
<main>
<section>
<h2>Overall Status</h2>
<div class="cards">
<div class="card"><span>Overall status</span><strong>{cell(overall_status)}</strong></div>
{severity_cards}
</div>
</section>
<section>
<h2>Recommendations</h2>
<ul>{recommendation_items}</ul>
</section>
<section>
<h2>Checks</h2>
<div class="table-wrap">
<table class="checks-table">
<colgroup>
<col style="width:18%">
<col style="width:12%">
<col style="width:10%">
<col style="width:10%">
<col style="width:30%">
<col style="width:20%">
</colgroup>
<thead><tr><th>ID</th><th>Group</th><th>Severity</th><th>Status</th><th>Message</th><th>Recommendation</th></tr></thead>
<tbody>{check_rows}</tbody>
</table>
</div>
</section>
<section>
<h2>Output Inventory</h2>
<table>
<thead><tr><th>Output</th><th>Exists</th><th>Path</th><th>Size bytes</th></tr></thead>
<tbody>{inventory_rows}</tbody>
</table>
</section>
<section>
<h2>Diagnostics</h2>
<pre>{diagnostics_html}</pre>
</section>
<section>
<h2>Notes</h2>
<ul>
<li>This report is generated from existing QRADE outputs and metadata.</li>
<li>Review warnings and recommendations before decision-making.</li>
</ul>
</section>
</main>
</body>
</html>
"""

        try:
            os.makedirs(qa_qc_dir, exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(report, json_file, indent=2, sort_keys=True)
            with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=[
                    'check_id',
                    'group',
                    'severity',
                    'status',
                    'message',
                    'recommendation',
                    'related_file',
                    'related_field',
                    'related_count',
                ])
                writer.writeheader()
                for check in checks:
                    writer.writerow({
                        'check_id': check.get('check_id', ''),
                        'group': check.get('group', ''),
                        'severity': check.get('severity', ''),
                        'status': check.get('status', ''),
                        'message': check.get('message', ''),
                        'recommendation': check.get('recommendation', ''),
                        'related_file': check.get('related_file', ''),
                        'related_field': check.get('related_field', ''),
                        'related_count': check.get('related_count', ''),
                    })
            with open(html_path, 'w', encoding='utf-8') as html_file:
                html_file.write(html_content)
        except Exception as e:
            raise QgsProcessingException(f'Could not write QRADE Smart QA/QC report in: {qa_qc_dir}\n{e}')

        feedback.pushInfo(f'QA/QC JSON written: {json_path}')
        feedback.pushInfo(f'QA/QC CSV written: {csv_path}')
        feedback.pushInfo(f'QA/QC HTML written: {html_path}')
        return json_path, csv_path, html_path

    def initAlgorithm(self, config=None):
        # Base directory of this file (plugin root)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(base_dir, 'Input')
        templates_dir = os.path.join(base_dir, 'Templates')
        default_csv = os.path.join(input_dir, 'classification_table.csv')

        # Landcover source
        self.addParameter(
            QgsProcessingParameterEnum(
                'landcover_source',
                'Land Cover Source',
                options=['Auto (generated from OSM)', 'Manual (user-defined landcover layer)'],
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=[0]
            )
        )

        # Manual landcover layer (optional so Auto OSM mode does not require it)
        self.addParameter(
            QgsProcessingParameterFile(
                'landcover_manual',
                'Manual LandCover Layer (Vector file / GeoPackage)',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='Vector files (*.gpkg *.shp *.geojson *.json);;GeoPackage (*.gpkg);;All files (*.*)',
                defaultValue=None,
                optional=True
            )
        )

# Extent
        self.addParameter(
            QgsProcessingParameterExtent(
                'extent',
                'Extent',
                defaultValue=None
            )
        )

        # Define risk assessment values
        self.addParameter(
            QgsProcessingParameterEnum(
                'risk_value_mode',
                'Risk Assessment Values',
                options=['Auto (use default values)', 'Manual (user-defined table)'],
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=[0]
            )
        )

                # Manual/custom classification table. Users create this with the Smart Assistant editor.
        self.addParameter(
            QgsProcessingParameterFile(
                'classification_table_manual',
                'Manual Classification Table (CSV; first edit values in Smart Assistant, then choose the saved custom CSV here)',
                behavior=QgsProcessingParameterFile.File,
                fileFilter='CSV Files (*.csv)',
                defaultValue='',
                optional=True
            )
        )

        # Area Type
        self.addParameter(
            QgsProcessingParameterEnum(
                'area_type',
                'Area Type and Buildings Typology',
                options=['Suburban (Masonry buildings)', 'Urban (Reinforced Concrete buildings)'],
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=[0]
            )
        )
        # Mean energy raster
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'mean_energy',
                'Kinetic Energy raster (J)',
                defaultValue=None
            )
        )

        # Temporal probability of occurrence
        self.addParameter(
            QgsProcessingParameterEnum(
                'temporal_mode',
                'Temporal Probability of Occurrence',
                options=[
                    'Time-Independent',
                    'Auto (Frequency-Based model)',
                    'Manual (Case-specific Volume-Based model)'
                ],
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=[0]
            )
        )

        # (Auto mode only) Number of events (N)
        p_number_of_events = QgsProcessingParameterNumber(
                'number_of_events',
                'Number of Recorded Events',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                defaultValue=None,
                optional=True
        )
        p_number_of_events.setMetadata({'widget_wrapper': {'decimals': 2}})
        self.addParameter(p_number_of_events)

        # (Auto mode only) Time span of all recorded events (years) (Tobs)
        p_time_span_years = QgsProcessingParameterNumber(
                'time_span_years',
                'Observation Period (Years)',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                defaultValue=None,
                optional=True
        )
        p_time_span_years.setMetadata({'widget_wrapper': {'decimals': 2}})
        self.addParameter(p_time_span_years)

        # (Auto mode only) Concerned return period (years) (Tr)
        p_return_period_years = QgsProcessingParameterNumber(
                'return_period_years',
                'Assessment Time Window (Years)',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                defaultValue=None,
                optional=True
        )
        p_return_period_years.setMetadata({'widget_wrapper': {'decimals': 2}})
        self.addParameter(p_return_period_years)

        # (Manual mode only) Temporal probability P (0-1)
        p_temporal_probability_manual = QgsProcessingParameterNumber(
                'temporal_probability_manual',
                'Temporal Probability (0-1)',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                maxValue=1,
                defaultValue=None,
                optional=True
        )
        p_temporal_probability_manual.setMetadata({'widget_wrapper': {'decimals': 2}})
        self.addParameter(p_temporal_probability_manual)

        # Output folder chosen by the user; results are saved inside a timestamped subfolder
        default_output_folder = os.path.join(base_dir, 'Result')
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                'output_folder',
                'Output Folder',
                defaultValue=default_output_folder,
                optional=False
            )
        )

        output_options_note = QgsProcessingParameterString(
            'output_options_note',
            'Optional GIS layer outputs',
            defaultValue=(
                'Automatic outputs: Reports, QA/QC files, BIM deliverables, summary files, '
                'and the output manifest are generated automatically in the timestamped '
                'QRADE result folder.'
            ),
            multiLine=True,
            optional=True
        )
        output_options_note.setMetadata({'widget_wrapper': {'readOnly': True}})
        self.addParameter(output_options_note)

        self.addParameter(
            QgsProcessingParameterBoolean(
                'save_landcover',
                'Save LandCover Layer',
                defaultValue=True,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                'save_riskassessment',
                'Save Risk Assessment Layer',
                defaultValue=True,
                optional=False
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                'save_runout',
                'Save Runout Layer',
                defaultValue=True,
                optional=False
            )
        )

        # Declared outputs returned by the algorithm
        self.addOutput(QgsProcessingOutputVectorLayer('Runout', 'Runout'))
        self.addOutput(QgsProcessingOutputVectorLayer('RiskAssessment', 'Risk Assessment'))
        self.addOutput(QgsProcessingOutputVectorLayer('Landcover', 'LandCover'))
        self.addOutput(QgsProcessingOutputString('OutputFolder', 'Timestamp output folder'))
        self.addOutput(QgsProcessingOutputHtml('InteractiveRiskDashboard', 'Interactive Risk Dashboard'))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Multi-step feedback
        feedback = QgsProcessingMultiStepFeedback(25, model_feedback)
        results = {}
        outputs = {}

        # --- PLUGIN PATHS & PARAMETERS ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        input_dir = os.path.join(base_dir, "Input")
        templates_dir = os.path.join(base_dir, "Templates")
        styles_dir = os.path.join(base_dir, "Styles")

        output_root = self.parameterAsString(parameters, 'output_folder', context)
        output_root = self._validate_output_folder(output_root, feedback)

        # Timestamped subfolder for this run
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_subdir = os.path.join(output_root, f"QRADE_Result_{timestamp}")
        try:
            output_paths = self._create_output_structure(output_subdir)
        except KeyError as e:
            raise QgsProcessingException(f'Internal QRADE output path-map key is missing: {e}')
        except Exception as e:
            raise QgsProcessingException(f'Could not create timestamped output folder: {output_subdir}\n{e}')

        save_landcover = self.parameterAsBool(parameters, 'save_landcover', context)
        save_riskassessment = self.parameterAsBool(parameters, 'save_riskassessment', context)
        save_runout = self.parameterAsBool(parameters, 'save_runout', context)

        if not any([save_landcover, save_riskassessment, save_runout]):
            raise QgsProcessingException('Please select at least one output to save: LandCover, Risk Assessment, or Runout.')

        feedback.pushInfo(f'Results will be saved in: {output_subdir}')

        # Style files
        runout_style_path = os.path.join(styles_dir, "Runout.qml")
        landcover_style_path = os.path.join(styles_dir, "Classification2.qml")
        risk_style_path = os.path.join(styles_dir, "RiskAssessment.qml")

        # Output file paths (inside timestamped folder)
        runout_path = output_paths['runout_gpkg']
        landcover_path = output_paths['landcover_gpkg']
        risk_path = output_paths['risk_assessment_gpkg']

        runout_output = runout_path if save_runout else QgsProcessing.TEMPORARY_OUTPUT
        landcover_output = landcover_path if save_landcover else QgsProcessing.TEMPORARY_OUTPUT
        risk_output = risk_path if save_riskassessment else QgsProcessing.TEMPORARY_OUTPUT

        # Parameters
        area_type_index = self.parameterAsInt(parameters, 'area_type', context)
        # Temporal probability (computed based on selected mode)
        temporal_mode = self.parameterAsInt(parameters, 'temporal_mode', context)  # 0,1,2
        temporal_manual_probability = None
        temporal_event_count = None
        temporal_observation_years = None
        temporal_assessment_years = None

        if temporal_mode == 1:
            temporal_event_count = self.parameterAsDouble(parameters, 'number_of_events', context)
            temporal_observation_years = self.parameterAsDouble(parameters, 'time_span_years', context)
            temporal_assessment_years = self.parameterAsDouble(parameters, 'return_period_years', context)
        elif temporal_mode == 2:
            temporal_manual_probability = self.parameterAsDouble(parameters, 'temporal_probability_manual', context)

        temporal_prob, temporal_diagnostics = self._evaluate_temporal_probability(
            temporal_mode,
            temporal_manual_probability,
            temporal_event_count,
            temporal_observation_years,
            temporal_assessment_years,
            feedback
        )

        # Classification table selection (Auto / Manual)
        risk_mode = self.parameterAsInt(parameters, 'risk_value_mode', context)  # 0=Auto, 1=Manual
        auto_table_path = os.path.join(input_dir, "classification_table.csv")
        manual_table_path = self.parameterAsFile(parameters, 'classification_table_manual', context)

        if risk_mode == 0:
            class_table_path = auto_table_path
        else:
            if not manual_table_path:
                raise QgsProcessingException(
                    'Manual risk-value table mode is selected. First open the Smart Assistant, '
                    'edit risk assessment values, save a custom CSV, then choose that CSV file path here.'
                )
            class_table_path = manual_table_path

        classification_table_values = self._validate_classification_table(class_table_path)
        risk_value_table_source_path = class_table_path
        risk_value_table_copied_to = None
        risk_value_table_copied_relative_path = None
        if risk_mode == 1:
            risk_value_table_copied_to, risk_value_table_copied_relative_path = self._copy_used_risk_value_table(
                class_table_path,
                output_paths,
                timestamp,
                feedback
            )

        # Landcover source selection (Auto / Manual)
        landcover_source = self.parameterAsInt(parameters, 'landcover_source', context)  # 0=Auto (OSM), 1=Manual
        mean_energy_layer = self.parameterAsRasterLayer(parameters, 'mean_energy', context)
        self._validate_crs_assumptions(mean_energy_layer, landcover_source, feedback)
        manual_landcover_path = self.parameterAsFile(parameters, 'landcover_manual', context)
        # -----------------------------
        # 1. RUNOUT (from Mean Energy raster)
        # -----------------------------
        feedback.pushInfo("Creating runout layer from Mean Energy raster...")

        # Polygonize (raster to vector)
        alg_params = {
            'BAND': 1,
            'EIGHT_CONNECTEDNESS': False,
            'EXTRA': None,
            'FIELD': 'DN',
            'INPUT': parameters['mean_energy'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PolygonizeRasterToVector'] = processing.run(
            'gdal:polygonize',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Dissolve (Runout)
        alg_params = {
            'FIELD': [''],
            'INPUT': outputs['PolygonizeRasterToVector']['OUTPUT'],
            'SEPARATE_DISJOINT': False,
            'OUTPUT': runout_output
        }
        outputs['Dissolve'] = processing.run(
            'native:dissolve',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Optional set style on the intermediate runout layer (not strictly needed now)
        alg_params = {
            'INPUT': outputs['Dissolve']['OUTPUT'],
            'STYLE': runout_style_path
        }
        processing.run(
            'native:setlayerstyle',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        # -----------------------------
        # 2. LANDCOVER (Auto from OSM OR Manual user-defined)
        # -----------------------------
        if landcover_source == 0:
            # -----------------------------
            # 2A) AUTO LANDCOVER FROM OSM
            # -----------------------------
            feedback.pushInfo("Landcover source: Auto (generated from OSM)")

            # OSM QUERY
            alg_params = {
                'AREA': None,
                'EXTENT': parameters['extent'],
                'QUERY': '[out:xml] [timeout:600];\n(\n    way["building"]( {{bbox}});\n    relation["building"]( {{bbox}});\n    way["landuse"="farmyard"]( {{bbox}});\n    way["landuse"="farmland"]( {{bbox}});\n    way["landuse"="farm"]( {{bbox}});\n    way["landuse"="meadow"]( {{bbox}});\n    way["landuse"="orchard"]( {{bbox}});\n    way["landuse"="vineyard"]( {{bbox}});\n    way["crop"="grape"]( {{bbox}});\n    way["landuse"="greenhouse_horticulture"]( {{bbox}});\n    way["landuse"="plant_nursery"]( {{bbox}});\n    way["landuse"="flowerbed"]( {{bbox}});\n    way["leisure"="garden"]( {{bbox}});\n    way["landuse"="grass"]( {{bbox}});\n    way["landuse"="village_green"]( {{bbox}});\n    way["leisure"="common"]( {{bbox}});\n    way["leisure"="park"]( {{bbox}});\n    way["landuse"="recreation_ground"]( {{bbox}});\n    way["landuse"="cemetery"]( {{bbox}});\n    way["landuse"="garages"]( {{bbox}});\n    way["landuse"="military"]( {{bbox}});\n    way["landuse"="greenfield"]( {{bbox}});\n    way["landuse"="quarry"]( {{bbox}});\n    relation["landuse"="farmyard"]( {{bbox}});\n    relation["landuse"="farmland"]( {{bbox}});\n    relation["landuse"="farm"]( {{bbox}});\n    relation["landuse"="meadow"]( {{bbox}});\n    relation["landuse"="orchard"]( {{bbox}});\n    relation["landuse"="vineyard"]( {{bbox}});\n    relation["crop"="grape"]( {{bbox}});\n    relation["landuse"="greenhouse_horticulture"]( {{bbox}});\n    relation["landuse"="plant_nursery"]( {{bbox}});\n    relation["landuse"="flowerbed"]( {{bbox}});\n    relation["leisure"="garden"]( {{bbox}});\n    relation["landuse"="grass"]( {{bbox}});\n    relation["landuse"="village_green"]( {{bbox}});\n    relation["leisure"="common"]( {{bbox}});\n    relation["leisure"="park"]( {{bbox}});\n    relation["landuse"="recreation_ground"]( {{bbox}});\n    relation["landuse"="cemetery"]( {{bbox}});\n    relation["landuse"="garages"]( {{bbox}});\n    relation["landuse"="military"]( {{bbox}});\n    relation["landuse"="greenfield"]( {{bbox}});\n    way["sport"]["amenity"="parking"]( {{bbox}});\n    relation["landuse"="quarry"]( {{bbox}});\n    way["amenity"="parking"]( {{bbox}});\n    relation["amenity"="parking"]( {{bbox}});\n    way["sport"]( {{bbox}});\n    relation["sport"]( {{bbox}});\n    way["leisure"="pitch"]( {{bbox}});\n    way["leisure"="sports_centre"]( {{bbox}});\n    way["leisure"="stadium"]( {{bbox}});\n    relation["leisure"="pitch"]( {{bbox}});\n    relation["leisure"="sports_centre"]( {{bbox}});\n    relation["leisure"="stadium"]( {{bbox}});\n    way["highway"]( {{bbox}});\n    way["railway"]( {{bbox}});\n    relation["highway"]( {{bbox}});\n    relation["railway"]( {{bbox}});\n);\n(._;>;);\nout body;',
                'SERVER': 'https://overpass-api.de/api/interpreter',
                'TIMEOUT': 600
            }
            outputs['BuildRawQuery'] = processing.run(
                'quickosm:buildrawquery',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(3)
            if feedback.isCanceled():
                return {}

            # Download file via HTTP(S)
            alg_params = {
                'DATA': None,
                'METHOD': 0,  # GET
                'URL': outputs['BuildRawQuery']['OUTPUT_URL'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }

            # -----------------------------
            # OSM DOWNLOAD WITH RETRY LOGIC
            # -----------------------------
            max_retries = 10
            attempt = 0
            download_success = False

            while attempt < max_retries and not download_success:
                try:
                    attempt += 1
                    feedback.pushInfo(f"Downloading OSM data (attempt {attempt}/{max_retries})...")

                    outputs['DownloadFileViaHttps'] = processing.run(
                        'native:filedownloader',
                        alg_params,
                        context=context,
                        feedback=feedback,
                        is_child_algorithm=True
                    )

                    download_success = True
                    feedback.pushInfo("OSM download completed successfully.")

                except Exception:
                    feedback.pushWarning(
                        f"OSM Overpass server overloaded (504). Retrying ({attempt}/{max_retries})...\n"
                        "Tip: reduce extent size or run later."
                    )

                    if attempt >= max_retries:
                        raise QgsProcessingException(
                            "OSM download failed after multiple retries. "
                            "Tip: reduce extent size or run later."
                        )

            feedback.setCurrentStep(4)
            if feedback.isCanceled():
                return {}

            # Open sublayers from an OSM file
            alg_params = {
                'FILE': outputs['DownloadFileViaHttps']['OUTPUT'],
                'OSM_CONF': None
            }
            outputs['OpenSublayersFromAnOsmFile'] = processing.run(
                'quickosm:openosmfile',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(5)
            if feedback.isCanceled():
                return {}

            # Reproject multipolygons layer
            alg_params = {
                'CONVERT_CURVED_GEOMETRIES': False,
                'INPUT': outputs['OpenSublayersFromAnOsmFile']['OUTPUT_MULTIPOLYGONS'],
                'OPERATION': None,
                'TARGET_CRS': 'ProjectCrs',
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['ReprojectMultipolygonsLayer'] = processing.run(
                'native:reprojectlayer',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(6)
            if feedback.isCanceled():
                return {}

            # -----------------------------
            # 2A.1) ROADS / RAILWAYS, MERGE, CLASSIFICATION
            # -----------------------------
            feedback.setCurrentStep(7)
            if feedback.isCanceled():
                return {}

            # Explode lines
            alg_params = {
                'INPUT': outputs['OpenSublayersFromAnOsmFile']['OUTPUT_LINES'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['ExplodeLines'] = processing.run(
                'native:explodelines',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(8)
            if feedback.isCanceled():
                return {}

            # Reproject exploded line layer
            alg_params = {
                'CONVERT_CURVED_GEOMETRIES': False,
                'INPUT': outputs['ExplodeLines']['OUTPUT'],
                'OPERATION': None,
                'TARGET_CRS': 'ProjectCrs',
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['ReprojectExplodedLineLayer'] = processing.run(
                'native:reprojectlayer',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(9)
            if feedback.isCanceled():
                return {}

            # Buffer (roads/railways)
            alg_params = {
                'DISSOLVE': False,
                'DISTANCE': 2,
                'END_CAP_STYLE': 0,  # Round
                'INPUT': outputs['ReprojectExplodedLineLayer']['OUTPUT'],
                'JOIN_STYLE': 0,  # Round
                'MITER_LIMIT': 2,
                'SEGMENTS': 3,
                'SEPARATE_DISJOINT': False,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['Buffer'] = processing.run(
                'native:buffer',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(10)
            if feedback.isCanceled():
                return {}

            # Join attributes by location (roads vs runout)
            alg_params = {
                'DISCARD_NONMATCHING': False,
                'INPUT': outputs['Buffer']['OUTPUT'],
                'JOIN': outputs['Dissolve']['OUTPUT'],
                'JOIN_FIELDS': ['fid'],
                'METHOD': 1,
                'PREDICATE': [0, 3],
                'PREFIX': 'jr_',
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['JoinAttributesByLocationForRoads'] = processing.run(
                'native:joinattributesbylocation',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(11)
            if feedback.isCanceled():
                return {}

            # Dissolve buffered roads by OSM id and runout flag
            alg_params = {
                'FIELD': ['osm_id', 'jr_fid'],
                'INPUT': outputs['JoinAttributesByLocationForRoads']['OUTPUT'],
                'SEPARATE_DISJOINT': False,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['DissolveRoads'] = processing.run(
                'native:dissolve',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(12)
            if feedback.isCanceled():
                return {}

            # Merge vector layers (dissolved roads + multipolygons)
            alg_params = {
                'CRS': 'ProjectCrs',
                'LAYERS': [
                    outputs['DissolveRoads']['OUTPUT'],
                    outputs['ReprojectMultipolygonsLayer']['OUTPUT']
                ],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['MergeVectorLayers'] = processing.run(
                'native:mergevectorlayers',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            feedback.setCurrentStep(13)
            if feedback.isCanceled():
                return {}

            # Field calculator for Classification (Landcover)
            alg_params = {
                'FIELD_LENGTH': 0,
                'FIELD_NAME': 'classification',
                'FIELD_PRECISION': 0,
                'FIELD_TYPE': 2,
                'FORMULA': 'CASE\r\n\r\n  -- 1) BUILDINGS (detailed subclasses)\r\n  WHEN "building" IS NOT NULL AND trim("building") <> \'\' THEN\r\n    CASE\r\n      -- normalize helpers\r\n      WHEN lower(coalesce("building", \'\')) IN (\'house\',\'detached\',\'residential\',\'semidetached_house\',\'terrace\')\r\n        THEN \'House\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'apartments\',\'residential_apartment\',\'residential_block\',\'dormitory\')\r\n        THEN \'Residential apartment building\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'retail\',\'commercial\',\'supermarket\',\'kiosk\',\'mall\')\r\n        THEN \'Commercial / Retail\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'industrial\',\'warehouse\',\'factory\',\'manufacture\',\'workshop\')\r\n        THEN \'Industrial building/ Manufacturing\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'office\')\r\n        THEN \'Offices / Business centers\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'hotel\',\'hostel\',\'guest_house\',\'motel\',\'alpine_hut\')\r\n        THEN \'Accommodation / Tourism\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'basilica\',\'cathedral\',\'chapel\',\'church\',\'mosque\',\'synagogue\',\'temple\',\'wayside_shrine\')\r\n        THEN \'Religious / Cultural heritage\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'school\',\'kindergarten\',\'university\',\'college\')\r\n        THEN \'Education facilities\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'hospital\',\'clinic\',\'doctors\')\r\n        THEN \'Health facilities\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'townhall\',\'civic\',\'public\',\'government\')\r\n        THEN \'Public administration / Government\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'police\',\'fire_station\',\'post_office\',\'library\',\'community_centre\',\'social_facility\')\r\n        THEN \'Community & public services\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'transformer_tower\',\'service\',\'utility\',\'power\',\'substation\',\'water_tower\')\r\n        THEN \'Energy / Utility building\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'parking\',\'multi-storey\',\'multistorey\')\r\n        THEN \'Parking Building\'\r\n      WHEN lower(coalesce("building", \'\')) IN (\'ruins\',\'ruin\')\r\n        THEN \'Ruin\'\r\n\r\n      -- building = yes → infer from other keys\r\n      WHEN lower(coalesce("building",\'\')) = \'yes\' THEN\r\n        CASE\r\n          WHEN lower(coalesce("amenity",\'\')) IN (\'townhall\',\'embassy\',\'courthouse\',\'public_building\',\'government\')\r\n            THEN \'Public administration / Government\'\r\n          WHEN lower(coalesce("amenity",\'\')) IN (\'school\',\'kindergarten\',\'college\',\'university\')\r\n            THEN \'Education facilities\'\r\n          WHEN lower(coalesce("amenity",\'\')) IN (\'hospital\',\'clinic\',\'doctors\')\r\n            THEN \'Health facilities\'\r\n          WHEN lower(coalesce("amenity",\'\')) = \'place_of_worship\'\r\n            THEN \'Religious / Cultural heritage\'\r\n          WHEN lower(coalesce("amenity",\'\')) IN (\'police\',\'fire_station\',\'post_office\',\'library\',\'community_centre\',\'social_facility\')\r\n            THEN \'Community & public services\'\r\n          WHEN lower(coalesce("amenity",\'\')) = \'parking\'\r\n            THEN \'Parking Building\'\r\n          WHEN trim(coalesce("office",\'\')) <> \'\'\r\n            THEN \'Offices / Business centers\'\r\n          WHEN trim(coalesce("shop",\'\')) <> \'\'\r\n            THEN \'Commercial / Retail\'\r\n          WHEN lower(coalesce("tourism",\'\')) IN (\'hotel\',\'guest_house\',\'hostel\',\'motel\',\'alpine_hut\')\r\n            THEN \'Accommodation / Tourism\'\r\n          WHEN lower(coalesce("man_made",\'\')) IN (\'water_tower\',\'gasometer\',\'storage_tank\',\'substation\',\'works\',\'communications_tower\',\'tower\')\r\n            THEN \'Energy / Utility building\'\r\n          ELSE \'House\'\r\n        END\r\n\r\n      -- any other non-empty building value\r\n      ELSE \'Mixed-use buildings\'\r\n    END\r\n\r\n\r\n  -- 2) Railway\r\n  WHEN "railway" IS NOT NULL AND trim("railway") <> \'\'\r\n  THEN \'Railway\'\r\n\r\n  -- 3) Paved road (surface tag)\r\n  WHEN lower("highway") IS NOT NULL\r\n       AND lower(coalesce("other_tags","")) LIKE \'%"surface"=>"asphalt"%\'\r\n  THEN \'Paved road\'\r\n\r\n  -- 4) Primary Road (treated as Paved road)\r\n  WHEN lower("highway") IS NOT NULL\r\n       AND lower("highway") NOT IN (\r\n         \'track\',\'steps\',\'service\',\'residential\',\'pedestrian\',\'path\',\'footway\',\'cycleway\'\r\n       )\r\n  THEN \'Paved road\'\r\n\r\n  -- 5) Dirt Road (treated as Unpaved road)\r\n  WHEN lower("highway") IN (\r\n         \'track\',\'steps\',\'service\',\'residential\',\'pedestrian\',\'path\',\'footway\',\'cycleway\'\r\n       )\r\n  THEN \'Unpaved road\'\r\n\r\n  -- 5) Parking\r\n  WHEN  lower("amenity") = \'parking\'\r\n     OR lower(coalesce("parking","")) IN (\'surface\',\'multi-storey\',\'multistorey\',\'underground\',\'park_and_ride\',\'layby\')\r\n     OR lower("landuse") = \'garages\'\r\n  THEN \'Parking area\'\r\n\r\n  -- 6) Productive agriculture\r\n  WHEN  lower("landuse") IN (\r\n          \'farmland\',\'orchard\',\'vineyard\',\r\n          \'greenhouse_horticulture\',\'plant_nursery\',\r\n          \'flowerbed\'\r\n        )\r\n     OR trim(coalesce(lower("crop"),\'\')) <> \'\'\r\n     OR trim(coalesce(lower("produce"),\'\')) <> \'\'\r\n  THEN \'Productive agriculture\'\r\n\r\n-- 6.1) Grassland and meadows\r\n  WHEN lower("landuse") IN (\'meadow\',\'grass\')\r\n  THEN \'Grassland and meadows\'\r\n\r\n-- 7) Livestock / Farm buildings\r\n  WHEN  lower("landuse") = \'farmyard\'\r\n     OR lower("building") IN (\'barn\',\'cowshed\',\'stable\',\'sty\',\'farm_auxiliary\',\'agricultural\',\'slurry_tank\',\'farm\')\r\n     OR lower("man_made") IN (\'cowshed\',\'stable\')\r\n  THEN \'Livestock / Farm buildings\'\r\n\r\n  -- 8) Recreation / Gathering areas\r\n  WHEN  lower("leisure") IN (\'park\',\'garden\',\'common\',\'recreation_ground\',\'pitch\',\'stadium\',\'playground\')\r\n     OR lower("landuse") IN (\'village_green\',\'recreation_ground\')\r\n     OR lower("amenity") IN (\'community_centre\',\'arts_centre\')\r\n  THEN \'Recreation / Gathering areas\'\r\n\r\n  ELSE \'Other\'\r\nEND\r\n',
                'INPUT': outputs['MergeVectorLayers']['OUTPUT'],
                'OUTPUT': landcover_output
            }
            outputs['FieldCalculatorForClassification'] = processing.run(
                'native:fieldcalculator',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            # Optional set style for intermediate landcover layer
            alg_params = {
                'INPUT': outputs['FieldCalculatorForClassification']['OUTPUT'],
                'STYLE': landcover_style_path
            }
            processing.run(
                'native:setlayerstyle',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

        else:
            # -----------------------------
            # 2B) MANUAL LANDCOVER (USER-DEFINED)
            # -----------------------------
            feedback.pushInfo("Landcover source: Manual (user-defined landcover layer)")

            if not manual_landcover_path:
                raise QgsProcessingException(
                    "Manual land-cover mode requires a valid vector layer/GeoPackage with a lowercase 'classification' field. "
                    "Please select a land-cover file."
                )

            if not os.path.exists(manual_landcover_path):
                raise QgsProcessingException(
                    "Manual land-cover mode requires a valid vector layer/GeoPackage with a lowercase 'classification' field.\n"
                    f"Selected path does not exist: {manual_landcover_path}"
                )

            # Load the layer to validate fields (expects the first layer in the GPKG if a layer name is not specified)
            manual_layer = QgsVectorLayer(manual_landcover_path, "ManualLandcover", "ogr")
            if not manual_layer.isValid():
                raise QgsProcessingException(
                    "Manual landcover layer is not a valid vector layer. "
                    "Please provide a valid GeoPackage layer."
                )

            field_names = [f.name() for f in manual_layer.fields()]
            if 'classification' not in field_names:
                raise QgsProcessingException(
                    "Manual landcover layer is missing the required field: 'classification'.\n"
                    "Please edit the template GeoPackage and keep the 'classification' column (string)."
                )

            # Reproject manual landcover to Project CRS and write it to the timestamped output folder
            alg_params = {
                'CONVERT_CURVED_GEOMETRIES': False,
                'INPUT': manual_landcover_path,
                'OPERATION': None,
                'TARGET_CRS': 'ProjectCrs',
                'OUTPUT': landcover_output
            }
            outputs['FieldCalculatorForClassification'] = processing.run(
                'native:reprojectlayer',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )

            # Optional set style for intermediate landcover layer
            alg_params = {
                'INPUT': landcover_path,
                'STYLE': landcover_style_path
            }
            processing.run(
                'native:setlayerstyle',
                alg_params,
                context=context,
                feedback=feedback,
                is_child_algorithm=True
            )
        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # Zonal statistics
        alg_params = {
            'COLUMN_PREFIX': 'energy_',
            'INPUT': outputs['FieldCalculatorForClassification']['OUTPUT'],
            'INPUT_RASTER': parameters['mean_energy'],
            'RASTER_BAND': 1,
            'STATISTICS': [6],  # Maximum
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ZonalStatistics'] = processing.run(
            'native:zonalstatisticsfb',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}

        # Optional set style for intermediate landcover layer
        alg_params = {
            'INPUT': outputs['FieldCalculatorForClassification']['OUTPUT'],
            'STYLE': landcover_style_path
        }
        processing.run(
            'native:setlayerstyle',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        self._validate_landcover_classification_values(
            outputs['ZonalStatistics']['OUTPUT'],
            context,
            classification_table_values
        )

        # -----------------------------
        # 3. JOIN CLASSIFICATION TABLE
        # -----------------------------
        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}

        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'classification',
            'FIELDS_TO_COPY': [''],
            'FIELD_2': 'classification',
            'INPUT': outputs['ZonalStatistics']['OUTPUT'],
            'INPUT_2': class_table_path,
            'METHOD': 1,
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByFieldValue'] = processing.run(
            'native:joinattributestable',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        # -----------------------------
        # 4. VULNERABILITY (PHY/SOC)
        # -----------------------------
        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}

        # Physical vulnerability expression
        if area_type_index == 0:
            v_phy_formula = (
                'CASE\n'
                '  WHEN "energy_max" IS NULL THEN 0\n'
                '  WHEN "energy_max"/1000 < 50  THEN "phy_vul_sub_kj_lt50"\n'
                '  WHEN "energy_max"/1000 < 150 THEN "phy_vul_sub_kj_50_150"\n'
                '  WHEN "energy_max"/1000 < 250 THEN "phy_vul_sub_kj_150_250"\n'
                '  WHEN "energy_max"/1000 < 400 THEN "phy_vul_sub_kj_250_400"\n'
                '  WHEN \"energy_max\"/1000 < 550 THEN \"phy_vul_sub_kj_400_550\"\n'
            '  ELSE \"phy_vul_sub_kj_gt550\"\n'
                'END\n'
            )
        else:
            v_phy_formula = (
                'CASE\n'
                '  WHEN "energy_max" IS NULL THEN 0\n'
                '  WHEN "energy_max"/1000 < 50  THEN "phy_vul_urb_kj_lt50"\n'
                '  WHEN "energy_max"/1000 < 150 THEN "phy_vul_urb_kj_50_150"\n'
                '  WHEN "energy_max"/1000 < 250 THEN "phy_vul_urb_kj_150_250"\n'
                '  WHEN "energy_max"/1000 < 400 THEN "phy_vul_urb_kj_250_400"\n'
                '  WHEN \"energy_max\"/1000 < 550 THEN \"phy_vul_urb_kj_400_550\"\n'
            '  ELSE \"phy_vul_urb_kj_gt550\"\n'
                'END\n'
            )

        alg_params = {
            'FIELD_LENGTH': 4,
            'FIELD_NAME': 'vulnerability_physical',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': v_phy_formula,
            'INPUT': outputs['JoinAttributesByFieldValue']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['V_phyFieldCalculator'] = processing.run(
            'native:fieldcalculator',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # Social vulnerability expression
        if area_type_index == 0:
            v_soc_formula = (
                'CASE\n'
                '  WHEN "energy_max" IS NULL THEN 0\n'
                '  WHEN "energy_max"/1000 < 50  THEN "soc_vul_sub_kj_lt50"\n'
                '  WHEN "energy_max"/1000 < 150 THEN "soc_vul_sub_kj_50_150"\n'
                '  WHEN "energy_max"/1000 < 250 THEN "soc_vul_sub_kj_150_250"\n'
                '  WHEN "energy_max"/1000 < 400 THEN "soc_vul_sub_kj_250_400"\n'
                '  WHEN \"energy_max\"/1000 < 550 THEN \"soc_vul_sub_kj_400_550\"\n'
            '  ELSE \"soc_vul_sub_kj_gt550\"\n'
                'END\n'
            )
        else:
            v_soc_formula = (
                'CASE\n'
                '  WHEN "energy_max" IS NULL THEN 0\n'
                '  WHEN "energy_max"/1000 < 50  THEN "soc_vul_urb_kj_lt50"\n'
                '  WHEN "energy_max"/1000 < 150 THEN "soc_vul_urb_kj_50_150"\n'
                '  WHEN "energy_max"/1000 < 250 THEN "soc_vul_urb_kj_150_250"\n'
                '  WHEN "energy_max"/1000 < 400 THEN "soc_vul_urb_kj_250_400"\n'
                '  WHEN \"energy_max\"/1000 < 550 THEN \"soc_vul_urb_kj_400_550\"\n'
            '  ELSE \"soc_vul_urb_kj_gt550\"\n'
                'END\n'
            )

        alg_params = {
            'FIELD_LENGTH': 4,
            'FIELD_NAME': 'vulnerability_social',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': v_soc_formula,
            'INPUT': outputs['V_phyFieldCalculator']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['V_socFieldCalculator'] = processing.run(
            'native:fieldcalculator',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        # Temporal probability (constant attribute)
        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        alg_params = {
            'FIELD_LENGTH': 4,
            'FIELD_NAME': 'temporal_probability',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': str(round(temporal_prob, 2)),
            'INPUT': outputs['V_socFieldCalculator']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['TemporalProbFieldCalculator'] = processing.run(
            'native:fieldcalculator',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        # -----------------------------
        # 5. RISK (PHY/SOC/TOT)
        # -----------------------------
        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        r_phy_formula = (
            '"exposure_physical" * '
            '"worth_physical" * '
            '"vulnerability_physical" * ' +
            str(temporal_prob)
        )
        alg_params = {
            'FIELD_LENGTH': 4,
            'FIELD_NAME': 'risk_physical',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': r_phy_formula,
            'INPUT': outputs['TemporalProbFieldCalculator']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['R_phyFieldCalculator'] = processing.run(
            'native:fieldcalculator',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        r_soc_formula = (
            '"exposure_social" * '
            '"worth_social" * '
            '"vulnerability_social" * ' +
            str(temporal_prob)
        )
        alg_params = {
            'FIELD_LENGTH': 4,
            'FIELD_NAME': 'risk_social',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': r_soc_formula,
            'INPUT': outputs['R_phyFieldCalculator']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['R_socFieldCalculator'] = processing.run(
            'native:fieldcalculator',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        alg_params = {
            'FIELD_LENGTH': 4,
            'FIELD_NAME': 'risk_total',
            'FIELD_PRECISION': 2,
            'FIELD_TYPE': 0,
            'FORMULA': '("risk_physical" + "risk_social") / 2',
            'INPUT': outputs['R_socFieldCalculator']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['R_totFieldCalculator'] = processing.run(
            'native:fieldcalculator',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )
        # Refactor fields (clean final Risk Assessment layer)
        fields_mapping = [
            {'expression': '"fid"', 'length': 0, 'name': 'fid', 'precision': 0, 'type': 4},
            {'expression': '"classification"', 'length': 0, 'name': 'classification', 'precision': 0, 'type': 10},
            {'expression': '"energy_max"', 'length': 10, 'name': 'energy_max', 'precision': 0, 'type': 6},
            {'expression': '"exposure_physical"', 'length': 10, 'name': 'exposure_physical', 'precision': 2, 'type': 6},
            {'expression': '"exposure_social"', 'length': 10, 'name': 'exposure_social', 'precision': 2, 'type': 6},
            {'expression': '"worth_physical"', 'length': 10, 'name': 'worth_physical', 'precision': 2, 'type': 6},
            {'expression': '"worth_social"', 'length': 10, 'name': 'worth_social', 'precision': 2, 'type': 6},
            {'expression': '"vulnerability_physical"', 'length': 4, 'name': 'vulnerability_physical', 'precision': 2, 'type': 6},
            {'expression': '"vulnerability_social"', 'length': 4, 'name': 'vulnerability_social', 'precision': 2, 'type': 6},
            {'expression': '"temporal_probability"', 'length': 4, 'name': 'temporal_probability', 'precision': 2, 'type': 6},
            {'expression': '"risk_physical"', 'length': 10, 'name': 'risk_physical', 'precision': 2, 'type': 6},
            {'expression': '"risk_social"', 'length': 10, 'name': 'risk_social', 'precision': 2, 'type': 6},
            {'expression': '"risk_total"', 'length': 10, 'name': 'risk_total', 'precision': 2, 'type': 6}
        ]

        alg_params = {
            'INPUT': outputs['R_totFieldCalculator']['OUTPUT'],
            'FIELDS_MAPPING': fields_mapping,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RefactorRiskAssessmentRaw'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        outputs['RefactorRiskAssessment'] = self._filter_risk_assessment_positive_energy(
            outputs['RefactorRiskAssessmentRaw']['OUTPUT'],
            risk_output,
            context,
            feedback
        )

        run_metadata = {
            'plugin_name': 'QRADE',
            'algorithm_id': 'qrade:qrade_risk_v3',
            'timestamp': timestamp,
            'run_folder': os.path.basename(output_subdir),
            'output_folder': output_subdir,
            'landcover_source_mode': 'Auto OSM' if landcover_source == 0 else 'Manual',
            'risk_value_mode': 'Default' if risk_mode == 0 else 'Manual',
            'risk_value_table_mode': 'Default' if risk_mode == 0 else 'Manual',
            'risk_value_table_source_path': risk_value_table_source_path,
            'risk_value_table_copied_to': risk_value_table_copied_to,
            'risk_value_table_copied_relative_path': risk_value_table_copied_relative_path,
            'area_type': 'Suburban masonry' if area_type_index == 0 else 'Urban reinforced concrete',
            'temporal_probability_mode': temporal_diagnostics.get('temporal_probability_mode'),
            'temporal_probability_value': temporal_prob,
            'temporal_lambda_per_year': temporal_diagnostics.get('temporal_lambda_per_year'),
            'temporal_expected_events': temporal_diagnostics.get('temporal_expected_events'),
            'temporal_equivalent_return_period_years': temporal_diagnostics.get('temporal_equivalent_return_period_years'),
            'temporal_probability_quality': temporal_diagnostics.get('temporal_probability_quality'),
            'temporal_probability_warnings': temporal_diagnostics.get('temporal_probability_warnings'),
            'project_crs_authid': QgsProject.instance().crs().authid(),
            'mean_energy_raster_source': mean_energy_layer.source() if mean_energy_layer is not None else None,
            'mean_energy_raster_crs_authid': mean_energy_layer.crs().authid() if mean_energy_layer is not None else None,
            'risk_assessment_energy_filter_applied': True,
            'risk_assessment_energy_filter_expression': outputs['RefactorRiskAssessment'].get('expression'),
            'risk_assessment_features_before_energy_filter': outputs['RefactorRiskAssessment'].get('original_count'),
            'risk_assessment_features_after_energy_filter': outputs['RefactorRiskAssessment'].get('filtered_count'),
            'risk_assessment_features_removed_no_energy': outputs['RefactorRiskAssessment'].get('removed_count'),
            'save_landcover': save_landcover,
            'save_riskassessment': save_riskassessment,
            'save_runout': save_runout,
        }
        risk_summary_layer = QgsProcessingUtils.mapLayerFromString(
            str(outputs['RefactorRiskAssessment']['OUTPUT']),
            context
        )
        summary_json_path, summary_csv_path = self._write_result_summary(
            risk_summary_layer or outputs['RefactorRiskAssessment']['OUTPUT'],
            output_paths,
            run_metadata,
            feedback
        )
        bim_csv_path, bim_json_path = self._write_bim_ready_export(
            risk_summary_layer or outputs['RefactorRiskAssessment']['OUTPUT'],
            output_paths,
            run_metadata,
            feedback
        )
        ifc_mapping_template_path = self._write_ifc_guid_mapping_template(
            risk_summary_layer or outputs['RefactorRiskAssessment']['OUTPUT'],
            output_paths,
            run_metadata,
            feedback
        )
        bcf_export_paths = self._write_bcf_issue_export(
            risk_summary_layer or outputs['RefactorRiskAssessment']['OUTPUT'],
            output_paths,
            run_metadata,
            feedback
        )
        web_data_dir = self._write_webgis_data_bundle(
            output_paths,
            {
                'risk_assessment': risk_summary_layer or outputs['RefactorRiskAssessment']['OUTPUT'],
                'landcover': outputs['FieldCalculatorForClassification']['OUTPUT'],
                'runout': outputs['Dissolve']['OUTPUT'],
            },
            {
                'summary_json': summary_json_path,
                'summary_csv': summary_csv_path,
            },
            {
                'bim_json': bim_json_path,
                'bim_csv': bim_csv_path,
            },
            context,
            feedback
        )
        web_index_path = self._write_webgis_index_html(output_paths, web_data_dir, feedback)
        self._write_qa_qc_report(
            output_paths,
            run_metadata,
            {
                'summary_json': summary_json_path,
                'summary_csv': summary_csv_path,
            },
            {
                'bim_json': bim_json_path,
                'bim_csv': bim_csv_path,
                'ifc_mapping_template': ifc_mapping_template_path,
                'bcf_zip': bcf_export_paths.get('bcf_zip'),
                'bcf_readme': bcf_export_paths.get('bcf_readme'),
                'bcf_issue_count': bcf_export_paths.get('bcf_issue_count'),
            },
            {
                'web_data_dir': web_data_dir,
                'index_html': web_index_path,
            },
            feedback
        )
        self._write_output_manifest(output_paths, run_metadata, feedback)

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # Optional intermediate style
        alg_params = {
            'INPUT': outputs['R_totFieldCalculator']['OUTPUT'],
            'STYLE': risk_style_path
        }
        processing.run(
            'native:setlayerstyle',
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True
        )

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}


        # -----------------------------
        # 6. ADD RESULT LAYERS TO QGIS WITH STYLES (timestamped names)
        # Load order requested by user: LandCover -> Risk Assessment -> Runout
        # -----------------------------
        results['OutputFolder'] = output_subdir

        if save_landcover:
            results['Landcover'] = landcover_path
            landcover_layer = QgsVectorLayer(landcover_path, f"LandCover ({timestamp})", "ogr")
            if landcover_layer.isValid():
                if os.path.exists(landcover_style_path):
                    landcover_layer.loadNamedStyle(landcover_style_path)
                    landcover_layer.triggerRepaint()
                QgsProject.instance().addMapLayer(landcover_layer)

        if save_riskassessment:
            results['RiskAssessment'] = risk_path
            risk_layer = QgsVectorLayer(risk_path, f"Risk Assessment ({timestamp})", "ogr")
            if risk_layer.isValid():
                if os.path.exists(risk_style_path):
                    risk_layer.loadNamedStyle(risk_style_path)
                    risk_layer.triggerRepaint()
                QgsProject.instance().addMapLayer(risk_layer)

        if save_runout:
            results['Runout'] = runout_path
            runout_layer = QgsVectorLayer(runout_path, f"Runout ({timestamp})", "ogr")
            if runout_layer.isValid():
                if os.path.exists(runout_style_path):
                    runout_layer.loadNamedStyle(runout_style_path)
                    runout_layer.triggerRepaint()
                QgsProject.instance().addMapLayer(runout_layer)

        # Ensure the progress bar reaches 100% after all post-processing steps
        # (layer loading and result assignment happen after the last child algorithm).
        try:
            feedback.setCurrentStep(25)
        except Exception:
            pass
        try:
            feedback.setProgress(100)
        except Exception:
            pass

        results['InteractiveRiskDashboard'] = web_index_path
        feedback.pushInfo(
            'QRADE completed successfully.\n'
            f'Result folder: {output_subdir}\n'
            f'Interactive Risk Dashboard: {web_index_path}\n'
            'Open the QRADE Smart Assistant to review the generated dashboard, QA/QC report, '
            'BIM deliverables, and BCF issues.'
        )

        return results

    def createCustomParametersWidget(self, parent=None):
        return QRADEAlgorithmDialog(self, parent=parent)

    def shortHelpString(self):
        """Return rich HTML help shown in the Processing dialog right-side help panel."""
        return """
<p>QRADE (Risk Assessment for Damage and Exposure) is a QGIS Processing algorithm for rockfall risk assessment. The risk calculation follows the IMIRILAND methodology for landslides in mountainous areas, which supports semi-quantitative and quantitative assessments depending on data availability. The method evaluates the main components of risk in a modular way, including hazard intensity and extent, exposure, vulnerability, temporal probability, and the value of the elements at risk (Bonnard et al., 2004; Castelli and Scavia, 2008; Scavia et al., 2020).</p>

<h3>NOTE:</h3>

<p>The QuickOSM plugin is required when using Auto land-cover generation from OpenStreetMap data.</p>

<p>For the rockfall hazard analysis and the generation of the kinetic-energy raster, the use of the QPROTO plugin is recommended. However, QRADE can also use kinetic-energy raster outputs produced by other rockfall hazard-analysis tools, provided that the raster is suitable for the assessment.</p>

<h3>Input:</h3>

<p>Land Cover Source: defines whether land-cover or exposed-element data are generated automatically from OpenStreetMap or provided manually as a local vector layer.</p>

<p>Extent: analysis area used for processing and, in Auto mode, for querying OpenStreetMap data.</p>

<p>Risk Assessment Values: default or custom CSV table containing the values used in the risk assessment.</p>

<p>Area Type and Buildings Typology: contextual setting used for the assessment of exposed elements and built-environment conditions.</p>

<p>Kinetic Energy raster (J): raster layer representing rockfall kinetic energy values.</p>

<p>Temporal Probability of Occurrence: temporal probability setting used in the risk calculation.</p>

<h3>Output:</h3>

<p>Runout layer: runout vector layer to identify elements at risk.</p>

<p>LandCover layer: classified land-cover layer used in the assessment.</p>

<p>Risk Assessment layer: final risk-assessment layer containing calculated risk attributes.</p>

<p>Summary files: JSON and CSV files describing the run settings, output paths, feature counts, and risk statistics.</p>

<p>Interactive Risk Dashboard: Web dashboard for reviewing risk-assessment, land-cover, and runout results including filtering and reporting tools.</p>

<p>QA/QC report: quality-control report summarizing generated outputs, diagnostics, warnings, and consistency checks.</p>

<p>BIM deliverables: BIM-ready CSV and JSON exports, IFC GUID mapping template, and BCF issue files for high-risk and critical features.</p>

<p>Output manifest: JSON file used by the QRADE Smart Assistant to identify and open generated deliverables.</p>

<h3>HELP:</h3>

<p>Documentation:<br>
<a href="https://github.com/sm-moeini/QRADE#readme">QRADE documentation</a><br>
<a href="https://github.com/sm-moeini/QRADE/tree/main/training_dataset">Example training dataset</a></p>

<p>Contact:<br>
Seyedmostafa Moeini: <a href="mailto:seyedmostafa.moeini@polito.it">seyedmostafa.moeini@polito.it</a><br>
Marta Castelli: <a href="mailto:marta.castelli@polito.it">marta.castelli@polito.it</a></p>
"""

    def helpUrl(self):
        """Optional: provide a URL for the help button."""
        help_path = os.path.join(os.path.dirname(__file__), "help", "qrade_help.html")
        return QUrl.fromLocalFile(help_path).toString()

    def name(self):
        return 'qrade_risk_v3'

    def displayName(self):
        return 'QRADE'

    def group(self):
        return 'Risk Assessment'

    def groupId(self):
        return 'risk_assessment'

    def createInstance(self):
        return QRADEAlgorithm()
