"""The modelling journeys without the real cursor: native messages on a hidden Windows desktop.

    python tests/quick/percorsi/modellazione_nascosto.py <quick|widgets> <journey> <out dir>

Nothing reaches the mouse and keyboard of whoever is using the PC: tools/quick_native_input.py opens the
program on a desktop of its own. Each run writes <journey>-<engine>.json and .log in <out dir>;
modellazione_confronta.py reads them.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'tests'), str(ROOT/'src')]
TOOL = ROOT/'tools/quick_native_input.py'


def _tool(*args, timeout, text=None):
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=os.pathsep.join((str(ROOT/'tests'), str(ROOT/'src'))))
    with tempfile.TemporaryFile() as output:     # a pipe would stay open in the program left running
        code = subprocess.run([sys.executable, str(TOOL), *args], stdout=output, stderr=subprocess.STDOUT,
                              input=None if text is None else text.encode('utf8'),
                              stdin=subprocess.DEVNULL if text is None else None,
                              env=environment, timeout=timeout, cwd=ROOT).returncode
        output.seek(0)
        return code, output.read().decode('utf-8', 'replace')


def run(engine, journey, out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='meridiana-nascosto-'))
    from quick.percorsi import modellazione
    project = modellazione.base_project(work, journey)
    ctl = work/'ctl'
    code, text = _tool('start', '--engine', engine, '--ctl', str(ctl), '--project', str(project),
                       '--desktop', 'meridiana-modellazione', '--idle-exit', '900', timeout=240)
    if code:
        return code, text
    script = (f'import sys\nsys.path[:0] = [{str(ROOT/"tests")!r}, {str(ROOT/"src")!r}]\n'
              'from quick.percorsi import modellazione\n'
              f'modellazione.on_hidden(app, host, win, native, {engine!r}, {journey!r}, {str(out)!r})\n')
    try:
        return _tool('run', '--ctl', str(ctl), '-', '--timeout', '560', timeout=600, text=script)
    finally:
        _tool('run', '--ctl', str(ctl), '--stop', timeout=30)
        # What Python printed on its own: an exception in a slot ends up only here.
        log = ctl/'server.log'
        if log.exists():
            (out/f'{journey}-{engine}.server.log').write_text(log.read_text(encoding='utf8', errors='replace')[-20000:], encoding='utf8')


if __name__ == '__main__':
    done = run(sys.argv[1], sys.argv[2], sys.argv[3])
    print(done[0], done[1][-3000:])
