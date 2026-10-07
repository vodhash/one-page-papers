"""Parts of the site (engine/website/) that need no PDF: the names of the formats, the versions of the
PDF links and their check, and the facts of a poster."""
import pytest

from papers import Paper
from website import common, pages
from website.check import pdf_pattern


@pytest.mark.parametrize("fmt, name", [("A", "A series"), ("50x70", "50 × 70 cm"),
                                       ("letter", "Letter"), ("24x36", "24 × 36 in")])
def test_format_names(fmt, name):
    assert common.format_name(fmt) == name


def test_the_print_guide_names_every_format_in_words():
    main = pages.print_page([], {}).main
    for name in ("Letter", "Tabloid", "18 × 24 in", "24 × 36 in"):
        assert f"<td>{name}</td>" in main
    assert "('" not in main  # never a tuple of Python
    assert "In the US zip" not in main


@pytest.fixture
def pdfs(tmp_path, monkeypatch):
    dist, us = tmp_path / "dist", tmp_path / "release" / "us"
    monkeypatch.setattr(common, "PDF_DIRS", (dist, us))
    common.pdf_version.cache_clear()
    yield Paper("crypto", "bitcoin", None), dist / "crypto", us / "crypto"
    common.pdf_version.cache_clear()


def test_a_pdf_link_ends_with_the_version_of_the_pdfs_of_its_poster(pdfs):
    paper, dist, us = pdfs
    dist.mkdir(parents=True)
    us.mkdir(parents=True)
    (dist / "bitcoin-A-ivory.pdf").write_bytes(b"v1")
    (us / "bitcoin-letter-ivory.pdf").write_bytes(b"us")
    url = common.pdf_url(paper, "A", "ivory")
    k = pdf_pattern().match(url)
    assert (k["category"], k["file"]) == ("crypto", "bitcoin-A-ivory.pdf") and len(k["v"]) == 10
    assert common.pdf_url(paper, "letter", "ivory").endswith(f"?v={k['v']}")  # one version per poster
    (us / "bitcoin-letter-ivory.pdf").write_bytes(b"us, corrected")
    common.pdf_version.cache_clear()
    assert pdf_pattern().match(common.pdf_url(paper, "A", "ivory"))["v"] != k["v"]


def test_the_check_tells_a_versioned_link_from_one_without_version():
    k = pdf_pattern().match("https://files.onepagepapers.com/crypto/bitcoin-A-ivory.pdf")
    assert k["file"] == "bitcoin-A-ivory.pdf" and k["v"] is None
    assert not pdf_pattern().match("https://files.onepagepapers.com/crypto/bitcoin-A-ivory.pdf?v=nothex")


def test_the_facts_of_a_poster_come_in_the_order_asked():
    m = {"min_print": "A2", "lang": "fr", "license": {"text": "Public domain", "holder": "Someone"},
         "source": {"url": "https://www.example.org/x?a=1&b=2", "retrieved": "2026-09-27"}}
    facts = common.poster_facts(m, ("Source", "Language", "Rights holder", "Proposed by"))
    assert facts.split("\n") == [
        '<div><dt>Source</dt><dd><a href="https://www.example.org/x?a=1&amp;b=2">example.org</a></dd></div>',
        "<div><dt>Language</dt><dd>French</dd></div>",
        "<div><dt>Rights holder</dt><dd>Someone</dd></div>"]


def test_the_pdf_links_of_the_readme_carry_the_version_of_the_files_of_the_paper(tmp_path):
    import readme
    from papers import source_version
    d = tmp_path / "bitcoin"
    d.mkdir()
    (d / "text.md").write_text("v1")
    paper = Paper("crypto", "bitcoin", d)
    v1 = source_version(paper)
    assert readme.pdf(paper, "ivory") == f"https://files.onepagepapers.com/crypto/bitcoin-A-ivory.pdf?v={v1}"
    (d / "annotations.yaml").write_text("notes: []")  # read by the site only: the PDF does not change
    (d / "text.md~").write_text("v0")  # an editor's backup, a draft, an unused image: not the poster
    (d / "draft.md").write_text("v0")
    (d / "unused.png").write_bytes(b"png")
    assert source_version(paper) == v1
    (d / "plate.png").write_bytes(b"png")
    (d / "text.md").write_text("v1\n\n::: image plate.png")
    assert source_version(paper) != v1  # an image that the poster shows counts
    v1 = source_version(paper)
    (d / "plate.png").write_bytes(b"png, retouched")
    assert source_version(paper) != v1
    (d / "text.md").write_text("v1")
    (d / "text.md").write_text("v2")
    assert source_version(paper) != v1


def test_the_version_of_a_paper_is_the_same_whatever_its_line_ends_and_its_code_blocks(tmp_path):
    from papers import source_version
    d = tmp_path / "rfc-1"
    d.mkdir()
    paper = Paper("internet", "rfc-1", d)
    (d / "text.md").write_bytes(b"line\nline\n")
    lf = source_version(paper)
    (d / "text.md").write_bytes(b"line\r\nline\r\n")  # a checkout with core.autocrlf, on Windows
    assert source_version(paper) == lf
    (d / "text.md").write_text("```\n::: image unused.png\n```\n")  # a directive shown in a code block
    (d / "unused.png").write_bytes(b"png")
    shown = source_version(paper)
    (d / "unused.png").write_bytes(b"png, changed")
    assert source_version(paper) == shown
