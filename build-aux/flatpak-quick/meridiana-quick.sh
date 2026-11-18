#!/bin/sh
# /app/bin/meridiana in the Quick Flatpak (build-aux/flatpak-quick): the Qt Quick window with the Qt of the
# PySide6 6.12 wheels.
# The KDE runtime points QT_PLUGIN_PATH and the QML import paths at its own Qt 6.11: Qt puts QT_PLUGIN_PATH before
# its own plugins, so the 6.12 libraries would load 6.11 platform plugins. Cleared here, also for the processes the
# window starts (the computation and the report run `python3 -m meridiana.quick.backend...`).
unset QT_PLUGIN_PATH QML2_IMPORT_PATH QML_IMPORT_PATH
export PYTHONPATH="/app/share/meridiana/src${PYTHONPATH:+:$PYTHONPATH}"
case "$1" in
    --version|-V|--self-test|--kokoro-worker)
        exec python3 /app/share/meridiana/bin/meridiana "$@" ;;
    --widgets)
        # bin/meridiana opens the Quick by itself (R542): the option goes on to it
        exec python3 /app/share/meridiana/bin/meridiana "$@" ;;
esac
# the Quick window keeps its preferences and caches in a folder of its own (--profile); a later --profile wins
exec python3 -m meridiana.quick --profile "${XDG_DATA_HOME:-$HOME/.local/share}/meridiana-quick" "$@"
