"""Vector redraws of Figures 1 to 5 of FIPS 197 (the state array, SubBytes, ShiftRows, MixColumns
and AddRoundKey), after the figures of the 2023 update, without their drop shadows."""
from svg import box, arr, txt, svg

def sym(x, y, base, sub, fs=13, prime=False, anchor="middle"):
    """An italic symbol with a subscript, such as s_{0,1} or s'_{r,c}."""
    p = "′" if prime else ""
    return (f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" font-style="italic">{base}{p}'
            f'<tspan font-size="{fs*0.72:.1f}" dy="{fs*0.28:.1f}">{sub}</tspan></text>')

def cell(x, y, w, h, base, sub, prime=False, cls="b", fs=13):
    return box(x, y, w, h, cls=cls) + sym(x + w / 2, y + h / 2 + fs * 0.25, base, sub, fs, prime)

def grid(x, y, prime=False, w=34, h=24, skip=None, content=None):
    """The 4x4 state; content(r, c) gives the subscript, skip leaves a column out."""
    s = ""
    for r in range(4):
        for c in range(4):
            if c == skip:
                continue
            sub = content(r, c) if content else f"{r},{c}"
            s += cell(x + c * w, y + r * h, w, h, "s", sub, prime)
    return s

def curve(x1, y1, cx, cy, x2, y2):
    return f'<path class="a" fill="none" d="M{x1},{y1} Q{cx},{cy} {x2},{y2}" marker-end="url(#ah)"/>'

def fig1():
    s = ""
    heads = [("input bytes", "in"), ("state array", "s"), ("output bytes", "out")]
    X = [4, 164, 324]; W, H = 30, 21
    for k, (head, base) in enumerate(heads):
        x0 = X[k]
        s += txt(x0 + 2 * W, 14, head, 12.5, cls="it")
        s += f'<line class="l" x1="{x0}" y1="21" x2="{x0 + 4 * W}" y2="21"/>'
        s += f'<line class="l" x1="{x0}" y1="{25 + 4 * H + 2}" x2="{x0 + 4 * W}" y2="{25 + 4 * H + 2}"/>'
        for c in range(4):
            if c % 2:
                s += f'<rect x="{x0 + c * W}" y="25" width="{W}" height="{4 * H}" style="fill:var(--box)"/>'
            for r in range(4):
                sub = f"{r},{c}" if base == "s" else f"{r + 4 * c}"
                s += sym(x0 + c * W + W / 2, 25 + r * H + H * 0.72, base, sub, 12)
        if k < 2:
            s += arr(x0 + 4 * W + 6, 25 + 2 * H, X[k + 1] - 8, 25 + 2 * H)
    return svg(448, 116, s)

def fig2():
    s = grid(8, 30) + grid(312, 30, prime=True)
    s += cell(48, 48, 44, 32, "s", "r,c", cls="ba") + cell(352, 48, 44, 32, "s", "r,c", prime=True, cls="ba")
    s += box(212, 4, 80, 36, "S-Box", fs=14, cls="bo")
    s += curve(92, 60, 150, 20, 210, 22) + curve(294, 22, 350, 20, 372, 46)
    return svg(456, 132, s)

def fig3():
    s = box(208, 4, 104, 28, "<tspan font-family=\"JetBrains Mono\">ShiftRows()</tspan>", fs=11, cls="bo")
    for c in range(4):
        s += cell(40 + c * 38, 40, 38, 24, "s", f"r,{c}")
        s += cell(328 + c * 38, 40, 38, 24, "s", f"r,{c}", prime=True)
    s += curve(170, 40, 190, 18, 206, 18) + curve(314, 18, 335, 18, 350, 38)
    s += sym(108, 92, "s", "", 12) + sym(412, 92, "s", "", 12, prime=True)
    s += grid(40, 100, w=34, h=24)
    s += grid(344, 100, w=34, h=24, content=lambda r, c: f"{r},{(c + r) % 4}")
    for r in range(1, 4):
        y = 100 + r * 24 + 7
        for k in range(4):
            cls = "ba" if k < r else "bo"
            s += f'<rect class="{cls}" x="{226 + k * 12}" y="{y}" width="12" height="10"/>'
        s += (f'<path class="a" fill="none" d="M{286},{y + 5} L{276},{y + 5} M{286},{y + 5} L{290},{y + 5} '
              f'L{290},{y + 14} L{222},{y + 14} L{222},{y + 5} L{224},{y + 5}"/>')
        s += f'<path class="mk" d="M{276},{y + 5} l6,-3 v6 z"/>'
    return svg(520, 202, s)

def column(x, y, prime, c="c", w=40, h=30):
    return "".join(cell(x, y + r * h, w, h, "s", f"{r},{c}", prime, cls="ba") for r in range(4))

def fig4():
    s = grid(8, 44, w=34, h=26) + column(46, 26, False)
    s += grid(290, 44, prime=True, w=34, h=26) + column(328, 26, True)
    s += box(186, 2, 100, 26, "<tspan font-family=\"JetBrains Mono\">MixColumns()</tspan>", fs=10.5, cls="bo")
    s += curve(88, 40, 130, 14, 184, 15) + curve(288, 15, 318, 14, 326, 36)
    return svg(432, 156, s)

def fig5():
    s = grid(8, 50, w=34, h=26) + column(46, 32, False)
    s += '<text x="172" y="112" font-size="20" text-anchor="middle" style="font-family:KaTeX_Main">⊕</text>'
    ws = [("w", "l"), ("w", "l+c"), ("w", "l+2"), ("w", "l+3")]
    xs = [192, 222, 272, 302]
    for k, (b, sub) in enumerate(ws):
        if k == 1:
            continue
        s += box(xs[k], 50, 30 if k != 0 else 30, 104, cls="b") + sym(xs[k] + 15, 106, b, sub, 12)
    s += box(222, 30, 50, 144, cls="ba") + sym(247, 106, "w", "l+c", 13)
    s += f'<text x="296" y="20" font-size="13" text-anchor="start" font-style="italic">l = 4 <tspan style="font-family:KaTeX_Main;font-style:normal">∗</tspan> round</text>'
    s += grid(362, 50, prime=True, w=34, h=26) + column(400, 32, True)
    s += curve(86, 80, 150, 50, 222, 70) + curve(272, 70, 340, 50, 398, 60)
    return svg(504, 182, s)

FIGS = {"state": fig1, "subbytes": fig2, "shiftrows": fig3, "mixcolumns": fig4, "addroundkey": fig5}
