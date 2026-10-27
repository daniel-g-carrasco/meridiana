ESITO: verde

# Incarico 21: pianta e stringhe disegnate

28/10/2026, ramo `kimi-incarico-21`, base `9214a70` da `origin/lavoro`. La sessione precedente aveva completato e
committato i punti 1, 2 e 3. Ho verificato quel lavoro, ho ripreso il punto 4 lasciato a metà nelle prove e ho
completato la chiusura. Commit: `866cae8` (R185), `dac04f3` (R186), `adcc94c` (R184), `b8a9241` (R183).

## R185: i numeri restano sul proprio modulo

[V] La causa era il centraggio della pillola: metà larghezza e metà altezza venivano sottratte dalla posizione nella
scena prima di attivare `ItemIgnoresTransformations`. Quella sottrazione era quindi soggetta alla rotazione e alla
scala della vista, mentre il disegno della pillola no. Ora `setPos()` riceve il centro del modulo in metri e
`ChipItem.offset` centra il disegno in pixel locali.

[V] La prova `test_string_numbers_stay_on_their_modules_at_every_rotation_zoom_and_pan` era rossa prima della
correzione. Ruota la pianta di 30° e 115°, applica tre ingrandimenti e uno spostamento, e misura ogni numero entro
3 pixel dal centro del proprio modulo. Le sei foto `foto/kimi21-r185-{0,30,115}-{chiaro,scuro}.png` mostrano il
risultato sul progetto reale di prova.

## R186: un pallino per ogni modulo stringato

[V] Ogni modulo della stringa ha un'ellisse al centro, nel colore della stringa e con il filo `label_fg` della
pianta. Il diametro è `ChipItem.DOT`, 8 pixel logici, lo stesso campione usato dalle pillole. L'elemento ignora la
trasformazione della vista e resta sopra linea e alone, sia per la stringa scelta sia durante il disegno. Anche le
pillole dei numeri hanno il campione nel colore della stringa.

**Soglia scelta:** i pallini indipendenti compaiono quando il lato corto del modulo misura almeno 14 pixel sullo
schermo (`STRING_DOT_MIN_MODULE_PX`). Sotto questa misura spariscono, perché un disco di 8 px e il suo filo si
fondono con la linea e con i pallini vicini. I campioni dentro le pillole dei numeri restano, perché lì hanno già
spazio e contrasto.

[V] `test_every_stringed_module_has_a_screen_sized_dot_until_modules_get_small` verifica un pallino per modulo,
centro entro 0,01 px, diametro costante e rotazioni di 0°, 30° e 115°. Verifica anche la scomparsa sotto soglia e
il colore del campione nelle pillole. Le foto da vicino di R184 mostrano i pallini in chiaro e scuro; quelle da
lontano mostrano la soglia senza poltiglia.

## R184: i salti fra i moduli

### Riferimento e alternative

