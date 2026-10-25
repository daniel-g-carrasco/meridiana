# La prova di PVsyst 8: cosa creare, in ordine di utilità

22/10/2026. Meridiana apre già i progetti PVsyst (File › Importa un progetto PVsyst): sui 23 progetti veri trovati in rete posa esattamente i moduli di PVsyst. Restano quattro cose che i file pubblici non mostrano e che solo PVsyst può produrre. Il piano completo, 30 giorni, è nella sezione 8 di `docs/studio/10-pvsyst-formati-file.md`; qui c'è la versione corta, ordinata per quanto sblocca.

## Prima di cominciare

- **Installazione.** PVsyst 8.1 da pvsyst.com, sul PC Windows (PVsyst gira solo su Windows). La prova dura 30 giorni, poi PVsyst passa in modalità DEMO, che apre i file ma non salva: salvare man mano.
- **Cartella di lavoro.** Fuori da OneDrive e da cartelle sincronizzate, per esempio `C:\PVsyst8.1_Data`.
- **Solo componenti generici.** In prova PVsyst accetta solo moduli e inverter generici (Condizioni generali d'uso, 2.4). Il primo giorno proviamo anche a importare `tests\data\pvsyst\ET-M772BH550GL.PAN`.
- **Meteo PVGIS, non Meteonorm.** I dati Meteonorm non si possono esportare verso altri programmi (Condizioni generali d'uso, 1.3). Il sito è Milano (45,4642 N, 9,19 E) con «PVGIS TMY» scelto in PVsyst.
- **Valori riconoscibili.** Ogni valore cambiato deve avere una cifra insolita (27,3 invece di 29), così nei file si ritrova senza dubbi.
- **Dove salvare.** In `C:\Users\utente\dev\meridiana-prove\pvsyst-trial\`: il PRJ, tutte le varianti, il SIT, il MET, gli eventuali SHD e HOR, il report PDF completo.

## I casi, dal più utile

| Ordine | Caso | Cosa fare | Cosa sblocca in Meridiana | Tempo |
|---|---|---|---|---|
| 1 | A, valori predefiniti | Progetto `M00_base`: piano fisso 30°, azimut 0, un modulo e un inverter generici, 2 stringhe da 10, nessuna ombra, tutte le perdite lasciate come sono. Simulare e salvare. | I valori che PVsyst non scrive quando sono quelli predefiniti: oggi Meridiana li prende come 0 e lo dice. | 30 min |
| 2 | B1, perdite | Nello stesso progetto una variante con Uc 27,3 e Uv 1,7; sporcamento 2,7%; LID 1,3%; qualità −0,4%; mismatch 1,7% e di stringa 0,13%; cavi in continua 1,9% a STC; cavi in alternata 37 m da 16 mm². | Le unità di ogni chiave, verificate. | 30 min |
| 3 | D, tetto in 3D | Progetto `M01_tetto`: un edificio per ogni forma elementare (casa a due falde, a falde asimmetriche, a quattro falde, con timpani, parallelepipedo, camino, albero), ognuno con misure diverse (3,1, 4,3, 5,7...); un oggetto in X = 10, Y = 0 e uno in X = 0, Y = 20; tavole su due falde, verticali e orizzontali. Salvare anche la scena come `.SHD`. | Edifici e ostacoli della scena PVsyst in Meridiana, con le loro misure. È il caso più utile per i tetti. | 2-3 ore |
| 4 | C, orizzonte | In `M00_base`, una variante con un orizzonte di 8 punti disegnato a mano (−120: 5°, −60: 12°, −20: 3°, 0: 7°, 20: 4°, 60: 15°, 90: 9°, 150: 2°), salvato come `manuale.HOR`; una con l'orizzonte PVGIS. | Il formato del file `.HOR`, che oggi nessuno conosce. | 30 min |
| 5 | J, accumulo | Progetto `M07_accumulo`: autoconsumo con una batteria generica salvata come `Prova_batteria.BTR`, SOC tra 0,21 e 0,89, carica 3,3 kW, scarica 3,7 kW, un carico da file CSV. | L'accumulo di PVsyst in Meridiana. | 1 ora |
| 6 | Q, un caso vero | Il capannone di prova (`meridiana-prove\Prova capannone Rho.meridiana`) rifatto in PVsyst con componenti generici. | Il confronto ora per ora tra i due programmi sullo stesso impianto. | 2 ore |

Gli altri casi del piano completo (tettoie e inseguitori di ogni tipo, MPPT condivisi, ottimizzatori, meteo importato, batch, economia) si possono fare dopo, se la prova lo permette.

## Cosa serve sapere

- Meridiana legge i file di PVsyst senza mai scriverli. Leggere i propri file per usarli in un altro programma è previsto dalla legge (direttiva 2009/24/CE, art. 5 e 6; sentenza C-406/10 della Corte di giustizia). I fatti con le fonti sono nella sezione 9 dello studio sui formati: non sono un parere legale.
- Mentre lavori in PVsyst io non tocco il mouse: le prove le prepari tu, oppure le faccio io quando non sei al PC, dopo che me lo dici.
