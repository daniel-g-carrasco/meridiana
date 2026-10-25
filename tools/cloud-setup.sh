#!/bin/bash
# Setup script for Meridiana's environment on claude.ai/code (cloud sessions of Claude Code): paste it in the
# environment's settings, with the variable QT_QPA_PLATFORM=offscreen and the "Trusted" network.
# It runs as root on Ubuntu before the session starts, and the machine is kept as a snapshot. The system
# libraries are the CI's (Qt offscreen, gettext); the Python packages are those of requirements.txt, written
# out because the repository may not be cloned yet when this runs: keep the two lists the same.
set -euo pipefail
apt-get update -q
apt-get install -y -q gettext desktop-file-utils appstream libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3
python3 -m pip install -q --break-system-packages \
    "PySide6_Essentials==6.12.0" "PySide6_Addons==6.12.0" "PySide6_Pdf==6.12.0.140" "shapely>=2.0" \
    "numpy>=1.26" "pandas>=2.2" "requests>=2.31" "pvlib==0.16.1" "scipy>=1.15" "matplotlib>=3.9" "pyqtgraph>=0.14" \
    "pypdf>=6.0" "anthropic>=2.3" "keyring>=25.7" "ifcopenshell>=0.9.0.post1" ruff polib
