"""A job that only counts (study 48): the mechanism's tests and the guard run it in place of a real computation. It
counts its parts (`mine`) with a pause between them, says each one as a result on the way, and on request holds
memory (`hog`, MiB) or does not listen to Cancel (`deaf`)."""

from __future__ import annotations

import os
import time

from meridiana.app.work.job import Kind, Refused, mine
from meridiana.i18n import N_

RUN = "meridiana.app.work.sample:count"


def kind(**changes) -> Kind:
    """The sample's kind, with what a test changes."""
    values = dict(name="count", title=N_("Counting"), run=RUN)
    values.update(changes)
    return Kind(**values)


def count(request: dict, ctx) -> dict:
    """request: steps (parts in all), pause (seconds for each), hog (MiB held while counting), deaf (Cancel not
    heard), fail (an error at that part), refuse (a job.Refused at that part), slow ({part: seconds} more), phase
    (the msgid it tells as its phase; the title's own word by default)."""
    steps, pause = int(request.get("steps", 10)), float(request.get("pause", 0.05))
    deaf, fail, refuse = bool(request.get("deaf")), request.get("fail"), request.get("refuse")
    slow = request.get("slow") or {}
    phase = request.get("phase") or N_("Counting")
    held = b"\x01" * (int(request.get("hog", 0)) << 20)        # written, so that it is really in memory
    parts = mine(list(range(steps)), ctx.share)
    ctx.progress(0, len(parts), phase)
    for n, part in enumerate(parts, 1):
        if not deaf:
            ctx.checkpoint()
        time.sleep(pause + float(slow.get(part, 0.0)))
        if fail is not None and part == fail:
            raise RuntimeError(f"the sample failed at part {part}, as asked")
        if refuse is not None and part == refuse:
            raise Refused(f"the sample refused at part {part}, as asked")
        ctx.partial(f"part {part}", part * part)
        ctx.progress(n, len(parts), phase)
    ctx.kept["runs"] = ctx.kept.get("runs", 0) + 1
    return {"parts": parts, "pid": os.getpid(), "runs": ctx.kept["runs"], "held": len(held),
            "tag": request.get("tag")}
