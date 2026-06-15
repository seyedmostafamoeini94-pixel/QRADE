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

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
import os

import processing  # QGIS Processing framework

from .qrade_provider import QRADEProvider
from .smart_assistant_dialog import QRADEAssistantDialog


class QRADEPlugin:
    def __init__(self, iface):
        """
        iface: QgisInterface instance, gives access to QGIS GUI.
        """
        self.iface = iface
        self.provider = None

        # UI (toolbar/menu)
        self.action_open = None
        self.action_assistant = None
        self.menu_name = "&QRADE"
        self.icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.assistant_icon_path = os.path.join(os.path.dirname(__file__), "smart_assistant_icon.png")
        self.assistant_dialog = None

    def _icon_from_paths(self, *paths):
        for path in paths:
            if path and os.path.exists(path):
                return QIcon(path)
        return QIcon()

    def initGui(self):
        """
        Called by QGIS when the plugin is loaded.
        We register our processing provider here.
        """
        registry = QgsApplication.processingRegistry()
        existing = registry.providerById('qrade')
        if existing is None:
            self.provider = QRADEProvider()
            registry.addProvider(self.provider)
        else:
            self.provider = existing

        # Add a toolbar icon to launch the algorithm dialog
        self._add_toolbar_action()

    def unload(self):
        """
        Called by QGIS when plugin is disabled/uninstalled.
        We remove our provider and UI actions here.
        """
        self._remove_toolbar_action()

        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    # ----------------------------
    # Toolbar/Menu action
    # ----------------------------
    def _add_toolbar_action(self):
        if self.action_open is not None and self.action_assistant is not None:
            return

        main_icon = self._icon_from_paths(self.icon_path)
        assistant_icon = self._icon_from_paths(self.assistant_icon_path, self.icon_path)

        if self.action_open is None:
            self.action_open = QAction(main_icon, QCoreApplication.translate("QRADE", "Open QRADE Risk Assessment"), self.iface.mainWindow())
            self.action_open.setToolTip(QCoreApplication.translate("QRADE", "Open QRADE Risk Assessment tool"))
            self.action_open.triggered.connect(self._open_algorithm_dialog)

            # Add to toolbar + plugin menu
            self.iface.addToolBarIcon(self.action_open)
            self.iface.addPluginToMenu(self.menu_name, self.action_open)

        if self.action_assistant is None:
            self.action_assistant = QAction(assistant_icon, QCoreApplication.translate("QRADE", "QRADE Smart Assistant"), self.iface.mainWindow())
            self.action_assistant.setToolTip(QCoreApplication.translate("QRADE", "Open QRADE Smart Assistant"))
            self.action_assistant.triggered.connect(self.open_smart_assistant)

            self.iface.addToolBarIcon(self.action_assistant)
            self.iface.addPluginToMenu(self.menu_name, self.action_assistant)

    def _remove_toolbar_action(self):
        if self.action_open is None and self.action_assistant is None:
            return

        if self.action_open is not None:
            try:
                self.iface.removeToolBarIcon(self.action_open)
            except Exception:
                pass

            try:
                self.iface.removePluginMenu(self.menu_name, self.action_open)
            except Exception:
                pass

            self.action_open = None

        if self.action_assistant is not None:
            try:
                self.iface.removeToolBarIcon(self.action_assistant)
            except Exception:
                pass

            try:
                self.iface.removePluginMenu(self.menu_name, self.action_assistant)
            except Exception:
                pass

            self.action_assistant = None

        self.assistant_dialog = None

    def _open_algorithm_dialog(self):
        """Open the Processing dialog for the QRADE algorithm."""
        alg_id = "qrade:qrade_risk_v3"

        # Open the Processing dialog
        try:
            processing.execAlgorithmDialog(alg_id, {})
        except Exception as e:
            # If the dialog cannot be opened, show a message to the user
            try:
                self.iface.messageBar().pushWarning("QRADE", f"Could not open tool: {e}")
            except Exception:
                pass

    def open_smart_assistant(self):
        """Open the standalone QRADE Smart Assistant dialog."""
        try:
            self.assistant_dialog = QRADEAssistantDialog(self.iface.mainWindow())
            self.assistant_dialog.setWindowIcon(self._icon_from_paths(self.assistant_icon_path, self.icon_path))
            self.assistant_dialog.show()
            self.assistant_dialog.raise_()
            self.assistant_dialog.activateWindow()
        except Exception as e:
            try:
                self.iface.messageBar().pushWarning("QRADE", f"Could not open Smart Assistant: {e}")
            except Exception:
                pass
