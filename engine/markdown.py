"""Minimal Markdown dialect for posters.

Blocks (separated by blank lines):
  ## Heading                 section title, ### and #### for sub-sections; numbered 1., 1.1.,
                             1.1.1. with meta.numbered, and a number that starts a title,
                             such as 3.1., is set the same way
  ::: figure <name>          SVG figure from the paper's figures.py
  ::: image <file> [caption="..."] [width=N%] [on_dark=plate|invert] [on_light=multiply]
                             image from the paper's folder, embedded in the page. On dark
                             themes plate (default) keeps it on a light card and invert turns
                             its white into the paper and its black into the ink; on light
                             themes multiply melts its white into the paper. With
                             meta.layout: hero, the first image goes to the top of the page
  ::: wide [cols=N]          block across all the columns, closed by a ":::" line, holding any
  ...                        of these blocks; with cols=N (default 1) its "## " sections sit side
  :::                        by side on a grid of N columns, one section per cell, in order
  $$ ... $$                  display math (KaTeX), may span several lines
  ```lang ... ```            code block, may contain blank lines
  1. item                    ordered list (after "## References": reference list)
  - item                     unordered list
  (1) text / (2a) text       labelled items; a label ending with a letter makes a sub-item,
                             kept in the same column as the item before it
  [^label]: text             footnote, listed with the others at the end of the text
  <html ...>                 raw HTML, passed through
  anything else              paragraph
Inline: **bold**, *italic*, `code`, [n] / [n-m] citations, [^label] footnote calls
(numbered in order of first call), smart quotes.
Malformed input raises MarkdownError, which carries the line number.
"""
import base64, html, re, shlex

class MarkdownError(ValueError):
    def __init__(self, line, msg):
        super().__init__(f"line {line}: {msg}")
        self.line, self.msg = line, msg

def smart(s):
    parts = re.split(r'(<[^>]+>)', s)
    for i, p in enumerate(parts):
        if i % 2: continue
        p = re.sub(r'(^|[\s(\[])"', r'\1“', p).replace('"', '”')
        p = re.sub(r"(^|[\s(\[])'", r'\1‘', p).replace("'", '’')
        parts[i] = p
    return ''.join(parts)

def inline(s):
    s = ' '.join(s.split())
    s = re.sub(r'`([^`]+)`', lambda m: f'<code>{html.escape(m.group(1))}</code>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<![\w*])\*(\S.*?)\*(?![\w*])', r'<i>\1</i>', s)
    s = re.sub(r'((?:\[\d+(?:-\d+)?\])+)', r'<cite>\1</cite>', s)
    return smart(s)

LABEL = re.compile(r'^\((\d+[a-z]?)\)\s+', re.M)
NOTE_CALL = re.compile(r'\[\^([^\]\s]+)\]')
NOTE_DEF = re.compile(r'\[\^([^\]\s]+)\]:\s+')
WIDE = re.compile(r':::\s+wide(?:\s+cols=([1-9]\d*))?\s*$')
IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
               '.webp': 'image/webp', '.svg': 'image/svg+xml'}
ON_DARK, ON_LIGHT = ('plate', 'invert'), ('multiply',)

def is_wide(line):
    return line.startswith(':::') and line.split()[1:2] == ['wide']

def fence_end(lines, i, first):
    """Index of the line after the ``` fence that closes the one opened at line i."""
    start = i
    i += 1
    while i < len(lines) and not lines[i].strip().startswith('```'):
        i += 1
    if i == len(lines):
        raise MarkdownError(first + start, 'code block is never closed with ```')
    return i + 1

def blocks(text, first=1):
    """Yields (line number, block). Blocks end at a blank line, except code, display math
    and wide blocks, which run to their closing fence. first numbers the first line."""
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        start = i
        if lines[i].startswith('```'):
            i = fence_end(lines, i, first)
        elif lines[i].startswith('$$'):
            # the opening line closes the block itself when it is more than a bare $$
            while not (lines[i].rstrip().endswith('$$') and (i > start or len(lines[i].strip()) > 2)):
                i += 1
                if i == len(lines):
                    raise MarkdownError(first + start, 'math block is never closed with $$')
            i += 1
        elif is_wide(lines[i]):
            i += 1
            while i < len(lines) and lines[i].strip() != ':::':
                if is_wide(lines[i]):
                    raise MarkdownError(first + i, 'wide blocks cannot be nested')
                i = fence_end(lines, i, first) if lines[i].startswith('```') else i + 1
            if i == len(lines):
                raise MarkdownError(first + start, 'wide block is never closed with a ":::" line')
            i += 1
        else:
            while i < len(lines) and lines[i].strip():
                i += 1
        yield first + start, '\n'.join(lines[start:i])

