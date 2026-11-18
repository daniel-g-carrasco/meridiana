"""Study 26 (and 27): the bars of the phases drawn in HTML from barre.json, the real words, keys, icons and tokens.
Only for the drawings of the studies: nothing of the program imports this."""

import json
import re
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "barre.json").read_text(encoding="utf-8"))
for _p in DATA["phases"]:          # the word the bar should have: «Pitch» is English left over in the program
    for _g in _p["groups"]:
        for _t in _g["tools"]:
            for _f in _t["family"]:
                if _f["word"] == "Pitch":
                    _f["word"], _f["text"] = "Falda", "Falda"
PHASES = {p["id"]: p for p in DATA["phases"]}
DESTRUCTIVE = {"strings_clear"}
# what stays lit while in use and may stay on the face: the tools of the plan (modes); the others are one-shot
MODES = {"tool_building", "tool_pitch", "tool_ridge", "tool_subfield", "tool_row"}
STRIPS = {
    "plant": '<div class="st2"><span>Non scelto: dimensionato da solo al rapporto DC/AC 1,10.</span>'
             '<span class="mut">0 stringhe su 0 ingressi · 128 moduli fuori stringa</span></div>',
    "production": '<div class="st2"><span class="mut">Non ancora scaricato.</span></div>'
                  '<div class="st2"><span><i class="ck"></i>Ombre dell\'orizzonte lontano</span>'
                  '<span><i class="ck"></i>Ombre degli ostacoli della scena</span></div>',
}


def sprite() -> str:
    out = []
    for name, svg in DATA["icons"].items():
        box = re.search(r'viewBox="([^"]+)"', svg)
        inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", svg, flags=re.S)
        out.append(f'<symbol id="i-{name}" viewBox="{box.group(1) if box else "0 0 24 24"}">{inner}</symbol>')
    return f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">{"".join(out)}</svg>'


def tokens_css() -> str:
    out = []
    for theme, t in DATA["tokens"].items():
        rules = "".join(f"--{k.replace('_', '-')}:{v};" for k, v in t.items())
        out.append(f".{theme}{{{rules}}}")
    return "\n".join(out)


