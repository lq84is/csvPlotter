import multiprocessing, sys, os
import pyqtgraph as pg
from pyqtgraph.Qt.QtWidgets import *
from pyqtgraph.Qt.QtGui import QAction
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import qtawesome
from pyqtgraph.Qt.QtCore import pyqtSignal
from pyqtgraph.dockarea import *
import csv
import functools
from pyqtgraph.Qt.QtCore import QRegularExpression
from pyqtgraph.Qt.QtCore import Qt
if __name__ != '__main__':
    from .log_utils.common import *
else:
    from log_utils.common import *
    print_err = print
__all__ = 'spawnViewer'


printinf = print
printerr = print


sampleBtnWidth = 14


trying_print = print


def color_rotator(start = [0, 255, 0], step = 100):
    color = start
    cur = color.index(max(color))
    dark = [255, 200, 150, 100]
    dark_step = 0
    while True:
        max_val = dark[dark_step]
        while color[(cur+1)%3] < max_val:
            yield tuple(color)
            color[(cur+1)%3] += step
        color[(cur+1)%3] = max_val
        color[cur] -= step
        while color[cur] > 0:
            yield tuple(color)
            color[cur] -= step
        color[cur] = 0
        cur = (cur + 1) % 3
        if cur == 0:
            dark_step += 1
            dark_step %= 4
        
col_rot = color_rotator()


class LineSetting(QWidget):
    def __init__(self, legend, item, label, on_done, *arg, **kw):
        super().__init__(*arg, **kw)
        self.on_done = on_done
        self.setAttribute(Qt.WA_DeleteOnClose) 
        self.setWindowTitle('Line properties')
        self.mainLayout = QFormLayout(self)
        self.labelText = QLineEdit(self)
        self.labelText.setText(label.text)
        self.labelText.textChanged.connect(label.setText)
        self.labelText.textChanged.connect(lambda _: legend.updateSize())
        self.mainLayout.addRow('Text', self.labelText)
        self.colorBtn = pg.ColorButton()
        pen = item.opts['pen']
        if type(pen) is QtGui.QPen:
            self.colorBtn.setColor(pen.color())
        if type(pen) is tuple:
            self.colorBtn.setColor(QtGui.QColor( (pen[0] << 16)|(pen[1] << 8)|pen[2]))
        self.colorBtn.update()
        self.mainLayout.addRow('Color', self.colorBtn)
        self.lineWidth = QSpinBox(self)
        self.lineWidth.setMinimum(1)
        self.lineWidth.setMaximum(10)
        self.lineWidth.setValue(1)
        self.lineWidth.valueChanged.connect(lambda w: item.setPen(color=self.colorBtn.color(), width = w))
        self.colorBtn.sigColorChanging.connect(lambda btn: item.setPen(color=btn.color(), width = self.lineWidth.value()))
        self.colorBtn.sigColorChanging.connect(lambda btn: item.setSymbolBrush(color=btn.color(), width = self.lineWidth.value()))
        self.mainLayout.addRow('Width', self.lineWidth)
        self.symbolCombo = QComboBox(self)
        symbols = { 'None': None,
                    'o': 'o',
                    's': 's',
                    't': 't',
                    'd': 'd',
                    '+': '+'}
        for k, v in symbols.items():
            self.symbolCombo.addItem(k, userData = v)
        self.symbolCombo.setCurrentIndex(0)
        self.symbolCombo.activated.connect(lambda _: item.setSymbol(self.symbolCombo.currentData()))
        self.mainLayout.addRow('Dots', self.symbolCombo)
        self.setLayout(self.mainLayout)
        self.setFixedHeight(self.mainLayout.sizeHint().height())
        self.show()
    def closeEvent(self, event):
        self.on_done()
        super().closeEvent(event)


class SampleBtn(pg.GraphicsWidget):
    clicked = pyqtSignal()
    def __init__(self, item, icon = None):
        pg.GraphicsWidget.__init__(self)
        self.item = item
        if not icon:
            self.pix = pg.icons.ctrl.qicon.pixmap(sampleBtnWidth,sampleBtnWidth)
        else:
            self.pix = icon.qicon.pixmap(sampleBtnWidth,sampleBtnWidth)
    def boundingRect(self):
        return QtCore.QRectF(0, 0, sampleBtnWidth, sampleBtnWidth)
    def paint(self, p, *args):
        opts = self.item.opts
        if opts.get('antialias'):
            p.setRenderHint(p.RenderHint.Antialiasing)
        p.drawPixmap(QtCore.QPoint(1, 1), self.pix)
    def mouseClickEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit()
        event.accept()
        self.update()


