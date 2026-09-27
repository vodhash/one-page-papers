"""Chromium, driven by Playwright: launched so that it lays text out the same way on every
machine, a page loaded until its fonts are ready, then printed or captured."""
import contextlib
from collections.abc import Iterable, Iterator
from os import PathLike

from playwright.sync_api import Browser, Page, sync_playwright

from .errors import FontLoadError

# Without this flag Chromium lays text out with the hinting of the local fontconfig setup,
# so the line breaks, and any size fitted to the page, would change from one machine to another.
CHROMIUM_ARGS = ("--font-render-hinting=none",)

FONTS_JS = """async () => {
    document.body.offsetHeight;  // lay out first, so that every font in use starts loading
    await document.fonts.ready;
    const faces = [...document.fonts];
    return {loaded: faces.filter(f => f.status === 'loaded').map(f => f.family),
            failed: faces.filter(f => f.status === 'error').map(f => f.family)};
}"""


@contextlib.contextmanager
def chromium(args: Iterable[str] = CHROMIUM_ARGS) -> Iterator[Browser]:
    """A headless Chromium launched with args, closed on exit."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=list(args))
        try:
            yield browser
        finally:
            browser.close()


def wait_for_fonts(page: Page, required: Iterable[str] = ()) -> list[str]:
    """Lays page out, waits until every font it uses has loaded, and returns the families loaded.
    Raises FontLoadError when a font failed to load, or when no loaded family contains one of the
    names of required."""
    fonts = page.evaluate(FONTS_JS)
    absent = [name for name in required if not any(name in family for family in fonts["loaded"])]
    if fonts["failed"] or absent:
        raise FontLoadError(", ".join(sorted(set(fonts["failed"]))) or ", ".join(absent))
    return fonts["loaded"]


def load(page: Page, url: str, required_fonts: Iterable[str] = ()) -> list[str]:
    """Opens url in page, then waits for its fonts (wait_for_fonts)."""
    page.goto(url)
    return wait_for_fonts(page, required_fonts)


def print_pdf(page: Page, width: float, height: float, unit: str = "mm",
              path: str | PathLike | None = None) -> bytes:
    """Prints the first page of page, backgrounds included, on a sheet width by height in unit
    ("mm" or "px"), and returns the PDF, also written to path when given. Playwright counts 3.78 px
    to the millimetre rather than 96 / 25.4, so a design laid out in CSS pixels prints best in px."""
    if unit not in ("mm", "px"):
        raise ValueError(f"unit must be mm or px, not {unit!r}")
    return page.pdf(path=None if path is None else str(path), width=f"{width:.2f}{unit}",
                    height=f"{height:.2f}{unit}", print_background=True, page_ranges="1")


def screenshot(page: Page, clip: dict | None = None, path: str | PathLike | None = None) -> bytes:
    """A PNG of the viewport of page, or of clip ({"x", "y", "width", "height"} in CSS pixels), also
    written to path when given."""
    return page.screenshot(path=None if path is None else str(path), clip=clip, type="png")
