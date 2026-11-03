"""Shared by the font study: the candidates (files, axes), the test texts, the po parser. Not run alone."""
import re
from pathlib import Path

DL = Path(r"scratchpad\font\dl")
PO = Path(r"meridiana\po\it.po")

# id: (label, [files], {axis: value} or {}, extra QFont options)
# "axes" are applied with QFont.setVariableAxis; "ls" is a letter spacing in px (QFont.AbsoluteSpacing)
CANDIDATES = {
    "inter": dict(label="Inter 4.1 (oggi)", files=["inter-static/Inter-Regular.ttf", "inter-static/Inter-SemiBold.ttf",
                                                   "inter-static/Inter-Bold.ttf"]),
    "inter-ls1": dict(label="Inter, spaziatura -0,2 px", base="inter", ls=-0.2),
    "inter-ls2": dict(label="Inter, spaziatura -0,4 px", base="inter", ls=-0.4),
    "inter-tnum": dict(label="Inter, cifre tabellari (tnum)", base="inter", features=["tnum"]),
    "intertight": dict(label="Inter Tight", files=["intertight/InterTight[wght].ttf"]),
    "adwaita": dict(label="Adwaita Sans", files=["adwaita-sans/AdwaitaSans-Regular.ttf"]),
    "noto": dict(label="Noto Sans wdth 100", files=["notosans/NotoSans[wdth,wght].ttf"]),
    "noto87": dict(label="Noto Sans wdth 87,5", base="noto", axes={"wdth": 87.5}),
    "noto75": dict(label="Noto Sans wdth 75", base="noto", axes={"wdth": 75}),
    "opensans": dict(label="Open Sans wdth 100", files=["opensans/OpenSans[wdth,wght].ttf"]),
    "opensans87": dict(label="Open Sans wdth 87,5", base="opensans", axes={"wdth": 87.5}),
    "opensans75": dict(label="Open Sans wdth 75", base="opensans", axes={"wdth": 75}),
    "roboto": dict(label="Roboto wdth 100", files=["roboto/Roboto[wdth,wght].ttf"]),
    "roboto87": dict(label="Roboto wdth 87,5", base="roboto", axes={"wdth": 87.5}),
    "roboto75": dict(label="Roboto wdth 75", base="roboto", axes={"wdth": 75}),
    "robotocond": dict(label="Roboto Condensed (statico del wght)", files=["robotocondensed/RobotoCondensed[wght].ttf"]),
    "robotoflex": dict(label="Roboto Flex wdth 100", files=["robotoflex/RobotoFlex[GRAD,XOPQ,XTRA,YOPQ,YTAS,YTDE,YTFI,YTLC,YTUC,opsz,slnt,wdth,wght].ttf"]),
    "robotoflex75": dict(label="Roboto Flex wdth 75", base="robotoflex", axes={"wdth": 75}),
    "plex": dict(label="IBM Plex Sans wdth 100", files=["ibmplexsans/IBMPlexSans[wdth,wght].ttf"]),
    "plex85": dict(label="IBM Plex Sans wdth 85", base="plex", axes={"wdth": 85}),
    "plexcond": dict(label="IBM Plex Sans Condensed (statico)", files=["ibmplexsanscondensed/IBMPlexSansCondensed-Regular.ttf",
                                                                       "ibmplexsanscondensed/IBMPlexSansCondensed-SemiBold.ttf"]),
    "source": dict(label="Source Sans 3", files=["sourcesans3/SourceSans3[wght].ttf"]),
    "fira": dict(label="Fira Sans", files=["firasans/FiraSans-Regular.ttf", "firasans/FiraSans-SemiBold.ttf"]),
    "firacond": dict(label="Fira Sans Condensed", files=["firasanscondensed/FiraSansCondensed-Regular.ttf",
                                                         "firasanscondensed/FiraSansCondensed-SemiBold.ttf"]),
    "barlow": dict(label="Barlow", files=["barlow/Barlow-Regular.ttf", "barlow/Barlow-SemiBold.ttf"]),
    "barlowsc": dict(label="Barlow Semi Condensed", files=["barlowsemicondensed/BarlowSemiCondensed-Regular.ttf",
                                                           "barlowsemicondensed/BarlowSemiCondensed-SemiBold.ttf"]),
    "archivo": dict(label="Archivo wdth 100", files=["archivo/Archivo[wdth,wght].ttf"]),
    "archivo87": dict(label="Archivo wdth 87,5", base="archivo", axes={"wdth": 87.5}),
    "archivo75": dict(label="Archivo wdth 75", base="archivo", axes={"wdth": 75}),
    "jbmono": dict(label="JetBrains Mono 2.304 (monospazio)", files=["jetbrains-static/JetBrainsMono-Regular.ttf",
                                                                     "jetbrains-static/JetBrainsMono-SemiBold.ttf"]),
    "nerdjb": dict(label="JetBrainsMono Nerd Font", files=["nerd/JetBrainsMonoNerdFont-Regular.ttf"]),
    "nerdjbpropo": dict(label="JetBrainsMono Nerd Font Propo", files=["nerd/JetBrainsMonoNerdFontPropo-Regular.ttf"]),
    "nerdubuntu": dict(label="Ubuntu Nerd Font Propo", files=["nerd/UbuntuNerdFontPropo-Regular.ttf"]),
    "nerdubuntucond": dict(label="Ubuntu Nerd Font Propo Condensed", files=["nerd/UbuntuNerdFontPropo-Condensed.ttf"], style="Condensed"),
    "adwaitamono": dict(label="Adwaita Mono", files=["adwaita-mono/AdwaitaMono-Regular.ttf"]),
}

