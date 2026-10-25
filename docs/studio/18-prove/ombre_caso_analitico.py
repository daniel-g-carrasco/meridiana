"""Study 18, part B.4: the near shading of src/meridiana/energy/nearshade.py against geometry done by hand.

A. A wall of height h south of a row of flat modules, the sun due South at a known elevation: the shadow
   reaches h / tan(elevation) from the wall's north face, and the shaded share of modules 2 m deep lying
   1.5 m behind it follows. nearshade.shading() computes the share on a grid of sun positions (every 5
   degrees of azimuth, every 4 of elevation from 2) and nearshade.at() reads it bilinearly: the check is
   exact on the grid's nodes and shows the interpolation's error between them, among which the noon of
   the winter solstice at Rho. Then the same wall before modules tilted 30 degrees, where the shadow
   climbs the slope.
B. The electrical effect of a shadow on a string (nearshade.electrical): one module of a string fully
   shaded, and a shadow across the bottom of every module, against Martinez-Moreno's rule as the code
   draws the blocks (three strips along the long side, one per bypass diode, split in two for half cells;
   a block counts as shaded when the shadow touches it, 1 mm inside its edges), against
   pvlib.shading.direct_martinez, and against the lines of simulate.py that turn the share into power;
   the rows' variant (nearshade.rows_electrical) beside it.
C. Limit cases: an obstacle behind the modules with the sun behind too (a summer sun in the North), an
   obstacle below the plane of tilted modules, the sun behind a steep plane, a sun lower than the grid's
   first row, and an obstacle behind tilted rows under a grazing sun.
D. What the grid costs over a real year: the beam lost to the wall of A, hour by hour on the PVGIS typical
   year of Rho (cached copy), computed exactly and read from the table.

The results go to ombre_caso_analitico-risultati.txt beside this script. Run from the repository root:
    PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/ombre_caso_analitico.py
"""

from __future__ import annotations

import math
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))

import pvlib  # noqa: E402

from meridiana import layout, sun  # noqa: E402
from meridiana.energy import meteo, nearshade  # noqa: E402

OUT = HERE / "ombre_caso_analitico-risultati.txt"
LAT, LON, ELEV = 45.5226, 9.03, 150.0
CACHE_SRC = Path(os.environ.get("LOCALAPPDATA", "")) / "Meridiana" / "cache"
SCRATCH = Path(os.environ.get("STUDIO18_SCRATCH") or Path(tempfile.gettempdir()) / "meridiana-studio18")
LINES: list[str] = []


def say(text: str = "") -> None:
    print(text)
    LINES.append(text)


def flat_modules(y0: float = 2.0, y1: float = 4.0, count: int = 10, x0: float = -5.0, width: float = 1.0,
                 z: float = 0.0) -> list:
    """Flat modules side by side along x, each `width` wide and y1 - y0 deep."""
    return [layout.PlacedModule(row=0, slot=k, group=0, corners=[(x, y0), (x + width, y0), (x + width, y1), (x, y1)],
                                centre=(x + width / 2, (y0 + y1) / 2), z=z, tilt=0.0, azimuth=0.0)
            for k, x in enumerate(x0 + width * np.arange(count))]


def wall(y0: float, y1: float, height: float, x0: float = -6.0, x1: float = 6.0, name: str = "wall") -> list:
    return nearshade.prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 0.0, height, name)


def tilted_module(tilt: float, y_low: float = 4.0, length: float = 2.0, x0: float = -5.0, x1: float = 5.0):
    """One wide module tilted towards South, its low edge at y_low on the ground (z 0)."""
    depth = length * math.cos(math.radians(tilt))
    rise = length * math.sin(math.radians(tilt))
    return layout.PlacedModule(row=0, slot=0, group=0, corners=[(x0, y_low), (x1, y_low), (x1, y_low + depth), (x0, y_low + depth)],
                               centre=(0.0, y_low + depth / 2), z=rise / 2, tilt=tilt, azimuth=0.0), depth, rise


