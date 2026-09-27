# onepage-engine

Renders a single HTML page to a vector PDF at a fixed design width, scaled to print formats,
with embedded fonts and the same layout on every machine. It is the engine of
[one-page-papers](https://github.com/vodhash/one-page-papers), as a package.

## What it guarantees

- **The same layout on every machine.** Chromium comes from a pinned Playwright (1.63.0, Chromium
  153.0.8010.12), and lays text out without the font hinting settings of the machine
  (`--font-render-hinting=none`).
- **One layout for every format.** A page is laid out at a fixed design width, as tall as the
  ratio of the target format requires, printed, then scaled to the format. The PDF stays vector,
  and its content is compressed losslessly.
- **Fonts loaded and embedded.** A render waits until every font of the page has loaded, and
  fails when one did not. It can also refuse a PDF in which some text was drawn with a font of the
  machine rather than one of the fonts the page ships.
- **Backgrounds printed.** Colours and backgrounds are part of the PDF.

## Install

Python 3.12 or later, then the Chromium build of the pinned Playwright:

```sh
pip install --index-url <index>/simple/ onepage-engine==0.1.0    # from the index it is published to
pip install "onepage-engine @ git+https://github.com/vodhash/one-page-papers@engine-v0.1.0#subdirectory=engine"
python -m playwright install --only-shell chromium
```

A private index that does not mirror PyPI (Forgejo, GitLab) leaves Playwright and pypdf to PyPI.
Adding PyPI with `--extra-index-url` would let pip take `onepage-engine` from whichever index has
the highest version, a dependency confusion. Either pin the engine with its hash
(`--require-hashes`), or declare the private index for this package alone, as uv does:

```toml
[[tool.uv.index]]
name = "private"
url = "<index>/simple/"
explicit = true                      # used only by the packages that name it below

[tool.uv.sources]
onepage-engine = { index = "private" }
```

## Quick start

```python
from pathlib import Path
from onepage_engine import Renderer

page = Path("poster.html").resolve().as_uri()
with Renderer(required_fonts=["EB Garamond"], bundled_fonts=["EBGaramond"]) as r:
    for size in ("A3", "50x70", "60x80"):
        pdf = r.render_pdf(page, design_width=1123, size=size, title="Block 100000", author="Blockmemento")
        Path(f"poster-{size}.pdf").write_bytes(pdf)
    png = r.render_png(page, width=1123, height=1588, scale=2)
```

The page is laid out 1123 CSS pixels wide (A3 at 96 dpi) and as tall as each format requires:
1588 px for A3, 1572 px for 50 × 70 cm, 1497 px for 60 × 80 cm. A page made for it fills its
viewport, and then every format is the same design, scaled.

## API

### Renderer

`Renderer(*, required_fonts=(), bundled_fonts=None, chromium_args=CHROMIUM_ARGS)` is a Chromium
session, used in a `with` statement. Every render runs in a browser context of its own, so that no
render depends on what an earlier one laid out.

- `required_fonts`: families that must have loaded, matched as substrings of the names the page
  gives them.
- `bundled_fonts`: PostScript name prefixes of the fonts the page ships (`EBGaramond`, for
  instance). When given, a PDF with text drawn in any other font raises `SystemFontError`.

`render_pdf(url, *, design_width, size, unit="px", title=None, author=None, subject=None,
creator=None, prepare=None) -> bytes`

- `size`: a name of `SIZES`, or `(width, height)` in millimetres.
- `unit`: `"px"` or `"mm"`, the unit of `design_width`.
- `title`, `author`, `subject`, `creator`: the metadata of the PDF; `None` leaves an entry out.
- `prepare(page)`: runs once the page has loaded and before it is printed, to fill it (with
  `page.evaluate(...)`, for instance); the fonts are awaited again after it.

`render_png(url, *, width, height, scale=1, clip=None, prepare=None) -> bytes` lays the page out in
a viewport of `width` by `height` CSS pixels and draws it at `scale` device pixels per CSS pixel;
`clip` (`{"x", "y", "width", "height"}`) keeps a region of the page only.

### The steps of a render

For a caller that acts on the page between loading and printing, as one-page-papers does when it
fits the size of its text to the page:

| Function | What it does |
|----------|--------------|
| `chromium(args=CHROMIUM_ARGS)` | context manager: a headless Chromium, closed on exit |
| `load(page, url, required_fonts=())` | opens `url`, waits for its fonts, returns the families loaded |
| `wait_for_fonts(page, required=())` | lays the page out and waits for its fonts, after a change |
| `print_pdf(page, width, height, unit="mm", path=None)` | prints the first page, backgrounds included, and returns the PDF |
| `screenshot(page, clip=None, path=None)` | a PNG of the viewport, or of a region |
| `to_format(pdf, size, *, title=None, author=None, subject=None, creator=None)` | scales the first page of a PDF to a format, with its metadata |
| `system_fonts(pdf, bundled)` | the fonts of a PDF that are not bundled, with the characters they draw |
| `same_pdf(old, new)` | whether two PDFs are the same, but for differences that do not show |
| `font_name(font)` | the PostScript name of a PDF font, without its subset tag |

```python
from onepage_engine import SIZES, chromium, design_height, load, print_pdf, to_format

with chromium() as browser:
    page = browser.new_page()
    height = design_height(594, SIZES["50x70"])          # millimetres
    load(page, "file:///path/to/paper.html", required_fonts=["EB Garamond"])
    ...                                                  # fit the text, measure, restyle
    pdf = to_format(print_pdf(page, 594, height), "50x70", title="Bitcoin")
```

### Formats and units

- `SIZES`: `A0` to `A5`, `50x70`, `60x80`, `letter`, `tabloid`, `18x24` and `24x36`, as
  `(width, height)` in millimetres. `ISO_A` holds the A sizes alone.
- `design_height(design_width, size)`: the height of a page laid out `design_width` wide for the
  format `size`, in the unit of `design_width`.
- `MM`: PDF points per millimetre. `PX`: CSS pixels per millimetre.
- Playwright counts 3.78 px to the millimetre rather than 96 / 25.4, so a page designed in CSS
  pixels is best printed in `px`; `to_format` then scales it to the exact size of the format.

### Errors

All of them are `EngineError`:

- `FontLoadError`: a font failed to load, or a required family is missing (`missing` names them).
- `SystemFontError`: some text was drawn with fonts of the machine (`fonts` maps each one to the
  characters it draws).

## Determinism

The same page renders to the same bytes. Between two machines, two differences that do not show
can remain: in about one print in twenty of a page full of formulas, Chromium sets one run of
glyphs on a baseline rounded to a whole pixel, and the last digits of some numbers (the matrix of
a rotation) depend on the processor. `same_pdf` tolerates exactly these, line by line in the
content stream, and requires every other object to be identical byte for byte. one-page-papers
checks its 1,200 versioned PDFs with it on every change.

## Versioning

Semantic versioning, the bytes of the PDFs included. Before 1.0, a change of the API or of the
output is a new minor version. From 1.0, a change of the API that breaks callers is a new major
version, and a change of the pinned Playwright or pypdf, or of the Chromium flags, which can move
text on the page, is at least a new minor version. `CHANGELOG.md` lists them.

## Tests

```sh
pip install -e "engine[test]"
python -m pytest engine/tests
```

The rendering tests need Chromium and the fonts of `node_modules/@fontsource` (`npm ci` at the
root of one-page-papers); they are skipped without them.

## Publishing

For maintainers. The tags `engine-vX.Y.Z` mark the releases of the package; the `v*` tags release
the posters of one-page-papers.

```sh
make engine-dist       # the wheel and the sdist, in engine/dist/
make engine-publish    # uploads them to UV_PUBLISH_URL, as UV_PUBLISH_USERNAME with UV_PUBLISH_PASSWORD
```

## License

MIT, like the rest of the engine code of one-page-papers.
