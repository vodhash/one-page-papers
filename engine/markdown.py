"""Minimal Markdown dialect for posters.

Blocks (separated by blank lines):
  ## Heading                 section title (auto-numbered if meta.numbered)
  ::: figure <name>          SVG figure from the paper's figures.py
  $$ ... $$                  display math (KaTeX)
  ```lang ... ```            code block
  1. item                    ordered list (after "## References": reference list)
  - item                     unordered list
  (1) text / (2a) text       labelled items (sub-items when the label ends with a letter)
  <html ...>                 raw HTML, passed through
  anything else              paragraph
Inline: **bold**, *italic*, `code`, [n] / [n-m] citations, smart quotes.
"""
import html, re

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

def render(text, figures=None, numbered=False):
    """Returns (html, math) where math is a list of TeX strings; html holds
    placeholders <!--MATH:i--> to be replaced once KaTeX has run."""
    figures = figures or {}
    out, math, sec, in_refs = [], [], 0, False
    blocks = re.split(r'\n\s*\n', text.strip())
    i = 0
    while i < len(blocks):
        b = blocks[i].strip('\n'); i += 1
        if b.startswith('```'):
            while b.count('```') < 2 and i < len(blocks):
                b += '\n\n' + blocks[i]; i += 1
            code = b.split('\n', 1)[1].rsplit('```', 1)[0].rstrip()
            out.append(f'<pre class="code">{html.escape(code)}</pre>')
        elif b.startswith('$$'):
            while not b.rstrip().endswith('$$') or b.strip() == '$$':
                b += '\n' + blocks[i]; i += 1
            math.append(b.strip()[2:-2].strip())
            out.append(f'<div class="eq"><!--MATH:{len(math)-1}--></div>')
        elif b.startswith('## '):
            title = b[3:].strip()
            in_refs = title.lower() == 'references'
            if numbered and not in_refs:
                sec += 1
                out.append(f'<h2><span class="n">{sec}.</span> {inline(title)}</h2>')
            else:
                title = re.sub(r'^(\d+\.)\s*', r'<span class="n">\1</span> ', inline(title))
                out.append(f'<h2{" class=refs" if in_refs else ""}>{title}</h2>')
        elif b.startswith('::: figure '):
            name = b.split()[2]
            out.append(f'<figure>{figures[name]()}</figure>')
        elif b.startswith('<'):
            out.append(b)
        elif re.match(r'^\d+\.\s', b):
            items = re.split(r'\n(?=\d+\.\s)', b)
            items = [inline(re.sub(r'^\d+\.\s+', '', x)) for x in items]
            if in_refs:
                out.append('<ol class="refs">' + ''.join(
                    f'<li><span>[{n+1}]</span>{x}</li>' for n, x in enumerate(items)) + '</ol>')
            else:
                out.append('<ol>' + ''.join(f'<li>{x}</li>' for x in items) + '</ol>')
        elif re.match(r'^-\s', b):
            items = re.split(r'\n(?=-\s)', b)
            out.append('<ul>' + ''.join(f'<li>{inline(x[2:])}</li>' for x in items) + '</ul>')
        elif LABEL.match(b):
            for lab, body in re.findall(r'^\((\d+[a-z]?)\)\s+(.*?)(?=^\(\d+[a-z]?\)\s|\Z)', b, re.S | re.M):
                sub = ' sub' if lab[-1].isalpha() else ''
                out.append(f'<div class="item{sub}"><span class="lbl">{lab}</span><div>{inline(body)}</div></div>')
        else:
            out.append(f'<p>{inline(b)}</p>')
    return '\n'.join(out), math
