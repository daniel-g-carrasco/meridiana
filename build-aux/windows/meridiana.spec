# -*- mode: python ; coding: utf-8 -*-
# The Windows bundle of Meridiana: PyInstaller 6.22 with the Python of python.org (3.12) in a venv of its own with
# requirements.txt, where Qt comes as its three wheels (PySide6_Essentials, _Addons, _Pdf: no WebEngine). From the
# repository root:
#   python tools/compile_po.py                 (msgfmt, or the compiler of that file where there is none)
#   python tools/make_ico.py
#   pyinstaller --noconfirm build-aux/windows/meridiana.spec
#   dist\Meridiana\Meridiana.exe --self-test report.txt          (offscreen; 0 when every check passed)
# A folder, never one file: a single exe would unpack some 400 MB at every start.
#
# What goes in: the program; Qt Quick 3D and the QML modules the 3D scene imports; QtPdf, QtSvg, QtMultimedia and
# QtTextToSpeech (Meridio's voices: the system's through SAPI or WinRT); Qt's own translations in Italian and
# English; matplotlib for the formulas and the report (Agg only), pvlib with the tables its functions read at run
# time, scipy, shapely, pyqtgraph, requests, anthropic and keyring; Meridiana's catalogues (share/locale), icons and
# fonts (share/), the manual (share/manuale), the 3D scene and the product catalogue (next to their modules), and
# Kokoro's worker as a script another Python can run (assistant/kokoro_worker.py: the voice's model and
# onnxruntime are not shipped, speech.worker_python).
#
# What is left out: the Qt modules Meridiana does not use, which the QML hook would bring for their QML plugins
# (Qt 3D, Charts, Graphs, Data Visualization, Location, Positioning, Web*, Sensors, Scxml, Remote Objects, the
# virtual keyboard, Quick 3D's physics, XR, particles and asset tools, the designer), FFmpeg (the Windows media backend
# plays the voice's sound), Qt's OpenSSL (Schannel does TLS), the QML debugger, the Direct2D platform, the mock voice
# of the tests and every translation but Italian and English. A part
# left out comes back by itself when a binary kept imports it (prune() reads the import tables): pruning never
# breaks a library, at worst it keeps it.
import re
import sys
from pathlib import Path

import pefile

ROOT = Path(SPECPATH).parent.parent
SRC = ROOT / 'src' / 'meridiana'

if not (ROOT / 'locale' / 'it' / 'LC_MESSAGES' / 'meridiana.mo').is_file():
    sys.exit('locale/ is missing: run python tools/compile_po.py first (the bundle would speak English only)')
if not (ROOT / 'build-aux' / 'windows' / 'meridiana.ico').is_file():
    sys.exit('build-aux/windows/meridiana.ico is missing: run python tools/make_ico.py first')

import pvlib  # noqa: E402  (the venv's: its tables)

PVLIB_TABLES = Path(pvlib.__file__).parent / 'data'

datas = [
    (str(ROOT / 'data' / 'icons'), 'share/icons'),
    (str(ROOT / 'data' / 'fonts'), 'share/fonts'),
    (str(ROOT / 'data' / 'natural_earth'), 'share/natural_earth'),
    (str(ROOT / 'data' / 'istat'), 'share/istat'),
    (str(ROOT / 'docs' / 'manuale'), 'share/manuale'),          # read inside the program (help.manual_dir)
    (str(ROOT / 'locale'), 'share/locale'),
    (str(SRC / 'ui' / 'qml'), 'meridiana/ui/qml'),              # view3d.QML_FILE, next to its module
    (str(SRC / 'catalog' / 'data'), 'meridiana/catalog/data'),  # catalog.DATA
    (str(SRC / 'assistant' / 'kokoro_worker.py'), 'meridiana/assistant'),
]
# pvlib's tables read at run time (the Linke turbidity of the Ineichen sky, the altitude of a place, the reference
# spectrum); not its copies of the CEC and Sandia libraries (Meridiana has its own catalogue) nor its sample years
datas += [(str(PVLIB_TABLES / name), 'pvlib/data') for name in ('LinkeTurbidities.h5', 'Altitude.h5', 'ASTMG173.csv')]

a = Analysis(
    [str(Path(SPECPATH) / 'meridiana_main.py')],
    pathex=[str(ROOT / 'src')],
    datas=datas,
    # pyqtgraph comes with its data and its Qt templates through hook-pyqtgraph of pyinstaller-hooks-contrib;
    # keyring finds its Windows backend by entry point (hook-keyring)
    hiddenimports=['keyring.backends.Windows'],
    hooksconfig={'matplotlib': {'backends': ['Agg']}},
    excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
              'PySide6.Qt3DCore', 'PySide6.QtCharts', 'PySide6.QtGraphs', 'PySide6.QtDataVisualization',
              'PySide6.QtLocation', 'PySide6.QtPositioning', 'PySide6.QtDesigner', 'PySide6.QtTest',
              # Kokoro's worker runs in another Python (speech.worker_python): its libraries stay out
              'kokoro_onnx', 'onnxruntime', 'phonemizer', 'espeakng_loader',
              'IPython', 'pytest', 'sphinx'],
)

