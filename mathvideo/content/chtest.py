from dsl import *

META = dict(chip="第1章 数と式", title="テスト", color="#2563eb", bgm=["calm"])


def build():
    S = []
    s = Scene("たすき掛けのテスト", "例題4(1)")
    s.beat("テストです。次の式を因数分解してみましょう。", Prob("例題4", "(1) $4x^2+8x-21$", "(2) $4x^2-9xy+2y^2$", cols=1), voice="K")
    tk = Tasuki.ints(2, 2, -3, 7, target=8)
    box = Box("point", T("たすき掛けでは、左の係数の積が[[o:最高次の係数]]、右の数の積が[[b:定数項]]になります。"))
    w = Work()
    s.beat("まず、四エックスの二乗は、二かける二に分けます。", tk.part("left"))
    s.beat("定数項のマイナス二十一は、マイナス三と七に分けます。", tk.part("right"))
    s.beat("斜めに掛けて、足します。", tk.part("cross"), tk.part("prod"))
    s.beat("八になりました。これが真ん中の項と一致します。", tk.part("total"))
    s.beat("よって、", w.row("4x^2+8x-21"))
    s.beat("このように因数分解できます。", w.row("(2x-3)(2x+7)", ans=True, note="←検算は展開して確認"))
    s.beat("ポイントです。", box)
    s.beat("では、少し考えてみましょう。", think=5)
    s.beat("答えは、エックスたす一、かける、二エックスたす一です。", Eq(r"(x+1)(2x+1)"))
    S.append(s)
    return S
