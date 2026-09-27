"""Real renders with Chromium; skipped without it, or without the fonts of node_modules."""
import io
import struct

import pytest
from pypdf import PdfReader

from onepage_engine import (MM, SIZES, FontLoadError, Renderer, SystemFontError, design_height, load, print_pdf,
                            system_fonts, to_format)


def pages(pdf):
    return PdfReader(io.BytesIO(pdf)).pages


def size_mm(pdf):
    box = pages(pdf)[0].mediabox
    return round(float(box.width) / MM, 1), round(float(box.height) / MM, 1)


def embedded_fonts(pdf):
    """The PostScript names of the fonts of the first page that carry their font file."""
    names = []
    for font in pages(pdf)[0]["/Resources"]["/Font"].values():
        font = font.get_object()
        desc = font["/DescendantFonts"][0].get_object() if "/DescendantFonts" in font else font
        fd = desc["/FontDescriptor"].get_object()
        if any(k in fd for k in ("/FontFile", "/FontFile2", "/FontFile3")):
            names.append(str(fd["/FontName"]).split("+")[-1])
    return names


@pytest.fixture
def renderer(browser):
    r = Renderer(required_fonts=["EB Garamond"], bundled_fonts=["EBGaramond"])
    r.browser = browser  # the session of the tests, rather than a Chromium per test
    return r


def test_render_pdf_prints_the_format_with_the_bundled_font_embedded(renderer, page_url):
    pdf = renderer.render_pdf(page_url("Proof of moment, block 100,000"), design_width=1123, size="A3",
                              title="Block 100000", author="Blockmemento", subject="For Léa")
    assert len(pages(pdf)) == 1
    assert size_mm(pdf) == (297, 420)
    assert "Proof of moment" in pages(pdf)[0].extract_text()
    meta = PdfReader(io.BytesIO(pdf)).metadata
    assert (meta["/Title"], meta["/Author"], meta["/Subject"]) == ("Block 100000", "Blockmemento", "For Léa")
    assert system_fonts(pdf, ["EBGaramond"]) == {}
    assert any(name.startswith("EBGaramond") for name in embedded_fonts(pdf))


@pytest.mark.parametrize("size", ["50x70", "60x80"])
def test_a_format_of_another_ratio_is_the_same_design_scaled(renderer, page_url, size):
    pdf = renderer.render_pdf(page_url("Block 840,000"), design_width=1123, size=size)
    assert size_mm(pdf) == SIZES[size]
    assert len(pages(pdf)) == 1


def test_prepare_fills_the_page_before_it_is_printed(renderer, page_url):
    pdf = renderer.render_pdf(page_url("A placeholder"), design_width=1123, size="A3",
                              prepare=lambda page: page.evaluate("t => document.body.textContent = t", "Block 210,000"))
    assert "Block 210,000" in pages(pdf)[0].extract_text()


def test_a_font_that_fails_to_load_stops_the_render(renderer, page_url):
    url = page_url("x", font=False, style="@font-face{font-family:Lost;src:url('file:///nowhere/lost.woff2')}"
                                          "body{font-family:Lost}")
    with pytest.raises(FontLoadError, match="Lost"):
        renderer.render_pdf(url, design_width=1123, size="A3")


def test_a_required_font_that_the_page_does_not_load_stops_the_render(renderer, page_url):
    with pytest.raises(FontLoadError) as e:
        renderer.render_pdf(page_url("x", font=False), design_width=1123, size="A3")
    assert e.value.missing == "EB Garamond"


def test_text_left_to_a_font_of_the_machine_is_refused(browser, page_url):
    r = Renderer(bundled_fonts=["EBGaramond"])
    r.browser = browser
    url = page_url("Drawn with a font of the machine", font=False)
    try:
        r.render_pdf(url, design_width=1123, size="A3")
    except SystemFontError as e:
        assert set("Drawn") <= set().union(*e.fonts.values())
    else:
        pytest.skip("this machine has no font at all, so Chromium drew no text")


def test_render_png_has_the_size_of_the_viewport_at_the_scale_given(renderer, page_url):
    png = renderer.render_png(page_url("Block 0"), width=400, height=300, scale=2)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (800, 600)


def test_the_steps_print_in_millimetres_as_one_page_papers_does(browser, page_url):
    page = browser.new_page()
    try:
        load(page, page_url("Bitcoin: A Peer-to-Peer Electronic Cash System"), required_fonts=["EB Garamond"])
        pdf = to_format(print_pdf(page, 594, design_height(594, SIZES["60x80"])), "60x80", title="Bitcoin")
    finally:
        page.close()
    assert size_mm(pdf) == (600, 800)
    assert "Peer-to-Peer" in pages(pdf)[0].extract_text()


def test_a_renderer_renders_only_inside_a_with_statement(page_url):
    with pytest.raises(RuntimeError, match="with statement"):
        Renderer().render_pdf(page_url("x", font=False), design_width=100, size="A3")
