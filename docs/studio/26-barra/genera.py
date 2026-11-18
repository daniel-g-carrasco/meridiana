"""Study 26: writes bozzetti.html (self-contained) from barre.json. python docs/studio/26-barra/genera.py"""

import barra_html as H

ORDER = ("model", "plant", "production", "consumption", "economics", "report")
TITLES = {p: f'{H.PHASES[p]["n"]} {H.PHASES[p]["title"]}' for p in ORDER}
STATES = (("rest", "A riposo"), ("hover", "Al passaggio"), ("open", "Aperto"), ("active", "Con una voce attiva"),
          ("changed", "Ultima voce cambiata"))
DESIGNS = {
    "g0": ("G0. Oggi (R306, fatto ieri alla svelta)",
           "Riferimento. Freccetta in alto a destra, 16 px, sopra la parola; clic sull'icona esegue l'ultima voce, "
           "tieni premuto o clic sulla freccetta apre. "
           "<b>Pro</b>: c'è già, larghezza ferma. <b>Contro</b>: la zona della freccia è piccola e non ha un suo passaggio; "
           "la faccia cambia anche per un tasto e da sola quando la voce si spegne; «Cancella tutte» può restare sul pulsante."),
    "g1": ("G1. L'angolo, alla AutoCAD",
           "Triangolino nell'angolo in basso a destra dell'icona. Clic esegue, tieni premuto o clic sull'angolo apre un elenco. "
           "<b>Pro</b>: discreto, la barra resta pulita, chi viene da AutoCAD lo riconosce. <b>Contro</b>: 7 px di segno, si scopre "
           "solo sapendolo; bersaglio piccolo, scomodo al tocco."),
    "g2": ("G2. Parte divisa: comando e striscia",
           "Il pulsante è in due parti: icona e parola eseguono; una striscia alta tutto il pulsante, con il chevron, apre. "
           "Al passaggio compare il filo fra le due. <b>Pro</b>: si vede sempre che c'è altro, due bersagli chiari, funziona in tutte "
           "le altezze, la striscia resta viva anche se il comando è spento. <b>Contro</b>: 14 px in più per ogni gruppo."),
    "g3": ("G3. Faccia fissa e tendina con anteprime",
           "Il pulsante non cambia mai: stessa icona, stessa parola, chevron accanto. Il clic apre sempre una tendina con "
           "icona grande, nome, descrizione e tasto; l'ultima usata ha il fondo. <b>Pro</b>: impossibile sbagliare comando. "
           "<b>Contro</b>: sempre due clic, anche per ripetere la stessa cosa; il disegno di serie (falde una dopo l'altra) rallenta."),
    "g4": ("G4. Fila che si apre a scomparsa",
           "Un chevron verso destra sul pulsante; il clic sulla faccia apre, sopra i vicini e senza spostarli, una fila con tutte le voci "
           "uguali ai pulsanti della barra (nella stessa altezza). <b>Pro</b>: si vede tutto con le parole, un solo sguardo, la "
           "scelta sta dove già si guarda. <b>Contro</b>: copre i vicini per un momento; non si può eseguire con un clic solo."),
    "g5": ("G5. Gruppo a pista",
           "Tutte le voci sempre visibili su una pista di 28 px con il rettangolo che scorre, come le viste (R322, B1), e la "
           "parola della scelta sotto. <b>Pro</b>: niente di nascosto, stesso linguaggio delle viste. <b>Contro</b>: una pista dice «uno "
           "fra N», quindi vale solo per i modi (Falda e Colmo), non per comandi («Da IFC», «Cancella tutte»); icone piccole; "
           "con quattro voci si capisce solo dal suggerimento."),
    "g6": ("G6. Pila di piccoli, alla Office",
           "Le voci in pulsantini da 24 px su due righe, con la parola accanto, nell'altezza di un pulsante grande. <b>Pro</b>: tutto "
           "visibile con il nome, un clic solo, nessuna faccia che cambia. <b>Contro</b>: la barra si allarga parecchio (vedi i px), "
           "in altezza bassa diventa una fila di icone tutte uguali, si perde «questo è il comando normale»."),
}

