"""Missing catalogue translations, local until the common PO catalogue is updated.

The main gettext catalogue wins. This adapter affects only the Quick catalogue.
"""
from meridiana.i18n import _ as gettext, language

_IT = {
    'Catalogue': 'Catalogo', '{n} products': '{n} prodotti', 'Choose': 'Scegli',
    'New personal product': 'Nuovo prodotto personale', 'No products match these filters.': 'Nessun prodotto corrisponde ai filtri.',
    'Power from': 'Potenza da', 'Power up to': 'Potenza fino a', 'Efficiency from (%)': 'Rendimento da (%)',
    'Length up to (m)': 'Lunghezza fino a (m)', 'Personal catalogue destination (.json)': 'Destinazione del catalogo personale (.json)',
    'Product details': 'Scheda del prodotto', 'Loading…': 'Caricamento…', 'Import PVsyst': 'Importa PVsyst',
    'Choose an absolute catalogue destination.': 'Indica il percorso completo del catalogo.',
    'Choose a JSON destination inside the allowed catalogue folder.': 'Scegli un file JSON nella cartella consentita.',
    'Choose an explicit personal catalogue destination before saving.': 'Indica la destinazione del catalogo personale prima di salvare.',
    'Allowed folder': 'Cartella consentita', 'Additional technical field': 'Campo tecnico aggiuntivo',
    'Copy JSON': 'Copia JSON', 'Compare up to four selected products.': 'Confronta fino a quattro prodotti selezionati.',
    'A technical JSON field is invalid: {field}': 'Il campo tecnico JSON non è valido: {field}',
    'The source must be an HTTP(S) address or a PDF document.': 'La fonte deve essere un indirizzo HTTP(S) o un documento PDF.',
    'The source document could not be opened.': 'Non è stato possibile aprire il documento della fonte.',
    'The destination is not a personal catalogue. Choose a new JSON file.': 'La destinazione non è un catalogo personale. Scegli un nuovo file JSON.',
    # mercato e stato di vita
    'For Europe (230/400 V)': 'Per l\'Europa (230/400 V)', 'USA (208/240/277/480 V)': 'USA (208/240/277/480 V)', 'Any market': 'Qualsiasi mercato',
    'Current': 'A catalogo', 'Phasing out': 'In uscita', 'Out of production': 'Fuori produzione', 'State unknown': 'Stato sconosciuto',
    'Current, verified': 'A catalogo, verificati', 'Any state': 'Qualsiasi stato', 'State': 'Stato',
    'From the CEC list: no word on whether it is still made.': 'Dalla lista CEC: non dice se è ancora prodotto.',
    'No written source read on whether it is still made.': 'Nessuna fonte scritta letta su se è ancora prodotto.',
    'Checked on {date}: {url}': 'Controllato il {date}: {url}', 'Read there: «{text}»': 'Letto lì: «{text}»',
    'In its place: {model}': 'Al suo posto: {model}', '{n} families': '{n} famiglie',
    '{n} in another state': '{n} in un altro stato', '{n} that do not go with it': '{n} non compatibili',
    '{n} that do not go with {what}': '{n} non compatibili con {what}', 'among them {models}': 'tra questi {models}',
    'current': 'a catalogo', 'phasing out': 'in uscita', 'out of production': 'fuori produzione',
    'state unknown': 'di stato sconosciuto', 'Close the comparison': 'Chiudi il confronto',
    'Hidden by the filters: {what}': 'Nascosti dai filtri: {what}', 'For: {what}': 'Per: {what}',
    'module': 'modulo', 'inverter': 'inverter', 'optimizer': 'ottimizzatore', 'Only what goes with it': 'Solo i compatibili',
    'Show all ({n})': 'Mostra tutti ({n})',
    'Also the products out of production, of unknown state, for other markets or that do not go with it.':
        'Anche i prodotti fuori produzione, di stato sconosciuto, per altri mercati o non compatibili.',
    'Show them': 'Mostrali', 'Use it anyway': 'Usalo comunque', 'Go back': 'Torna indietro',
    'Open the family': 'Apri la famiglia', 'Close the family': 'Chiudi la famiglia',
    '{name} does not go with what you have: {why}': '{name} non è compatibile con ciò che hai: {why}',
    '{name} is out of production.': '{name} è fuori produzione.',
    'the table of this class could not be read on the datasheet: choose it only after adding its values':
        'la tabella di questa classe non è stata letta dalla scheda: si può scegliere solo dopo averne aggiunto i valori',
    "not listed on Huawei's European product page of this date, which lists MAP0, MB0 and MG0: that does not say it is out of production":
        'non è nella pagina prodotti europea di Huawei a questa data, che elenca MAP0, MB0 e MG0: non vuol dire che sia fuori produzione',
    # la finestra di revisione
    'Drag the datasheet here, or choose the file': 'Trascina qui la scheda tecnica, oppure scegli il file',
    'Meridiana reads the PDF on this PC, without sending it anywhere. Nothing is saved before you check it.':
        'Meridiana legge il PDF su questo PC, senza inviarlo. Niente viene salvato prima che tu lo controlli.',
    'Choose the datasheet…': 'Scegli la scheda…', 'Import a .PAN or .OND…': 'Importa un .PAN o .OND…',
    'Power classes': 'Classi di potenza', 'One row for each class, with its own values from the table of the datasheet.':
        'Una riga per classe, con i suoi valori presi dalla tabella della scheda.',
    'Add a class': 'Aggiungi una classe', 'Remove': 'Togli', 'read on the sheet': 'letto dalla scheda', 'Source': 'Fonte',
    'Required for the calculations': 'Serve ai calcoli', 'Which product of this sheet?': 'Quale prodotto di questa scheda?',
    'Select a product to see its card.': 'Seleziona un prodotto per vederne la scheda.',
    'sure, checked': 'sicuro, controllato', 'to check': 'da controllare', 'doubtful': 'dubbio', 'p. {page}': 'p. {page}',
    'Still needed for the calculations: {fields}': 'Servono ancora ai calcoli: {fields}',
    '{field}: «{text}» is not a number.': '{field}: «{text}» non è un numero.', 'A class: «{text}» is not a number.': 'Una classe: «{text}» non è un numero.',
    'Reading {file}…': 'Lettura di {file}…',
    '{file} has no text: it is a scanned sheet. Meridio can read its pictures if you allow it, or type the values here.':
        '{file} non ha testo: è una scheda scansionata. Meridio può leggerne le immagini, se lo consenti, oppure scrivi qui i valori.',
    'Nothing in {file} could be read as a product of this kind. Type the values, or try Meridio.':
        'In {file} non è stato letto nulla di questo tipo di prodotto. Scrivi i valori, o prova con Meridio.',
    'Read from {file}: check every value against the sheet.': 'Letto da {file}: controlla ogni valore sulla scheda.',
    'Read from {file}: {what}.': 'Letto da {file}: {what}.',
    'Proposed by Meridio: check every value against the sheet.': 'Proposto da Meridio: controlla ogni valore sulla scheda.',
    # i gruppi e i campi
    'Product': 'Prodotto', 'Notes': 'Note', 'Electrical values at STC': 'Valori elettrici in STC',
    'Temperature coefficients': 'Coefficienti di temperatura', 'Size and limits': 'Misure e limiti', 'Technology': 'Tecnologia',
    'Warranty and ageing': 'Garanzia e degrado', 'Output': 'Uscita', 'DC input': 'Ingresso DC', 'Storage': 'Accumulo',
    'Installation': 'Installazione', 'Modules on it': 'Moduli collegati', 'Input': 'Ingresso', 'Compatibility': 'Compatibilità',
    'Energy': 'Energia', 'Power and connection': 'Potenza e collegamento', 'Modules and warranty': 'Moduli e garanzia',
    'Manufacturer': 'Costruttore', 'Model': 'Modello', 'Series': 'Serie', 'Datasheet revision': 'Revisione della scheda',
    'The exact code: a family\'s range goes in the table of classes.': 'Il codice esatto: la gamma di una famiglia va nella tabella delle classi.',
    'The address of the datasheet, or its file name.': 'L\'indirizzo della scheda, o il nome del file.',
    'Power at STC': 'Potenza in STC', 'Efficiency': 'Rendimento', 'Length': 'Lunghezza', 'Width': 'Larghezza', 'Thickness': 'Spessore',
    'Weight': 'Peso', 'Cells': 'Celle', 'Maximum system voltage': 'Tensione massima di sistema', 'Maximum series fuse': 'Fusibile massimo in serie',
    'Bifacial': 'Bifacciale', 'Bifaciality': 'Bifaccialità', 'Product warranty': 'Garanzia di prodotto', 'Power warranty': 'Garanzia di potenza',
    'First year degradation': 'Degrado del primo anno', 'Yearly degradation': 'Degrado annuo',
    'Nominal AC power': 'Potenza nominale AC', 'Maximum AC power': 'Potenza massima AC', 'Phases': 'Fasi', 'Single-phase': 'Monofase', 'Three-phase': 'Trifase',
    'Nominal AC voltage': 'Tensione nominale AC', 'Maximum AC current': 'Corrente massima AC', 'European efficiency': 'Rendimento europeo',
    'Maximum efficiency': 'Rendimento massimo', 'DC architecture': 'Architettura DC', 'MPPT in the inverter': 'MPPT nell\'inverter',
    'Fixed string voltage, with optimizers': 'Tensione di stringa fissa, con ottimizzatori', 'Maximum DC voltage': 'Tensione massima DC',
    'Maximum DC power': 'Potenza massima DC', 'MPPT from': 'MPPT da', 'MPPT to': 'MPPT a', 'Number of MPPT': 'Numero di MPPT',
    'Strings per MPPT': 'Stringhe per MPPT', 'One value, or one for each MPPT: 2 2 1.': 'Un valore, oppure uno per MPPT: 2 2 1.',
    'Maximum current per MPPT': 'Corrente massima per MPPT', 'One value, or one for each MPPT: 30 30 16.': 'Un valore, oppure uno per MPPT: 30 30 16.',
    'Maximum Isc per MPPT': 'Isc massima per MPPT', 'One value, or one for each MPPT.': 'Un valore, oppure uno per MPPT.',
    'Fixed string voltage': 'Tensione di stringa fissa', 'Start-up voltage': 'Tensione di avvio', 'Type': 'Tipo', 'String': 'Di stringa', 'Hybrid': 'Ibrido',
    'Maximum battery power': 'Potenza massima batteria', 'Dimensions': 'Dimensioni', 'IP rating': 'Grado IP', 'Warranty': 'Garanzia',
    'CEI 0-21 stated': 'CEI 0-21 citata', 'Weighted efficiency': 'Rendimento ponderato', 'Peak efficiency': 'Rendimento di picco',
    'Modules per unit': 'Moduli per unità', 'Maximum power per input': 'Potenza massima per ingresso', 'Maximum voltage per input': 'Tensione massima per ingresso',
    'Maximum current per input': 'Corrente massima per ingresso', 'Maximum Isc per input': 'Isc massima per ingresso',
    'Rated input power': 'Potenza nominale di ingresso', 'Maximum input voltage': 'Tensione massima di ingresso', 'Maximum input Isc': 'Isc massima di ingresso',
    'Maximum input current': 'Corrente massima di ingresso', 'Maximum output current': 'Corrente massima di uscita', 'Maximum output voltage': 'Tensione massima di uscita',
    'Compatible inverters': 'Inverter compatibili', 'As the datasheet says it: the rules of its strings come with the catalogue\'s data for the maker.':
        'Come lo dice la scheda: le regole delle stringhe vengono dai dati del catalogo per quel costruttore.',
    'Rapid shutdown': 'Spegnimento rapido', 'Usable energy': 'Energia utilizzabile', 'Nominal energy': 'Energia nominale', 'Depth of discharge': 'Profondità di scarica',
    'Round-trip efficiency': 'Rendimento di ciclo', 'Chemistry': 'Chimica', 'Coupling': 'Accoppiamento', 'Voltage class': 'Classe di tensione', 'Nominal voltage': 'Tensione nominale',
    'Maximum charge power': 'Potenza massima di carica', 'Maximum discharge power': 'Potenza massima di scarica', 'Modules, from': 'Moduli, da', 'Modules, up to': 'Moduli, fino a',
    'Energy per module': 'Energia per modulo', 'Warranted cycles': 'Cicli garantiti', 'yes': 'sì', 'no': 'no',
    # i controlli di coerenza
    '{field}: {value} {unit} is unusual for this kind of product (from {low} to {high})': '{field}: {value} {unit} è insolito per questo tipo di prodotto (da {low} a {high})',
    'Voc must be above Vmp ({voc} V, {vmp} V)': 'Voc deve superare Vmp ({voc} V, {vmp} V)', 'Isc must be above Imp ({isc} A, {imp} A)': 'Isc deve superare Imp ({isc} A, {imp} A)',
    'Vmp × Imp gives {product} W, not {pmax} W: check the three values': 'Vmp × Imp dà {product} W, non {pmax} W: controlla i tre valori',
    'Power and size give an efficiency of {derived} %, not {stated} %': 'Potenza e misure danno un rendimento del {derived} %, non del {stated} %',
    'The width is above the length: check the order of the two': 'La larghezza supera la lunghezza: controlla l\'ordine dei due valori',
    'The class of {pmax} W: Vmp × Imp gives {product} W': 'La classe da {pmax} W: Vmp × Imp dà {product} W', 'The class of {pmax} W: Voc must be above Vmp': 'La classe da {pmax} W: Voc deve superare Vmp',
    'The MPPT window must rise: from {low} V to {high} V': 'La finestra MPPT deve salire: da {low} V a {high} V',
    'The MPPT window ends above the maximum DC voltage ({top} V, {dc} V)': 'La finestra MPPT finisce sopra la tensione massima DC ({top} V, {dc} V)',
    'The maximum AC power is below the nominal one ({va} VA, {ac} W)': 'La potenza massima AC è sotto la nominale ({va} VA, {ac} W)',
    'The maximum DC power is below the nominal AC power ({dc} W, {ac} W)': 'La potenza massima DC è sotto la nominale AC ({dc} W, {ac} W)',
    '{count} MPPT and {given} values: one value, or one for each MPPT': '{count} MPPT e {given} valori: un valore, oppure uno per MPPT',
    'The usable energy is above the nominal one ({usable} kWh, {nominal} kWh)': 'L\'energia utilizzabile supera la nominale ({usable} kWh, {nominal} kWh)',
}


