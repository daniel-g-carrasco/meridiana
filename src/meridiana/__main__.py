"""Entry point: `meridiana --version` and `--help` answer from the command
line, `--self-test [REPORT]` checks the program offscreen (ui/selftest.py,
the packages' smoke test), anything else starts the app (a file given on
the command line is opened in the window)."""

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
        print(_("usage: {command} [PROJECT]").format(command=__package__.replace("_", "-")))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        from .ui.selftest import main as self_test
        return self_test(sys.argv[2:])
    from .app import main as app_main
    return app_main(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
