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
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
from .qrade_algorithm import QRADEAlgorithm


class QRADEProvider(QgsProcessingProvider):

    def loadAlgorithms(self, *args, **kwargs):
        """
        Called by QGIS to register algorithms.
        """
        self.addAlgorithm(QRADEAlgorithm())


    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        return QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    def id(self):
        """
        Provider ID (no spaces).
        """
        return "qrade"

    def name(self):
        """
        Human readable name shown in Processing Toolbox.
        """
        return "QRADE"

    def longName(self):
        return "QRADE - Rockfall Risk Assessment"
