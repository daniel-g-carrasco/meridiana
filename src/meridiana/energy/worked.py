"""The formulas of the calculation written again with the numbers (R479): after the formula with the symbols and
the table of the values, the same formula with the numbers in place of the symbols, «=» and the result with its
unit. The quantities that change hour by hour are those of one declared hour, the hour of the typical year with
the most irradiance on the plane of the modules (each sub-field its own hour, the plant's for the steps of the
whole plant), taken from the calculation of that hour as it ran (simulate.py keeps them); the constants with their
value; a result of one step used by the next with the same value. Each line is LaTeX (the decimal comma as
«{,}», so that Typst, MathML and OMML keep the digits together) and carries its proof: the numbers it shows, the
expression they make, and where the calculation keeps the value it used (tests/calcoli/test_worked.py checks
every step of the shed of the tests against it)."""

from __future__ import annotations

import math
import re

import numpy as np

from ..i18n import _, number, pgettext

TOKEN = re.compile(r"@([A-Za-z]\w*)")


def months() -> list[str]:
    """The months by their whole name («May» alone is the charts' short «mag»)."""
    return [pgettext("month", m) for m in ("January", "February", "March", "April", "May", "June", "July", "August",
                                            "September", "October", "November", "December")]


def unit_tex(unit: str) -> str:
    """A unit as LaTeX after a number: upright, a thin space before it, the angle's degree attached."""
    if not unit:
        return ""
    if unit == "°":
        return r"\mathrm{°}"
    if unit == "%":
        return r"\,\%"
    if unit == "%/K":
        return r"\,\%/\mathrm{K}"
    return r"\,\mathrm{" + unit.replace("²", "^{2}") + "}"


class V:
    """A number as the line shows it: rounded to its decimals, on the language's decimal comma, with its unit; its
    value for the expression of the line is the rounded one (a share in % as a fraction), so that the check uses
    the numbers the reader sees."""

    def __init__(self, value, decimals: int = 1, unit: str = ""):
        v = round(float(value), decimals)
        self.value, self.decimals, self.unit = (0.0 if v == 0 else v), decimals, unit

    def digits(self) -> str:
        return number(self.value, self.decimals, grouping=True).replace(",", "{,}")

    def tex(self) -> str:
        text = self.digits() + unit_tex(self.unit)
        return f"({text})" if self.value < 0 else text

    def py(self) -> float:
        return self.value / 100.0 if self.unit == "%" else self.value


def cosd(x: float) -> float:
    return math.cos(math.radians(x))


FUNCTIONS = {"cosd": cosd, "min": min, "max": max}


def evaluate(expr: str, env: dict) -> float:
    """The value of a line's expression with the numbers it shows (the tests' check)."""
    return float(eval(expr, {"__builtins__": {}}, {**FUNCTIONS, **env}))   # noqa: S307 - our own expressions


class Lines:
    """The lines of one step: each a LaTeX equation ending in «= result», with its proof."""

    def __init__(self):
        self.tex: list[str] = []
        self.proof: list[dict] = []

    def add(self, tex: str, result: V, of: list, expr: str = "", hour: int | None = None, strong: bool = True,
            **values: V) -> None:
        body = TOKEN.sub(lambda m: values[m.group(1)].tex(), tex)
        shown = result.digits()
        value = (r"\mathbf{" + shown + "}" if strong else shown) + unit_tex(result.unit)
        self.tex.append(f"{body} = {value}")
        if of:
            self.proof.append({"line": len(self.tex) - 1, "shown": result.value, "decimals": result.decimals,
                               "percent": result.unit == "%", "expr": expr,
                               "env": {k: v.py() for k, v in values.items()}, "of": of, "hour": hour})

    def put(self, step, example: str = "") -> None:
        step.worked, step.proof, step.example = self.tex, self.proof, example


def hour_text(index, h: int, subject: str = "") -> str:
    """Which hour the numbers are of, as the line above them says it: the day, the hour of standard time."""
    ts = index[h]
    standard = ts.utcoffset() - ts.dst()
    local = ts.tz_convert("UTC").tz_localize(None) + standard
    offset = standard.total_seconds() / 3600.0
    text = _("Example: {day} {month}, {time} standard time (UTC{offset}); the calculation is repeated for each of "
             "the {hours} hours of the typical year.").format(
        day=local.day, month=months()[local.month - 1], time=local.strftime("%H:%M"),
        offset=f"{offset:+g}", hours=number(len(index), 0, grouping=True))
    return f"{text} {subject}".strip()


