"""Assemble labelled comparisons, native-pixel details and a capture manifest."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]


def save(image, path):
    if path.exists():
        raise FileExistsError(path)
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    folder = args.output / 'R02'
    font_path = ROOT / 'data/fonts/ibm-plex/IBMPlexSans-Regular.ttf'
    font = ImageFont.truetype(str(font_path), 18)
    title = ImageFont.truetype(str(font_path), 24)
    manifest = []
    for theme in ('light', 'dark'):
        dark = theme == 'dark'
        bg, ink = ('#171b23', '#eeeeef') if dark else ('#f4f4f5', '#25252b')
        board = Image.new('RGB', (1560, 1120), bg)
        draw = ImageDraw.Draw(board)
        draw.text((24, 16), f'Cubo delle viste | {"Scuro" if dark else "Chiaro"}', font=title, fill=ink)
        draw.text((24, 50), 'Scene QML isolate, tema e controlli reali. Dimensione del cubo: 76 px logici.', font=font, fill=ink)
        for col, (variant, name) in enumerate((('A', 'Oggi'), ('B', 'Cubo leggibile'), ('C', 'Comandi nella barra'))):
            x = 20+col*520
            draw.text((x, 96), f'{variant} | {name}', font=title, fill=ink)
            for row, state in enumerate(('rest', 'face')):
                y = 140+row*200
                draw.text((x, y), f'Scala 1 | {"Riposo" if state == "rest" else "Puntatore sulla faccia"}', font=font, fill=ink)
                im = Image.open(folder / f'{variant}-{theme}-x1.0-{state}.png')
                assert im.size == (420, 260), im.size
                board.paste(im.crop((0, 0, 420, 160)), (x, y+28))
            draw.text((x, 550), 'Scala 2,5 | dettagli a pixel nativi', font=font, fill=ink)
            for col2, state in enumerate(('rest', 'face')):
                im = Image.open(folder / f'{variant}-{theme}-x2.5-{state}.png')
                assert im.size == (1050, 650), im.size
                # The whole cube and North sign, at 2.5 physical px per logical px.
                detail = im.crop((840, 0, 1050, 340))
                dx = x+col2*244
                draw.text((dx, 584), 'Riposo' if state == 'rest' else 'Faccia', font=font, fill=ink)
                board.paste(detail, (dx, 614))
            draw.text((x, 974), 'Barra a scala 2,5', font=font, fill=ink)
            im = Image.open(folder / f'{variant}-{theme}-x2.5-rest.png')
            board.paste(im.crop((20, 20, 520, 120)), (x, 1002))
        save(board, args.output / f'tavola-{theme}.png')
        # Extra sheet: edge/corner feedback, arrow and open menu at scale 1.
        proof = Image.new('RGB', (1440, 1020), bg)
        draw = ImageDraw.Draw(proof)
        draw.text((20, 12), f'Stati aggiuntivi | {theme} | scala 1', font=title, fill=ink)
        for col, variant in enumerate(('A', 'B', 'C')):
            for row, state in enumerate(('edge', 'corner', 'arrow', 'menu')):
                x, y = 16+col*480, 60+row*240
                draw.text((x, y), f'{variant} | {state}', font=font, fill=ink)
                path = folder / f'{variant}-{theme}-x1.0-{state}.png'
                if path.exists():
                    proof.paste(Image.open(path).crop((0, 0, 420, 210)), (x, y+26))
        save(proof, args.output / f'stati-{theme}.png')
    for path in sorted(folder.glob('*.png')):
        im = Image.open(path)
        manifest.append({'file': path.name, 'size': im.size,
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    assert len(list(folder.glob('real-*-context.png'))) == 24
    assert len(list(folder.glob('[ABC]-*.png'))) == 64
    out = args.output / 'manifest-R02.json'
    if out.exists():
        raise FileExistsError(out)
    out.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Verified: 24 real states, 64 proposal states, {len(manifest)} PNG files; boards 1560 px wide.')


if __name__ == '__main__':
    main()
