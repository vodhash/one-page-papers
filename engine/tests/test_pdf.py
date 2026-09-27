"""The PDF side, on PDFs written with pypdf: no browser needed."""
import io

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject

from onepage_engine import MM, same_pdf, to_format


def pdf_with(content: bytes, width: float = 595.28, height: float = 841.89) -> bytes:
    """A one-page PDF whose content stream is content."""
    w = PdfWriter()
    page = w.add_blank_page(width, height)
    stream = DecodedStreamObject()
    stream.set_data(content)
    page.replace_contents(stream)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def page_size_mm(pdf: bytes) -> tuple[float, float]:
    box = PdfReader(io.BytesIO(pdf)).pages[0].mediabox
    return round(float(box.width) / MM, 2), round(float(box.height) / MM, 2)


def test_to_format_scales_the_page_and_writes_the_metadata_given():
    pdf = to_format(pdf_with(b"0 0 m 100 100 l S"), (297, 420), title="Block 100000", author="", creator="test")
    assert page_size_mm(pdf) == (297, 420)
    meta = PdfReader(io.BytesIO(pdf)).metadata
    assert (meta["/Title"], meta["/Author"], meta["/Creator"]) == ("Block 100000", "", "test")
    assert "/Subject" not in meta


def test_to_format_takes_a_format_name_and_keeps_the_page_vector_and_compressed():
    pdf = to_format(pdf_with(b"0 0 m 100 100 l S"), "50x70", subject="For Léa, born in this block")
    assert page_size_mm(pdf) == (500, 700)
    page = PdfReader(io.BytesIO(pdf)).pages[0]
    assert PdfReader(io.BytesIO(pdf)).metadata["/Subject"] == "For Léa, born in this block"
    assert page["/Contents"].get_object()["/Filter"] == "/FlateDecode"
    assert b"100 100 l" in page.get_contents().get_data()  # still a path, not an image


def test_same_pdf_accepts_identical_files():
    pdf = pdf_with(b"0 0 m 100 100 l S")
    assert same_pdf(pdf, pdf)


@pytest.mark.parametrize("a, b", [
    (b"1 0 0 1 10.00000001 20 cm", b"1 0 0 1 10.00000002 20 cm"),  # the last digits of a number
    (b"BT\n1 0 0 1 100 200.4 Tm\nET", b"BT\n1 0 0 1 100 200 Tm\nET"),  # a baseline rounded to a pixel
])
def test_same_pdf_tolerates_the_differences_that_do_not_show(a, b):
    assert same_pdf(pdf_with(a), pdf_with(b))


@pytest.mark.parametrize("a, b", [
    (b"0 0 m 100 100 l S", b"0 0 m 100 110 l S"),                  # a line moved by 10 points
    (b"BT\n1 0 0 1 100 200 Tm\nET", b"BT\n1 0 0 1 101.5 200 Tm\nET"),  # a text moved sideways
    (b"0 0 m 100 100 l S", b"0 0 m 100 100 l S\n0 0 m 50 50 l S"),  # one more line
])
def test_same_pdf_sees_the_differences_that_show(a, b):
    assert not same_pdf(pdf_with(a), pdf_with(b))


def test_same_pdf_sees_a_different_page_size_and_rejects_what_is_not_a_pdf():
    assert not same_pdf(pdf_with(b"0 0 m 1 1 l S"), pdf_with(b"0 0 m 1 1 l S", width=600))
    assert not same_pdf(b"not a pdf", b"not a pdf either")
