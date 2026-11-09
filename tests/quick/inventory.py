"""Reproduce the UI/test migration census without constructing Widgets."""
import ast
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Review estimates, not metrics. The report gives the shared-work day ranges.
GROUPS = {
    'shell': ('alta', 'window phasebar cards dock_motion file_page menubar variant_bar variants viewbar title_tools panel_buttons'),
    'plan': ('molto alta', 'plan plan_overlays world_map map_sources tileloader underlays sunbar day_picker canopy_dialog'),
    '3d': ('alta', 'view3d preview3d quick_image lit_modules viewcube report_3d still_view'),
    'properties': ('alta', 'properties inspector quantity_field pedigree rows'),
    'plant': ('molto alta', 'plant_page optimizer_groups sizing_job shared_tables'),
    'energy': ('alta', 'energy_pages charts charts_pg storage_page'),
    'checks': ('alta', 'checks_page marks status_pill'),
    'assistant': ('molto alta', 'assistant assistant_chat assistant_local assistant_setup conversation_view voice'),
    'documents': ('media', 'report_page report template_dialog document_style help_box help guide_card'),
    'catalogs': ('alta', 'catalog_dialog catalog_editor brand_picker registry_page pvsyst_import ifc_import'),
    'preferences': ('media', 'preferences appearance new_project site_dialog shortcuts_dialog update_controller update_dialog'),
    'system': ('media', 'style theme design icons symbols segments checkboxes scrollbars popups sections elided feedback '
               'motion fades app_events waiting lazy_page wheel undo save_status qt_translations input_log '
               'navigation_targets spotlight tour gallery selftest __init__'),
}


def imports_widgets(text):
    return 'QtWidgets' in text


def main():
    ui = []
    for path in sorted((ROOT/'src/meridiana/ui').glob('*.py')):
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text)
        group = next((k for k, (_d, names) in GROUPS.items() if path.stem in names.split()), 'unclassified')
        ui.append({'file': path.relative_to(ROOT).as_posix(), 'lines': len(text.splitlines()),
                   'classes': [n.name for n in tree.body if isinstance(n, ast.ClassDef)],
                   'direct_widgets': imports_widgets(text), 'group': group,
                   'difficulty_inferred': GROUPS[group][0] if group in GROUPS else 'da classificare'})
    assert not any(r['group'] == 'unclassified' for r in ui)
    tests = {}
    for group in ('widget', 'finestra'):
        rows = []
        for path in sorted((ROOT/'tests'/group).glob('test*.py')):
            text = path.read_text(encoding='utf-8')
            tree = ast.parse(text)
            rows.append({'file': path.relative_to(ROOT).as_posix(),
                         'test_methods': sum(isinstance(n, ast.FunctionDef) and n.name.startswith('test') for n in ast.walk(tree)),
                         'direct_widgets': imports_widgets(text), 'direct_ui': 'meridiana.ui' in text,
                         'widget_harness': any(s in text for s in ('qt_or_skip(', '_setup.window(', 'window(', 'window as '))})
        tests[group] = rows
    template = Path(r'C:\Users\Grasso\dev\qt-app-template\src\qtkit')
    template_rows = []
    for path in sorted(template.glob('*.py')):
        text = path.read_text(encoding='utf-8')
        template_rows.append({'file': path.name, 'lines': len(text.splitlines()), 'direct_widgets': imports_widgets(text)})
    out = ROOT/'docs/revisioni'
    (out/'quick-prova-inventario.json').write_text(json.dumps({'ui': ui, 'tests': tests, 'template': template_rows}, indent=2), encoding='utf-8')
    with (out/'quick-prova-moduli.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=('file','lines','direct_widgets','group','difficulty_inferred'))
        writer.writeheader()
        writer.writerows({k:r[k] for k in writer.fieldnames} for r in ui)
    for name in GROUPS:
        group = [r for r in ui if r['group'] == name]
        print(name, len(group), sum(r['lines'] for r in group))
    print('template', len(template_rows), sum(r['lines'] for r in template_rows),
          sum(r['direct_widgets'] for r in template_rows))


if __name__ == '__main__':
    main()
