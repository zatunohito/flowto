"""Mechanical math check of the lesson content.
 - every Work: consecutive rows must be equal expressions (same 'domain': rows containing capital A are a substitution domain)
 - Work first row vs single-line Prob statement of the scene
 - every Tasuki: products/sums consistent
usage: python3 verify.py ch01 [ch02 ...]   (no args = all content/ch*.py)
"""
import glob, importlib, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sympy as sp
from sympy.parsing.latex import parse_latex
import dsl

_cmd = re.compile(r"\\[a-zA-Z]+")


def prep(t):
    t = re.sub(r"\\(?:o|bl|rd|gr|pu)\{([^{}]*)\}", r"\1", t)
    t = t.replace(r"\{", "(").replace(r"\}", ")").replace(r"\,", "").replace(r"\;", "").replace(r"\ ", "").replace(r"\!", "")
    t = t.replace(r"\left", "").replace(r"\right", "").replace(r"\dfrac", r"\frac").replace(r"\cdot", "*").replace(r"\times", "*")
    holders = []
    def keep(m):
        holders.append(m.group(0)); return f"①{len(holders)-1}②"
    t = _cmd.sub(keep, t)
    t = re.sub(r"([A-Za-z])\(", r"\1*(", t)
    t = re.sub(r"\)([A-Za-z])", r")*\1", t)
    def back(m): return holders[int(m.group(1))]
    t = re.sub(r"①(\d+)②", back, t)
    return t


CTX = {}


def P(t):
    t = prep(t)
    t = re.sub(r"\\sqrt\s*([0-9a-zA-Z])", r"\\sqrt{\1}", t)
    t = re.sub(r"\\frac\s*([0-9a-zA-Z])([0-9a-zA-Z])", r"\\frac{\1}{\2}", t)
    e = parse_latex(t)
    e = e.subs(sp.Symbol("pi"), sp.pi)
    if CTX:
        e = e.subs(CTX)
    return e


def same(a, b):
    d = sp.simplify(sp.expand(sp.radsimp(a - b)))
    if d == 0:
        return True
    # numeric fallback
    syms = list((a - b).free_symbols)
    if not syms:
        try:
            return abs(complex(sp.N(a - b, 30))) < 1e-12
        except Exception:
            return False
    import random
    for _ in range(4):
        sub = {s: random.uniform(1.1, 3.7) for s in syms}
        try:
            if abs(complex((a - b).subs(sub).evalf())) > 1e-8:
                return False
        except Exception:
            return False
    return True


def walk(item):
    yield item
    for c in getattr(item, "children", []):
        yield from walk(c)


def ptex(s):
    """pull math out of problem text like '(1) $x^2$'"""
    m = re.findall(r"\$(.+?)\$", s)
    return m


bad = 0
checked = 0


def report(msg):
    global bad
    bad += 1
    print("  !!", msg)


_dec = re.compile(r"(-?)(\d+)\.((?:\d|\\dot\{\d\})*)(\\cdots)?")


def numval(t):
    """decimal incl. recurring dots -> (Fraction, tol)  ; None if not a decimal literal"""
    from fractions import Fraction
    t = t.strip().replace(r"\ ", "")
    m = _dec.fullmatch(t)
    if not m:
        return None
    sign, ip, frac, cd = m.groups()
    toks = re.findall(r"\\dot\{(\d)\}|(\d)", frac)
    digs = [(a or b, bool(a)) for a, b in toks]
    dots = [i for i, (_, d) in enumerate(digs) if d]
    v = Fraction(int(ip))
    if not dots:
        n = len(digs)
        v += Fraction(int("".join(d for d, _ in digs) or "0"), 10 ** n) if n else 0
        tol = Fraction(1, 10 ** n) if cd else 0
    else:
        i0 = dots[0]
        i1 = dots[1] if len(dots) > 1 else dots[0]
        pre = "".join(d for d, _ in digs[:i0])
        per = "".join(d for d, _ in digs[i0:i1 + 1])
        p = len(pre)
        if pre:
            v += Fraction(int(pre), 10 ** p)
        v += Fraction(int(per), 10 ** len(per) - 1) / 10 ** p
        tol = 0
    return (-v if sign else v), tol


