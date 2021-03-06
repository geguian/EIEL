# -*- coding: utf-8 -*-
"""
/***************************************************************************
 viviendaseielDialog
                                 A QGIS plugin
 Asignación de viviendas a núcleo de población
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2020-04-27
        git sha              : $Format:%H$
        copyright            : (C) 2020 by gga
        email                : Geguian74@usal.com
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
from PyQt5.QtWidgets import QTableWidgetItem
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.utils import iface
from PyQt5.QtWidgets import QMessageBox



import os # This is is needed in the pyqgis console also
import random
from qgis.core import (
    QgsProject, QgsExpression
)
from qgis.core import (
    QgsVectorLayer, QgsDataItem
)
from qgis.core import (
    QgsProcessingFeatureSourceDefinition, QgsCategorizedSymbolRenderer, QgsStyle, QgsSymbol,
    QgsRendererCategory, QgsSimpleFillSymbolLayer, QgsStatisticalSummary
)

import processing
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'viviendaseiel_dialog_base.ui'))


class viviendaseielDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(viviendaseielDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.input_gml.setFilter("Archivos gml(*.gml)")
        self.input_shp.setFilter("Archivos shp(*.shp)")

        # Acción asociada al botón calcular viviendas
        self.btn_unir.clicked.connect(self.unionespacial)

        # Acción asociada al seleccionar un registro de la lista de referencias duplicadas
        self.lst_duplicados.itemClicked.connect(self.zoom)

        # Definición de la función principal
    def unionespacial(self, event):
        # Datos de viviendas de catastro
        bu = self.input_gml.filePath()

        # Datos de perímetros de núcleos de población EIEL
        nucleo = self.input_shp.filePath()

        # Unir aributos por localización: Viviendas y núcleos
        bu_output = 'C:/V_EIEL/viviendasclasificadas.shp'
        processing.run("qgis:joinattributesbylocation", {'INPUT': bu,
                                         'JOIN': nucleo,
                                         'PREDICATE': 0,
                                         'JOIN_FIELDS': ['CODIGO','DENOMINACI'],
                                         'METHOD': 0,
                                         'PREFIX':'NU_',
                                         'OUTPUT': bu_output})

        joinat = QgsVectorLayer(bu_output, "Viviendas clasificadas nucleo", "ogr")
        QgsProject.instance().addMapLayers([joinat])

        # Selecciono registros sin clasificar de la capa de viviendas clasificadas utilizando la capa núcleos

        expresion = "NU_CODIGO is NULL"
        joinat.selectByExpression(expresion, QgsVectorLayer.SetSelection)

        #Genero el buffer de la capa núcleos

        nucleo = self.input_shp.filePath()
        file_output = 'C:/V_EIEL/buffernucleo.shp'

        processing.run("native:buffer", {'INPUT': nucleo,
                                             'DISTANCE': 200,
                                             'SEGMENTS': 10,
                                             'DISSOLVE': False,
                                             'END_CAP_STYLE': 0,
                                             'JOIN_STYLE': 0,
                                             'MITER_LIMIT': 1,
                                             'OUTPUT': file_output})

        lyrBuffer = QgsVectorLayer(file_output, "Buffer nucleo", "ogr")
        QgsProject.instance().addMapLayers([lyrBuffer])

        # Unión espacial de los registros seleccionados de joinat con buffer
        bu_output_2 = 'C:/V_EIEL/viviendasclasificadas_2.shp'
        processing.run("qgis:joinattributesbylocation", {'INPUT': QgsProcessingFeatureSourceDefinition('Viviendas clasificadas nucleo',True),
                                         'JOIN': lyrBuffer,
                                         'PREDICATE': 0,
                                         'JOIN_FIELDS': ['CODIGO','DENOMINACI'],
                                         'METHOD': 0,
                                         'PREFIX':'NU_',
                                         'OUTPUT': bu_output_2})

        joinat_2 = QgsVectorLayer(bu_output_2, "Viviendas clasificadas buffer", "ogr")
        QgsProject.instance().addMapLayers([joinat_2])

        joinat.removeSelection()
        joinat.commitChanges()


        # El resto de viviendas no clasificadas mediante la union con capa buffer pasan a estar en diseminado
        joinat_2=iface.activeLayer()

        expresion_2 ="NU_CODIGO_ is NULL"
        joinat_2.selectByExpression(expresion_2, QgsVectorLayer.SetSelection)
        joinat_2.startEditing()
        n = joinat_2.selectedFeatureCount()

        for i in range (0,n):
            diseminado = joinat_2.selectedFeatures()
            viv_diseminado=diseminado[i]
            viv_diseminado.setAttribute("NU_CODIGO_", "99")
            viv_diseminado["NU_CODIGO_"]="99"
            joinat_2.updateFeature(viv_diseminado)
            viv_diseminado.setAttribute("NU_DENOM_1", "DISEMINADO")
            viv_diseminado["NU_DENOM_1"] = "DISEMINADO"
            joinat_2.updateFeature(viv_diseminado)

        joinat_2.commitChanges()
        joinat_2.removeSelection()


        joinat_2.startEditing()
        features=joinat_2.getFeatures()
        for feature in features:
            feature.setAttribute(feature.fieldNameIndex('NU_CODIGO'), feature['NU_CODIGO_'])
            feature.setAttribute(feature.fieldNameIndex('NU_DENOMIN'), feature['NU_DENOM_1'])
            joinat_2.updateFeature(feature)

        joinat_2.commitChanges()
        joinat_2.removeSelection()

        # Elimino los campos NU_CODIGO_ y NU_DENOM_1 para conservar la misma estructura en las dos capas joint attributes
        joinat_2.startEditing()
        joinat_2.deleteAttributes([27,28])
        joinat_2.updateFields()
        joinat_2.commitChanges()

        # Creo la capa union de Viviendas clasificadas nucleo(solo la selección) y viviendas clasificadas buffer
        # En primer lugar extraigo las viviendas clasificadas en la union con la capa nucleos
        expresion_3 ="NU_CODIGO is not NULL"
        joinat.selectByExpression(expresion_3, QgsVectorLayer.SetSelection)
        joinat.startEditing()

        seleccion = 'C:/V_EIEL/viviendasclasificadas_seleccion.shp'
        processing.run("native:saveselectedfeatures",
                       {'INPUT': joinat,
                        'OUTPUT': seleccion})
        nucleo_seleccion = QgsVectorLayer(seleccion, "Viviendas clasificadas nucleo seleccion", "ogr")
        QgsProject.instance().addMapLayers([nucleo_seleccion])

        joinat.removeSelection()


        resultado= 'C:/V_EIEL/viviendasclasificadas_resultado.shp'
        processing.run("native:mergevectorlayers",
                       {'LAYERS': [nucleo_seleccion, joinat_2],
                        'OUTPUT': resultado})

        resultado_merge = QgsVectorLayer(resultado, "Viviendas clasificadas", "ogr")
        QgsProject.instance().addMapLayers([resultado_merge])

        # Suprimo del proyecto todas las capas intermedias generadas en el proceso
        QgsProject.instance().removeMapLayer(nucleo_seleccion)
        QgsProject.instance().removeMapLayer(joinat_2)
        QgsProject.instance().removeMapLayer(joinat)
        QgsProject.instance().removeMapLayer(lyrBuffer)


        #Representación categorizada de la capa resultado
        #Valores únicos
        resultado_merge = iface.activeLayer()

        valoresnucleo = []
        unico = resultado_merge.dataProvider()
        campos = unico.fields()
        id = campos.indexFromName('NU_DENOMIN')
        valoresnucleo = unico.uniqueValues(id)

        #Creación de categorías
        categorias = []
        for valornucleo in valoresnucleo:

            # inicio el valor de símbolo por defecto para la geometría tipo
            symbol = QgsSymbol.defaultSymbol(resultado_merge.geometryType())

            # configuración de capa de simbología
            layer_style = {}
            layer_style['color'] = '%d, %d, %d' % (random.randint(0, 256), random.randint(0, 256),random.randint(0, 256))
            layer_style['outline'] = '#000000'
            symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

            # sustitución de simbología por defecto por simbología configurada
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)

            # creación de objeto renderer
            categoria = QgsRendererCategory(valornucleo, symbol, str(valornucleo))

            # generación de entrada para la lista de categorías
            categorias.append(categoria)

        renderer = QgsCategorizedSymbolRenderer('NU_DENOMIN', categorias)
        # asignación del renderer a la capa
        if renderer is not None:
            resultado_merge.setRenderer(renderer)

        resultado_merge.triggerRepaint()

    # Cálculo de estadísticas

        resultado = iface.activeLayer()
        estadisticas='C:/V_EIEL/estadisticas.csv'
        processing.run("qgis:statisticsbycategories",
                       {'CATEGORIES_FIELD_NAME': ['NU_DENOMIN','NU_CODIGO'],
                        'INPUT':'Viviendas clasificadas',
                        'OUTPUT': 'C:/V_EIEL/estadisticas.csv',
                        'VALUES_FIELD_NAME': 'numberOfDw',
                        })

    # Cargo datos calculados de estadísticas de distribución de viviendas en QTableWidget tbl_resultados
        with open(estadisticas,'r') as leer_estadisticas:
            registros = leer_estadisticas.read().splitlines()
            contar = 0 #Descarto la primera linea del archivo por contener las cabeceras de los campos
            for registro in registros:
                r=0
                if contar > 0:
                    campos = registro.split(',')
                    #Puesto que el campo codigo se almacena con "" las elimino para que no aparezcan en la tabla
                    sc=campos[1].lstrip('"').rstrip('"')

                    #Cargo datos del csv en Qtable widget
                    self.tbl_resultados.insertRow(r)
                    self.tbl_resultados.setItem(r, 0, QTableWidgetItem(str(sc)))
                    self.tbl_resultados.setItem(r, 1, QTableWidgetItem(str(campos[0])))
                    self.tbl_resultados.setItem(r, 2, QTableWidgetItem(str(campos[7])))
                    r=r+1
                contar=contar+1

        # Rastreo de registros duplicados en capa resultado por intersectar con dos buffer o dos núcleos
        features = resultado_merge.getFeatures()
        referencias=[]
        referencias_dup = []
        for f in features:
            idr= f.fieldNameIndex('reference')
            referencia =f.attribute(idr)
            if referencia not in referencias:
                referencias.append(referencia)
            else:
                referencias_dup.append(referencia)

        self.lst_duplicados.addItems(referencias_dup)
        total_duplicados=self.lst_duplicados.count()
        self.text_duplicados.append(str(total_duplicados))

    # Configuración de la acción de zoom al clicar sobre algún elemento de la lista de duplicados
    def zoom (self):
        layer = iface.mapCanvas().layers()[0]
        seleccion = self.lst_duplicados.currentItem()
        features=layer.getFeatures()
        valorseleccion = seleccion.text()

        for f in features:
            idr = f.fieldNameIndex('reference')
            referencia = f.attribute(idr)

            if str(referencia) == str(valorseleccion):
                it = f.id()
                layer.selectByIds([int(it)])
                iface.mapCanvas().zoomToSelected()
