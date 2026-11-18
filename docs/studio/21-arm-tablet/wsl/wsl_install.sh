#!/bin/bash
# Study 21 (R87): install the aarch64 user-mode emulation and podman in the WSL openSUSE, as root.
set -x
date
zypper --non-interactive install qemu-linux-user podman 2>&1 | tail -15
echo "--- binfmt after install"
systemctl restart systemd-binfmt 2>&1
ls /proc/sys/fs/binfmt_misc/
cat /proc/sys/fs/binfmt_misc/qemu-aarch64 2>/dev/null
ls -la /usr/bin/qemu-aarch64* 2>/dev/null
podman --version
echo "--- flathub remote and aarch64 runtime"
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo 2>&1
flatpak remote-info --arch=aarch64 flathub org.kde.Platform//6.11 2>&1 | head -12
flatpak remote-info --arch=aarch64 flathub org.kde.Sdk//6.11 2>&1 | head -5
flatpak remote-info --arch=aarch64 flathub io.qt.PySide.BaseApp//6.11 2>&1 | head -8
flatpak remote-info --arch=x86_64 flathub io.qt.PySide.BaseApp//6.11 2>&1 | head -8
flatpak remote-ls --arch=aarch64 flathub 2>&1 | grep -E "org.kde.(Platform|Sdk)|io.qt.PySide" | head -20
date
