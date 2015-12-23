# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GetLinkData
                                 A QGIS plugin
 Retrieve data from LinkData.org
                             -------------------
        begin                : 2015-12-21
        copyright            : (C) 2015 by Midori IT Office, LLC
        email                : info@midoriit.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load GetLinkData class from file GetLinkData.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .get_link_data import GetLinkData
    return GetLinkData(iface)
