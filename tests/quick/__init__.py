"""The tests of the Qt Quick interface.

Importing the package installs the Quick's common base (tests/_setup.quick_isolation, r23-f8): one QApplication for
the run, every module and every test starting from the same state, what a module leaves taken apart before the next."""
import _setup

_setup.quick_isolation()