def share_flat(h: float, gap: float, depth: float, el: float, az: float = 180.0, wall_x: tuple = (-6.0, 6.0),
               mods_x: tuple = (-5.0, 5.0)) -> float:
    """Shaded share of flat modules `depth` deep, `gap` north of a wall of height h that spans wall_x along
    the rows; the modules span mods_x. The shadow of the wall's top edge is displaced by h / tan(el) away
    from the sun: its north reach takes the direct light off the modules over the depth it covers, and its
    slide along the rows leaves the modules at the far end in the sun."""
    if el <= 0 or math.cos(math.radians(az)) >= 0:
        return 0.0
    shift = h / math.tan(math.radians(el))
    reach = -math.cos(math.radians(az)) * shift
    dx = -math.sin(math.radians(az)) * shift
    overlap = max(0.0, min(mods_x[1], wall_x[1] + dx) - max(mods_x[0], wall_x[0] + dx))
    return overlap / (mods_x[1] - mods_x[0]) * min(max(reach - gap, 0.0), depth) / depth


def share_exact(solids: list, modules: list, az: float, el: float) -> float:
    """Shaded share of flat modules at z = 0 under the shadow of convex solids, projected here corner by
    corner along the sun's rays (a point at height z lands at (x, y) - (s_x, s_y) z / s_z) and hulled:
    an independent reading of the same geometry nearshade._hulls does, at the exact sun position."""
    import shapely
    if el <= 0:
        return 0.0
    s = nearshade.sun_vectors([az], [el])[0]
    hulls = []
    for sol in solids:
        pts = [(x - s[0] * z / s[2], y - s[1] * z / s[2]) for x, y, z in sol.corners]
        hulls.append(shapely.convex_hull(shapely.multipoints(np.array(pts))))
    shadow = shapely.union_all(hulls)
    mods = shapely.union_all([shapely.Polygon(pm.corners) for pm in modules])
    return float(shapely.intersection(mods, shadow).area / mods.area)


