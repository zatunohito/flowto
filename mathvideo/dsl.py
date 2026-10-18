"""Scene DSL: items (visual blocks) + scenes made of beats (narration + reveal)."""
import html as H
import re

INF = 10 ** 9


def esc(s):
    return H.escape(s, quote=False)


def inline(s):
    """Escape text, keep $math$ for KaTeX, support [[o:..]] colours, [[h3:..]] step-highlight, **bold**."""
    s = esc(s)

    def sub(m):
        k, body = m.group(1), m.group(2)
        if k.startswith("h"):
            return f'<span class="hl" data-h="{k[1:]}">{body}</span>'
        return f'<span class="c-{k}">{body}</span>'

    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"\[\[(o|b|r|g|p|h\d+):((?:(?!\[\[).)*?)\]\]", sub, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = s.replace("\n", "<br>")
    return s


OK_SVG = ('<svg class="ok-mark" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#15803d"/>'
          '<path d="M6 12.5l4 4 8-9" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')
NG_SVG = ('<svg class="ng-mark" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="#dc2626"/>'
          '<path d="M7 7l10 10M17 7L7 17" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/></svg>')


class Item:
    """A revealable block. step=None until attached to a beat (or inherited from parent)."""

    def __init__(self):
        self.step = None
        self.parent = None
        self.is_ans = False
        self.kind_hint = None  # for default sfx

    def own_min(self):
        return self.step if self.step is not None else INF

    def _s(self, inherit):
        st = self.step if self.step is not None else inherit
        if st is None:
            raise ValueError(f"{type(self).__name__} never attached to a beat")
        return st

    def html(self, inherit=None):
        raise NotImplementedError

    def tree(self):
        yield self


class Container(Item):
    def __init__(self):
        super().__init__()
        self.children = []

    def add(self, child):
        child.parent = self
        self.children.append(child)
        return child

    def min_child(self):
        m = INF
        for c in self.children:
            m = min(m, c.min_step() if isinstance(c, Container) else c.own_min())
        return m

    def min_step(self):
        return min(self.own_min(), self.min_child())

    def my_step(self, inherit):
        s = self.step
        mc = self.min_child()
        if s is None:
            if mc < INF:
                s = mc
            elif inherit is not None:
                s = inherit
        if s is None:
            raise ValueError(f"{type(self).__name__} never attached to a beat")
        if mc < INF:
            s = min(s, mc)
        return s

    def tree(self):
        yield self
        for c in self.children:
            yield from c.tree()


# ---------------------------------------------------------------- simple blocks
class T(Item):
    """Text paragraph. cls: '', 'big', 'sm', 'c', 'l' (space separated)."""

    def __init__(self, text, cls=""):
        super().__init__()
        self.text, self.cls = text, cls

    def html(self, inherit=None):
        return f'<div class="t {self.cls}" data-s="{self._s(inherit)}">{inline(self.text)}</div>'


class Eq(Item):
    def __init__(self, tex, left=False, size=None, color=None):
        super().__init__()
        self.tex, self.left, self.size, self.color = tex, left, size, color

    def html(self, inherit=None):
        st = f"font-size:{self.size}px;" if self.size else ""
        if self.color:
            st += f"color:{self.color};"
        cl = "eq left" if self.left else "eq"
        return f'<div class="{cl}" style="{st}" data-s="{self._s(inherit)}">$${self.tex}$$</div>'


class Spacer(Item):
    def __init__(self, px=20):
        super().__init__()
        self.px = px

    def html(self, inherit=None):
        return f'<div style="height:{self.px}px" data-s="{self._s(inherit)}"></div>'


class Raw(Item):
    def __init__(self, html_, cls=""):
        super().__init__()
        self.h, self.cls = html_, cls

    def html(self, inherit=None):
        return f'<div class="{self.cls}" data-s="{self._s(inherit)}">{self.h}</div>'


PROB_KINDS = {"例題": "mo", "例": "ex", "練習": "pr", "応用例題": "ap", "問題": "mo", "問": "pr",
              "発展練習": "pr", "発展例": "ex", "深める": "ap"}


