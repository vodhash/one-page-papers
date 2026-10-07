import subprocess
import sys

import pytest

from onepage_engine import ISO_A, SIZES, design_height
from onepage_engine.formats import resolve


def test_each_iso_size_is_the_previous_one_folded_in_two():
    sizes = list(ISO_A.values())
    for (w, h), (w2, h2) in zip(sizes, sizes[1:]):
        assert (w2, h2) == (h // 2, w)


def test_sizes_hold_the_formats_of_one_page_papers_and_blockmemento():
    assert SIZES["A1"] == (594, 841) and SIZES["A3"] == (297, 420)
    assert SIZES["50x70"] == (500, 700) and SIZES["60x80"] == (600, 800)
    assert SIZES["letter"] == (215.9, 279.4)


def test_design_height_keeps_the_width_and_takes_the_ratio_of_the_format():
    assert design_height(594, SIZES["A1"]) == 841
    assert design_height(594, SIZES["50x70"]) == 594 * 700 / 500
    assert round(design_height(1123, SIZES["A3"]), 2) == 1588.08


def test_resolve_takes_a_name_or_a_pair():
    assert resolve("A3") == (297, 420)
    assert resolve((100, 150)) == (100, 150)
    with pytest.raises(ValueError, match="unknown format 'B5'"):
        resolve("B5")


def test_the_formats_need_neither_playwright_nor_pypdf():
    code = ("import sys, onepage_engine; onepage_engine.SIZES; onepage_engine.FontLoadError; "
            "print(sorted(m for m in ('playwright', 'pypdf') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "[]"


def test_the_rest_of_the_api_is_imported_on_first_use():
    import onepage_engine
    assert onepage_engine.same_pdf.__module__ == "onepage_engine.pdf"
    assert onepage_engine.Renderer.__module__ == "onepage_engine.render"
    assert set(onepage_engine.__all__) <= set(dir(onepage_engine))
    with pytest.raises(AttributeError, match="no attribute 'nothing'"):
        onepage_engine.nothing
