"""Entry point: `meridiana --version` and `--help` answer from the command
line, `--self-test [REPORT]` checks the program offscreen (ui/selftest.py,
the packages' smoke test), anything else opens the Qt Quick window (quick/app.py;
a file given on the command line is opened in it). The old Widgets window
(app.py), frozen since 07/11/2026 (R542), opens only with `--widgets`, and
`--tour [STEP|new]` is its guided tour (tour.py)."""

import os
import sys

from . import __version__, i18n


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
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        print(__version__)
        return 0
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        from .i18n import _
        command = __package__.replace("_", "-")
        print(_("usage: {command} [PROJECT]").format(command=command))
        print(_("  --widgets [PROJECT]  the old Widgets window, frozen: no new work goes there (the Qt Quick "
                "window opens without it)"))
        print(_("  --tour [STEP|new]    start with the guided tour at STEP (its number or name; the first when "
                "omitted); «new» pretends it is the first start. Your own settings are never touched."))
        print(_("  --self-test [REPORT] check the program without a screen and write a report"))
        print(_("  --version, -V        print the version"))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        from .ui.selftest import main as self_test
        return self_test(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "--kokoro-worker":
        # Meridio's voice in a process of its own: the Windows package runs itself with this option
        # (quick/backend/settings.py, assistant/speech.py)
        from .assistant.kokoro_worker import main as voice_worker
        return voice_worker(sys.argv[2:])
    if "--widgets" in sys.argv[1:] or (len(sys.argv) > 1 and sys.argv[1] == "--tour"):
        # R542: the Widgets window, frozen (the guided tour is its own)
        from .app import main as app_main
        return app_main([a for a in sys.argv if a != "--widgets"])
    from .quick import app as quick
    if getattr(sys, "frozen", False) and "--profile" not in sys.argv[1:]:
        # the Windows package: the Quick's preferences and caches in the user's folder, not next to the program (the
        # Flatpak's launcher gives its own, a source checkout keeps build/quick-runtime)
        from .paths import Paths
        sys.argv[1:1] = ["--profile", str(Paths.from_env().data / "quick")]
    return quick.main()


if __name__ == "__main__":
    sys.exit(main())
