#!/bin/bash
# Study 21 (R87): build the aarch64 image and run Meridiana's imports, the pipeline test and the self-test in it.
# Run as root in the WSL openSUSE: bash run_arm64.sh
set -x
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO=/mnt/c/Users/Grasso/dev/meridiana-integra-kimi-9-10
OUT="$HERE/out"
mkdir -p "$OUT"
date
podman run --rm --arch arm64 docker.io/library/python:3.12-slim-trixie sh -c 'uname -m; python -c "import platform,sys;print(platform.machine(), sys.version)"; ldd --version | head -1'
date
time podman build --arch arm64 -t meridiana-arm64 -f "$HERE/Containerfile" "$HERE" 2>&1 | tail -40
date
RUN="podman run --rm --arch arm64 -v $REPO:/src:ro -v $OUT:/out -w /src -e PYTHONUTF8=1 -e QT_QPA_PLATFORM=offscreen -e PYTHONPATH=/src/tests:/src/src -e LANGUAGE=en -e HOME=/tmp meridiana-arm64"
echo "=== imports"
time $RUN python -c "
import platform, sys, time
t = time.perf_counter()
import numpy, scipy, pandas, shapely, pvlib, matplotlib, pyqtgraph
from PySide6 import QtCore, QtWidgets, QtQuick3D, QtQuickWidgets
print('machine', platform.machine(), 'python', sys.version.split()[0])
print('qt', QtCore.qVersion(), 'numpy', numpy.__version__, 'scipy', scipy.__version__, 'pandas', pandas.__version__, 'pvlib', pvlib.__version__, 'shapely', shapely.__version__)
import meridiana
print('meridiana', meridiana.__version__)
print('imports in %.1f s' % (time.perf_counter() - t))
"
echo "=== pipeline test (calcoli, no Qt)"
time $RUN python -m unittest -v tests.calcoli.test_pipeline 2>&1 | tail -15
echo "=== a small offscreen window test (widget)"
time $RUN python -m unittest -v tests.finestra.test_selection_3d 2>&1 | tail -15
echo "=== self-test"
time $RUN python -m meridiana --self-test /out/self-test-aarch64.txt 2>&1 | tail -40
date