CSS = H.CSS + """
html{background:#e6e3dc}
body{margin:0;font:13px/1.35 Inter,"Segoe UI",system-ui,sans-serif;color:#1e1c19;padding:20px 24px;width:1560px}
h1{font-size:22px;font-weight:600;margin:0 0 4px}
h2{font-size:16px;font-weight:600;margin:0 0 2px}
h3{font-size:13px;font-weight:600;margin:12px 0 4px}
p{margin:0 0 6px;color:#514c44;max-width:1180px}
p b{color:#1e1c19}
section{margin:0 0 28px;padding:14px 0 0;border-top:1px solid #cfcbc2}
.states{display:grid;grid-template-columns:1fr 1fr 360px 1fr 1fr;gap:8px;margin:6px 0;align-items:start}
.cell{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 10px 10px;color:var(--text)}
.cell .cap{font-size:11px;color:var(--muted);margin-bottom:6px}
.cell .row{display:flex;gap:2px}
.h-open-g3{min-height:292px}.h-open{min-height:230px}.h-open-low{min-height:210px}.h-open-g4{min-height:96px}
.rowbar{display:grid;grid-template-columns:128px minmax(0,1fr) 54px;gap:8px;align-items:center;margin:0 0 4px}
.rowbar .pn{font-size:12px;color:#514c44}
.rowbar .wlab{font-size:11px;color:#6f685d;text-align:right;font-variant-numeric:tabular-nums}
.note{font-size:12px;color:#514c44;margin:4px 0 8px}
.reco{background:#fff;border-left:3px solid #1e1c19;padding:8px 12px;margin:8px 0;max-width:1180px}
table{border-collapse:collapse;background:#fff;font-size:12px;margin:6px 0}
th,td{border:1px solid #d9d5cc;padding:4px 8px;text-align:left;vertical-align:top}
th{background:#f2f1ed;font-weight:600}
.vs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:6px 0 10px}
.opt{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:6px 10px 8px}
.opt .cap{font-size:11px;color:var(--muted);margin-bottom:6px}
.opt .cap b{color:var(--text)}
.opt .bar{margin-bottom:6px}
.today .b.primary{background:transparent}.today .b.primary .w{font-weight:400}
.vS1 .b.plain{min-width:0}
.vS3 .tall .b.plain,.vS3 .bar.tall .b.plain{width:64px;min-width:64px;padding:0}
.vP1 .b.primary{background:transparent}.vP1 .b.primary .w{font-weight:400}
.vP3 .b.primary{background:transparent;outline:1px solid var(--line);outline-offset:-1px}
.vT2 .ttl{text-transform:none;font-size:11px;letter-spacing:0}
.vT3 .ttl{display:none}
.vL1 .sep{margin:4px 8px}
.vL3 .sep{background:transparent;width:8px;margin:0 4px}
"""


def bars(design: str, modes=("tall",), phases=ORDER, theme="light", faces=None, titles=True) -> str:
    out = []
    for mode in modes:
        for p in phases:
            out.append(f'<div class="rowbar {theme}"><span class="pn">{H.escape(TITLES[p])}</span>'
                       f'<div class="card">{H.bar(p, design, mode, faces=faces, titles=titles)}</div><span class="wlab"></span></div>')
    return "".join(out)


