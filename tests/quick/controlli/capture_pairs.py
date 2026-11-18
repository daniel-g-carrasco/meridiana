"""Real Windows Widgets/Quick pairs. Run with python -m quick.controlli.capture_pairs.

The reference instantiates production Widgets, never a QML imitation. All input is
sent to the two test windows; neither the system pointer nor user settings move.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QLocale, QPoint, QPointF, QRect, QSize, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QEnterEvent, QFont, QIcon, QImage, QMouseEvent, QPainter, QPalette
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QLabel,
                               QLineEdit, QListWidget, QMenu, QProgressBar, QPushButton,
                               QScrollArea, QScrollBar, QSlider, QTabBar, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget, QDialog, QDialogButtonBox, QTableWidget,
                               QTableWidgetItem, QToolTip, QMainWindow, QSplitter, QStackedWidget)
from shiboken6 import delete

from meridiana.config import Config
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.capture import grab
from meridiana.ui import design, icons, motion, segments, style
from meridiana.ui.theme import Theme, class_fonts


CASES = {
    'button': 'M.Button { text: "Salva" }',
    'command': 'M.Button { text: "Calcola"; iconName: "compute" }',
    'tool': 'M.ToolButton { text: "Edificio"; iconName: "building" }',
    'split': 'M.SplitButton { text: "Edificio"; iconName: "building"; model: [{text:"Edificio"},{text:"Copertura"}] }',
    'field': 'M.TextField { text: "Capannone Rho" }',
    'field-narrow': 'M.TextField { text: "non indicata" }',
    'number': 'M.NumberField { value: 12.5; unit: "kW"; decimals: 2 }',
    'combo': 'M.ComboBox { model: ["Chiaro", "Scuro", "Sistema"] }',
    'combo-narrow': 'M.ComboBox { model: ["non indicata", "monofase", "trifase"] }',
    'check': 'M.CheckBox { text: "Mostra ombre" }',
    'partial': 'M.CheckBox { text: "Mostra ombre"; tristate: true; checkState: Qt.PartiallyChecked }',
    'segments': 'M.Segments { model: ["Pianta", "Vista 3D", "Entrambe"] }',
    'tabs': 'M.Tabs { model: ["Mesi", "Perdite", "Giorno tipo"] }',
    'badge': 'M.Pill { text: "Pronto"; state: "done" }',
    'count': 'M.Pill { variant: "count"; level: "warn"; text: "12" }',
    'section': 'M.Section { title: "Sito"; M.TextField { objectName: "section-field"; width: parent.width; text: "Capannone Rho" } }',
    'empty': 'M.EmptyState { title: "Calcola la producibilità per vedere i risultati."; actionText: "Calcola" }',
    'scroll': 'M.ScrollBar { orientation: Qt.Vertical; size: .3; position: .2 }',
    'divider': 'M.SplitHandle {}',
    'slider': 'M.Slider { from: 0; to: 100; value: 50; stepSize: 1 }',
    'progress': 'M.ProgressBar { value: .5 }',
    'list': 'M.List { model: ["Capannone", "Uffici", "Copertura"] }',
    'tree': 'M.Tree { model: [{id:"b", text:"Capannone", children:[{id:"r",text:"Copertura"}]},{id:"u",text:"Uffici"}]; expandedIds: ["b"] }',
    'card': 'M.Card { title: "Proprietà"; closable: true; M.Label { text: "Capannone Rho" } }',
    'icon': 'M.Icon { iconName: "building" }',
    'label': 'M.Label { text: "Capannone Rho" }',
    'menu': '''Item { id: fixture; M.Menu { enabled: fixture.enabled; width: parent.width; x: 0; y: 0; visible: true
        M.MenuItem { text: "Salva"; iconName: "save_revision"; shortcutText: "Ctrl+S" }
        M.MenuSeparator {}
        M.Menu { title: "Viste"; M.MenuItem { text: "Pianta" } }
        M.MenuItem { text: "Non disponibile"; enabled: false }
    } }''',
    'submenu': '''Item { id: fixture; M.Menu { enabled: fixture.enabled; width: parent.width; x: 0; y: 0; visible: true
        M.MenuItem { text: "Pianta"; checkable: true; checked: true }
        M.MenuItem { text: "Vista 3D" }
    } }''',
    'tooltip': '''Item { M.ToolTip { x: 0; y: 0; visible: true; delay: 0
        onAboutToShow: shownAt = Qt.point(0,0)
        text: "Salva (Ctrl+S)\\nConserva la copia precedente e salva tutte le modifiche al progetto nella cartella scelta." } }''',
    'combo-list': '''Item { M.ComboBox { width: parent.width; y: -height-2
        model: ["Chiaro", "Scuro", "Sistema"]; Component.onCompleted: popup.open() } }''',
    'table': '''M.Table { columns: [{title:"Edificio",key:"name"},{title:"Potenza",unit:"kW",key:"value",numeric:true}]
        model: [{name:"Capannone",value:"12,50"},{name:"Uffici",value:"8,40"}]
        total: ({name:"Totale",value:"20,90"}) }''',
    'dialog': '''Item { id: fixture; M.Dialog { enabled: fixture.enabled; title: "Proprietà"; width: parent.width; height: parent.height; x: 0; y: 0
        acceptText: "Conferma"; rejectText: "Annulla"; visible: true
        contentItem: M.Label { text: "Confermare le modifiche?" } } }''',
}
for variant in ('list', 'page', 'table'):
    CASES['fades-' + variant] = """Item {
        Flickable { id: port; objectName: "fade-port"; anchors.fill: parent; anchors.topMargin: AIR; anchors.bottomMargin: AIR
            contentHeight: 300; clip: true
            Column { width: parent.width; Repeater { model: 15
                Rectangle { required property int index; width: port.width; height: 20
                    color: index % 2 ? Theme.colors.panel : Theme.colors.accent } } }
        }
        M.EdgeFades { flickable: port; page: PAGE; table: TABLE }
    }""".replace('AIR', '6' if variant == 'page' else '0').replace('PAGE', str(variant == 'page').lower()).replace('TABLE', str(variant == 'table').lower())
STATES = ('normal', 'hover', 'pressed', 'active', 'disabled', 'focus', 'selected')


class ReferenceBar(QStackedWidget):
    """The toolbar's transparent stacked widget needs the window's painted floor."""

    def __init__(self, floor):
        super().__init__()
        self.floor = floor

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.floor)
        painter.end()
        super().paintEvent(event)


STATE_CASES = {
    **{name: ('normal', 'active', 'selected') for name in CASES if name.startswith('fades-')},
    'field-narrow': ('normal', 'hover', 'disabled', 'focus', 'selected'),
    'combo-narrow': ('normal', 'hover', 'disabled', 'focus'),
    'tooltip': ('normal',),
    **{name: ('normal', 'disabled') for name in ('badge', 'icon', 'label', 'progress', 'empty')},
    **{name: ('normal', 'hover', 'pressed', 'active', 'disabled') for name in ('tool', 'split')},
    **{name: ('normal', 'hover', 'pressed', 'active', 'disabled', 'focus')
       for name in ('button', 'command', 'combo', 'check', 'partial', 'segments', 'tabs', 'count')},
    **{name: ('normal', 'hover', 'pressed', 'disabled', 'focus', 'selected')
       for name in ('field', 'number', 'list', 'tree', 'table')},
    **{name: ('normal', 'hover', 'pressed', 'disabled', 'focus') for name in ('scroll', 'slider', 'divider')},
    'card': ('normal', 'hover', 'disabled'),
    'section': ('normal', 'hover', 'disabled', 'focus'),
    **{name: ('normal', 'hover', 'disabled', 'focus') for name in ('menu', 'submenu', 'combo-list', 'dialog')},
}


def reference(name, theme, host):
    """Return a production widget, and its natural/representative size."""
    if name.endswith('-narrow'):
        widget, size = reference(name.removesuffix('-narrow'), theme, host)
        if name == 'field-narrow':
            widget.setText('non indicata')
        else:
            widget.clear()
            widget.addItems(['non indicata', 'monofase', 'trifase'])
        return widget, QSize(85, size.height())
    if name.startswith('fades-'):
        from meridiana.ui import fades
        fades.set_colour(theme.tokens['panel'])
        class Stripes(QWidget):
            def paintEvent(self, event):
                painter = QPainter(self)
                for i in range(15):
                    painter.fillRect(0, i*20, self.width(), 20, QColor(theme.tokens['panel' if i % 2 else 'accent']))
        w = QScrollArea(host)
        w.setFrameShape(QScrollArea.Shape.NoFrame)
        w.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        w.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        stripes = Stripes()
        stripes.setFixedSize(240, 300)
        w.setWidget(stripes)
        fades.attach(w, air=name == 'fades-page', table=name == 'fades-table')
        fades.set_ground(w, theme.tokens['panel'])
        size = QSize(240, 100)
    elif name in ('button', 'command'):
        w = QPushButton('Salva' if name == 'button' else 'Calcola', host)
        if name == 'command':
            w.setIcon(icons.icon('compute'))
        size = QSize(110, 28)
    elif name in ('tool', 'split'):
        from meridiana.ui.phasebar import ToolButton, ToolMenuButton
        a = QAction(icons.icon('building'), 'Edificio', host)
        if name == 'tool':
            w = ToolButton(a, 'Edificio', parent=host)
            w.setFont(design.text_font(design.Text.SECONDARY, w.font()))
            w.fit('under', 52, 64)
        else:
            b = QAction('Copertura', host)
            w = ToolMenuButton([('a', 'Edificio', a), ('b', 'Copertura', b)])
            w.setParent(host)
            w.setFont(design.text_font(design.Text.SECONDARY, w.font()))
            w.fit('under', 52, 64)
            w.set_colours(theme.tokens)
        size = w.size()
    elif name in ('field', 'number', 'combo'):
        if name == 'field':
            w = QLineEdit('Capannone Rho', host)
        elif name == 'number':
            w = QDoubleSpinBox(host)
            w.setRange(-1e12, 1e12)
            w.setDecimals(2)
            w.setValue(12.5)
            w.setSuffix(' kW')
            w.setLocale(QLocale('it_IT'))
        else:
            w = QComboBox(host)
            w.addItems(['Chiaro', 'Scuro', 'Sistema'])
        size = QSize(220, 28)
    elif name in ('check', 'partial'):
        w = QCheckBox('Mostra ombre', host)
        if name == 'partial':
            w.setTristate(True)
            w.setCheckState(Qt.CheckState.PartiallyChecked)
        size = QSize(220, 28)
    elif name == 'segments':
        w = segments.Segments(parent=host)
        for word in ('Pianta', 'Vista 3D', 'Entrambe'):
            w.add(word)
        w.set_current('Pianta')
        size = w.sizeHint()
    elif name == 'tabs':
        w = QTabBar(host)
        for word in ('Mesi', 'Perdite', 'Giorno tipo'):
            w.addTab(word)
        segments.on_bar(w)
        size = w.sizeHint()
    elif name == 'badge':
        w = QLabel('Pronto', host)
        w.setObjectName('state-done')
        w.setFont(design.text_font(design.Text.CONTROL))
        size = QSize(72, 24)
    elif name == 'count':
        from meridiana.ui.checks_page import CountChip
        w = CountChip('warn')
        w.setParent(host)
        w.setText('12')
        size = w.sizeHint()
    elif name == 'section':
        w = style.Group('Sito', host)
        box = QVBoxLayout(w)
        box.setContentsMargins(8, 8, 8, 8)
        box.addWidget(QLineEdit('Capannone Rho'))
        size = QSize(300, 71)
    elif name == 'empty':
        w = style.EmptyState('Calcola la producibilità per vedere i risultati.', host)
        w.set_action(QAction('Calcola', w))
        size = QSize(340, 150)
    elif name == 'scroll':
        w = QScrollBar(Qt.Orientation.Vertical, host)
        w.setRange(0, 700)
        w.setPageStep(300)
        w.setValue(200)
        size = QSize(10, 160)
    elif name == 'slider':
        w = QSlider(Qt.Orientation.Horizontal, host)
        w.setRange(0, 100)
        w.setValue(50)
        size = QSize(220, 22)
    elif name == 'divider':
        splitter = QSplitter(Qt.Orientation.Horizontal, host)
        splitter.addWidget(QWidget())
        splitter.addWidget(QWidget())
        splitter.setHandleWidth(8)
        splitter.setGeometry(12, 12, 180, 184)
        splitter.show()
        w = splitter.handle(1)
        size = QSize(8, 160)
    elif name == 'progress':
        w = QProgressBar(host)
        w.setValue(50)
        w.setTextVisible(False)
        size = QSize(220, 6)
    elif name == 'list':
        w = QListWidget(host)
        w.addItems(['Capannone', 'Uffici', 'Copertura'])
        size = QSize(300, 110)
    elif name == 'tree':
        w = QTreeWidget(host)
        w.setHeaderHidden(True)
        b = QTreeWidgetItem(w, ['Capannone'])
        QTreeWidgetItem(b, ['Copertura'])
        QTreeWidgetItem(w, ['Uffici'])
        w.expandAll()
        size = QSize(300, 110)
    elif name == 'card':
        from meridiana.ui.cards import CardDock
        w = CardDock('Proprietà', host)
        w.set_colours(theme.tokens, theme.dark)
        label = QLabel('Capannone Rho')
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        w.setWidget(label)
        size = QSize(300, 120)
    elif name in ('menu', 'submenu'):
        w = QMenu(host)
        if name == 'menu':
            action = w.addAction(icons.icon('save_revision'), 'Salva')
            action.setShortcut('Ctrl+S')
            w.addSeparator()
            w.addMenu('Viste').addAction('Pianta')
            w.addAction('Non disponibile').setEnabled(False)
        else:
            action = w.addAction('Pianta')
            action.setCheckable(True)
            action.setChecked(True)
            w.addAction('Vista 3D')
        style.quiet_menus(w)
        size = w.sizeHint()
    elif name == 'combo-list':
        combo = QComboBox(host)
        combo.addItems(['Chiaro', 'Scuro', 'Sistema'])
        combo.resize(220, 28)
        host.show()
        combo.showPopup()
        w = combo.view().window()
        size = w.size()
    elif name == 'tooltip':
        QToolTip.showText(QPoint(50, 50), 'Salva (Ctrl+S)\nConserva la copia precedente e salva tutte le modifiche al progetto nella cartella scelta.', host)
        QTest.qWait(250)
        w = next(w for w in QApplication.instance().allWidgets() if w.metaObject().className() == 'QTipLabel')
        size = w.size()
    elif name == 'dialog':
        w = QDialog(host)
        w.setWindowTitle('Proprietà')
        box = QVBoxLayout(w)
        box.addWidget(QLabel('Confermare le modifiche?'))
        buttons = QDialogButtonBox(w)
        buttons.addButton('Annulla', QDialogButtonBox.ButtonRole.RejectRole)
        buttons.addButton('Conferma', QDialogButtonBox.ButtonRole.AcceptRole)
        box.addWidget(buttons)
        size = QSize(340, 160)
    elif name == 'table':
        w = QTableWidget(2, 2, host)
        w.setHorizontalHeaderLabels(['Edificio', 'Potenza\nkW'])
        for i, row in enumerate((('Capannone', '12,50'), ('Uffici', '8,40'))):
            for j, value in enumerate(row):
                w.setItem(i, j, QTableWidgetItem(value))
        w.horizontalHeader().setStretchLastSection(True)
        size = QSize(340, 160)
    elif name in ('icon', 'label'):
        w = QLabel(host)
        if name == 'icon':
            w.setPixmap(icons.icon('building').pixmap(QSize(16, 16), host.devicePixelRatioF()))
            size = QSize(16, 16)
        else:
            w.setText('Capannone Rho')
            size = QSize(200, 28)
    else:
        raise ValueError(name)
    w.ensurePolished()
    return w, size


def apply_widget_state(w, name, state):
    name = name.removesuffix('-narrow')
    w.setEnabled(state != 'disabled')
    if name.startswith('fades-'):
        bar = w.verticalScrollBar()
        bar.setValue(bar.maximum() if state == 'selected' else 100 if state == 'active' else 0)
    if name == 'icon':
        w.setEnabled(True)  # The QIcon already supplies its disabled pixels.
        mode = QIcon.Mode.Disabled if state == 'disabled' else QIcon.Mode.Normal
        w.setPixmap(icons.icon('building').pixmap(QSize(16, 16), w.devicePixelRatioF(), mode))
    if state == 'active':
        if name == 'split':
            w.face.defaultAction().setCheckable(True)
            w.face.defaultAction().setChecked(True)
        elif hasattr(w, 'setChecked'):
            if hasattr(w, 'setCheckable'):
                w.setCheckable(True)
            w.setChecked(True)
        elif name == 'segments':
            w.set_current('Vista 3D')
        elif name in ('tabs', 'combo'):
            w.setCurrentIndex(1)
    if state == 'selected':
        if name == 'list':
            w.setCurrentRow(1)
        elif name == 'tree':
            w.setCurrentItem(w.topLevelItem(0).child(0))
        elif name == 'table':
            w.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            w.setCurrentCell(1, 0)
        elif hasattr(w, 'selectAll'):
            w.setFocus()
            w.selectAll()
    target = w.face if name == 'split' else w.title_bar.close_button if name == 'card' else w
    if name in ('list', 'tree', 'table'):
        target = w.viewport()
    if state in ('hover', 'pressed'):
        point = QPoint(min(25, target.width()//2), min(12, target.height()//2))
        if name == 'scroll':
            point = QPoint(5, 60)
        # Local mouse moves alone do not generate QWidget's native Enter on the
        # isolated desktop. Deliver the actual entry event to the ancestry too.
        ancestor = target
        while ancestor is not None:
            local = ancestor.mapFromGlobal(target.mapToGlobal(point))
            QApplication.sendEvent(ancestor, QEnterEvent(QPointF(local), QPointF(local), QPointF(target.mapToGlobal(point))))
            ancestor = ancestor.parentWidget()
        # QPushButton records MouseOver in mouseMoveEvent. On the isolated
        # desktop it needs local delivery, including when no button is held.
        target.setMouseTracking(True)
        QApplication.sendEvent(target, QMouseEvent(QEvent.Type.MouseMove, QPointF(point),
            QPointF(target.mapToGlobal(point)), Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
        if state == 'pressed' and name not in ('section', 'combo'):
            QTest.mousePress(target, Qt.MouseButton.LeftButton, pos=point)
    elif state == 'focus':
        w.setFocus(Qt.FocusReason.TabFocusReason)
        if name in ('menu', 'submenu'):
            w.setActiveAction(w.actions()[0])
        if hasattr(w, 'keyboard'):
            w.keyboard = True
            w.update()
        if name == 'tabs':
            segments.on_bar(w).keyboard = True
            w.update()


def apply_quick_state(item, window, name, state):
    name = name.removesuffix('-narrow')
    item.setEnabled(state != 'disabled')
    if name.startswith('fades-'):
        port = item.findChild(QQuickItem, 'fade-port')
        port.setProperty('contentY', 300-port.height() if state == 'selected' else 100 if state == 'active' else 0)
    if state == 'active':
        if name == 'split':
            item.setProperty('active', True)
        elif item.metaObject().indexOfProperty('checked') >= 0:
            item.setProperty('checkable', True)
            item.setProperty('checked', True)
        elif name in ('segments', 'tabs', 'combo'):
            item.setProperty('currentIndex', 1)
    if state == 'selected':
        if name in ('field', 'number'):
            item.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        elif name in ('list', 'tree', 'table'):
            item.setProperty('currentIndex', 1)
    if state in ('hover', 'pressed'):
        local = QPointF(item.width()-20, 18) if name == 'card' else QPointF(min(25, item.width()/2), min(12, item.height()/2))
        if name == 'scroll':
            local = QPointF(5, 60)
        elif name == 'table':
            local = QPointF(25, 62)
        point = item.mapToScene(local).toPoint()
        QTest.mouseMove(window, point)
        if state == 'pressed' and name not in ('section', 'combo'):
            QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=point)
    elif state == 'focus':
        if name in ('menu', 'submenu'):
            QTest.keyClick(window, Qt.Key.Key_Down)
        elif name == 'dialog':
            return  # The dialog has already focused its default accept button.
        elif name == 'section':
            item.findChild(QQuickItem, 'section-field').forceActiveFocus(Qt.FocusReason.TabFocusReason)
        else:
            item.forceActiveFocus(Qt.FocusReason.TabFocusReason)


def capture(args):
    app = QApplication.instance() or QApplication(['fidelity-pairs'])
    design.set_text_size('large' if args.large else 'medium')
    theme = Theme(Config(theme=args.theme, font='plex', accent='indigo', backgrounds='grey'))
    base = QFont(app.font())
    base.setPixelSize(design.Type.BODY)
    app.setFont(base)
    class_fonts(app)
    motion.set_reduced(True)
    engine = QQmlEngine()
    install_controls(engine, dict(theme=args.theme, textSize='large' if args.large else 'medium', reducedMotion=True))
    errors = []
    engine.warnings.connect(lambda es: errors.extend(e.toString() for e in es))
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    report = []
    names = args.controls.split(',') if args.controls else CASES
    for name in names:
        applicable = STATE_CASES.get(name, STATES)
        for state in (s for s in (args.states.split(',') if args.states else applicable) if s in applicable):
            host = QMainWindow() if name == 'card' else ReferenceBar(QColor(theme.tokens['panel'])) if name in ('tool', 'split') else QWidget()
            if name in ('tool', 'split'):
                host.setObjectName('phase-bars')
            pal = host.palette()
            pal.setColor(QPalette.ColorRole.Window, QColor(theme.tokens['panel']))
            host.setPalette(pal)
            host.setAutoFillBackground(True)
            host.resize(400, 200)
            host.show()
            host.activateWindow()
            QTest.qWaitForWindowExposed(host)
            w, size = reference(name, theme, host)
            w.setGeometry(QRect(QPoint(12, 12), size))
            if name not in ('menu', 'submenu', 'tooltip', 'combo-list', 'dialog'):
                w.show()
            host.resize(max(400, size.width()+24), max(200, size.height()+24))
            host.show()
            QTest.qWaitForWindowExposed(host)
            if name != 'tooltip':
                host.setFocus()
                QTest.mouseMove(host, QPoint(host.width()-4, host.height()-4))
            QTest.qWait(25)
            apply_widget_state(w, name, state)
            QTest.qWait(35)
            reference_hint = [w.sizeHint().width(), w.sizeHint().height()]
            popup = name in ('menu', 'submenu', 'combo-list', 'tooltip', 'dialog')
            if popup:
                if name in ('menu', 'submenu'):
                    w.popup(host.mapToGlobal(QPoint(12, 12)))
                else:
                    w.show()
                QTest.qWait(200)
                if name in ('menu', 'submenu', 'combo-list'):
                    apply_widget_state(w, name, state)
                    QTest.qWait(35)
                pixels = w.grab().toImage()
                ratio = pixels.devicePixelRatio()
                size = w.size()
                wi = QImage(round((size.width()+8)*ratio), round((size.height()+8)*ratio), QImage.Format.Format_ARGB32_Premultiplied)
                wi.setDevicePixelRatio(ratio)
                wi.fill(QColor(theme.tokens['panel']))
                painter = QPainter(wi)
                painter.drawImage(QPoint(4, 4), pixels)
                painter.end()
                w.hide()
            else:
                wi = host.grab(QRect(w.mapTo(host, QPoint(-4, -4)), QSize(size.width()+8, size.height()+8))).toImage()
            component = QQmlComponent(engine)
            component.setData(('import QtQuick\nimport Meridiana.Theme\nimport Meridiana.Controls as M\n' + CASES[name]).encode(), QUrl())
            if component.isError():
                raise RuntimeError('\n'.join(e.toString() for e in component.errors()))
            item = component.create()
            item.setParent(engine)
            natural = [item.implicitWidth(), item.implicitHeight()]
            window = QQuickWindow()
            window.setColor(QColor(theme.tokens['panel']))
            window.resize(host.width(), host.height())
            item.setParentItem(window.contentItem())
            item.setPosition(QPointF(12, 12))
            item.setSize(size)
            window.show()
            window.requestActivate()
            QTest.qWaitForWindowExposed(window)
            QTest.mouseMove(window, QPoint(window.width()-4, window.height()-4))
            QTest.qWait(25)
            apply_quick_state(item, window, name, state)
            QTest.qWait(35)
            image = grab(window)
            dpr = image.devicePixelRatio()
            qi = image.copy(QRect(round(8*dpr), round(8*dpr), round((size.width()+8)*dpr), round((size.height()+8)*dpr)))
            suffix = '-large' if args.large else ''
            stem = f'{name}-{args.theme}-s{dpr:g}-{state}{suffix}'
            wi.save(str(out / (stem+'-widgets.png')))
            qi.save(str(out / (stem+'-quick.png')))
            report.append(dict(control=name, state=state, theme=args.theme, scale=dpr, large=args.large,
                               stem=stem, width=size.width()+8, height=size.height()+8, quickNatural=natural,
                               widgetsNatural=reference_hint,
                               api=str(window.rendererInterface().graphicsApi())))
            # Release test presses before disposal, avoiding an application's stuck grab.
            if state == 'pressed' and name not in ('section', 'combo'):
                event = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(-1, -1), QPointF(-1, -1),
                                    Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
                app.sendEvent(w, event)
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(window.width()-4, window.height()-4))
            window.close()
            host.close()
            delete(item)
            delete(window)
            delete(host)
        print(name, flush=True)
    if errors:
        raise RuntimeError('\n'.join(errors))
    manifest = out / f'manifest-{args.theme}-s{app.primaryScreen().devicePixelRatio():g}{"-large" if args.large else ""}.json'
    previous = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
    merged = {row['stem']: row for row in previous}
    merged.update({row['stem']: row for row in report})
    manifest.write_text(json.dumps(list(merged.values()), indent=2, ensure_ascii=False), encoding='utf-8')
    build_index(out)
    delete(engine)


def build_index(out):
    records = []
    for source in sorted(out.glob('manifest-*.json')):
        records += json.loads(source.read_text(encoding='utf-8'))
    sections = []
    for r in records:
        caption = html.escape(f'{r["control"]} | {r["theme"]} | scala {r["scale"]:g} | {r["state"]}' + (' | testo grande' if r['large'] else ''))
        pair = ''.join(f'<figure><figcaption>{kind}</figcaption><img loading="lazy" src="{r["stem"]}-{kind}.png" width="{r["width"]*2}" height="{r["height"]*2}"></figure>' for kind in ('widgets', 'quick'))
        sections.append(f'<section data-control="{r["control"]}" data-theme="{r["theme"]}" data-scale="{r["scale"]:g}"><h2>{caption}</h2><div class="pair">{pair}</div></section>')
    options = ''.join(f'<option>{html.escape(c)}</option>' for c in sorted({r['control'] for r in records}))
    page = '''<!doctype html><html lang="it"><meta charset="utf-8"><title>Controlli: Widgets e Quick</title>
<style>body{font:14px system-ui;margin:24px;background:#ddd;color:#222}header{position:sticky;top:0;background:#fff;padding:12px;z-index:1}h2{font-size:15px}section{border-bottom:1px solid #aaa;padding:10px 0}.pair{display:flex;gap:24px;flex-wrap:wrap}figure{margin:0}img{image-rendering:pixelated;display:block}select{margin-right:16px}</style>
<header><h1>Controlli veri, affiancati al 200 %</h1><p>Sinistra Widgets, destra Quick. Stessa misura logica, Plex, grigio/indaco. Catture Windows e Direct3D 11. Le differenze e i casi non applicabili sono descritti nel rapporto r13-controlli-fedelta.md.</p>
<label>Controllo <select id="control"><option value="">Tutti</option>''' + options + '''</select></label>
<label>Tema <select id="theme"><option value="">Entrambi</option><option>light</option><option>dark</option></select></label>
<label>Scala <select id="scale"><option value="">Entrambe</option><option>1</option><option>2</option></select></label></header>
''' + '\n'.join(sections) + '''<script>function filter(){for(const s of document.querySelectorAll('section'))s.hidden=['control','theme','scale'].some(k=>document.getElementById(k).value&&s.dataset[k]!==document.getElementById(k).value)}for(const e of document.querySelectorAll('select'))e.onchange=filter;</script></html>'''
    (out/'index.html').write_text(page, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('docs/quick/confronto/controlli'))
    parser.add_argument('--theme', default='light', choices=('light', 'dark'))
    parser.add_argument('--large', action='store_true')
    parser.add_argument('--controls', default='')
    parser.add_argument('--states', default='')
    parser.add_argument('--matrix', action='store_true', help='Isolated process per family, both themes and DPRs')
    args = parser.parse_args()
    os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    if args.matrix:
        for scale in (1, 2):
            for theme in ('light', 'dark'):
                for name in args.controls.split(',') if args.controls else CASES:
                    if args.states and not set(args.states.split(',')).intersection(STATE_CASES.get(name, STATES)):
                        continue
                    cmd = [sys.executable, '-m', 'quick.controlli.capture_pairs', '--out', str(args.out),
                           '--theme', theme, '--controls', name]
                    if args.states:
                        cmd += ['--states', args.states]
                    if args.large:
                        cmd += ['--large']
                    subprocess.run(cmd, env=dict(os.environ, QT_SCALE_FACTOR=str(scale)), check=True)
                print(f'Complete: {theme}, DPR {scale}', flush=True)
        return
    capture(args)


if __name__ == '__main__':
    main()
