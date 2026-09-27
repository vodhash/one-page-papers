"""Vector redraws of the four diagrams of 12factor.net (public/images of github.com/heroku/12factor):
codebase-deploys.png, attached-resources.png, release.png and process-types.png. Labels as in the
images; the URLs of attached-resources.png are set in the monospaced font."""
import math
from svg import box, arr, ln, txt, svg


def page(x, y, w, h, fill="b"):
    """A sheet of paper whose bottom edge is a wave, as drawn in the original images."""
    b = y + h
    return (f'<path class="{fill}" d="M{x},{y} H{x + w} V{b - 6} C{x + w * .72},{b - 16} {x + w * .45},{b + 6} '
            f'{x + w * .22},{b - 2} C{x + w * .12},{b - 5} {x + w * .05},{b - 5} {x},{b - 3} Z"/>')


def code_page(x, y, w, h, label=None):
    """The front sheet of a stack, with lines of code; the two sheets behind it stick out up right."""
    s = page(x + 16, y - 16, w, h) + page(x + 8, y - 8, w, h) + page(x, y, w, h)
    rows = [(0, .55), (0, .8), (.12, .7), (.12, .5), (0, .2), (0, .45), (0, .75), (.12, .62), (.12, .82), (0, .3)]
    top = y + (30 if label else 18)
    for i, (dx, lw) in enumerate(rows):
        yy = top + i * 7 + (6 if i > 4 else 0)
        s += f'<line class="l" x1="{x + 12 + dx * w}" y1="{yy}" x2="{x + 12 + lw * (w - 24)}" y2="{yy}" style="stroke-width:3"/>'
    if label:
        s += txt(x + w / 2, y + 17, label, 12, cls="h")
    return s


def folded(x, y, w, h, label, fs=12, extra=None):
    """A box whose top right corner is folded, like the Build and Config boxes of release.png."""
    c = 12
    s = f'<path class="b" d="M{x},{y} H{x + w - c} L{x + w},{y + c} V{y + h} H{x} Z"/>'
    s += f'<path class="l" style="fill:none" d="M{x + w - c},{y} V{y + c} H{x + w}"/>'
    if extra:
        s += txt(x + w / 2, y + h / 2 - 3, label, fs, cls="h") + txt(x + w / 2, y + h / 2 + 17, extra, 15, cls="h")
    else:
        s += txt(x + w / 2, y + h / 2 + 4, label, fs, cls="h")
    return s


def cylinder(cx, cy, w, h, label):
    """A drum, as the backing services of attached-resources.png."""
    rx, ry = w / 2, 8
    top, bot = cy - h / 2 + ry, cy + h / 2 - ry
    s = (f'<path class="b" d="M{cx - rx},{top} V{bot} A{rx},{ry} 0 0 0 {cx + rx},{bot} V{top} '
         f'A{rx},{ry} 0 0 0 {cx - rx},{top} Z"/>')
    s += f'<path class="l" style="fill:none" d="M{cx - rx},{top} A{rx},{ry} 0 0 0 {cx + rx},{top}"/>'
    lines = label.split('|')
    for i, l in enumerate(lines):
        s += txt(cx, cy + 8 + (i - (len(lines) - 1) / 2) * 14, l, 11.5, cls="h")
    return s


def along(x1, y1, x2, y2, label, off=-5, fs=8.2):
    """A label written along the arrow from (x1, y1) to (x2, y2), on its upper side."""
    a = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if a > 90 or a < -90:
        a += 180
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    nx, ny = -math.sin(math.radians(a)) * off, math.cos(math.radians(a)) * off
    return (f'<text class="m" x="{mx + nx:.1f}" y="{my + ny:.1f}" font-size="{fs}" text-anchor="middle" '
            f'transform="rotate({a:.1f} {mx + nx:.1f} {my + ny:.1f})">{label}</text>')


def codebase():
    s = txt(78, 20, "Codebase", 15, cls="h") + txt(355, 20, "Deploys", 15, cls="h")
    s += code_page(22, 52, 112, 170)
    fan = (152, 150)
    for i, name in enumerate(["production", "staging", "developer 1", "developer 2"]):
        y = 36 + i * 70
        s += box(290, y, 130, 50, name, fs=12.5)
        s += arr(fan[0], fan[1], 286, y + 25)
    return svg(440, 322, s)


def release():
    s = code_page(14, 36, 100, 140, label="Code")
    s += arr(134, 64, 180, 64)
    s += folded(188, 30, 104, 62, "Build")
    s += folded(188, 128, 104, 62, "Config", extra="{ }")
    s += box(336, 78, 94, 62, cls="b") + txt(383, 113, "Release", 12, cls="h")
    s += arr(294, 76, 332, 100) + arr(294, 150, 332, 120)
    return svg(440, 200, s)


def processes():
    s = arr(66, 372, 66, 10) + arr(66, 372, 434, 372)
    s += txt(26, 190, "Scale", 15, cls="h").replace('<text ', '<text transform="rotate(-90 26 190)" ')
    s += txt(44, 190, "(running processes)", 13, cls="h").replace('<text ', '<text transform="rotate(-90 44 190)" ')
    s += txt(250, 397, "Workload diversity", 15, cls="h") + txt(250, 415, "(process types)", 13, cls="h")
    cols = {"web": (["web.1", "web.2"], 88), "worker": (["worker.1", "worker.2", "worker.3", "worker.4"], 196),
            "clock": (["clock.1"], 304)}
    for names, x in cols.values():
        for i, n in enumerate(names):
            s += box(x, 300 - i * 64, 96, 50, n, fs=12.5, cls="ba")
    return svg(440, 424, s)


def attached():
    s = box(160, 6, 120, 60, "Production|deploy", fs=13)
    ends = {"mysql": ((160, 52), (72, 146)), "smtp": ((190, 66), (130, 228)),
            "s3": ((250, 66), (310, 228)), "twitter": ((280, 52), (368, 146))}
    s += cylinder(42, 180, 76, 60, "MySQL") + cylinder(110, 266, 104, 62, "Outbound|email service")
    s += cylinder(330, 266, 104, 62, "Amazon S3") + cylinder(398, 180, 76, 60, "Twitter")
    labels = {"mysql": "mysql://auth@host/db", "smtp": "smtp://auth@host/",
              "s3": "https://auth@s3.amazonaws.com/", "twitter": "http://auth@api.twitter.com/"}
    for k, ((x1, y1), (x2, y2)) in ends.items():
        s += arr(x1, y1, x2, y2) + along(x1, y1, x2, y2, labels[k], fs=7.8)
    s += txt(220, 250, "Attached", 19, cls="h") + txt(220, 272, "resources", 19, cls="h")
    return svg(440, 300, s)


FIGS = {"codebase": codebase, "release": release, "processes": processes, "attached": attached}
