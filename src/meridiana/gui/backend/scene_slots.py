"""R554: the decorative models of the 3D view (scene.SceneBackend._decorated) as rows that stay.

The 3D view drew them with a Repeater3D over a list made again at every change of the objects: each change made the
Models again, and when the last Model of a catalogue model left the scene its shared mesh (one SceneGeometry per model,
scene._asset_geometry) left with it. Qt Quick 3D gave the mesh back to the scene without its data: the objects of
that model drew nothing until the mesh was written again (Daniel 08/11/2026, «gli oggetti 3d che inserisco
scompaiono»; seen on a real Wayland display). Here a model of the catalogue has one row from the first object drawn
with it to the end of the session: a change writes the row's instance table and count, the Model stays, its mesh
with it. A model no object uses any more keeps its row, with an empty table, hidden.

R575 D3: the pieces of an imported IFC model's true geometry (scene_context.IfcContext) the same way, ContextSlots."""
from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, QUrl
from PySide6.QtGui import QVector3D

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

    def rowCount(self, parent=QModelIndex()):     # noqa: B008 - the invalid index, never changed: Qt's own default
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


PIECE_NAME, PIECE_GEOMETRY, PIECE_COLOUR, PIECE_POSITION, PIECE_TURN, PIECE_SHOWN = range(
    Qt.ItemDataRole.UserRole + 1, Qt.ItemDataRole.UserRole + 7)
PIECE_FIELDS = {PIECE_NAME: 'name', PIECE_GEOMETRY: 'geometry', PIECE_COLOUR: 'colour', PIECE_POSITION: 'position',
                PIECE_TURN: 'turn', PIECE_SHOWN: 'shown'}


class ContextSlots(QAbstractListModel):
    """R575 D3: the pieces of the IFC model's true geometry as rows that stay, one for each piece of the file shown.

    The 3D view drew them with a Repeater3D over scene_context.IfcContext.entries, a list made again at every change
    of the geometry, the sub-fields or a layout: every change made the 29 Models of a real model again on the same
    meshes, and the meshes left the scene with their last Models and came back empty (seen on a real screen: after
    one change 0.1 % of the model was drawn, R575). Here a piece keeps its row, and its Model, while the same file is
    shown: a change writes only its position, turn and whether it is shown. Another file (or other storeys left out)
    gives other pieces: the rows are made again then, once.
    Rows {name, geometry, colour, position, turn, shown}: Viewport.qml binds pieceName, pieceGeometry, pieceColour,
    piecePosition, pieceTurn, pieceShown."""

    def __init__(self, parent):
        super().__init__(parent)
        self._rows: list[dict] = []

    def roleNames(self):
        return {PIECE_NAME: QByteArray(b'pieceName'), PIECE_GEOMETRY: QByteArray(b'pieceGeometry'),
                PIECE_COLOUR: QByteArray(b'pieceColour'), PIECE_POSITION: QByteArray(b'piecePosition'),
                PIECE_TURN: QByteArray(b'pieceTurn'), PIECE_SHOWN: QByteArray(b'pieceShown')}

    def rowCount(self, parent=QModelIndex()):     # noqa: B008 - the invalid index, never changed: Qt's own default
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows) or role not in PIECE_FIELDS:
            return None
        return self._rows[index.row()][PIECE_FIELDS[role]]

    def names(self) -> list[str]:
        return [row['name'] for row in self._rows]

    def shown(self) -> bool:
        """A piece of the model is shown (the measuring tool's probe then gives no point through it to the ground)."""
        return any(row['shown'] for row in self._rows)

    def show(self, entries: list[dict]) -> None:
        """The pieces as IfcContext.entries gives them now; [] when there is nothing to show (no model, the frame
        lost): the rows stay, hidden."""
        if entries and [(e['name'], e['geometry']) for e in entries] != [(r['name'], r['geometry']) for r in self._rows]:
            self.beginResetModel()
            self._rows = [self._row(e) for e in entries]
            self.endResetModel()
            return
        for i, row in enumerate(self._rows):
            new = self._row(entries[i]) if entries else {**row, 'shown': False}
            roles = [role for role, key in PIECE_FIELDS.items() if role != PIECE_GEOMETRY and new[key] != row[key]]
            if roles:
                self._rows[i] = new
                here = self.index(i)
                self.dataChanged.emit(here, here, roles)

    @staticmethod
    def _row(entry: dict) -> dict:
        x, y, z = (float(v) for v in entry['position'])
        return {'name': entry['name'], 'geometry': entry['geometry'], 'colour': [float(c) for c in entry['colour']],
                'position': QVector3D(x, y, z), 'turn': float(entry['turn']), 'shown': True}
