"""A page rendered in one call: to a PDF of a print format, or to a PNG."""
from collections.abc import Callable, Iterable

from playwright.sync_api import Page

from .browser import CHROMIUM_ARGS, chromium, load, print_pdf, screenshot, wait_for_fonts
from .errors import SystemFontError
from .formats import PX, design_height, resolve
from .pdf import system_fonts, to_format

Prepare = Callable[[Page], object]


class Renderer:
    """A Chromium session that renders pages one after the other, each in a browser context of
    its own, so that a render never depends on what an earlier one laid out.

        with Renderer(required_fonts=["EB Garamond"], bundled_fonts=["EBGaramond"]) as r:
            pdf = r.render_pdf(url, design_width=1123, size="A3", title="Block 100000")

    required_fonts are families that must have loaded (substrings of the names the page gives
    them). bundled_fonts are the PostScript name prefixes of the fonts the page ships: when given,
    a PDF that draws any text with another font raises SystemFontError, rather than depending on
    the fonts of the machine.
    """

    def __init__(self, *, required_fonts: Iterable[str] = (), bundled_fonts: Iterable[str] | None = None,
                 chromium_args: Iterable[str] = CHROMIUM_ARGS):
        self.required_fonts = tuple(required_fonts)
        self.bundled_fonts = None if bundled_fonts is None else tuple(bundled_fonts)
        self.chromium_args = tuple(chromium_args)
        self._session = None
        self.browser = None

    def __enter__(self) -> "Renderer":
        self._session = chromium(self.chromium_args)
        self.browser = self._session.__enter__()
        return self

    def __exit__(self, *exc):
        session, self._session, self.browser = self._session, None, None
        return session.__exit__(*exc)

    def _open(self, url: str, prepare: Prepare | None, **context):
        """A browser context of its own and its page, with url loaded, prepare(page) run, and the
        fonts ready."""
        if self.browser is None:
            raise RuntimeError("a Renderer renders inside a with statement")
        ctx = self.browser.new_context(**context)
        try:
            page = ctx.new_page()
            load(page, url, self.required_fonts)
            if prepare is not None:
                prepare(page)
                wait_for_fonts(page, self.required_fonts)
        except BaseException:
            ctx.close()
            raise
        return ctx, page

    def render_pdf(self, url: str, *, design_width: float, size: str | tuple[float, float], unit: str = "px",
                   title: str | None = None, author: str | None = None, subject: str | None = None,
                   creator: str | None = None, prepare: Prepare | None = None) -> bytes:
        """The page at url as a PDF of the format size (a name of SIZES, or (width, height) in
        millimetres). The page is laid out design_width wide (in unit, "px" or "mm") and as tall as
        the ratio of the format requires, printed, then scaled to the format with the metadata
        given. prepare(page), when given, runs once the page has loaded and before it is printed,
        to fill it (with page.evaluate, for instance); the fonts are awaited again after it."""
        fmt = resolve(size)
        height = design_height(design_width, fmt)
        per_unit = 1 if unit == "px" else PX
        ctx, page = self._open(url, prepare, viewport={"width": round(design_width * per_unit),
                                                       "height": round(height * per_unit)})
        try:
            raw = print_pdf(page, design_width, height, unit)
        finally:
            ctx.close()
        if self.bundled_fonts is not None and (found := system_fonts(raw, self.bundled_fonts)):
            raise SystemFontError(found)
        return to_format(raw, fmt, title=title, author=author, subject=subject, creator=creator)

    def render_png(self, url: str, *, width: int, height: int, scale: float = 1, clip: dict | None = None,
                   prepare: Prepare | None = None) -> bytes:
        """The page at url as a PNG, laid out in a viewport of width by height CSS pixels and drawn
        at scale device pixels per CSS pixel; clip ({"x", "y", "width", "height"}) keeps a region
        of the page only. prepare works as in render_pdf."""
        ctx, page = self._open(url, prepare, viewport={"width": width, "height": height},
                               device_scale_factor=scale)
        try:
            return screenshot(page, clip=clip)
        finally:
            ctx.close()
