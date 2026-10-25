"""PVsyst's own files, read (never written): the text "PVObject" format of its projects, variants, sites,
weather and components (PVsyst 6.40 and later), the compact hourly records inside them, and the mapping of a
PVsyst project onto a Meridiana project. The format is "intended for internal use only" by PVsyst's own
help: everything here is read tolerantly, what is not understood is said, never guessed. The study behind it
is docs/studio/10-pvsyst-formati-file.md.

No Qt here: the window asks, shows what was read and creates the project."""
