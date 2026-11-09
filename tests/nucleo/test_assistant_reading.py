"""How Meridio reads aloud in Italian (R493): real sentences of Meridiana with what is to be said.

The sources: «it.po» a translation the program shows (checks, settings, report), «manuale» docs/manuale,
«modello» a template of the checks or of the report with test values, «Meridio» the kind of answer he gives,
«norma» a standard as the report cites it."""

import unittest

from meridiana.assistant import reading, speech

CASES = [
    ('Meridio', "Ciao, sono Meridio. Il tuo impianto da 45 kWp produce circa 58.000 kWh all'anno.",
     "Ciao, sono Meridio. Il tuo impianto da quarantacinque chilowatt picco produce circa cinquantottomila chilowattora all'anno."),
    ('it.po', 'Questa stringa regge a -10 °C?',
     'Questa stringa regge a meno dieci gradi?'),
    ('it.po', 'Stringhe (CEI 64-8/7)',
     'Stringhe, cei sessantaquattro otto parte sette'),
    ('it.po', 'Oltre 11,08 kW la protezione di interfaccia è un relè dedicato',
     'Oltre undici virgola zero otto chilowatt la protezione di interfaccia è un relè dedicato'),
    ('it.po', 'valore predefinito di calcolo (0,4%/anno)',
     "valore predefinito di calcolo, zero virgola quattro per cento all'anno"),
    ('it.po', 'Nord (+10 €/MWh)',
     'Nord, più dieci euro al megawattora'),
    ('it.po', 'trifase, rete 230/400 V',
     'trifase, rete duecentotrenta quattrocento volt'),
    ('it.po', 'S1200 su un SE33.3K: tensione di stringa a 850 V',
     'esse milleduecento su un esse e trentatré punto tre kappa: tensione di stringa a ottocentocinquanta volt'),
    ('it.po', 'S1400: un inverter senza fusibili CC',
     'esse millequattrocento: un invèrter senza fusibili ci ci'),
    ('it.po', 'azimut da Sud, + verso Ovest (CEI 82-25/1)',
     'azimut da Sud, più verso Ovest, cei ottantadue venticinque parte uno'),
    ('it.po', "fattore di albedo dell'orizzonte di PVsyst, nullo a 20°",
     "fattore di albedo dell'orizzonte di pi vi sist, nullo a venti gradi"),
    ('it.po', 'rendimento medio al punto di lavoro, ore sopra 50 W/m²',
     'rendimento medio al punto di lavoro, ore sopra cinquanta watt al metro quadrato'),
    ('it.po', 'scheda, rendimento relativo a 200 W/m² (IEC 61853-1)',
     'scheda, rendimento relativo a duecento watt al metro quadrato, i e ci sessantuno ottocentocinquantatré parte uno'),
    ('it.po', 'i moduli cristallini recenti misurano 96-99% secondo IEC 61853-1',
     'i moduli cristallini recenti misurano da novantasei a novantanove per cento secondo i e ci sessantuno ottocentocinquantatré parte uno'),
    ('it.po', 'rendimento relativo a 200 W/m², 25 °C',
     'rendimento relativo a duecento watt al metro quadrato, venticinque gradi'),
    ('it.po', 'SELV o PELV possibili sul lato c.c. (Uoc max fino a 120 V)',
     'selv o pelv possibili sul lato corrente continua, u o ci max fino a centoventi volt'),
    ('it.po', "L'attività del DPR 151/2011 dell'edificio e le regole per i moduli.",
     "L'attività del di pi erre centocinquantuno del duemilaundici dell'edificio e le regole per i moduli."),
    ('it.po', "l'area racchiusa è inferiore a 1 m²",
     "l'area racchiusa è inferiore a un metro quadrato"),
    ('it.po', 'Modello (IFC4)',
     'Modello, i effe ci quattro'),
    ('it.po', 'le schede dei produttori di pannelli sandwich (Isopan), studio 16 A.8',
     'le schede dei produttori di pannelli sènduic, Isopan, studio sedici a otto'),
    ('it.po', 'Bassa tensione (CEI 0-21)',
     'Bassa tensione, cei zero ventuno'),
    ('it.po', 'Media tensione (CEI 0-16)',
     'Media tensione, cei zero sedici'),
    ('it.po', 'Edificio pubblico: la potenza è maggiorata del 10%.',
     'Edificio pubblico: la potenza è maggiorata del dieci per cento.'),
    ('it.po', 'CEI 64-8/7:2024-07 sez. 712 (pag. 91-110)',
     'cei sessantaquattro otto parte sette, edizione luglio duemilaventiquattro, sezione settecentododici, pagina da novantuno a centodieci'),
    ('it.po', 'CEI 0-21:2026-07 punto 8.2.2.4 (pag. 63-64)',
     'cei zero ventuno, edizione luglio duemilaventisei, punto otto punto due punto due punto quattro, pagina da sessantatré a sessantaquattro'),
    ('it.po', 'ARERA 385/2025/R/eel artt. 2-4; CEI 0-16 All. O e T',
     'arera trecentottantacinque del duemilaventicinque R eel articoli da due a quattro; cei zero sedici allegato O e T'),
    ('it.po', 'DCPREV 14030/2025 par. 3.3.5.1 (pag. 13-16), 4.2 (pag. 20-22)',
     'di ci prev quattordicimilatrenta del duemilaventicinque paragrafo tre punto tre punto cinque punto uno, pagina da tredici a sedici, quattro punto due, pagina da venti a ventidue'),
    ('it.po', 'D.Lgs. 199/2021 All. III Sez. C; DCPREV 14030/2025 1.2',
     'decreto legislativo centonovantanove del duemilaventuno allegato tre sezione C; di ci prev quattordicimilatrenta del duemilaventicinque uno punto due'),
    ('it.po', 'Tensione a vuoto oltre 1500 V',
     'Tensione a vuoto oltre millecinquecento volt'),
    ('it.po', 'Oltre 20 kW: rincalzo al dispositivo di interfaccia',
     'Oltre venti chilowatt: rincalzo al dispositivo di interfaccia'),
    ('it.po', 'Oltre 100 kW il distributore può proporre la media tensione',
     'Oltre cento chilowatt il distributore può proporre la media tensione'),
    ('it.po', 'Attività soggetta ai controlli VVF: linee guida DCPREV 14030/2025',
     'Attività soggetta ai controlli vu vu effe: linee guida di ci prev quattordicimilatrenta del duemilaventicinque'),
    ('it.po', 'mai sotto nel 95% delle ore',
     'mai sotto nel novantacinque per cento delle ore'),
    ('it.po', 'Gira di 90°',
     'Gira di novanta gradi'),
    ('it.po', 'La caduta diretta del bypass è assunta pari a 0,5 V.',
     'La caduta diretta del bàipas è assunta pari a zero virgola cinque volt.'),
    ('manuale', "Automatica dalla potenza sceglie la bassa tensione fino a 100 kW, la media fino a 10 MW e l'alta oltre.",
     "Automatica dalla potenza sceglie la bassa tensione fino a cento chilowatt, la media fino a dieci megawatt e l'alta oltre."),
    ('manuale', "Serve un professionista iscritto all'albo sopra 6 kW di potenza impegnata, sopra 200 m² per produzione.",
     "Serve un professionista iscritto all'albo sopra sei chilowatt di potenza impegnata, sopra duecento metri quadrati per produzione."),
    ('manuale', 'Tegole marsigliesi 35 %, coppi 30 %, lamiera o pannelli 7 %.',
     'Tegole marsigliesi trentacinque per cento, coppi trenta per cento, lamiera o pannelli sette per cento.'),
    ('manuale', '45 kWp con moduli da 475 W: 94,7, quindi 95 moduli e 45,13 kWp.',
     'quarantacinque chilowatt picco con moduli da quattrocentosettantacinque watt: novantaquattro virgola sette, quindi novantacinque moduli e quarantacinque virgola tredici chilowatt picco.'),
    ('manuale', "Quando gli ostacoli tolgono più del 3 % dell'irraggiamento di un campo.",
     "Quando gli ostacoli tolgono più del tre per cento dell'irraggiamento di un campo."),
    ('manuale', 'Tra 1.000 e 1.500 kWh/kWp, da nord a sud.',
     'Tra mille e millecinquecento chilowattora per chilowatt picco, da nord a sud.'),
    ('manuale', 'Tra 75 e 85 % è normale per un impianto con poche ombre.',
     'Tra settantacinque e ottantacinque per cento è normale per un impianto con poche ombre.'),
    ('manuale', "I predefiniti sono 25 anni e un tasso del 4 %, con i prezzi che crescono del 2 % l'anno.",
     "I predefiniti sono venticinque anni e un tasso del quattro per cento, con i prezzi che crescono del due per cento l'anno."),
    ('manuale', "0,25 €/kWh per ogni fascia, 0,10 €/kWh per l'energia immessa.",
     "zero virgola venticinque euro al chilowattora per ogni fascia, zero virgola dieci euro al chilowattora per l'energia immessa."),
    ('Meridio', "Il PR dell'impianto è 82,4 %: le perdite DC sono il 9,1 % e quelle AC il 2,3 %.",
     "Il pi erre dell'impianto è ottantadue virgola quattro per cento: le perdite di ci sono il nove virgola uno per cento e quelle a ci il due virgola tre per cento."),
    ('Meridio', 'Il rapporto DC/AC è 1,18: 59,4 kWp di moduli su un inverter da 50 kW.',
     'Il rapporto di ci barra, a ci è uno virgola diciotto: cinquantanove virgola quattro chilowatt picco di moduli su un invèrter da cinquanta chilowatt.'),
    ('Meridio', "L'inverter ha 2 MPPT, ciascuno da 12,5 A e fino a 1.100 V.",
     "L'invèrter ha due emme pi pi ti, ciascuno da dodici virgola cinque ampere e fino a millecento volt."),
    ('Meridio', 'In STC il modulo dà 475 Wp; alla NOCT di 45 °C la potenza scende.',
     'In esse ti ci il modulo dà quattrocentosettantacinque watt picco; alla enne o ci ti di quarantacinque gradi la potenza scende.'),
    ('Meridio', 'Il coefficiente di temperatura è -0,29 %/°C.',
     'Il coefficiente di temperatura è meno zero virgola ventinove per cento per grado.'),
    ('Meridio', "I dati meteo vengono da PVGIS, l'anno tipo TMY dal 2005 al 2023.",
     "I dati meteo vengono da pi vi gis, l'anno tipo ti emme ipsilon dal duemilacinque al duemilaventitré."),
    ('Meridio', 'Il quadro MT/BT è a 15 kV, la cabina ha il trasformatore da 630 kVA.',
     'Il quadro emme ti barra, bi ti è a quindici chilovolt, la cabina ha il trasformatore da seicentotrenta chilovoltampere.'),
    ('Meridio', 'Il POD è IT001E12345678; la pratica GSE è del 06/11/2026.',
     'Il pod è i ti zero zero uno e uno due tre quattro cinque sei sette otto; la pratica gi esse e è del sei novembre duemilaventisei.'),
    ('Meridio', 'Lato CA servono gli SPD di tipo 2, lato CC quelli da 1.000 V.',
     'Lato ci a servono gli esse pi di di tipo due, lato ci ci quelli da mille volt.'),
    ('Meridio', 'La sezione dei cavi solari è 6 mm², 4 x 10 mm² per la dorsale.',
     'La sezione dei cavi solari è sei millimetri quadrati, quattro per dieci millimetri quadrati per la dorsale.'),
    ('Meridio', 'Il modello JKM440N-54HL4-B ha 108 celle.',
     'Il modello i lunga kappa emme quattrocentoquaranta enne cinquantaquattro acca elle quattro bi ha centotto celle.'),
    ('Meridio', 'Commessa 26116, revisione R02 del 30/10.',
     'Commessa ventisei centosedici, revisione erre zero due del trenta ottobre.'),
    ('Meridio', 'Esporta il modello in IFC4 per il BIM del progettista.',
     'Esporta il modello in i effe ci quattro per il bim del progettista.'),
    ('Meridio', "L'irraggiamento sul piano è 1.712 kWh/m² all'anno, il 14,6 % in più dell'orizzontale.",
     "L'irraggiamento sul piano è millesettecentododici chilowattora al metro quadrato all'anno, il quattordici virgola sei per cento in più dell'orizzontale."),
    ('Meridio', "Il risparmio è circa € 1.250 all'anno, il rientro in 7,5 anni.",
     "Il risparmio è circa milleduecentocinquanta euro all'anno, il rientro in sette virgola cinque anni."),
    ('Meridio', 'Inclinazione 30°, azimut -15°: ±2 % sulla produzione.',
     'Inclinazione trenta gradi, azimut meno quindici gradi: più o meno due per cento sulla produzione.'),
    ('Meridio', 'Temperatura minima ≤ -10 °C → tensione massima 1.043 V ≥ 1.000 V.',
     'Temperatura minima minore o uguale a meno dieci gradi, tensione massima millequarantatré volt maggiore o uguale a mille volt.'),
    ('Meridio', 'La stringa ha 18 × 475 W = 8,55 kWp.',
     'La stringa ha diciotto per quattrocentosettantacinque watt uguale a otto virgola cinquantacinque chilowatt picco.'),
    ('Meridio', 'Alle 14:30 la produzione è di 38,2 kW.',
     'Alle quattordici e trenta la produzione è di trentotto virgola due chilowatt.'),
    ('Meridio', 'Il tuo impianto ha 1 inverter, 1 stringa e 21 moduli.',
     'Il tuo impianto ha un invèrter, una stringa e ventuno moduli.'),
    ('Meridio', 'Vedi la «tabella dei carichi» e la relazione «Completa».',
     'Vedi la tabella dei carichi e la relazione Completa.'),
    ('Meridio', "Il fattore di forma è 2/3 e l'ombra copre 1/4 del campo.",
     "Il fattore di forma è due terzi e l'ombra copre un quarto del campo."),
    ('Meridio', "La CEI 0-21 chiede l'SPI oltre 11,08 kW; il DDI è nel quadro.",
     "La cei zero ventuno chiede l'esse pi i oltre undici virgola zero otto chilowatt; il di di i è nel quadro."),
    ('Meridio', 'Secondo ARERA, il ritiro dedicato vale 0,105 €/kWh.',
     'Secondo arera, il ritiro dedicato vale zero virgola centocinque euro al chilowattora.'),
    ('Meridio', "L'energia annua è di 1,2 MWh e 3,45 GWh nel parco.",
     "L'energia annua è di uno virgola due megawattora e tre virgola quarantacinque gigawattora nel parco."),
    ('Meridio', 'Il file è R03_26149.ifc, revisione del 2026-11-06.',
     'Il fàil è erre zero tre due sei uno quattro nove ifc, revisione del sei novembre duemilaventisei.'),
    ('Meridio', 'Tensione di circuito aperto Voc 49,8 V, corrente Isc 13,9 A.',
     'Tensione di circuito aperto vu o ci quarantanove virgola otto volt, corrente i esse ci tredici virgola nove ampere.'),
    ('Meridio', 'Ombre: perdita stimata ~3 %, accettabile.',
     'Ombre: perdita stimata circa tre per cento, accettabile.'),
    ('modello it.po con valori di prova', '50 kW c.a., finestra MPPT 200-1.000 V',
     'cinquanta chilowatt corrente alternata, finestra emme pi pi ti da duecento a mille volt'),
    ('modello it.po con valori di prova', '1.043 V a -10 °C su 1.100 V',
     'millequarantatré volt a meno dieci gradi su millecento volt'),
    ('modello it.po con valori di prova', '59,4 kWp su 50 kW: 1,19',
     'cinquantanove virgola quattro chilowatt picco su cinquanta chilowatt: uno virgola diciannove'),
    ('modello it.po con valori di prova', '580 V a 70 °C, la finestra comincia a 200 V',
     'cinquecentottanta volt a settanta gradi, la finestra comincia a duecento volt'),
    ('modello it.po con valori di prova', '96 moduli · 45,6 kWp · inclinazione 30° · azimut -15°',
     'novantasei moduli, quarantacinque virgola sei chilowatt picco, inclinazione trenta gradi, azimut meno quindici gradi'),
    ('modello it.po con valori di prova', "Verificate alla cella più calda dell'anno tipo, 68 °C, e a -10 °C.",
     "Verificate alla cella più calda dell'anno tipo, sessantotto gradi, e a meno dieci gradi."),
    ('modello it.po con valori di prova', 'Totale sui MPPT: 26,4 A, limite complessivo 40 A; i limiti per MPPT sono verificati separatamente.',
     'Totale sui emme pi pi ti: ventisei virgola quattro ampere, limite complessivo quaranta ampere; i limiti per emme pi pi ti sono verificati separatamente.'),
    ('modello it.po con valori di prova', ', 10 kWh utilizzabili · 3.250 kWh forniti ai carichi',
     'dieci chilowattora utilizzabili, tremiladuecentocinquanta chilowattora forniti ai carichi'),
    ('modello it.po con valori di prova', 'nessun numero di JKM440N in serie sta nella finestra MPPT da 200 a 1.000 V entro 1.100 V (cella da -10 a 70 °C, minima -10 °C)',
     'nessun numero di i lunga kappa emme quattrocentoquaranta enne in serie sta nella finestra emme pi pi ti da duecento a mille volt entro millecento volt, cella da meno dieci a settanta gradi, minima meno dieci gradi'),
    ('modello it.po con valori di prova', 'Falda sud: 24 moduli, una stringa ne vuole da 12 a 18 in serie (MPPT da 200 V, Vmp del modulo 34,1 V con la cella a 70 °C)',
     'Falda sud: ventiquattro moduli, una stringa ne vuole da dodici a diciotto in serie, emme pi pi ti da duecento volt, vu emme pi del modulo trentaquattro virgola uno volt con la cella a settanta gradi'),
    ('modello it.po con valori di prova', "1.420 kWh/m² all'anno, media 14,2 °C",
     "millequattrocentoventi chilowattora al metro quadrato all'anno, media quattordici virgola due gradi"),
    ('modello it.po con valori di prova', 'investimento 52.000 €, risparmio 8.400 € il primo anno',
     'investimento cinquantaduemila euro, risparmio ottomilaquattrocento euro il primo anno'),
    ('modello it.po con valori di prova', 'Fonte: DPR 151/2011 Allegato I, GU n. 221 del 22/09/2011, p. 12.',
     'Fonte: di pi erre centocinquantuno del duemilaundici Allegato uno, gazzetta ufficiale numero duecentoventuno del ventidue settembre duemilaundici, pagina dodici.'),
    ('modello it.po con valori di prova', "Edificio B: attività n. 49 dell'Allegato I del DPR 151/2011 (gruppi elettrogeni), categoria A.",
     "Edificio B: attività numero quarantanove dell'Allegato uno del di pi erre centocinquantuno del duemilaundici, gruppi elettrogeni, categoria A."),
    ('modello it.po con valori di prova', 'Lunghezza di stringa: 12 moduli per la finestra MPPT, al massimo 18 per la tensione massima (1.100 V).',
     'Lunghezza di stringa: dodici moduli per la finestra emme pi pi ti, al massimo diciotto per la tensione massima, millecento volt.'),
    ('modello it.po con valori di prova', 'Vmp 612 V fuori dalla finestra MPPT 200-600 V.',
     'vu emme pi seicentododici volt fuori dalla finestra emme pi pi ti da duecento a seicento volt.'),
    ('norma', 'Il CEI EN 62446-1 chiede le prove di messa in servizio.',
     'Il cei e enne sessantadue quattrocentoquarantasei parte uno chiede le prove di messa in servizio.'),
    ('norma', 'La UNI EN 1991-1-3 dà il carico neve.',
     'La uni e enne millenovecentonovantuno parte uno tre dà il carico neve.'),
]

