"""The images of the site: the previews of the posters, rasterized from their A PDFs, the Open
Graph images, the logo as a bitmap, and the images of the reading pages, all cached in
build/site-previews/."""
import concurrent.futures, hashlib, io, os, shutil, subprocess, time

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import markdown
from papers import ROOT
from .common import A_H, A_W, CACHE, PREVIEW_VERSION, PREVIEW_WIDTHS, SMALL_W, SiteError, TOKENS, pdf_file, save_atomic

def pdftoppm():
    path = shutil.which("pdftoppm")
    if not path:
        raise SiteError("pdftoppm is missing, install poppler-utils (apt install poppler-utils)")
    return path

def webp(im):
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=72, method=6)  # the same to the eye as 80 on these pages of text, and 20% lighter
    return buf.getvalue()

def rasterize(pdf):
    """The WebP previews of the page of an A PDF, {width: path in the cache}: poppler draws it
    1200 px wide, Pillow reduces it to 600."""
    key = f"{hashlib.sha256(pdf.read_bytes()).hexdigest()[:24]}-v{PREVIEW_VERSION}"
    paths = {w: CACHE / f"{key}-{w}.webp" for w in PREVIEW_WIDTHS}
    if all(p.exists() for p in paths.values()):
        return paths
    r = subprocess.run([pdftoppm(), "-singlefile", "-scale-to-x", str(max(PREVIEW_WIDTHS)), "-scale-to-y", "-1",
                        str(pdf)], capture_output=True)
    if r.returncode:
        raise SiteError(f"{pdf.relative_to(ROOT)}: pdftoppm failed: {r.stderr.decode(errors='replace').strip()}")
    big = Image.open(io.BytesIO(r.stdout)).convert("RGB")
    for w, path in paths.items():
        im = big if w == big.width else big.resize((w, round(w * A_H / A_W)), Image.LANCZOS)
        save_atomic(path, webp(im))
    return paths

