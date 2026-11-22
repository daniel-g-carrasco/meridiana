"""The exact references used by the extracted rules, without a claim of legal currency."""

import re
from meridiana.core.rules.types import StandardRef
from . import rules, vvf_activities, calendar, economics


def references():
    sources = [r.source() for r in rules.RULES] + [calendar.SOURCE, *IMPLEMENTED_SOURCES]
    sources += [
        economics.DM414, economics.GSE_RULES,
        "CEI 64-8/7:2024",
        vvf_activities.SOURCE,
        vvf_activities.PROCEDURE,
        vvf_activities.PV_NOT_AN_ACTIVITY,
        "CEI 0-21:2026-07",
        "CEI 64-8/7:2024-07",
        "CEI 82-25/3:2026",
        "NTC 2018",
    ]
    refs = []
    for source in dict.fromkeys(sources):
        edition = re.search(r":(\d{4}(?:-\d{2})?)", source)
        refs.append(
            StandardRef(
                source, edition.group(1) if edition else None, "as_implemented", source
            )
        )
    return tuple(refs)


# Exact source fields acquired before the extraction, including the existing language variants.
IMPLEMENTED_SOURCES = (
    'ARERA 385/2025/R/eel arts. 2-4; CEI 0-16 Annexes O and T',
    'ARERA 385/2025/R/eel artt. 2-4; CEI 0-16 All. O e T',
    'ARERA, delibera 181/06, Tabella 1 (fasce orarie dal 1 gennaio 2007)',
    'CEI 0-16:2026-07 8.8, 8.8.3, 8.8.7.3, Annex N',
    'CEI 0-16:2026-07 par. 1 (pag. 7); Codice di rete Terna',
    'CEI 0-16:2026-07 punti 8.8, 8.8.3, 8.8.7.3, Allegato N',
    'CEI 0-16:2026-07 sect. 1 (p. 7); Terna Grid Code',
    'CEI 0-16:2026-07, 6.3, Tab. 4, p. 43',
    'CEI 0-21:2026-07 8.2.2.2, 8.2.2.3, 8.4.1 (p. 65), 8.6.2 (p. 96), Annex Bbis.1 (p. 166), Annex G',
    'CEI 0-21:2026-07 8.2.2.2, 8.2.2.3, 8.6.2 (p. 96), 8.6.2.1, Annex A.4.3-A.4.4, Annex D D.1 (p. 249), Annex Gbis (p. 272)',
    'CEI 0-21:2026-07 8.2.2.2; CEI 0-16:2026-07 8.8.3.1 (p. 117)',
    'CEI 0-21:2026-07 8.2.2.2; CEI 0-16:2026-07 8.8.3.1 (pag. 117)',
    'CEI 0-21:2026-07 8.2.2.4 (p. 63-64)',
    'CEI 0-21:2026-07 All. Bbis (pag. 166); CEI 0-16:2026-07 All. Nbis; D.Lgs. 190/2024; DCPREV 14030/2025 par. 2.1',
    'CEI 0-21:2026-07 Annex Bbis (p. 166); CEI 0-16:2026-07 Annex Nbis; Legislative Decree 190/2024; DCPREV 14030/2025 sect. 2.1',
    'CEI 0-21:2026-07 Tabella 5, punto 7.4.10',
    'CEI 0-21:2026-07 Table 5, 7.4.10',
    'CEI 0-21:2026-07 punti 8.2.2.2, 8.2.2.3, 8.4.1 (pag. 65), 8.6.2 (pag. 96), Allegato Bbis.1 (pag. 166), Allegato G',
    'CEI 0-21:2026-07 punti 8.2.2.2, 8.2.2.3, 8.6.2 (pag. 96), 8.6.2.1, Allegati A.4.3-A.4.4, D D.1 (pag. 249), Gbis (pag. 272)',
    'CEI 0-21:2026-07 punto 8.2.2.4 (pag. 63-64)',
    'CEI 0-21:2026-07, 6.3, Tab. 5, p. 33',
    'CEI 0-21:2026-07, 8.2.2.4, p. 63',
    'CEI 0-21:2026-07, 8.3, p. 65',
    'CEI 0-21:2026-07, 8.6.2, p. 96',
    'CEI 64-8/1; DCPREV 14030/2025 par. 1.2',
    'CEI 64-8/1; DCPREV 14030/2025 par. 1.2 (core/rules/rules.py N12)',
    'CEI 64-8/1; DCPREV 14030/2025 sect. 1.2',
    'CEI 64-8/1; DCPREV 14030/2025 sect. 1.2 (core/rules/rules.py N12)',
    'CEI 64-8/7 come senza ottimizzatori [I]: la scheda non lo dice',
    'CEI 64-8/7:2024-07 sect. 712 (p. 91-110)',
    'CEI 64-8/7:2024-07 sez. 712 (pag. 91-110)',
    'CEI 64-8/7:2024-07, Allegato B, B.1, p. 109',
    'CEI 64-8/7:2024-07, Allegato B, B.2, p. 109',
    'D.Lgs. 190/2024 All. A Sez. I (pag. 19)',
    'D.Lgs. 190/2024 artt. 5, 7 e All. A Sez. I (pag. 19); DM MASE 223/2026; D.Lgs. 199/2021 art. 25 (GU 15/2026)',
    'D.Lgs. 199/2021 All. III Sez. C p. 2 (GU n. 15/2026)',
    'D.Lgs. 199/2021 All. III Sez. C p. 3 (GU n. 15/2026)',
    'D.Lgs. 199/2021 All. III Sez. C; DCPREV 14030/2025 1.2',
    'D.Lgs. 199/2021 art. 26, All. III Sez. B-C (GU n. 15 del 20/01/2026)',
    'D.Lgs. 199/2021 art. 26, Allegato III',
    'D.Lgs. 199/2021 art. 26, Allegato III Sez. B p. 3',
    'DCPREV 14030/2025 par. 1.2 pag. 2, 4.5',
    'DCPREV 14030/2025 par. 1.2 pag. 4',
    'DCPREV 14030/2025 par. 1.2 pag. 4 (core/rules/rules.py N14)',
    'DCPREV 14030/2025 par. 3.3.5.1 (pag. 13-16), 4.2 (pag. 20-22)',
    'DCPREV 14030/2025 par. 3.3.5.1 (pag. 13-16), 4.2 (pag. 20-22) (core/rules/rules.py N15)',
    'DCPREV 14030/2025 par. 4.4',
    'DCPREV 14030/2025 par. 4.4 (core/rules/rules.py N16)',
    'DCPREV 14030/2025 sect. 1.2 p. 2, 4.5',
    'DCPREV 14030/2025 sect. 1.2 p. 4',
    'DCPREV 14030/2025 sect. 1.2 p. 4 (core/rules/rules.py N14)',
    'DCPREV 14030/2025 sect. 3.3.5.1 (p. 13-16), 4.2 (p. 20-22)',
    'DCPREV 14030/2025 sect. 3.3.5.1 (p. 13-16), 4.2 (p. 20-22) (core/rules/rules.py N15)',
    'DCPREV 14030/2025 sect. 3.3.5.1 (p. 13-16); core/layout/layout.py; checks.manual_items',
    'DCPREV 14030/2025 sect. 4.4',
    'DCPREV 14030/2025 sect. 4.4 (core/rules/rules.py N16)',
    'DM 37/2008 (consolidated with DM 130/2025) art. 5 par. 1-2 (p. 4), art. 7',
    'DM 37/2008 (consolidated with DM 130/2025) art. 5 par. 2 (p. 4), art. 5 par. 4, arts. 7, 11',
    'DM 37/2008 (testo integrato DM 130/2025) art. 5 c. 1-2 (pag. 4), art. 7',
    'DM 37/2008 (testo integrato DM 130/2025) art. 5 c. 2 (pag. 4), art. 5 c. 4, artt. 7, 11',
    'DM 37/2008 art. 5 c. 2 (pag. 4)',
    'DM 37/2008 art. 5 par. 2 (p. 4)',
    'DM MASE 414/2023, Allegato 1 (in reference\\laws); GSE, Regole operative CACER e TIAD, versione del 16/07/2025, §2.2.2.2.2, p. 45-46',
    'DPR 151/2011 Allegato I (GU n. 221 del 22/09/2011); DCPREV 14030 del 01/09/2025 par. 1.2, 2.2, 2.3, 3.2.1, 3.3.5.2-3.3.5.4, cap. 5; Codice di prevenzione incendi S.10.6.1-S.10.6.2',
    'DPR 151/2011 Allegato I (GU n. 221 del 22/09/2011); DCPREV 14030 del 01/09/2025 par. 1.2, 2.2, 2.3, 3.2.1, 3.3.5.2-3.3.5.4, cap. 5; Codice di prevenzione incendi S.10.6.1-S.10.6.2 (core/rules/rules.py N13)',
    'DPR 151/2011 Annex I (GU no. 221 of 22/09/2011); DCPREV 14030 of 01/09/2025 sect. 1.2, 2.2, 2.3, 3.2.1, 3.3.5.2-3.3.5.4, ch. 5; Fire Prevention Code S.10.6.1-S.10.6.2',
    'DPR 151/2011 Annex I (GU no. 221 of 22/09/2011); DCPREV 14030 of 01/09/2025 sect. 1.2, 2.2, 2.3, 3.2.1, 3.3.5.2-3.3.5.4, ch. 5; Fire Prevention Code S.10.6.1-S.10.6.2 (core/rules/rules.py N13)',
    'Disposizioni efficienza energetica edifici Lombardia (decreto 6437/2026) punti 4.7, 6.14, 6.16, 6.27; DGR XII/6153/2026',
    'L.R. Lombardia 11/2026 artt. 2, 4; DGR XII/6645/2026 All. A par. 2.2, All. B',
    'Legislative Decree 190/2024 arts. 5, 7 and Annex A Sect. I (p. 19); DM MASE 223/2026; Legislative Decree 199/2021 art. 25 (GU 15/2026)',
    'Legislative Decree 199/2021 Annex III Sect. C; DCPREV 14030/2025 1.2',
    'Lombardy Regional Law 11/2026 arts. 2, 4; DGR XII/6645/2026 Annex A sect. 2.2, Annex B',
    'Lombardy building energy rules (decree 6437/2026) points 4.7, 6.14, 6.16, 6.27; DGR XII/6153/2026',
    'Transposition: Perez 1990 (pvlib.irradiance). Irradiation terms: CEI 82-25/1:2026, 3.2.1.15-18, p. 13-14',
    "Trasposizione: Perez 1990 (pvlib.irradiance). Termini dell'irraggiamento: CEI 82-25/1:2026, 3.2.1.15-18, pag. 13-14",
)
