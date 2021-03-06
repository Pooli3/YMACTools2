# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtXml import *   # For QDomDocument (to read map composer template)
from qgis.core import *
from qgis.gui import *
import qgis.utils

import xml.etree.ElementTree as ET
import os, shutil
from ..tools import Tools
from ..data.metadata.metadatatools import MetadataTools
from .datamenu import DataMenu
from datetime import datetime

from .datalocationsdialog import DataLocationsDialog
from .metadataviewerdialog import MetadataViewerDialog
from .metadataeditordialog import MetadataEditorDialog
from .selectcrsdialog import SelectCRSDialog
from .convertlayertocrsdialog import ConvertLayerToCRSDialog
from ..mapproduction.mapproduction import MapProduction, MapLabelDialog
from ..data.crs.crshelper import CRSHelper
from ..ui.aboutdialog import AboutDialog
from .zoomtolocationdialog import ZoomToLocationDialog

from ..data.requests.loadShapefile import LoadShapefile
from ..data.requests.loadImagery import LoadImagery

# from pydevd import*

##############################################################################


class DockableWindow():

    @staticmethod
    def getDockable(display=True):

        mw = qgis.utils.iface.mainWindow()
        dock = mw.findChild(QDockWidget, Tools.applicationName)
        if dock is not None:
            dock.setVisible(not dock.isVisible())
            return dock
        else:
            # dockable
            dock = QDockWidget(Tools.applicationName, mw)
            dock.setObjectName(Tools.applicationName)
            dock.dockLocationChanged.connect(DockableWindow.dockAreaChange)

            qgis.utils.iface.addDockWidget(Tools.getDockArea(), dock)
            dockCanvas = QWidget()
            dock.setWidget(dockCanvas)
            dockLayout = QVBoxLayout()
            dockCanvas.setLayout(dockLayout)
            dockLayout.setContentsMargins(0, 0, 0, 0)

            # toolbar
            topLayout = QBoxLayout(QBoxLayout.LeftToRight, dock)
            searchLayout = QBoxLayout(QBoxLayout.LeftToRight, dock)
            dockLayout.addLayout(topLayout)
            dockLayout.addLayout(searchLayout)
            toolbar = QToolBar(dock)
            topLayout.addWidget(toolbar)
            menubar = QMenuBar(toolbar)
            toolbar.addWidget(menubar)
            barLayout = QBoxLayout(QBoxLayout.LeftToRight, toolbar)
            menubar.setLayout(barLayout)


