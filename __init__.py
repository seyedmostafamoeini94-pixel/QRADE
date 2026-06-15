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

from .qrade_plugin import QRADEPlugin


def classFactory(iface):
    """QGIS calls this to create the plugin instance."""
    return QRADEPlugin(iface)
