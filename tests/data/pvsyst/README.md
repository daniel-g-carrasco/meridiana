# Real PVsyst files for the import tests

`ET-M772BH550GL.PAN` (a module) and `CPS SCH275KTL-DO-US-800-250kW_275kVA_1.OND` (an inverter) are the
manufacturers' PVsyst files that pvlib-python keeps for its own tests (`tests/data` of
https://github.com/pvlib/pvlib-python, taken on 22/10/2026). They are copied unchanged under pvlib's
BSD 3-Clause licence, whose text is in `LICENSE-pvlib.txt`.

## Prova Rho (written by hand)

`Prova Rho_Project.PRJ`, `.VC0` and `.VC1` were written by hand for the tests of
`meridiana.pvsyst`, following the grammar of PVsyst's text files described in
`docs/studio/10-pvsyst-formati-file.md`. They are not PVsyst output and carry no third-party data: the
variant VC0 names the two pvlib files above as its module and inverter.