class Prob(Item):
    """Problem card: label like '例題4', '練習16', '応用例題2'."""

    def __init__(self, label, *lines, cols=None, kind=None, size=None):
        super().__init__()
        self.label, self.lines, self.cols, self.size = label, lines, cols, size
        m = re.match(r"^(\D+)(.*)$", label)
        self.head, self.num = (m.group(1), m.group(2)) if m else (label, "")
        self.kind = kind or PROB_KINDS.get(self.head, "ex")
        self.kind_hint = "card"

    def html(self, inherit=None):
        lab = f'{esc(self.head)}<small>{esc(self.num)}</small>' if self.num else esc(self.head)
        fs = f"font-size:{self.size}px;" if self.size else ""
        if self.cols:
            body = f'<div class="body cols" style="{fs}grid-template-columns:repeat({self.cols},auto);justify-content:start;column-gap:70px">'
        else:
            body = f'<div class="body" style="{fs}">'
        body += "".join(f'<span class="ln">{inline(l)}</span>' for l in self.lines) + "</div>"
        return f'<div class="prob k-{self.kind}" data-s="{self._s(inherit)}"><div class="lab">{lab}</div>{body}</div>'


class Box(Container):
    TITLES = {"point": "ポイント", "formula": "公式", "warn": "注意", "tip": "コツ", "def": "定義"}

    def __init__(self, kind, *children, title=None):
        super().__init__()
        self.kind = kind
        self.title = Box.TITLES.get(kind, "") if title is None else title
        for c in children:
            self.add(c)
        self.kind_hint = {"formula": "sparkle", "warn": "warn", "point": "ding", "def": "ding", "tip": "ding"}.get(kind)

    def html(self, inherit=None):
        s = self.my_step(inherit)
        inner = "".join(c.html(s) for c in self.children)
        t = f'<div class="bt">{esc(self.title)}</div>' if self.title else ""
        return f'<div class="box {self.kind}" data-s="{s}">{t}<div class="in">{inner}</div></div>'


class Row(Container):
    def __init__(self, *children, gap=40, flex=None, align="flex-start"):
        super().__init__()
        self.gap, self.flex, self.align = gap, flex, align
        for c in children:
            self.add(c)

    def html(self, inherit=None):
        s = self.my_step(inherit)
        cells = []
        for i, c in enumerate(self.children):
            fl = f' style="flex:{self.flex[i]} 1 0"' if self.flex else ""
            cells.append(f"<div{fl}>{c.html(s)}</div>")
        return (f'<div class="row" style="gap:{self.gap}px;align-items:{self.align}" data-s="{s}">'
                + "".join(cells) + "</div>")


class Col(Container):
    def __init__(self, *children, gap=14):
        super().__init__()
        self.gap = gap
        for c in children:
            self.add(c)

    def html(self, inherit=None):
        s = self.my_step(inherit)
        return (f'<div style="display:flex;flex-direction:column;gap:{self.gap}px" data-s="{s}">'
                + "".join(c.html(s) for c in self.children) + "</div>")


# ---------------------------------------------------------------- work (aligned rows)
class _WRow(Item):
    def __init__(self, tex, lead, note, ans, size, lead_txt):
        super().__init__()
        self.tex, self.lead, self.note, self.is_ans, self.size, self.lead_txt = tex, lead, note, ans, size, lead_txt
        self.kind_hint = "chime" if ans else "tick"

    def html(self, inherit=None):
        s = self._s(inherit)
        st = f' style="--m:{self.size}px"' if self.size else ""
        if self.lead_txt:
            lead = f'<div class="lead txt">{inline(self.lead)}</div>'
        else:
            lead = f'<div class="lead">{"$" + self.lead + "$" if self.lead else ""}</div>'
        note = f'<div class="note">{inline(self.note)}</div>' if self.note else "<div></div>"
        ans = " ans" if self.is_ans else ""
        return f'<div class="wrow{ans}" data-s="{s}"{st}>{lead}<div class="expr">$ {self.tex} $</div>{note}</div>'


class Work(Container):
    """Vertical working. Each row() is an Item to attach to a beat. First row has no leading '='."""

    def __init__(self, title=None, lw=76, size=None):
        super().__init__()
        self.title, self.lw, self.size = title, lw, size
        self.n = 0

    def row(self, tex, lead=None, note=None, ans=False, size=None, text_lead=False):
        if lead is None:
            lead = "" if self.n == 0 else "="
        self.n += 1
        return self.add(_WRow(tex, lead, note, ans, size, text_lead))

    def html(self, inherit=None):
        s = self.my_step(inherit)
        t = f'<div class="wt">{esc(self.title)}</div>' if self.title else ""
        st = f"--lw:{self.lw}px;" + (f"--m:{self.size}px;" if self.size else "")
        return (f'<div class="work" style="{st}" data-s="{s}">{t}'
                + "".join(c.html(s) for c in self.children) + "</div>")


