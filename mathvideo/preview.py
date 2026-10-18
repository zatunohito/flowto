"""usage: python3 preview.py ch01 [scene_idx ...]  -> contact sheet(s) of the final state of scenes (or all states of one scene with -a)"""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build
from PIL import Image

chap = sys.argv[1]
args = [a for a in sys.argv[2:] if not a.startswith("-")]
mod = importlib.import_module(f"content.{chap}")
scenes = mod.build()
frames = build.render_scenes(scenes, mod.META, chap)
all_states = "-a" in sys.argv
sel = [int(a) for a in args] if args else list(range(len(scenes)))
tiles = []
for si in sel:
    n = len(scenes[si].beats)
    ts = range(1, n + 1) if all_states else [n]
    for t in ts:
        tiles.append((si, t, frames[(si, t, 0)]))
per = 6 if len(tiles) > 6 else len(tiles)
W, H = 960, 540
out_i = 0
for k in range(0, len(tiles), 6):
    chunk = tiles[k:k + 6]
    rows = (len(chunk) + 1) // 2
    sheet = Image.new("RGB", (W * 2, H * rows), "white")
    for i, (si, t, p) in enumerate(chunk):
        im = Image.open(p).resize((W, H))
        sheet.paste(im, ((i % 2) * W, (i // 2) * H))
    path = os.path.join(build.WORK, f"prev_{chap}_{out_i}.jpg")
    sheet.save(path, quality=88)
    print(path, [(si, t) for si, t, _ in chunk])
    out_i += 1
