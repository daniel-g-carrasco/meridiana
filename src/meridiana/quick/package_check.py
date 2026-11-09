"""The Qt Quick window checked from end to end, offscreen, the way the Windows package runs it (r28, 09/11/2026):

    Meridiana.exe -m meridiana.quick.package_check PROJECT OUT [--language en]
    python -m meridiana.quick.package_check PROJECT OUT [--language en]          (from the sources)

PROJECT is opened in the window with a profile of its own in OUT/profile (settings, caches: nothing of the person's
own is read or written), its year is computed by the computation's process (the package runs itself with -m, see
build-aux/windows/meridiana_main.py), every phase is shown and grabbed, then File, Settings and Meridio, and the
report is written to OUT/report.pdf by the report's worker. OUT/check.json says what was seen (the language, the
year's kWh, the times, the QML warnings); the exit code is 0 when the year and the report came. The project file
is never written. Without a screen (Qt's offscreen platform) unless QT_QPA_PLATFORM says otherwise."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

PHASES = ('model', 'plant', 'production', 'consumption', 'economics', 'report')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--language', default='', help="'' the desktop's (as the program starts), 'en', 'it'")
    parser.add_argument('--timeout', type=float, default=900, help='seconds for the year and for the report')
    parser.add_argument('--update', choices=('check', 'install'),
                        help='instead of the year: the update path against MERIDIANA_DEV_RELEASE_API (the notice by '
                             'itself, Help > Check for updates, the download and its checks; with install, Setup too)')
    args = parser.parse_args(argv)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    args.out.mkdir(parents=True, exist_ok=True)
    lines = (args.out / 'check.txt').open('w', encoding='utf-8')
    start = time.perf_counter()

    def say(*words):
        line = f'{time.perf_counter() - start:7.1f} s  ' + ' '.join(str(w) for w in words)
        lines.write(line + '\n')
        lines.flush()
        if sys.stdout is not None:
            print(line, flush=True)

    from PySide6.QtCore import Q_ARG, QEventLoop, QMetaObject, QObject, QTimer

    from meridiana import i18n, model
    from meridiana.quick.app import QuickWindow, create_app
    from meridiana.quick.capture import grab

    def pump(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def wait(predicate, seconds):
        end = time.perf_counter() + seconds
        while not predicate() and time.perf_counter() < end:
            pump(50)
        return predicate()

    result = {'project': str(args.project), 'frozen': bool(getattr(sys, 'frozen', False))}
    app = create_app(language=args.language)
    result.update(language=i18n.language(), platform=app.platformName())
    say('language', result['language'], 'platform', result['platform'])
    project, notice = model.Project.load(args.project)
    host = QuickWindow(project, args.out / 'profile', real_views=True, path=args.project.resolve())
    host.window.show()
    host.window.resize(1600, 960)
    pump(1500)
    say('window shown')

    def shot(name):
        pump(1200)
        grab(host.window).save(str(args.out / f'{name}.png'))
        say('grabbed', name)

    if args.update:
        code = update(host, args, result, say, wait, shot)
        (args.out / 'check.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        lines.close()
        # with install, Setup has been started by now and the window has asked to quit (files_part.install_update):
        # this process ends here as the window's would
        host.close()
        return code
    host.bridge.recompute()
    bridge = host.bridge
    told = [time.perf_counter()]

    def computed():
        if time.perf_counter() - told[0] > 20:
            told[0] = time.perf_counter()
            say('  computing:', 'busy' if bridge._busy else 'idle', repr(bridge._error),
                {k: v for k, v in (getattr(bridge, '_progress', None) or {}).items() if not isinstance(v, (list, dict))})
        return not bridge._busy and ((bridge.session.energy and not bridge.session.year_outdated()) or bridge._error)
    wait(computed, args.timeout)
    sim = (bridge.session.energy or {}).get('sim')
    year = sim is not None
    result['kwh'] = float(getattr(sim, 'energy_kwh', None) or 0) if year else None
    result['year_error'] = bridge._error
    result['year_note'] = bridge._year_note
    result['year_s'] = round(time.perf_counter() - start, 1)
    say('year', 'computed' if year else 'NOT computed', result['kwh'], repr(bridge._error), repr(bridge._year_note))
    for phase in PHASES:
        QMetaObject.invokeMethod(host.window, 'showPhase', Q_ARG('QVariant', phase))
        shot(f'phase-{phase}')
    part = host.parts.controllers['filePart']
    part.show_file('open')
    shot('file')
    for section in ('appearance', 'privacy', 'report'):
        part.show_file('preferences:' + section)
        shot(f'settings-{section}')
    part.closeFile()
    pump(500)
    host.window.setProperty('helpOpen', True)
    shot('meridio')
    host.window.setProperty('helpOpen', False)
    report = host.parts.controllers['report']
    written, failed = [], []
    report.completed.connect(written.append)
    report.failed.connect(failed.append)
    target = args.out / 'report.pdf'
    report.exportPdf(str(target))
    wait(lambda: written or failed or target.is_file(), args.timeout)
    pump(500)
    result['report'] = target.is_file() and target.stat().st_size or 0
    result['report_error'] = failed[:1]
    say('report', result['report'], failed[:1])
    result['warnings'] = host.warnings[:50]
    result['total_s'] = round(time.perf_counter() - start, 1)
    host.close()
    (args.out / 'check.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    say('done', json.dumps({k: result[k] for k in ('language', 'kwh', 'report', 'total_s')}))
    lines.close()
    return 0 if year and result['report'] else 1


def update(host, args, result, say, wait, shot):
    """The update as the window does it: the notice of the check by itself (update_check.py, after
    MERIDIANA_DEV_UPDATE_DELAY_MS), then what Help > Check for updates does (dialogs.checkUpdate, downloadUpdate);
    with --update install, the verified installer is handed to the window, which starts Setup and quits."""
    from meridiana import __version__, updates
    result['version'] = __version__
    result['installed_build'] = updates.installed_build()
    noticed = wait(lambda: 'available' in host.shell._notice or 'disponibile' in host.shell._notice, 60)
    result['notice'] = host.shell._notice
    say('notice', repr(host.shell._notice))
    shot('update-notice')
    part = host.parts.controllers['filePart']
    dialogs = part.dialogs
    ready = []
    if args.update == 'check':
        dialogs.installerReady.disconnect(part.install_update)
    dialogs.installerReady.connect(ready.append)
    part.openDialog('update')
    dialogs.checkUpdate()
    wait(lambda: not dialogs._busy, 60)
    result['offer'] = {k: dialogs._state.get(k) for k in ('title', 'hasInstaller', 'releaseUrl')}
    result['check_status'] = dialogs._status
    say('offer', result['offer'], repr(dialogs._status))
    shot('update-dialog')
    if not dialogs._state.get('hasInstaller'):
        return 1
    dialogs.downloadUpdate()
    wait(lambda: not dialogs._busy, 300)
    result['download_status'] = dialogs._status
    result['installer'] = ready[:1]
    say('download', ready[:1], repr(dialogs._status))
    shot('update-downloaded')
    if args.update == 'install' and ready:
        wait(lambda: False, 2)          # the save's guard and the start of Setup
        result['setup_started'] = True
    return 0 if noticed and ready else 1


if __name__ == '__main__':
    sys.exit(main())
