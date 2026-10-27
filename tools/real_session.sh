#!/usr/bin/env bash
# Run one command on a private, headless GNOME Wayland display.
set -uo pipefail

if [[ "${1:-}" == "--inside" ]]; then
    shift
else
    if [[ $# -eq 0 ]]; then
        echo "Usage: $0 command [argument ...]" >&2
        exit 2
    fi
    root=$(mktemp -d /tmp/meridiana-real-session-XXXXXX) || exit 1
    export REAL_SESSION_ROOT="$root"
    export XDG_RUNTIME_DIR="$root/runtime"
    mkdir -m 700 -p "$XDG_RUNTIME_DIR" || exit 1
    exec dbus-run-session -- "$0" --inside "$@"
fi

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 command [argument ...]" >&2
    exit 2
fi

root="$REAL_SESSION_ROOT"
display="${REAL_SESSION_DISPLAY:-meridiana-prova-$$}"
size="${REAL_SESSION_SIZE:-1600x1000}"
runtime="$XDG_RUNTIME_DIR"
socket="$runtime/$display"
log="$root/compositor.log"
shell_pid=""
ready=0

export REAL_SESSION_ROOT="$root"
export WAYLAND_DISPLAY="$display"
export QT_QPA_PLATFORM=wayland
export QT_QPA_PLATFORMTHEME="${QT_QPA_PLATFORMTHEME:-gtk3}"
export XDG_CURRENT_DESKTOP=GNOME
export XDG_CONFIG_HOME="$root/config"
export XDG_STATE_HOME="$root/state"
export XDG_CACHE_HOME="$root/cache"
export XDG_DATA_HOME="$root/data"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME" "$XDG_DATA_HOME"

cleanup() {
    status=$?
    trap - EXIT INT TERM
    if [[ -n "$shell_pid" ]] && kill -0 "$shell_pid" 2>/dev/null; then
        kill -TERM "$shell_pid" 2>/dev/null || true
        for _ in {1..50}; do
            kill -0 "$shell_pid" 2>/dev/null || break
            sleep 0.1
        done
        kill -KILL "$shell_pid" 2>/dev/null || true
    fi
    if [[ -n "$shell_pid" ]]; then
        wait "$shell_pid" 2>/dev/null || true
    fi
    if [[ $status -ne 0 && -s "$log" ]]; then
        echo "----- ${compositor:-compositor} ($display) -----" >&2
        command cat "$log" >&2
    fi
    for mount in "$runtime/doc" "$runtime/gvfs"; do
        mountpoint -q "$mount" 2>/dev/null && fusermount3 -uz "$mount" 2>/dev/null || true
    done
    rm -rf -- "$root"
    exit "$status"
}
trap cleanup EXIT INT TERM

options=(--headless --wayland --virtual-monitor "$size" --wayland-display "$display")
if [[ "${REAL_SESSION_DISPLAY_SERVER:-0}" == "1" ]]; then
    options+=(--display-server)
fi
if [[ -n "${REAL_SESSION_COMPOSITOR:-}" ]]; then
    compositor="$REAL_SESSION_COMPOSITOR"
elif command -v mutter >/dev/null 2>&1; then
    compositor=mutter
else
    compositor=gnome-shell
fi
"$compositor" "${options[@]}" >"$log" 2>&1 &
shell_pid=$!
for _ in {1..200}; do
    if [[ -S "$socket" ]]; then
        ready=1
        break
    fi
    if ! kill -0 "$shell_pid" 2>/dev/null; then
        break
    fi
    sleep 0.1
done
if [[ $ready -ne 1 ]]; then
    echo "The hidden Wayland display $display did not become ready." >&2
    exit 1
fi

# The private compositor needs no desktop portal. On this host its GTK backend
# can leave even a minimal QApplication waiting for several D-Bus timeouts.
# Keep the bus available only when a caller explicitly asks to exercise it.
if [[ "${REAL_SESSION_DBUS:-0}" == "1" ]]; then
    "$@"
else
    env -u DBUS_SESSION_BUS_ADDRESS -u DBUS_SESSION_BUS_WINDOWID "$@"
fi
