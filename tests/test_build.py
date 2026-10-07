"""build.py and the meta.yaml of papers.py, without a browser: the checks of meta.yaml, the search
of the body size, the cache and its warnings, the errors of a paper, and the treatment of images."""
import base64
import contextlib
import io
import re
import types

import pytest
from PIL import Image

import build
from papers import BuildError, Paper, load_meta, pdf_name, pdf_url, themes_of
from themes import colour

VALID = """\
title: A paper
summary: Says something in one sentence.
year: 1900
authors: [Someone]
min_print: A2
source: {url: "https://example.org/paper", retrieved: 2026-01-01, edition: The first edition.}
license: {text: Public domain, basis: Its author died in 1901.}
commercial: true
commercial_basis: Public domain.
"""


def make_paper(tmp_path, meta=VALID, slug="a-paper", text="Some text."):
    d = tmp_path / "papers" / "physics" / slug
    d.mkdir(parents=True)
    (d / "meta.yaml").write_text(meta)
    (d / "text.md").write_text(text)
    return Paper("physics", slug, d)


def test_a_valid_meta_loads(tmp_path):
    assert load_meta(make_paper(tmp_path).dir)["title"] == "A paper"


@pytest.mark.parametrize("line, message", [
    ("colour: red", "unknown key 'colour'"),
    ("summary: " + "word " * 21 + "end.", "summary must be one sentence of 20 words at most"),
    ("authors: Someone", "authors must be a list of names"),
    ("min_print: B2", "min_print must be one of A3, A2, A1, A0"),
    ("source: {url: https://example.org}", "source needs exactly url, retrieved (a date) and edition"),
    ("license: {text: MIT}", "license needs text, and either notice"),
    ("commercial: maybe", "commercial must be true or false"),
    ("font_range: [20, 10]", "font_range must be [min, max] in pt"),
    ("max_font: 5", "max_font must be a size in pt above the minimum of font_range"),
    ("layout: spiral", "layout must be one of columns, centered, hero"),
    ("themes: [neon]", "themes must be a list of some of ivory, white, genesis, blueprint"),
    ("hero_height: 95", "hero_height must be a percentage of the page height"),
    ("contributors: ['@someone']", "contributors must be a list of GitHub user names"),
    ("footer: [a, b, c, d]", "footer takes at most 3 cells"),
])
def test_a_meta_that_breaks_a_rule_is_refused(tmp_path, line, message):
    with pytest.raises(BuildError, match=re.escape(message)):
        load_meta(make_paper(tmp_path, VALID + line + "\n").dir)  # the last of two keys wins


@pytest.mark.parametrize("meta, message", [
    (VALID.replace("title: A paper\n", ""), "missing 'title'"),
    ("title: [never closed\n", "meta.yaml: while parsing"),
    ("- a list\n", "expected a mapping of keys"),
])
def test_a_meta_that_cannot_be_read_is_refused(tmp_path, meta, message):
    with pytest.raises(BuildError, match=message):
        load_meta(make_paper(tmp_path, meta).dir)


def test_themes_follow_the_order_of_the_themes():
    assert themes_of({"themes": ["genesis", "ivory"]}) == ["ivory", "genesis"]
    assert themes_of({}) == ["ivory", "white", "genesis", "blueprint"]


def test_a_pdf_has_one_name_in_dist_and_in_the_bucket():
    p = Paper("crypto", "bitcoin", None)
    assert pdf_name("bitcoin", "A", "ivory") == "bitcoin-A-ivory.pdf"
    assert pdf_url(p, "letter", "genesis") == "https://files.onepagepapers.com/crypto/bitcoin-letter-genesis.pdf"


class Page:
    """A page on which the text fits up to a body size, limit (pt)."""

    def __init__(self, limit):
        self.limit, self.tried = limit, []

    def evaluate(self, js, fs):
        self.tried.append(fs)
        return fs <= self.limit


def test_the_body_size_is_the_largest_that_fits_on_the_grid_of_hundredths():
    page = Page(12.345)
    assert build.best_font(page, 8, 40, "a-paper A") == (12.34, False)
    assert all(abs(fs * 100 - round(fs * 100)) < 1e-9 for fs in page.tried)


def test_a_text_that_fits_at_the_maximum_says_so():
    assert build.best_font(Page(50), 8, 40, "a-paper A") == (40.0, True)


def test_a_text_that_overflows_at_the_minimum_fails():
    with pytest.raises(BuildError, match="overflows even at 8.0 pt, lower font_range"):
        build.best_font(Page(5), 8, 40, "a-paper A")


@pytest.mark.parametrize("fs, size", [(16, "A3"), (12, "A2"), (8, "A1"), (6, "A0"), (5, None)])
def test_min_print_is_the_smallest_size_with_a_body_of_8_pt(fs, size):
    assert build.min_print(fs) == size


def test_printed_sizes():
    assert build.printed("A", 10) == "A0 14.1, A1 10.0, A2 7.1, A3 5.0 pt printed"
    assert build.printed("50x70", 10) == "8.4 pt printed"


