"""Entry point: `meridiana --version` and `--help` answer from the command line, anything else opens the Qt Quick
window (gui/application.py; a file given on the command line is opened in it, or handed to the Meridiana already running).
`--kokoro-worker` is Meridio's voice in a process of its own. A package is checked with
`-m meridiana.gui.package_check PROJECT OUT` (the Windows package runs a module of its own with -m:
build-aux/windows/meridiana_main.py). The Widgets window and its options (`--widgets`, `--tour`, `--self-test`) are
gone with r30-struttura: asked for, they are said gone and nothing is opened."""

import os
import sys

from . import __version__, i18n

GONE = ("--widgets", "--tour", "--self-test")       # the Widgets window's options, until R542 and r30-struttura


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        # a file name the console's code page cannot show must not crash a print
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    if os.environ.get(f"{__package__.upper()}_DEV_STACKS") and not getattr(sys, "frozen", False):
        # developer aid: every thread's stack written to that file every
        # 30 s, to see where an app that seems stuck is (never the built app)
        import faulthandler
        faulthandler.dump_traceback_later(30, repeat=True,
                                          file=open(os.environ[f"{__package__.upper()}_DEV_STACKS"], "w"))
    i18n.setup()
    command = __package__.replace("_", "-")
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(__version__)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        from .i18n import _
        print(_("usage: {command} [PROJECT]").format(command=command))
        print(_("  --version, -V        print the version"))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--kokoro-worker":
        # Meridio's voice in a process of its own: the Windows package runs itself with this option
        # (gui/backend/settings.py, assistant/speech.py)
        from meridiana.app.assistant.kokoro_worker import main as voice_worker
        return voice_worker(sys.argv[2:])
    gone = next((a for a in sys.argv[1:] if a in GONE or a.startswith("--tour=")), None)
    if gone is not None:
        # an old shortcut or script: said, never a window nobody asked for (a script waiting for --self-test to end)
        from .i18n import _
        print(_("{command}: {option} is no longer there: the Qt Quick window is the only one, and a package is "
                "checked with «-m meridiana.gui.package_check PROJECT OUT»").format(
                    command=command, option=gone.partition("=")[0]), file=sys.stderr)
        return 2
    from meridiana.gui import application as quick
    if getattr(sys, "frozen", False) and "--profile" not in sys.argv[1:]:
        # the Windows package: the Quick's preferences and caches in the user's folder, not next to the program (the
        # Flatpak's launcher gives its own, a source checkout keeps build/quick-runtime)
        from meridiana.app.platform.paths import Paths
        sys.argv[1:1] = ["--profile", str(Paths.from_env().data / "quick")]
    return quick.main()


if __name__ == "__main__":
    sys.exit(main())