CSS = """
*{box-sizing:border-box}
.ic{display:block;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;flex:none}
.card{background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:5px 10px}
.bar{display:flex;align-items:stretch;min-height:0}
.grp{display:flex;flex-direction:column;padding:0 4px;flex:none}
.grp .row{display:flex;gap:2px}
.ttl{font-size:10px;line-height:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);text-align:center;margin-top:4px;white-space:nowrap}
.sep{width:1px;background:var(--line-soft);margin:4px 8px 17px;flex:none}
.today .sep{margin:4px 8px}
.b{position:relative;display:flex;align-items:center;justify-content:center;border-radius:6px;color:var(--text);cursor:default;flex:none;user-select:none}
.b:hover{background:var(--hover)}
.b.on{background:var(--press)}
.b.hot{background:var(--hover)}
.b .w{font-size:12px;line-height:15px;white-space:nowrap}
.tall .b.plain,.b.plain.tall{flex-direction:column;height:50px;min-width:48px;padding:0 8px;gap:2px}
.beside .b.plain{flex-direction:row;height:28px;padding:0 8px;gap:6px}
.low .b.plain{height:28px;width:28px}
.low .b.plain .w{display:none}
.tall .ic{width:24px;height:24px}.low .ic{width:22px;height:22px}.beside .ic{width:18px;height:18px}
.b.primary{background:var(--field)}.b.primary:hover{background:color-mix(in srgb,var(--field),var(--text) 8%)}
.b.primary .w{font-weight:600}
.b.off{color:var(--muted);opacity:.55;background:transparent}
.mut{color:var(--muted)}
.st2{display:flex;flex-direction:column;justify-content:center;gap:6px;font-size:12px;padding:0 8px;white-space:nowrap;color:var(--text);min-width:0;overflow:hidden;flex:0 1 auto}
.st2 span{overflow:hidden;text-overflow:ellipsis}
.spring{flex:1 1 auto;min-width:8px}
.ck{display:inline-block;width:12px;height:12px;border-radius:3px;background:var(--text2);margin-right:6px;vertical-align:-1px}
.chev{display:inline-block;width:6px;height:6px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(45deg) translate(-1px,-1px)}
.g{position:relative;display:flex;flex:none}
.pop{display:none;position:absolute;z-index:30;top:calc(100% + 4px);left:0}
.g.open>.pop{display:block}
.menu{background:var(--card);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:4px;width:238px}
.mi{display:flex;align-items:center;gap:8px;height:28px;padding:0 8px;border-radius:4px;font-size:13px;white-space:nowrap}
.mi:hover,.mi.hot{background:var(--hover)}
.mi .ic{width:16px!important;height:16px!important}
.mi .k{margin-left:auto;color:var(--muted);font-size:12px}
.mi .mark{width:12px;flex:none;font-size:12px}
.mi.danger{color:var(--danger)}
.mhr{border-top:1px solid var(--line-soft);margin:4px 0}
/* G0, today: the arrow beside the top of the icon */
.g0 .b{flex-direction:column}
.g0 .aw{position:absolute;top:6px;right:5px;color:var(--muted)}
.tall .g0 .b{padding-right:16px;padding-left:16px}
.low .g0 .b{width:44px;height:28px;padding-right:14px}.low .g0 .aw{top:8px;right:6px}
.beside .g0 .b{flex-direction:row;padding-right:16px;height:28px}.beside .g0 .aw{top:9px}
/* G1, the corner */
.g1 .iw{position:relative;display:block}
.g1 .tri{position:absolute;width:7px;height:7px;background:var(--text2);clip-path:polygon(100% 0,100% 100%,0 100%);right:-6px;bottom:0}
.low .g1 .tri{right:-3px;bottom:-1px}
.beside .g1 .tri{right:-5px;bottom:-1px}
.g1 .arr{position:absolute;right:0;top:0;width:45%;height:60%;border-radius:0 6px 0 6px}
.g1 .arr:hover{background:var(--hover)}
.low .g1 .arr{height:100%;width:40%;border-radius:0 6px 6px 0}
.beside .g1 .b.plain{padding-right:14px}
/* G2, the strip */
.g2{border-radius:6px}
.g2:hover{background:var(--hover)}
.g2.hot{background:var(--hover)}
.g2 .main{border-radius:6px 0 0 6px}
.g2 .main.plain{padding-right:4px}
.g2 .arr{display:flex;align-items:center;justify-content:center;width:14px;border-radius:0 6px 6px 0;color:var(--muted);flex:none;border-left:1px solid transparent}
.g2:hover .arr,.g2.hot .arr,.g2.open .arr{border-left-color:var(--line)}
.g2 .arr:hover,.g2.open .arr{background:var(--hover);color:var(--text)}
.g2 .main:hover{background:transparent}
.g2 .main.on{background:var(--press)}
.tall .g2 .arr{height:50px}.low .g2 .arr,.beside .g2 .arr{height:28px;width:12px}
.g2 .chev{width:5px;height:5px}
/* G3, the fixed face and the big menu */
.g3 .b{flex-direction:column}
.g3 .w .chev{margin-left:4px;width:5px;height:5px;vertical-align:2px}
.low .g3 .b{width:40px;height:28px;flex-direction:row;gap:3px}
.low .g3 .aw{display:flex;color:var(--muted)}.low .g3 .chev{width:5px;height:5px}
.tall .g3 .aw,.beside .g3 .aw{display:none}
.menu.big{width:330px}
.menu.big .mi{height:44px;gap:10px}
.menu.big .mi .ic{width:24px!important;height:24px!important}
.menu.big .mi .tx{display:flex;flex-direction:column;line-height:16px;min-width:0}
.menu.big .mi .tx b{font-weight:600;font-size:13px}.menu.big .mi .tx span{font-size:12px;color:var(--text2);white-space:normal}
.menu.big .mi.last{background:var(--line-soft)}
/* G4, the row that opens over its neighbours */
.g4 .sign{position:absolute;right:4px;top:50%;margin-top:-4px;color:var(--muted)}
.g4 .sign .chev{width:5px;height:5px;transform:rotate(-45deg)}
.tall .g4 .sign{top:14px;margin:0}
.fly{display:flex;gap:2px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:3px;white-space:nowrap}
.g4>.pop{top:-4px;left:-4px}
.low .g4 .b.plain{width:34px;padding-right:6px}
.beside .g4 .b.plain{padding-right:14px}
/* G5, the track */
.g5{flex-direction:column;align-items:center;gap:2px}
.low .g5 .wd,.beside .g5 .wd{display:none}
.g5 .wd{font-size:12px;line-height:15px;white-space:nowrap}
.track{position:relative;display:flex;background:var(--field);border-radius:6px;padding:2px;height:28px}
.track .thumb{position:absolute;top:2px;height:24px;width:26px;background:var(--panel);border:1px solid var(--line);border-radius:4px;transition:left 110ms cubic-bezier(.33,1,.68,1)}
.seg{position:relative;width:26px;height:24px;display:flex;align-items:center;justify-content:center;border-radius:4px;color:var(--text2)}
.seg:hover{color:var(--text)}.seg.sel{color:var(--text)}
.seg .ic{width:16px!important;height:16px!important}
.tall .g5{height:50px;justify-content:center}
/* G6, the stack */
.g6{display:grid;grid-auto-flow:column;grid-template-rows:24px 24px;gap:2px}
.mini{display:flex;align-items:center;gap:4px;height:24px;padding:0 6px 0 4px;border-radius:4px;font-size:12px;white-space:nowrap;color:var(--text)}
.mini:hover{background:var(--hover)}.mini.hot{background:var(--hover)}.mini.on{background:var(--press)}
.mini .ic{width:16px!important;height:16px!important}
.low .g6,.beside .g6{grid-auto-flow:column;grid-template-rows:28px;gap:2px}
.low .mini,.beside .mini{height:28px;width:28px;padding:0;justify-content:center;border-radius:6px}
.low .mini .ic{width:22px!important;height:22px!important}
.low .mini span{display:none}
.beside .mini{width:auto;padding:0 6px}
"""

