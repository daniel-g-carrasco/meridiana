"""R624: one component makes the soft ends of the areas that scroll (Daniel 15/11/2026: «ricordiamoci di mantenerla
ben centralizzata»). Controls/EdgeFades.qml with its shader Controls/edgefade.frag and its length in the theme
(design.Size.FADE); the areas get it through the common scrolling components (M.ScrollPage, M.List, M.Tree, M.Table,
M.Dialog, every vertical M.ScrollBar), never by hand.

Read in the sources: a QML outside the component that makes a soft end of its own (a gradient over what scrolls, a
mask, a dissolving shader, the old image veils) is red, unless it is in ALLOWED with its reason. Whether every area that
scrolls has the soft ends is the window's walk (quick/confini.py, «senza-sfumature»); how they look, the drawn guard
(quick/controlli/test_dissolvenza_r624.py).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QML = ROOT / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana'
COMPONENT = 'Controls/EdgeFades.qml'
# the common scrolling components that place EdgeFades
PLACERS = {'Controls/ScrollPage.qml', 'Controls/ScrollBar.qml', 'Controls/List.qml', 'Controls/Tree.qml',
           'Controls/Table.qml', 'Controls/Dialog.qml'}
# what may look like a soft end and is not one, each with its reason
ALLOWED = {
    ('View3D/Viewport.qml', 'Gradient'): "the sky behind the 3D scene, a background, nothing scrolls under it",
    ('Controls/ViewMask.qml', 'ShaderEffect'): "the selection's highlight on the plan (selection.frag)",
}
SHADERS_ALLOWED = {
    'Controls/edgefade.frag': "the dissolve of EdgeFades itself",
    'Plan/selection.frag': "the selection's highlight on the plan",
    'View3D/context.frag': "the material of the 3D context",
    'View3D/dots.frag': "the 3D view's dots",
    'View3D/ribbon.frag': "the 3D view's ribbons",
}
PATTERNS = {
    'Gradient': re.compile(r'\bGradient\s*\{'),
    'ShaderEffect': re.compile(r'\bShaderEffect\s*\{'),
    'MultiEffect': re.compile(r'\bMultiEffect\b'),
    'OpacityMask': re.compile(r'\bOpacityMask\b'),
    'maskSource': re.compile(r'\bmaskSource\b'),
    'layer.effect': re.compile(r'\blayer\.effect\b'),
    'image veil': re.compile(r'image://meridiana/fade'),
}


def sources():
    for path in sorted(QML.rglob('*.qml')):
        yield path.relative_to(QML).as_posix(), path.read_text(encoding='utf-8')


class OneSoftEnd(unittest.TestCase):
    def test_no_soft_end_made_by_hand(self):
        found = []
        for name, text in sources():
            if name == COMPONENT:
                continue
            code = '\n'.join(line.split('//', 1)[0] for line in text.splitlines())
            for kind, pattern in PATTERNS.items():
                if pattern.search(code) and (name, kind) not in ALLOWED:
                    found.append(f'{name}: {kind}')
        self.assertEqual(found, [], 'a soft end of its own: use M.EdgeFades through the scrolling components (R624)')

    def test_the_allowed_ones_are_still_there(self):
        # an exception whose file changed is taken out, so the list says only what is true
        texts = dict(sources())
        for (name, kind), reason in ALLOWED.items():
            self.assertRegex(texts.get(name, ''), PATTERNS[kind], f'{name}: {reason}')

    def test_no_shader_of_its_own(self):
        shaders = {p.relative_to(QML).as_posix() for p in QML.rglob('*.frag')}
        self.assertEqual(shaders - set(SHADERS_ALLOWED), set())
        self.assertTrue((QML / 'Controls' / 'edgefade.frag.qsb').is_file(), 'the compiled shader ships with the QML')

    def test_edge_fades_only_in_the_scrolling_components_and_without_parameters_of_their_own(self):
        uses = re.compile(r'\b(?:M\.|MC\.)?EdgeFades\s*\{([^}]*)\}')
        for name, text in sources():
            for match in uses.finditer(text):
                with self.subTest(name):
                    self.assertIn(name, PLACERS, 'EdgeFades is placed by the scrolling components, not by a page')
                    names = set(re.findall(r'(\w+)\s*:', match.group(1)))
                    # R633: `held`, the heads M.ScrollPage holds at the edges of a panel's page (HeldHeads.qml)
                    # spansSurface (r39, the kit's hybrid): false where the sides are closed, the shadow instead of the dissolve
                    self.assertLessEqual(names, {'flickable', 'barRoom', 'held', 'spansSurface'}, f'{name}: {match.group(0)}')

    def test_the_length_is_a_token(self):
        text = (QML / COMPONENT).read_text(encoding='utf-8')
        self.assertIn('Theme.size.FADE', text)
        # the dissolve paints no band; the gradient lives only in the shadow of the closed edges (r39, the kit)
        dissolve = text[:text.index('component Undershoot')] + text[text.index('Undershoot { objectName: "topUndershoot"'):]
        self.assertNotRegex(dissolve, r'GradientStop|image://')
        self.assertNotIn('image://', text)


if __name__ == '__main__':
    unittest.main()