def year_text() -> str:
    return _("With the totals of the typical year.")


# ---- the steps ----

def annotate(rec, first, stages: dict, per_array: list, plant: dict) -> None:
    """Write the numbers into the steps of `rec`: `first` the first pass (its arrays and their hour), `stages` the
    powers of step 8 by array, `per_array` the arrays' year, `plant` the plant's hour and its inverter's."""
    index, h0 = first.index, plant["hour"]
    _sun(rec.find("sun"), first, h0)
    for ap, year in zip(first.per_array, per_array, strict=True):
        ex, k = ap.example, ap.a.key
        when = hour_text(index, ex["hour"])
        _poa(rec.find(f"{k}.poa"), ap, ex, when)
        _far(rec.find(f"{k}.far"), ap, ex, when)
        _rows(rec.find(f"{k}.rows"), ap, ex, year, when)
        _obstacles(rec.find(f"{k}.obstacles"), ap, ex, year, when)
        _iam(rec.find(f"{k}.iam"), ap, ex, when)
        _soiling(rec.find(f"{k}.soiling"), ap, ex, first.losses, when)
        _temperature(rec.find(f"{k}.temperature"), ap, ex, when)
        _module(rec.find(f"{k}.module"), ap, ex, stages[k], when)
        _array(rec.find(f"{k}.array"), ap, ex, stages[k], first.losses, when)
        _electrical_year(rec.find(f"{k}.rows_electrical"), ap, stages[k], "rows_electrical")
        _electrical_year(rec.find(f"{k}.electrical"), ap, stages[k], "electrical_shading")
        _optimizers(rec.find(f"{k}.optimizers"), ap, ex, stages[k], year, first.losses, when)
    _inverter(rec.find("inverter"), plant, index, h0)
    _ac(rec.find("ac"), plant, first.losses, index, h0)
    _pr(rec.find("pr"), plant)
    _network(rec.find("electrical_network"), stages, index, h0)


def _sun(step, first, h):
    if step is None:
        return
    m = first.meteo
    t = m.data.index[h]
    at = t.strftime("%H{:}%M") + r"\ \mathrm{UTC}"
    w = Lines()
    w.add(r"\theta_z,\ \gamma_s = \mathrm{SPA}(" + at + r" + @dt,\ @lat,\ @lon,\ @h)",
          V(90.0 - first.sun_el[h], 2, "°"), ["sun", "zenith"], hour=h,
          dt=V(m.time_offset_h, 3, "h"), lat=V(m.latitude, 4, "°"), lon=V(m.longitude, 4, "°"), h=V(m.elevation, 0, "m"))
    azimuth = V(first.sun_az[h], 2, "°")
    w.tex[-1] += r",\ \mathbf{" + azimuth.digits() + r"}\mathrm{°}"
    w.proof.append({"line": 0, "shown": azimuth.value, "decimals": 2, "percent": False, "expr": "", "env": {},
                    "of": ["sun", "azimuth"], "hour": h})
    w.put(step, hour_text(first.index, h))


def _poa(step, ap, ex, when):
    if step is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    w.add(r"G_{inc} = @gb \cdot \cos @theta + @gd + @gh \cdot @rho \cdot \frac{1 - \cos @beta}{2}",
          V(ap.g_inc[h], 1, "W/m²"), ["array", a.key, "g_inc"],
          "gb * cosd(theta) + gd + gh * rho * (1 - cosd(beta)) / 2", h,
          gb=V(ex["dni"], 1, "W/m²"), theta=V(ex["aoi"], 2, "°"), gd=V(ex["sky"], 1, "W/m²"),
          gh=V(ex["ghi"], 1, "W/m²"), rho=V(ex["albedo"], 2), beta=V(a.tilt, 1, "°"))
    w.put(step, when)


