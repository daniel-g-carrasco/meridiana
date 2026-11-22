"""The weather of the site as a job of the common mechanism (study 48, chapter 3): fetched from PVGIS into the cache
when a view needs it and it is not on this PC (the sun map: decided by Daniel on 14/11/2026, study 48 chapter 7, choice
5). A thread job: it waits for the network. Without Qt.

One way to fetch: the year's own functions on the same cache (app/pipeline.py: weather_at_hand, weather_of,
horizon_of), so the year finds what this job fetched and this job finds what the year or the PVGIS command fetched,
under the same keys (meteo._cache_file: the site to four decimals). The project's own consent to the network is the
year's too (Project.online_allowed("pvgis", the settings' switch)): without it the job refuses with a sentence that says
what to do, and asks nothing of the network.

What the job does: the typical year when it is not at hand, and the horizon when the losses use it and it is neither in
the project nor in the cache (a horizon that cannot be had is said in the log and left out, as the year leaves it). One
request to each service (meteo: PVGIS 5.3, then 6): no round of retries. The result says the site it was fetched
for."""

from __future__ import annotations

from pathlib import Path

from meridiana.app import pipeline
from meridiana.app.platform import log
from meridiana.app.work.job import Kind, Refused
from meridiana.core.energy import meteo, system
from meridiana.i18n import N_, _

TYPICAL = N_("typical year")        # what the bar says of each step (msgids), after the job's title
HORIZON = N_("horizon")

# What the weather is made of: the site; the project's consent (project:privacy) decides whether it may be fetched.
# A change restarts it after the quiet with the photo of then: what was fetched for the old site stays in the cache.
KIND = Kind(name="weather", title=N_("Weather of the site"), run="meridiana.app.weather_job:run", where="thread",
            on_change="restart", topics=("project:site", "project:privacy"), settle=1.0)


def request_of(photo: dict, cache: Path | str, network: bool) -> dict:
    """The request: `photo` the project as data (session.photo()), `cache` the folder of the weather's cache, `network`
    the settings' switch of PVGIS (Config.network_pvgis)."""
    return {"photo": photo, "cache": str(cache), "network": bool(network)}


def refusal(project, network: bool) -> str:
    """Why the weather of the site may not be fetched now, in the user's words; "" when it may (the rule of the
    year's PVGIS: the settings' switch, and for a reserved project its own consent)."""
    if project.online_allowed("pvgis", network):
        return ""
    if not network:
        return _("The weather of the site is not on this PC and PVGIS is off in Settings > Privacy: turn it on there "
                 "to fetch it.")
    return _("The weather of the site is not on this PC and this project is reserved: allow PVGIS weather in its "
             "Properties to fetch it.")


def _horizon_missing(project, cache: Path) -> bool:
    """The losses use the horizon and it is neither in the project nor in the cache (a damaged one counts as
    missing: fetched again)."""
    if not system.losses_of(project).use_horizon:
        return False
    try:
        return pipeline.horizon_of(project, cache, fetch=False) is None
    except meteo.MeteoError as error:
        log.complain("The horizon of the site in the cache could not be read: fetched again", error)
        return True


def run(request: dict, ctx) -> dict:
    """What is missing of the weather of the photo's site, fetched into the cache. The result: {"site": (lat, lon),
    "fetched": the kinds fetched ("tmy", "horizon")}."""
    from meridiana.core.model import model
    project = model.Project.from_json(request["photo"], check=False)
    cache = Path(request["cache"])
    site = (float(project.site.lat), float(project.site.lon))
    wants = ([] if pipeline.weather_at_hand(project, cache) else ["tmy"]) + (
        ["horizon"] if _horizon_missing(project, cache) else [])
    if not wants:
        return {"site": site, "fetched": []}
    why = refusal(project, request["network"])
    if why:
        if "tmy" in wants:
            raise Refused(why)
        return {"site": site, "fetched": []}        # the horizon alone is not worth a refusal: left out, as the year does
    done = 0
    if "tmy" in wants:
        ctx.progress(done, len(wants), TYPICAL)
        try:
            pipeline.weather_of(project, cache)
        except meteo.MeteoError as error:
            log.complain("The weather of the site could not be fetched", error)
            raise Refused(_("The weather of the site could not be fetched from PVGIS: check the network and try "
                            "again.")) from error
        done += 1
        ctx.checkpoint()
    if "horizon" in wants:
        ctx.progress(done, len(wants), HORIZON)
        try:
            pipeline.horizon_of(project, cache, fetch=True)
        except meteo.MeteoError as error:
            log.complain("The horizon of the site could not be fetched: left out", error)
            wants.remove("horizon")
        done += 1
    ctx.progress(done, done, HORIZON if "horizon" in wants else TYPICAL)
    return {"site": site, "fetched": wants}
