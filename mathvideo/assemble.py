"""Collect part mp4s -> output/ (ASCII names), build chaptered full video, write README.
usage: python3 assemble.py
"""
import glob, importlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa

OUT = build.OUT
DEST = os.path.join(HERE, "output")
SLUG = {"ch00": "00_intro", "ch01": "01_factor_tasuki", "ch02": "02_factor_patterns", "ch03": "03_factor_descending_order",
        "ch04": "04_cubic_formulas", "ch05": "05_practice_expand_factor", "ch06": "06_rational_decimals",
        "ch07": "07_real_numbers_abs", "ch08": "08_radicals_basics", "ch09": "09_rationalize_symmetric_nested",
        "ch10": "10_practice_real_radical"}
FULL = "math1_shiki_to_jissuu_full.mp4"


def parts():
    res = []
    for ch in sorted(SLUG):
        mod = importlib.import_module(f"content.{ch}")
        pp = getattr(mod, "PARTS", None)
        if pp:
            for i, (label, _) in enumerate(pp):
                res.append((f"{ch}{'abcdefgh'[i]}", f"{SLUG[ch].split('_', 1)[0]}{'abcdefgh'[i]}_{SLUG[ch].split('_', 1)[1]}.mp4", mod.META, label))
        else:
            res.append((ch, f"{SLUG[ch]}.mp4", mod.META, ""))
    return res


def fmt(sec):
    sec = int(round(sec))
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def main():
    os.makedirs(DEST, exist_ok=True)
    rows, total = [], 0.0
    meta_lines = [";FFMETADATA1"]
    lst = []
    t = 0.0
    for key, fname, meta, label in parts():
        src = os.path.join(OUT, f"{key}.mp4")
        js = os.path.join(OUT, f"{key}.json")
        if not (os.path.exists(src) and os.path.exists(js)):
            print("missing", key); return 1
        subprocess.run(["cp", src, os.path.join(DEST, fname)], check=True)
        d = json.load(open(js))
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
        title = f"{meta['chip'].split()[0]} {label} {meta['title']}".replace("  ", " ").strip() if label else f"{meta['chip'].split()[0]} {meta['title']}"
        meta_lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(t * 1000)}", f"END={int((t + dur) * 1000)}", f"title={title}"]
        lst.append(f"file '{src}'")
        rows.append((fname, title, dur, os.path.getsize(src) / 1e6, [s for s, _ in d["scenes"]]))
        t += dur
    total = t
    open(os.path.join(OUT, "chapters.txt"), "w").write("\n".join(meta_lines) + "\n")
    open(os.path.join(OUT, "concat.txt"), "w").write("\n".join(lst) + "\n")
    full = os.path.join(DEST, FULL)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "concat.txt"), "-i", os.path.join(OUT, "chapters.txt"),
                    "-map_metadata", "1", "-map_chapters", "1", "-c", "copy", "-movflags", "+faststart", full], check=True)
    fsize = os.path.getsize(full) / 1e6
    # README
    md = ["# 数学I「式の計算」「実数」 動画教材", "",
          "教科書 数研出版 ISBN978-4-410-80331-4 の p.19〜p.37（第1章 数と式／第1節 式の計算の後半・第2節 実数）を、",
          "ナレーション・効果音・BGM付きで解説した動画教材です。全体で約 %s（%d本）。" % (fmt(total), len(rows)), "",
          f"- 通しで見る：`{FULL}`（{fsize:.0f} MB、各パートの開始位置にチャプター付き）",
          "- 分割版：下表の `NN?_*.mp4`（1本 7〜13分）", "",
          "| ファイル | 内容 | 長さ | サイズ |", "|---|---|---|---|"]
    for fname, title, dur, mb, scs in rows:
        md.append(f"| `{fname}` | {title} | {fmt(dur)} | {mb:.0f} MB |")
    md += ["", "## 各パートで扱う内容", ""]
    for fname, title, dur, mb, scs in rows:
        md.append(f"### {title}（{fmt(dur)}）")
        md.append("、".join(s.replace("$", "") for s in scs))
        md.append("")
    md += ["## 作り方（再生成）", "", "`mathvideo/` 内のPythonスクリプトで生成しています。", "",
           "- `content/chNN.py` … 台本（画面の構成・ナレーション・効果音の指定）。数式はLaTeX（KaTeXで描画）", "- `verify.py` … 台本中の数式を sympy で機械検証（途中式の同値・たすき掛けの計算・循環小数の分数化など）",
           "- `build.py` … 画面描画（Chromium）→ 音声合成（edge-tts）→ 効果音・BGM合成 → ffmpegでmp4化", "- `sfx.py` / `bgm.py` … 効果音とBGMをコードで合成（外部素材なし）", "- `assemble.py` … 通し動画とこのREADMEの作成", ""]
    open(os.path.join(DEST, "README.md"), "w").write("\n".join(md))
    print(f"parts={len(rows)} total={fmt(total)} full={fsize:.0f}MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