JS = """
function closeAll(x){document.querySelectorAll('.live .g.open').forEach(g=>{if(g!==x)g.classList.remove('open')})}
document.addEventListener('click',e=>{
  const it=e.target.closest('.live [data-word]');
  const g=e.target.closest('.live .g');
  if(it&&g&&it.closest('.pop')){
    const main=g.querySelector('.face');
    if(main&&!g.dataset.fixed){if(it.dataset.mode==='1'||g.dataset.any){main.querySelector('use').setAttribute('href','#i-'+it.dataset.icon);main.querySelector('.w').firstChild.textContent=it.dataset.word;}}
    g.querySelectorAll('.mi').forEach(m=>{m.querySelector('.mark')&&(m.querySelector('.mark').textContent=(m===it&&it.dataset.mode==='1')?'✓':'')});
    g.classList.remove('open');return;}
  if(g&&(e.target.closest('.arr')||g.dataset.fixed||g.classList.contains('g4once'))){const o=g.classList.contains('open');closeAll();g.classList.toggle('open',!o);return;}
  const seg=e.target.closest('.live .seg');
  if(seg){const t=seg.parentNode;t.querySelector('.thumb').style.left=(2+26*[...t.querySelectorAll('.seg')].indexOf(seg))+'px';t.querySelectorAll('.seg').forEach(s=>s.classList.toggle('sel',s===seg));const wd=seg.closest('.g5').querySelector('.wd');if(wd)wd.textContent=seg.dataset.word;return;}
  const f=e.target.closest('.live .face, .live .mini');
  if(f&&f.dataset.mode!=='0'){closeAll();return;}
  closeAll();
});
document.addEventListener('contextmenu',e=>{const g=e.target.closest('.live .g');if(g&&g.querySelector('.pop')){e.preventDefault();closeAll();g.classList.add('open');}});
window.addEventListener('load',()=>{document.querySelectorAll('.bar[data-measure]').forEach(b=>{const gs=b.querySelectorAll(':scope>.grp');if(!gs.length)return;const w=Math.round(gs[gs.length-1].getBoundingClientRect().right-b.getBoundingClientRect().left);b.dataset.measured=w;const lab=b.closest('.rowbar')&&b.closest('.rowbar').querySelector('.wlab');if(lab)lab.textContent=w+' px'})});
"""