class LegendItemMod(pg.LegendItem):
    def setSampleType(self, sample):
        if sample is self.sampleType:
            return
        items = list(self.items)
        self.sampleType = sample
        self.clear()
        for sample, label, paletteBtn, closeBtn in items:
            plot_item = sample.item
            plot_name = label.text
            self.addItem(plot_item, plot_name)
        self.updateSize()
    def setLabelTextColor(self, *args, **kargs):
        self.opts['labelTextColor'] = fn.mkColor(*args, **kargs)
        for sample, label, _, _ in self.items:
            label.setAttr('color', self.opts['labelTextColor'])
        self.update()
    def setLabelTextSize(self, size):
        self.opts['labelTextSize'] = size
        for _, label, _, _ in self.items:
            label.setAttr('size', self.opts['labelTextSize'])
        self.update()
    def addItem(self, item, name, paletteBtn=None, closeBtn=None):
        label = pg.LabelItem(name, color=self.opts['labelTextColor'],
                          justify='left', size=self.opts['labelTextSize'])
        if isinstance(item, self.sampleType):
            sample = item
        else:
            sample = self.sampleType(item)
        if not paletteBtn:
            paletteBtn = SampleBtn(item)
        if not closeBtn:
            closeBtn   = SampleBtn(item, icon = pg.icons.close)
        closeBtn.clicked.connect(lambda: self.parentItem().parentItem().removeItem(sample.item))#-> PlotitemMod
        def delSettingWindow():
            del(paletteBtn.settingWindow)
        def startSetting():
            if not hasattr(paletteBtn, 'settingWindow'):
                paletteBtn.settingWindow = LineSetting(self, sample.item, label, delSettingWindow)
            else:
                paletteBtn.settingWindow.activateWindow()
        paletteBtn.clicked.connect(startSetting)
        self.items.append((sample, label, paletteBtn, closeBtn))
        self._addItemToLayout(sample, label, paletteBtn, closeBtn)
        self.updateSize()
    def _addItemToLayout(self, sample, label, paletteBtn, closeBtn):
        col = self.layout.columnCount()
        row = self.layout.rowCount()
        if row:
            row -= 1
        nCol = self.columnCount * 4
        if col == nCol:
            for col in range(0, nCol, 4):
                if not self.layout.itemAt(row, col):
                    break
            else:
                if col + 4 == nCol:
                    col = 0
                    row += 1
        self.layout.addItem(closeBtn, row, col)
        self.layout.addItem(paletteBtn, row, col + 1)
        self.layout.addItem(sample, row, col + 2)
        self.layout.addItem(label, row, col + 3)
        self.rowCount = max(self.rowCount, row + 1)
    def setColumnCount(self, columnCount):
        if columnCount != self.columnCount:
            self.columnCount = columnCount
            self.rowCount = math.ceil(len(self.items) / columnCount)
            for i in range(self.layout.count() - 1, -1, -1):
                self.layout.removeAt(i)  # clear layout
            for sample, label, paletteBtn, closeBtn in self.items:
                self._addItemToLayout(sample, label, paletteBtn, closeBtn)
            self.updateSize()
    def getLabel(self, plotItem):
        out = [(it, lab) for it, lab,_,_ in self.items if it.item == plotItem]
        try:
            return out[0][1]
        except IndexError:
            return None
    def removeItem(self, item):
        for sample, label, paletteBtn, closeBtn in self.items:
            if sample.item is item or label.text == item:
                self.items.remove((sample, label, paletteBtn, closeBtn))  # remove from itemlist
                self.layout.removeItem(sample)  # remove from layout
                sample.close()  # remove from drawing
                self.layout.removeItem(label)
                label.close()
                self.layout.removeItem(paletteBtn)
                if hasattr(paletteBtn, 'settingWindow'):
                    paletteBtn.settingWindow.close()
                    del(paletteBtn.settingWindow)
                paletteBtn.close()
                self.layout.removeItem(closeBtn)
                closeBtn.close()
                item.clear()
                item.deleteLater()
                self.updateSize()  # redraw box
                return  # return after first match
    def clear(self):
        for sample, label, paletteBtn, closeBtn in self.items:
            self.layout.removeItem(sample)
            sample.close()
            self.layout.removeItem(label)
            label.close()
            self.layout.removeItem(paletteBtn)
            paletteBtn.close()
            self.layout.removeItem(closeBtn)
            closeBtn.close()
        self.items = []
        self.updateSize()


class PlotItemMod(pg.PlotItem):
    def addLegend(self, offset=(30, 30), **kwargs):
        if self.legend is None:
            self.legend = LegendItemMod(offset=offset, **kwargs)
            self.legend.setParentItem(self.vb)
        return self.legend