class _StepItem(Item):
    def __init__(self, no, text):
        super().__init__()
        self.no, self.text = no, text

    def html(self, inherit=None):
        return (f'<div class="st" data-s="{self._s(inherit)}"><div class="no">{self.no}</div>'
                f'<div>{inline(self.text)}</div></div>')


class Steps(Container):
    """Numbered list; items revealed by beats."""

    def __init__(self):
        super().__init__()
        self.n = 0

    def item(self, text):
        self.n += 1
        return self.add(_StepItem(self.n, text))

    def html(self, inherit=None):
        s = self.my_step(inherit)
        return f'<div class="steps" data-s="{s}">' + "".join(c.html(s) for c in self.children) + "</div>"


# ---------------------------------------------------------------- canvas with absolutely placed parts
class _Part(Item):
    def __init__(self, h):
        super().__init__()
        self.h = h

    def html(self, inherit=None):
        return (f'<div data-s="{self._s(inherit)}" style="position:absolute;left:0;top:0;width:100%;height:100%">'
                f'{self.h}</div>')


class Canvas(Container):
    """Fixed-size relative box. base: html shown with the canvas; part(): html shown at a later beat.
    HTML inside should use A(x, y, ...) for absolute px placement."""

    def __init__(self, w, h, base="", center=True):
        super().__init__()
        self.w, self.h, self.base, self.center = w, h, base, center

    def part(self, h):
        return self.add(_Part(h))

    def html(self, inherit=None):
        s = self.my_step(inherit)
        m = "margin:0 auto;" if self.center else ""
        return (f'<div class="canvas" style="{m}width:{self.w}px;height:{self.h}px" data-s="{s}">{self.base}'
                + "".join(c.html(s) for c in self.children) + "</div>")


def A(x, y, inner, w=None, extra="", cls=""):
    """absolute-positioned html cell inside Canvas (px)."""
    ws = f"width:{w}px;" if w else ""
    if inner and "<" not in inner:
        inner = inline(inner)
    return f'<div class="abs {cls}" style="left:{x}px;top:{y}px;{ws}{extra}">{inner}</div>'


# ---------------------------------------------------------------- tasuki
def _term(n, var="", pw=1):
    """integer n times var^pw as TeX text."""
    if not var:
        return str(n)
    v = var if pw == 1 else f"{var}^{pw}"
    if n == 1:
        return v
    if n == -1:
        return "-" + v
    return f"{n}{v}"


