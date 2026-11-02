"""The activities subject to fire prevention controls: Annex I of DPR 1 August 2011, no. 151 (R327), as data.

The text is the one published in the Gazzetta Ufficiale, Serie generale no. 221 of 22/09/2011, pages 5-20,
transcribed from the copy in Daniel's archive (reference/laws, «DPR 151-2011 ... GU n.221 del 22-09-2011.pdf»,
pages 9-24 of the PDF) and checked against the page images. It is a law: its text is free, and it is kept in
Italian, as written. Only the typography is plain: straight apostrophes, m² and m³ also where the GU prints «m2»
(activity 75), the bullets of a cell joined with «;». Later amendments of the Annex, if any, are not here: the
text is the one of 2011.

Each activity has its number, the text of the column «ATTIVITA'» (which holds the threshold above which it is
subject), the threshold itself as a part of that text, and the rows of the categories A, B and C as the table
gives them (an activity with sub-items, a) and b), has one row each). `short` is a label of the program for the
lists, not a text of the law. The categories (DPR 151/2011 art. 2 par. 3, GU p. 2): B and C ask for the
examination of the project (art. 3 par. 1); every activity starts with the SCIA (art. 4 par. 1); A and B are
checked also by sample (art. 4 par. 2), C always with a visit and the certificate (CPI, art. 4 par. 3).

Photovoltaic plants are not themselves among these activities (DCPREV 14030 of 01/09/2025, sect. 1.1 point 1,
p. 3): the building is, when it hosts one of them. No Qt here."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

SOURCE = "DPR 1 agosto 2011, n. 151, Allegato I (GU Serie generale n. 221 del 22/09/2011, pp. 5-20)"
PROCEDURE = ("DPR 151/2011 art. 2 c. 3 (categorie A, B, C), art. 3 c. 1 (B e C: esame del progetto), art. 4 c. 1 "
             "(SCIA prima dell'esercizio), c. 2 (A e B: controlli anche a campione), c. 3 (C: visita e CPI); GU n. 221 "
             "del 22/09/2011, p. 2")
PV_NOT_AN_ACTIVITY = ("DCPREV 14030 del 01/09/2025, par. 1.1 punto 1 (p. 3): gli impianti fotovoltaici non rientrano fra "
                      "le attività soggette di cui all'Allegato I al DPR 151/2011; par. 1.2 punto 1 (p. 3): le linee "
                      "guida si applicano agli impianti ubicati in attività soggette, o a servizio delle stesse")
CATEGORIES = ("A", "B", "C")


@dataclass(frozen=True)
class Band:
    """One row of the categories: the sub-item it is about ("" for the whole activity) and what falls in A, B, C
    ("" where the cell is empty)."""
    item: str
    a: str = ""
    b: str = ""
    c: str = ""

    def of(self, category: str) -> str:
        return {"A": self.a, "B": self.b, "C": self.c}.get(category, "")


@dataclass(frozen=True)
class Activity:
    number: int
    short: str                  # the program's label for the lists, not the law's words
    text: str                   # the column «ATTIVITA'», as written
    threshold: str              # the part of `text` that says above what it is subject ("" when every one is)
    bands: tuple[Band, ...]
    page: int                   # the page of the GU where its row begins

    def categories(self) -> tuple[str, ...]:
        """The categories this activity can fall in, in order."""
        return tuple(c for c in CATEGORIES if any(b.of(c) for b in self.bands))

    def category_text(self, category: str) -> str:
        """What falls in `category`, sub-item by sub-item: «a) ...: fino a 10 m³»."""
        parts = []
        for b in self.bands:
            cell = b.of(category)
            if cell:
                parts.append(f"{b.item}: {cell}" if b.item else cell)
        return "; ".join(parts)

    def label(self) -> str:
        return f"{self.number}. {self.short}"


def _a(number, short, text, threshold, bands, page) -> Activity:
    return Activity(number, short, text, threshold, tuple(bands), page)


ALL = Band("", c="tutti")

ACTIVITIES: tuple[Activity, ...] = (
    _a(1, "Stabilimenti e impianti con gas infiammabili e/o comburenti",
       "Stabilimenti ed impianti ove si producono e/o impiegano gas infiammabili e/o comburenti con quantità globali "
       "in ciclo superiori a 25 Nm³/h.", "superiori a 25 Nm³/h",
       [Band("", c="Tutti")], 5),
    _a(2, "Compressione o decompressione di gas infiammabili e/o comburenti",
       "Impianti di compressione o di decompressione dei gas infiammabili e/o comburenti con potenzialità superiore a "
       "50 Nm³/h, con esclusione dei sistemi di riduzione del gas naturale inseriti nelle reti di distribuzione con "
       "pressione di esercizio non superiore a 0,5 MPa", "superiore a 50 Nm³/h",
       [Band("", b="Cabine di decompressione del gas naturale fino a 2,4 MPa", c="tutti gli altri casi")], 5),
    _a(3, "Riempimento, depositi, rivendite di gas infiammabili in recipienti mobili",
       "Impianti di riempimento, depositi, rivendite di gas infiammabili in recipienti mobili: a) compressi con "
       "capacità geometrica complessiva superiore o uguale a 0,75 m³; b) disciolti o liquefatti per quantitativi in "
       "massa complessivi superiori o uguali a 75 kg",
       "a) compressi con capacità geometrica complessiva superiore o uguale a 0,75 m³; b) disciolti o liquefatti per "
       "quantitativi in massa complessivi superiori o uguali a 75 kg",
       [Band("a) compressi", b="rivendite, depositi fino a 10 m³", c="Impianti di riempimento, depositi oltre 10 m³"),
        Band("b) disciolti o liquefatti", a="Depositi di GPL fino a 300 kg",
             b="rivendite, depositi di GPL oltre 300 kg e fino a 1.000 kg, depositi di gas infiammabili diversi dal "
               "GPL fino a 1.000 kg",
             c="Impianti di riempimento, depositi oltre 1.000 kg")], 5),
    _a(4, "Depositi di gas infiammabili in serbatoi fissi",
       "Depositi di gas infiammabili in serbatoi fissi: a) compressi per capacità geometrica complessiva superiore o "
       "uguale a 0,75 m³; b) disciolti o liquefatti per capacità geometrica complessiva superiore o uguale a 0,3 m³",
       "a) compressi per capacità geometrica complessiva superiore o uguale a 0,75 m³; b) disciolti o liquefatti per "
       "capacità geometrica complessiva superiore o uguale a 0,3 m³",
       [Band("a) compressi", b="fino a 2 m³", c="oltre i 2 m³"),
        Band("b) disciolti o liquefatti", a="Depositi di GPL fino a 5 m³",
             b="Depositi di gas diversi dal GPL fino a 5 m³; Depositi di GPL da 5 m³ fino a 13 m³",
             c="Depositi di gas diversi dal GPL oltre i 5 m³; Depositi di GPL oltre i 13 m³")], 6),
    _a(5, "Depositi di gas comburenti",
       "Depositi di gas comburenti compressi e/o liquefatti in serbatoi fissi e/o recipienti mobili per capacità "
       "geometrica complessiva superiore o uguale a 3 m³:", "superiore o uguale a 3 m³",
       [Band("", b="fino a 10 m³", c="oltre i 10 m³")], 6),
    _a(6, "Reti di trasporto e distribuzione di gas infiammabili",
       "Reti di trasporto e di distribuzione di gas infiammabili, compresi quelli di origine petrolifera o chimica, "
       "con esclusione delle reti di distribuzione e dei relativi impianti con pressione di esercizio non superiore a "
       "0,5 MPa", "con esclusione delle reti di distribuzione e dei relativi impianti con pressione di esercizio non "
       "superiore a 0,5 MPa",
       [Band("", a="fino a 2,4 MPa limitatamente alle opere e gli impianti di trasporto di gas naturale con densità "
                   "non superiore a 0,8.", b="oltre 2,4 MPa")], 7),
    _a(7, "Centrali di produzione di idrocarburi, stoccaggio di gas naturale, piattaforme",
       "Centrali di produzione di idrocarburi liquidi e gassosi e di stoccaggio sotterraneo di gas naturale, "
       "piattaforme fisse e strutture fisse assimilabili, di perforazione e/o produzione di idrocarburi di cui al "
       "decreto del Presidente della Repubblica 24 maggio 1979, n. 886 ed al decreto legislativo 25 novembre 1996, "
       "n. 624", "", [Band("", c="Tutti")], 7),
    _a(8, "Oleodotti oltre 100 mm",
       "Oleodotti con diametro superiore a 100 mm", "con diametro superiore a 100 mm",
       [Band("", b="tutti")], 7),
    _a(9, "Officine e laboratori di saldatura e taglio dei metalli con gas",
       "Officine e laboratori con saldatura e taglio dei metalli utilizzanti gas infiammabili e/o comburenti, con oltre "
       "5 addetti alla mansione specifica di saldatura o taglio.",
       "con oltre 5 addetti alla mansione specifica di saldatura o taglio",
       [Band("", b="fino a 10 addetti alla mansione specifica di saldatura o taglio.",
             c="oltre 10 addetti alla mansione specifica di saldatura o taglio.")], 7),
    _a(10, "Stabilimenti con liquidi infiammabili e/o combustibili (fino a 125 °C)",
       "Stabilimenti ed impianti ove si producono e/o impiegano, liquidi infiammabili e/o combustibili con punto di "
       "infiammabilità fino a 125 °C, con quantitativi globali in ciclo e/o in deposito superiori a 1 m³",
       "con quantitativi globali in ciclo e/o in deposito superiori a 1 m³",
       [Band("", b="fino a 50 m³", c="oltre 50 m³")], 7),
    _a(11, "Preparazione di oli lubrificanti, diatermici e simili",
       "Stabilimenti ed impianti per la preparazione di oli lubrificanti, oli diatermici e simili, con punto di "
       "infiammabilità superiore a 125 °C, con quantitativi globali in ciclo e/o in deposito superiori a 5 m³.",
       "con quantitativi globali in ciclo e/o in deposito superiori a 5 m³",
       [Band("", b="fino a 100 m³", c="oltre 100 m³")], 7),
    _a(12, "Depositi e rivendite di liquidi infiammabili, combustibili, oli",
       "Depositi e/o rivendite di liquidi infiammabili e/o combustibili e/o oli lubrificanti, diatermici, di qualsiasi "
       "derivazione, di capacità geometrica complessiva superiore a 1 m³",
       "di capacità geometrica complessiva superiore a 1 m³",
       [Band("", a="liquidi con punto di infiammabilità superiore a 65 °C per capacità geometrica complessiva compresa "
                   "da 1 m³ a 9 m³",
             b="liquidi infiammabili e/o combustibili e/o lubrificanti e/o oli diatermici di qualsiasi derivazione per "
               "capacità geometrica complessiva compresa da 1 m³ a 50 m³, ad eccezione di quelli indicati nella "
               "colonna A)",
             c="liquidi infiammabili e/o combustibili e/o lubrificanti e/o oli diatermici di qualsiasi derivazione per "
               "capacità geometrica complessiva superiore a 50 m³")], 8),
    _a(13, "Distributori di carburanti",
       "Impianti fissi di distribuzione carburanti per l'autotrazione, la nautica e l'aeronautica; contenitori – "
       "distributori rimovibili di carburanti liquidi. a) Impianti di distribuzione carburanti liquidi; b) Impianti "
       "fissi di distribuzione carburanti gassosi e di tipo misto (liquidi e gassosi)", "",
       [Band("a) Impianti di distribuzione carburanti liquidi",
             a="Contenitori distributori rimovibili e non di carburanti liquidi fino a 9 mc con punto di "
               "infiammabilità superiore a 65 °C", b="Solo liquidi combustibili", c="tutti gli altri"),
        Band("b) Impianti fissi di distribuzione carburanti gassosi e di tipo misto (liquidi e gassosi)", c="tutti")],
       8),
    _a(14, "Verniciatura con vernici infiammabili e/o combustibili",
       "Officine o laboratori per la verniciatura con vernici infiammabili e/o combustibili con oltre 5 addetti.",
       "con oltre 5 addetti", [Band("", b="fino a 25 addetti", c="oltre 25 addetti")], 9),
    _a(15, "Depositi e rivendite di alcoli oltre il 60%",
       "Depositi e/o rivendite di alcoli con concentrazione superiore al 60% in volume di capacità geometrica "
       "superiore a 1 m³", "di capacità geometrica superiore a 1 m³",
       [Band("", a="fino a 10 m³", b="oltre 10 m³ e fino a 50 m³", c="oltre 50 m³")], 9),
    _a(16, "Estrazione con solventi, raffinazione di oli e grassi",
       "Stabilimenti di estrazione con solventi infiammabili e raffinazione di oli e grassi vegetali ed animali, con "
       "quantitativi globali di solventi in ciclo e/o in deposito superiori a 0,5 m³",
       "superiori a 0,5 m³", [ALL], 9),
    _a(17, "Sostanze esplodenti",
       "Stabilimenti ed impianti ove si producono, impiegano o detengono sostanze esplodenti classificate come tali "
       "dal regolamento di esecuzione del testo unico delle leggi di pubblica sicurezza approvato con regio decreto 6 "
       "maggio 1940, n. 635, e successive modificazioni ed integrazioni.", "", [ALL], 9),
    _a(18, "Vendita e depositi di esplodenti, artifici pirotecnici",
       "Esercizi di minuta vendita e/o depositi di sostanze esplodenti classificate come tali dal regolamento di "
       "esecuzione del testo unico delle leggi di pubblica sicurezza approvato con regio decreto 6 maggio 1940, n. "
       "635, e successive modificazioni ed integrazioni. Esercizi di vendita di artifici pirotecnici declassificati "
       "in “libera vendita” con quantitativi complessivi in vendita e/o deposito superiori a 500 kg, comprensivi "
       "degli imballaggi.", "superiori a 500 kg, comprensivi degli imballaggi",
       [Band("", b="Esercizi di vendita di artifici pirotecnici declassificati in “libera vendita”",
             c="Esercizi di minuta vendita di sostanze esplodenti classificate come tali dal regolamento di esecuzione "
               "del testo unico delle leggi di pubblica sicurezza approvato con regio decreto 6 maggio 1940, n. 635, "
               "e successive modificazioni ed integrazioni.")], 9),
    _a(19, "Sostanze instabili, perossidi organici",
       "Stabilimenti ed impianti ove si producono, impiegano o detengono sostanze instabili che possono dar luogo da "
       "sole a reazioni pericolose in presenza o non di catalizzatori ivi compresi i perossidi organici", "", [ALL],
       10),
    _a(20, "Nitrati di ammonio, perossidi inorganici",
       "Stabilimenti ed impianti ove si producono, impiegano o detengono nitrati di ammonio, di metalli alcalini e "
       "alcolino-terrosi, nitrato di piombo e perossidi inorganici", "", [ALL], 10),
    _a(21, "Sostanze ad accensione spontanea o che con l'acqua sviluppano gas infiammabili",
       "Stabilimenti ed impianti ove si producono, impiegano o detengono sostanze soggette all'accensione spontanea "
       "e/o sostanze che a contatto con l'acqua sviluppano gas infiammabili.", "", [ALL], 10),
    _a(22, "Acqua ossigenata oltre il 60%",
       "Stabilimenti ed impianti ove si produce acqua ossigenata con concentrazione superiore al 60% di perossido di "
       "idrogeno", "con concentrazione superiore al 60% di perossido di idrogeno", [ALL], 10),
    _a(23, "Fosforo e sesquisolfuro di fosforo",
       "Stabilimenti ed impianti ove si produce, impiega e/o detiene fosforo e/o sesquisolfuro di fosforo", "",
       [ALL], 10),
    _a(24, "Zolfo: macinazione, raffinazione, depositi",
       "Stabilimenti ed impianti per la macinazione e la raffinazione dello zolfo; depositi di zolfo con potenzialità "
       "superiore a 10.000 kg", "depositi di zolfo con potenzialità superiore a 10.000 kg", [ALL], 10),
    _a(25, "Fiammiferi: fabbriche e depositi",
       "Fabbriche di fiammiferi; depositi di fiammiferi con quantitativi in massa superiori a 500 kg",
       "depositi di fiammiferi con quantitativi in massa superiori a 500 kg", [ALL], 11),
    _a(26, "Magnesio, elektron e leghe di magnesio",
       "Stabilimenti ed impianti ove si produce, impiega o detiene magnesio, elektron e altre leghe ad alto tenore di "
       "magnesio", "", [ALL], 11),
    _a(27, "Mulini e depositi di cereali",
       "Mulini per cereali ed altre macinazioni con potenzialità giornaliera superiore a 20.000 kg; depositi di cereali "
       "e di altre macinazioni con quantitativi in massa superiori a 50.000 kg",
       "con potenzialità giornaliera superiore a 20.000 kg; depositi di cereali e di altre macinazioni con "
       "quantitativi in massa superiori a 50.000 kg",
       [Band("", b="Depositi di cereali e di altre macinazioni fino a 100.000 kg",
             c="Mulini per cereali ed altre macinazioni; depositi oltre 100.000 kg")], 11),
    _a(28, "Essiccazione di cereali e vegetali",
       "Impianti per l'essiccazione di cereali e di vegetali in genere con depositi di prodotto essiccato con "
       "quantitativi in massa superiori a 50.000 kg", "con quantitativi in massa superiori a 50.000 kg", [ALL], 11),
    _a(29, "Surrogati del caffè",
       "Stabilimenti ove si producono surrogati del caffè", "", [ALL], 11),
    _a(30, "Zuccherifici e raffinerie dello zucchero",
       "Zuccherifici e raffinerie dello zucchero", "", [ALL], 11),
    _a(31, "Pastifici e riserie",
       "Pastifici e/o riserie con produzione giornaliera superiore a 50.000 kg",
       "con produzione giornaliera superiore a 50.000 kg", [ALL], 11),
    _a(32, "Tabacco: lavorazione e deposito con essiccazione",
       "Stabilimenti ed impianti ove si lavora e/o detiene foglia di tabacco con processi di essiccazione con oltre "
       "100 addetti o con quantitativi globali in ciclo e/o in deposito superiori a 50.000 kg",
       "con oltre 100 addetti o con quantitativi globali in ciclo e/o in deposito superiori a 50.000 kg", [ALL], 11),
    _a(33, "Produzione di carta e cartoni",
       "Stabilimenti ed impianti per la produzione della carta e dei cartoni e di allestimento di prodotti cartotecnici "
       "in genere con oltre 25 addetti o con materiale in lavorazione e/o in deposito superiore a 50.000 kg",
       "con oltre 25 addetti o con materiale in lavorazione e/o in deposito superiore a 50.000 kg", [ALL], 11),
    _a(34, "Depositi di carta, archivi, biblioteche",
       "Depositi di carta, cartoni e prodotti cartotecnici, archivi di materiale cartaceo, biblioteche, depositi per la "
       "cernita della carta usata, di stracci di cascami e di fibre tessili per l'industria della carta, con "
       "quantitativi in massa superiori a 5.000 kg.", "con quantitativi in massa superiori a 5.000 kg",
       [Band("", b="fino a 50.000 kg", c="oltre 50.000 kg")], 11),
    _a(35, "Carte e pellicole fotografiche, radiografiche, cinematografiche",
       "Stabilimenti, impianti, depositi ove si producono, impiegano e/o detengono carte fotografiche, calcografiche, "
       "eliografiche e cianografiche, pellicole cinematografiche, radiografiche e fotografiche con materiale in "
       "lavorazione e/o in deposito superiore a 5.000 kg",
       "con materiale in lavorazione e/o in deposito superiore a 5.000 kg",
       [Band("", b="depositi fino a 20.000 kg", c="tutti")], 12),
    _a(36, "Depositi di legnami, legna, paglia, fieno, carbone",
       "Depositi di legnami da costruzione e da lavorazione, di legna da ardere, di paglia, di fieno, di canne, di "
       "fascine, di carbone vegetale e minerale, di carbonella, di sughero e di altri prodotti affini con quantitativi "
       "in massa superiori a 50.000 kg con esclusione dei depositi all'aperto con distanze di sicurezza esterne "
       "superiori a 100 m", "con quantitativi in massa superiori a 50.000 kg",
       [Band("", b="fino a 500.000 kg", c="oltre 500.000 kg")], 12),
    _a(37, "Lavorazione del legno",
       "Stabilimenti e laboratori per la lavorazione del legno con materiale in lavorazione e/o in deposito superiore "
       "a 5.000 kg", "con materiale in lavorazione e/o in deposito superiore a 5.000 kg",
       [Band("", b="fino a 50.000 kg", c="oltre 50.000 kg")], 12),
    _a(38, "Fibre tessili, tessuti, linoleum",
       "Stabilimenti ed impianti ove si producono, lavorano e/o detengono fibre tessili e tessuti naturali e "
       "artificiali, tele cerate, linoleum e altri prodotti affini, con quantitativi in massa superiori a 5.000 kg",
       "con quantitativi in massa superiori a 5.000 kg",
       [Band("", b="fino a 10.000 kg", c="oltre 10.000 kg")], 12),
    _a(39, "Arredi, abbigliamento, pelle, calzaturifici",
       "Stabilimenti per la produzione di arredi, di abbigliamento, della lavorazione della pelle e calzaturifici, con "
       "oltre 25 addetti.", "con oltre 25 addetti", [ALL], 12),
    _a(40, "Crine vegetale, paglia, sparto, sughero",
       "Stabilimenti ed impianti per la preparazione del crine vegetale, della trebbia e simili, lavorazione della "
       "paglia, dello sparto e simili, lavorazione del sughero, con quantitativi in massa in lavorazione o in deposito "
       "superiori a 5.000 kg", "con quantitativi in massa in lavorazione o in deposito superiori a 5.000 kg",
       [ALL], 12),
    _a(41, "Teatri e studi di ripresa cinematografica e televisiva",
       "Teatri e studi per le riprese cinematografiche e televisive", "",
       [Band("", a="fino a 25 persone presenti", b="oltre 25 e fino a 100 persone presenti",
             c="oltre 100 persone presenti")], 13),
    _a(42, "Laboratori di attrezzerie e scenografie",
       "Laboratori per la realizzazione di attrezzerie e scenografie, compresi i relativi depositi, di superficie "
       "complessiva superiore a 200 m²", "di superficie complessiva superiore a 200 m²",
       [Band("", b="fino a 2.000 m²", c="oltre 2.000 m²")], 13),
    _a(43, "Gomma: produzione, vulcanizzazione, depositi di pneumatici",
       "Stabilimenti ed impianti per la produzione, lavorazione e rigenerazione della gomma e/o laboratori di "
       "vulcanizzazione di oggetti di gomma, con quantitativi in massa superiori a 5.000 kg; depositi di prodotti "
       "della gomma, pneumatici e simili, con quantitativi in massa superiori a 10.000 kg",
       "con quantitativi in massa superiori a 5.000 kg; depositi di prodotti della gomma, pneumatici e simili, con "
       "quantitativi in massa superiori a 10.000 kg",
       [Band("", b="depositi fino a 50.000 kg",
             c="Stabilimenti ed impianti per la produzione, lavorazione e rigenerazione e/o laboratori; depositi oltre "
               "50.000 kg")], 13),
    _a(44, "Materie plastiche",
       "Stabilimenti, impianti, depositi ove si producono, lavorano e/o detengono materie plastiche, con quantitativi "
       "in massa superiori a 5.000 kg", "con quantitativi in massa superiori a 5.000 kg",
       [Band("", b="depositi fino a 50.000 kg", c="Stabilimenti ed impianti; depositi oltre 50.000 kg")], 13),
    _a(45, "Resine, fitofarmaci, coloranti, farmaceutici con solventi",
       "Stabilimenti ed impianti ove si producono e lavorano resine sintetiche e naturali, fitofarmaci, coloranti "
       "organici e intermedi e prodotti farmaceutici con l'impiego di solventi ed altri prodotti infiammabili", "",
       [Band("", b="fino a 25 addetti", c="oltre 25 addetti")], 13),
    _a(46, "Depositi di fitofarmaci e concimi chimici",
       "Depositi di fitofarmaci e/o di concimi chimici a base di nitrati e/o fosfati con quantitativi in massa "
       "superiori a 50.000 kg", "con quantitativi in massa superiori a 50.000 kg",
       [Band("", b="fino a 100.000 kg", c="oltre 100.000 kg")], 13),
    _a(47, "Cavi elettrici isolati: fabbricazione e depositi",
       "Stabilimenti ed impianti per la fabbricazione di cavi e conduttori elettrici isolati, con quantitativi in "
       "massa in lavorazione e/o in deposito superiori a 10.000 kg; depositi e/o rivendite di cavi elettrici isolati "
       "con quantitativi in massa superiori a 10.000 kg.",
       "con quantitativi in massa in lavorazione e/o in deposito superiori a 10.000 kg; depositi e/o rivendite di cavi "
       "elettrici isolati con quantitativi in massa superiori a 10.000 kg",
       [Band("", b="fino a 100.000 kg", c="oltre 100.000 kg")], 14),
    _a(48, "Centrali termoelettriche, macchine elettriche con liquidi isolanti oltre 1 m³",
       "Centrali termoelettriche, macchine elettriche fisse con presenza di liquidi isolanti combustibili in "
       "quantitativi superiori a 1 m³", "con presenza di liquidi isolanti combustibili in quantitativi superiori a 1 m³",
       [Band("", b="Macchine elettriche", c="Centrali termoelettriche.")], 14),
    _a(49, "Gruppi elettrogeni con motori endotermici e cogenerazione oltre 25 kW",
       "Gruppi per la produzione di energia elettrica sussidiaria con motori endotermici ed impianti di cogenerazione "
       "di potenza complessiva superiore a 25 kW.", "di potenza complessiva superiore a 25 kW",
       [Band("", a="fino a 350 kW", b="oltre 350 kW e fino a 700 kW", c="oltre 700 kW")], 14),
    _a(50, "Lampade, pile e accumulatori elettrici: produzione",
       "Stabilimenti ed impianti ove si producono lampade elettriche e simili, pile ed accumulatori elettrici e simili, "
       "con oltre 5 addetti", "con oltre 5 addetti", [Band("", b="fino a 25 addetti", c="oltre 25 addetti")], 14),
    _a(51, "Siderurgia e lavorazioni a caldo dei metalli",
       "Stabilimenti siderurgici e per la produzione di altri metalli con oltre 5 addetti; attività comportanti "
       "lavorazioni a caldo di metalli, con oltre 5 addetti, ad esclusione dei laboratori artigiani di oreficeria ed "
       "argenteria fino a 25 addetti.", "con oltre 5 addetti",
       [Band("", b="fino a 25 addetti. Laboratori artigiani di oreficeria ed argenteria fino a 50 addetti",
             c="oltre 25 addetti. Laboratori artigiani di oreficeria ed argenteria oltre 50 addetti")], 14),
    _a(52, "Costruzione di aeromobili, veicoli, materiale rotabile; cantieri navali",
       "Stabilimenti, con oltre 5 addetti, per la costruzione di aeromobili, veicoli a motore, materiale rotabile "
       "ferroviario e tramviario, carrozzerie e rimorchi per autoveicoli; cantieri navali con oltre 5 addetti",
       "con oltre 5 addetti", [Band("", b="fino a 25 addetti", c="oltre 25 addetti")], 14),
    _a(53, "Officine di riparazione di veicoli, materiale rotabile, aeromobili",
       "Officine per la riparazione di: - veicoli a motore, rimorchi per autoveicoli e carrozzerie, di superficie "
       "coperta superiore a 300 m²; - materiale rotabile ferroviario, tramviario e di aeromobili, di superficie "
       "coperta superiore a 1.000 m²;",
       "di superficie coperta superiore a 300 m²; - materiale rotabile ferroviario, tramviario e di aeromobili, di "
       "superficie coperta superiore a 1.000 m²",
       [Band("", b="a) officine per veicoli a motore, rimorchi per autoveicoli e carrozzerie, di superficie fino a "
                   "1.000 m²; b) officine per materiale rotabile ferroviario, tramviario e di aeromobili, di superficie "
                   "fino a 2.000 m²",
             c="a) officine per veicoli a motore, rimorchi per autoveicoli e carrozzerie, di superficie superiore a "
               "1.000 m²; b) officine per materiale rotabile ferroviario, tramviario e di aeromobili, di superficie "
               "superiore a 2.000 m²")], 15),
    _a(54, "Officine meccaniche per lavorazioni a freddo",
       "Officine meccaniche per lavorazioni a freddo con oltre 25 addetti.", "con oltre 25 addetti",
       [Band("", b="fino a 50 addetti", c="oltre 50 addetti")], 15),
    _a(55, "Demolizione di veicoli",
       "Attività di demolizioni di veicoli e simili con relativi depositi, di superficie superiore a 3.000 m²",
       "di superficie superiore a 3.000 m²", [Band("", b="fino a 5.000 m²", c="oltre 5.000 m²")], 15),
    _a(56, "Laterizi, maioliche, porcellane",
       "Stabilimenti ed impianti ove si producono laterizi, maioliche, porcellane e simili con oltre 25 addetti",
       "con oltre 25 addetti", [Band("", b="fino a 50 addetti", c="oltre 50 addetti")], 15),
    _a(57, "Cementifici",
       "Cementifici con oltre 25 addetti", "con oltre 25 addetti", [ALL], 15),
    _a(58, "Pratiche con radiazioni ionizzanti soggette ad autorizzazione (D.Lgs. 230/1995)",
       "Pratiche di cui al decreto legislativo 17 marzo 1995, n. 230 e s.m.i. soggette a provvedimenti autorizzativi "
       "(art. 27 del decreto legislativo 17 marzo 1995, n. 230 ed art. 13 legge 31 dicembre 1962, n. 1860).", "",
       [Band("", b="Assoggettate a nulla osta di categoria B di cui all'art. 29 del d.lgs. 230/95 s.m.i",
             c="Assoggettate a nulla osta di categoria A di cui all'art. 28 del d.lgs. 230/95 s.m.i e art. 13 della "
               "legge n. 1860/62")], 16),
    _a(59, "Autorimesse per mezzi che trasportano materie fissili e radioattive",
       "Autorimesse adibite al ricovero di mezzi utilizzati per il trasporto di materie fissili speciali e di materie "
       "radioattive (art. 5 della legge 31 dicembre 1962, n. 1860, sostituito dall'art. 2 del decreto del Presidente "
       "della Repubblica 30 dicembre 1965, n. 1704; art. 21 del decreto legislativo 17 marzo 1995, n. 230)", "",
       [ALL], 16),
    _a(60, "Depositi di materie nucleari",
       "Impianti di deposito delle materie nucleari ed attività assoggettate agli articoli 33 e 52 del decreto "
       "legislativo 17 marzo 1995, n. 230 e s.m.i, con esclusione dei depositi in corso di spedizione.", "",
       [ALL], 16),
    _a(61, "Combustibili nucleari, prodotti o residui radioattivi",
       "Impianti nei quali siano detenuti combustibili nucleari o prodotti o residui radioattivi [art. 1, lettera b) "
       "della legge 31 dicembre 1962, n. 1860]", "", [ALL], 16),
    _a(62, "Impianti nucleari",
       "Impianti relativi all'impiego pacifico dell'energia nucleare ed attività che comportano pericoli di radiazioni "
       "ionizzanti derivanti dal predetto impiego: - impianti nucleari; - reattori nucleari, eccettuati quelli che "
       "facciano parte di un mezzo di trasporto; - impianti per la preparazione o fabbricazione delle materie "
       "nucleari; - impianti per la separazione degli isotopi; - impianti per il trattamento dei combustibili "
       "nucleari irradianti; - attività di cui agli articoli 36 e 51 del decreto legislativo 17 marzo 1995, n. 230 e "
       "s.m.i.", "", [ALL], 16),
    _a(63, "Sapone, candele, cera, paraffina, glicerina",
       "Stabilimenti per la produzione, depositi di sapone, di candele e di altri oggetti di cera e di paraffina, di "
       "acidi grassi, di glicerina grezza quando non sia prodotta per idrolisi, di glicerina raffinata e distillata ed "
       "altri prodotti affini, con oltre 500 kg di prodotto in lavorazione e/o deposito.",
       "con oltre 500 kg di prodotto in lavorazione e/o deposito",
       [Band("", b="fino a 5.000 kg", c="oltre 5.000 kg")], 17),
    _a(64, "Centri informatici di elaborazione e archiviazione dati (data center)",
       "Centri informatici di elaborazione e/o archiviazione dati con oltre 25 addetti", "con oltre 25 addetti",
       [Band("", b="fino a 50 addetti", c="oltre 50 addetti")], 17),
    _a(65, "Locali di spettacolo e trattenimento, impianti sportivi, palestre",
       "Locali di spettacolo e di trattenimento in genere, impianti e centri sportivi, palestre, sia a carattere "
       "pubblico che privato, con capienza superiore a 100 persone, ovvero di superficie lorda in pianta al chiuso "
       "superiore a 200 m². Sono escluse le manifestazioni temporanee, di qualsiasi genere, che si effettuano in "
       "locali o luoghi aperti al pubblico.",
       "con capienza superiore a 100 persone, ovvero di superficie lorda in pianta al chiuso superiore a 200 m²",
       [Band("", b="fino a 200 persone", c="oltre 200 persone")], 17),
    _a(66, "Alberghi e strutture ricettive, campeggi",
       "Alberghi, pensioni, motel, villaggi albergo, residenze turistico - alberghiere, studentati, villaggi turistici, "
       "alloggi agrituristici, ostelli per la gioventù, rifugi alpini, bed & breakfast, dormitori, case per ferie, con "
       "oltre 25 posti-letto; Strutture turistico-ricettive nell'aria aperta (campeggi, villaggi-turistici, ecc.) con "
       "capacità ricettiva superiore a 400 persone.",
       "con oltre 25 posti-letto; Strutture turistico-ricettive nell'aria aperta (campeggi, villaggi-turistici, ecc.) "
       "con capacità ricettiva superiore a 400 persone",
       [Band("", a="fino a 50 posti letto",
             b="oltre 50 posti letto fino a 100 posti letto; Strutture turistico-ricettive nell'aria aperta (campeggi, "
               "villaggi-turistici, ecc.)", c="oltre 100 posti letto")], 17),
    _a(67, "Scuole, collegi, accademie, asili nido",
       "Scuole di ogni ordine, grado e tipo, collegi, accademie con oltre 100 persone presenti; Asili nido con oltre 30 "
       "persone presenti.", "con oltre 100 persone presenti; Asili nido con oltre 30 persone presenti",
       [Band("", a="fino a 150 persone", b="oltre 150 e fino a 300 persone; asili nido", c="oltre 300 persone")], 17),
    _a(68, "Strutture sanitarie, case di riposo, ambulatori",
       "Strutture sanitarie che erogano prestazioni in regime di ricovero ospedaliero e/o residenziale a ciclo "
       "continuativo e/o diurno, case di riposo per anziani con oltre 25 posti letto; Strutture sanitarie che erogano "
       "prestazioni di assistenza specialistica in regime ambulatoriale, ivi comprese quelle riabilitative, di "
       "diagnostica strumentale e di laboratorio, di superficie complessiva superiore a 500 m²",
       "con oltre 25 posti letto; Strutture sanitarie che erogano prestazioni di assistenza specialistica in regime "
       "ambulatoriale, ivi comprese quelle riabilitative, di diagnostica strumentale e di laboratorio, di superficie "
       "complessiva superiore a 500 m²",
       [Band("", a="fino a 50 posti letto; Strutture riabilitative, di diagnostica strumentale e di laboratorio fino a "
                   "1.000 m²",
             b="Strutture fino a 100 posti letto; Strutture riabilitative, di diagnostica strumentale e di laboratorio "
               "oltre 1.000 m²", c="oltre 100 posti letto")], 18),
    _a(69, "Locali di esposizione e vendita, fiere",
       "Locali adibiti ad esposizione e/o vendita all'ingrosso o al dettaglio, fiere e quartieri fieristici, con "
       "superficie lorda superiore a 400 m² comprensiva dei servizi e depositi. Sono escluse le manifestazioni "
       "temporanee, di qualsiasi genere, che si effettuano in locali o luoghi aperti al pubblico.",
       "con superficie lorda superiore a 400 m² comprensiva dei servizi e depositi",
       [Band("", a="fino a 600 m²", b="oltre 600 e fino a 1.500 m²", c="oltre 1.500 m²")], 18),
    _a(70, "Locali adibiti a depositi (merci e materiali combustibili)",
       "Locali adibiti a depositi di superficie lorda superiore a 1000 m² con quantitativi di merci e materiali "
       "combustibili superiori complessivamente a 5.000 kg",
       "di superficie lorda superiore a 1000 m² con quantitativi di merci e materiali combustibili superiori "
       "complessivamente a 5.000 kg",
       [Band("", b="fino a 3.000 m²", c="oltre 3.000 m²")], 18),
    _a(71, "Aziende e uffici oltre 300 persone",
       "Aziende ed uffici con oltre 300 persone presenti", "con oltre 300 persone presenti",
       [Band("", a="fino a 500 persone", b="oltre 500 e fino a 800 persone", c="oltre 800 persone")], 18),
    _a(72, "Edifici tutelati aperti al pubblico (biblioteche, archivi, musei)",
       "Edifici sottoposti a tutela ai sensi del d.lgs. 22 gennaio 2004, n. 42, aperti al pubblico, destinati a "
       "contenere biblioteche ed archivi, musei, gallerie, esposizioni e mostre, nonché qualsiasi altra attività "
       "contenuta nel presente Allegato.", "", [ALL], 18),
    _a(73, "Edifici terziari o industriali promiscui",
       "Edifici e/o complessi edilizi a uso terziario e/o industriale caratterizzati da promiscuità strutturale e/o dei "
       "sistemi delle vie di esodo e/o impiantistica con presenza di persone superiore a 300 unità, ovvero di "
       "superficie complessiva superiore a 5.000 m², indipendentemente dal numero di attività costituenti e dalla "
       "relativa diversa titolarità.",
       "con presenza di persone superiore a 300 unità, ovvero di superficie complessiva superiore a 5.000 m²",
       [Band("", b="fino a 500 unità ovvero fino a 6.000 m²", c="oltre 500 unità ovvero oltre 6.000 m²")], 19),
    _a(74, "Impianti di produzione di calore oltre 116 kW",
       "Impianti per la produzione di calore alimentati a combustibile solido, liquido o gassoso con potenzialità "
       "superiore a 116 kW", "con potenzialità superiore a 116 kW",
       [Band("", a="fino a 350 kW", b="oltre 350 kW e fino a 700 kW", c="oltre 700 kW")], 19),
    _a(75, "Autorimesse, ricovero di natanti e aeromobili, depositi di mezzi rotabili",
       "Autorimesse pubbliche e private, parcheggi pluriplano e meccanizzati di superficie complessiva coperta "
       "superiore a 300 m²; locali adibiti al ricovero di natanti ed aeromobili di superficie superiore a 500 m²; "
       "depositi di mezzi rotabili (treni, tram ecc.) di superficie coperta superiore a 1.000 m².",
       "di superficie complessiva coperta superiore a 300 m²; locali adibiti al ricovero di natanti ed aeromobili di "
       "superficie superiore a 500 m²; depositi di mezzi rotabili (treni, tram ecc.) di superficie coperta superiore "
       "a 1.000 m²",
       [Band("", a="Autorimesse fino a 1.000 m²",
             b="Autorimesse oltre 1.000 m² e fino a 3.000 m²; ricovero di natanti ed aeromobili oltre 500 m² e fino a "
               "1000 m²",
             c="Autorimesse oltre 3000 m²; ricovero di natanti ed aeromobili di superficie oltre i 1000 m²; depositi "
               "di mezzi rotabili")], 19),
    _a(76, "Tipografie, litografie, stampa",
       "Tipografie, litografie, stampa in offset ed attività similari con oltre cinque addetti.",
       "con oltre cinque addetti", [Band("", b="fino a 50 addetti", c="oltre 50 addetti")], 19),
    _a(77, "Edifici civili con altezza antincendio oltre 24 m",
       "Edifici destinati ad uso civile con altezza antincendio superiore a 24 m",
       "con altezza antincendio superiore a 24 m",
       [Band("", a="fino a 32 m", b="oltre 32 m e fino a 54 m", c="oltre 54 m")], 19),
    _a(78, "Aerostazioni, stazioni ferroviarie e marittime, metropolitane",
       "Aerostazioni, stazioni ferroviarie, stazioni marittime, con superficie coperta accessibile al pubblico "
       "superiore a 5.000 m²; metropolitane in tutto o in parte sotterranee.",
       "con superficie coperta accessibile al pubblico superiore a 5.000 m²", [ALL], 19),
    _a(79, "Interporti oltre 20.000 m²",
       "Interporti con superficie superiore a 20.000 m²", "con superficie superiore a 20.000 m²", [ALL], 20),
    _a(80, "Gallerie stradali e ferroviarie",
       "Gallerie stradali di lunghezza superiore a 500 m e ferroviarie superiori a 2000 m",
       "di lunghezza superiore a 500 m e ferroviarie superiori a 2000 m", [Band("", a="tutte")], 20),
)

_BY_NUMBER = {a.number: a for a in ACTIVITIES}


def activity(number) -> Activity | None:
    """The activity with this number, or None (0, "", a number outside 1-80)."""
    try:
        return _BY_NUMBER.get(int(number))
    except (TypeError, ValueError):
        return None


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _haystack(a: Activity) -> str:
    return _fold(" ".join([a.short, a.text, *(f"{b.item} {b.a} {b.b} {b.c}" for b in a.bands)]))


_STOP = {"di", "del", "della", "dei", "delle", "e", "ed", "o", "il", "la", "le", "lo", "gli", "i", "un", "una", "per",
         "con", "in", "a", "da", "al", "alla", "che", "the", "of", "and", "or", "for", "with"}


def search(query: str, limit: int = 8) -> list[Activity]:
    """The activities that match `query`: a number gives that activity, words the ones whose text, label or
    categories hold most of them (accents and case ignored; a word matches the start of a word of the text, so
    «deposit» finds «depositi»)."""
    query = str(query or "").strip()
    found = activity(query) if query.isdigit() else None
    if found is not None:
        return [found]
    words = [w for w in re.findall(r"\w+", _fold(query)) if w not in _STOP and (len(w) > 1 or w.isdigit())]
    if not words:
        return []
    scored = []
    for a in ACTIVITIES:
        hay = _haystack(a)
        score = sum(1 for w in words if re.search(r"(?<!\w)" + re.escape(w), hay))
        if str(a.number) in words:
            score += 2
        if score:
            scored.append((-score, a.number, a))
    scored.sort()
    return [a for _s, _n, a in scored[:limit]]


def as_dict(a: Activity) -> dict:
    """An activity for a reader that is not Python (Meridio's tool): number, texts and categories, its page."""
    return {"number": a.number, "label": a.short, "text": a.text, "threshold": a.threshold or "tutte (nessuna soglia)",
            "categories": {c: a.category_text(c) for c in a.categories()},
            "source": f"{SOURCE}, p. {a.page}"}
