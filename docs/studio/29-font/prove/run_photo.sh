#!/bin/bash
# usage: run_photo.sh <variant> <scale> <theme>
S=/c/Users/Grasso/AppData/Local/Temp/claude/c--Users-Grasso-Elettrico/ac24d128-fcc4-4bd8-9c13-8ce732bbae55/scratchpad
v=$1; sc=$2; th=$3
mkdir -p $S/fontout/cfg
w=$((1500*sc)); h=$((960*sc))
cat > $S/fontout/cfg/s$sc.json <<J
{"synchronousWindowSystemEvents": true, "windowFrameMargins": false, "screens": [{"name": "s", "x": 0, "y": 0, "width": $w, "height": $h, "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}
J
cd /c/Users/Grasso/dev/meridiana-wt-r10-font
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONPATH="tests;src" PATH="/c/Users/Grasso/dev/meridiana/.venv/Lib/site-packages/PySide6:$PATH"
export QT_SCALE_FACTOR=$sc
export QT_QPA_PLATFORM="offscreen:configfile=../../AppData/Local/Temp/claude/c--Users-Grasso-Elettrico/ac24d128-fcc4-4bd8-9c13-8ce732bbae55/scratchpad/fontout/cfg/s$sc.json"
/c/Users/Grasso/dev/meridiana/.venv/Scripts/python.exe $S/fontscripts/photo.py $v $sc $th $S/fontout/photos "$(cygpath -w $S/fontloc)" 2>&1 | tail -15
