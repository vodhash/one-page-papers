# one-page-papers

**Foundational papers, typeset on a single poster. Print them, frame them, hang them.**

Each paper is laid out in full on one page: every section, equation, code listing, table and reference, with figures redrawn as vector graphics. The body size is computed automatically so the text fills the page exactly.

## Papers

### Bitcoin: A Peer-to-Peer Electronic Cash System
Satoshi Nakamoto, 2008. Full text, 7 redrawn figures, genesis block in the footer.

| ivory | white | genesis | blueprint |
|---|---|---|---|
| ![](docs/bitcoin-ivory.png) | ![](docs/bitcoin-white.png) | ![](docs/bitcoin-genesis.png) | ![](docs/bitcoin-blueprint.png) |

### RFC 1925: The Twelve Networking Truths
Ross Callon, 1 April 1996. Large type, readable from across the room.

| ivory | white | genesis | blueprint |
|---|---|---|---|
| ![](docs/rfc-1925-ivory.png) | ![](docs/rfc-1925-white.png) | ![](docs/rfc-1925-genesis.png) | ![](docs/rfc-1925-blueprint.png) |

### PEP 20: The Zen of Python
Tim Peters, 2004. The nineteen aphorisms, set as a typographic poster; comfortable down to A3.

| ivory | white | genesis | blueprint |
|---|---|---|---|
| ![](docs/zen-of-python-ivory.png) | ![](docs/zen-of-python-white.png) | ![](docs/zen-of-python-genesis.png) | ![](docs/zen-of-python-blueprint.png) |

### RFC 791: Internet Protocol (excerpt)
Jon Postel, Editor, September 1981. Section 3.1, the Internet Header Format, with Figure 4 across the page, drawn exactly as in the RFC. Dense text: print at A1 or larger.

| ivory | white | genesis | blueprint |
|---|---|---|---|
| ![](docs/rfc-791-ivory.png) | ![](docs/rfc-791-white.png) | ![](docs/rfc-791-genesis.png) | ![](docs/rfc-791-blueprint.png) |

### John Snow: the Broad Street cholera map
John Snow, 1854. The map that traced the Soho outbreak to one water pump, with a short notice written for this poster (not a period text).

| ivory | white | genesis | blueprint |
|---|---|---|---|
| ![](docs/snow-cholera-map-ivory.png) | ![](docs/snow-cholera-map-white.png) | ![](docs/snow-cholera-map-genesis.png) | ![](docs/snow-cholera-map-blueprint.png) |

## Download