def states(design: str) -> str:
    sub = H.family("plant", "tool_subfield")
    cells = {"tall": [], "low": []}
    wide = ' style="grid-template-columns:1fr 1fr 360px 1fr 360px"' if design == "g3" else ""
    for mode in cells:
        for key, label in STATES:
            face = 1 if key == "changed" else 0
            tall = "h-open" if mode == "tall" else "h-open-low"
            if design == "g3":
                tall = "h-open-g3"
            if design in ("g5", "g6"):
                tall = ""
            elif design == "g4":
                tall = "h-open-g4"
            state = key if design not in ("g5", "g6") or key != "open" else "rest"
            cap = label
            if design == "g3" and key == "changed":
                cap += ": la faccia non cambia, nel menu l'ultima ha il fondo"
                state = "open"
                face = 1
                tall = "h-open-g3"
            if design == "g5" and key == "open":
                cap += ": non si apre, è già tutto lì"
            if design == "g6" and key == "open":
                cap += ": non si apre, è già tutto lì"
            btn = H.grouped(design, sub, state=state, face=face, mode=mode)
            cells[mode].append(f'<div class="cell {mode} {tall if key in ("open", "changed") else ""}"><div class="cap">{cap}</div>'
                               f'<div class="row">{btn}</div></div>')
    others = "".join(H.grouped(design, H.family(p, c), mode="tall") for p, c in
                     (("model", "tool_building"), ("model", "tool_pitch"), ("plant", "strings_auto"), ("plant", "tool_erase_string")))
    return (f'<div class="states light"{wide}>{"".join(cells["tall"])}</div><div class="states light"{wide}>{"".join(cells["low"])}</div>'
            f'<div class="cell light tall" style="display:inline-block"><div class="cap">Le altre famiglie a riposo: Edificio, Falda, Automatico, '
            f'Elimina stringa</div><div class="row" style="gap:8px">{others}</div></div>')


def rest() -> str:
    def sample(cls: str, cap: str, modes=("tall", "low"), design="g2") -> str:
        bars_ = "".join(H.bar("plant", design, m, measure=False, select_on=False, strip=False, only=("Pannelli", "Inverter")) for m in modes)
        return f'<div class="opt {cls}"><div class="cap">{cap}</div>{bars_}</div>'

    rows = [
        ("Pulsante semplice", [
            ("vS1", "<b>S1 oggi.</b> Largo quanto la parola: ritmo irregolare fra parole corte e lunghe."),
            ("", "<b>S2 consigliato.</b> Minimo 48 px, parola 12 px nel colore del testo, 2 px fra pulsanti. Il minimo tiene insieme le parole corte."),
            ("vS3", "<b>S3 griglia.</b> Tutti 64 px, ordinati come un cassetto. Le parole lunghe non ci stanno: andrebbero a capo o accorciate.")]),
        ("Pulsante primario (Posa, Calcola)", [
            ("vP1", "<b>P1 oggi.</b> Uguale agli altri (R158 ha tolto l'accento e non ha messo altro): non si distingue più."),
            ("", "<b>P2 consigliato.</b> Velo <code>field</code> come un pulsante, parola <code>strong</code>. Nessun accento (R104, R158). Spento: senza velo."),
            ("vP3", "<b>P3 col filo.</b> Solo un contorno <code>line</code>. Leggero, ma sembra un campo o un pulsante premuto.")]),
        ("Titolini dei gruppi", [
            ("", "<b>T1 oggi, consigliato.</b> <code>GROUP</code>, 10 px maiuscole, <code>muted</code>, centrato (R159). Regge e spiega i gruppi."),
            ("vT2", "<b>T2 minuscole.</b> 11 px normali. Più leggibile, ma si confonde con le parole dei pulsanti."),
            ("vT3", "<b>T3 senza.</b> Solo per le parole accanto all'icona: lì le parole spiegano già e si guadagnano 17 px in altezza.")]),
        ("Separatori", [
            ("vL1", "<b>L1 oggi.</b> <code>line_soft</code> per tutta l'altezza, fino sotto ai titolini."),
            ("", "<b>L2 consigliato.</b> Lo stesso filo, alto solo quanto i pulsanti: i titolini restano aria, il gruppo si legge di più."),
            ("vL3", "<b>L3 senza filo.</b> Solo 16 px d'aria. Più calmo, ma con molti gruppi in fila la struttura si perde.")]),
    ]
    out = []
    for title, options in rows:
        cells = "".join(sample(c, cap) for c, cap in options)
        out.append(f'<h3>{title}</h3><div class="vs light">{cells}</div>')
    return "".join(out)


