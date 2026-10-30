#!/bin/bash
# Study 21 (R87): the aarch64 PySide BaseApp of Flathub run under qemu-user on the x86_64 WSL (as root, is
# root's own flatpak store): does the Python of the runtime import PySide6 and numpy? Measures the download too.
set -x
date
flatpak install --noninteractive --arch=aarch64 flathub org.kde.Platform//6.11 io.qt.PySide.BaseApp//6.11 2>&1 | tail -5
date
flatpak list --arch=aarch64 2>&1
time flatpak run --arch=aarch64 --command=sh io.qt.PySide.BaseApp//6.11 -c 'uname -m; python3 --version; python3 -c "
import platform, time
t = time.perf_counter()
import numpy
from PySide6 import QtCore, QtQuick3D
print(\"machine\", platform.machine(), \"qt\", QtCore.qVersion(), \"numpy\", numpy.__version__, \"in %.1f s\" % (time.perf_counter() - t))
"' 2>&1 | tail -8
date
