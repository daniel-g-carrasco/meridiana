"""Quick assistant behaviour, provider parity and real-window evidence."""
import os

# Both must precede the first Quick engine, including isolated component tests.
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
