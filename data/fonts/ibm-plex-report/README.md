IBM Plex Sans Condensed, by IBM Corp., SIL Open Font License 1.1 (OFL.txt), unchanged.

The condensed cuts of the report's tables (R460, 06/11/2026): Light, Medium and SemiBold as Google Fonts packs them
(`github.com/google/fonts`, `ofl/ibmplexsanscondensed`). Their names say «Light», «Medium», «SemiBold», which Typst
reads as weights of IBM Plex Sans at 75 % width; the cuts of `../ibm-plex` (from IBM's repository) are named «Cond
SmBld», a family of its own for Typst, and stay for the window (ui/theme.py). Only the report reads this folder
(report_typst/engine.py, REPORT_FONTS).

SHA-256:
3836ed1e1f5c870ddf9fd6a0ed7d74a4385a2ca194fa68782c6a10e609379cc8  IBMPlexSansCondensed-Light.ttf
426350c298277f7f9d1a93956572799ca3d16e2d43e7f60eec8382bcd795ec30  IBMPlexSansCondensed-Medium.ttf
a081ca60548aea14100757a2d6fe71ca60fd90ebce779c9a8ae5a0c8fb4526d4  IBMPlexSansCondensed-SemiBold.ttf
