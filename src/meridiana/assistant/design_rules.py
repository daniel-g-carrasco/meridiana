"""What Meridio knows to advise the design (R462, Daniel 06/11/2026: «teniamolo in memoria, Meridio deve sapere tutte
queste cose per consigliare le scelte migliori»), read by the tool `design_rules`.

The passages are built from the data and the code the program designs with, never copied into a prompt, so that
Meridio and the program cannot disagree, and each carries its source:
- the optimizers by maker and family: architecture, modules per unit, how strings are sized, units of one and of two
  modules in one string, partial installation, strings in parallel, orientations, module power, the string rules per
  inverter (catalog/data/optimizer_rules.json, study 35);
- SolarEdge's tables, continuous and connected power per string, residential and commercial (the same file, read by
  energy/optimizers.py), and how the automatic proposals use them (optimizers.proposal_tiers);
- the DC/AC band of the inverter sizing (energy/sizing.py, study 34 sect. 6) and the ratio asked by default
  (settings.dc_ac_ratio);
- the preferred makers (catalog/data/preferred_makers.json, study 34);
- the fire brigade's rules for sub-fields and roofs (rules.py N12-N16, DCPREV 14030/2025) and how the layout applies
  them (layout.py, checks.FIRE_SOURCE).

`search(query, inverter, optimizer, module_w)`: the passages that match the words of the query (Italian or English)
and the models named in it, the best first; with an inverter or an optimizer, also `advice`, what the program's own
rules give for that pair (energy/optimizers.rules_for for SolarEdge, catalog/rules.string_rule for the others).
No Qt."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "catalog" / "data"
RULES_FILE = "catalog/data/optimizer_rules.json"
MAKERS_FILE = "catalog/data/preferred_makers.json"
HITS = 6

# the words of one fire rule, beside those of its topic
FIRE_KEYWORDS = {
    "N12": "tensione circuito aperto oltre 1500 V campo di applicazione",
    "N13": "attivita soggetta controlli segnaletica cartello sezionamento manutenzione registro termografia",
    "N14": "non soggetta buona tecnica",
    "N15": "sottocampi sottocampo grandi dimensioni massime 20 m corridoi 2 m bordo 1 m evacuatori fumo aperture "
           "lucernari impianti in copertura shed compartimentazione propagazione classe reazione BAPV",
    "N16": "integrati integrazione BIPV involucro",
    "layout": "posa automatica sottocampi corridoi bordo evacuatori fascia di rispetto",
}

# the words a designer uses for each topic, Italian and English, so that a question in either finds its passages
KEYWORDS = {
    "family": "ottimizzatore ottimizzatori famiglia architettura scheda moduli per unita optimizer family architecture",
    "mixing": "singolo singoli doppio doppi misto misti mescolare insieme stessa stringa un modulo due moduli uso misto "
              "modulo da solo dispari mixing single double one module two modules",
    "partial": "parziale parzialmente alcuni moduli selettiva selettivo installazione partial selective deployment",
    "parallel": "parallelo parallele stesso mppt ingresso stringhe lunghezze diverse stessa lunghezza parallel input",
    "orientations": "orientamenti orientamento falde diverse esposizioni inclinazioni est ovest orientation tilt",
    "module_power": "potenza modulo moduli watt grandi massima tolleranza module power rated",
    "strings": "lunghezza stringa quanti moduli massimo minimo stringa lunga inverter compatibile compatibilita "
               "string length",
    "table": "potenza continua collegata per stringa tabella quanti ottimizzatori quanti moduli stringhe synergy "
             "continuous connected power table",
    "policy": "proposte automatiche automatica superare sopra potenza continua collegata mano avviso automatic proposal",
    "makers": "marca marche altra marca altre marche compatibili compatibilita inverter di altre marche other makers",
    "dcac": "rapporto dc/ac dcac sovradimensionamento sottodimensionamento fascia taglia inverter dimensionamento "
            "quanti inverter ratio band sizing",
    "preferred": "marche preferite preferenziali preferiamo marca produttori fornitori quali usiamo brand makers",
    "fire": "vigili fuoco vvf antincendio prevenzione incendi dcprev fire brigade",
}
_FUNCTION = {"optimizer": "a power optimizer (it tracks each module's maximum power)",
             "safety": "a safety device only (rapid shutdown and monitoring): it does not optimize"}
_SIZING = {"solaredge_tables": "the strings follow SolarEdge's tables (fixed string voltage, no MPPT in the inverter)",
           "long_string": "a long string: the count of optimizers and the power per string of the maker's table, the "
                          "inverter's MPPT window does not limit the length",
           "inverter_window": "as without optimizers: the inverter's MPPT window and voltage"}
_MIXING = {"no": "no: units of one and of two modules never in one string",
           "one_single": "yes, but at most one optimizer with a single module per string, otherwise all of them",
           "not_stated": "not stated by the maker: only by hand, with a warning",
           "n/a": "does not apply: one module per unit",
           "with_safety": "with the safety-only units in the same string (selective deployment)",
           "with_optimizer": "with the optimizing units in the same string",
           "ok": "yes"}
_PARTIAL = {"no": "no: every module under that inverter needs the optimizer",
            "conditions": "yes, with conditions", "not_stated": "not stated by the maker"}


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _stems(text: str) -> list[str]:
    """The words of a query, folded and cut to five letters (as search_manual does), the short ones left out; and
    «dc/ac» kept whole."""
    t = fold(text)
    out = [w[:5] for w in re.findall(r"\w+", t) if len(w) > 3 and not w.isdigit()]
    return out + ["dc/ac"] * ("dc/ac" in t or "dcac" in t)


def _number(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads((DATA / "optimizer_rules.json").read_text(encoding="utf-8"))


def _passage(pid: str, topic: str, title: str, text: str, source: str, models=(), patterns=(), keywords="") -> dict:
    return {"id": pid, "topic": topic, "title": title, "text": text, "source": source, "models": list(models),
            "patterns": list(patterns), "keywords": keywords}


def _family_passages(maker: str, fam: dict) -> list[dict]:
    name, fid, pattern = fam.get("name", fam["id"]), fam["id"], fam.get("optimizers", "")
    per = fam.get("modules_per_unit") or [1]
    out = [_passage(fid, "family", name,
                    f"{name}: {_FUNCTION.get(fam.get('function'), fam.get('function'))}; "
                    f"{' or '.join(str(p) for p in per)} module(s) per unit; {_SIZING.get(fam.get('sizing'), '')}.",
                    f"{fam.get('datasheet', '')}; {RULES_FILE}", (maker,), (pattern,))]
    mixing = fam.get("mixing") or {}
    if mixing.get("state"):
        text = f"{name}, units of one and of two modules in one string: {_MIXING.get(mixing['state'], mixing['state'])}"
        if mixing.get("with"):
            text += f", with {mixing['with']} in the same string"
        out.append(_passage(f"{fid}.mixing", "mixing", f"{name}: singles and doubles", text + ".",
                            mixing.get("source") or RULES_FILE, (maker,), (pattern,)))
    partial = fam.get("partial") or {}
    if partial.get("state"):
        text = f"{name}, partial installation (optimizers on some modules only): {_PARTIAL.get(partial['state'])}"
        text += f": {partial['rule']}" if partial.get("rule") else ""
        out.append(_passage(f"{fid}.partial", "partial", f"{name}: partial installation", text + ".",
                            partial.get("source") or RULES_FILE, (maker,), (pattern,)))
    par = fam.get("parallel") or {}
    if par:
        bits = ["strings in parallel of the same length" if par.get("same_length") else
                "strings in parallel may differ in length and orientation"]
        if par.get("max_strings_per_mppt"):
            bits.append(f"at most {par['max_strings_per_mppt']} string per MPPT")
        if par.get("length_mismatch_max"):
            bits.append(f"the shortest at most {round(100 * par['length_mismatch_max'])} % shorter than the longest")
        level = f" (level {par.get('level', 'fail')})" if par.get("same_length") or par.get("max_strings_per_mppt") else ""
        out.append(_passage(f"{fid}.parallel", "parallel", f"{name}: strings in parallel",
                            f"{name}: {'; '.join(bits)}{level}.",
                            par.get("source") or RULES_FILE, (maker,), (pattern,)))
    orient = fam.get("orientations") or {}
    if orient.get("state"):
        text = ("one string may run over several orientations" if orient["state"] == "free" else
                "one orientation and tilt per string")
        out.append(_passage(f"{fid}.orientations", "orientations", f"{name}: orientations", f"{name}: {text}.",
                            orient.get("source") or RULES_FILE, (maker,), (pattern,)))
    power = fam.get("module_power") or {}
    if power:
        text = (f"{name}: the module's STC power at most {power.get('factor', 1.0):g} times the optimizer's rated input "
                f"power{' per module' if power.get('per_module') else ''} (level {power.get('level', 'fail')})")
        out.append(_passage(f"{fid}.module_power", "module_power", f"{name}: module power", text + ".",
                            power.get("source") or fam.get("datasheet", ""), (maker,), (pattern,)))
    rows = fam.get("string_rules") or []
    if rows:
        said = []
        for row in rows:
            piece = f"inverters {row['inverters']}: "
            if row.get("min") or row.get("max"):
                piece += f"{row.get('min', '?')}-{row.get('max', '?')} optimizers"
                piece += f", {_number(row['p_string_w'])} W per string" if row.get("p_string_w") else ""
            else:
                piece += {"unknown": "length as without optimizers", "no": "not compatible"}.get(row.get("state"),
                                                                                                 row.get("state", ""))
            piece += " (consult the maker first)" if row.get("consult") else ""
            piece += f" [{row.get('source', '')}]"
            said.append(piece)
        out.append(_passage(f"{fid}.strings", "strings", f"{name}: string rules by inverter",
                            f"{name}: " + "; ".join(said) + ".", fam.get("datasheet", "") or RULES_FILE,
                            (maker,), (pattern,)))
    return out


def _solaredge_tables(se: dict) -> list[dict]:
    out = []
    for model, entry in (*se["commercial"].items(), *(("P800p/P850/P950/P1100", se["commercial_p"]),)):
        for column, row in entry["table"].items():
            lo, mlo, hi, mhi, cont, one, many_w, many = row
            fewer = "1 string" if many == 2 else f"1-{many - 1} strings"
            out.append(_passage(
                f"solaredge.{model}.{column}", "table", f"SolarEdge {model} on {column}",
                f"SolarEdge {model} on {column} (or a Synergy unit of the same power): {lo}-{hi} optimizers per string "
                f"({mlo}-{mhi} modules, two per optimizer); continuous power {_number(cont)} W per string; connected "
                f"at STC up to {_number(one)} W per string with {fewer}, {_number(many_w)} W with {many} strings or "
                f"more.", f"SolarEdge {entry['source']}; {RULES_FILE}", ("SolarEdge", *model.split("/"), column)))
    for key in ("residential_s", "residential_p"):
        entry = se[key]
        for grid, (lo_long, lo_short, hi, cont, over, ac_rule) in entry["table"].items():
            series = "S440, S500, S500B, S650B" if key == "residential_s" else "P370-P601"
            text = (f"SolarEdge {series} on a residential inverter ({grid.replace('_', ' ')}): {lo_long} optimizers "
                    f"per string at least for {', '.join(entry['long'])} ({lo_short} for the others), {hi} at most; "
                    f"continuous power {_number(cont)} W per string")
            text += (f"; connected up to {_number(over[0])} W with one string, {_number(over[1])} W with two or more"
                     if over else "")
            text += ("; an inverter whose AC power is within the continuous power takes up to its own maximum DC power"
                     if ac_rule else "")
            out.append(_passage(f"solaredge.{key}.{grid}", "table", f"SolarEdge {series}, {grid}", text + ".",
                                f"SolarEdge {entry['source']}; {RULES_FILE}",
                                ("SolarEdge", *(m.strip() for m in series.split(",")))))
    out.append(_passage("solaredge.synergy", "table", "SolarEdge Synergy inverters", se["note"],
                        f"SolarEdge DS-000297-EU (05/04/2026); {RULES_FILE}",
                        ("SolarEdge", "SE50K", "SE66.6K", "SE90K", "SE100K")))
    out.append(_passage(
        "solaredge.policy", "policy", "Automatic proposals and the continuous power",
        "The automatic stringing never goes above the continuous power on SolarEdge's residential tables. On the "
        "commercial ones (S1000, S1200, S1400, P-series) it stays within the continuous power first, then within the "
        "power the table allows connected per string, above the continuous power on purpose. By hand the designer may "
        "go above the continuous power: a warning with the source (opt_continuous); within the connected power of a "
        "commercial table it is an information. Beyond the tables, SolarEdge Designer.",
        "Daniel 06/11/2026 (R456 answer 1); energy/optimizers.py proposal_tiers; docs/studio/35-ottimizzatori-marche.md "
        "sect. 3 and 4.3; SolarEdge DS-000105-IT p. 3 notes 6 and 13; DS-000205-EU p. 3 note 11", ("SolarEdge",)))
    return out


def _placing() -> dict:
    """How an imported IFC model is placed on the plan (R454), from the constants the program places it with."""
    from .. import ifc_import, ifc_place, move
    steps = move.ANGLE_STEPS

    def number(v, _places=0):
        return f"{v:g}"
    return _passage(
        "ifc.place", "ifc", "Placing an imported IFC model on the plan",
        "After «Add» in the IFC import the model is not added at once: the plan goes into «Place» mode. The outlines of "
        "its bodies (with roof planes and obstacles) follow the pointer by their middle; a corner of the model takes a "
        f"corner of a building already drawn within {ifc_place.SNAP_PX} screen pixels, else a side (Ctrl held: no snap; "
        f"F3 switches the snaps off). R turns it by {number(steps[''], 0)} degrees ({number(steps['ctrl'], 0)} with Ctrl, "
        f"{number(steps['shift'], 0)} with Shift), the wheel held with Shift turns it too; the arrows nudge it "
        f"({number(move.NUDGE[''], 2)} m, {number(move.NUDGE['shift'], 0)} m with Shift) and hold it still; M lets the "
        "mouse take it again. A click or Enter lays it, Esc gives the import up. C opens its coordinates: UTM, latitude "
        "and longitude, or metres East and North of the site, of the IFC file's origin, with the turn from the file's axes "
        "to the north; the file's own georeferencing (IfcMapConversion, or a named IfcSite) is proposed first; the "
        f"distance from the site is shown and beyond {number(ifc_import.FAR_KM, 0)} km a warning says to check them. "
        "Laid over a building already drawn, the program asks: Replace (the building goes, the sub-fields drawn on it go "
        "to the model's roof under them), Keep both, Beside (moved the least to stand "
        f"{number(ifc_place.GAP, 0)} m beside it), or go on placing. The bodies stay one group with their base heights; "
        "moved or turned later they move together, and the IFC «plant only» and the DXF in the imported file's frame "
        "still lie on the architect's model. Ctrl+Z takes the whole import back in one step. In the import window the "
        "other ways stay: at the middle of the plan, where the file says, or the site moved to the file.",
        "Daniel 06/11/2026 (R454); ifc_place.py, quick/backend/plan_place.py; tests/nucleo/test_ifc_place.py, "
        "tests/quick/percorsi/test_native_posiziona.py",
        keywords="ifc importare importato posizionare posiziona posa modello architetto mouse coordinate utm "
                 "georeferenziazione sovrapposto sovrapposizione sostituire affiancare ruotare ruota place placing "
                 "position coordinates overlap replace beside")


def _dcac() -> dict:
    from .. import settings
    from ..energy import sizing
    wanted = float(settings.Settings().dc_ac_ratio) if hasattr(settings, "Settings") else 1.1
    low, high = sizing.band(wanted)
    w, lo, hi, below, above, floor = (f"{v:.2f}".replace(".", ",") for v in (
        wanted, low, high, sizing.BAND_BELOW, sizing.BAND_ABOVE, sizing.BAND_FLOOR))
    return _passage(
        "dcac.band", "dcac", "DC/AC ratio: the band of the sizing",
        f"The inverters are sized for the DC/AC ratio asked, {w} by default (Settings, and each project's energy "
        f"page). Taken as asked: from {below} below it (never under {floor}, unless less "
        f"was asked) to {above} above it: {lo}-{hi} for {w}. Order: within the band, below it but at "
        f"least 1, above it, under 1 (said); within the band {sizing.CRITERION}. Several inverters: the ratios closest "
        f"to each other (R428). Single-phase inverters are not proposed together, nor with three-phase ones.",
        "energy/sizing.py (BAND_BELOW, BAND_ABOVE, BAND_FLOOR, band, CRITERION); settings.dc_ac_ratio; "
        "docs/studio/34-catalogo-marche-fonti.md sect. 6 (R420, R428) and sect. 10 decision 2")


def _preferred() -> list[dict]:
    data = json.loads((DATA / "preferred_makers.json").read_text(encoding="utf-8"))
    status = data.get("status", "")
    return [_passage(f"preferred.{kind}", "preferred", f"Preferred makers: {kind}",
                     f"Preferred makers of {kind}, in order: {', '.join(names)}. Status: {status}.",
                     f"{MAKERS_FILE}; docs/studio/34-catalogo-marche-fonti.md", names)
            for kind, names in data["kinds"].items()]


def _fire() -> list[dict]:
    from .. import checks, rules
    out = []
    facts = rules.Facts()
    for rule in rules.RULES:
        if rule.id not in ("N12", "N13", "N14", "N15", "N16"):
            continue
        try:
            paragraphs = rule.paragraphs(facts)
        except Exception:  # noqa: BLE001  a rule that needs the project's facts: its title only
            paragraphs = []
        out.append(_passage(f"fire.{rule.id}", "fire", rules.title(rule, facts), " ".join(paragraphs),
                            f"{rule.source()} (rules.py {rule.id})", keywords=FIRE_KEYWORDS[rule.id]))
    out.append(_passage(
        "fire.layout", "fire", "How Meridiana lays the modules under the fire brigade's rules",
        "With «fire rules» on (an activity subject to fire controls): 1 m free from the roof edge, groups of modules of "
        "at most 20 m in every direction separated by corridors of 2 m, 1 m around smoke vents, openings and the plant "
        "on the roof (each exclusion with its own clearance); a layout by hand is checked for groups beyond 20 m and "
        "corridors narrower than 2 m.", f"{checks.FIRE_SOURCE}; layout.py; checks.manual_items",
        keywords=FIRE_KEYWORDS["layout"]))
    return out


def _partial_in_the_program(data: dict) -> list[dict]:
    """How the program applies the partial installation (R456, Daniel's answer 6 of 06/11/2026), family by family, with
    the pages its checks cite (energy/optimizer_strings.partial_checks, PARTIAL_SOURCES) and what it does by itself."""
    from ..energy import optimizer_strings, plant
    out = [_passage(
        "partial.program", "partial", "Optimizers on some modules only: how Meridiana does it",
        "The designer chooses the modules with an optimizer on the plan of the Plant (selected modules: «Optimizer on these "
        "modules», «No optimizer on these modules»), or lets Meridiana put them on the modules the obstacles shade in the "
        "design window («Optimizers on the modules in the shadow»: the same shadows the layout keeps out of); only on "
        "inverters with MPPT whose optimizers admit it (Huawei SUN2000-450W-P2/600W-P and SUN2000-600W-PA0, Tigo TS4-A-O). "
        "A string with both kinds is sized as without optimizers (the inverter's window); the year computes it on one I/V "
        "curve, the plain modules at the string's current and each optimizer at its module's maximum power point. On a "
        "roof with the rows in shade at Rho (SUN2000-10KTL-M1): 10.950 kWh without, 11.635 kWh with optimizers on the 12 "
        "shaded modules of 18, 11.637 kWh on all of them.",
        f"energy/plant.py (optimized_after, shaded_keys, energy[\"strings\"][\"{plant.PARTIAL}\"]); "
        "energy/electrical_network.mixed_curve; tests/calcoli/test_partial_optimizers.py", ("Huawei", "Tigo"))]
    rules = {
        "huawei_sun2000_p": "optimizers anywhere in the string, one orientation in it, sized as without optimizers; on an "
                            "MPPT with two inputs only on one string, or on every module of both identical strings "
                            "(partial optimization of parallel strings is not recommended): a warning",
        "huawei_pa0": "possible after the inverter's software update, one input per MPPT",
        "tigo_ts4_o": "only on a string with its own MPPT, none in parallel (a failure otherwise), one orientation and "
                      "tilt (a failure otherwise); the other modules without TS4 or with TS4-A-S",
        "huawei_merc": "note 8 of the datasheet wants a MERC on every module under the same inverter; the selective "
                       "optimization was asked to Huawei on 06/11/2026 and is to be confirmed: a warning, never proposed",
        "sungrow_sp": "the datasheet does not say: a warning, ask Sungrow",
    }
    for maker, entry in data.items():
        if not isinstance(entry, dict):
            continue
        for fam in entry.get("families", []):
            rule = rules.get(fam["id"])
            if rule is None:
                continue
            source = optimizer_strings.PARTIAL_SOURCES.get(fam["id"]) or (fam.get("partial") or {}).get("source", "")
            out.append(_passage(f"{fam['id']}.partial.program", "partial", f"{fam.get('name', fam['id'])}: partial "
                                "installation in Meridiana's checks", f"{fam.get('name', fam['id'])}: {rule}.",
                                f"{source}; energy/optimizer_strings.partial_checks", (maker,),
                                (fam.get("optimizers", ""),)))
    out.append(_passage(
        "solaredge.partial.program", "partial", "SolarEdge: never on some modules only",
        "SolarEdge's inverters work at a fixed string voltage, «progettato specificamente per il funzionamento con "
        "ottimizzatori di potenza», and SolarEdge's tables count the string in optimizers: every module needs one. No "
        "SolarEdge document of the archive admits a module without (searched on 06/11/2026); a module named without on a "
        "SolarEdge inverter is a failure of the checks and the year counts one on it.",
        "SolarEdge SE25K-SE33.3K, Italian datasheet, p. 1; DS-000105-IT p. 3; DS-000205-EU p. 3; "
        "energy/plant._check_partial_fixed", ("SolarEdge",)))
    return out


def _faces() -> dict:
    """A string over more than one roof face (R433, Daniel's rule of 05/11/2026) and what the program does with it."""
    from ..energy import faces, plant
    return _passage(
        "faces", "orientations", "A string over more than one roof face",
        "Daniel's rule: a string stays on its own face first; in the same building, with optimizers that keep every "
        "module at its maximum power point (SolarEdge, Huawei, Sungrow, Tigo TS4-A-O), the proposal lets it go on over "
        "another face only when the modules left on a face make no string by themselves, with a warning; without "
        "optimizers only when the designer asks (the proposal's choice «a string may go on over another face», or drawn by "
        "hand), the warning giving the estimated loss for the different exposures in % and kWh; between different "
        "buildings only by hand. The estimate: hour by hour the string carries one current, the modules below it are "
        "bypassed (module-level bypass), those on optimizers give their own. A capannone East-West at 15° near Milan: one "
        "string over both faces 14,5 % below two strings one a face in the year of the electrical network (estimate "
        "16,7 %); with Huawei's SUN2000-450W-P2 0,3 %.",
        f"Daniel 05/11/2026 (R433); energy/faces.py (check «{faces.KEY}»); energy/plant._continue_on_faces "
        f"(energy[\"strings\"][\"{plant.ACROSS}\"]); SolarEdge Single String Design Guidelines v1.1 p. 1; "
        "tests/calcoli/test_string_faces.py",
        keywords="falda falde piu falde stringa su due falde altra falda proseguire continuare tetto a due falde "
                 "edifici diversi stima perdita esposizione roof face faces")


def _free() -> dict:
    """Inverters and strings for the modules in no string only (R522, Daniel 07/11/2026)."""
    from ..energy import sizing
    low, high = (f"{v:.2f}".replace(".", ",") for v in sizing.band(1.1))
    return _passage(
        "free", "free", "Inverters and strings for the modules in no string only",
        "When part of the modules is strung by hand and others are left, Meridiana proposes inverters and strings for the "
        "modules in no string only: the strings, inverters and optimizers there are stay byte for byte. Where: the window "
        "«Choose automatically» (sizing) with «Only the n modules in no string», on by itself when some modules are in "
        "strings and others are left; the window «String automatically» with «only the n modules in no string» (the "
        "inverters there are only); in Plant the plan's menu «Propose inverters and strings for the modules in no "
        "string». The same rules as the automatic choice: the DC/AC band (" + low + "-" + high + " for 1,10), the brand "
        "chosen with the favourites first, the optimizers, a string over more faces (R433), optimizers on part of the "
        "modules (R456). Two ways, and the program says which and why: first the free MPPT inputs of the inverters there "
        "are, if their strings pass the checks and no inverter that takes them goes above the band (nothing added); "
        "otherwise inverters added after the others, sized at the ratio asked on the free modules alone, or on those the "
        "free inputs leave when they take part of them; between the two, the fewer inverters taking free modules outside "
        "the band (each inverter's ratio), then the fewer added (the others listed as alternatives). A sub-field that sends its strings to an inverter gets no new one. The ratio is given for the "
        "whole plant and for each inverter. One undo step.",
        "Daniel 07/11/2026 (R522); energy/sizing.py choose_free (FREE_INPUTS, FREE_NEW); quick/backend/plant.py "
        "sizeInvertersFor; tests/calcoli/test_free_modules.py",
        keywords="moduli scollegati rimasti liberi senza stringa solo i moduli scollegati inverter nuovi ingressi mppt "
                 "liberi completa stringatura parte collegata a mano free modules in no string")


@lru_cache(maxsize=1)
def passages() -> tuple:
    data = _data()
    out = []
    for maker, entry in data.items():
        if not isinstance(entry, dict):
            continue
        text = f"{maker}'s optimizers: architecture {entry.get('architecture', '')}."
        if entry.get("other_makers"):
            om = entry["other_makers"]
            text += f" With inverters of other makers: {om.get('state')} ({om.get('why', '')})."
        out.append(_passage(f"{maker.lower()}.makers", "makers", f"{maker}: architecture and other makers",
                            text + (" " + entry["note"] if entry.get("note") and maker != "SolarEdge" else ""),
                            f"{RULES_FILE} ({maker})", (maker,)))
        for fam in entry.get("families", []):
            out += _family_passages(maker, fam)
    out += _solaredge_tables(data["SolarEdge"])
    out += _partial_in_the_program(data)
    out.append(_faces())
    out.append(_free())
    out.append(_placing())
    out.append(_dcac())
    out += _preferred()
    out += _fire()
    return tuple(out)


# the models named in a question: SolarEdge's inverters and optimizers, Huawei's, Sungrow's, Tigo's
_INVERTER = re.compile(r"\b(SE\s?\d+(?:[.,]\d+)?\s?K|SUN2000-\d+K(?:TL)?-[A-Z0-9]+|SUN5000-\d+K-[A-Z0-9]+|"
                       r"SG\d+(?:\.\d)?(?:RT|RS|CX)[-A-Z0-9]*|SH\d+(?:\.\d)?RS)\b", re.IGNORECASE)
_OPTIMIZER = re.compile(r"\b(S(?:440|500B?|650B|1000|1200|1400)|P(?:370|401|404|485|500|505|601|800P|850|950|1100)|"
                        r"SUN2000-(?:450W-P2|600W-PA?0?|600W-P)|MERC-\d+W-PA?0?|TS4-A-[A-Z0-9]+|SP600S)\b", re.IGNORECASE)
_MODULE_W = re.compile(r"\b(\d{3})\s?(?:W|Wp|watt)\b", re.IGNORECASE)


def models_in(text: str) -> tuple[str, str, float | None]:
    """(inverter, optimizer, module W) named in a question, "" or None when not."""
    inv = _INVERTER.search(text or "")
    opt = _OPTIMIZER.search(text or "")
    watts = _MODULE_W.search(text or "")
    inverter = re.sub(r"\s", "", inv.group(1)).upper().replace(",", ".") if inv else ""
    return inverter, opt.group(1).upper() if opt else "", float(watts.group(1)) if watts else None


def _matches(p: dict, model: str) -> bool:
    if not model:
        return False
    if any(fold(m) == fold(model) for m in p["models"]):
        return True
    return any(pat and re.search(pat, model, re.IGNORECASE) for pat in p["patterns"])


def _score(p: dict, stems: list[str], inverter: str, optimizer: str) -> float:
    keys = fold(f"{KEYWORDS.get(p['topic'], '')} {p.get('keywords', '')}")
    hay = f"{keys} {fold(p['title'])} {fold(p['text'])}"
    hits = sum(s in hay for s in set(stems))
    score = 10 * hits + 3 * sum(s in keys for s in set(stems)) + 4 * sum(s in fold(p.get("keywords", ""))
                                                                       for s in set(stems))
    if _matches(p, optimizer):
        score += 25
    if inverter and (inverter.lower() in fold(p["text"]) or _matches(p, inverter)):
        score += 20 if p["topic"] in ("table", "strings") else 5
    return score if hits or score >= 20 else 0


def _record(kind: str, model: str) -> dict | None:
    from .. import catalog
    want = fold(model).replace(" ", "")
    found = catalog.search(kind, model, limit=40)
    exact = [r for r in found if fold(r.get("model", "")).replace(" ", "") == want]
    return (exact or found or [None])[0]


def advise(inverter: str = "", optimizer: str = "", module_w: float | None = None) -> dict:
    """What the program's own rules say for an inverter, an optimizer and a module's power, as the stringing uses them."""
    from .. import catalog
    from ..catalog import rules as catalog_rules
    from ..energy import optimizers as se
    out: dict = {}
    inv_rec = _record("inverters", inverter) if inverter else None
    if inverter:
        out["inverter"] = (f"{inv_rec.get('manufacturer', '')} {inv_rec.get('model', '')}".strip() if inv_rec else
                           f"{inverter}: not in the catalogue")
    fixed = se.fixed_voltage(inv_rec) if inv_rec else None
    if fixed is not None:                                   # SolarEdge: the tables
        records = catalog.search("optimizers", manufacturer="SolarEdge", limit=None)
        rows, pick, toggled = [], None, set()
        for rec in records:
            opt = se.Optimizer.from_record(rec)
            rules, why = se.rules_for(opt, fixed)
            row = {"optimizer": opt.name, "modules_per_optimizer": opt.per_unit, "rated_w": opt.rated_w}
            if module_w:
                need = opt.per_unit * module_w
                row["module_power"] = (f"{opt.per_unit} x {module_w:g} W = {need:g} W of {opt.rated_w:g} W: "
                                       f"{'fits' if need <= opt.rated_w + 1e-6 else 'too much'}")
            if rules is None:
                row["fits"] = False
                row["why"] = why
            else:
                row["fits"] = not module_w or opt.per_unit * module_w <= opt.rated_w + 1e-6
                row["rules"] = {"optimizers_per_string": f"{rules.opt_min}-{rules.opt_max}",
                                "modules_per_string": f"{rules.mod_min}-{rules.mod_max}" if rules.mod_max else "",
                                "continuous_w": rules.p_cont, "connected_w_fewer": rules.p_one,
                                "connected_w_many": rules.p_many, "many_strings": rules.many,
                                "column": rules.column}
                row["source"] = rules.source
                row["warnings"] = [f"{label} [{src}]" for _k, label, _detail, src in rules.warnings]
                if any(k == "toggle" for k, *_rest in rules.warnings):
                    toggled.add(opt.model.upper())
            rows.append(row)
        # the order of energy/optimizers.suggest: on a commercial inverter two modules on S1000, S1400, S1200, then
        # one module on the residential S-series; the first whose table takes the inverter, without the 850 V toggle
        commercial = bool(fixed.unit_model and fixed.grid != "single_phase")
        options = (*(se.COMMERCIAL_ORDER if commercial else ()), *se.RESIDENTIAL_ORDER)
        by_model = {r["optimizer"].split()[-1].upper(): r for r in rows}
        pick = next((by_model[m] for m in options if m in by_model and by_model[m].get("fits") and m not in toggled),
                    None)
        order = {m: i for i, m in enumerate(options)}
        named = fold(optimizer)
        rows.sort(key=lambda r: (fold(r["optimizer"].split()[-1]) != named, not r.get("fits"),
                                 order.get(r["optimizer"].split()[-1].upper(), 99)))
        out["optimizers"] = [r for r in rows if r.get("fits") or fold(r["optimizer"].split()[-1]) == named][:3] + \
            [{"optimizer": r["optimizer"], "why": (r.get("why") or r.get("module_power", ""))[:160]}
             for r in rows if not r.get("fits") and fold(r["optimizer"].split()[-1]) != named][:5]
        if pick:
            out["program_would_choose"] = (f"{pick['optimizer']}, {pick['modules_per_optimizer']} module(s) per "
                                           "optimizer: the first of SolarEdge's current S-series whose table takes "
                                           "this inverter and whose rated power takes the module(s) (the module's "
                                           "Voc and Isc are checked with its datasheet once chosen)")
            out["program_would_choose_source"] = "energy/optimizers.py suggest (COMMERCIAL_ORDER, RESIDENTIAL_ORDER)"
        out["note"] = ("SolarEdge inverters hold a fixed string voltage and take only SolarEdge optimizers "
                       f"[{se.SINGLE}]")
    elif optimizer:
        rec = _record("optimizers", optimizer)
        fam = catalog_rules.family(rec) if rec else None
        if fam is not None:
            out["family"] = fam.name
            if inv_rec is not None:
                rule = catalog_rules.string_rule(fam, inv_rec)
                out["string_rule"] = {"state": rule.state, "optimizers_min": rule.minimum,
                                      "optimizers_max": rule.maximum, "p_string_w": rule.p_string_w,
                                      "consult_maker": rule.consult, "why": rule.why, "source": rule.source}
            if module_w and rec:
                factor = float((fam.raw.get("module_power") or {}).get("factor") or 1.0)
                rated = float(rec.get("rated_input_power_w") or 0)
                per = 2 if (fam.raw.get("module_power") or {}).get("per_module") else 1
                limit = rated * factor / per if rated else math.nan
                out["module_power"] = (f"{module_w:g} W against {limit:g} W allowed per module ({rated:g} W rated, "
                                       f"factor {factor:g}): {'fits' if module_w <= limit + 1e-6 else 'too much'} "
                                       f"[{(fam.raw.get('module_power') or {}).get('source', fam.datasheet)}]")
    return out


def fitted(out: dict, limit: int) -> dict:
    """`out` within `limit` characters of JSON: the last passages dropped first (their ids kept in `more`), then
    the advice's list cut."""
    def size() -> int:
        return len(json.dumps(out, ensure_ascii=False, default=str))
    while size() > limit and len(out["rules"]) > 2:
        out.setdefault("more", []).insert(0, out["rules"].pop()["id"])
    while size() > limit and len(out.get("advice", {}).get("optimizers", [])) > 1:
        out["advice"]["optimizers"].pop()
    return out


def search(query: str = "", inverter: str = "", optimizer: str = "", module_w: float | None = None) -> dict:
    found_inv, found_opt, found_w = models_in(query)
    inverter = (inverter or found_inv).strip()
    optimizer = (optimizer or found_opt).strip()
    module_w = module_w if module_w else found_w
    stems = _stems(f"{query} {inverter} {optimizer}")
    scored = sorted(((_score(p, stems, inverter, optimizer), i, p) for i, p in enumerate(passages())),
                    key=lambda s: (-s[0], s[1]))
    hits = [{k: p[k] for k in ("id", "title", "text", "source")} for score, _i, p in scored if score > 0][:HITS]
    out: dict = {"query": query, "rules": hits}
    if inverter or optimizer:
        out["advice"] = advise(inverter, optimizer, module_w)
    if not hits and "advice" not in out:
        out["topics"] = sorted({p["title"] for p in passages() if p["topic"] in ("dcac", "preferred", "policy")} |
                               {"optimizers by maker and family", "SolarEdge tables", "fire brigade sub-fields"})
        out["message"] = "no rule matches these words: ask with the words of a topic"
    return out
