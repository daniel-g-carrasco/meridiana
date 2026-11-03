"""Contact sheets of the photos for looking at: bars stacked, panels side by side. usage: montage.py <photos> <out> <scale> <theme> v1,v2,..."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
ph, out, sc, th, vs = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5].split(",")
out.mkdir(parents=True, exist_ok=True)
def lab(im, text):
    d = ImageDraw.Draw(im); d.rectangle([0, 0, 190, 14], fill=(255, 255, 0)); d.text((3, 1), text, fill=(0, 0, 0)); return im
rows = []
for v in vs:
    p = ph / f"{v}-{sc}x-{th}-bar.png"
    if p.exists():
        im = Image.open(p).convert("RGB"); w = int(1000 * int(sc)); rows.append(lab(im.crop((0, 0, min(im.width, w), im.height)), v))
if rows:
    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows)), "white"); y = 0
    for r in rows: sheet.paste(r, (0, y)); y += r.height
    sheet.save(out / f"bars-{sc}x-{th}.png")
cols = []
for v in vs:
    p = ph / f"{v}-{sc}x-{th}-panel.png"
    if p.exists():
        im = Image.open(p).convert("RGB"); cols.append(lab(im.crop((0, 0, im.width, int(640 * int(sc)))), v))
if cols:
    sheet = Image.new("RGB", (sum(c.width + 6 for c in cols), max(c.height for c in cols)), "white"); x = 0
    for c in cols: sheet.paste(c, (x, 0)); x += c.width + 6
    sheet.save(out / f"panels-{sc}x-{th}.png")
