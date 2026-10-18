"""Reusable scene builders / diagram helpers."""
from dsl import *


def opening(num, title, sub, goals, say_intro, say_goals, color=None):
    """Chapter opening scene. goals: list[str]; say_goals: list[str] (same length)."""
    s = Scene("この動画で学ぶこと", sub, kind="title")
    s.beat(say_intro, Raw(f'<div class="titlecard"><div class="tnum">{esc(num)}</div>'
                          f'<div class="tbig">{inline(title)}</div><div class="tsub">{inline(sub)}</div></div>'),
           sfx="sparkle", pre=0.9)
    for i, (g, sg) in enumerate(zip(goals, say_goals), start=1):
        s.beat(sg, Raw(f'<div class="goal"><i>{i}</i><div>{inline(g)}</div></div>'), sfx="ding")
    return s


def summary(title, points, say_intro, says, closing=None, sub="ここまでのまとめ"):
    s = Scene(title, sub, kind="title")
    st = Steps()
    s.beat(say_intro, T("ここだけは押さえよう！", "big"), sfx="sparkle")
    for p, sy in zip(points, says):
        s.beat(sy, st.item(p), sfx="ding")
    if closing:
        s.beat(closing, sfx="pop", dur=1.0)
    return s


def rows(s, w, items):
    """items: (say, tex[, kwargs]) -> one beat per row."""
    out = []
    for it in items:
        say, tex = it[0], it[1]
        kw = it[2] if len(it) > 2 else {}
        out.append(s.beat(say, w.row(tex, **kw)))
    return out


def think(s, sec, say="手を止めて、自分で解いてみましょう。"):
    s.beat(say, think=sec, sfx="ding", gap=0.4)


# ----------------------------------------------------------------- diagrams
def arrow_svg(w, color, left=False, label=""):
    """horizontal arrow w px wide."""
    h = 28
    if left:
        d = f'<line x1="{w-4}" y1="{h/2}" x2="12" y2="{h/2}" stroke="{color}" stroke-width="6" stroke-linecap="round"/>' \
            f'<polyline points="30,2 6,{h/2} 30,{h-2}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
    else:
        d = f'<line x1="4" y1="{h/2}" x2="{w-12}" y2="{h/2}" stroke="{color}" stroke-width="6" stroke-linecap="round"/>' \
            f'<polyline points="{w-30},2 {w-6},{h/2} {w-30},{h-2}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{d}</svg>'


def LR(left_tex, right_tex, top="展開", bottom="因数分解", w=1500, fs=62):
    """left expr  ⇄  right expr diagram. returns (canvas, part_top_arrow, part_bottom_arrow)."""
    cv = Canvas(w, 190)
    lw = 520
    cv.base = (A(0, 62, f"${left_tex}$", w=lw, extra=f"text-align:center;font-size:{fs}px")
               + A(w - lw, 62, f"${right_tex}$", w=lw, extra=f"text-align:center;font-size:{fs}px"))
    mid = w - 2 * lw - 80
    top_ = cv.part(A(lw + 40, 8, f'<div style="text-align:center;color:var(--blue);font-size:38px;font-weight:900">{top}</div>'
                     + arrow_svg(mid, "#2563eb"), w=mid))
    bot_ = cv.part(A(lw + 40, 100, arrow_svg(mid, "#ea580c", left=True)
                     + f'<div style="text-align:center;color:var(--orange);font-size:38px;font-weight:900">{bottom}</div>', w=mid))
    return cv, top_, bot_


def numline(lo, hi, w=1500, labels=None, ticks=None, h=170, y=100, step=1, scale=None):
    """number-line helper. returns object with x(v) mapping and base html + part factories (html strings)."""
    return NL(lo, hi, w, h, y, step, labels)