def _(message):
    translated = gettext(message)
    return _IT.get(message, translated) if translated == message and language() == 'it' else translated


_FIELDS_IT = {
    'ac_current_max_a': 'Corrente massima AC (A)', 'ac_power_max_va': 'Potenza massima AC (VA)',
    'ac_voltage_nominal_v': 'Tensione nominale AC (V)', 'afci': 'Rilevamento arco AFCI',
    'backup_or_eps': 'Uscita di emergenza EPS', 'battery_charge_power_max_w': 'Potenza massima carica batteria (W)',
    'battery_current_max_a': 'Corrente massima batteria (A)', 'battery_discharge_power_max_w': 'Potenza massima scarica batteria (W)',
    'battery_power_max_w': 'Potenza massima batteria (W)', 'battery_voltage_range_v': 'Intervallo tensione batteria (V)',
    'bifaciality_estimated': 'Bifaccialità stimata (%)', 'bipv': 'Integrato BIPV', 'cei_0_21': 'CEI 0-21 citata',
    'cells': 'Celle', 'cells_in_series': 'Celle in serie', 'certifications': 'Certificazioni',
    'compatible_inverters': 'Inverter compatibili', 'coupling': 'Accoppiamento AC/DC', 'cycles_warranted': 'Cicli garantiti',
    'datasheet_revision': 'Revisione della scheda', 'dc_architecture': 'Architettura DC',
    'dc_current_max_a': 'Corrente massima DC (A)', 'dc_current_max_per_input_a': 'Corrente massima per ingresso DC (A)',
    'dc_current_max_per_mppt_a': 'Corrente massima per MPPT (A)',
    'dc_current_max_per_mppt_by_strings_a': 'Corrente massima MPPT per numero di stringhe (A)',
    'dc_input_limits_source': 'Fonte dei limiti di ingresso DC', 'dc_input_pairs': 'Coppie di ingressi DC',
    'dc_isc_max_per_input_a': 'Isc massima per ingresso (A)', 'dc_isc_max_per_mppt_a': 'Isc massima per MPPT (A)',
    'dc_power_max_per_input_w': 'Potenza massima per ingresso DC (W)', 'dc_power_max_w': 'Potenza massima DC (W)',
    'dc_power_nominal_w': 'Potenza nominale DC (W)', 'dc_voltage_nominal_v': 'Tensione nominale DC (V)',
    'dimensions_mm': 'Dimensioni (mm)', 'efficiency_cec_pct': 'Rendimento CEC (%)',
    'efficiency_euro_pct': 'Rendimento europeo (%)', 'efficiency_max_pct': 'Rendimento massimo (%)',
    'efficiency_peak_pct': 'Rendimento di picco (%)', 'efficiency_weighted_pct': 'Rendimento ponderato (%)',
    'efficiency_derived': 'Rendimento ricavato', 'efficiency_basis': 'Base di misura del rendimento',
    'end_of_warranty_capacity_pct': 'Capacità a fine garanzia (%)', 'energy_per_module_kwh': 'Energia per modulo (kWh)',
    'field_sources': 'Fonti dei singoli valori', 'fire_rating': 'Classe di reazione al fuoco',
    'first_year_loss': 'Degrado del primo anno (%)', 'yearly_loss': 'Degrado annuo (%)',
    'full_power_mppt_min_v': 'Tensione minima MPPT a piena potenza (V)', 'glass': 'Vetro',
    'hybrid': 'Ibrido', 'ip_rating': 'Grado IP', 'list_date': 'Data elenco', 'list_version': 'Versione elenco',
    'listed': 'Incluso nell’elenco', 'markets': 'Mercati', 'max_input_current_a': 'Corrente massima ingresso (A)',
    'max_input_isc_home_hub_a': 'Isc massima ingresso Home Hub (A)', 'max_output_voltage_v': 'Tensione massima uscita (V)',
    'max_series_fuse_a': 'Fusibile massimo in serie (A)', 'max_system_voltage_v': 'Tensione massima sistema (V)',
    'modules_max': 'Moduli, fino a', 'modules_min': 'Moduli, da', 'noct': 'NOCT (°C)',
    'nominal_voltage_v': 'Tensione nominale (V)', 'operating_temp_c': 'Temperatura di esercizio (°C)',
    'optimizer_grid': 'Griglia degli ottimizzatori', 'optimizer_unit_model': 'Modello ottimizzatore',
    'power_after_25_or_30_years_pct': 'Potenza dopo 25 o 30 anni (%)', 'power_after_years': 'Potenza dopo anni',
    'power_classes_w': 'Classi di potenza (W)', 'rapid_shutdown': 'Spegnimento rapido',
    'sandia': 'Parametri Sandia', 'sdm': 'Parametri del modello a diodo singolo',
    'startup_voltage_v': 'Tensione di avvio (V)', 'storage_compatibility': 'Compatibilità accumulo attestata',
    'storage_limit_notes': 'Note sui limiti di accumulo', 'string_voltage_v': 'Tensione stringa (V)',
    'strings_per_mppt': 'Stringhe per MPPT', 'synergy_units': 'Unità Synergy', 'thickness_mm': 'Spessore (mm)',
    'tolerance': 'Tolleranza', 'type': 'Tipo', 'voltage_range_by_phases_v': 'Intervallo tensione per fasi (V)',
    'warranty_power_years': 'Garanzia di potenza (anni)', 'warranty_product_years': 'Garanzia prodotto (anni)',
    'voltage_range_v': 'Intervallo tensione (V)', 'max_charge_current_a': 'Corrente massima carica (A)',
    'max_discharge_current_a': 'Corrente massima scarica (A)', 'max_parallel_units': 'Unità massime in parallelo',
}


def field_label(key, known):
    if key in known:
        return known[key]
    if language() == 'it':
        return _FIELDS_IT.get(key, _IT['Additional technical field'] + ': ' + key)
    return key.replace('_', ' ')
