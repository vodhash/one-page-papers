"""Colour themes (CSS variables) and print formats (width, height in mm)."""
import re

from onepage_engine import SIZES

THEMES = {
    "ivory":     "--paper:#f6f1e6;--ink:#1d1b17;--mute:#6b645a;--acc:#e0800d;--onacc:#f6f1e6;--rule:#c9bfae;--box:#fbf8f1;--boxa:#f6dcb4;--code:#ede5d5",
    "white":     "--paper:#ffffff;--ink:#111111;--mute:#666666;--acc:#f7931a;--onacc:#ffffff;--rule:#d4d4d4;--box:#ffffff;--boxa:#fde6c6;--code:#f2f2f2",
    "genesis":   "--paper:#121110;--ink:#ece6d8;--mute:#9a9284;--acc:#f7931a;--onacc:#121110;--rule:#3a3631;--box:#1c1a18;--boxa:#3d2a12;--code:#1e1c19",
    "blueprint": "--paper:#12304f;--ink:#e8f0f8;--mute:#9db4cc;--acc:#7fd1ff;--onacc:#12304f;--rule:#2f5277;--box:#16395d;--boxa:#1f5680;--code:#0f2944",
}
# "A" prints at any ISO A size (A0 to A3); the file itself is A1.
FORMATS = {"A": SIZES["A1"], "50x70": SIZES["50x70"], "60x80": SIZES["60x80"]}
# US print sizes, built on demand (build.py --us) into release/us/, which git ignores: only the
# formats above are versioned in dist/. Letter, Tabloid, 18 x 24 in and 24 x 36 in.
US_FORMATS = {name: SIZES[name] for name in ("letter", "tabloid", "18x24", "24x36")}

def colour(theme, name):
    """A colour of a theme as (r, g, b), each from 0 to 1."""
    return tuple(int(h, 16) / 255 for h in re.findall(rf"--{name}:#(..)(..)(..)", THEMES[theme])[0])

def dark(theme):
    """Whether the paper of a theme is dark, which changes how images are shown on it."""
    r, g, b = colour(theme, "paper")
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.5
