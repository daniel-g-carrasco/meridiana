"""Independent Qt Quick interface. No user settings or project writes on import."""
import os

# Qt reads this before the first Quick window, including a standalone gallery.
# Its software partial-update path leaves stale physical pixels after a DPR 2
# resize. GPU renderers do not use this option. An explicit diagnostic override
# remains possible, so the regression can still demonstrate the faulty path.
os.environ.setdefault('QSG_SOFTWARE_RENDERER_FORCE_PARTIAL_UPDATES', '0')
