"""Persistent Quick panel arrangements, separate from the Widgets profile."""
import math

from meridiana import atomic, log


def layout(value):
    if not isinstance(value, dict):
        raise ValueError('The window layout must be an object')
    for key in ('left', 'right', 'bottom'):
        number = value.get(key)
        if not isinstance(number, (int, float)) or not math.isfinite(number) or not 100 <= number <= 20000:
            raise ValueError('Invalid panel extent: '+key)
    if value.get('view') not in ('both', 'plan', '3d') or not isinstance(value.get('selected'), dict):
        raise ValueError('Invalid layout selection')
    if not isinstance(value.get('panels'), list):
        raise ValueError('Missing panel arrangements')
    for panel in value['panels']:
        if panel.get('id') not in ('project', 'properties', 'checks', 'assistant') or panel.get('zone') not in ('left', 'right', 'bottom', 'floating'):
            raise ValueError('Unknown panel or docking zone')
        for key in ('x', 'y', 'width', 'height'):
            number = panel.get(key)
            if not isinstance(number, (int, float)) or not math.isfinite(number) or not 0 <= number <= 20000:
                raise ValueError('Invalid floating panel geometry')
    return value


# R549 (Daniel, 08/11/2026: «l'avvio deve sempre mostrare Progetto a sinistra e Proprietà a destra»): the two cards every
# start shows, each on its side, whatever the last session left; the window then moves Project beside Properties when
# it is too narrow for two columns (Workbench.qml, sideProject). Checks follows the window's height (arrangement.py).
START_SIDES = {'project': 'left', 'properties': 'right'}


def at_start(value):
    """A saved arrangement as a start shows it: Project and Properties shown, on their own sides, in front."""
    for panel in value['panels']:
        side = START_SIDES.get(panel.get('id'))
        if side:
            panel['opened'], panel['zone'] = True, side
            value['selected'] = dict(value['selected'], **{side: panel['id']})
    return value


class ShellState:
    def __init__(self, host):
        self.host = host
        self.path = host.paths.state / 'quick-shell.json'

    def restore(self):
        if not self.path.exists():
            return
        try:
            data, notice = atomic.read_json(self.path)
            if data.get('version') != 1 or not isinstance(data.get('shapes'), dict):
                raise ValueError('Unsupported window layout version')
            at_start(layout(data['layout']))
            for value in data['shapes'].values():
                at_start(layout(value))
            self.host.window.restoreLayout(data)
            if notice:
                log.complain('Quick window layout', ValueError(notice))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            log.complain('Quick window layout', error)

    def save(self):
        try:
            state = self.host.window.savedLayout().toVariant()
            layout(state['layout'])
            atomic.write_json(self.path, dict(version=1, **state))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            log.complain('Quick window layout', error)
