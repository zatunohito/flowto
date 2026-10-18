# mathvideo

数学I「式の計算」「実数」の動画教材（`output/`）を生成するスクリプト群。
再生成の手順:

```
pip install edge-tts playwright sympy pillow numpy "antlr4-python3-runtime==4.11.1"
npm i katex@0.16.11 @fontsource/noto-sans-jp@5.1.0   # MV_WORK で指定した作業ディレクトリに
python3 -m http.server 8765 --directory $MV_WORK &
python3 verify.py            # 台本中の数式を機械検証
python3 build.py ch01        # 章ごとにmp4生成（MV_OUT に出力）
python3 assemble.py          # output/ と通し動画を作成
```
動画の一覧・内容は `output/README.md`。