def _far(step, ap, ex, when):
    if step is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    seen = not ex["blocked"]
    sign = r"\geq" if seen else "<"
    w.add(r"\alpha_s = @el " + sign + r" h_{oriz}(@az) = @hor \Rightarrow G'_{b} + G'_{cs} = @b + @cs",
          V(ex["beam"] + ex["circum"], 1, "W/m²"), [], "", h, strong=False,
          el=V(ex["sun_el"], 2, "°"), az=V(ex["sun_az"], 2, "°"), hor=V(ex["horizon"], 2, "°"),
          b=V(ex["beam"], 1), cs=V(ex["circum"], 1))
    if not seen:
        w.tex[-1] = w.tex[-1].rsplit("=", 1)[0] + r"\ \to\ 0"
    w.add(r"G_{far} = @bl + (@sky - @cs) \cdot @fc + @gr \cdot @fa",
          V(ap.g_far[h], 1, "W/m²"), ["array", a.key, "g_far"], "bl + (sky - cs) * fc + gr * fa", h,
          bl=V(ex["beam_far"], 1), sky=V(ex["sky"], 1), cs=V(ex["circum"], 1), fc=V(100 * ap.dome, 1, "%"),
          gr=V(ex["ground"], 1), fa=V(100 * ap.alb, 1, "%"))
    w.put(step, when)


def _rows(step, ap, ex, year, when):
    if step is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    behind = (a.rows - 1) / a.rows
    w.add(r"f_s = f(@z,\ @az,\ @beta,\ @w,\ @p) \cdot \frac{@n - 1}{@n} = @share \cdot @behind",
          V(100 * ex["f_s"], 1, "%"), ["shaded", a.key], "share * behind", h,
          z=V(ex["zenith"], 2, "°"), az=V(ex["sun_az"], 2, "°"), beta=V(a.tilt, 1, "°"), w=V(a.slant, 2, "m"),
          p=V(a.pitch, 2, "m"), n=V(a.rows, 0), share=V(100 * ex["row_share"], 1, "%"), behind=V(behind, 3))
    w.add(r"G_{rows} = @b \cdot (1 - @fs) + @d \cdot (1 - @dd) + @r \cdot (1 - @dr)",
          V(ap.g_rows[h], 1, "W/m²"), ["array", a.key, "g_rows"], "b * (1 - fs) + d * (1 - dd) + r * (1 - dr)", h,
          b=V(ex["beam_far"], 1), fs=V(100 * ex["f_s"], 1, "%"), d=V(ex["sky_far"], 1),
          dd=V(100 * ap.sky_mask, 1, "%"), r=V(ex["ground_far"], 1), dr=V(100 * ex["ground_rows_lost"], 1, "%"))
    w.add(r"\bar{f_s} = \frac{\sum_h (G_{far} - G_{rows})}{\sum_h G_{far}} = \frac{@lost}{@far}",
          V(100 * year["row_shading"], 2, "%"), ["year", a.key, "row_shading"], "lost / far",
          lost=V(ex["year_rows_lost"], 1, "kWh/m²"), far=V(ex["year_far"], 1, "kWh/m²"))
    w.put(step, when)


def _obstacles(step, ap, ex, year, when):
    if step is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    fo = V(100 * ex["f_o"], 1, "%")
    w.add(r"f_o(@az,\ @el) = @fo,\quad G_{near} = @b \cdot (1 - @fo) + @d \cdot @fc + @r",
          V(ap.g_near[h], 1, "W/m²"), ["array", a.key, "g_near"], "b * (1 - fo) + d * fc + r", h,
          az=V(ex["sun_az"], 2, "°"), el=V(ex["sun_el"], 2, "°"), fo=fo,
          b=V(ex["beam_rows"], 1), d=V(ex["sky_rows"], 1), fc=V(100 * ap.near.sky, 1, "%"), r=V(ex["ground_near"], 1))
    w.add(r"\bar{f_o} = \frac{\sum_h (G_{rows} - G_{near})}{\sum_h G_{far}} = \frac{@lost}{@far}",
          V(100 * year["obstacle_shading"], 2, "%"), ["year", a.key, "obstacle_shading"], "lost / far",
          lost=V(ex["year_near_lost"], 1, "kWh/m²"), far=V(ex["year_far"], 1, "kWh/m²"))
    w.put(step, when)