[V] La [documentazione PVsyst sullo schema dei cablaggi](https://www.pvsyst.com/help/project-design/array-and-system-losses/ohmic-losses/wiring-loss-optimisation.html)
distingue per colore le connessioni dei moduli di una stringa. Il [Module Layout di PVsyst](https://www.pvsyst.com/help/project-design/shadings/electrical-shadings-module-strings/index.html)
rappresenta le interconnessioni reali fra moduli. Questi riferimenti non impongono una geometria universale per il
salto grafico: la scelta deve quindi rendere evidente l'ordine e non fingersi il percorso esatto del cavo.

Sono state preparate e fotografate tre modalità sulla stringa avanti e indietro fra due file, a tre zoom, con
rotazione 0° e 30°, in chiaro e scuro:

1. **Attuale**, `kimi21-r184-attuale-*.png`: i vecchi aggiramenti con tratti obliqui e anse. È il confronto prima.
2. **Diretto**, `kimi21-r184-diretto-*.png`: ogni salto è una linea tratteggiata diretta fra i due centri. È la più
   semplice, ma fra due file attraversa i moduli intermedi e può sembrare che li includa.
3. **Corsia**, `kimi21-r184-corsia-*.png`: la modalità raccomandata e realizzata. Nella stessa fila il salto resta
   diretto e tratteggiato. Fra file vicine usa un ponticello ortogonale nella corsia libera, senza uscire dalla
   fila. Se non c'è una corsia libera, torna al diretto tratteggiato.

Le 36 fotografie sono state aperte in tavole di confronto e i casi decisivi anche a dimensione originale. La corsia
è la più leggibile per un installatore: i moduli consecutivi vicini hanno la linea piena, il salto è sempre
tratteggiato, il ponticello non scavalca altri moduli e non crea anse. Il diretto resta disponibile nel codice come
ripiego geometrico, non come seconda modalità da scegliere nell'interfaccia.

### Geometria realizzata

[V] `string_paths.Router` decide i vicini senza Qt: due moduli consecutivi sono vicini se la linea fra i centri non
attraversa un altro modulo. Per un salto fra file prova entrambi gli assi del modulo e sceglie il ponticello
ortogonale valido più corto. Oltre 12 lati corti fra i centri evita una deviazione enorme e conserva il diretto.
Ogni percorso comincia e finisce al centro del modulo.

[V] I salti che si incontrano usano corsie laterali derivate dai pixel sullo schermo quando c'è spazio. Dove la
geometria non consente la separazione, numeri di corsia diversi producono tratteggi diversi. Una stringa sola e le
stringhe che non si incontrano non vengono spostate. Le prove coprono salti nella stessa fila, ponticelli nella
corsia, assenza di ingresso negli altri moduli, salti lunghi, salti sovrapposti, file attaccate e 8.000 moduli.

## R183: i pulsanti per ruotare

[V] «Allinea a un lato» ha il nuovo `data/icons/meridiana/view_align.svg`, griglia 24 e tratto 1,7 px come gli altri
simboli. Prima il nome `rotate` non trovava alcun file e l'icona era vuota. `ViewBar.icons_only` conserva il
comando a sola icona anche quando gli altri pulsanti mostrano la parola. Il suggerimento dice «Allinea a un lato
(A)». Quando la larghezza cambia, la barra si riposiziona e non copre la bussola.

[V] «Nord in alto» non ha più un pulsante nella barra. Restano il tasto N, il clic sulla bussola e la voce nel menu
del tasto destro quando la pianta è ruotata. Le prove di `test_viewbar`, inizialmente rosse sui tre cambiamenti,
ora verificano comandi, icona, suggerimento, tasti e menu. Una seconda prova rossa ha riprodotto la sovrapposizione
alla bussola nella vista stretta prima della correzione del riposizionamento.

### Prova reale e fotografie

[V] `tools/real_session.sh` con runtime privato ha aperto `capannone()` su Wayland, monitor nascosto 1600 x 1000.
Il copione dentro il processo ha selezionato l'edificio, premuto A, mosso il puntatore e cliccato un lato, premuto
N, cliccato la bussola e usato il tasto destro con pianta dritta e ruotata. Tutti i comandi hanno dato l'esito
atteso. Il compositore nascosto scrive `Failed to create grabbing popup` per il menu, quindi contenuto e azione del
menu sono stati verificati senza richiedere che il popup restasse visibile; il difetto non si è visto nelle altre
azioni o nelle foto.

[V] Le quattro foto sono state aperte e giudicate:

- `foto/kimi21-r183-chiaro.png` e `kimi21-r183-scuro.png`: barra normale nei due temi, simbolo leggibile, Nord in
  alto assente;
- `foto/kimi21-r183-parole-chiaro.png`: pianta a tutta larghezza, tutti i comandi visibili, Allinea unico a sola
  icona;
- `foto/kimi21-r183-finale-chiaro.png`: stato dopo il giro dei comandi, Nord di nuovo in alto.

## Moduli condivisi cambiati

- `src/meridiana/string_paths.py`: geometria condivisa dei salti, senza Qt.
- `src/meridiana/ui/plan.py`: numeri, pallini, tratteggi e disegno delle stringhe; riusa `ChipItem` e i colori della
  pianta. `ui/marks.py` non è stato modificato.
- `src/meridiana/ui/viewbar.py`: eccezioni a sola icona e riposizionamento dopo il cambio di larghezza.
- `src/meridiana/ui/window.py`: composizione dei comandi della pianta.
- `data/icons/meridiana/view_align.svg`: nuovo simbolo nel sistema delle icone.
- `docs/design/sistema-grafico.md`: regola della barra e dei comandi di rotazione.

## Verifica finale

[V] Interprete `/var/home/daniel/fvtest/venv314/bin/python`, con `meridiana` importato da questo checkout. Il
catalogo è stato aggiornato con `tools/compile_po.py --update`: nessun nuovo testo da tradurre, 3.127 messaggi
tradotti, nessun fuzzy. `msgfmt --check` è pulito.

Prove automatiche offscreen, un gruppo per processo:

| Gruppo | Esito |
|---|---:|
| nucleo | 805 prove, OK, 4 saltate |
| calcoli | 176 prove, OK |
| formati | 60 prove, OK |
| esterni | 6 prove, OK, 6 saltate perché gli ingressi esterni non sono abilitati |
| widget | 324 prove, OK, 1 saltata |
| finestra | 133 prove, OK |
| totale | 1.504 prove, nessun fallimento, 11 saltate |

[V] `ruff check src tests tools`, `git diff --check` e `msgfmt --check` sono puliti. Le 46 fotografie
dell'incarico sono state esaminate, comprese tutte le alternative a tre zoom e nei due temi. Non restano processi
del programma, del compositore o delle sessioni nascoste. `/run/user/1000/doc` è rimasto montato.

[V] Non è stata installata alcuna dipendenza, non è stata aperta una finestra sullo schermo e non sono stati letti
progetti o impostazioni reali di Daniel. La resa sul portatile Dell Windows al 200 % non è stata provata su quel
computer: le fotografie qui sono Linux a 1600 x 1000 e le prove automatiche usano anche le misure in pixel logici.
