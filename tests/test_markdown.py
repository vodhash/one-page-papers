"""The Markdown dialect of the posters (engine/markdown.py): no browser needed."""
import pytest

import markdown
from markdown import MarkdownError


def html(text, **kw):
    return markdown.render(text, **kw)[0]


def test_a_list_split_by_blank_lines_keeps_the_numbers_of_the_source():
    out = html("1. one\n2. two\n\n3. three\n\n4. four")
    assert out.split("\n") == ['<ol><li>one</li><li>two</li></ol>', '<ol start="3"><li>three</li></ol>',
                               '<ol start="4"><li>four</li></ol>']


def test_references_are_numbered_from_the_source_too():
    out = html("## References\n\n1. Nakamoto\n2. Back\n\n3. Dai")
    assert '<span>[1]</span>Nakamoto' in out and '<span>[2]</span>Back' in out and '<span>[3]</span>Dai' in out
    assert '<h2 class=refs>References</h2>' in out


def test_lists_paragraphs_and_inline_marks():
    out = html("- **bold** and *italic*\n- `a*b*c` [1]\n\nA paragraph [2-4].")
    assert out.startswith('<ul><li><b>bold</b> and <i>italic</i></li><li><code>a*b*c</code> <cite>[1]</cite></li></ul>')
    assert out.endswith('<p>A paragraph <cite>[2-4]</cite>.</p>')


def test_smart_quotes_close_after_a_tag():
    assert markdown.smart('"Wien" <i>Wien</i>\'s') == '“Wien” <i>Wien</i>’s'
    assert markdown.smart("it's ('quoted')") == "it’s (‘quoted’)"


def test_numbered_headings():
    out = html("## A\n\n### B\n\n#### C\n\n### D\n\n## E", numbered=True)
    assert [line.split('</span>')[0].split('>')[-1] for line in out.split("\n")] == ["1.", "1.1.", "1.1.1.", "1.2.", "2."]


def test_a_heading_that_starts_with_a_section_number_is_styled_as_one():
    assert html("## 3.1. Proof") == '<h2><span class="n">3.1.</span> Proof</h2>'
    assert html("## 1149 birds") == '<h2>1149 birds</h2>'


def test_math_is_left_as_placeholders_for_katex():
    out, math, _ = markdown.render("Energy \\( E = mc^2 \\) and\n\n$$\na^2 + b^2\n$$")
    assert math == [{"tex": "E = mc^2", "display": False}, {"tex": "a^2 + b^2", "display": True}]
    assert "<!--MATH:0-->" in out and '<div class="eq"><!--MATH:1--></div>' in out


def test_code_blocks_keep_blank_lines_and_are_escaped():
    assert html("```c\nint a;\n\nif (a < b) {}\n```") == '<pre class="code">int a;\n\nif (a &lt; b) {}</pre>'


def test_footnotes_are_numbered_in_the_order_of_their_first_call():
    out = html("B[^b] then A[^a], B again[^b].\n\n[^a]: Note a.\n\n[^b]: Note b.")
    assert 'B<sup class="fn">1</sup> then A<sup class="fn">2</sup>, B again<sup class="fn">1</sup>.' in out
    assert '<li><span>1</span><div>Note b.</div></li><li><span>2</span><div>Note a.</div></li>' in out


@pytest.mark.parametrize("text, line, message", [
    ("Text[^x].", 1, "footnote [^x] is never defined"),
    ("Text.\n\n[^x]: Never called.", 3, "footnote [^x] is defined but never called"),
    ("A[^x].\n\n[^x]: One.\n\n[^x]: Two.", 5, "footnote [^x] is defined twice"),
    ("```\nnever closed", 1, "code block is never closed"),
    ("$$\nx", 1, "math block is never closed"),
    ("::: wide\ntext", 1, 'wide block is never closed'),
    ("::: wide\n::: wide\n:::\n:::", 2, "wide blocks cannot be nested"),
    ("# Title", 1, 'headings are "##"'),
    ("::: figure nowhere", 1, 'unknown figure "nowhere"'),
    ("::: chart x", 1, 'expected "::: figure <name>"'),
])
def test_mistakes_are_reported_with_their_line(text, line, message):
    with pytest.raises(MarkdownError) as e:
        markdown.render(text)
    assert e.value.line == line and message in e.value.msg


def test_figures_come_from_figures_py():
    assert html("::: figure dot", figures={"dot": lambda: "<svg/>"}) == "<figure><svg/></figure>"


def test_a_wide_grid_puts_each_section_in_a_cell():
    out = html("::: wide cols=2\n## One\n\nText one.\n\n## Two\n\nText two.\n:::")
    assert out.startswith('<div class="wide grid" style="--wcols:2"><div class="cell"><h2>One</h2>')
    assert out.count('<div class="cell">') == 2


def test_labelled_items_keep_a_sub_item_with_its_item():
    out = html("(1) First.\n(1a) Its detail.\n(2) Second.")
    assert out.startswith('<div class="group"><div class="item"><span class="lbl">1</span>')
    assert '<div class="item sub"><span class="lbl">1a</span>' in out
    assert out.endswith('<div class="item"><span class="lbl">2</span><div>Second.</div></div>')


@pytest.fixture
def folder(tmp_path):
    from PIL import Image
    Image.new("RGB", (40, 20), "white").save(tmp_path / "plate.png")
    (tmp_path / "drawing.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 150"/>')
    return tmp_path


def test_an_image_is_embedded_with_its_size_and_treatments(folder):
    out = html('::: image plate.png caption="A *plate*" width=50% on_dark=invert on_light=multiply', assets=folder)
    assert out.startswith('<figure class="image" data-dark="invert" data-light="multiply" data-file="plate.png" '
                          'style="width:50%"><img src="data:image/png;base64,')
    assert 'width="40" height="20" alt=""><figcaption>A <i>plate</i></figcaption></figure>' in out
    assert markdown.image_size(folder / "drawing.svg", (folder / "drawing.svg").read_bytes()) == (300, 150)


def test_the_hero_takes_the_first_image_out_of_the_text(folder):
    out, _, hero = markdown.render("::: image plate.png\n\n::: image plate.png", assets=folder, hero=True)
    assert (hero["w"], hero["h"], hero["file"]) == (40, 20, "plate.png")
    assert out.count("<figure") == 1


@pytest.mark.parametrize("head, message", [
    ("::: image missing.png", 'image "missing.png" not found'),
    ("::: image plate.png width=150%", "width must be a percentage"),
    ("::: image plate.png on_dark=glow", "on_dark must be one of plate, invert"),
    ("::: image plate.png on_light=screen", "on_light must be one of multiply"),
    ("::: image plate.png size=2", 'unexpected "size=2"'),
    ('::: image plate.png caption="open', "No closing quotation"),
])
def test_image_mistakes(folder, head, message):
    with pytest.raises(MarkdownError, match=message):
        markdown.render(head, assets=folder)


def test_a_code_fence_ends_the_paragraph_before_it():
    assert html("A line of text\n```\nint a;\n```\nand text after") == \
        '<p>A line of text</p>\n<pre class="code">int a;</pre>\n<p>and text after</p>'