def _iam(step, ap, ex, when):
    if step is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    terms = ex["iam_terms"]
    theta = V(ex["aoi"], 2, "°")
    if terms is None:
        w.add(r"IAM(@theta) = 1 - @b \left(\frac{1}{\cos @theta} - 1\right)", V(ap.iam_b[h], 3),
              ["array", a.key, "iam_b"], "1 - b * (1 / cosd(theta) - 1)", h, theta=theta, b=V(ex["b0"], 3))
    elif terms["kind"] == "linear":
        w.add(r"IAM(@theta) = @v0 + (@v1 - @v0) \frac{@theta - @t0}{@t1 - @t0}", V(ap.iam_b[h], 3),
              ["array", a.key, "iam_b"], "v0 + (v1 - v0) * (theta - t0) / (t1 - t0)", h, theta=theta,
              v0=V(terms["v"][0], 3), v1=V(terms["v"][1], 3), t0=V(terms["t"][0], 1, "°"), t1=V(terms["t"][1], 1, "°"))
    else:
        env = {f"v{i}": V(terms["v"][i], 3) for i in range(4)} | {f"l{i}": V(terms["l"][i], 4) for i in range(4)}
        w.add(r"IAM(@theta) = " + " + ".join(f"@v{i} \\cdot @l{i}" for i in range(4)), V(ap.iam_b[h], 3),
              ["array", a.key, "iam_b"], " + ".join(f"v{i} * l{i}" for i in range(4)), h, theta=theta, **env)
    w.add(r"G_{IAM} = @b \cdot @ib + @d \cdot @id + @r \cdot @ir", V(ap.g_iam[h], 1, "W/m²"),
          ["array", a.key, "g_iam"], "b * ib + d * id + r * ir", h,
          b=V(ex["beam_near"], 1), ib=V(ap.iam_b[h], 3), d=V(ex["sky_near"], 1), id=V(ex["iam_sky"], 3),
          r=V(ex["ground_near"], 1), ir=V(ex["iam_ground"], 3))
    w.put(step, when)


def _soiling(step, ap, ex, losses, when):
    if step is None:
        return
    h, w = ex["hour"], Lines()
    w.add(r"G_{eff} = @g \cdot (1 - @s)", V(ap.g_eff[h], 1, "W/m²"), ["array", ap.a.key, "g_eff"],
          "g * (1 - s)", h, g=V(ap.g_iam[h], 1, "W/m²"), s=V(losses.soiling, 1, "%"))
    w.put(step, when)


def _temperature(step, ap, ex, when):
    if step is None:
        return
    h, w = ex["hour"], Lines()
    w.add(r"T_c = @ta + \frac{@al \cdot @g \cdot (1 - @eta)}{@uc + @uv \cdot @v}", V(ap.t_cell[h], 1, "°C"),
          ["array", ap.a.key, "t_cell"], "ta + al * g * (1 - eta) / (uc + uv * v)", h,
          ta=V(ex["temp_air"], 1, "°C"), al=V(0.9, 1), g=V(ap.g_far[h], 1, "W/m²"), eta=V(100 * ex["eta"], 2, "%"),
          uc=V(ap.u_c, 1, "W/m²K"), uv=V(ap.u_v, 1, "W/m²K·s/m"), v=V(ex["wind"], 1, "m/s"))
    w.put(step, when)


def _module(step, ap, ex, stage, when):
    if step is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    n, p_t, tc = a.generating_modules, stage["p_t"][h] / 1000.0, V(ap.t_cell[h], 1, "°C")
    gamma = V(a.module.gamma_pmax, 3, "%/K")
    if stage["network"]:
        w.add(r"P_{ref} = \sum_{j=1}^{@n} \max_V\{V\,I_j(V,\ G_{mean,j},\ @tc)\}", V(p_t, 2, "kW"),
              ["stage", a.key, "p_t"], "", h, n=V(n, 0), tc=tc)
    elif a.module.sdm().get("linear"):
        w.add(r"P = @n \cdot @p \cdot \frac{@g}{1000} \cdot [1 + @gamma \cdot (@tc - 25)]", V(p_t, 2, "kW"),
              ["stage", a.key, "p_t"], "n * p * g / 1000 * (1 + gamma / 100 * (tc - 25)) / 1000", h, n=V(n, 0),
              p=V(a.module.pmax, 1, "W"), g=V(ap.g_eff[h], 1, "W/m²"), gamma=gamma, tc=tc)
    else:
        per = V(ex["p25_module"], 1, "W")
        w.add(r"P_{mp,25}(@g) = \max_V\{V\,I(V)\}", per, ["module25", a.key], "", h, g=V(ap.g_eff[h], 1, "W/m²"))
        w.add(r"P = @n \cdot @p \cdot [1 + @gamma \cdot (@tc - 25)]", V(p_t, 2, "kW"), ["stage", a.key, "p_t"],
              "n * p * (1 + gamma / 100 * (tc - 25)) / 1000", h, n=V(n, 0), p=per, gamma=gamma, tc=tc)
    w.put(step, when)


