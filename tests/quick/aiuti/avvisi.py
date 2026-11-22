"""The QML warnings a test asserts empty, without the one loss of Qt's that the program mends by itself.

A results page is made a slice at a time while hidden (Workbench.qml warms the pages of the other phases); when
something of it is taken apart between two slices, Qt throws a result tile away half made and says so twice
(«Cannot create delegate», «Object or context destroyed during incubation»). ResultsPage.mendTiles makes the tiles
again when one is still missing (R625), and the user sees the page whole. On the CI's runner (two cores, software
OpenGL) it came now and then in tests that are about something else (22/11/2026): those two lines, of
ResultsPage.qml only, are left out; any other warning, and the same lines of another file, still fail."""
from __future__ import annotations

MENDED = ('QML Component: Cannot create delegate', 'Object or context destroyed during incubation')


def real(warnings) -> list:
    return [w for w in warnings if not ('/Charts/ResultsPage.qml' in str(w) and any(m in str(w) for m in MENDED))]