# TOOL MENU
            toolsMenu = QMenu("Tools", menubar)
            toolsMenu.setToolTip("Click for more tools")
            menubar.addMenu(toolsMenu)

    # Settings
            settingsMenu = QMenu("Settings", toolsMenu)
            toolsMenu.addMenu(settingsMenu)

            # data locations
            dl = settingsMenu.addAction("Data Locations")
            dl.triggered.connect(DockableWindow.dataLocations)

    # default project
            defaultProjectMenu = QMenu("Default Project", toolsMenu)
            defProject = settingsMenu.addMenu(defaultProjectMenu)

            disableLink = defaultProjectMenu.addAction("Disable use of Default Project")
            disableLink.triggered.connect(DockableWindow.disableDefaultProject)

            setCurrentLink = defaultProjectMenu.addAction("Set current project as the Default Project")
            setCurrentLink.triggered.connect(DockableWindow.setCurrentProjectAsDefault)

            restoreInitialLink = defaultProjectMenu.addAction("Reset")
            restoreInitialLink.triggered.connect(DockableWindow.setYMACProjectAsDefault)


    # coord ref systems
            coordinatesMenu = QMenu("Coordinate Systems", toolsMenu)
            coordinatesMenu.aboutToShow.connect(DockableWindow.showCoordinateSystemsMenu)
            toolsMenu.addMenu(coordinatesMenu)

            cltdcrs = coordinatesMenu.addAction("Convert Layer to Different Coordinate Reference System")
            DockableWindow.convertLayerToCoordinateSystemAction = cltdcrs
            cltdcrs.triggered.connect(DockableWindow.convertLayerToCoordinateSystem)

            coordinatesMenu.addSeparator()

            dlcs = coordinatesMenu.addAction("Define Layer Coordinate Reference System")
            DockableWindow.defineLayerCoordinateSystemAction = dlcs
            dlcs.triggered.connect(DockableWindow.defineLayerCoordinateSystem)

            dfcs = coordinatesMenu.addAction("Set Data Frame Coordinate Reference System")
            DockableWindow.defineFrameCoordinateSystemAction = dfcs
            dfcs.triggered.connect(DockableWindow.defineFrameCoordinateSystem)

    # metadata
            metadataMenu = QMenu("Metadata", toolsMenu)
            metadataMenu.aboutToShow.connect(DockableWindow.showMetadataMenu)
            toolsMenu.addMenu(metadataMenu)

            cmd = metadataMenu.addAction("Create Metadata")
            cmd.triggered.connect(DockableWindow.createMetadata)
            DockableWindow.createMetadataMenuAction = cmd

            vmd = metadataMenu.addAction("View Metadata")
            vmd.triggered.connect(DockableWindow.viewMetadata)
            DockableWindow.viewMetadataMenuAction = vmd

            emd = metadataMenu.addAction("Edit Metadata")
            emd.triggered.connect(DockableWindow.editMetadata)
            DockableWindow.editMetadataMenuAction = emd


    # YMAC QGIS Home Page
            dqhp = toolsMenu.addAction("YMAC QGIS Home Page")
            dqhp.triggered.connect(DockableWindow.QGISWebpage)

    # YMAC's QGIS Quick-Start will be accessed through the YMAC QGIS Home Page
            '''
    # QGIS Quick-Start
            qqs = toolsMenu.addAction("QGIS Quick-Start")
            qqs.triggered.connect(DockableWindow.QGISQuickStart)
            '''

    # About info
            adb = toolsMenu.addAction("About")
            adb.triggered.connect(DockableWindow.aboutDialogBox)

# ZOOM TO LOCATION BUTTON
            zoomLocationButton = QAction(toolsMenu)
            zoomLocationButton.setIcon(Tools.iconZoomLocation)
            zoomLocationButton.setText("Zoom to Location")
            zoomLocationButton.setToolTip("Zoom to Town, FD Grid or Lat/Long")
            zoomLocationButton.triggered.connect(DockableWindow.openZoomLocation)
            toolbar.addAction(zoomLocationButton)


# MAP PROD BUTTON
            mapProButton = QAction(toolsMenu)
            mapProButton.setIcon(Tools.iconMapPro)
            mapProButton.setText("MapPro")
            mapProButton.setToolTip("Map Production")
            mapProButton.triggered.connect(DockableWindow.mapProduction)
            toolbar.addAction(mapProButton)

# REGION SELECTOR
            regionComboBox = QComboBox(toolbar)
            regionComboBox.setToolTip("YMAC Region selector")
            topLayout.addWidget(regionComboBox)
            target = Tools.getRegion()
            for r in Tools.regions:
                regionComboBox.addItem(r.replace("_", " "), None)
                if r == target:
                    regionComboBox.setCurrentIndex(regionComboBox.count() - 1)
            regionComboBox.currentIndexChanged.connect(DockableWindow.regionChange)

# SEARCH CDDP
            searchbar = QMenuBar(dock)
            searchLayout.addWidget(searchbar)
            searchbar.setLayout(searchLayout)

            searchLabel = QLabel("Search data menu for:", searchbar)
            searchText = QLineEdit(searchbar)
            searchText.setToolTip("Start typing search text")
            searchLayout.addWidget(searchLabel)
            searchLayout.addWidget(searchText)
            searchText.textChanged.connect(DockableWindow.searchTextChange)

