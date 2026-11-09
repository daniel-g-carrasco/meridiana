"""Italian additions awaiting the shared catalogue merge; gettext always has priority.

The settings branch owns only settings*.py. Keep these additions here until the
integration branch extracts them into po/it.po, then remove the fallback table.
"""
from meridiana import i18n


ITALIAN = {
    'Enter a value between {low} and {high}.': 'Scrivi un valore tra {low} e {high}.',
    'Pitch, in semitones': 'Tono, in semitoni',
    'Speed': 'Velocità',
    'Listen': 'Ascolta',
    'Automatic: Sara in Italian, Michael in English': 'Automatica: Sara in italiano, Michael in inglese',
    'Higher is younger: the voice is resampled, so its pitch and its timbre rise together. Daniel chose +1 with Sara (R492).':
        'Più alto è più giovane: la voce è ricampionata, così tono e timbro salgono insieme. Daniel ha scelto +1 con Sara (R492).',
    '1 is the speed of the model; Daniel chose 1.15. «Listen» reads a sentence with these settings.':
        '1 è la velocità del modello; Daniel ha scelto 1,15. «Ascolta» legge una frase con queste impostazioni.',
    'Kokoro is not on this PC: download its model in Settings > Assistant.':
        'Kokoro non è su questo PC: scarica il suo modello in Impostazioni > Assistente.',
    'The sentence of trial did not come: {why}': 'La frase di prova non è arrivata: {why}',
    'Other settings': 'Altre impostazioni',
    'Already used by: {commands}': 'Già usato da: {commands}',
    'Assign these keys and remove them from the other commands': 'Assegna questi tasti e toglili dagli altri comandi',
    'A different logo already has that file name.': 'Esiste già un logo diverso con questo nome di file.',
    'Automatic takes the best source for the site of each project.': 'Automatico sceglie la fonte migliore per il sito di ogni progetto.',
    'Capabilities address': 'Indirizzo delle capabilities',
    'Choose WMS or WMTS first.': 'Scegli prima WMS o WMTS.',
    'Choose a profile.': 'Scegli un profilo.',
    'Choose a source.': 'Scegli una fonte.',
    'Choose a unique profile name.': 'Scegli un nome di profilo non ancora usato.',
    'Choose on or off.': 'Scegli attivo o disattivo.',
    'Choose one of the available values.': 'Scegli uno dei valori disponibili.',
    'Choose the folder for the natural voice first.': 'Scegli prima la cartella per la voce naturale.',
    'Cloud providers': 'Fornitori cloud',
    'Coordinate reference system': 'Sistema di riferimento',
    'Could not search for local models: {reason}': 'Ricerca dei modelli locali non riuscita: {reason}',
    'Desktop language': 'Lingua del sistema',
    "Download Kokoro's model (two files, about 350 MB) from its official release on GitHub into the folder above. Licence: Apache-2.0. Nothing of yours is sent.":
        'Scarica il modello di Kokoro (due file, circa 350 MB) dalla sua pubblicazione ufficiale su GitHub nella cartella indicata sopra. Licenza: Apache-2.0. Non viene inviato niente di tuo.',
    'Download cancelled.': 'Scaricamento annullato.',
    'Enter a size between 160 and 2400 pixels.': 'Inserisci una dimensione fra 160 e 2400 pixel.',
    'Enter a value between 0 and 1.': 'Inserisci un valore fra 0 e 1.',
    'Enter a whole number.': 'Inserisci un numero intero.',
    'Enter text.': 'Inserisci un testo.',
    'Enter the model name.': 'Inserisci il nome del modello.',
    'Height of the speech bubble': 'Altezza del fumetto',
    'Language': 'Lingua',
    'Map under the plan: the area in view goes to the server of the source in use.':
        'Mappa sotto la pianta: la zona in vista viene inviata al server della fonte in uso.',
    'No custom map source yet.': 'Non hai ancora aggiunto fonti cartografiche.',
    'No profile yet. Add a profile to sign your reports.': 'Non ci sono profili. Aggiungi un profilo per firmare le relazioni.',
    'Profiles': 'Profili',
    'Reduce motion': 'Riduci il movimento',
    'The language changes at the next start.': 'La lingua cambia al prossimo avvio.',
    'The source changed while its capabilities were being read. Read them again.':
        'La fonte è cambiata durante la lettura delle capabilities. Leggile di nuovo.',
    'The system keyring is not available: {reason}': 'Il portachiavi del sistema non è disponibile: {reason}',
    'Tile matrix set': 'Griglia delle tessere',
    'Unknown command or invalid keys.': 'Comando sconosciuto o tasti non validi.',
    'Unknown key service.': 'Servizio del portachiavi sconosciuto.',
    'Unknown section.': 'Sezione sconosciuta.',
    'Unknown setting: {key}': 'Impostazione sconosciuta: {key}',
    'Use a colour such as #1c6e8c.': 'Usa un colore come #1c6e8c.',
    'Use a list of records.': 'Usa un elenco di voci.',
    'Veil over the map': 'Velo sulla mappa',
    'Width of the speech bubble': 'Larghezza del fumetto',
    'Zoom is outside the allowed range.': 'L’ingrandimento è fuori dall’intervallo consentito.',
}


def _(message):
    translated = i18n._(message)
    if translated == message and i18n.language() == 'it':
        return ITALIAN.get(message, translated)
    return translated
