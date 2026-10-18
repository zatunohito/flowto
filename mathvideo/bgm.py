"""Synthesised BGM loops (stereo float32, SR=44100). Gentle pad + mallet arpeggio + bass + reverb."""
import os
import numpy as np

SR = 44100
WORK = os.environ.get("MV_WORK", "/tmp/claude-0/-home-user-flowto/822ad1fa-d985-5ed3-936a-0b5a6da616d3/scratchpad/work")
CACHE = os.path.join(WORK, "bgm_cache")
os.makedirs(CACHE, exist_ok=True)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tone_pad(f, dur, amp):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for det in (-0.004, 0.0, 0.004):
        ff = f * (1 + det)
        x += np.sin(2 * np.pi * ff * t) + 0.35 * np.sin(2 * np.pi * 2 * ff * t) + 0.12 * np.sin(2 * np.pi * 3 * ff * t)
    a, r = 0.9, 1.1
    env = np.minimum(1, t / a) * np.minimum(1, np.maximum(0, (dur - t) / r))
    return x / 3 * env * amp


def tone_pluck(f, dur, amp, tau=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * 2.0 * t) * 1.4 * np.exp(-t / 0.12)
    x = np.sin(2 * np.pi * f * t + mod) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.08)
    env = np.exp(-t / tau) * np.minimum(1, t / 0.004)
    return x * env * amp


def tone_bass(f, dur, amp):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    env = np.exp(-t / 1.1) * np.minimum(1, t / 0.02) * np.minimum(1, np.maximum(0, (dur - t) / 0.25))
    return x * env * amp


def add(buf, x, at):
    i = int(at * SR)
    j = min(len(buf), i + len(x))
    if i < len(buf):
        buf[i:j] += x[: j - i]


SPECS = {
    # name: (bpm, chords[(bass_midi, [chord midi...])], arp patterns, arp octave offset, pad amp, arp amp)
    "calm": dict(bpm=76, chords=[(36, [60, 64, 67, 71]), (33, [57, 60, 64, 67]), (29, [57, 60, 65, 69]), (31, [59, 62, 67, 69]),
                                 (36, [60, 64, 67, 71]), (33, [57, 60, 64, 67]), (38, [58, 62, 65, 69]), (31, [59, 62, 67, 74])],
                 pat=[[0, 2, 1, 3, 2, 1, 3, 2], [0, 1, 2, 3, 2, 1, 2, 1]], oct=12, pad=0.10, arp=0.11),
    "focus": dict(bpm=88, chords=[(38, [62, 65, 69, 72]), (31, [59, 62, 65, 69]), (36, [60, 64, 67, 71]), (33, [57, 60, 64, 67]),
                                  (38, [62, 65, 69, 72]), (31, [59, 62, 65, 69]), (40, [59, 64, 67, 71]), (29, [60, 65, 69, 72])],
                  pat=[[0, None, 2, None, 1, None, 3, 2], [0, 2, None, 1, 3, None, 2, None]], oct=12, pad=0.09, arp=0.10),
    "bright": dict(bpm=104, chords=[(36, [60, 64, 67, 72]), (31, [59, 62, 67, 71]), (33, [57, 60, 64, 69]), (29, [60, 65, 69, 72]),
                                    (36, [60, 64, 67, 72]), (31, [59, 62, 67, 71]), (29, [60, 65, 69, 72]), (31, [62, 67, 71, 74])],
                   pat=[[0, 1, 2, 3, 2, 1, 2, 3], [3, 2, 1, 0, 1, 2, 3, 2]], oct=12, pad=0.11, arp=0.13),
}


B_PHRASE = {
    "calm": [(29, [57, 60, 65, 69]), (40, [59, 64, 67, 71]), (38, [57, 62, 65, 69]), (31, [59, 62, 65, 69]),
             (36, [60, 64, 67, 71]), (33, [57, 60, 64, 67]), (38, [57, 62, 65, 69]), (31, [62, 67, 71, 74])],
    "focus": [(33, [57, 60, 64, 67]), (38, [62, 65, 69, 72]), (31, [59, 62, 65, 69]), (36, [60, 64, 67, 71]),
              (29, [60, 65, 69, 72]), (31, [59, 62, 67, 71]), (33, [57, 60, 64, 67]), (31, [59, 62, 65, 69])],
    "bright": [(33, [57, 60, 64, 69]), (29, [60, 65, 69, 72]), (36, [60, 64, 67, 72]), (31, [59, 62, 67, 71]),
               (33, [57, 60, 64, 69]), (29, [60, 65, 69, 72]), (31, [62, 67, 71, 74]), (36, [60, 64, 67, 72])],
}


def _reverb(x2, wet=0.28, secs=1.8):
    n = int(secs * SR)
    outs = []
    for ch in range(2):
        r = np.random.default_rng(100 + ch)
        ir = r.standard_normal(n) * np.exp(-np.arange(n) / (SR * secs / 4.5))
        ir[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
        ir /= np.sqrt(np.sum(ir ** 2))
        L = len(x2[ch]) + n
        N = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x2[ch], N) * np.fft.rfft(ir, N), N)[: len(x2[ch])]
        outs.append(x2[ch] * (1 - wet) + y * wet)
    return np.stack(outs)


def make(name):
    p = os.path.join(CACHE, name + ".npy")
    if os.path.exists(p):
        return np.load(p)
    s = dict(SPECS[name])
    s["chords"] = s["chords"] + B_PHRASE[name]
    beat = 60.0 / s["bpm"]
    bar = beat * 4
    nbars = len(s["chords"])
    loop = bar * nbars
    cycles = 2
    total = loop * cycles + 4.0
    L = np.zeros(int(total * SR))
    R = np.zeros(int(total * SR))
    rng = np.random.default_rng(3)
    for cyc in range(cycles):
        for bi, (bass, chord) in enumerate(s["chords"]):
            t0 = cyc * loop + bi * bar
            for note in chord:
                x = tone_pad(mtof(note - 12 + 12), bar + 0.4, s["pad"] / len(chord) * 2.2)
                add(L, x, t0)
                add(R, x, t0)
            b = tone_bass(mtof(bass), bar * 0.95, 0.20)
            add(L, b, t0)
            add(R, b, t0)
            add(L, tone_bass(mtof(bass), beat * 1.8, 0.12), t0 + beat * 2)
            add(R, tone_bass(mtof(bass), beat * 1.8, 0.12), t0 + beat * 2)
            pat = s["pat"][(bi // 2) % len(s["pat"])]
            for k, idx in enumerate(pat):
                if idx is None:
                    continue
                at = t0 + k * beat / 2
                note = chord[idx % len(chord)] + s["oct"] + (12 if (bi % 4 == 3 and k == 7) else 0)
                vel = 1.0 if k % 4 == 0 else (0.75 if k % 2 == 0 else 0.55)
                vel *= 0.9 + 0.2 * rng.random()
                x = tone_pluck(mtof(note), 1.4, s["arp"] * vel)
                pan = 0.35 + 0.3 * ((k % 4) / 3)
                add(L, x * (1 - pan) * 1.4, at)
                add(R, x * pan * 1.4, at)
    st = _reverb(np.stack([L, R]))
    a = int(loop * SR) * 1
    seg = st[:, a: a + int(loop * SR)]
    seg = seg / (np.max(np.abs(seg)) + 1e-9) * 0.8
    seg = seg.astype(np.float32)
    np.save(p, seg)
    return seg


def track(name, nsamples):
    base = make(name)
    reps = int(np.ceil(nsamples / base.shape[1]))
    return np.tile(base, (1, reps))[:, :nsamples]