def _array(step, ap, ex, stage, losses, when):
    if step is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    p_t, p_mm, p_cut, p_dc = (stage[k][h] / 1000.0 for k in ("p_t", "p_mm", "p_cut", "p_dc"))
    p_stc, r = a.p_connected / 1000.0, losses.dc_wiring
    squares = (p_cut - p_dc) / (r / 100.0 * p_stc) if r > 0 and p_stc > 0 else 0.0
    factors = dict(p=V(p_t, 2, "kW"), q=V(losses.quality, 1, "%"), lid=V(ap.lid, 1, "%"),
                   m=V(stage["mismatch"], 1, "%"))
    wiring = dict(r=V(r, 1, "%"), ps=V(p_stc, 2, "kWp"), x=V(math.sqrt(max(squares, 0.0)), 3))
    if not stage["network"] and abs(p_cut - p_mm) <= 1e-9 * max(1.0, abs(p_mm)):
        w.add(r"P_{DC} = @p \cdot (1 - @q)(1 - @lid)(1 - @m) - @r \cdot @ps \cdot @x^2", V(p_dc, 2, "kW"),
              ["stage", a.key, "p_dc"], "p * (1 - q) * (1 - lid) * (1 - m) - r * ps * x ** 2", h, **factors, **wiring)
    else:
        w.add(r"P_{mm} = @p \cdot (1 - @q)(1 - @lid)(1 - @m)", V(p_mm, 2, "kW"), ["stage", a.key, "p_mm"],
              "p * (1 - q) * (1 - lid) * (1 - m)", h, **factors)
        w.add(r"P_{DC} = @pc - @r \cdot @ps \cdot @x^2", V(p_dc, 2, "kW"), ["stage", a.key, "p_dc"],
              "pc - r * ps * x ** 2", h, pc=V(p_cut, 2, "kW"), **wiring)
    w.put(step, when)


def _electrical_year(step, ap, stage, name):
    """The electrical effect of a shade, by the year: what it took over what came to it."""
    if step is None:
        return
    cut = stage["cut_rows"] if name == "rows_electrical" else stage["cut_obst"]
    mm = stage["p_mm"]
    w = Lines()
    w.add(r"\Delta E = \frac{\sum_h P_{mm}\,(F_{ES} - F_{GS})}{\sum_h P_{mm}} = \frac{@lost}{@total}",
          V(step.result.value, 2, "%"), ["year", ap.a.key, name], "lost / total",
          lost=V(float((mm * np.clip(cut, 0.0, 1.0)).sum() / 1e6), 3, "MWh"), total=V(float(mm.sum() / 1e6), 3, "MWh"))
    w.put(step, year_text())


def _optimizers(step, ap, ex, stage, year, losses, when):
    opt = year.get("optimizers")
    if step is None or opt is None:
        return
    a, h, w = ap.a, ex["hour"], Lines()
    w.add(r"m' = @m \cdot (1 - @s1)", V(opt["mismatch"], 2, "%"), ["optimizer", a.key, "mismatch"],
          "m * (1 - s1)", None, m=V(losses.mismatch, 1, "%"), s1=V(100 * opt["single"], 0, "%"))
    if not stage["network"]:
        w.add(r"P_{opt} = @pel \cdot [1 - @s \cdot (1 - @eta)]", V(stage["p_opt"][h] / 1000.0, 2, "kW"),
              ["stage", a.key, "p_opt"], "pel * (1 - s * (1 - eta))", h,
              pel=V(stage["p_el"][h] / 1000.0, 2, "kW"), s=V(100 * opt["share"], 0, "%"),
              eta=V(100 * opt["eta"], 1, "%"))
    w.add(r"\Delta E = 1 - (1 - @loss)(1 - @cut)", V(step.result.value, 2, "%"), ["optimizer", a.key, "total"],
          "1 - (1 - loss) * (1 - cut)", loss=V(100 * opt["loss"], 2, "%"), cut=V(100 * opt["cut"], 2, "%"))
    w.put(step, when if not stage["network"] else year_text())