# CLEAR SEARCH BUTTON
            clearSearchButton = QPushButton(Tools.iconRefresh, "", searchbar)
            clearSearchButton.setToolTip("Clear search text")
            clearSearchButton.clicked.connect(lambda: searchText.setText(""))
            searchLayout.addWidget(clearSearchButton)

            topLayout.addStretch(99)
            searchLayout.addStretch(99)
            Tools.dm = DataMenu(dockLayout)

            Tools.flushErrors()
            return dock


##################################
##
#  Window management
##
##############################################################################
    @staticmethod
    def regionChange(index):
        Tools.setRegion(Tools.regions[index])

##############################################################################
    @staticmethod
    def dockAreaChange(location):
        Tools.setDockArea(location)


###################################
##
#  Click Handlers
##
##############################################################################
    @staticmethod
    def YMACGISWebpage():
        QDesktopServices.openUrl(QUrl("http://ymac-dc3-app1/"))

##############################################################################
    @staticmethod
    def QGISWebpage():
        QDesktopServices.openUrl(QUrl("http://qgis.org/en/docs/index.html"))

##############################################################################
    @staticmethod
    def QGISQuickStart():
        QDesktopServices.openUrl(QUrl("http://intranet/csd/gis/Documents/QGIS%20Quick%20Start.pdf"))

##############################################################################
    @staticmethod
    def viewMetadata():
        MetadataViewerDialog(Tools.activeLayer())

##############################################################################
    @staticmethod
    def editMetadata():
        MetadataEditorDialog(MetadataEditorDialog.EDIT, Tools.activeLayer())

##############################################################################
    @staticmethod
    def createMetadata():
        MetadataEditorDialog(MetadataEditorDialog.CREATE, Tools.activeLayer())

##############################################################################
    @staticmethod
    def dataLocations(checked):
        DataLocationsDialog()

##############################################################################
    @staticmethod
    def defineLayerCoordinateSystem(checked):
        SelectCRSDialog(SelectCRSDialog.LAYER, Tools.activeLayer())

##############################################################################
    @staticmethod
    def defineFrameCoordinateSystem(checked):
        SelectCRSDialog(SelectCRSDialog.FRAME)

##############################################################################
    @staticmethod
    def convertLayerToCoordinateSystem(checked):
        ConvertLayerToCRSDialog(Tools.activeLayer())

##############################################################################
    @staticmethod
    def aboutDialogBox(checked):
        AboutDialog()

##############################################################################
    @staticmethod
    def disableDefaultProject(checked):
        QSettings().setValue("QGis/newProjectDefault", "false")
        registry = QgsMapLayerRegistry.instance()
        registry.removeAllMapLayers()

##############################################################################
    @staticmethod
    def setCurrentProjectAsDefault(checked):
        QSettings().setValue("QGis/newProjectDefault", "true")
        project = QgsProject.instance()
        userProjDefaultPath = "C:/Users/" + Tools.username + "/.qgis2/project_default.qgs"
        if os.path.exists(userProjDefaultPath):
            shutil.copyfile(userProjDefaultPath, userProjDefaultPath + '~')
        project.setFileName(userProjDefaultPath)
        project.write()

##############################################################################
    @staticmethod
    def setYMACProjectAsDefault(checked):
        QSettings().setValue("QGis/newProjectDefault", "true")
        QSettings().setValue("YMAC/showDefaultMapDialog", "true")
        userProjDefaultLocation = "C:/Users/" + Tools.username + "/.qgis2/project_default.qgs"
        pluginPath = Tools.getPluginPath()
        pluginProjDefaultLocation = pluginPath + "/resources/project_default_YMAC.qgs"
        shutil.copyfile(pluginProjDefaultLocation, userProjDefaultLocation)


