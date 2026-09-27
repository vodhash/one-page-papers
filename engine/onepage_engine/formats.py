"""Print formats, as (width, height) in millimetres, and the units of the engine."""

MM = 72 / 25.4  # PDF points per millimetre
PX = 96 / 25.4  # CSS pixels per millimetre

ISO_A = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297), "A5": (148, 210)}
SIZES = {
    **ISO_A,
    "50x70": (500, 700),
    "60x80": (600, 800),
    # US print sizes: Letter, Tabloid, 18 x 24 in and 24 x 36 in
    "letter": (215.9, 279.4),
    "tabloid": (279.4, 431.8),
    "18x24": (457.2, 609.6),
    "24x36": (609.6, 914.4),
}


def design_height(design_width: float, size: tuple[float, float]) -> float:
    """Height of a page laid out design_width wide for the format size: the design keeps its
    width and takes the ratio of the format, so that one layout serves every format, ISO or not,
    once scaled."""
    return design_width * size[1] / size[0]


def resolve(size: str | tuple[float, float]) -> tuple[float, float]:
    """size as (width, height) in millimetres, from a name of SIZES or from the pair itself."""
    if isinstance(size, str):
        try:
            return SIZES[size]
        except KeyError:
            raise ValueError(f"unknown format {size!r} (choose from {', '.join(SIZES)})") from None
    return size
