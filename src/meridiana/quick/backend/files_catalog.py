"""File's browsing catalogue never chooses a product for the project."""
from PySide6.QtCore import Slot
from .catalog import CatalogBackend


class BrowseCatalog(CatalogBackend):
    @Slot()
    def choose(self):
        # In browse mode Enter and double click leave the project untouched.
        return

    @Slot(str)
    def readProduct(self, url):
        self.beginEdit(False)
        self.importPvsystInto(url)
