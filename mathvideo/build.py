"""Build one chapter: scenes -> html -> png frames -> audio mix -> mp4.
usage: python3 build.py ch01 [--noenc] [--only N]
"""
import hashlib, importlib, json, os, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dsl, tts, sfx, bgm  # noqa: E402

WORK = tts.WORK
SR = 44100
FPS = 15
XF = 3  # crossfade frames
PORT = int(os.environ.get("MV_PORT", "8765"))
OUT = os.environ.get("MV_OUT", os.path.join(WORK, "out"))
os.makedirs(OUT, exist_ok=True)


# ------------------------------------------------------------------ html
def page_html(scene, meta, idx, total):
    chip_color = meta.get("color", "#2563eb")
    title = scene.title
    sub = scene.sub
    pct = 100.0 * (idx + 1) / total
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<link rel="stylesheet" href="/node_modules/katex/dist/katex.min.css">
<link rel="stylesheet" href="/node_modules/@fontsource/noto-sans-jp/500.css">
<link rel="stylesheet" href="/node_modules/@fontsource/noto-sans-jp/700.css">
<link rel="stylesheet" href="/node_modules/@fontsource/noto-sans-jp/900.css">
<link rel="stylesheet" href="/static/page.css">
<style>#chip{{background:{chip_color}}} #bar i{{background:linear-gradient(90deg,{chip_color},#0d9488)}}</style>
</head><body><div id="stage">
<div id="top"><div id="chip">{dsl.esc(meta['chip'])}</div><div id="title">{dsl.inline(title)}</div><div id="sub">{dsl.esc(sub)}</div></div>
<div id="content">{scene.content_html()}</div>
<div id="cdl">考えてみよう！</div><div id="cd"></div>
<div id="cnt">{idx + 1} / {total}</div>
<div id="bar"><i style="width:{pct:.1f}%"></i></div>
</div>
<script src="/node_modules/katex/dist/katex.min.js"></script>
<script src="/node_modules/katex/dist/contrib/auto-render.min.js"></script>
<script src="/static/page.js"></script></body></html>"""


# ------------------------------------------------------------------ render
def render_scenes(scenes, meta, chap, only=None):
    """returns dict[(si, t, cd)] -> png path"""
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.join(WORK, "html"), exist_ok=True)
    os.makedirs(os.path.join(WORK, "frames"), exist_ok=True)
    # static assets
    st = os.path.join(WORK, "static")
    os.makedirs(st, exist_ok=True)
    for f in ("page.css", "page.js"):
        subprocess.run(["cp", os.path.join(HERE, "assets", f), os.path.join(st, f)], check=True)
    frames = {}
    jobs = []
    for si, sc in enumerate(scenes):
        html = page_html(sc, meta, si, len(scenes))
        h = hashlib.md5((html + open(os.path.join(HERE, "assets", "page.css")).read() + open(os.path.join(HERE, "assets", "page.js")).read()).encode()).hexdigest()[:12]
        hp = os.path.join(WORK, "html", f"{chap}_{si:02d}.html")
        open(hp, "w").write(html)
        for t, b in enumerate(sc.beats, start=1):
            states = [(t, 0)]
            if b.think:
                states = [(t, 0)] + [(t, c) for c in range(b.think, 0, -1)]
            for (tt, cd) in states:
                png = os.path.join(WORK, "frames", f"{h}_{tt}_{cd}.jpg")
                frames[(si, tt, cd)] = png
                if not os.path.exists(png):
                    jobs.append((si, hp, tt, cd, png))
    if jobs:
        with sync_playwright() as p:
            br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
                                   args=["--no-sandbox", "--font-render-hinting=none"])
            pg = br.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
            cur = None
            for si, hp, tt, cd, png in jobs:
                if cur != si:
                    pg.goto(f"http://localhost:{PORT}/html/{os.path.basename(hp)}")
                    pg.wait_for_function("window.READY===true", timeout=60000)
                    errs = pg.evaluate("window.ERRS")
                    if errs:
                        print(f"[KaTeX error] scene {si} {scenes[si].title}: {errs}")
                    fit = pg.evaluate("window.FIT")
                    if fit < 0.97:
                        print(f"[fit] scene {si} '{scenes[si].title}' scaled to {fit:.2f}")
                    cur = si
                pg.evaluate(f"setState({tt},{cd})")
                pg.screenshot(path=png, type="jpeg", quality=95)
            br.close()
    return frames


# ------------------------------------------------------------------ timeline
def q(sec):
    return max(1, int(round(sec * FPS)))


def build_timeline(scenes):
    """list of beat records with frame counts. Also returns narration pairs."""
    pairs = [(b.say, b.voice) for sc in scenes for b in sc.beats if b.say]
    tts.ensure(pairs)
    recs = []
    for si, sc in enumerate(scenes):
        for bi, b in enumerate(sc.beats):
            first = (bi == 0)
            pre = b.pre if b.pre is not None else (0.55 if first else 0.22)
            speech = tts.load(b.say, b.voice) if b.say else np.zeros(0, dtype=np.float32)
            sp = len(speech) / SR
            gap = b.gap if b.gap is not None else (0.55 if b.say else 0.0)
            if b.say:
                dur = pre + sp + gap
            else:
                dur = b.dur if b.dur is not None else 1.2
            nf = q(dur)
            think_frames = []
            if b.think:
                per = q(1.0)
                think_frames = [per] * b.think
            recs.append(dict(si=si, bi=bi, t=bi + 1, pre=pre, speech=speech, nf=nf, think=think_frames,
                             sfx=b.sfx, first=first, say=b.say))
    return recs


# ------------------------------------------------------------------ video frames
def blend_frames(a, b, k, chap, tag):
    from PIL import Image
    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    out = []
    for i in range(1, k + 1):
        w = i / (k + 1)
        p = os.path.join(WORK, "xfade", f"{tag}_{i}.jpg")
        if not os.path.exists(p):
            Image.blend(ia, ib, w).save(p, quality=93)
        out.append(p)
    return out


def make_sequence(recs, frames, chap):
    os.makedirs(os.path.join(WORK, "xfade"), exist_ok=True)
    seq = []  # (path, nframes)
    prev = None
    for r in recs:
        png = frames[(r["si"], r["t"], 0)]
        nf = r["nf"]
        if prev is not None and prev != png and nf > XF + 1:
            tag = hashlib.md5((prev + png).encode()).hexdigest()[:14]
            xf = blend_frames(prev, png, XF, chap, tag)
            for p in xf:
                seq.append((p, 1))
            nf -= XF
        seq.append((png, nf))
        prev = png
        for i, per in enumerate(r["think"]):
            cdpng = frames[(r["si"], r["t"], r["think"].__len__() - i)]
            seq.append((cdpng, per))
            prev = cdpng
    return seq


# ------------------------------------------------------------------ audio
def build_audio(recs, scenes, meta, lead, tail):
    sfx_cache = {}
    total_frames = lead + sum(r["nf"] + sum(r["think"]) for r in recs) + tail
    n = int(total_frames / FPS * SR) + SR
    voice = np.zeros(n, dtype=np.float32)
    fx = np.zeros(n, dtype=np.float32)
    mask = np.zeros(n, dtype=np.float32)
    thinkmask = np.zeros(n, dtype=np.float32)
    cur = lead / FPS
    starts = []
    scene_first = {}
    for r in recs:
        t0 = cur
        starts.append((r["si"], r["t"], t0))
        i0 = int(t0 * SR)
        # sfx
        def put(name, at, gain=1.0):
            x = sfx.get(name) * gain
            j = int(at * SR)
            fx[j:j + len(x)] += x[: max(0, n - j)][: len(fx[j:j + len(x)])]
        if r["first"]:
            put("whoosh", t0 + 0.02, 0.7)
            if r["sfx"] not in ("whoosh",):
                put(r["sfx"], t0 + 0.30, 0.8)
        else:
            put(r["sfx"], t0 + 0.02, 0.9 if r["sfx"] not in ("tick", "pop") else 0.8)
        sp = r["speech"]
        if len(sp):
            j = i0 + int(r["pre"] * SR) + (int(0.25 * SR) if r["first"] else 0)
            if r["sfx"] in ("card", "chime", "sparkle", "ding", "warn"):
                j += int(0.12 * SR)
            voice[j:j + len(sp)] += sp[: n - j]
            mask[j:j + len(sp)] = 1.0
        cur += r["nf"] / FPS
        if r["think"]:
            tstart = cur
            for k, per in enumerate(r["think"]):
                at = cur + k * per / FPS
                last3 = (len(r["think"]) - k) <= 3
                j = int(at * SR)
                x = sfx.get("beep" if last3 else "clock") * (1.0 if last3 else 0.9)
                fx[j:j + len(x)] += x[: n - j][: len(fx[j:j + len(x)])]
            cur += sum(r["think"]) / FPS
            thinkmask[int(tstart * SR):int(cur * SR)] = 1.0
    dur_s = total_frames / FPS
    # bgm
    tracks = meta.get("bgm", ["calm", "focus"])
    pieces = []
    seg = 0
    per = 150 * SR  # switch track every 150 s
    arr = np.zeros((2, n), dtype=np.float32)
    pos = 0
    ti = 0
    while pos < n:
        ln = min(per, n - pos)
        arr[:, pos:pos + ln] = bgm.track(tracks[ti % len(tracks)], ln)
        # short crossfade at joins
        if pos > 0:
            cf = int(2.0 * SR)
            ramp = np.linspace(0, 1, cf, dtype=np.float32)
            prevt = bgm.track(tracks[(ti - 1) % len(tracks)], pos + cf)[:, pos:pos + cf]
            arr[:, pos:pos + cf] = prevt * (1 - ramp) + arr[:, pos:pos + cf] * ramp
        pos += ln
        ti += 1
    # ducking envelope
    def smooth(m, att, rel):
        out = np.zeros_like(m)
        a = np.exp(-1.0 / (att * SR))
        r_ = np.exp(-1.0 / (rel * SR))
        # vectorised-ish: block processing with IIR via loop on downsampled signal
        step = 441
        md = m[::step]
        o = np.zeros_like(md)
        v = 0.0
        ad = np.exp(-step / (att * SR))
        rd = np.exp(-step / (rel * SR))
        for i, x in enumerate(md):
            v = x + (v - x) * (ad if x > v else rd)
            o[i] = v
        return np.interp(np.arange(len(m)), np.arange(len(o)) * step, o).astype(np.float32)
    act = smooth(np.clip(mask, 0, 1), 0.12, 0.45)
    base = float(meta.get("bgm_gain", 0.22))
    gain = base * (1 - 0.62 * act)
    gain = gain * (1 + 0.45 * thinkmask)  # slightly louder while thinking
    # chapter fade in/out
    fi = np.minimum(1, np.arange(n) / (1.5 * SR)).astype(np.float32)
    fo = np.minimum(1, np.maximum(0, (dur_s * SR - np.arange(n)) / (2.5 * SR))).astype(np.float32)
    gain = gain * fi * fo
    L = voice + fx + arr[0] * gain
    R = voice + fx + arr[1] * gain
    st = np.stack([L, R], axis=1)
    pk = np.max(np.abs(st))
    if pk > 0.98:
        st = st * (0.98 / pk)
    nsamp = int(dur_s * SR)
    return st[:nsamp].astype(np.float32), starts


# ------------------------------------------------------------------ main
def part_intro(meta, label, subscenes, say_title):
    """auto title card for the 2nd.. part of a long lesson"""
    from lib import Scene, Raw, inline, esc
    sc = Scene("続きから", label, kind="title")
    items = [x.title for x in subscenes if "答え" not in x.title][:7]
    lis = "".join(f'<div class="goal"><i>{i}</i><div>{inline(t)}</div></div>' for i, t in enumerate(items, 1))
    sc.beat(f"ここからは、{say_title}の、{label}です。前の動画の、続きから、進めていきましょう。",
            Raw(f'<div class="titlecard"><div class="tnum">{esc(meta["chip"].split()[0])} {esc(label)}</div>'
                f'<div class="tbig" style="font-size:84px">{inline(meta["title"])}</div></div>'), sfx="sparkle", pre=0.9)
    sc.beat("この動画では、次の内容を学びます。", Raw('<div style="display:flex;flex-direction:column;gap:14px">' + lis + "</div>"), sfx="ding")
    return sc


def build(chap, enc=True, only=None):
    mod = importlib.import_module(f"content.{chap}")
    importlib.reload(mod)
    meta = mod.META
    scenes = mod.build()
    parts = getattr(mod, "PARTS", None)
    if only is not None:
        scenes = [scenes[i] for i in only]
        parts = None
    if not parts:
        return build_one(chap, scenes, meta, enc)
    starts = []
    for label, st in parts:
        if st is None:
            starts.append(0)
        else:
            idx = next((i for i, sc in enumerate(scenes) if sc.title.startswith(st)), None)
            if idx is None:
                raise ValueError(f"PARTS start title not found: {st}")
            starts.append(idx)
    ends = starts[1:] + [None]
    for pi, ((label, _), a, b) in enumerate(zip(parts, starts, ends)):
        sub = scenes[a:b]
        m2 = dict(meta)
        m2["chip"] = f"{meta['chip']} {label}"
        if pi > 0:
            sub = [part_intro(meta, label, sub, meta.get("say", meta["title"]))] + sub
        build_one(f"{chap}{'abcdefgh'[pi]}", sub, m2, enc)


def build_one(chap, scenes, meta, enc=True):
    t0 = time.time()
    recs = build_timeline(scenes)
    nbeats = len(recs)
    print(f"[{chap}] scenes={len(scenes)} beats={nbeats} tts+timeline {time.time() - t0:.1f}s")
    frames = render_scenes(scenes, meta, chap)
    print(f"[{chap}] frames ready {time.time() - t0:.1f}s")
    lead = q(0.4)
    tail = q(1.8)
    seq = make_sequence(recs, frames, chap)
    first_png = seq[0][0]
    seq = [(first_png, lead)] + seq + [(seq[-1][0], tail)]
    audio, starts = build_audio(recs, scenes, meta, lead, tail)
    aud_path = os.path.join(WORK, f"{chap}.wav")
    import wave
    with wave.open(aud_path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    lst = os.path.join(WORK, f"{chap}_frames.txt")
    with open(lst, "w") as f:
        for p, nf in seq:
            f.write(f"file '{p}'\nduration {nf / FPS:.6f}\n")
        f.write(f"file '{seq[-1][0]}'\n")
    dur = sum(nf for _, nf in seq) / FPS
    scene_marks, seen = [], set()
    for si, t, st in starts:
        if si not in seen:
            seen.add(si)
            scene_marks.append((scenes[si].title, st))
    json.dump(dict(duration=dur, scenes=scene_marks, title=meta["title"], chip=meta["chip"]),
              open(os.path.join(OUT, f"{chap}.json"), "w"), ensure_ascii=False)
    if not enc:
        print(f"[{chap}] duration {dur:.1f}s ({dur / 60:.1f} min, not encoded)")
        return
    mp4 = os.path.join(OUT, f"{chap}.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", aud_path,
           "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "28", "-tune", "stillimage",
           "-profile:v", "high", "-c:a", "aac", "-b:a", "64k", "-ar", "44100",
           "-af", "loudnorm=I=-17:TP=-1.5:LRA=11", "-movflags", "+faststart", "-t", f"{dur:.3f}", mp4]
    subprocess.run(cmd, check=True)
    print(f"[{chap}] done {dur / 60:.1f} min -> {mp4} ({os.path.getsize(mp4) / 1e6:.1f} MB) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    chap = sys.argv[1]
    only = None
    if "--only" in sys.argv:
        only = [int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")]
    build(chap, enc="--noenc" not in sys.argv, only=only)
