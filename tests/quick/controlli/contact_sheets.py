"""Pack every indexed pair at 200 percent into readable review sheets."""
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main():
    source = Path('docs/quick/confronto/controlli')
    destination = Path('build/quick-foto/r13-controlli/review')
    destination.mkdir(parents=True, exist_ok=True)
    index = []
    for manifest in sorted(source.glob('manifest-*.json')):
        rows, height, part = [], 0, 0

        def save(stem=manifest.stem):
            nonlocal rows, height, part
            if not rows:
                return
            canvas = Image.new('RGB', (1450, height), '#d7d7d7')
            draw = ImageDraw.Draw(canvas)
            y = 0
            for record, a, b in rows:
                draw.text((4, y+2), record['stem'], fill='#111111')
                y += 20
                canvas.paste(a, (0, y))
                canvas.paste(b, (730, y))
                y += max(a.height, b.height) + 8
            name = f'{stem}-{part:02}.png'
            canvas.save(destination / name)
            index.append(dict(sheet=name, pairs=[r['stem'] for r, _, _ in rows]))
            part += 1
            rows, height = [], 0

        for record in json.loads(manifest.read_text(encoding='utf-8')):
            pair = []
            for engine in ('widgets', 'quick'):
                image = Image.open(source / f'{record["stem"]}-{engine}.png').convert('RGB')
                pair.append(image.resize((record['width']*2, record['height']*2)))
            row_height = max(image.height for image in pair) + 28
            if height + row_height > 1600:
                save()
            rows.append((record, *pair))
            height += row_height
        save()
    (destination / 'index.json').write_text(json.dumps(index, indent=2), encoding='utf-8')
    print(f'{len(index)} sheets, {sum(len(row["pairs"]) for row in index)} pairs')


if __name__ == '__main__':
    main()