The PDFs are attached to the [latest release](https://github.com/vodhash/one-page-papers/releases/latest): one zip per poster, or each PDF alone, named `<paper>-<format>-<theme>.pdf`. Text, equations and figures are all vector, so they print sharp at any size.

| Format | File size | Prints at |
|---|---|---|
| `A` | 59.4 × 84.1 cm (A1) | A0, A1, A2, A3 (same ratio, just scale) |
| `50x70` | 50 × 70 cm | 50 × 70 cm |
| `60x80` | 60 × 80 cm | 60 × 80 cm |

Themes: `ivory` (warm paper), `white` (pure white), `genesis` (dark, bitcoin orange), `blueprint` (navy).

**Print tips.** For dense papers like Bitcoin, A2 is the smallest comfortable size (8.7 pt body text; `make check` prints the size of every paper at every format). Use matte paper, 200 g/m² or heavier. Dark themes are best printed by a professional lab.

## Build

Requires Node.js, Python 3 and Make. `make deps` uses [uv](https://docs.astral.sh/uv/) when it is installed, and the standard `venv` module otherwise (on Debian and Ubuntu: `apt install python3-venv`).

```bash
make deps      # node_modules and .venv at the pinned versions, plus headless Chromium
make           # every paper × format × theme, into dist/ and docs/
make bitcoin   # a single paper
make check     # fit every poster and report problems, without touching dist/ or docs/
.venv/bin/python engine/build.py rfc-1925 --formats A --themes genesis
```

Builds are deterministic: rebuilding unchanged sources rewrites byte-identical files, so a commit only carries the previews in `docs/` of the posters that changed. The PDFs in `dist/` are not versioned: pushing a `v*` tag makes GitHub Actions build them all and attach them to a release. Versions are pinned (`package-lock.json`, and `requirements.txt`, whose Playwright version fixes the Chromium build), and Chromium lays text out without the local font hinting settings, to keep the layout independent of the machine.

`make check` also runs on GitHub Actions for every push and pull request. It fails when a poster overflows its page, when it still fits at the largest allowed body size, or when a character is drawn with a system font.

## Add a paper

Create `papers/<name>/` with:

| File | Purpose |
|---|---|
| `meta.yaml` | title, header, abstract, footer, columns, license (see existing papers) |
| `text.md` | the text, in the small Markdown dialect documented in `engine/markdown.py` |
| `figures.py` | optional: `FIGS = {"name": fn}`, each `fn()` returns an SVG string built with `engine/svg.py` |
| images | optional: PNG, JPEG, GIF, WebP or SVG files for `::: image`, embedded in the PDF |
| `style.css` | optional: paper-specific CSS; a rule on `:root[data-theme=genesis]` applies to one theme only |

`text.md` is plain Markdown paragraphs and lists, plus these constructs (all listed in `engine/markdown.py`):

| Syntax | Effect |
|---|---|
| `## Title`, `### Title`, `#### Title` | headings; with `numbered: true` they are numbered 1., 1.1., 1.1.1., and a title that starts with a number such as `3.1.` gets the same styling |
| `::: figure <name>` | an SVG figure from `figures.py` |
| `::: image <file> [caption="…"] [width=N%] [on_dark=plate\|invert] [on_light=multiply]` | an image from the folder of the paper, embedded in the page, `width` of its column (default 100%). On the dark themes, `plate` (default) keeps it on a light card and `invert` turns its white into the paper and its black into the ink (for line drawings). On the light themes, `on_light=multiply` melts its white into the paper, for scans with a white background |
| `::: wide` … `:::` | a block across all the columns, holding any other syntax (code, math, figures, HTML) |
| `::: wide cols=N` … `:::` | the `##` sections of the block side by side, one per left-aligned cell of an N-column grid (see `papers/rfc-1925`) |
| `$$ … $$` | display math, rendered with KaTeX |
| `(1)`, `(1a)` | labelled items; a sub-item such as `(1a)` stays in the same column as its item |
| `[^label]`, `[^label]: text` | footnote call and definition; notes are numbered in order of first call and listed at the end of the text |
| `<tag …>` | raw HTML, passed through |

Mistakes, such as an unclosed block or a footnote that is never defined, are reported with their line number.

In `meta.yaml`, `title` and `license` are required and unknown keys are rejected. The optional keys:

| Key | Default | Effect |
|---|---|---|
| `lang` | `en` | language of the text, for hyphenation (English, French, German and many more) |
| `layout` | `columns` | `centered` suits short texts: one column unless `columns` says otherwise, vertically centered on the page. `hero` puts the first `::: image` of the text across the top of the page, and the text in columns below |
| `hero_height` | 50 | share of the page height given to the hero image, in % |
| `themes` | all | the themes this paper is printed in, for instance `[white, genesis]` |
| `columns` | 4, or 1 when centered | number of text columns |
| `font_range` | `[8, 40]` | bounds of the search for the body size, in pt; the build warns when the text still fits at the maximum |
| `max_font` | none | hard cap on the body size, in pt, so that a short text does not end up in giant type; reaching it is expected |
| `numbered` | `false` | number the `##` sections |
| `title_html`, `title_size`, `header_scale` | `title`, `76pt`, `1` | title with HTML markup, its size, and the scale of the other header lines |
| `kicker`, `author`, `byline`, `emblem`, `abstract`, `abstract_label`, `footer` | | header and footer content (see existing papers) |

Every character must come from the bundled fonts (EB Garamond, JetBrains Mono, KaTeX), since a system font would make the PDF depend on the machine. `make check` names the characters that fall back; `papers/bitcoin/style.css` shows the fix, taking ₿ from JetBrains Mono.

Only add texts whose license allows redistribution, and record it in `meta.yaml`.

## How it works

`engine/build.py` parses the Markdown, pre-renders math with KaTeX, injects SVG figures into an HTML template, then drives headless Chromium: for each format it waits for the fonts, binary-searches the largest body size that fits in whole hundredths of a point, checks it again on a freshly loaded page, prints a PDF at a fixed 594 mm design width, and scales it to the target format with pypdf, keeping the page vector and its content losslessly compressed. Images are embedded in the page as data URIs, so every PDF is self-contained. Themes are sets of CSS variables in `engine/themes.py`.

## Origin

It started with a simple wish: to frame the Bitcoin whitepaper and hang
it in my office. A few one-page versions already existed online, but none
matched what I had in mind, so I typeset my own: the full text, the
equations and the C code, with every figure redrawn as vector graphics
and the genesis block hash in the footer.

The first version was a single poster, briefly published as
`one-page-satoshi`. Once it worked, the obvious question followed: which
other texts deserve the same treatment? A list quickly grew, from early
cryptocurrency papers to RFCs, manifestos and founding texts of science,
and it became clear that the typesetting engine was the real project.
The Bitcoin-specific code was split into a reusable engine and per-paper
content, and the project became `one-page-papers`.

Each new poster has pushed the engine a little further. RFC 1925 brought
short texts in large type, the Zen of Python centred layouts, RFC 791
full-width diagrams, and John Snow's cholera map images and hero layouts.
Some texts taught the limits of the idea: Turing's *On Computable
Numbers* runs to 36 pages and cannot fit legibly on a single sheet, so
not every classic makes the cut.

## License

Engine code: MIT. Each paper keeps its own license, see [`LICENSE`](LICENSE) and `papers/*/meta.yaml`.