##############################################################################
##
#  Context Management
##
##############################################################################
    @staticmethod
    def showMetadataMenu():
        canEdit = False
        canView = False
        canCreate = False
        layer = Tools.activeLayer()
        if layer is not None:
            layerSource = str(layer.source())
            if layerSource.rsplit(".", 1)[-1].lower() == "shp":
                metadataLocation = MetadataTools.getExistingMetadataFileLocation(layerSource)
                if metadataLocation is not None:
                    canView = True
                    try:
                        # check for write access
                        f = open(metadataLocation, "r+")
                        f.close()
                        canEdit = True
                    except:
                        canEdit = False
                else:
                    try:
                        # check for write access
                        metadataLocation = layerSource + ".xml"
                        f = open(metadataLocation, "w+")
                        f.close()
                        os.remove(metadataLocation)
                        canCreate = True
                    except:
                        canCreate = False
        DockableWindow.viewMetadataMenuAction.setEnabled(canView)
        DockableWindow.editMetadataMenuAction.setEnabled(canEdit)
        DockableWindow.createMetadataMenuAction.setEnabled(canCreate)

    @staticmethod
    def showCoordinateSystemsMenu():
        canConvertLayer = False
        canDefineLayer = False
        canSetDataFrame = True

        layer = Tools.activeLayer()
        if layer is not None:
            if isinstance(layer, QgsVectorLayer):
                canConvertLayer = True
                layerSource = str(layer.source())
                if layerSource.rsplit(".", 1)[-1] == "shp":
                    prjLocation = layerSource[0:-4] + ".prj"
                    if os.path.isfile(prjLocation):
                        try:
                            # check for write access
                            f = open(prjLocation, "r+")
                            f.close()
                            canDefineLayer = True
                        except:
                            canDefineLayer = False
                    else:
                        try:
                            # check for write access
                            f = open(prjLocation, "w+")
                            f.close()
                            canDefineLayer = True
                        except:
                            canDefineLayer = False
                        try:
                            os.remove(prjLocation)
                        except:
                            pass

        DockableWindow.convertLayerToCoordinateSystemAction.setEnabled(canConvertLayer)
        DockableWindow.defineLayerCoordinateSystemAction.setEnabled(canDefineLayer)
        DockableWindow.defineFrameCoordinateSystemAction.setEnabled(canSetDataFrame)


##############################################################################
##
# Search management  #New code 20140908 to add search facility to CDDP
##
##############################################################################
    @staticmethod
    def searchTextChange(text):
        DataMenu.loadMenuData(Tools.dm, text)


###########################################################################
##
# Open Zoom to location  #New code 20140908 to add search facility to CDDP
##
##############################################################################
    @staticmethod
    def openZoomLocation():
        # Check at least one layer loaded
        if len(QgsMapLayerRegistry.instance().mapLayers()) != 0:
            ZoomToLocationDialog()
        else:
            Tools.debug("Please load at least one layer to map first!",
                        "Map Requirements")


##############################################################################
##
# map Production
# New code by PWM; 20140923
##
##############################################################################

    @staticmethod
    def mapProduction():
        # Tools.mapProdTool = True
        # check  at least one layer
        if len(QgsMapLayerRegistry.instance().mapLayers()) == 0:
            Tools.alert("Please load at least one layer to map first!",
                        "Map Requirements")
        else:
            # validate CRS
            # if Tools.iface.mapCanvas().mapRenderer().destinationCrs().mapUnits() != QGis.Meters:
                # Tools.debug("It looks like you are using an unprojected Coordinate Reference System.\n" +
                            # "Change to a projected CRS then retry the Map Production Tool.",
                            # "Invalid Coordinate Reference System")
                # crsDialog = SelectCRSDialog(SelectCRSDialog.PROJECTEDFRAME, None, None)
                # #return     #removed this so user not required to again click on Map Prod Tool icon
            dlg = MapLabelDialog()
            if dlg.result != QDialog.Rejected:
                MapProduction().createMap(dlg)
            else:
                return