class DockOpenCSV(Dock):
    @trying(trying_print)
    def __init__(self, *arg, addCursor = None, **kw):
        super().__init__(*arg, **kw)
        self.plotter = pg.PlotWidget(plotItem = PlotItemMod())
        self.plotter.showGrid(x=True, y=True, alpha=1)
        self.mouse_coord_x = 0
        self.plotter.scene().sigMouseMoved.connect(self.updateMouseCoordX)
        self.legend = self.plotter.addLegend()
        self.addWidget(self.plotter)
        self.urls = None
        addCursorAction = QAction('Add Cursor', self)
        if addCursor is None:
            addCursorAction.triggered.connect(lambda _: self.addCursor(self.mouse_coord_x))
        else:
            addCursorAction.triggered.connect(lambda _: addCursor(self.mouse_coord_x))
        menu = self.plotter.plotItem.vb.menu
        menu.addAction(addCursorAction)
    @trying(trying_print)
    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            super().dragMoveEvent(e)
    @trying(trying_print)
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
        else:
            super().dragEnterEvent(e)
    @trying(trying_print)
    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            try:
                files = e.mimeData().urls()
                rx = QRegularExpression(r'.*\.csv', QRegularExpression.CaseInsensitiveOption)
                txts = [t.url() for t in files if rx.match(t.url()).hasMatch() == True]
                if not txts:
                    printinf('No csv files')
                    return
                rx = QRegularExpression('file.*')
                txts = [t for t in txts if rx.match(t).hasMatch() == True]
                txts = [t[len('file:///'):] for t in txts]
                self.urls = txts
                #file = txts[0]
                self.files = txts
                self.handleFile(txts)
            except Exception as ex:
                printinf('Drop error:{}'.format(ex))
        else:
            super().dropEvent(e)
    @trying(trying_print)
    def handleFile(self, files):
        for file in files:
            with open(file) as f:
                reader = csv.reader(f)
                header_row = next(reader)       # названия столбцов, если есть
                x = []
                cols = None                     # список списков под y1, y2, ..., yN
                for row in reader:
                    if not row:
                        continue
                    # read 1st row as X
                    x.append(float(row[0]))
                    if cols is None:
                        # create array for ech Y-col except zero
                        cols = [[] for _ in range(len(row) - 1)]
                    # write data to corresponding arrays
                    for i in range(1, len(row)):
                        try:
                            cols[i-1].append(float(row[i]))
                        except ValueError:
                            # if we meet junk in CSV
                            cols[i-1].append(float('nan')) 
        
            # draw:
            base_name = getNameOnly(file)
        
            for idx, y in enumerate(cols):
                # name 
                if header_row and len(header_row) > idx + 1:
                    curve_name = f"{base_name}: {header_row[idx + 1]}"
                else:
                    curve_name = f"{base_name}: col {idx+1}"
        
                plot_item = self.plotter.plot(
                    x=x,
                    y=y,
                    name=curve_name,
                    pen=col_rot.__next__()
                )
                plot_item.setDownsampling(auto=True, method='peak')
                plot_item.setClipToView(True)
#    def handleFile(self, files):
#        for file in files:
#            with open(file) as f:
#                reader = csv.reader(f)
#                header_row = next(reader)
#                x=[]
#                y=[]
#                for row in reader:
#                    x.append(float(row[0]))
#                    y.append(float(row[1]))
#                plot_item = self.plotter.plot(x=x,y=y, name=getNameOnly(file), pen = col_rot.__next__())
#                plot_item.setDownsampling(auto=True, method = 'peak')
#                plot_item.setClipToView(True)
    def updateMouseCoordX(self, pos):
        mouse_point = self.plotter.getViewBox().mapSceneToView(pos)
        self.mouse_coord_x = mouse_point.x()
    def addCursor(self, coord):
        cursor = pg.InfiniteLine(movable=True, angle=90, label='{value:0.3f}', 
            labelOpts={'position':0.1, 'color': (255,255,0), 'fill': (200,200,200,50), 'movable': True})
        self.plotter.addItem(cursor)
        cursor.setPos([coord,0])