def ic(name: str) -> str:
    return f'<svg class="ic"><use href="#i-{escape(name)}"/></svg>'


def _menu(fam: list, cur: int, big: bool = False, last: int | None = None, hot: int | None = None, lit: bool = False) -> str:
    rows = []
    for i, f in enumerate(fam):
        if f["cmd"] in DESTRUCTIVE:
            rows.append('<div class="mhr"></div>')
        cls = "mi" + (" danger" if f["cmd"] in DESTRUCTIVE else "") + (" last" if big and last == i else "") + \
            (" hot" if hot == i else "")
        mode = "1" if f["cmd"] in MODES else "0"
        data = f'data-word="{escape(f["word"])}" data-icon="{f["icon"]}" data-mode="{mode}"'
        if big:
            desc = f["text"] if f["text"] != f["word"] else ""
            tail = f'<span class="k">{escape(f["key"])}</span>' if f["key"] else ""
            rows.append(f'<div class="{cls}" {data}>{ic(f["icon"])}<div class="tx"><b>{escape(f["word"])}</b>'
                        f'<span>{escape(desc)}</span></div>{tail}</div>')
        else:
            mark = "✓" if lit and i == cur else ""
            tail = f'<span class="k">{escape(f["key"])}</span>' if f["key"] else ""
            rows.append(f'<div class="{cls}" {data}><span class="mark">{mark}</span>{ic(f["icon"])}'
                        f'<span>{escape(f["text"])}</span>{tail}</div>')
    return f'<div class="menu{" big" if big else ""}">{"".join(rows)}</div>'


def _face(f: dict, extra: str = "", inner: str = "", cls: str = "plain", minw: int = 0, tail: str = "") -> str:
    style = f' style="min-width:{minw}px"' if minw else ""
    return (f'<div class="b {cls} face {extra}"{style} title="{escape(f["text"])}">{inner or ic(f["icon"])}'
            f'<span class="w">{escape(f["word"])}{tail}</span></div>')


def widest(fam: list) -> int:
    return max(len(f["word"]) for f in fam)


