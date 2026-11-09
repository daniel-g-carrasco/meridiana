"""Run by LibreOffice's own Python (not the program's): opens an ODT or a DOCX hidden in a LibreOffice of its own (its
own profile, headless), lays it out, updates its indexes and says what the layout found, as JSON: the size each formula
object takes (the name of its frame, width and height in 1/100 mm), the contents as LibreOffice numbers it (each entry's
text and page), the pages. Nothing is saved: office.py writes the numbers into the file the program made.

    <LibreOffice>/program/python.exe lo_measure.py FILE OUT.json PROFILE_URL SOFFICE

It imports nothing of the program: LibreOffice's Python has only its own modules."""

import json
import os
import subprocess
import sys
import time
import uuid


# com.sun.star.embed.EmbedMapUnits as 1/100 mm
UNITS = {0: 1.0, 1: 10.0, 2: 100.0, 3: 1000.0, 4: 2.54, 5: 25.4, 6: 254.0, 7: 2540.0, 8: 2540 / 72, 9: 2540 / 1440}


def connect(profile_url: str, soffice: str):
    import uno
    pipe = "meridiana" + uuid.uuid4().hex[:12]
    process = subprocess.Popen([soffice, "-env:UserInstallation=" + profile_url, "--headless", "--invisible",
                                "--nologo", "--norestore", "--nodefault", "--nolockcheck",
                                f"--accept=pipe,name={pipe};urp;StarOffice.ComponentContext"])
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    deadline = time.time() + 90
    while True:
        try:
            ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
            return process, ctx
        except Exception:          # noqa: BLE001  not listening yet
            if time.time() > deadline or process.poll() is not None:
                process.kill()
                raise
            time.sleep(0.4)


def prop(name, value):
    import uno
    p = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    p.Name, p.Value = name, value
    return p


def measure(path: str, profile_url: str, soffice: str) -> dict:
    import uno
    process, ctx = connect(profile_url, soffice)
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = None
    try:
        doc = desktop.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(path)), "_blank", 0,
                                           (prop("Hidden", True), prop("ReadOnly", True)))
        formulas = {}
        start = time.time()
        objects = doc.getEmbeddedObjects()
        doc.lockControllers()
        for name in objects.getElementNames():
            obj = objects.getByName(name)
            try:
                model = obj.getEmbeddedObject()
                if model is None or not model.supportsService("com.sun.star.formula.FormulaProperties"):
                    continue
                control = obj.getExtendedControlOverEmbeddedObject()
                size = control.getVisualAreaSize(1)
                factor = UNITS.get(control.getMapUnit(1), 1.0)          # its own unit, in 1/100 mm
                formulas[name] = [round(size.Width * factor), round(size.Height * factor)]
                obj.Size = size          # so the contents' page numbers are those of the formulas at their size
            except Exception:  # noqa: BLE001  an object LibreOffice cannot measure keeps the size it has
                continue
        doc.unlockControllers()
        print("formulas", len(formulas), "%.1f s" % (time.time() - start), file=sys.stderr, flush=True)
        indexes = doc.getDocumentIndexes()
        toc = []
        for i in range(indexes.getCount()):
            index = indexes.getByIndex(i)
            index.update()
            if index.supportsService("com.sun.star.text.ContentIndex") and not toc:
                enum = index.getAnchor().createEnumeration()
                while enum.hasMoreElements():
                    para = enum.nextElement()
                    if para.supportsService("com.sun.star.text.Paragraph"):
                        text = para.getString()
                        if "\t" in text:
                            title, _tab, page = text.rpartition("\t")
                            toc.append([title, page.strip()])
        print("indexes %.1f s" % (time.time() - start), file=sys.stderr, flush=True)
        pages = doc.getCurrentController().getPropertyValue("PageCount") if doc.getCurrentController() else 0
        return {"formulas": formulas, "toc": toc, "pages": pages}
    finally:
        if doc is not None:
            try:
                doc.close(True)
            except Exception:  # noqa: BLE001
                pass
        try:
            desktop.terminate()
        except Exception:  # noqa: BLE001  the bridge goes with it
            pass
        try:
            process.wait(20)
        except Exception:  # noqa: BLE001
            process.kill()


if __name__ == "__main__":
    result = measure(sys.argv[1], sys.argv[3], sys.argv[4])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