class ReadingTest(unittest.TestCase):
    def test_real_sentences_are_said_as_a_designer_says_them(self):
        self.assertGreaterEqual(len(CASES), 60)
        for where, text, said in CASES:
            with self.subTest(where=where, text=text):
                self.assertEqual(reading.normalize(text), said)

    def test_no_digit_and_no_unit_symbol_is_left_to_the_voice(self):
        for _where, text, _said in CASES:
            out = reading.normalize(text)
            with self.subTest(text=text):
                self.assertFalse(any(ch.isdigit() for ch in out), out)
                for symbol in (" kW", " kWh", " kWp", " V ", "°", "%", "€", "²", "«", "»"):
                    self.assertNotIn(symbol, out + " ")

    def test_italian_numbers(self):
        for n, words in ((0, "zero"), (1, "uno"), (3, "tre"), (8, "otto"), (21, "ventuno"), (23, "ventitré"),
                         (28, "ventotto"), (101, "centouno"), (108, "centotto"), (180, "centottanta"),
                         (1000, "mille"), (1043, "millequarantatré"), (2026, "duemilaventisei"),
                         (21000, "ventunmila"), (58000, "cinquantottomila"),
                         (100000, "centomila"), (1000000, "un milione"), (2500000, "due milioni cinquecentomila")):
            self.assertEqual(reading.cardinal(n), words, n)
        self.assertEqual(reading.number("1.043,5"), "millequarantatré virgola cinque")
        self.assertEqual(reading.number("0,05"), "zero virgola zero cinque")
        self.assertEqual(reading.number("11,08"), "undici virgola zero otto")
        self.assertEqual(reading.number("8.55"), "otto virgola cinquantacinque")     # the English way, two decimals

    def test_one_agrees_with_what_follows(self):
        self.assertEqual(reading.normalize("1 inverter, 1 stringa, 1 m², 1 kW, tra 1 e 2"),
                         "un invèrter, una stringa, un metro quadrato, un chilowatt, tra uno e due")

    def test_foreign_words_are_said_with_the_italian_designers_accent(self):
        """R512 (Daniel 06/11/2026: «inverter» with the accent on the last «e»): the spelling Kokoro's espeak-ng
        stresses right; any case, whole words only, the longest first."""
        for text, said in (("L'inverter e gli INVERTER", "L'invèrter e gli invèrter"),
                           ("il datasheet del power optimizer", "il data scìt del pàuer optimàiser"),
                           ("backup sul cloud, layout del report", "bècap sul clàud, lèiaut del ripòrt"),
                           ("tracker, bypass, buffer, cluster, download", "trècher, bàipas, bàffer, clàster, dàunlod"),
                           ("SolarEdge, GoodWe, BYD e JA Solar", "sòlar ègi, gud uì, bi uai dì e gei a sòlar"),
                           ("lo string box e il combiner box", "lo string box e il combàiner box"),
                           ("Ctrl+Z", "contròl più Z"), ("Allegato Bbis", "Allegato bi bis"),
                           ("inverters", "inverters"), ("smart, carport, offset, software", "smart, carport, offset, software")):
            with self.subTest(text=text):
                self.assertEqual(reading.normalize(text), said)

    def test_two_acronyms_with_a_slash_are_said_with_barra(self):
        for text, said in (("DC/AC", "di ci barra, a ci"), ("il rapporto DC/AC", "il rapporto di ci barra, a ci"),
                           ("cabina MT/BT", "cabina emme ti barra, bi ti"), ("lato CA/CC", "lato ci a barra, ci ci"),
                           ("SPD/SPI", "esse pi di barra, esse pi i"),
                           ("1.250 kWh/kWp", "milleduecentocinquanta chilowattora per chilowatt picco"),
                           ("0,25 €/kWh", "zero virgola venticinque euro al chilowattora"), ("e/o", "e o")):
            with self.subTest(text=text):
                self.assertEqual(reading.normalize(text), said)

    def test_a_computers_file_is_not_a_row_of_modules(self):
        for text, said in (("il file", "il fàil"), ("i file IFC", "i fàil i effe ci"), ("un nuovo file", "un nuovo fàil"),
                           ("file PDF", "fàil pi di effe"), ("le file di moduli", "le file di moduli"),
                           ("tra le file", "tra le file"), ("delle file", "delle file"), ("due file", "due file")):
            with self.subTest(text=text):
                self.assertEqual(reading.normalize(text), said)

    def test_every_word_of_the_census_has_its_reading_decided(self):
        """docs/meridio/censimento-pronuncia.json (tools/censimento_pronuncia.py): the foreign words and acronyms of
        the program's texts, the manual and the catalogue, each with a decision the rules keep."""
        import json
        from pathlib import Path
        census = json.loads((Path(__file__).resolve().parents[2] / "docs" / "meridio" / "censimento-pronuncia.json")
                            .read_text(encoding="utf-8"))
        words = census["parole"]
        self.assertGreater(len(words), 500)
        rules = reading.rules()
        rewrites = {k.casefold(): v for k, v in rules["pronuncia"].items()}
        for e in words:
            with self.subTest(word=e["parola"]):
                self.assertNotEqual(e["decisione"], "da decidere")
                self.assertTrue(e["fonti"])
                said = reading.normalize(e["parola"])
                if e["decisione"] == "riscritta" and e["parola"].casefold() in rewrites:
                    self.assertEqual(said, rewrites[e["parola"].casefold()])
                if e["decisione"] in ("va bene", "italiana", "lasciata"):
                    self.assertEqual(said, e["parola"])
        for word in ("inverter", "datasheet", "cloud", "DC/AC", "file"):
            self.assertIn(word, {e["parola"] for e in words})

    def test_the_rules_are_data(self):
        rules = reading.rules()
        for section in ("unita", "sigle", "abbreviazioni", "norme", "simboli", "lettere", "mesi"):
            self.assertIn(section, rules)
        self.assertEqual(next(u for u in rules["unita"] if u["simbolo"] == "kWp")["molti"], "chilowatt picco")
        self.assertTrue(str(reading.RULES).endswith("reading_it.json"))

    def test_every_reading_aloud_goes_through_it_in_italian_only(self):
        self.assertEqual(speech.speakable("**45 kWp** e 58.000 kWh"),
                         "quarantacinque chilowatt picco e cinquantottomila chilowattora")
        self.assertEqual(speech.speakable("45 kWp", "en"), "45 kWp")


if __name__ == "__main__":
    unittest.main()
