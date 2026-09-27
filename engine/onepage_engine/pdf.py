"""The PDF side: a printed page scaled to its format, the fonts that are not the bundled ones, and
the comparison of two PDFs."""
import io
from collections.abc import Iterable
from os import PathLike

from pypdf import PdfReader, PdfWriter

from .formats import MM, resolve

Source = bytes | str | PathLike


def _source(pdf: Source):
    """What PdfReader reads: a stream over bytes, or the path itself."""
    return io.BytesIO(pdf) if isinstance(pdf, (bytes, bytearray)) else pdf


def to_format(pdf: Source, size: str | tuple[float, float], *, title: str | None = None,
              author: str | None = None, subject: str | None = None, creator: str | None = None) -> bytes:
    """The first page of pdf scaled to size (a name of SIZES, or (width, height) in millimetres), as
    a new PDF with the metadata given; None leaves an entry out. The page stays vector and its
    content is compressed losslessly."""
    width, height = resolve(size)
    w = PdfWriter()
    pg = w.add_page(PdfReader(_source(pdf)).pages[0])
    pg.scale_to(width * MM, height * MM)
    pg.compress_content_streams()  # lossless; pypdf would store the rescaled stream uncompressed
    meta = {key: value for key, value in (("/Title", title), ("/Author", author), ("/Subject", subject),
                                          ("/Creator", creator)) if value is not None}
    if meta:
        w.add_metadata(meta)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def font_name(font) -> str:
    """PostScript name of a PDF font without its subset tag. Chromium embeds some glyphs
    (synthetic bold, for instance) as Type 3 fonts, whose name is only in the descriptor."""
    fd = font.get("/FontDescriptor")
    name = font.get("/BaseFont") or (fd.get_object().get("/FontName") if fd is not None else None)
    return str(name or "an unnamed font").lstrip("/").split("+")[-1]


def system_fonts(pdf: Source, bundled: Iterable[str]) -> dict[str, set[str]]:
    """Maps each font of the first page of pdf whose PostScript name starts with none of the
    prefixes of bundled to the characters it draws: text that the bundled fonts could not draw,
    left to the fonts of the machine."""
    prefixes = tuple(bundled)
    found = {}

    def visit(text, cm, tm, font, size):
        if font is not None and text.strip():
            name = font_name(font)
            if not name.startswith(prefixes):
                found.setdefault(name, set()).update(c for c in text if not c.isspace())

    PdfReader(_source(pdf)).pages[0].extract_text(visitor_text=visit)
    return found


def same_line(x: bytes, y: bytes) -> bool:
    """Whether two lines of the content stream of a page differ only in ways that do not show:
    the last digits of a number, which vary with the processor (the matrix of a rotation, for
    instance, as the CI and a laptop compute its sine), or the vertical offset of a text matrix
    (Tm) by less than a pixel, which Chromium now and then rounds (see same_pdf)."""
    tx, ty = x.split(), y.split()
    if len(tx) != len(ty) or tx[-1:] != ty[-1:]:
        return False
    for i, (u, v) in enumerate(zip(tx, ty)):
        if u == v:
            continue
        try:
            fu, fv = float(u), float(v)
        except ValueError:
            return False
        if abs(fu - fv) > 1e-6 * max(1, abs(fu), abs(fv)) and not (tx[-1] == b"Tm" and i == 5 and abs(fu - fv) < 1):
            return False
    return True


def same_pdf(old: bytes, new: bytes) -> bool:
    """Whether two PDFs of one page are the same, but for differences that do not show: now and
    then, in about one print in twenty of a page full of formulas, Chromium sets one run of glyphs
    of a KaTeX formula (in a fraction, or an equation number) on a baseline rounded to a whole
    pixel, and the last digits of some numbers depend on the processor. Line by line, the content
    stream of the page may differ only in that way (same_line), and everything else must be the
    same byte for byte."""
    if old == new:
        return True
    try:
        a, b = PdfReader(io.BytesIO(old)), PdfReader(io.BytesIO(new))
        ca = a.pages[0].get_contents().get_data().split(b"\n")
        cb = b.pages[0].get_contents().get_data().split(b"\n")
    except Exception:
        return False
    if len(ca) != len(cb) or not all(x == y or same_line(x, y) for x, y in zip(ca, cb)):
        return False

    def objects(data, r):
        """Every object but the content stream of the page, as the file writes it."""
        skip = r.pages[0].raw_get("/Contents").idnum
        starts = sorted((offset, num) for num, offset in r.xref[0].items())
        ends = [offset for offset, _ in starts[1:]] + [data.rindex(b"\nxref\n")]
        return {num: data[start:end] for (start, num), end in zip(starts, ends) if num != skip}

    return objects(old, a) == objects(new, b)