def grouped(design: str, tool: dict, state: str = "rest", face: int = 0, mode: str = "tall") -> str:
    """The grouped button in one of the designs and one state: rest, hover, open, active, changed."""
    fam = tool["family"]
    cur = face
    f = fam[cur]
    tall = mode == "tall"
    w = widest(fam)
    lit = "on" if state == "active" else ""
    hot = "hot" if state == "hover" else ""
    open_ = " open" if state == "open" else ""
    minw = round(w * 6.3) + 16 if tall else (round(w * 6.3) + 34 if mode == "beside" else 0)
    if design == "g0":
        return (f'<div class="g g0{open_}">{_face(f, f"{lit} {hot}", minw=minw + 16 if minw else 0)}'
                f'<span class="aw arr"><i class="chev"></i></span><div class="pop">{_menu(fam, cur, lit=bool(lit))}</div></div>')
    if design == "g1":
        inner = f'<span class="iw">{ic(f["icon"])}<i class="tri"></i></span>'
        return (f'<div class="g g1{open_}">{_face(f, f"{lit} {hot}", inner=inner, minw=minw)}<span class="arr"></span>'
                f'<div class="pop">{_menu(fam, cur, lit=bool(lit))}</div></div>')
    if design == "g2":
        return (f'<div class="g g2{open_} {hot}">{_face(f, lit, cls="plain main", minw=minw)}'
                f'<div class="arr"><i class="chev"></i></div><div class="pop">{_menu(fam, cur, lit=bool(lit))}</div></div>')
    if design == "g3":
        first = fam[0]
        last = cur if state in ("changed", "open") and cur else None
        tail = '<i class="chev"></i>'
        return (f'<div class="g g3{open_}" data-fixed="1">{_face(first, f"{lit} {hot}", minw=minw + 8 if minw else 0, tail=tail)}'
                f'<span class="aw" style="position:absolute;right:6px;top:11px"><i class="chev"></i></span>'
                f'<div class="pop">{_menu(fam, cur, big=True, last=last)}</div></div>')
    if design == "g4":
        sign = '<span class="sign"><i class="chev"></i></span>'
        items = "".join(
            f'<div class="b plain mi0" data-word="{escape(m["word"])}" data-icon="{m["icon"]}" '
            f'data-mode="{1 if m["cmd"] in MODES else 0}" title="{escape(m["text"])}">{ic(m["icon"])}<span class="w">{escape(m["word"])}</span></div>'
            for m in fam)
        return (f'<div class="g g4 g4once{open_}" data-any="1">{_face(f, f"{lit} {hot} arr", minw=minw + 6 if minw else 0)}{sign}'
                f'<div class="pop"><div class="fly">{items}</div></div></div>')
    if design == "g5":
        segs = "".join(f'<div class="seg{" sel" if i == cur else ""}" data-word="{escape(m["word"])}" title="{escape(m["text"])}">{ic(m["icon"])}</div>'
                       for i, m in enumerate(fam))
        thumb = f'<i class="thumb" style="left:{2 + 26 * cur}px"></i>'
        word = f'<span class="wd" style="min-width:{round(w * 6.3)}px;text-align:center">{escape(f["word"])}</span>' if mode != "low" else ""
        return f'<div class="g g5" title="{escape(f["text"])}"><div class="track">{thumb}{segs}</div>{word}</div>'
    if design == "g6":
        minis = "".join(f'<div class="mini{" on" if lit and i == cur else ""}{" hot" if state == "hover" and i == 1 else ""}" '
                        f'title="{escape(m["text"])}" data-mode="1">{ic(m["icon"])}<span>{escape(m["word"])}</span></div>'
                        for i, m in enumerate(fam))
        return f'<div class="g g6">{minis}</div>'
    raise ValueError(design)


def plain(f: dict, primary: bool = False, on: bool = False, off: bool = False) -> str:
    cls = ("primary " if primary else "") + ("on " if on else "") + ("off" if off else "")
    return (f'<div class="b plain {cls}" title="{escape(f["text"])}{(" (" + f["key"] + ")") if f["key"] else ""}">'
            f'{ic(f["icon"])}<span class="w">{escape(f["word"])}</span></div>')


def bar(phase_id: str, design: str, mode: str = "tall", measure: bool = True, titles: bool = True, strip: bool = True,
        select_on: bool = True, faces: dict | None = None, only: tuple = ()) -> str:
    """One whole bar of a phase, as it is drawn in the card."""
    phase = PHASES[phase_id]
    parts = []
    for g in phase["groups"]:
        if only and g["title"] not in only:
            continue
        if parts:
            parts.append('<div class="sep"></div>' if titles else '<div class="sep" style="margin:4px 8px"></div>')
        row = []
        for t in g["tools"]:
            fam = t["family"]
            if len(fam) > 1:
                row.append(grouped(design, t, face=(faces or {}).get(fam[0]["cmd"], 0), mode=mode))
            else:
                f = fam[0]
                row.append(plain(f, primary=t["primary"], on=select_on and f["cmd"] == "tool_select"))
        title = f'<div class="ttl">{escape(g["title"])}</div>' if titles else ""
        parts.append(f'<div class="grp"><div class="row">{"".join(row)}</div>{title}</div>')
    tail = ""
    if strip and phase_id in STRIPS and mode == "tall":
        tail = f'<div class="spring"></div><div class="sep" style="margin:4px 8px"></div>{STRIPS[phase_id]}'
    flag = " data-measure=\"1\"" if measure else ""
    return f'<div class="bar {mode}{" today" if design == "g0" else ""}"{flag}>{"".join(parts)}{tail}</div>'


def family(phase_id: str, first_cmd: str) -> dict:
    for g in PHASES[phase_id]["groups"]:
        for t in g["tools"]:
            if t["family"][0]["cmd"] == first_cmd:
                return t
    raise KeyError(first_cmd)
