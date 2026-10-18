"""Japanese narration via edge-tts (cached by text hash). Returns float32 mono arrays at SR."""
import asyncio, hashlib, os, ssl, subprocess, sys
import numpy as np

SR = 44100
WORK = os.environ.get("MV_WORK", "/tmp/claude-0/-home-user-flowto/822ad1fa-d985-5ed3-936a-0b5a6da616d3/scratchpad/work")
CACHE = os.path.join(WORK, "tts_cache")
VOICES = {"N": "ja-JP-NanamiNeural", "K": "ja-JP-KeitaNeural"}
RATE = {"N": "-4%", "K": "-4%"}
os.makedirs(CACHE, exist_ok=True)


_KAN = "〇一二三四五六七八九"


def norm(text):
    """spoken-form normalisation: (3) -> 三番, 数学I -> 数学一"""
    import re
    t = re.sub(r"\((\d)\)", lambda m: _KAN[int(m.group(1))] + "番", text)
    t = t.replace("数学I", "数学一")
    return t


def _key(text, voice):
    return hashlib.md5(f"{voice}|{RATE[voice]}|{text}".encode()).hexdigest()


def mp3_path(text, voice):
    return os.path.join(CACHE, _key(norm(text), voice) + ".mp3")


async def _one(sem, text, voice):
    import edge_tts.communicate as c
    c._SSL_CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")
    p = mp3_path(text, voice)
    if os.path.exists(p) and os.path.getsize(p) > 500:
        return
    async with sem:
        for attempt in range(6):
            try:
                com = c.Communicate(norm(text), VOICES[voice], rate=RATE[voice], proxy=os.environ.get("HTTPS_PROXY"))
                await com.save(p + ".tmp")
                if os.path.getsize(p + ".tmp") > 500:
                    os.replace(p + ".tmp", p)
                    return
            except Exception as e:  # noqa
                await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"TTS failed: {text[:40]}")


def ensure(pairs, conc=6):
    pairs = sorted(set(pairs))
    todo = [(t, v) for t, v in pairs if not (os.path.exists(mp3_path(t, v)) and os.path.getsize(mp3_path(t, v)) > 500)]
    if not todo:
        return

    async def main():
        sem = asyncio.Semaphore(conc)
        await asyncio.gather(*[_one(sem, t, v) for t, v in todo])
    asyncio.run(main())


_mem = {}


def load(text, voice):
    k = (text, voice)
    if k in _mem:
        return _mem[k]
    p = mp3_path(text, voice)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32).copy()
    # trim leading/trailing near-silence, normalise RMS of active part
    thr = 0.01
    idx = np.where(np.abs(a) > thr)[0]
    if len(idx):
        a = a[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.05 * SR)]
    act = a[np.abs(a) > thr]
    rms = np.sqrt(np.mean(act ** 2)) if len(act) else 0.1
    a = a * (0.115 / max(rms, 1e-4))
    pk = np.max(np.abs(a))
    if pk > 0.95:
        a = a * (0.95 / pk)
    _mem[k] = a.astype(np.float32)
    return _mem[k]
