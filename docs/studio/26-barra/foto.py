"""The drawings of studies 26 and 27 photographed with headless Chrome, the empty bottom cut away.
python foto.py <html> <query or -> <width> <out.png> [height]"""

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def shot(html: str, query: str, width: int, out: str, height: int = 9000) -> None:
    url = Path(html).resolve().as_uri() + ("" if query == "-" else "?" + query)
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                        f"--window-size={width},{height}", "--virtual-time-budget=1500", f"--screenshot={Path(out).resolve()}", url],
                       check=True, capture_output=True, timeout=120)
    image = Image.open(out).convert("RGB")
    ground = Image.new("RGB", image.size, image.getpixel((image.width - 1, image.height - 1)))
    box = ImageChops.difference(image, ground).getbbox()
    if box:
        image = image.crop((0, 0, image.width, min(image.height, box[3] + 16)))
    image.save(out, optimize=True)
    print(out, image.size)


if __name__ == "__main__":
    shot(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 9000)