class NL:
    def __init__(self, lo, hi, w=1500, h=170, y=100, step=1, labels=None):
        self.lo, self.hi, self.w, self.h, self.y, self.step = lo, hi, w, h, y, step
        self.pad = 60
        self.labels = labels  # dict value->tex label override

    def x(self, v):
        return self.pad + (v - self.lo) / (self.hi - self.lo) * (self.w - 2 * self.pad)

    def base(self):
        y = self.y
        parts = [f'<svg class="abs" style="left:0;top:0" width="{self.w}" height="{self.h}">'
                 f'<line x1="10" y1="{y}" x2="{self.w - 14}" y2="{y}" stroke="#1f2a44" stroke-width="5"/>'
                 f'<polyline points="{self.w - 34},{y - 14} {self.w - 10},{y} {self.w - 34},{y + 14}" fill="none" stroke="#1f2a44" stroke-width="5"/>']
        v = self.lo
        import math
        k = math.ceil(self.lo / self.step) * self.step
        txt = ""
        while k <= self.hi + 1e-9:
            xx = self.x(k)
            parts.append(f'<line x1="{xx}" y1="{y - 12}" x2="{xx}" y2="{y + 12}" stroke="#1f2a44" stroke-width="4"/>')
            lab = self.labels.get(k) if self.labels and k in self.labels else (str(int(k)) if float(k).is_integer() else str(k))
            txt += A(xx - 40, y + 20, f"${lab}$", w=80, extra="text-align:center;font-size:40px")
            k += self.step
        parts.append("</svg>")
        return "".join(parts) + txt

    def dot(self, v, label, color="#ea580c", above=True, r=13, lw=140, fs=46, dy=0):
        xx, y = self.x(v), self.y
        s = f'<svg class="abs" style="left:0;top:0" width="{self.w}" height="{self.h}"><circle cx="{xx}" cy="{y}" r="{r}" fill="{color}"/></svg>'
        if label:
            ty = (y - 88 + dy) if above else (y + 62 + dy)
            s += A(xx - lw / 2, ty, f"${label}$", w=lw, extra=f"text-align:center;font-size:{fs}px;color:{color};font-weight:900")
        return s

    def seg(self, v1, v2, color="#2563eb", label="", up=46, fs=42):
        x1, x2, y = self.x(v1), self.x(v2), self.y
        yy = y - up
        s = (f'<svg class="abs" style="left:0;top:0" width="{self.w}" height="{self.h}">'
             f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="12" stroke-linecap="round" opacity=".9"/>'
             f'<path d="M{x1} {yy + 14} v-10 h{x2 - x1} v10" fill="none" stroke="{color}" stroke-width="4"/></svg>')
        if label:
            s += A(min(x1, x2), yy - 54, f"${label}$", w=abs(x2 - x1), extra=f"text-align:center;font-size:{fs}px;color:{color};font-weight:900")
        return s


def mini(text, color="blue"):
    return f'<span class="c-{color[0] if color not in ("blue","orange","red","green","purple") else {"blue":"b","orange":"o","red":"r","green":"g","purple":"p"}[color]}">{text}</span>'


def frow(label, tex, ex="", lab_color="var(--blue)"):
    """one line of a formula list: [label] formula   example"""
    exh = f'<div style="margin-left:auto;font-size:38px;color:var(--ink2);text-align:right">{inline(ex)}</div>' if ex else ""
    return Raw(f'<div style="display:flex;gap:26px;align-items:center;min-height:84px">'
               f'<div style="flex:none;min-width:200px;text-align:center;background:{lab_color};color:#fff;font-weight:900;font-size:32px;padding:6px 14px;border-radius:12px">{esc(label)}</div>'
               f'<div style="font-size:52px">${tex}$</div>{exh}</div>')


def trio(items, size=44, cols=3):
    """helper: list of (head_text, Tasuki, result_tex) -> Row of Col(head, tk, eq). returns (row, [(tk, eq)])"""
    cs, refs = [], []
    for head, tk, res in items:
        tk.size = size
        eq = Eq(res, size=size + 6) if res else None
        cs.append(Col(*([T(head, "sm"), tk] + ([eq] if eq else [])), gap=6))
        refs.append((tk, eq))
    return Row(*cs, gap=30), refs


