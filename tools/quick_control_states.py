"""Capture every shared control with real Qt pointer and keyboard events.

Run without arguments for the four theme/DPR combinations and portable HTML.
No hovered, down, visualFocus or pressed property is written by this tool.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
from pathlib import Path
import subprocess
import sys

STATES = ('normal', 'hover', 'pressed', 'active', 'disabled', 'focus')
LABELS = ('Normale', 'Passaggio', 'Premuto', 'Attivo', 'Disattivato', 'Fuoco')
WIDTH, HEIGHT = 360, 240
DEST = Path('build/quick-foto/controlli/stati')
HTML = Path('docs/quick/confronto/controlli.html')

# Each specimen is a genuine public control. Names only help locate the event target.
SPECS = {
    'Button': 'M.Button { text: "Salva"; iconName: "save"; checkable: true; onClicked: probe.actions++ }',
    'ToolButton': 'M.ToolButton { text: "Edificio"; iconName: "building"; checkable: true; onClicked: probe.actions++ }',
    'SplitButton': 'M.SplitButton { text: "Edificio"; iconName: "building"; model: [{text:"Copertura"},{text:"Moduli"}]; onClicked: probe.actions++ }',
    'MenuItem': 'M.MenuItem { width: 240; text: "Ombre"; checkable: true; onTriggered: probe.actions++ }',
    'Menu': 'M.MenuItem { width: 240; text: "Ombre"; checkable: true; onTriggered: probe.actions++ }',
    'ComboBox': 'M.ComboBox { width: 240; model: ["Edificio", "Copertura", "Moduli"]; onActivated: probe.actions++ }',
    'TextField': 'M.TextField { width: 240; text: "Edificio principale"; onTextEdited: probe.actions++ }',
    'NumberField': 'M.NumberField { width: 240; value: 12.5; unit: "kW"; minimum: 0; maximum: 100; onValueEdited: probe.actions++ }',
    'CheckBox': 'M.CheckBox { text: "Mostra le ombre"; onClicked: probe.actions++ }',
    'Segments': 'M.Segments { width: 280; model: [{text:"Pianta"},{text:"Vista 3D"}]; onActivated: probe.actions++ }',
    'Tabs': 'M.Tabs { width: 280; model: [{text:"Pianta"},{text:"Vista 3D"}]; onActivated: probe.actions++ }',
    'ScrollBar': 'M.ScrollBar { width: 14; height: 170; size: 0.3; onPositionChanged: probe.actions++ }',
    'Card': 'M.Card { width: 280; height: 130; title: "Proprieta"; closable: true; onClosed: probe.actions++; M.Label { text: "Edificio principale" } }',
    'Section': 'M.Section { width: 280; title: "Proprieta"; onToggled: probe.actions++; M.Label { text: "Edificio principale"; height: 60 } }',
    'SplitHandle': 'Base.SplitView { width: 290; height: 170; handle: M.SplitHandle {}; Rectangle { color: Theme.colors.field; implicitWidth: 120; Base.SplitView.minimumWidth: 40 } Rectangle { color: Theme.colors.panel; Base.SplitView.minimumWidth: 40 } }',
    'Table': 'M.Table { width: 300; height: 190; columns: [{title:"Edificio",key:"name"},{title:"Potenza",key:"power",numeric:true}]; model: [{name:"Principale",power:"12,50"},{name:"Deposito",power:"5,00"}]; onRowActivated: probe.actions++ }',
    'Tree': 'M.Tree { width: 280; height: 170; model: [{text:"Progetto",id:"p",children:[{text:"Edificio",id:"b"}]},{text:"Impianto",id:"i"}]; onActivated: probe.actions++ }',
    'List': 'M.List { width: 280; height: 170; model: [{text:"Edificio",icon:"building"},{text:"Copertura",icon:"ridge"}]; onActivated: probe.actions++ }',
    'Dialog': 'M.Dialog { objectName: "popup"; x: 8; y: 8; width: 330; title: "Proprieta"; acceptText: "Conferma"; rejectText: "Annulla"; onAccepted: probe.actions++; contentItem: M.Label { text:"Edificio principale" } }',
    'EmptyState': 'M.EmptyState { width: 300; height: 190; title: "Nessun risultato"; description: "Calcola il progetto."; actionText: "Calcola"; onTriggered: probe.actions++ }',
    'ToolTip': 'M.Button { text: "Salva"; tip: "Conserva la copia precedente." }',
    'Pill': 'M.Pill { text: "Pronto" }',
    'Icon': 'M.Icon { iconName: "building"; width: 32; height: 32 }',
    'Label': 'M.Label { text: "Edificio principale"; textStyle: "title" }',
    'ProgressBar': 'M.ProgressBar { width: 260; value: 0.65 }',
}
STATIC = {'Pill', 'Icon', 'Label', 'ProgressBar'}
NOTES = {
    'Card': 'Stati del pulsante di chiusura. Attivo: comando emesso, nessuno stato persistente.',
    'Dialog': 'Stati di Conferma nel dialogo aperto. Attivo: accettazione emessa e dialogo chiuso.',
    'EmptyState': 'Stati del comando Calcola. Attivo: azione emessa, nessuno stato persistente.',
    'ScrollBar': 'Attivo: trascinamento del cursore. Fuoco N/A: il fuoco appartiene alla vista scorrevole, non alla barra.',
    'SplitHandle': 'Attivo: divisore spostato. Fuoco N/A: SplitHandle Qt e un bersaglio del puntatore, senza navigazione da tastiera.',
    'ToolTip': 'Il suggerimento appare al passaggio sul comando. Premuto, attivo, disattivato e fuoco autonomi N/A: sono stati del comando ospite.',
    'TextField': 'Attivo: selezione del testo con Ctrl+A. Il puntatore premuto posiziona il cursore.',
    'NumberField': 'Attivo: incremento reale con freccia Su, valore 13,50.',
    'Table': 'Il passaggio e la pressione sono gesti sulla riga; il controllo non aggiunge una tinta specifica alla pressione.',
    'Menu': 'Menu aperto dal pulsante Apri. Sei stati della voce selezionabile contenuta nel menu.',
    'ProgressBar': 'Indicatore determinato al 65%. Passaggio, premuto, attivo e fuoco N/A: nessuna interazione o selezione.',
}


def applicable(name, state):
    if name in STATIC:
        return state in ('normal', 'disabled')
    if name == 'ToolTip':
        return state in ('normal', 'hover')
    return not (name in ('SplitHandle', 'ScrollBar') and state == 'focus')


def capture(theme, scale, names):
    from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickItem, QQuickWindow
    from PySide6.QtTest import QTest
    from shiboken6 import delete
    from meridiana.quick.backend.controls import install_controls
    from meridiana.quick.capture import grab
    from PIL import Image

    app = QGuiApplication.instance() or QGuiApplication(['control-states'])
    engine = QQmlEngine()
    install_controls(engine, dict(theme=theme))
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    window = QQuickWindow()
    window.setFlags(Qt.WindowType.FramelessWindowHint)
    window.resize(WIDTH, HEIGHT)
    window.show()
    assert QTest.qWaitForWindowExposed(window)
    destination = DEST / f'{theme}-s{scale}'
    destination.mkdir(parents=True, exist_ok=True)
    records = {}

    def visual(item):
        for child in item.childItems():
            yield child
            yield from visual(child)

    def point(item, x=None, y=None):
        pos = item.mapToScene(QPointF(item.width()/2 if x is None else x,
                                     item.height()/2 if y is None else y))
        return QPoint(round(pos.x()), round(pos.y()))

    def click(item, x=None, y=None):
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point(item, x, y))

    for name in names:
        records[name] = {}
        for state in STATES:
            body = SPECS[name]
            if name == 'Dialog':
                body += ' M.Button { objectName:"launcher"; x:12; y:12; text:"Apri"; onClicked: parent.children[0].open() }'
            elif name == 'Menu':
                body = 'M.Menu { id: popup; x:12; y:48; ' + body.replace('{', '{ objectName:"subject";', 1) + ' } M.Button { objectName:"launcher"; x:12; y:12; text:"Apri"; onClicked: popup.open() }'
            else:
                body = body.replace('{', '{ objectName:"subject"; x:24; y:24;', 1)
            source = ('import QtQuick\nimport QtQuick.Controls.Basic as Base\nimport Meridiana.Theme\nimport Meridiana.Controls as M\n'
                      'Rectangle { id:probe; width:360; height:240; color:Theme.colors.card; property int actions:0; ' + body + '}')
            component = QQmlComponent(engine)
            component.setData(source.encode(), QUrl())
            assert not component.isError(), [e.toString() for e in component.errors()]
            root = component.create()
            assert root is not None, [e.toString() for e in component.errors()]
            root.setParent(engine)
            root.setParentItem(window.contentItem())
            QTest.qWait(35)
            launcher = root.findChild(QQuickItem, 'launcher')
            if launcher:
                click(launcher)
                QTest.qWait(220)
            subject = root.findChild(QObject, 'subject')
            candidates = [i for i in visual(window.contentItem()) if i.isVisible()]
            target = subject
            if name == 'Dialog':
                target = next(i for i in candidates if i.property('text') == 'Conferma' and i.metaObject().indexOfProperty('down') >= 0)
                subject = target
            elif name in ('Card', 'Section', 'EmptyState', 'SplitButton'):
                buttons = [i for i in visual(subject) if i.isVisible() and i.metaObject().indexOfProperty('down') >= 0]
                target = buttons[-1] if name == 'SplitButton' else buttons[0]
            elif name == 'SplitHandle':
                target = next(i for i in visual(subject) if i.metaObject().className().startswith('SplitHandle'))
            elif name in ('Table', 'Tree', 'List'):
                target = subject
            assert isinstance(target, QQuickItem), (name, target)
            QTest.mouseMove(window, QPoint(WIDTH-2, HEIGHT-2))
            window.contentItem().forceActiveFocus()
            QTest.qWait(40)
            before = root.property('actions')
            event = 'riposo'
            used = applicable(name, state)
            # Table header precedes its first row. List and tree start at their first row.
            pointer = point(target, 100, 66 if name == 'Table' else 16) if name in ('Table', 'Tree', 'List') else point(target)
            if used and state in ('hover', 'pressed'):
                QTest.mouseMove(window, pointer)
                event = 'mouseMove'
                if state == 'pressed':
                    QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=pointer)
                    event += ' + mousePress (tenuto)'
                QTest.qWait(900 if name == 'ToolTip' else 150)
            elif used and state == 'focus':
                for _ in range(25):
                    QTest.keyClick(window, Qt.Key.Key_Tab)
                    if target.hasActiveFocus() or any(i.hasActiveFocus() for i in visual(target)):
                        break
                assert target.hasActiveFocus() or any(i.hasActiveFocus() for i in visual(target)), name
                event = 'Tab fino al bersaglio, activeFocus verificato'
            elif used and state == 'disabled':
                subject.setProperty('enabled', False)
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=pointer)
                assert root.property('actions') == before, name
                assert not target.isEnabled(), name
                QTest.mouseMove(window, QPoint(WIDTH-2, HEIGHT-2))
                event = 'enabled=false; clic ignorato verificato'
            elif used and state == 'active':
                if name in ('Segments', 'Tabs'):
                    click(target, target.width()*0.75, target.height()/2)
                    assert subject.property('currentIndex') == 1
                elif name in ('ScrollBar', 'SplitHandle'):
                    start = point(target, target.width()/2, 20 if name == 'ScrollBar' else target.height()/2)
                    end = start + QPoint(0, 65) if name == 'ScrollBar' else start + QPoint(60, 0)
                    QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=start)
                    QTest.mouseMove(window, end, 80)
                    QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=end)
                    if name == 'ScrollBar':
                        assert subject.property('position') > 0
                elif name in ('TextField', 'NumberField'):
                    click(target)
                    QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
                    if name == 'NumberField':
                        QTest.keyClick(window, Qt.Key.Key_Up)
                        assert subject.property('value') == 13.5
                    else:
                        assert subject.property('selectedText') == 'Edificio principale'
                elif name in ('Table', 'Tree', 'List'):
                    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=pointer)
                    QTest.keyClick(window, Qt.Key.Key_Right if name == 'Tree' else Qt.Key.Key_Down)
                    if name != 'Tree':
                        assert subject.property('currentIndex') == 1
                else:
                    click(target)
                    if name in ('Button', 'ToolButton', 'MenuItem', 'Menu', 'CheckBox'):
                        assert target.property('checked'), name
                    elif name in ('Card', 'Dialog', 'EmptyState', 'Section'):
                        assert root.property('actions') == before + 1, name
                QTest.mouseMove(window, QPoint(WIDTH-2, HEIGHT-2))
                event = 'clic / tastiera / trascinamento; effetto verificato'
            QTest.qWait(220)
            image = grab(window)
            assert (image.width(), image.height()) == (WIDTH*scale, HEIGHT*scale)
            path = destination / f'{name}-{state}.png'
            assert image.save(str(path))
            records[name][state] = dict(applicable=used, event=event if used else 'N/A, riposo di riferimento', actions=root.property('actions'))
            if state == 'pressed' and used:
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=pointer)
            delete(root)
            delete(component)
            QTest.qWait(10)
            assert not warnings, warnings
        strip = Image.new('RGB', (WIDTH*scale*6, HEIGHT*scale))
        for index, state in enumerate(STATES):
            with Image.open(destination / f'{name}-{state}.png') as cell:
                strip.paste(cell.convert('RGB'), (index*WIDTH*scale, 0))
        strip.save(destination / f'{name}.png')
        print(f'{theme} DPR{scale}: {name}', flush=True)
    (destination / 'events.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    window.close()
    delete(window)
    delete(engine)
    return app


def build_html(names):
    sections = []
    for theme in ('light', 'dark'):
        for scale in (1, 2):
            folder = DEST / f'{theme}-s{scale}'
            records = json.loads((folder / 'events.json').read_text(encoding='utf-8'))
            rows = []
            for name in names:
                data = base64.b64encode((folder / f'{name}.png').read_bytes()).decode()
                headers = ''.join(f'<th>{label}{" (N/A)" if not applicable(name, state) else ""}</th>' for label, state in zip(LABELS, STATES, strict=True))
                note = NOTES.get(name, 'Passaggio, premuto, attivo e fuoco N/A: elemento senza interazione.' if name in STATIC else '')
                events = '; '.join(f'{label}: {records[name][state]["event"]}' for label, state in zip(LABELS, STATES, strict=True))
                rows.append(f'<article><h2>{name}</h2><p>{html.escape(note)}</p><table><tr>{headers}</tr></table><img alt="{name}: sei stati" src="data:image/png;base64,{data}"><details><summary>Eventi e verifiche</summary>{html.escape(events)}</details></article>')
            sections.append(f'<section id="{theme}-{scale}"><h1>{"Chiaro" if theme == "light" else "Scuro"}, DPR {scale}</h1>{"".join(rows)}</section>')
    HTML.parent.mkdir(parents=True, exist_ok=True)
    HTML.write_text('<!doctype html><html lang="it"><meta charset="utf-8"><title>Controlli: ogni stato</title><style>body{font:14px system-ui;margin:24px;background:#eee;color:#222}nav{position:sticky;top:0;background:white;padding:12px;z-index:2}a{margin-right:24px}article{background:white;padding:16px;margin:18px 0}img{width:100%;height:auto;display:block}table{width:100%;table-layout:fixed}th{width:16.666%;font-size:13px}details{margin-top:8px}section{scroll-margin-top:65px}</style><nav><a href="#light-1">Chiaro 1</a><a href="#light-2">Chiaro 2</a><a href="#dark-1">Scuro 1</a><a href="#dark-2">Scuro 2</a></nav><h1>Matrice dei controlli condivisi</h1><p>25 tipi, sei colonne, due temi e due rapporti di pixel. Ogni cella applicabile usa eventi Qt reali. N/A mantiene il riposo per confronto e dichiara lo stato assente. Le immagini sono incorporate: questo file funziona anche da solo. Ingrandire la pagina per osservare i pixel originali. Ogni cella misura 360 x 240 pixel logici.</p>' + ''.join(sections) + '</html>', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', choices=('light', 'dark'))
    parser.add_argument('--scale', type=int, default=1)
    parser.add_argument('--only', nargs='+', choices=list(SPECS))
    args = parser.parse_args()
    names = args.only or list(SPECS)
    if args.theme:
        capture(args.theme, args.scale, names)
    else:
        for theme in ('light', 'dark'):
            for scale in (1, 2):
                env = dict(os.environ, QT_SCALE_FACTOR=str(scale))
                subprocess.run([sys.executable, __file__, '--theme', theme, '--scale', str(scale), *(['--only', *names] if args.only else [])], env=env, check=True)
        build_html(names)
        print(HTML)


if __name__ == '__main__':
    main()