PHASES = ["Modellazione", "Impianto", "Producibilità", "Bilancio ed economia", "Relazione"]
BAR = ["Annulla", "Ripeti", "Disegna", "Misura", "Precisione", "Stringhe", "Batteria", "Esporta", "Ombreggiamento",
       "Ottimizzatori di potenza", "Cavi in continua", "Cavi in alternata", "Inverter e stringhe"]
LABELS = ["Rapporto DC/AC voluto", "Aggiungi un inverter dal catalogo\u2026", "Potenza dei moduli", "Perdite del campo",
          "Producibilità specifica (kWh/kWp)", "Produzione (kWh/anno)", "Orientamento 2", "Inclinazione dei moduli"]
CHECKS = ["Tensione massima a circuito aperto della stringa", "Tensione MPP entro la finestra MPPT con la cella più calda",
          "Corrente massima di cortocircuito di una stringa", "Ottimizzatori nella stringa entro l'intervallo di SolarEdge",
          "12 moduli in serie, tutte le verifiche superate", "Stringhe: verifiche della CEI 64-8/7"]
NUMBERS = ["1,44", "5.489,56", "412 V", "1.234,5 kWh", "98,7 %", "10,86 kWp", "1500 V", "0,83", "-12,4 \u00b0C", "37,2\u00b0"]
GROUPS = {"fasi": PHASES, "barra": BAR, "etichette": LABELS, "verifiche": CHECKS, "numeri": NUMBERS}

# characters the program uses beyond the Italian letters (the study's list) plus all that the catalogue has
CHARS = "àèéìòù\u00b0\u00b2\u00b7\u00ab\u00bb\u2212\u2265\u2225\u22a5\u2014\u2026\u00b1\u00d7\u2248\u03b3\u03a9\u2299\u21e7\u22ef\u2192\u2713"
PRESET_CHARS = {c: n for c, n in zip(CHARS, ["à", "è", "é", "ì", "ò", "ù", "° gradi", "² quadrato", "· punto medio",
                                           "« ", "» ", "− meno", "≥", "∥", "⊥", "— (non usato)", "…", "±", "×", "≈",
                                           "γ", "Ω", "⊙", "⇧", "⋯", "→", "✓"])}


def parse_po(path: Path = PO):
    """[(msgid, msgstr)] of the translated entries, one line each (plurals skipped)."""
    text = path.read_text(encoding="utf-8")
    out = []
    for block in text.split("\n\n"):
        m_id = re.search(r'^msgid ((?:"(?:[^"\\]|\\.)*"\s*\n?)+)', block, re.M)
        m_st = re.search(r'^msgstr ((?:"(?:[^"\\]|\\.)*"\s*\n?)+)', block, re.M)
        if not m_id or not m_st or "fuzzy" in block.split("msgid")[0]:
            continue

        def join(m):
            parts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
            return "".join(parts).encode("utf-8").decode("unicode_escape").encode("latin-1", "ignore").decode("utf-8", "ignore") \
                if False else "".join(p.replace('\\"', '"').replace("\\n", "\n").replace("\\t", "\t") for p in parts)
        out.append((join(m_id), join(m_st)))
    return [(i, s) for i, s in out if i and s]


def corpus(max_len: int = 70):
    """The translated strings of the interface, one line, with the placeholders replaced by a typical value."""
    res = []
    for _i, s in parse_po():
        if "\n" in s or not (3 <= len(s) <= max_len) or "<" in s:
            continue
        s = re.sub(r"\{[a-z_0-9]+(:[^}]*)?\}", "12", s)
        res.append(s)
    return res
