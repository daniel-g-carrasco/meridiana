"""Table clipboard text comes from model rows, including rows outside the viewport."""
import _setup  # noqa: F401
from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtTest import QTest
from quick.aiuti.text_scene import TextScene

class CopyValues(TextScene):
    def test_tsv_order_units_and_quoting(self):
        root, window = self.scene('Table', 'height: 160; columns: [{key:"name",title:"Name",sortable:true},{key:"power",title:"Power",unit:"kW"}]; model: [{name:"Z",power:2},{name:"A",power:1}]; selectionMode:"multiple"; selection: [0,1]')
        self.evaluate(root, 'sortBy(0); copyRows()')
        self.assertEqual(self.app.clipboard().text(), 'Name\tPower (kW)\nA\t1\nZ\t2')
        self.evaluate(root, 'freezeCell(0, 1); cellCopy.execute("copy")')
        self.assertEqual(self.app.clipboard().text(), '2 kW')

    def test_virtualized_rows_are_copied(self):
        root, window = self.scene('Table', 'height: 100; columns: [{key:"name",title:"Name"}]; model: Array.from({length:100}, (_,i)=>({name:"Row "+i})); selectionMode:"multiple"; selection:[0,99]')
        self.evaluate(root, 'copyRows()')
        self.assertEqual(self.app.clipboard().text(), 'Name\nRow 0\nRow 99')

    def test_copy_precedes_project_shortcut(self):
        root, window = self.scene('Table', 'height: 100; columns: [{key:"name",title:"Name"}]; model: [{name:"Value"}]; currentIndex:0; property int projectCopies:0; Shortcut { sequence: StandardKey.Copy; onActivated: projectCopies++ }')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
        self.assertEqual(root.property('projectCopies'), 0)
        self.assertEqual(self.app.clipboard().text(), 'Name\nValue')

    def test_right_click_copies_cell_without_changing_row_selection(self):
        root, window = self.scene('Table', 'height: 180; columns: [{key:"name",title:"Name"},{key:"power",title:"Power",unit:"kW"}]; model: [{name:"First",power:2},{name:"Second",power:3}]; selectionMode:"multiple"; currentIndex:1; selection:[1]')
        y = int(root.findChild(QObject, 'tableHeader').property('height')) + 10
        x = int(self.evaluate(root, 'columnLeft(1)')) + 20
        QTest.mouseClick(window, Qt.RightButton, pos=QPoint(x, y))
        self.assertEqual(root.property('frozenCell'), '2 kW')
        self.assertEqual(root.property('currentIndex'), 1)
        self.evaluate(root, 'cellCopy.execute("copy")')
        self.assertEqual(self.app.clipboard().text(), '2 kW')

    def test_tsv_quotes_tabs_newlines_and_quotes(self):
        root, window = self.scene('Table')
        actual = self.evaluate(root, 'quoted("a\\tb\\n\\\"c")')
        self.assertEqual(actual, '"a\tb\n""c"')

    def test_formula_copy_uses_source_without_rendering(self):
        from meridiana.gui.backend import charts_bridge
        _setup.quick_app()
        charts_bridge.register()
        for kind, module, extra in [('Formula', 'Charts', 'tex: "a+b"; inViewport:false'),
                                    ('PedigreeFormula', 'local:Properties', 'formula:"a+b"; active:false')]:
            with self.subTest(kind=kind):
                root, window = self.scene(kind, extra, module=module)
                root.forceActiveFocus()
                QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
                self.assertEqual(self.app.clipboard().text(), 'a+b')
                QTest.keyClick(window, Qt.Key_Menu)
                self.app.clipboard().setText('sentinel')
                QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
                self.assertEqual(self.app.clipboard().text(), 'a+b')

    def test_chart_menu_freezes_active_point(self):
        from meridiana.gui.backend import charts_bridge
        _setup.quick_app()
        charts_bridge.register()
        root, window = self.scene('Chart', 'height: 250; chartData: ({kind:"bars",categories:["Jan","Feb"],series:[["Power",[1,2]]],unit:"kW",table:{headers:[],rows:[]}})', module='Charts')
        root.setProperty('activePoint', 0)
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_Menu)
        frozen = root.property('frozenPoint')
        self.assertIn('Jan', frozen)
        self.assertIn('kW', frozen)
        root.setProperty('hoverIndex', 1)
        self.assertEqual(root.property('frozenPoint'), frozen)
        menu = next(o for o in root.findChildren(QObject) if o.metaObject().indexOfProperty('measuredWidth') >= 0 and o.property('visible'))
        self.evaluate(menu, 'itemAt(0).triggered()')
        self.assertEqual(self.app.clipboard().text(), frozen)
