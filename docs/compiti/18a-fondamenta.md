# Compito per una sessione cloud: le fondamenta (revisione 18, le cose urgenti)

Bozza del 23/10/2026 dalla revisione completa (`docs/studio/18-revisione-completa.md`, sezione 4, ordine 1). Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»): ramo `fondamenta` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per passo con i suoi test spinto subito, `docs/richieste.md` aggiornato, riassunto in italiano alla fine. Leggi prima i rapporti `docs/studio/18-prove/G-qualita-sicurezza.md` (sezioni 3, 6, 9), `A-architettura.md` (sezione 5) e `B-norme-citazioni.md` (sezione 4.1 e il punto 10 della 4.2): ogni passo cita il file e la riga.

## Passo 1: il file di progetto validato
1. `model.Project.from_json` valida tipi, chiavi e intervalli e solleva `ValueError` con il percorso della chiave («buildings[2].ring[0]: atteso un numero»); `NaN` e infiniti rifiutati; le chiavi ignote dette, non ignorate in silenzio (A §5, G §6.1, `model.py:423-457`).
2. `config._typed` controlla anche i float (`config.py:131`); un valore sbagliato torna al predefinito con una riga nel log.
3. `open_path` (`window.py:2337-2352`) legge e valida tutto prima di sostituire il progetto; con un errore mostra un messaggio in parole e lascia il progetto di prima; cattura ogni eccezione della lettura, non solo `OSError` e `ValueError`.
4. Test: i 20 file malformati di `docs/studio/18-prove/G-prova-file-progetto.py` diventano test del nucleo e della finestra (tutti con un messaggio, nessuno con una finestra a metà); un file d'esempio per ogni versione del formato (1-6) scritto una volta e congelato in `tests/formati/`, con il test che lo apre (D §7.3, punto 2).

## Passo 2: gli errori arrivano a qualcuno
5. Un `sys.excepthook` in `app.py` (e il gestore dei thread di Qt) che scrive il traceback in un log in `paths.state` con rotazione e mostra «Meridiana ha incontrato un errore: <riga>; il dettaglio è in <file>»; `log.py` scrive anche su file.
6. `tileFailed` collegato alla barra di stato (`ui/tileloader.py:28`, `ui/plan.py:168`); autosave, impostazioni e stato della finestra con un messaggio nella barra di stato quando falliscono (`window.py:2243, 2381, 2464`); Nominatim con timeout (`window.py:352-362`); i `log.complain` dei dati energetici mostrati.
7. `ui/preferences.py:93`: il parametro `page` non va coperto; `Preferences(page="navigation")` apre su Navigazione (test).
8. `ui/energy_pages.py:326-332, 520-533`: un input scartato lo dice.

## Passo 3: la riservatezza
9. Le immagini importate senza EXIF (`ui/underlays.py:79-80`); un limite di dimensione detto all'utente (`underlays.py:87-96`).
10. Una pagina delle Preferenze «Riservatezza»: quali servizi ricevono che cosa (Nominatim l'indirizzo, PVGIS le coordinate, le mappe il riquadro) e un interruttore per ciascuno; il PCN in HTTPS se il servizio lo dà (`tiles.py:52`); `User-Agent` nelle chiamate (`energy/pvgis.py:46`).

## Passo 4: le note normative
11. Le nove correzioni di `B-norme-citazioni.md` §4.1: N22 (Allegato Bbis della CEI 0-21), `model.py:8` (CEI 82-25/1 3.2.3.2), N15 (figure e i quattro casi del 4.2 della DCPREV 14030/2025), N23/N27 (D.Lgs. 190/2024 Allegato A Sez. I; DM MASE 223/2026 al posto di TNE), N05 (via la FAQ CEI 2017: CEI 0-21 8.4.1 e Bbis.1), N04 (Allegato D D.1 e Gbis), N08 (8.8.3.1), N13 (S.10.6.2 da 3.2.1 e 3.3.5.2), N24 (data del 03/08/2026 marcata come dedotta). I testi italiani in `po/it.po`.
12. N02/N03 (DM 37/08 art. 5 c. 2): l'innesco sulla potenza impegnata dell'utenza, sulla superficie (200 m² produttivo e terziario, 400 m² domestico, condomini) e sulla lettera d), non sulla potenza del FV: servono due campi del sito (potenza impegnata, superficie, uso) con i predefiniti marcati; finché non ci sono, la regola dice che il progetto del professionista è dovuto salvo i casi dell'art. 5 c. 2.
13. Il secondo parere PVGIS (`energy/pvgis.py:31-33`, `window.py:226-236`): `pvtechchoice=crystSi2025`, `usehorizon` secondo l'impostazione, e nella finestra la frase che dice quale tecnologia e quale base di anni PVGIS usa; il LID passato a PVGIS uguale a quello della catena (`energy/system.py:101`).

## Passo 5: pulizia
14. `requirements.txt` con `requests` e `pandas`, senza `PySide6_WebEngine` (i tre wheel Essentials, Addons, Pdf); un file delle attribuzioni con le licenze (G §7) e l'About che lo cita.
15. I residui del template: metainfo, `.desktop`, icona, `__init__.py`, `__main__.py`, `updates.py:1-2` (G §9.7); il codice morto elencato lì (`layout.MOUNTINGS`, `Pitch.name`, `MONTHS`, `tileloader.failures`, `config.check_updates` resta per il tema H).
16. `tests/test_release.py:68-70` con `rglob` e il trattino lungo tolto da `docs/studio/06-pvsyst-aurora-pvlib.md`; `_setup.dispose` nelle finestre di `EnergyPages` (`test_window.py:842`).

## Da provare sul PC di Daniel
- Un file `.meridiana` danneggiato a mano aperto dalla finestra: il messaggio e il progetto di prima intatto.
- Uno slot che solleva nella build senza console: il messaggio e il log.
- Le Preferenze aperte su Navigazione dal menu della navigazione.
