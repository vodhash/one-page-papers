"""The fonts and styles of the site: the faces of @fontsource that its text needs, the stylesheet of
KaTeX cut to the math it shows, the colour tokens of its two modes and their contrast."""
import re
from html.parser import HTMLParser

from papers import ROOT
from .common import EXTRA_TOKENS, SURFACES, SiteError, TEXT_TOKENS, TOKENS

# family: the @fontsource package, its CSS files that declare the faces, and the characters it
# draws (None: any text of the site); a face is kept in every subset that covers one of them
FONTS = {
    "EB Garamond": ("eb-garamond", ("400", "400-italic", "500", "500-italic", "600", "600-italic"), None),
    "JetBrains Mono": ("jetbrains-mono", ("400", "700"), None),  # the hash of the footer, and the code of the texts
}
PRELOAD = ("eb-garamond-latin-400-normal.woff2", "eb-garamond-latin-500-normal.woff2")

KATEX_CSS = ROOT / "node_modules" / "katex" / "dist" / "katex.min.css"
PDFJS = ROOT / "node_modules" / "pdfjs-dist"
PDFJS_FILES = ("build/pdf.min.mjs", "build/pdf.worker.min.mjs", "LICENSE")  # into assets/pdfjs/

def katex_css(pages_html):
    """The stylesheet of KaTeX for the site, and the font files it needs: the families that the
    classes of the math of the pages use, in WOFF2 only."""
    if not KATEX_CSS.exists():
        raise SiteError(f"{KATEX_CSS.relative_to(ROOT)} is missing, run `make deps`")
    css = KATEX_CSS.read_text()
    classes = set()
    for h in pages_html:
        for attr in re.findall(r'class="([^"]*)"', h):
            classes.update(attr.split())
    used = {"KaTeX_Main"}
    for sel, decl in re.findall(r"([^{}@]+)\{([^{}]*font(?:-family)?:[^{}]*)\}", css):
        fam = re.findall(r"KaTeX_\w+", decl)
        if fam and any(all(c in classes for c in re.findall(r"\.([\w-]+)", one)) for one in sel.split(",")):
            used.update(fam)
    files = []
    def face(k):
        block = k.group(0)
        fam = re.search(r"font-family:\"?(KaTeX_\w+)", block).group(1)
        if fam not in used:
            return ""
        woff2 = re.search(r"url\((fonts/[^)]+\.woff2)\)", block).group(1)
        files.append(KATEX_CSS.parent / woff2)
        return re.sub(r"src:[^;}]+", f'src:url({woff2}) format("woff2")', block)
    css = re.sub(r"@font-face\{[^}]*\}", face, css)
    return css, files

def text_of(page_html):
    """The characters that a page draws with its fonts."""
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.chars, self.skip = set(), 0
        def handle_starttag(self, tag, attrs):
            self.skip += tag in ("script", "style", "title")
        def handle_endtag(self, tag):
            self.skip -= tag in ("script", "style", "title")
        def handle_data(self, data):
            if not self.skip:
                self.chars.update(data)
    t = Text()
    t.feed(page_html)
    return t.chars

def unicode_ranges(spec):
    out = []
    for part in spec.split(","):
        lo, _, hi = part.strip().removeprefix("U+").partition("-")
        out.append((int(lo, 16), int(hi or lo, 16)))
    return out

def font_faces(chars):
    """@font-face rules of the site and the files they use: every face of FONTS in every
    subset of @fontsource that covers a character of the site."""
    rules, files = [], []
    for family, (package, sheets, only) in FONTS.items():
        drawn = set(only) if only else chars
        base = ROOT / "node_modules" / "@fontsource" / package
        for sheet in sheets:
            path = base / f"{sheet}.css"
            if not path.exists():
                raise SiteError(f"{path.relative_to(ROOT)} is missing, run `make deps`")
            for block in re.findall(r"@font-face\s*{([^}]*)}", path.read_text()):
                style = re.search(r"font-style:\s*(\w+)", block).group(1)
                weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
                woff2 = re.search(r"url\(\./files/([^)]+\.woff2)\)", block).group(1)
                spec = re.search(r"unicode-range:\s*([^;]+);", block).group(1)
                if not any(lo <= ord(c) <= hi for lo, hi in unicode_ranges(spec) for c in drawn):
                    continue
                files.append(base / "files" / woff2)
                rules.append(f"@font-face{{font-family:'{family}';font-style:{style};font-weight:{weight};"
                             f"font-display:swap;src:url(fonts/{woff2}) format('woff2');unicode-range:{spec}}}")
    return rules, files

def mode_css():
    """The colour tokens: light by default, dark when the system asks for it unless the theme
    button chose light, and dark when the theme button chose it."""
    def block(i):
        return ";".join(f"--{k}:{v[i]}" for k, v in {**TOKENS, **EXTRA_TOKENS}.items()) + \
            f";color-scheme:{('light', 'dark')[i]}"
    return (f":root{{{block(0)}}}\n@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{{block(1)}}}}}\n"
            f":root[data-theme=dark]{{{block(1)}}}")

def luminance(hexa):
    rgb = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)

def contrasts():
    """(mode, text token, surface token, ratio) for every text colour on every surface, and the
    filled buttons, whose text is the background on ink."""
    rows = []
    for i, name in enumerate(("light", "dark")):
        rows += [(name, t, s, contrast(TOKENS[t][i], TOKENS[s][i])) for t in TEXT_TOKENS for s in SURFACES]
        rows.append((name, "bg", "ink", contrast(TOKENS["bg"][i], TOKENS["ink"][i])))
    return rows