def page() -> str:
    parts = ['<h1>Barra degli strumenti: i pulsanti raggruppati</h1>'
             '<p>Studio 26 (R333), 02/11/2026. Barre vere delle sei fasi: parole, tasti e icone letti dalla finestra (<code>estrai.py</code>), '
             'colori da <code>theme_colors.derive</code> con accento indigo. Raggio 6, simboli piatti, niente ombre, niente accento sui pulsanti. '
             'Le barre sono vive: passaggio del puntatore, clic sulla freccia o tasto destro aprono, una voce scelta va sulla faccia solo se è un modo di '
             'disegno (Fila, Colmo), non se è un comando secondo la regola del README. '
             'A destra di ogni barra la larghezza misurata dei gruppi (senza la striscia di stato). Il testo è Inter se installato, se no Segoe UI. '
             'Con <code>?only=g2</code> (g0...g6, r, p) si vede una sezione sola.</p>'
             '<p>Nel disegno «Pitch» è scritto «Falda»: nel programma la parola sotto l\'icona è ancora inglese (voce <code>pgettext("roof", "Pitch")</code> senza traduzione, vedi README).</p>']
    for key, (title, text) in DESIGNS.items():
        parts.append(f'<section id="{key}" class="live"><h2>{title}</h2><p>{text}</p>{states(key)}'
                     f'<h3>Le sei barre, altezza piena</h3>{bars(key)}'
                     f'<h3>Modellazione e Impianto, altezza bassa</h3>{bars(key, ("low",), ("model", "plant"))}</section>')
    parts.append(f'<section id="r"><h2>Il resto della barra: pulsante semplice, primario, titolini, separatori</h2>'
                 f'<p>Ogni riquadro: due gruppi di Impianto (Pannelli, Inverter) in altezza piena (69 px) e bassa (47 px). Il pulsante raggruppato qui è G2; le altre scelte sono quelle del titolo di ogni riquadro.</p>{rest()}</section>')
    faces = {"tool_pitch": 1, "tool_subfield": 1}
    parts.append('<section id="p" class="live"><h2>La proposta intera: G2 con S2, P2, T1, L2</h2>'
                 '<div class="reco"><b>Regola della faccia.</b> Un modo di disegno scelto dalla tendina va sulla faccia e resta acceso finché è in uso; un comando secondo '
                 '(«Modello», «Da IFC», «Est-ovest», «Completa», «Cancella tutte») si esegue e la faccia non cambia. La faccia non cambia mai da sola, né per un tasto, né perché la voce si è spenta: '
                 'si spegne la parte comando, la striscia resta viva.</div>'
                 f'<h3>Altezza piena (qui Falda e Sottocampo sono su Colmo e Fila: l\'ultimo modo usato)</h3>{bars("g2", faces=faces)}'
                 f'<h3>Altezza bassa, solo icone con i titolini (47 px)</h3>{bars("g2", ("low",))}'
                 f'<h3>Altezza bassa con la larghezza che avanza: le parole accanto, senza titolini (31 px invece di 47, vedi studio 27)</h3>{bars("g2", ("beside",), titles=False)}'
                 f'<h3>Tema scuro</h3>{bars("g2", phases=("model", "plant"), theme="dark", faces=faces)}{bars("g2", ("low",), ("model", "plant"), theme="dark")}</section>')
    return "\n".join(parts)


TEMPLATE = """<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Barra degli strumenti</title>
<style>{tokens}{css}</style></head>
<body>{sprite}{body}
<script>
const only=new URLSearchParams(location.search).get('only');
if(only)document.querySelectorAll('section').forEach(s=>{{if(s.id!==only)s.style.display='none'}});
{js}
</script></body></html>
"""

if __name__ == "__main__":
    html = TEMPLATE.format(tokens=H.tokens_css(), css=CSS, sprite=H.sprite(), body=page(), js=H.JS)
    (H.HERE / "bozzetti.html").write_text(html, encoding="utf-8", newline="\n")
    print(len(html))
