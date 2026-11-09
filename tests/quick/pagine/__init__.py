"""Quick File, Settings, Report and dialog journeys."""
import os

# Match create_app before the first isolated QML component is constructed.
# Selecting it only in FilePart.setUpClass is too late in the combined suite.
os.environ.setdefault('QT_QUICK_CONTROLS_STYLE', 'Basic')
