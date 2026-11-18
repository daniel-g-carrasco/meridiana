"""The report without Qt (R314, study 24, sketch V1 «Cornice»): the chapters as data (chapters.py, compose.py), the look
in a Typst file of its own (template.typ), the compilation in a temporary folder (engine.py). The interface hands in
the project, the data of the year, the author's profile and, where it can make them, the 3D pictures; ui/report.py
does that for the Qt window, and any other interface can do the same."""

from .compose import Composed, Picture, compose
from .engine import Build, EngineMissing, available, self_check

__all__ = ["Build", "Composed", "EngineMissing", "Picture", "available", "compose", "self_check"]