# -- what the QML hook and the Qt hooks bring and Meridiana does not use ------------------------------------------
QML = 'PySide6/qml/'
QML_LEFT_OUT = ('Qt3D', 'Qt5Compat', 'QtCharts', 'QtDataVisualization', 'QtGraphs', 'QtLocation', 'QtMultimedia',
                'QtPositioning', 'QtRemoteObjects', 'QtScxml', 'QtSensors', 'QtTest', 'QtTextToSpeech', 'QtWebChannel',
                'QtWebEngine', 'QtWebSockets', 'QtWebView', 'QtQuick/VirtualKeyboard', 'QtQuick/Scene2D',
                'QtQuick/Scene3D', 'QtQuick/LocalStorage', 'QtQuick3D/Physics', 'QtQuick3D/Xr',
                'QtQuick3D/SpatialAudio', 'QtQuick3D/Particles3D', 'QtQuick3D/ParticleEffects',
                'QtQuick3D/MaterialEditor', 'QtQuick3D/lightmapviewer', 'QtQuick3D/AssetUtils', 'QtQuick/Pdf',
                'QtQml/StateMachine', 'QtQml/XmlListModel')
PLUGINS_LEFT_OUT = ('qmltooling', 'assetimporters', 'sceneparsers', 'geometryloaders', 'renderers', 'renderplugins',
                    'geoservices', 'position', 'sensors', 'canbus', 'sqldrivers', 'designer', 'webview',
                    'scxmldatamodel', 'texttospeech/qtexttospeech_mock', 'multimedia/ffmpegmediaplugin',
                    'platforminputcontexts/qtvirtualkeyboardplugin', 'platforms/qdirect2d', 'tls/qopensslbackend')
DLL_LEFT_OUT = re.compile(r'^(qt63d|qt6(charts|datavisualization|graphs|location|positioning|webengine|webchannel|'
                          r'websockets|webview|designer|sensors|scxml|statemachine|remoteobjects|virtualkeyboard|'
                          r'bluetooth|nfc|serialbus|serialport|httpserver|help|spatialaudio|quick3dphysics|quick3dxr|'
                          r'quick3dparticle|quick3dspatialaudio|quick3dassetimport|quick3dassetutils|pdfquick|qmlxmllistmodel)|'
                          r'(avcodec|avformat|avutil|swresample|swscale)-\d+\.dll$)', re.I)
TRANSLATION = re.compile(r'^PySide6/translations/.*\.qm$', re.I)


def left_out(dest: str) -> bool:
    d = dest.replace('\\', '/')
    name = d.rsplit('/', 1)[-1]
    if d.startswith(QML):
        return any(d[len(QML):] == m or d[len(QML):].startswith(m + '/') for m in QML_LEFT_OUT)
    if d.startswith('PySide6/plugins/'):
        rest = d[len('PySide6/plugins/'):]
        return any(rest == p or rest.startswith(p + '/') or rest.startswith(p + '.') for p in PLUGINS_LEFT_OUT)
    if TRANSLATION.match(d):
        return not re.search(r'_(it|en)\.qm$', name, re.I)
    if name.lower() in ('libssl-3-x64.dll', 'libcrypto-3-x64.dll'):     # Qt's OpenSSL: Qt uses Schannel here
        return True
    return d.startswith('PySide6/') and bool(DLL_LEFT_OUT.match(name))


def imports(path: str) -> set:
    """The DLLs a binary loads by its import tables (and the delayed ones), lower case."""
    try:
        pe = pefile.PE(path, fast_load=True)
    except (pefile.PEFormatError, OSError):
        return set()
    try:
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
                                               pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT']])
        found = getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []) + getattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT', [])
        return {e.dll.decode('ascii', 'replace').lower() for e in found}
    finally:
        pe.close()


def prune(binaries, datas):
    """The entries left out, but for those a binary kept still imports (followed until nothing changes)."""
    out = [e for e in binaries if left_out(e[0])]
    kept = [e for e in binaries if not left_out(e[0])]
    needed = set()
    for e in kept:
        needed |= imports(e[1])
    while True:
        back = [e for e in out if Path(e[0]).name.lower() in needed]
        if not back:
            break
        for e in back:
            print(f'meridiana.spec: kept, a binary kept imports it: {e[0]}')
            out.remove(e)
            kept.append(e)
            needed |= imports(e[1])
    dropped = [e for e in datas if left_out(e[0])]
    print(f'meridiana.spec: left out {len(out)} binaries ({sum(Path(e[1]).stat().st_size for e in out) / 2**20:.1f} MB) '
          f'and {len(dropped)} data files')
    return kept, [e for e in datas if not left_out(e[0])]


a.binaries, a.datas = prune(a.binaries, a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='Meridiana',
    console=False,
    icon=str(ROOT / 'build-aux' / 'windows' / 'meridiana.ico'),
    manifest=str(Path(SPECPATH) / 'meridiana.manifest'),
    version=None,
)

coll = COLLECT(exe, a.binaries, a.datas, name='Meridiana')
