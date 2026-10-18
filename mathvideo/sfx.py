"""Synthesised sound effects (mono float32, SR=44100)."""
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def _t(n):
    return np.arange(n) / SR


def _fade(x, a=0.002, r=0.01):
    n = len(x)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    x = x.copy()
    x[:na] *= np.linspace(0, 1, na)
    x[-nr:] *= np.linspace(1, 0, nr)
    return x


def _bell(f, dur, tau, amp=1.0, parts=((1, 1.0), (2.0, 0.35), (3.01, 0.18), (4.2, 0.08))):
    n = int(dur * SR)
    t = _t(n)
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / (tau / (1 + 0.6 * (m - 1)))) for m, a in parts)
    return _fade(x * amp, 0.001, 0.02)


def _place(buf, x, at):
    i = int(at * SR)
    if i + len(x) > len(buf):
        buf = np.pad(buf, (0, i + len(x) - len(buf)))
    buf[i:i + len(x)] += x
    return buf


def pop():
    n = int(0.16 * SR)
    t = _t(n)
    f = 900 * np.exp(-t * 6) + 450
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035)
    return _fade(x * 0.30)


def tick():
    n = int(0.07 * SR)
    t = _t(n)
    x = np.sin(2 * np.pi * 1900 * t) * np.exp(-t / 0.012) * 0.5 + (rng.standard_normal(n) * np.exp(-t / 0.004)) * 0.25
    return _fade(x * 0.35, 0.0005, 0.01)


def card():
    n = int(0.22 * SR)
    t = _t(n)
    f = 300 + 1100 * (t / 0.22) ** 1.5
    sw = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.22) ** 1.5 * 0.18
    buf = _place(np.zeros(int(0.9 * SR), dtype=np.float64), sw, 0)
    buf = _place(buf, _bell(1318.5, 0.7, 0.28, 0.20), 0.14)
    return buf


def ding():
    return _bell(1568.0, 1.0, 0.35, 0.22)


def chime():
    buf = np.zeros(int(1.5 * SR))
    for i, f in enumerate([1046.5, 1318.5, 1568.0, 2093.0]):
        buf = _place(buf, _bell(f, 1.0, 0.45, 0.17), i * 0.085)
    return buf


def sparkle():
    buf = np.zeros(int(1.0 * SR))
    for i in range(7):
        buf = _place(buf, _bell(float(rng.integers(2600, 5200)), 0.35, 0.08, 0.10, parts=((1, 1.0), (2.0, 0.2))), i * 0.05 + rng.random() * 0.02)
    return buf


def warn():
    buf = np.zeros(int(0.7 * SR))
    for i in range(2):
        n = int(0.16 * SR)
        t = _t(n)
        x = (np.sign(np.sin(2 * np.pi * 196 * t)) * 0.5 + np.sin(2 * np.pi * 196 * t) * 0.5) * np.exp(-t / 0.12)
        buf = _place(buf, _fade(x * 0.20), i * 0.2)
    return buf


def whoosh():
    n = int(0.65 * SR)
    t = _t(n)
    noise = rng.standard_normal(n)
    a = 0.02 + 0.55 * np.sin(np.pi * t / 0.65) ** 2          # cutoff coefficient sweep
    y = np.zeros(n)
    z = 0.0
    for i in range(n):
        z += a[i] * (noise[i] - z)
        y[i] = z
    # second pass for steeper slope
    z = 0.0
    for i in range(n):
        z += a[i] * (y[i] - z)
        y[i] = z
    env = np.sin(np.pi * t / 0.65) ** 1.5
    y = y / (np.max(np.abs(y)) + 1e-9) * env * 0.30
    return _fade(y, 0.02, 0.05)


def clock():
    n = int(0.05 * SR)
    t = _t(n)
    x = np.sin(2 * np.pi * 1300 * t) * np.exp(-t / 0.01) * 0.4
    return _fade(x * 0.30, 0.0005, 0.01)


def beep():
    n = int(0.16 * SR)
    t = _t(n)
    return _fade(np.sin(2 * np.pi * 988 * t) * 0.20, 0.005, 0.04)


def fanfare():
    buf = np.zeros(int(2.4 * SR))
    for i, f in enumerate([523.25, 659.25, 783.99, 1046.5]):
        buf = _place(buf, _bell(f, 1.6, 0.8, 0.20), i * 0.16)
    buf = _place(buf, _bell(1318.5, 1.6, 0.9, 0.16), 0.64)
    return buf


_BANK = {}


def get(name):
    if name not in _BANK:
        _BANK[name] = globals()[name]().astype(np.float32)
    return _BANK[name]
