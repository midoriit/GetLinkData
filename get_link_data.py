# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GetLinkData
                                 A QGIS plugin
 Retrieve data from LinkData.org
                              -------------------
        begin                : 2015-12-21
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Midori IT Office, LLC
        email                : info@midoriit.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from get_link_data_dialog import GetLinkDataDialog
import os.path
# additional imports
from PyQt4.QtGui import QMessageBox, QDialogButtonBox
from PyQt4.QtCore import *
from qgis.core import *
from qgis.gui import *
import json, urllib, urllib2

class GetLinkData:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GetLinkData_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = GetLinkDataDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&GetLinkData')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'GetLinkData')
        self.toolbar.setObjectName(u'GetLinkData')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GetLinkData', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/GetLinkData/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Retrieve data from LinkData.org'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # Dialog box buttons
        self.dlg.selectButton.clicked.connect(self.setID)
        self.dlg.resetButton.clicked.connect(self.resetID)
        self.dlg.fileComboBox.currentIndexChanged.connect(self.changeFile)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&GetLinkData'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""

        # initialize
        lost_features = 0
        self.dlg.fileComboBox.clear()
        self.dlg.latComboBox.clear()
        self.dlg.lonComboBox.clear()
        self.dlg.labelComboBox.clear()
        self.dlg.idTextEdit.clear()
        self.dlg.idTextEdit.setEnabled(True)
        self.dlg.selectButton.setEnabled(True)
        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.dlg.infoText.setText(self.tr("Enter Dataset ID and click Select button"))
        self.dlg.infoText.setStyleSheet("color: black")
        self.dlg.latComboBox.setEnabled(True)
        self.dlg.lonComboBox.setEnabled(True)

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:

            id = self.dlg.idTextEdit.toPlainText()
            file = self.dlg.fileComboBox.currentText()
            num = self.dlg.fileComboBox.currentIndex()

            # check geometry
            latIdx = self.dlg.latComboBox.currentIndex()
            lonIdx = self.dlg.lonComboBox.currentIndex()
            if latIdx == 0 or lonIdx == 0:
              QMessageBox.critical(self.iface.mainWindow(), \
                self.tr("Error"), self.tr("No geometry"))
              return

            # RDF/JSON
            url2 = "http://linkdata.org/api/1/" + id + "/" + \
              urllib.quote(file.encode("utf-8")) + "_rdf.json"
            req2 = urllib2.Request(url2)
            try:
              rsp2 = urllib2.urlopen(req2)
            except urllib2.HTTPError, e:
              QMessageBox.critical(self.iface.mainWindow(), \
                self.tr("Error"), self.tr("Failed to read data"))
              return
            dat2 = json.loads(rsp2.read())

            # add layer
            newLayer = QgsVectorLayer("Point?crs=epsg:4326", file, "memory")
            newLayer.setProviderEncoding("UTF-8")
            QgsMapLayerRegistry.instance().addMapLayer(newLayer)
            newLayer.startEditing()

            # add attributes
            flds = self.dat1["resources"][num]["schema"]["fields"]
            for fld in flds:
              if "uri" in fld:
                newLayer.addAttribute(QgsField(fld["uri"], QVariant.String))
              else:
                newLayer.addAttribute(QgsField(fld["label"], QVariant.String))

            # label setting
            labelIdx = self.dlg.labelComboBox.currentIndex()
            if labelIdx > 0:
              newLayer.setCustomProperty("labeling", "pal")
              newLayer.setCustomProperty("labeling/enabled", "true")
              newLayer.setCustomProperty("labeling/fieldName", \
                self.dlg.labelComboBox.currentText())
              newLayer.setCustomProperty("labeling/fontSize", "10")

            # add features
            lat = self.dlg.latComboBox.currentText()
            lon = self.dlg.lonComboBox.currentText()

            if lat != "http://www.w3.org/2003/01/geo/wgs84_pos#lat":
              lat = "http://linkdata.org/property/" + id + "#" + urllib.quote(lat.encode("utf-8"))
            if lon != "http://www.w3.org/2003/01/geo/wgs84_pos#long":
              lon = "http://linkdata.org/property/" + id + "#" + urllib.quote(lon.encode("utf-8"))

            for k in dat2.iterkeys():
              if lat in dat2[k] and lon in dat2[k]:
                try:
                  flat = float(dat2[k][lat][0]["value"])
                  flon = float(dat2[k][lon][0]["value"])
                except:
                  lost_features = lost_features + 1;
                  continue
                feature = QgsFeature(newLayer.pendingFields())
                feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(flon, flat)))

                # set attributes (subject)
                feature.setAttribute(self.subject, unicode(k))

                # set attributes (objects)
                for fld in flds:
                  if "uri" in fld:
                    uri = fld["uri"]
                    if uri in dat2[k]:
                      feature.setAttribute(uri, unicode(dat2[k][uri][0]["value"]))
                  else:
                    uri = "http://linkdata.org/property/" + id + "#" + \
                      urllib.quote(fld["label"].encode("utf-8"))
                    if uri in dat2[k]:
                      feature.setAttribute(fld["label"], unicode(dat2[k][uri][0]["value"]))
                newLayer.addFeature(feature)
              else:
                lost_features = lost_features + 1;
            newLayer.commitChanges()
            newLayer.updateExtents()
            if lost_features > 0:
              QMessageBox.warning(self.iface.mainWindow(), self.tr("Warning"), \
                self.tr("Lost {:d} item(s) without geometry").format(lost_features) )

    def setID(self):

      id = self.dlg.idTextEdit.toPlainText()
      if not id:
        # nothing to do
        return

      # Tabular Data Package
      url1 = "http://linkdata.org/api/1/" + id + "/datapackage.json"
      req1 = urllib2.Request(url1)
      try:
        rsp1 = urllib2.urlopen(req1)
      except urllib2.HTTPError, e:
        self.dlg.infoText.setText(self.tr("Dataset unavailable"))
        self.dlg.infoText.setStyleSheet("color: red")
        self.dlg.idTextEdit.setEnabled(False)
        return

      # setup comboBox
      self.dat1 = json.loads(rsp1.read())
      file_list = []
      for rs in self.dat1["resources"]:
        if "url" in rs:
          # extract from CSV file URL
          csv = rs["url"]
          s = csv.find(id) + len(id) + 1
          file_list.append(urllib.unquote(csv[s:len(csv)-4]).encode("raw_unicode_escape").decode("utf-8"))
        else:
          self.dlg.infoText.setText(self.tr("Sorry, this dataset is not supported"))
          self.dlg.infoText.setStyleSheet("color: red")
          self.dlg.idTextEdit.setEnabled(False)
          return
      self.dlg.fileComboBox.blockSignals(True)
      self.dlg.fileComboBox.addItems(file_list)
      self.dlg.fileComboBox.blockSignals(False)
      self.dlg.selectButton.setEnabled(False)
      self.dlg.idTextEdit.setEnabled(False)
      self.changeFile()

    def resetID(self):

      self.dlg.selectButton.setEnabled(True)
      self.dlg.idTextEdit.clear()
      self.dlg.idTextEdit.setEnabled(True)
      self.dlg.fileComboBox.clear()
      self.dlg.latComboBox.clear()
      self.dlg.lonComboBox.clear()
      self.dlg.labelComboBox.clear()
      self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
      self.dlg.infoText.setText(self.tr("Enter Dataset ID and click Select button"))
      self.dlg.infoText.setStyleSheet("color: black")

    def changeFile(self):

      self.dlg.latComboBox.clear()
      self.dlg.lonComboBox.clear()
      self.dlg.labelComboBox.clear()
      self.dlg.latComboBox.setEnabled(True)
      self.dlg.lonComboBox.setEnabled(True)
      num = self.dlg.fileComboBox.currentIndex()

      # addItems to comboBoxes
      hasLat = False
      hasLon = False
      item_list = [""]
      flds = self.dat1["resources"][num]["schema"]["fields"]
      for fld in flds:
        if "uri" in fld:
          if fld["id"] == "0":
            self.subject = fld["uri"]
          else:
            item_list.append(fld["uri"])
        else:
          if fld["id"] == "0":
            self.subject = fld["label"]
          else:
            item_list.append(fld["label"])
      self.dlg.latComboBox.addItems(item_list)
      self.dlg.lonComboBox.addItems(item_list)
      self.dlg.labelComboBox.addItems(item_list)
      idx = self.dlg.latComboBox.findText("http://www.w3.org/2003/01/geo/wgs84_pos#lat")
      if idx > 0:
        hasLat = True
        self.dlg.latComboBox.setCurrentIndex(idx)
        self.dlg.latComboBox.setEnabled(False)
      idx = self.dlg.lonComboBox.findText("http://www.w3.org/2003/01/geo/wgs84_pos#long")
      if idx > 0:
        hasLon = True
        self.dlg.lonComboBox.setCurrentIndex(idx)
        self.dlg.lonComboBox.setEnabled(False)
      idx = self.dlg.labelComboBox.findText("http://www.w3.org/2000/01/rdf-schema#label")
      if idx > 0:
        self.dlg.labelComboBox.setCurrentIndex(idx)
      self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(True)

      if hasLat and hasLon:
        self.dlg.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        self.dlg.infoText.setText("")
      else:
        self.dlg.infoText.setText(self.tr("Select Latitude and/or Longitude"))
      