def _inverter(step, plant, index, h):
    if step is None or plant["inverter"] is None:      # no inverter connected: no hour of one
        return
    inv, w = plant["inverter"], Lines()
    pdc, pac, eta = inv["p_dc"][h] / 1000.0, inv["pac"] / 1000.0, inv["eta"]
    z = V(pdc / (pac / eta), 3)
    w.add(r"\zeta = \frac{P_{DC}}{P_{AC,nom} / \eta_{nom}} = \frac{@pdc}{@pac / @eta}", z, ["inverter_zeta"],
          "pdc / (pac / eta)", h, pdc=V(pdc, 2, "kW"), pac=V(pac, 2, "kW"), eta=V(100 * eta, 1, "%"))
    eff = V(100 * inv["p_raw"][h] / inv["p_dc"][h] if inv["p_dc"][h] > 0 else 0.0, 2, "%")
    w.add(r"\eta = \frac{@eta}{@c0}\left(-@c1 \cdot @z - \frac{@c2}{@z} + @c3\right)", eff, ["inverter_eta"],
          "eta / c0 * (-c1 * z - c2 / z + c3)", h, eta=V(100 * eta, 1, "%"), z=z, c0=V(0.9637, 4), c1=V(0.0162, 4),
          c2=V(0.0059, 4), c3=V(0.9858, 4))
    w.add(r"P_{AC} = \min(@e \cdot @pdc,\ @pac)", V(inv["p_clip"][h] / 1000.0, 2, "kW"), ["inverter", "p_clip"],
          "min(e * pdc, pac)", h, e=eff, pdc=V(pdc, 2, "kW"), pac=V(pac, 2, "kW"))
    w.put(step, hour_text(index, h, inv["subject"]))


def _ac(step, plant, losses, index, h):
    if step is None or plant["inverter"] is None:      # no inverter connected: no hour of one
        return
    inv, w = plant["inverter"], Lines()
    p = V(inv["p_clip"][h] / 1000.0, 2, "kW")
    w.add(r"P_{AC}\left(1 - r_{AC}\frac{P_{AC}}{P_{AC,nom}}\right)(1-u) = @p \cdot \left(1 - @r \cdot \frac{@p}{@pac}"
          r"\right)(1 - @u)", V(inv["p_grid"][h] / 1000.0, 2, "kW"), ["inverter", "p_grid"],
          "p * (1 - r * p / pac) * (1 - u)", h, p=p, r=V(losses.ac_wiring, 1, "%"),
          pac=V(inv["pac"] / 1000.0, 2, "kW"), u=V(losses.unavailability, 1, "%"))
    w.add(r"E_{AC} = \sum_{h=1}^{@n} P_{AC,h}\left(1 - r_{AC}\frac{P_{AC,h}}{P_{AC,nom}}\right)(1-u)\,\Delta t",
          V(plant["energy"], 0, "kWh"), ["energy"], "", None, n=V(len(index), 0))
    w.put(step, hour_text(index, h, inv["subject"]))


def _pr(step, plant):
    if step is None:
        return
    w = Lines()
    w.add(r"PR = \frac{@e / @p}{@hi / @g}", V(100 * plant["pr"], 1, "%"), ["pr"], "e / p / (hi / g)",
          e=V(plant["energy"], 0, "kWh"), p=V(plant["p_stc"] / 1000.0, 2, "kWp"), hi=V(plant["h_poa"], 1, "kWh/m²"),
          g=V(1, 0, "kW/m²"))
    w.put(step, year_text())


def _network(step, stages, index, h):
    if step is None:
        return
    w = Lines()
    w.add(r"\sum P_{MPP} = \sum_{inv} \max_V V\,I_p(V)", V(sum(s["p_el"][h] for s in stages.values()) / 1000.0, 2, "kW"),
          ["network_mpp"], "", h)
    w.put(step, hour_text(index, h))
