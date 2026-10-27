# Incarico 12 per Kimi: unire gli incarichi 5, 6 e 7 in un ramo di integrazione (27/10/2026, notte)

Daniel è andato a dormire e ha chiesto che il lavoro vada avanti da solo. Gli incarichi 8, 9 e 10 si appoggiano sul
lavoro del 5 (Meridio, R170), del 6 (le mappe, R131, R149, R173) e del 7 (le Impostazioni dentro File, il passo delle
file, le Proprietà riusate: R133, R172, R2), che Claude non ha ancora verificato. Il tuo compito è unirli in un ramo
di integrazione, verde in tutte le prove, da cui partirà l'incarico 8. Claude verificherà tutto domattina, prima che
qualcosa arrivi al ramo lavoro e a Daniel.

Usa la skill meridiana (regole, divieti, prove, prova vera). In più, per questo incarico:

## Dove lavori
- Nella cartella ~/dev/meridiana-kimi-12, sul ramo kimi-integra preso da origin/lavoro (c207d1b): il lanciatore la
  crea prima di avviarti. Non toccare ~/dev/meridiana-kimi né ~/dev/meridiana-kimi-11.
- Qui, e solo qui, unisci altri rami nel tuo: `git merge --no-ff` dei rami kimi-incarico-5, kimi-incarico-6 e
  kimi-incarico-7 dentro kimi-integra, e `git cherry-pick 9ae75e9` dall'incarico 11. Non unire niente altro, non
  modificare quei rami, niente rebase, reset --hard, force, push.

## Punti
1. Unisci kimi-incarico-5. È partito da un commit più vecchio (2053deb): aspettati conflitti, per esempio nella riga
   R170 di docs/richieste.md, nel CHANGELOG e in po/it.po. Risolvi tenendo le due intenzioni: le righe e le voci di
   tutte e due le parti, lo stato più recente di ogni richiesta; nel codice leggi che cosa voleva ciascuna parte
   (le righe del registro, il file kimi-incarico-5 in docs/revisioni) prima di scegliere. Il catalogo: dopo ogni
   unione tools/compile_po.py --update, nessuna voce fuzzy o vuota, msgfmt --check pulito. Commit di unione con
   messaggio in inglese che finisce con «(integration, point 1)».
2. Unisci kimi-incarico-6 allo stesso modo («(integration, point 2)»).
3. Unisci kimi-incarico-7 allo stesso modo («(integration, point 3)»). Se uno dei tre rami ha punti non fatti (lo
   dicono il suo git log e il suo file in docs/revisioni), uniscilo lo stesso e scrivilo nell'esito.
4. Porta gli strumenti della prova vera: `git cherry-pick 9ae75e9` (tools/real_session.sh e tools/real_tour.py, punto
   1 dell'incarico 11). Gli altri commit dell'11 no: R178 e R180 aspettano la scelta di Daniel. Se il cherry-pick porta
   anche file dell'esito dell'11, tienili. Poi la verifica: tutti i gruppi di prove (nucleo, calcoli, formati,
   esterni, widget, finestra, un gruppo per processo), ruff, msgfmt, e il giro della prova vera con
   tools/real_session.sh e tools/real_tour.py, con le foto in docs/revisioni/foto/kimi12-*.png, guardate.
   Correggi quello che cade per colpa dell'unione. Scrivi docs/revisioni/kimi-incarico-12-esito.md: la **prima
   riga** deve essere esattamente `ESITO: verde` se tutte le prove passano (una prova di tempo che passa ripetuta da
   sola conta come passata) e il giro mostra il programma sano, altrimenti `ESITO: rosso` e sotto il perché. Il
   lanciatore dell'incarico 8 legge quella riga: con rosso la catena si ferma e aspetta Claude. Sotto, per ogni
   unione: i conflitti trovati e come li hai risolti, i file toccati, che cosa Claude deve guardare con più cura.
   Commit «(integration, point 4)». Alla fine nessun processo lasciato acceso.
