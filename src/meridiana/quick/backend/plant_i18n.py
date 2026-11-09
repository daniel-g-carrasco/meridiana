"""Page-local additions until the shared PO catalogue includes the Quick pages."""
from meridiana.i18n import _ as gettext, language

ITALIAN = {
    'Cards': 'Schede', 'Choose automatically…': 'Scegli automaticamente…', 'Clear': 'Svuota',
    'Compute production to see the energy cut.': 'Calcola la produzione per vedere l’energia tagliata.',
    'Continue': 'Continua', 'Choose': 'Scegli', 'Diagram': 'Schema', 'Draw a string': 'Disegna una stringa',
    'Draw again': 'Ridisegna', 'Inverters and strings': 'Inverter e stringhe', 'Lay out': 'Posa',
    'Modules per optimizer, in string order': 'Moduli per ottimizzatore, nell’ordine della stringa',
    'Modules selected': 'Moduli selezionati', 'Move to input': 'Sposta sull’ingresso',
    'No strings yet. Draw a string on an input, or ask Meridiana to propose them.':
        'Nessuna stringa. Disegnala su un ingresso oppure chiedi a Meridiana di proporre la stringatura.',
    'Optimizer groups': 'Gruppi di ottimizzatori', 'Reverse the string': 'Inverti il verso della stringa',
    'The existing strings will be replaced. Undo restores the previous wiring.':
        'Le stringhe esistenti verranno sostituite. Annulla ripristina i collegamenti precedenti.',
    'modules in no string': 'moduli senza stringa', 'The groups must contain all modules.':
        'I gruppi devono contenere tutti i moduli.', 'Choose a string strategy.': 'Scegli il percorso delle stringhe.',
    'Change energy settings': 'Modifica i dati energetici', 'Typical year': 'Anno tipico',
    'Design conditions': 'Condizioni di progetto', 'Favourites': 'Preferite',
    'No datasheet data for sizing.': 'Mancano i dati di targa per il dimensionamento.',
    'Modules laid': 'Moduli posati', 'Connected': 'Collegati', 'Not connected': 'Scollegati', 'Power': 'Potenza',
    'Inputs': 'Ingressi', '{used} used, {free} free': '{used} usati, {free} liberi', 'none chosen': 'nessuno scelto',
    'Optimizers': 'Ottimizzatori', 'Series': 'In serie', 'String {name}': 'Stringa {name}',
    'Module {key}': 'Modulo {key}', '{name}, a row': '{name}, una fila', 'Modules': 'Moduli', 'Strings': 'Stringhe',
    'Module {k} of {n}': 'Modulo {k} di {n}', 'optimizer {k} of {n}': 'ottimizzatore {k} di {n}',
    'Power optimizer': 'Ottimizzatore', 'String': 'Stringa', 'Cable to the module': 'Cavo al modulo',
    'Inverters': 'Inverter', '{n} inverters, {m} models': '{n} inverter, {m} modelli',
    'Inverters sized': 'Inverter dimensionati', 'Other valid combinations': 'Altre combinazioni valide',
    'DC max': 'DC max', 'oversized': 'sovradimensionato', 'Use this': 'Usa questa',
    'Optimizer datasheet…': 'Scheda dell’ottimizzatore…',
}


def _(message):
    translated = gettext(message)
    return ITALIAN.get(message, translated) if language() == 'it' and translated == message else translated