def mark_image(k, bold=False):
    """The logo of mark_svg as an RGBA image, k px per unit of its 60 x 84 grid, drawn at 4x then
    reduced. bold thickens it and keeps four lines of text, for the small icons."""
    ink, acc, paper, mute = (TOKENS[t][0] for t in ("ink", "acc", "bg", "mute"))
    K = 4 * k
    im = Image.new("RGBA", (round(60 * K), round(84 * K)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = lambda x, y, w, h: (x * K, y * K, (x + w) * K, (y + h) * K)
    d.rectangle(box(2.5, 2.5, 55, 79), fill=paper, outline=ink, width=round((4.5 if bold else 3) * K))
    if not bold:
        d.rectangle(box(7, 7, 46, 70), outline=ink, width=round(1.2 * K))
    for x in (13, 37):
        d.line((x * K, 21 * K, (x + 10) * K, 21 * K), fill=ink, width=round((3 if bold else 1.6) * K))
    d.ellipse(box(24.5, 15.5, 11, 11) if bold else box(25.4, 16.4, 9.2, 9.2), fill=acc)
    rows = [(36, 47), (46, 47), (56, 47), (66, 35)] if bold else \
           [(y, 47 if i % 4 != 3 else 35) for i, y in enumerate(range(36, 74, 5))]
    for y, end in rows:
        d.line((13 * K, y * K, end * K, y * K), fill=mute, width=round((3.2 if bold else 1.6) * K))
    return im.resize((round(60 * k), round(84 * k)), Image.LANCZOS)

def matted(im, height, pad):
    """A preview reduced to a height, in its passe-partout (light frame colour)."""
    im = im.resize((round(height * im.width / im.height), height), Image.LANCZOS)
    mat = Image.new("RGB", (im.width + 2 * pad, im.height + 2 * pad), TOKENS["frame"][0])
    mat.paste(im, (pad, pad))
    return mat

def share_image(sources, brand=False):
    """The Open Graph image, 1200 x 630: the posters side by side on the wall, each in its
    passe-partout with a soft shadow, as on the site. sources are 1200 px WebP previews. With
    brand, the logo and the name of the site sit under the posters."""
    key = hashlib.sha256(b"".join(s.read_bytes() for s in sources) + f"v{PREVIEW_VERSION}{brand}".encode()).hexdigest()[:24]
    path = CACHE / f"share-{key}.jpg"
    if path.exists():
        return path
    W, H = 1200, 630
    height = 500 if len(sources) == 1 else 380 if brand else 430
    mats = [matted(Image.open(s).convert("RGB"), height, 14) for s in sources]
    gap = 56
    x = (W - sum(m.width for m in mats) - gap * (len(mats) - 1)) // 2
    canvas = Image.new("RGB", (W, H), TOKENS["wall"][0])
    shadow = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(shadow)
    boxes = []
    for m in mats:
        y = (H - m.height) // 2 - (38 if brand else 0)
        boxes.append((x, y))
        draw.rectangle((x + 6, y + 16, x + m.width - 6, y + m.height + 10), fill=120)
        x += m.width + gap
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    canvas.paste(Image.new("RGB", (W, H), "#3a3226"), (0, 0), shadow)
    for m, (x, y) in zip(mats, boxes):
        canvas.paste(m, (x, y))
    if brand:
        fonts = ROOT / "node_modules/@fontsource/eb-garamond/files"
        roman = ImageFont.truetype(str(fonts / "eb-garamond-latin-500-normal.woff2"), 40)
        italic = ImageFont.truetype(str(fonts / "eb-garamond-latin-400-italic.woff2"), 40)
        mark = mark_image(0.62)
        d = ImageDraw.Draw(canvas)
        w1, w2 = d.textlength("One Page ", font=roman), d.textlength("Papers", font=italic)
        x = (W - mark.width - 18 - w1 - w2) / 2
        y = H - 78
        canvas.paste(mark, (round(x), y - mark.height // 2), mark)
        x += mark.width + 18
        d.text((x, y), "One Page ", font=roman, fill=TOKENS["ink"][0], anchor="lm")
        d.text((x + w1, y), "Papers", font=italic, fill=TOKENS["ink"][0], anchor="lm")
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=86, optimize=True, progressive=True)
    save_atomic(path, buf.getvalue())
    return path

def prune(used):
    """Removes the files of the cache that this run did not use, such as the previews of a PDF
    since rebuilt, once they are a day old: a run that is going on at the same time keeps its own."""
    for f in CACHE.iterdir():
        if f not in used and time.time() - f.stat().st_mtime > 86400:
            f.unlink(missing_ok=True)

def make_previews(out, posters):
    """Writes out/previews/: <slug>-<theme>-<width>.webp for every theme of every poster, from
    the cache or rasterized in parallel. Returns {(slug, theme): {width: path in the site}}."""
    CACHE.mkdir(parents=True, exist_ok=True)
    (out / "previews").mkdir(parents=True)
    jobs = [(p, t) for p in posters for t in p.themes]
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(16, os.cpu_count() or 2)) as ex:
        done = list(ex.map(lambda job: rasterize(pdf_file(job[0].paper, "A", job[1])), jobs))
    previews = {}
    for (p, t), paths in zip(jobs, done):
        previews[p.slug, t] = {}
        for w, src in paths.items():
            dst = f"previews/{p.slug}-{t}-{w}.webp"
            shutil.copyfile(src, out / dst)
            previews[p.slug, t][w] = dst
    return previews, {(q.slug, t): paths for (q, t), paths in zip(jobs, done)}

SMALL_H = round(SMALL_W * A_H / A_W)

def make_thumbs(out, series, cached):
    """Writes out/previews/<slug>-<theme>-<SMALL_W>.webp, the small previews of the series cards,
    for the light and dark theme of every poster of a series, reduced from the cached 600 px
    previews. Returns ({(slug, theme): path in the site}, the files of the cache it used)."""
    thumbs, used = {}, set()
    for p in {p.slug: p for s in series for p in s.posters}.values():
        for t in dict.fromkeys((p.light, p.dark)):
            src = cached[p.slug, t][600]
            path = CACHE / f"{src.stem.removesuffix('-600')}-{SMALL_W}.webp"
            if not path.exists():
                with Image.open(src) as im:
                    save_atomic(path, webp(im.convert("RGB").resize((SMALL_W, SMALL_H), Image.LANCZOS)))
            dst = f"previews/{p.slug}-{t}-{SMALL_W}.webp"
            shutil.copyfile(path, out / dst)
            thumbs[p.slug, t] = dst
            used.add(path)
    return thumbs, used

READ_IMAGE_W = 2000  # px: the raster images of a reading page are reduced to this width at most
READ_VERSION = 1  # part of the cache key of the images of the reading pages

def web_image(path):
    """An image of a text for the web, in the cache: an SVG as it is, a raster image as WebP at
    most READ_IMAGE_W wide. Returns (path in the cache, width, height)."""
    data = path.read_bytes()
    key = f"read-{hashlib.sha256(data).hexdigest()[:24]}-v{READ_VERSION}"
    if path.suffix.lower() == ".svg":
        dst = CACHE / f"{key}.svg"
        if not dst.exists():
            save_atomic(dst, data)
        w, h = markdown.image_size(path, data)
        return dst, w, h
    dst = CACHE / f"{key}.webp"
    if dst.exists():
        with Image.open(dst) as im:
            return dst, *im.size
    im = Image.open(io.BytesIO(data))
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info else "RGB")
    if im.width > READ_IMAGE_W:
        im = im.resize((READ_IMAGE_W, round(im.height * READ_IMAGE_W / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=84, method=6)
    save_atomic(dst, buf.getvalue())
    return dst, im.width, im.height
