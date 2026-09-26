"""Minimal Markdown dialect for posters.

Blocks (separated by blank lines):
  ## Heading                 section title (auto-numbered if meta.numbered)
  ::: figure <name>          SVG figure from the paper's figures.py
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
import html, re

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
    def __init__(self, figures, numbered):
        self.figures, self.numbered = figures, numbered
        self.math, self.sec, self.in_refs = [], 0, False
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
            elif b.startswith('## '):
                title = b[3:].strip()
                self.in_refs = title.lower() == 'references'
                if self.numbered and not self.in_refs:
                    self.sec += 1
                    out.append(f'<h2><span class="n">{self.sec}.</span> {self.inline(title, line)}</h2>')
                else:
                    title = re.sub(r'^((?:\d+\.)+)\s*', r'<span class="n">\1</span> ', self.inline(title, line))
                    out.append(f'<h2{" class=refs" if self.in_refs else ""}>{title}</h2>')
            elif re.match(r'#+\s', b):
                raise MarkdownError(line, 'only level-2 headings ("## ") are supported')
            elif b.startswith(':::'):
                out.append(self.directive(line, b))
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

    def directive(self, line, b):
        head, *rest = b.split('\n')
        if is_wide(head):
            m = WIDE.match(head)
            if not m:
                raise MarkdownError(line, f'expected "::: wide" or "::: wide cols=N", got "{head}"')
            return self.wide(int(m.group(1) or 1), '\n'.join(rest[:-1]), line + 1)
        words = head.split()
        if words[1:2] != ['figure'] or len(words) != 3 or rest:
            raise MarkdownError(line, f'expected "::: figure <name>" or "::: wide", got "{head}"')
        if words[2] not in self.figures:
            known = ', '.join(sorted(self.figures)) or 'none, figures.py is missing or empty'
            raise MarkdownError(line, f'unknown figure "{words[2]}" (known: {known})')
        return f'<figure>{self.figures[words[2]]()}</figure>'

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

def render(text, figures=None, numbered=False):
    """Returns (html, math) where math is a list of TeX strings; html holds
    placeholders <!--MATH:i--> to be replaced once KaTeX has run."""
    r = Renderer(figures or {}, numbered)
    out = r.render(text) + r.footnotes()
    return '\n'.join(out), r.math