def practice(label, lines, cols=None, sec=60, say_read="", say_think="", title=None, sub="次の式を因数分解せよ", size=None):
    """practice scene: big problem card (read by Keita) + countdown think time."""
    s = Scene(title or label, sub)
    n = len(lines) if not cols else -(-len(lines) // cols)
    sz = size or {1: 90, 2: 84, 3: 76, 4: 68}.get(n, 62)
    if size and cols and cols >= 3:
        sz = max(size, 78)   # many short items in one row: make them big
    top = {1: 220, 2: 200, 3: 160, 4: 120}.get(n, 90)
    s.beat(say_read, Spacer(top), Prob(label, *lines, cols=cols, size=sz), voice="K")
    s.beat(say_think, think=sec, sfx="ding", gap=0.3)
    return s


# ----------------------------------------------------------------- isometric-ish boxes
def _shade(hexcol, f):
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (min(255, int(c * f)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def box3d(x, y, w, h, d, col, W=1700, H=420, k=0.5):
    """oblique-projected box. (x,y)=top-left of the front face. returns svg html."""
    dx, dy = d * k, -d * k
    front = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{col}" stroke="#1f2a44" stroke-width="3"/>'
    top = (f'<polygon points="{x},{y} {x + w},{y} {x + w + dx},{y + dy} {x + dx},{y + dy}" fill="{_shade(col, 1.25)}" stroke="#1f2a44" stroke-width="3"/>')
    right = (f'<polygon points="{x + w},{y} {x + w + dx},{y + dy} {x + w + dx},{y + h + dy} {x + w},{y + h}" fill="{_shade(col, 0.78)}" stroke="#1f2a44" stroke-width="3"/>')
    return f'<svg class="abs" style="left:0;top:0" width="{W}" height="{H}">{front}{top}{right}</svg>'


# ----------------------------------------------------------------- long division diagram
def longdiv(m, n, nsteps, cw=58, rh=52, fs=44):
    """Long division m ÷ n (m single digit) for nsteps quotient digits. returns (Canvas, [part per step], remainders)."""
    digs, rems, subs, brought = [], [], [], []
    r = m
    q0 = r // n
    digs.append(q0)
    r = r - q0 * n
    subs.append(q0 * n)
    rems.append(r)
    brought.append(r * 10)
    for _ in range(nsteps - 1):
        cur = r * 10
        q = cur // n
        digs.append(q)
        r = cur - q * n
        subs.append(q * n)
        rems.append(r)
        brought.append(r * 10)
    x0 = 130
    ytop = 70

    def num(txt, endcol, row, color="var(--ink)", extra=""):
        right = x0 + (endcol + 1) * cw
        w = cw * len(txt)
        return A(right - w, ytop + row * rh, txt, w=w, extra=f"font-family:'DejaVu Sans Mono','Noto Sans JP',monospace;font-size:{fs}px;letter-spacing:0;text-align:right;color:{color};{extra}", cls="")

    def hline(startcol, endcol, row):
        return A(x0 + startcol * cw, ytop + row * rh - 4, "", w=(endcol - startcol + 1) * cw, extra="border-top:3px solid var(--ink);height:0")

    base = (A(30, ytop - 10, f"${n}$", w=90, extra=f"font-size:{fs + 6}px;text-align:right")
            + A(x0 - 12, ytop - 6, "", w=cw * (nsteps + 1) + 20, extra=f"border-top:4px solid var(--ink);border-left:4px solid var(--ink);height:{rh}px;border-top-left-radius:18px")
            + num(str(m), 0, 0))
    cv = Canvas(x0 + cw * (nsteps + 2) + 10, ytop + rh * (2 * nsteps + 1) + 10, base=base, center=False)
    parts = []
    for i in range(nsteps):
        h = ""
        # quotient digit (+ decimal point after first)
        qx = x0 + i * cw
        h += A(qx, ytop - rh - 8, str(digs[i]), w=cw, extra=f"font-family:'DejaVu Sans Mono',monospace;font-size:{fs}px;text-align:center;color:#2563eb;font-weight:900")
        if i == 0:
            h += A(x0 + cw - 18, ytop - rh - 8, ".", w=20, extra=f"font-size:{fs}px;font-weight:900;color:#2563eb")
        row = 1 + 2 * i
        s_txt = str(subs[i])
        h += num(s_txt, i, row)
        h += hline(max(0, i - len(s_txt) + 1), i, row + 1)
        rem_txt = str(rems[i])
        bt = str(brought[i]) if i < nsteps - 1 or True else rem_txt
        # remainder shown with the next 0 brought down; remainder in orange
        h += num(bt[:-1], i, row + 1, color="#ea580c", extra="font-weight:900") if False else ""
        right = x0 + (i + 2) * cw if i + 1 < nsteps + 1 else x0 + (i + 1) * cw
        txt_r = f'<span style="color:#ea580c;font-weight:900">{rem_txt}</span>'
        if i + 1 < nsteps:
            txt_r += "0"
        endcol = i + 1 if i + 1 < nsteps else i
        wtxt = cw * (len(rem_txt) + (1 if i + 1 < nsteps else 0))
        h += A(x0 + (endcol + 1) * cw - wtxt, ytop + (row + 1) * rh, txt_r, w=wtxt,
               extra=f"font-family:'DejaVu Sans Mono','Noto Sans JP',monospace;font-size:{fs}px;text-align:right")
        parts.append(cv.part(h))
    return cv, parts, digs, rems


# ----------------------------------------------------------------- generic helpers for diagrams
def nbox(x, y, w, h, text, color="#2563eb", fs=40, bg="#fff"):
    """rounded labelled box (absolute html)"""
    return A(x, y, inline(text), w=w, extra=f"height:{h}px;display:flex;align-items:center;justify-content:center;border:4px solid {color};"
             f"border-radius:16px;background:{bg};font-size:{fs}px;font-weight:900;color:{color};text-align:center;line-height:1.2")


def elbow(x1, y1, x2, y2, color="#4b587a", W=1700, H=800):
    xm = (x1 + x2) / 2
    return (f'<svg class="abs" style="left:0;top:0" width="{W}" height="{H}"><path d="M{x1} {y1} H{xm} V{y2} H{x2}" '
            f'fill="none" stroke="{color}" stroke-width="4"/></svg>')


def table_cv(header, rowhead, cells, cw=230, rh=92, hw=300, fs=48):
    """table: header=[col labels], rowhead=[row labels], cells[r][c] = text. returns (canvas, base_part, [row_part])"""
    W = hw + cw * len(header) + 10
    H = rh * (len(rowhead) + 1) + 10
    cv = Canvas(W, H)
    base = ""
    for c, t in enumerate(header):
        base += A(hw + c * cw, 0, t, w=cw, extra=f"height:{rh}px;display:flex;align-items:center;justify-content:center;border:3px solid #4b587a;background:#e8eefc;font-size:{fs - 4}px;font-weight:900")
    base += A(0, 0, "数の範囲", w=hw, extra=f"height:{rh}px;display:flex;align-items:center;justify-content:center;border:3px solid #4b587a;background:#e8eefc;font-size:{fs - 4}px;font-weight:900")
    cv.base = base
    parts = []
    for r, rt in enumerate(rowhead):
        h = A(0, (r + 1) * rh, rt, w=hw, extra=f"height:{rh}px;display:flex;align-items:center;justify-content:center;border:3px solid #4b587a;background:#f3f6ff;font-size:{fs - 4}px;font-weight:900")
        for c, t in enumerate(cells[r]):
            col = "#15803d" if t == "○" else ("#dc2626" if t == "×" else "#1f2a44")
            h += A(hw + c * cw, (r + 1) * rh, t, w=cw, extra=f"height:{rh}px;display:flex;align-items:center;justify-content:center;border:3px solid #4b587a;background:#fff;font-size:{fs + 14}px;font-weight:900;color:{col}")
        parts.append(cv.part(h))
    return cv, parts
