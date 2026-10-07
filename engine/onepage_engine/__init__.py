"""Renders a single HTML page to a vector PDF at a fixed design width, scaled to print formats,
with embedded fonts and the same layout on every machine.

This is the engine of one-page-papers as a package. Renderer renders a page in one call; the
functions below are its steps, for a caller that acts on the page between loading and printing
(one-page-papers fits the size of its text there). README.md documents the whole API.

The parts that need Playwright (rendering) or pypdf (the PDF side) are imported on first use, so
that a caller of the formats and errors alone, such as a script that only reads SIZES, needs neither.
"""
import importlib
from typing import TYPE_CHECKING

from .errors import EngineError, FontLoadError, SystemFontError
from .formats import ISO_A, MM, PX, SIZES, design_height

if TYPE_CHECKING:
    from .browser import CHROMIUM_ARGS, chromium, load, print_pdf, screenshot, wait_for_fonts
    from .pdf import font_name, same_pdf, system_fonts, to_format
    from .render import Renderer

__version__ = "0.1.0"

__all__ = [
    "CHROMIUM_ARGS", "ISO_A", "MM", "PX", "SIZES", "EngineError", "FontLoadError", "Renderer",
    "SystemFontError", "chromium", "design_height", "font_name", "load", "print_pdf", "same_pdf",
    "screenshot", "system_fonts", "to_format", "wait_for_fonts",
]

# the name of each lazy attribute: the module that defines it
_LAZY = {
    **dict.fromkeys(("CHROMIUM_ARGS", "chromium", "load", "print_pdf", "screenshot", "wait_for_fonts"), "browser"),
    **dict.fromkeys(("font_name", "same_pdf", "system_fonts", "to_format"), "pdf"),
    "Renderer": "render",
}


def __getattr__(name: str):
    if name not in _LAZY:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(f".{_LAZY[name]}", __name__), name)
    globals()[name] = value  # the next access does not come back here
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY))