@pytest.fixture
def no_browser(tmp_path, monkeypatch):
    """build() without Chromium: a format fits at the maximum of its body size (which deserves a
    warning), and its PDFs hold the name of their theme. Returns the options and the page."""
    monkeypatch.setattr(build, "out_dir", lambda paper, fmt: tmp_path / "dist" / paper.category)
    monkeypatch.setattr(build, "load", lambda page, path, html: None)
    monkeypatch.setattr(build, "best_font", lambda page, lo, hi, what: (float(hi), True))
    fresh = types.SimpleNamespace(context=types.SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(build, "settle", lambda browser, viewport, tmp, html, fs, hi, what: (fs, fresh))

    def print_format(job, fmt, fs, page, at_cap, log):
        log.say(f"{job.paper.slug} {fmt}: body {fs:.2f} pt")
        out = build.out_dir(job.paper, fmt)
        out.mkdir(parents=True, exist_ok=True)
        made = {pdf_name(job.paper.slug, fmt, th): b"%PDF " + th.encode() for th in job.themes}
        for name, data in made.items():
            (out / name).write_bytes(data)
        return made
    monkeypatch.setattr(build, "print_format", print_format)
    page = types.SimpleNamespace(set_viewport_size=lambda viewport: None, context=types.SimpleNamespace(browser=None))
    a = types.SimpleNamespace(formats=["A"], themes=["ivory", "white"], no_previews=True, check=True,
                              cache=tmp_path / "cache")
    return a, page


def test_a_format_taken_from_the_cache_gives_its_warnings_again(tmp_path, monkeypatch, no_browser, capsys):
    a, page = no_browser
    paper = make_paper(tmp_path)
    first, again = [], []
    build.build(paper, a, page, first)
    assert first == ["a-paper A: the text still fits at 40.0 pt and leaves space, raise font_range in meta.yaml"]
    # nothing changed: the format comes from the cache, with its warning, so that a check fails again
    monkeypatch.setattr(build, "build_format", lambda *args: pytest.fail("laid out again"))
    (tmp_path / "dist" / "physics" / "a-paper-A-white.pdf").unlink()
    build.build(paper, a, page, again)
    assert again == first
    assert (tmp_path / "dist" / "physics" / "a-paper-A-white.pdf").read_bytes() == b"%PDF white"
    assert "a-paper A: body 40.00 pt (cached)" in capsys.readouterr().out


def test_a_changed_paper_is_laid_out_again(tmp_path, monkeypatch, no_browser):
    a, page = no_browser
    paper = make_paper(tmp_path)
    build.build(paper, a, page, [])
    (paper.dir / "text.md").write_text("Another text.")
    laid_out, original = [], build.build_format
    monkeypatch.setattr(build, "build_format", lambda job, fmt, *rest: laid_out.append(fmt) or original(job, fmt, *rest))
    build.build(paper, a, page, [])
    assert laid_out == ["A"]


def test_a_paper_that_fails_does_not_stop_the_others(monkeypatch, capsys):
    built = []

    def fake_build(paper, a, page, warnings):
        if paper.slug == "b":
            raise ZeroDivisionError("in figures.py")
        if paper.slug == "c":
            raise BuildError("papers/x/c/meta.yaml: missing 'title'")
        built.append(paper.slug)
    monkeypatch.setattr(build, "build", fake_build)
    pages = []

    @contextlib.contextmanager
    def chromium():
        yield types.SimpleNamespace(new_page=lambda: pages.append(1) or types.SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(build, "chromium", chromium)
    failed, warnings = build.build_all([Paper("x", s, None) for s in "abcd"], None)
    assert (failed, warnings, built) == (["b", "c"], [], ["a", "d"])
    assert len(pages) == 2  # a page of its own for the paper after the one that raised
    err = capsys.readouterr().err
    assert "error: papers/x/b: ZeroDivisionError: in figures.py" in err
    assert "error: papers/x/c/meta.yaml: missing 'title'" in err


def test_a_browser_that_does_not_start_fails_every_paper(monkeypatch, capsys):
    @contextlib.contextmanager
    def chromium():
        raise RuntimeError("Executable doesn't exist")
        yield
    monkeypatch.setattr(build, "chromium", chromium)
    failed, _ = build.build_all([Paper("x", s, None) for s in "ab"], None)
    assert failed == ["a", "b"]
    assert "the browser failed (RuntimeError: Executable doesn't exist), 2 paper(s) not built" in capsys.readouterr().err


def pixels(uri):
    im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGB")
    return [im.getpixel((x, 0)) for x in range(im.width)]


def rgb(theme, name):
    return tuple(round(c * 255) for c in colour(theme, name))


@pytest.fixture
def black_and_white(tmp_path):
    path = tmp_path / "plate.png"
    im = Image.new("RGB", (2, 1), "white")
    im.putpixel((1, 0), (0, 0, 0))
    im.save(path)
    return path


def test_invert_turns_white_into_the_paper_and_black_into_the_ink(black_and_white):
    assert pixels(build.treated(black_and_white, "invert", "genesis")) == [rgb("genesis", "paper"),
                                                                            rgb("genesis", "ink")]


def test_multiply_melts_white_into_the_paper_and_keeps_black(black_and_white):
    assert pixels(build.treated(black_and_white, "multiply", "ivory")) == [rgb("ivory", "paper"), (0, 0, 0)]