def main() -> None:
    i_of = {float(e): i for i, e in enumerate(nearshade.ELEVATIONS)}
    j_of = {float(a): j for j, a in enumerate(nearshade.AZIMUTHS)}
    say("Ombre vicine (nearshade.py) contro la geometria a mano")
    say(f"griglia del sole: azimut ogni {nearshade.AZ_STEP} gradi, elevazione da {nearshade.ELEVATIONS[0]} ogni {nearshade.EL_STEP}")
    say()

    # ---- A. the wall and the flat modules
    say("A. Muro alto 1 m a sud di moduli piani profondi 2 m, 1,5 m dietro la faccia nord del muro; sole a sud")
    h, gap, depth = 1.0, 1.5, 2.0
    mods = flat_modules()
    sh = nearshade.shading(mods, wall(0.0, 0.5, h), 0.0, 0.0)
    say(f"   cielo visto oltre il muro (fattore diffuso): {sh.sky:.4f}")
    say("   elevazione  ombra h/tan  frazione a mano  tabella/at()   errore   nodo della griglia?")
    worst = 0.0
    for el in (2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 30.0, 32.0, 34.0, 36.0, 38.0, 42.0, 46.0, 50.0):
        exact = share_flat(h, gap, depth, el)
        got = float(nearshade.at(sh.table, 180.0, el))
        node = el in i_of
        if not node:
            worst = max(worst, abs(got - exact))
        say(f"   {el:9.2f}  {h / math.tan(math.radians(el)):10.3f}  {exact:14.4f}  {got:12.4f}  {got - exact:+8.4f}   {'si' if node else 'no'}")
    say(f"   errore massimo fuori dai nodi (interpolazione bilineare di una curva in 1/tan): {worst:.4f} di frazione")
    # the noon of the winter solstice at Rho
    day = pd.date_range("2026-12-21 00:00", "2026-12-21 23:59", freq="1min", tz="Europe/Rome")
    sp = pvlib.solarposition.get_solarposition(day, LAT, LON, altitude=ELEV)
    k = int(sp.apparent_elevation.to_numpy().argmax())
    el_noon = float(sp.apparent_elevation.iloc[k])
    az_noon = float(sp.azimuth.iloc[k])
    el_geom = sun.noon_elevation(LAT, LON, date(2026, 12, 21))
    exact = share_flat(h, gap, depth, el_noon, az_noon)
    got = float(nearshade.at(sh.table, az_noon, el_noon))
    say(f"   mezzogiorno del solstizio d'inverno a Rho: SPA {el_noon:.2f} gradi apparenti alle {day[k].strftime('%H:%M')} locali, "
        f"azimut {az_noon:.2f}; sun.noon_elevation (geometrica) {el_geom:.2f}")
    say(f"   frazione in ombra a mano {exact:.4f}, dalla tabella {got:.4f}, errore {got - exact:+.4f} ({100 * (got / exact - 1):+.2f} %)")
    # off-grid azimuth, on-grid elevation: the wall is a solid, its shadow the hull of the base and the top
    the_wall = wall(0.0, 0.5, h)
    for az in (182.5, 187.5, 185.0, 230.0):
        exact = share_exact(the_wall, mods, az, 22.0)
        got = float(nearshade.at(sh.table, az, 22.0))
        say(f"   azimut {az} ({'nodo' if az in j_of else 'fra due nodi'}), elevazione 22: proiezione esatta {exact:.4f}, tabella {got:.4f}, "
            f"errore {got - exact:+.4f}; formula del solo spigolo alto {share_flat(h, gap, depth, 22.0, az):.4f}")
    say()
    say("A2. Lo stesso muro (1,5 m) davanti a un modulo di 2 m inclinato 30 gradi verso sud, bordo basso a 3,5 m dal muro")
    tilt = 30.0
    pm, depth_t, rise_t = tilted_module(tilt)
    sh_t = nearshade.shading([pm], wall(0.0, 0.5, 1.5), tilt, 0.0)
    say("   elevazione  s_lim (m)  frazione a mano  tabella   errore   nodo?")
    for el in (6.0, 10.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0):
        t = math.tan(math.radians(el))
        s_lim = (1.5 - 3.5 * t) / (math.sin(math.radians(tilt)) + math.cos(math.radians(tilt)) * t)
        exact = min(max(s_lim / 2.0, 0.0), 1.0)
        got = float(nearshade.at(sh_t.table, 180.0, el))
        say(f"   {el:9.1f}  {s_lim:9.4f}  {exact:14.4f}  {got:8.4f}  {got - exact:+8.4f}   {'si' if el in i_of else 'no'}")
    say()

    # ---- B. the electrical effect
    say("B. Effetto elettrico (Martinez-Moreno 2010, eq. 6): un modulo in ombra piena su una stringa")
    i30, j180 = i_of[30.0], j_of[180.0]
    chimney = nearshade.prism([(-5.0, 0.0), (-4.0, 0.0), (-4.0, 0.5), (-5.0, 0.5)], 0.0, 3.0, "chimney")
    for lay in ((3, 1), (3, 2)):
        shc = nearshade.shading(mods, chimney, 0.0, 0.0, layout=lay)
        each = shc.modules[:, i30, j180]
        blocks = shc.blocks[:, i30, j180]
        nb = lay[0] * lay[1]
        say(f"   blocchi per modulo {lay} = {nb}: quote in ombra per modulo {np.round(each, 4).tolist()}, blocchi toccati {blocks.astype(int).tolist()}, "
            f"tabella {float(shc.table[i30, j180]):.4f}")
        keys = [m.key for m in mods]
        one = float(nearshade.electrical(shc, [keys], [180.0], [30.0])[0])
        two = float(nearshade.electrical(shc, [keys[:5], keys[5:]], [180.0], [30.0])[0])
        f1, nsb1, ntb1 = 0.1, nb, 10 * nb
        hand_one = 10 * (1 - f1) * nsb1 / (ntb1 + 1) / 10
        f2, nsb2, ntb2 = 0.2, nb, 5 * nb
        hand_two = 5 * (1 - f2) * nsb2 / (ntb2 + 1) / 10
        say(f"      una stringa di 10: extra {one:.5f} (a mano (1 - 0.1) x {nsb1}/({ntb1} + 1) = {hand_one:.5f}); "
            f"due stringhe di 5: {two:.5f} (a mano 5/10 x (1 - 0.2) x {nsb2}/({ntb2} + 1) = {hand_two:.5f})")
        loss_pvlib = float(pvlib.shading.direct_martinez(1.0, 1.0, f1, nsb1, ntb1))
        say(f"      pvlib.shading.direct_martinez(1, 1, {f1}, {nsb1}, {ntb1}) = {loss_pvlib:.5f} di perdita sul diretto, "
            f"di cui lineare {f1}: extra {loss_pvlib - f1:.5f}")
        # the composition of simulate.py:315-322 with the direct light alone (beam_part 1)
        f_obst = float(shc.table[i30, j180])
        cut = one / (1.0 - f_obst)
        kept = (1.0 - f_obst) * (1.0 - cut)
        say(f"      simulate.py: p_el = p_mm (1 - extra/(1 - f_obst)) con p_mm gia' ridotto di (1 - f_obst): resta {kept:.5f} del diretto; "
            f"Martinez (1 - F_GS)(1 - N_SB/(N_TB + 1)) = {(1 - f1) * (1 - nsb1 / (ntb1 + 1)):.5f}")
    say()
    say("B2. Ombra sul quarto inferiore di tutti e dieci i moduli (muro a tutta larghezza, altezza 2 tan 30 = 1,1547 m)")
    low = wall(0.0, 0.5, 2.0 * math.tan(math.radians(30.0)))
    for lay in ((3, 1), (3, 2)):
        shl = nearshade.shading(mods, low, 0.0, 0.0, layout=lay)
        each = shl.modules[:, i30, j180]
        blocks = shl.blocks[:, i30, j180]
        nb = lay[0] * lay[1]
        ex = float(nearshade.electrical(shl, [[m.key for m in mods]], [180.0], [30.0])[0])
        f = float(each.mean())
        nsb, ntb = int(blocks.sum()), 10 * nb
        kept = (1 - f) * (1 - nsb / (ntb + 1))
        rows_ex = float(nearshade.rows_electrical(np.array([f]), 1, True, lay)[0])
        say(f"   blocchi {lay}: quota in ombra {f:.4f} per modulo, blocchi toccati {int(blocks[0])} di {nb} per modulo; extra {ex:.4f} "
            f"(a mano (1 - {f:.2f}) x {nsb}/({ntb} + 1) = {(1 - f) * nsb / (ntb + 1):.4f}); del diretto resta {kept:.4f}; "
            f"rows_electrical (file, senza +1): extra {rows_ex:.4f}, resta {(1 - f) - rows_ex:.4f}")
    say("   lettura: con i tre diodi lungo il lato lungo un'ombra dal basso tocca tutti i blocchi e il modello toglie quasi tutto il diretto; "
        "con le mezze celle resta la meta' superiore")
    say()

    # ---- C. limit cases
    say("C. Casi al limite")
    north = wall(6.0, 6.5, 3.0, name="north wall")
    shn = nearshade.shading(mods, north, 0.0, 0.0)
    el = 46.0
    reach = 3.0 / math.tan(math.radians(el))
    exact = min(max(reach - 2.0, 0.0), 2.0) / 2.0          # the wall's south face is 2 m north of the modules' far edge
    got = float(nearshade.at(shn.table, 0.0, el))
    say(f"   C1 muro di 3 m a nord dei moduli piani, sole a nord a {el} gradi: ombra {reach:.3f} m verso sud, frazione a mano {exact:.4f}, "
        f"tabella {got:.4f}; con il sole a sud (180, 30): {float(nearshade.at(shn.table, 180.0, 30.0)):.4f}")
    pm30, _d, _r = tilted_module(30.0, y_low=0.0, length=1.0, x0=-1.0, x1=1.0)
    box = nearshade.prism([(-1.0, 2.0), (1.0, 2.0), (1.0, 3.0), (-1.0, 3.0)], 0.0, 1.0, "box")
    shb = nearshade.shading([pm30], box, 30.0, 0.0)
    say(f"   C2 scatola alta 1 m dietro un modulo inclinato 30 gradi, sotto il piano prolungato: tabella max {float(shb.table.max()):.4f}, cielo {shb.sky:.4f}")
    pm60, _d, _r = tilted_module(60.0, y_low=4.0, length=2.0)
    sh60 = nearshade.shading([pm60], wall(6.0, 6.5, 5.0), 60.0, 0.0)
    n60 = nearshade.plane_axes(60.0, 0.0)[0]
    s = nearshade.sun_vectors([0.0], [20.0])[0]
    say(f"   C3 modulo a 60 gradi verso sud, muro di 5 m a nord, sole a nord a 20 gradi: sole dietro il piano (s.n = {float(s @ n60):+.3f}), "
        f"tabella {float(nearshade.at(sh60.table, 0.0, 20.0)):.4f} (la faccia non riceve diretto: coerente)")
    say(f"   C4 sole sotto la prima riga della griglia: at(1 grado) = {float(nearshade.at(sh.table, 180.0, 1.0)):.4f} = at(2 gradi) "
        f"{float(nearshade.at(sh.table, 180.0, 2.0)):.4f}; at(0) = {float(nearshade.at(sh.table, 180.0, 0.0)):.4f}; "
        f"at(-3) = {float(nearshade.at(sh.table, 180.0, -3.0)):.4f}")
    # an obstacle behind tilted rows under a grazing sun from the North-West
    pm15, d15, r15 = tilted_module(15.0, y_low=0.0, length=2.0)
    behind = nearshade.prism([(-5.0, d15 + 1.0), (5.0, d15 + 1.0), (5.0, d15 + 1.5), (-5.0, d15 + 1.5)], 0.0, 2.0, "behind")
    sh15 = nearshade.shading([pm15], behind, 15.0, 0.0)
    n15 = nearshade.plane_axes(15.0, 0.0)[0]
    for az, el in ((300.0, 8.0), (300.0, 2.0), (330.0, 6.0)):
        s = nearshade.sun_vectors([az], [el])[0]
        got = float(nearshade.at(sh15.table, az, el))
        say(f"   C5 falda a 15 gradi, ostacolo di 2 m un metro dietro, sole a ({az:.0f}, {el:.0f}): cos(aoi) = {float(s @ n15):+.4f}, "
            f"frazione in ombra {got:.4f}, diretto in gioco {100 * max(float(s @ n15), 0):.2f} % della DNI")
    say()

    # ---- D. the grid over a real year
    say("D. Il costo della griglia su un anno vero: il muro di A sui moduli piani, anno tipo PVGIS di Rho")
    cache = SCRATCH / "cache"
    shutil.copytree(CACHE_SRC / "pvgis", cache / "pvgis", dirs_exist_ok=True)
    m = meteo.typical_year(LAT, LON, cache)
    d = m.data
    t_sun = d.index + pd.Timedelta(hours=m.time_offset_h)
    sp = pvlib.solarposition.get_solarposition(t_sun, LAT, LON, altitude=m.elevation, pressure=d.pressure.to_numpy(),
                                               temperature=d.temp_air.to_numpy())
    el_h = 90.0 - sp.apparent_zenith.to_numpy()
    az_h = sp.azimuth.to_numpy()
    beam_flat = d.dni.to_numpy() * np.clip(np.sin(np.radians(el_h)), 0.0, None)        # beam on the flat modules
    up = el_h > 0
    exact = np.array([share_exact(the_wall, mods, a, e) if e > 0 else 0.0 for e, a in zip(el_h, az_h, strict=False)])
    table = nearshade.at(sh.table, az_h, el_h)
    needed = nearshade.needed_cells(az_h, el_h)
    sh_fast = nearshade.cached_shading(mods, wall(0.0, 0.5, h), 0.0, 0.0, needed)
    fast = nearshade.at(sh_fast.table, az_h, el_h)
    tot = beam_flat.sum()
    lost_exact, lost_table, lost_fast = (beam_flat * exact).sum(), (beam_flat * table).sum(), (beam_flat * fast).sum()
    say(f"   diretto sul piano {tot / 1000:.1f} kWh/m2; perso per il muro: esatto {100 * lost_exact / tot:.3f} %, tabella completa "
        f"{100 * lost_table / tot:.3f} %, tabella delle sole celle necessarie (come simulate) {100 * lost_fast / tot:.3f} %")
    say(f"   errore della tabella sulla perdita: {100 * (lost_table / lost_exact - 1):+.2f} % della perdita; errore orario massimo "
        f"{np.abs(table - exact)[up].max():.4f} di frazione, medio {np.abs(table - exact)[up].mean():.4f}")
    say(f"   celle calcolate con needed_cells: {int(needed.sum())} di {needed.size}; cielo: tabella completa {sh.sky:.4f}, ridotta {sh_fast.sky:.4f}")
    err = np.where(up, table - exact, 0.0)
    worst = np.argsort(-np.abs(err))[:6]
    say("   le ore peggiori (ora UTC dell'anno tipo, elevazione, azimut, DNI, esatto, tabella):")
    for k in worst:
        say(f"      {d.index[k].strftime('%d/%m %H:%M')}  el {el_h[k]:6.2f}  az {az_h[k]:7.2f}  DNI {d.dni.iloc[k]:6.0f}  "
            f"esatto {exact[k]:.4f}  tabella {table[k]:.4f}  diretto sul piano {beam_flat[k]:.1f} W/m2")
    low = up & (el_h < 6.0)
    say(f"   ore con il sole fra 0 e 6 gradi: {int(low.sum())}, diretto sul piano in quelle ore {beam_flat[low].sum() / 1000:.2f} kWh/m2 "
        f"({100 * beam_flat[low].sum() / tot:.2f} % dell'anno)")
    say()

    # ---- E. the rows model of simulate.py (pvlib.shading.shaded_fraction1d) against the 1D geometry
    say("E. File inclinate: pvlib.shading.shaded_fraction1d come simulate.py la chiama, contro la geometria piana")
    tilt, width, pitch = 25.0, 2.278, 2.6
    surface_az = 180.0
    say(f"   file a {tilt} gradi verso sud, larghezza {width} m, passo {pitch} m (GCR {width / pitch:.2f}); sole a sud")
    say("   elevazione  s_lim (m)  frazione a mano  shaded_fraction1d   errore")
    for el in (10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0):
        t = math.tan(math.radians(el))
        b = math.radians(tilt)
        s_lim = (width * math.sin(b) - (pitch - width * math.cos(b)) * t) / (math.sin(b) + math.cos(b) * t)
        exact = min(max(s_lim / width, 0.0), 1.0)
        got = float(np.atleast_1d(pvlib.shading.shaded_fraction1d(90.0 - el, 180.0, (surface_az - 90.0) % 360.0, tilt,
                                                                    collector_width=width, pitch=pitch))[0])
        say(f"   {el:9.1f}  {s_lim:9.4f}  {exact:14.4f}  {got:17.4f}  {got - exact:+8.4f}")
    # the sun off the rows' normal: the shadow stretches along the rows and its depth follows the projected sun
    el, az = 20.0, 135.0
    b = math.radians(tilt)
    t_proj = math.tan(math.radians(el)) / abs(math.cos(math.radians(az - 180.0)))     # the sun's profile angle
    s_lim = (width * math.sin(b) - (pitch - width * math.cos(b)) * t_proj) / (math.sin(b) + math.cos(b) * t_proj)
    exact = min(max(s_lim / width, 0.0), 1.0)
    got = float(np.atleast_1d(pvlib.shading.shaded_fraction1d(90.0 - el, az, (surface_az - 90.0) % 360.0, tilt,
                                                                collector_width=width, pitch=pitch))[0])
    say(f"   sole a ({az:.0f}, {el:.0f}): angolo di profilo {math.degrees(math.atan(t_proj)):.2f} gradi, a mano {exact:.4f}, pvlib {got:.4f}, "
        f"errore {got - exact:+.4f}")
    OUT.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"\nscritto {OUT}")


if __name__ == "__main__":
    main()