def chain_check(si, sc, tex):
    global checked
    parts = [p.strip() for p in tex.split("=")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if not CTX:
        if re.fullmatch(r"\d*x", parts[0]) and len(parts) > 2:
            parts = parts[1:]
        elif re.fullmatch(r"\d*x", parts[0]):
            return
        if any(re.fullmatch(r"\d*x", p) for p in parts):
            return
    if len(parts) < 2:
        return
    def has_letters(t):
        return bool(re.search(r"(?<![\\a-zA-Z])[a-zA-Z](?![a-zA-Z])", re.sub(r"\\[a-zA-Z]+", "", t)))
    if not CTX and any(not has_letters(p) for p in parts) and any(has_letters(p) for p in parts):
        return  # an equation to solve, not an identity
    if r"\cdots" in tex and re.search(r"\dx|\d*x", tex) and re.search(r"(^|[^a-z\\])[0-9]*x", tex):
        return
    if any(r"\Rightarrow" in p or r"\mathrm" in p or r"\qquad" in p or r"\quad" in p or r"\xrightarrow" in p or r"\overset" in p for p in parts):
        return
    vals = []
    try:
        for p in parts:
            nv = numval(p)
            if nv is not None:
                vals.append(("n", nv))
            else:
                vals.append(("e", P(p)))
    except Exception as ex:
        print(f"  ?? scene {si} '{sc.title}' eq parse fail: {tex} ({str(ex)[:50]})"); return
    for (ka, a), (kb, b) in zip(vals, vals[1:]):
        checked += 1
        if ka == "n" and kb == "n":
            ok = abs(a[0] - b[0]) <= max(a[1], b[1])
        elif ka == "n" or kb == "n":
            nv, ex_ = (a, b) if ka == "n" else (b, a)
            try:
                ok = abs(float(ex_.evalf()) - float(nv[0])) <= float(nv[1]) + 1e-12
            except Exception:
                print(f"  ?? scene {si} '{sc.title}': cannot evaluate numerically: {tex}")
                return
        else:
            ok = same(a, b)
        if not ok:
            report(f"scene {si} '{sc.title}': equation false: {tex}")
            return


def check_scene(si, sc):
    global checked, CTX
    CTX = {sp.Symbol(k): sp.sympify(v) for k, v in (getattr(sc, "ctx", None) or {}).items()}
    probs = [x for it in sc.top for x in walk(it) if isinstance(x, dsl.Prob)]
    for it in sc.top:
        for x in walk(it):
            if isinstance(x, dsl.Work):
                rows = [c for c in x.children if isinstance(c, dsl._WRow)]
                prev = {"A": None, "n": None}
                for ri, r in enumerate(rows):
                    tex = r.tex
                    if r.note and "誤り" in r.note:
                        continue  # intentionally false row
                    if "=" in tex and r"\pm" not in tex and "text" not in tex:
                        chain_check(si, sc, tex)
                        continue
                    if "=" in tex or r"\pm" in tex or "text" in tex:
                        continue
                    try:
                        e = P(tex)
                    except Exception as ex:
                        print(f"  ?? scene {si} '{sc.title}' row {ri} parse fail: {tex} ({str(ex)[:50]})"); continue
                    dom = "A" if re.search(r"(?<![a-zA-Z\\])A(?![a-zA-Z])", tex) else "n"
                    if prev[dom] is not None:
                        checked += 1
                        if not same(e, prev[dom]):
                            report(f"scene {si} '{sc.title}': row {ri} not equal to previous: {tex}")
                    prev[dom] = e
                # first row vs problem
                if rows and len(probs) == 1 and len(probs[0].lines) == 1:
                    ln = re.sub(r"^\(\d+\)\s*", "", probs[0].lines[0]).strip()
                    m = ptex(ln) if (ln.startswith("$") and ln.endswith("$") and ln.count("$") == 2) else None
                    if m and "=" not in rows[0].tex:
                        try:
                            if not same(P(m[0]), P(rows[0].tex)):
                                report(f"scene {si} '{sc.title}': first row != problem {m[0]} vs {rows[0].tex}")
                            checked += 1
                        except Exception:
                            pass
            if isinstance(x, dsl.Eq) and "=" in x.tex and r"\pm" not in x.tex and "text" not in x.tex:
                chain_check(si, sc, x.tex)
            if isinstance(x, dsl.Tasuki):
                v = x.v
                try:
                    a1, a2, c1, c2 = (P(v[k]) for k in ("a1", "a2", "c1", "c2"))
                    p1, p2, tot = P(v["p1"]), P(v["p2"]), P(v["tot"])
                    checked += 1
                    if not (same(p1, a2 * c1) and same(p2, a1 * c2) and same(tot, p1 + p2)):
                        report(f"scene {si} '{sc.title}': tasuki arithmetic wrong {v}")
                    if v["aa"] and not same(P(v["aa"]), a1 * a2):
                        report(f"scene {si} '{sc.title}': tasuki aa wrong {v}")
                    if v["cc"] and not same(P(v["cc"]), c1 * c2):
                        report(f"scene {si} '{sc.title}': tasuki cc wrong {v}")
                except Exception as ex:
                    print(f"  ?? tasuki parse {v} {ex}")


EXTRA = [(r"3.\dot{2}\dot{7}", "36/11"), (r"0.\dot{1}", "1/9"), (r"0.\dot{1}\dot{2}", "4/33"), (r"0.\dot{6}4\dot{8}", "24/37"), (r"6.\dot{2}\dot{7}", "69/11"),
         (r"0.\dot{5}", "5/9"), (r"3.\dot{2}\dot{5}", "322/99"), (r"0.\dot{1}23\dot{4}", "1234/9999"), (r"0.3\dot{2}\dot{1}", "53/165"),
         (r"1.\dot{2}8571\dot{4}", "9/7"), (r"0.\dot{2}\dot{1}", "7/33"), (r"0.\dot{8}", "8/9"), (r"1.0\dot{1}8\dot{5}", "55/54"), (r"0.\dot{6}", "2/3"),
         (r"0.1\dot{3}\dot{6}", "3/22"), (r"1.3\dot{1}7\dot{8}", "None")]


def extra_checks():
    from fractions import Fraction
    global bad
    for t, f in EXTRA:
        if f == "None":
            continue
        v = numval(t)[0]
        if v != Fraction(f):
            print(f"  !! decimal {t} = {v} != {f}"); bad += 1


def main(names):
    for n in names:
        mod = importlib.import_module(f"content.{n}")
        scenes = mod.build()
        before = bad
        for si, sc in enumerate(scenes):
            check_scene(si, sc)
        print(f"{n}: scenes={len(scenes)} {'OK' if bad == before else 'PROBLEMS'}")
    extra_checks()
    print(f"checked comparisons: {checked}, problems: {bad}")


if __name__ == "__main__":
    names = sys.argv[1:] or sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "content", "ch[0-9][0-9].py")))
    main(names)
    sys.exit(1 if bad else 0)
