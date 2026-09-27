import pathlib

import pytest

FONTS = pathlib.Path(__file__).resolve().parents[2] / "node_modules" / "@fontsource"
GARAMOND = FONTS / "eb-garamond" / "files" / "eb-garamond-latin-400-normal.woff2"


@pytest.fixture(scope="session")
def browser():
    """One Chromium for the rendering tests, which are skipped without it."""
    from onepage_engine import chromium
    try:
        session = chromium()
        browser = session.__enter__()
    except Exception as e:
        pytest.skip(f"Chromium is missing ({type(e).__name__}): python -m playwright install --only-shell chromium")
    yield browser
    session.__exit__(None, None, None)


@pytest.fixture
def page_url(tmp_path):
    """Writes an HTML page and returns its file URL. With font=True, the text is set in the EB
    Garamond of node_modules, and the test is skipped when those fonts are missing."""
    def write(body, *, font=True, style=""):
        face = ""
        if font:
            if not GARAMOND.exists():
                pytest.skip("node_modules/@fontsource is missing: npm ci")
            face = f"@font-face{{font-family:'EB Garamond';src:url('{GARAMOND.as_uri()}') format('woff2')}}"
        html = (f"<!doctype html><html><head><meta charset='utf-8'><style>{face}"
                f"html,body{{margin:0}}body{{width:100vw;height:100vh;background:#f6f1e6;color:#1d1b17;"
                f"font:40px {'EB Garamond' if font else 'serif'}}}{style}</style></head><body>{body}</body></html>")
        path = tmp_path / f"page-{len(list(tmp_path.iterdir()))}.html"
        path.write_text(html)
        return path.as_uri()
    return write
