"""Inventory guard for editor declarations, aliases and the shared text behavior."""
import re
import unittest
from pathlib import Path
import _setup  # noqa: F401

QML = Path(__file__).resolve().parents[3] / 'src/meridiana/gui/qml/Meridiana'

class TextInventory(unittest.TestCase):
    def test_raw_editors_are_confined_to_common_controls_and_hidden_measurer(self):
        wrong = []
        for path in QML.rglob('*.qml'):
            text = re.sub(r'//[^\n]*', '', path.read_text(encoding='utf8'))
            aliases = set(re.findall(r'import QtQuick(?:\.(?:Templates|Controls)(?:\.\w+)?)? as (\w+)', text))
            for match in re.finditer(r'(?:(\w+)\.)?\b(TextInput|TextEdit|TextField|TextArea)\s*\{', text):
                alias, kind = match.groups()
                raw = (not alias and (kind in ('TextInput', 'TextEdit') or path.parent.name != 'Controls')) or alias in aliases
                if not raw:
                    continue
                if path.parent.name == 'Controls' and path.stem in ('TextField','TextArea','GrowingField','OverlayField'):
                    continue
                tail = text[match.end():match.end()+300]
                if path.name == 'Conversation.qml' and kind == 'TextEdit' and 'id: oneLine' in tail and 'visible: false' in tail:
                    continue
                wrong.append(str(path.relative_to(QML)) + ': ' + kind)
        self.assertEqual(wrong, [])

    def test_each_editor_family_keeps_common_menu_and_actions(self):
        for name in ('TextField','TextArea','GrowingField','OverlayField'):
            with self.subTest(name=name):
                source = (QML / 'Controls' / (name+'.qml')).read_text(encoding='utf8')
                self.assertIn('C.ContextMenu.menu: TextMenu', source)
                self.assertIn('TextActions {', source)
        self.assertIn('TextField {', (QML/'Controls/NumberField.qml').read_text(encoding='utf8'))

    def test_semantic_surfaces_have_copy_consumers(self):
        surfaces = ['Assistant/Conversation.qml','Checks/ChecksPage.qml','Controls/HelpBubble.qml',
                    'File/FileSection.qml','Settings/SettingsPage.qml','Dialogs/IfcImportPage.qml',
                    'Controls/WorkRow.qml','ProjectTree/ProjectTreePage.qml','Plant/PlantStringMenu.qml',
                    'Controls/Table.qml','Charts/Chart.qml','Charts/Formula.qml','Charts/Pedigree.qml',
                    'Properties/PedigreeQuantity.qml','Properties/PedigreeFormula.qml','Report/ReportPage.qml',
                    'Charts/BillsGrid.qml','Shell/CloseDialog.qml','Shell/ObjectPicker.qml','View3D/SunBar.qml']
        for name in surfaces:
            with self.subTest(name=name):
                self.assertRegex((QML/name).read_text(encoding='utf8'), r'ReadableText|CopyLabel|TextActions|Copy page text|labels.page')