class MainWindow(QtWidgets.QMainWindow):
    @trying(trying_print)
    def __init__(self, *arg, **kw):
        super().__init__(*arg, **kw)
        self.docks = []
        self.cursors = {}
        self.dockcounter = 0
        self.setWindowTitle('CSV viewer')
        self.area = DockArea()
        self.setCentralWidget(self.area)
        self.resize(1000,500)
        #
        self.control_menu = self.menuBar()
        self.addPlot_action = QAction('Add Window', self)
        self.addPlot_action.triggered.connect(lambda _: self.addPlot())
        self.control_menu.addAction(self.addPlot_action)
        #
        self.linkAxis_action = QAction('Link Axes', self)
        self.linkAxis_action.setCheckable(True)
        self.linkAxis_action.toggled.connect(self.linkAxis)
        self.control_menu.addAction(self.linkAxis_action)
        #
        self.resetLegends_action = QAction('Reset Legends', self)
        self.resetLegends_action.triggered.connect(lambda _: self.resetLegends())
        self.control_menu.addAction(self.resetLegends_action)
    @trying(trying_print)
    def addPlot(self):
        self.dockcounter += 1
        dock = DockOpenCSV('Plot № {}'.format(self.dockcounter), closable=True, addCursor = self.addCursor)
        self.area.addDock(dock, 'bottom')
        dock.sigClosed.connect(self.delDock)
        self.docks.append(dock)
        if self.linkAxis_action.isChecked():
            self.linkAll()
        for cursor, lst in self.cursors.items():
            dockcursor = pg.InfiniteLine(movable=True, angle=90, 
                label='{value:0.3f}', labelOpts={'position':0.1, 
                                                'color': (255,255,0), 
                                                'fill': (200,200,200,100), 
                                                'movable': True})
            lst.append(dockcursor)
            dock.plotter.addItem(dockcursor)
            dockcursor.setValue(cursor.value())
            dockcursor.sigPositionChanged.connect(self.setMasterCursor)
    @trying(trying_print)
    def unlinkAll(self):
        for dock in self.docks:
            dock.plotter.setXLink(None)
    @trying(trying_print)
    def linkAll(self):
        for dock in self.docks:
            dock.plotter.setXLink(self.docks[0].plotter)
    @trying(trying_print)
    def linkAxis(self, linked):
        if linked:
            #self.linkAxis_action.setIcon(qtawesome.icon('fa.unlink'))
            self.linkAxis_action.setText('Unlink Axes')
            self.linkAll()
        else:
            #self.linkAxis_action.setIcon(qtawesome.icon('fa.link'))
            self.linkAxis_action.setText('Link Axes')
            self.unlinkAll()
    @trying(trying_print)
    def delDock(self, dock):
        delCursors = [c for c in dock.plotter.items() if issubclass(type(c), pg.InfiniteLine)]
        for fict, lst in self.cursors.items():
            for cur in delCursors:
                if cur in lst:
                    lst.remove(cur)
                    break
        for cur in delCursors:
            cur.deleteLater()    
        while dock.plotter.plotItem.items:
            dock.plotter.plotItem.removeItem(dock.plotter.plotItem.items[0])
        self.docks.remove(dock)
        dock.deleteLater()
        if self.linkAxis_action.isChecked():
            self.linkAll()
    def resetLegends(self):
        for dock in self.docks:
            dock.legend.setOffset((30,30))
    def addCursor(self, coord):
        fict_cur = pg.InfiniteLine(movable=True, angle=90)
        fict_cur.setValue(coord)
        self.cursors[fict_cur] = []
        for dock in self.docks:
            dockcursor = pg.InfiniteLine(movable=True, angle=90, label='{value:0.3f}', labelOpts={'position':0.1, 'color': (255,255,0), 'fill': (200,200,200,100), 'movable': True})
            self.cursors[fict_cur].append(dockcursor)
            dock.plotter.addItem(dockcursor)
            dockcursor.setValue(coord)
            dockcursor.sigPositionChanged.connect(self.setMasterCursor)
            dockcursor.sigClicked.connect(self.cursorClickHandler)
        fict_cur.sigPositionChanged.connect(self.setAllCursors)
    def setMasterCursor(self, slaveCursor):
        masterCursor = [c for c in self.cursors.keys() if slaveCursor in self.cursors[c]][0]
        masterCursor.setValue(slaveCursor.value())
    def setAllCursors(self, masterCursor):
        coord = masterCursor.value()
        for slaveCursor in self.cursors[masterCursor]:
            slaveCursor.setValue(coord)
    def delCursor(self, cursor):
        cursorToDel = [c for c in self.cursors if cursor in self.cursors[c]]
        if cursorToDel:
            cursorToDel = cursorToDel[0]
            for dock in self.docks:
                for c in self.cursors[cursorToDel]:
                    if c in dock.plotter.plotItem.items:
                        dock.plotter.removeItem(c)
            for c in self.cursors[cursorToDel]:
                c.deleteLater()
            del(self.cursors[cursorToDel])
    def cursorClickHandler(self, cursor, ev):
        if ev.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.delCursor(cursor)


def _process_entry_point():
    #app = pg.mkQApp("CSV Plotter")
    app = pg.mkQApp()
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


@trying(trying_print)
def spawnViewer(*arg, **kw):
    proc = multiprocessing.Process(target=_process_entry_point, name='csvviewer', daemon=None)
    proc.start()


if __name__ == '__main__':
    _process_entry_point()
