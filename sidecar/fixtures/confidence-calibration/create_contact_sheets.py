#!/usr/bin/env python3
"""Inspect selected originals without labels, model predictions, or evaluation outputs."""
import json
import pathlib
from PIL import Image, ImageDraw, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent
selection = json.loads((ROOT / 'selection.freeze.json').read_bytes())
for split in ('calibration', 'heldout'):
    entries = [e for e in selection['images'] if e['split'] == split and e['stratum'] == 'no_person_annotation']
    assert len(entries) == 20
    sheet = Image.new('RGB', (1200, 5 * 265), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, entry in enumerate(entries):
        record = json.loads((ROOT / 'source' / 'fetch-records' / f"{entry['id']}.json").read_bytes())
        original = Image.open(ROOT / record['manifestImage']['asset']).convert('RGB')
        tile = ImageOps.contain(original, (292, 235))
        x, y = (index % 4) * 300, (index // 4) * 265
        sheet.paste(tile, (x + (300-tile.width)//2, y + (235-tile.height)//2))
        draw.text((x + 5, y + 238), f"{entry['imageId']:012d} / {split}", fill='black')
    path = ROOT / f'negative-contactsheet-{split}.png'
    sheet.save(path)
    print(path)