class Tasuki(Container):
    """たすき掛け図.  rows: (a1 c1 -> p1), (a2 c2 -> p2); bottom: a1a2, c1c2, sum.
    parts: part('left'|'right'|'cross'|'prod'|'total') -> Item to attach to a beat."""

    def __init__(self, a1, a2, c1, c2, p1, p2, aa, cc, tot, cw=2.6, pw=2.8, size=None, ok=None):
        super().__init__()
        self.v = dict(a1=a1, a2=a2, c1=c1, c2=c2, p1=p1, p2=p2, aa=aa, cc=cc, tot=tot)
        self.cw, self.pw, self.size, self.ok = cw, pw, size, ok

    @classmethod
    def ints(cls, a1, a2, c1, c2, var="", target=None, **kw):
        """integers a1,a2 (left) and c1,c2 (right, optionally times `var`).
        products follow the cross: row1 = a2*c1, row2 = a1*c2."""
        p1, p2 = a2 * c1, a1 * c2
        tot = p1 + p2
        ok = None if target is None else (tot == target)
        return cls(str(a1), str(a2), _term(c1, var), _term(c2, var), _term(p1, var), _term(p2, var),
                   str(a1 * a2), _term(c1 * c2, var, 2), _term(tot, var), ok=ok, **kw)

    def part(self, kind):
        h = {"left": self._left, "right": self._right, "cross": self._cross, "prod": self._prod, "total": self._total}[kind]()
        return self.add(_Part(h))

    def _g(self):
        xa = 2.0
        xc = xa + 1.0
        xr = xc + self.cw
        xarrow = xr + 0.2
        xp = xarrow + 1.6
        return xa, xc, xr, xarrow, xp, xp + self.pw

    def _left(self):
        xa = self._g()[0]
        return "".join(f'<div class="abs" style="left:0;top:{y}em;width:{xa}em;text-align:right">${self.v[k]}$</div>'
                       for y, k in ((0.15, "a1"), (1.55, "a2")))

    def _right(self):
        xc = self._g()[1]
        return "".join(f'<div class="abs" style="left:{xc}em;top:{y}em">${self.v[k]}$</div>'
                       for y, k in ((0.15, "c1"), (1.55, "c2")))

    def _cross(self):
        g = self._g()
        xa, xc = g[0], g[1]
        x1, x2 = xa + 0.15, xc - 0.15
        y1, y2 = 0.95, 2.35
        return (f'<svg class="abs" style="left:0;top:0;width:{g[5]}em;height:4.6em;overflow:visible" '
                f'viewBox="0 0 {g[5] * 100:.0f} 460" preserveAspectRatio="none">'
                f'<line x1="{x1 * 100}" y1="{y1 * 100}" x2="{x2 * 100}" y2="{y2 * 100}" stroke="#ea580c" stroke-width="6" stroke-linecap="round"/>'
                f'<line x1="{x1 * 100}" y1="{y2 * 100}" x2="{x2 * 100}" y2="{y1 * 100}" stroke="#2563eb" stroke-width="6" stroke-linecap="round"/></svg>')

    def _prod(self):
        g = self._g()
        r = ""
        for y, k, col in ((0.15, "p1", "#2563eb"), (1.55, "p2", "#ea580c")):
            r += (f'<div class="abs" style="left:{g[3]}em;top:{y}em">$\\longrightarrow$</div>'
                  f'<div class="abs" style="left:{g[4]}em;top:{y}em;color:{col}">${self.v[k]}$</div>')
        return r

    def _total(self):
        g = self._g()
        xa, xc, xp, xe = g[0], g[1], g[4], g[5]
        col = {None: "var(--ink)", True: "var(--green)", False: "var(--red)"}[self.ok]
        icon = "" if self.ok is None else (OK_SVG if self.ok else NG_SVG)
        r = f'<div class="abs" style="left:0;top:3.05em;width:{xe}em;border-top:3px solid var(--ink)"></div>'
        if self.v["aa"]:
            r += f'<div class="abs" style="left:0;top:3.2em;width:{xa}em;text-align:right">${self.v["aa"]}$</div>'
        if self.v["cc"]:
            r += f'<div class="abs" style="left:{xc}em;top:3.2em">${self.v["cc"]}$</div>'
        r += f'<div class="abs" style="left:{xp}em;top:3.2em;color:{col};font-weight:900">${self.v["tot"]}$ {icon}</div>'
        return r

    def html(self, inherit=None):
        s = self.my_step(inherit)
        w = self._g()[5] + 0.8
        st = f"--m:{self.size}px;" if self.size else ""
        return (f'<div class="tk" style="{st}width:{w}em;height:4.8em" data-s="{s}">'
                + "".join(c.html(s) for c in self.children) + "</div>")


# ---------------------------------------------------------------- scene
class Beat:
    def __init__(self, say, items, sfx, voice, gap, think, dur, pre):
        self.say, self.items, self.sfx, self.voice = say, items, sfx, voice
        self.gap, self.think, self.dur, self.pre = gap, think, dur, pre


class Scene:
    def __init__(self, title, sub="", kind="lesson"):
        self.title, self.sub, self.kind = title, sub, kind
        self.beats = []
        self.top = []
        self.ctx = None  # verification context: {symbol: sympy-expression string}

    @property
    def n(self):
        return len(self.beats)

    def beat(self, say="", *items, sfx=None, voice="N", gap=None, think=0, dur=None, pre=None):
        n = len(self.beats) + 1
        flat = []
        for it in items:
            if isinstance(it, (list, tuple)):
                flat.extend(it)
            elif it is not None:
                flat.append(it)
        for it in flat:
            if it.step is None:
                it.step = n
            root = it
            while root.parent is not None:
                root = root.parent
            if root not in self.top:
                self.top.append(root)
        if sfx is None:
            sfx = "pop"
            for it in flat:
                for x in it.tree():
                    if x.is_ans:
                        sfx = "chime"
                    elif x.kind_hint and sfx in ("pop", "tick"):
                        sfx = x.kind_hint
        self.beats.append(Beat(say, flat, sfx, voice, gap, think, dur, pre))
        return n

    def content_html(self):
        return "\n".join(it.html(None) for it in self.top)