class Renderer:
    """State shared by the whole text: math, section numbers, footnotes."""
    def __init__(self, figures, numbered, assets=None, hero=False):
        self.figures, self.numbered, self.assets = figures, numbered, assets
        self.hero = {} if hero else None  # filled by the first image when the layout is hero
        self.math, self.nums, self.in_refs = [], [0, 0, 0], False  # nums: ##, ###, #### counters
        self.notes = {}  # label: (line of the definition, text)
        self.calls = {}  # label: line of the first call, in the order of first calls

    def inline(self, s, line):
        """inline(), plus footnote calls outside code spans."""
        def call(m):
            self.calls.setdefault(m.group(1), line)
            return f'<sup class="fn">{list(self.calls).index(m.group(1)) + 1}</sup>'
        parts = re.split(r'(`[^`]+`)', s)
        parts[::2] = [NOTE_CALL.sub(call, p) for p in parts[::2]]
        return inline(''.join(parts))

    def render(self, text, first=1):
        """HTML fragments of the blocks of text."""
        out = []
        for line, b in blocks(text, first):
            if b.startswith('```'):
                code = b.split('\n', 1)[1].rsplit('```', 1)[0].rstrip()
                out.append(f'<pre class="code">{html.escape(code)}</pre>')
            elif b.startswith('$$'):
                tex = '\n'.join(l for l in b.split('\n') if l.strip())
                self.math.append(tex.strip()[2:-2].strip())
                out.append(f'<div class="eq"><!--MATH:{len(self.math)-1}--></div>')
            elif m := re.match(r'(#{2,4}) ', b):
                out.append(self.heading(len(m.group(1)), b[m.end():].strip(), line))
            elif re.match(r'#+\s', b):
                raise MarkdownError(line, 'headings are "##", "###" or "####"')
            elif b.startswith(':::'):
                if h := self.directive(line, b):
                    out.append(h)
            elif m := NOTE_DEF.match(b):
                if m.group(1) in self.notes:
                    raise MarkdownError(line, f'footnote [^{m.group(1)}] is defined twice')
                self.notes[m.group(1)] = (line, b[m.end():])
            elif b.startswith('<'):
                out.append(b)
            elif re.match(r'^\d+\.\s', b):
                items = re.split(r'\n(?=\d+\.\s)', b)
                items = [self.inline(re.sub(r'^\d+\.\s+', '', x), line) for x in items]
                if self.in_refs:
                    out.append('<ol class="refs">' + ''.join(
                        f'<li><span>[{n+1}]</span>{x}</li>' for n, x in enumerate(items)) + '</ol>')
                else:
                    out.append('<ol>' + ''.join(f'<li>{x}</li>' for x in items) + '</ol>')
            elif re.match(r'^-\s', b):
                items = re.split(r'\n(?=-\s)', b)
                out.append('<ul>' + ''.join(f'<li>{self.inline(x[2:], line)}</li>' for x in items) + '</ul>')
            elif LABEL.match(b):
                for lab, body in re.findall(r'^\((\d+[a-z]?)\)\s+(.*?)(?=^\(\d+[a-z]?\)\s|\Z)', b, re.S | re.M):
                    sub = lab[-1].isalpha()
                    item = (f'<div class="item{" sub" if sub else ""}"><span class="lbl">{lab}</span>'
                            f'<div>{self.inline(body, line)}</div></div>')
                    # a sub-item joins its item in a group that columns cannot split
                    if sub and out and out[-1].startswith('<div class="group">'):
                        out[-1] = out[-1][:-len('</div>')] + item + '</div>'
                    elif sub and out and out[-1].startswith('<div class="item">'):
                        out[-1] = f'<div class="group">{out[-1]}{item}</div>'
                    else:
                        out.append(item)
            else:
                out.append(f'<p>{self.inline(b, line)}</p>')
        return out

    def heading(self, level, title, line):
        if level == 2:
            self.in_refs = title.lower() == 'references'
        title = self.inline(title, line)
        if self.numbered and not self.in_refs:
            self.nums[level - 2] += 1
            self.nums[level - 1:] = [0] * (4 - level)
            n = '.'.join(map(str, self.nums[:level - 1])) + '.'
            return f'<h{level}><span class="n">{n}</span> {title}</h{level}>'
        # 1., 3.1., 3.1.1. or, as in some RFCs, 2.1 and 2.2.1.1; a bare number such as 1149 is not one
        title = re.sub(r'^(\d+(?:\.\d+)+\.?|\d+\.)\s+', r'<span class="n">\1</span> ', title)
        return f'<h{level}{" class=refs" if level == 2 and self.in_refs else ""}>{title}</h{level}>'

    def directive(self, line, b):
        head, *rest = b.split('\n')
        if is_wide(head):
            m = WIDE.match(head)
            if not m:
                raise MarkdownError(line, f'expected "::: wide" or "::: wide cols=N", got "{head}"')
            return self.wide(int(m.group(1) or 1), '\n'.join(rest[:-1]), line + 1)
        words = head.split()
        if words[1:2] == ['image'] and not rest:
            return self.image(line, head)
        if words[1:2] != ['figure'] or len(words) != 3 or rest:
            raise MarkdownError(line, f'expected "::: figure <name>", "::: image <file>" or "::: wide", got "{head}"')
        if words[2] not in self.figures:
            known = ', '.join(sorted(self.figures)) or 'none, figures.py is missing or empty'
            raise MarkdownError(line, f'unknown figure "{words[2]}" (known: {known})')
        return f'<figure>{self.figures[words[2]]()}</figure>'

    def image(self, line, head):
        usage = '::: image <file> [caption="..."] [width=N%] [on_dark=plate|invert] [on_light=multiply]'
        try:
            words = shlex.split(head)
        except ValueError as e:
            raise MarkdownError(line, f'{e} in "{head}"') from None
        if len(words) < 3:
            raise MarkdownError(line, f'expected {usage}')
        opts = {}
        for w in words[3:]:
            key, eq, value = w.partition('=')
            if not eq or key not in ('caption', 'width', 'on_dark', 'on_light') or key in opts:
                raise MarkdownError(line, f'unexpected "{w}", expected {usage}')
            opts[key] = value
        width, dark, light = opts.get('width', '100%'), opts.get('on_dark', 'plate'), opts.get('on_light', '')
        if not re.fullmatch(r'(100|[1-9]\d?)%', width):
            raise MarkdownError(line, f'width must be a percentage from 1% to 100%, got "{width}"')
        if dark not in ON_DARK:
            raise MarkdownError(line, f'on_dark must be one of {", ".join(ON_DARK)}, got "{dark}"')
        if light and light not in ON_LIGHT:
            raise MarkdownError(line, f'on_light must be one of {", ".join(ON_LIGHT)}, got "{light}"')
        path = self.assets / words[2] if self.assets else None
        if path is None or not path.is_file():
            raise MarkdownError(line, f'image "{words[2]}" not found in the folder of the paper')
        if path.suffix.lower() not in IMAGE_TYPES:
            raise MarkdownError(line, f'unsupported image type "{path.suffix}" ({", ".join(IMAGE_TYPES)})')
        data = path.read_bytes()
        w, h = image_size(path, data)
        img = {'src': f'data:{IMAGE_TYPES[path.suffix.lower()]};base64,{base64.b64encode(data).decode()}',
               'w': w, 'h': h, 'dark': dark, 'light': light, 'caption': self.inline(opts.get('caption', ''), line)}
        if self.hero == {}:
            self.hero.update(img)
            return ''
        size = f' width="{w}" height="{h}"' if w else ''  # reserves the space before the image loads
        caption = f'<figcaption>{img["caption"]}</figcaption>' if img['caption'] else ''
        return (f'<figure {figure_attrs(img)} style="width:{width}"><img src="{img["src"]}"{size} alt="">'
                f'{caption}</figure>')

    def wide(self, cols, text, first):
        parts = self.render(text, first)
        if cols == 1:
            return '<div class="wide">' + '\n'.join(parts) + '</div>'
        cells = []
        for p in parts:  # each "## " section opens a cell
            if p.startswith('<h2') or not cells:
                cells.append([])
            cells[-1].append(p)
        cells = ''.join('<div class="cell">' + '\n'.join(c) + '</div>' for c in cells)
        return f'<div class="wide grid" style="--wcols:{cols}">{cells}</div>'

    def footnotes(self):
        for label, line in self.calls.items():
            if label not in self.notes:
                raise MarkdownError(line, f'footnote [^{label}] is never defined')
        for label, (line, text) in self.notes.items():
            if label not in self.calls:
                raise MarkdownError(line, f'footnote [^{label}] is defined but never called')
            if NOTE_CALL.search(text):
                raise MarkdownError(line, f'footnote [^{label}] calls another footnote')
        if not self.calls:
            return []
        notes = ''.join(f'<li><span>{n}</span><div>{inline(self.notes[label][1])}</div></li>'
                        for n, label in enumerate(self.calls, 1))
        return [f'<div class="footnotes"><ol>{notes}</ol></div>']

def figure_attrs(img):
    """Class and data attributes of an image figure, which the page styles by theme."""
    light = f' data-light="{img["light"]}"' if img['light'] else ''
    return f'class="image" data-dark="{img["dark"]}"{light}'

def image_size(path, data):
    """Pixel size of an image, or (None, None) for an SVG that does not state it."""
    if path.suffix.lower() == '.svg':
        head = data[:2000].decode('utf-8', 'replace')
        m = re.search(r'viewBox="[\d.\s-]*?([\d.]+)\s+([\d.]+)"', head)
        return (round(float(m.group(1))), round(float(m.group(2)))) if m else (None, None)
    from PIL import Image
    with Image.open(path) as im:
        return im.size

def render(text, figures=None, numbered=False, assets=None, hero=False):
    """Returns (html, math, hero). math is a list of TeX strings, and html holds
    placeholders <!--MATH:i--> to be replaced once KaTeX has run. With hero, the first
    image is kept out of the text and returned as a dict (src, w, h, dark, light, caption).
    assets is the folder that ::: image files are read from."""
    r = Renderer(figures or {}, numbered, assets, hero)
    out = r.render(text) + r.footnotes()
    return '\n'.join(out), r.math, r.hero
