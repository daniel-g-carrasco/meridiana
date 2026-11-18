"""R554: the decorative models of the 3D view (scene.SceneBackend._decorated) as rows that stay.

The 3D view drew them with a Repeater3D over a list made again at every change of the objects: each change made the
Models again, and when the last Model of a catalogue model left the scene its shared mesh (one SceneGeometry per model,
scene._asset_geometry) left with it. Qt Quick 3D gave the mesh back to the scene without its data: the objects of
that model drew nothing until the mesh was written again (Daniel 08/11/2026, «gli oggetti 3d che inserisco
scompaiono»; seen on a real Wayland display). Here a model of the catalogue has one row from the first object drawn
with it to the end of the session: a change writes the row's instance table and count, the Model stays, its mesh
with it. A model no object uses any more keeps its row, with an empty table, hidden."""
from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, QUrl

NAME, GEOMETRY, SOURCE, COUNT = range(Qt.ItemDataRole.UserRole + 1, Qt.ItemDataRole.UserRole + 5)
FIELDS = {NAME: 'name', GEOMETRY: 'geometry', SOURCE: 'source', COUNT: 'count'}


class DecorationSlots(QAbstractListModel):
    """Rows {name, geometry, source, count}: Shell's Viewport.qml binds slotName, slotGeometry, slotSource, slotCount."""

    def __init__(self, parent, empty: QUrl):
        super().__init__(parent)
        self._rows: list[dict] = []
        self._empty = empty          # an instance table of no rows

    def roleNames(self):
        return {NAME: QByteArray(b'slotName'), GEOMETRY: QByteArray(b'slotGeometry'),
                SOURCE: QByteArray(b'slotSource'), COUNT: QByteArray(b'slotCount')}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows) or role not in FIELDS:
            return None
        return self._rows[index.row()][FIELDS[role]]

    def names(self) -> list[str]:
        return [row['name'] for row in self._rows]

    def show(self, decorations: list[dict]) -> None:
        """The decorations of the scene now (scene._decorations): the rows of the models they use get their table, the
        others an empty one; a model drawn for the first time gets a row at the end."""
        wanted = {d['name']: d for d in decorations}
        for i, row in enumerate(self._rows):
            d = wanted.pop(row['name'], None)
            source, count = (d['source'], d['count']) if d is not None else (self._empty, 0)
            if row['source'] != source or row['count'] != count:
                row['source'], row['count'] = source, count
                here = self.index(i)
                self.dataChanged.emit(here, here, [SOURCE, COUNT])
        if wanted:
            first = len(self._rows)
            self.beginInsertRows(QModelIndex(), first, first + len(wanted) - 1)
            self._rows.extend({'name': d['name'], 'geometry': d['geometry'], 'source': d['source'], 'count': d['count']}
                              for d in wanted.values())
            self.endInsertRows()
